"""Load source-aligned DataFrames into Snowflake RAW.

Each dataset load:
  1. writes every frame to a session-temporary table (write_pandas),
  2. creates the RAW table if needed (source columns VARCHAR; VARIANT where
     declared; typed metadata), or checks an existing table for schema drift,
  3. removes orphan rows left by an earlier, unfinished run,
  4. appends with a single INSERT ... SELECT,
  5. returns the RAW row count for this run's _INGEST_RUN_ID.

Source values stay strings in RAW. Analytical typing belongs to dbt STAGING.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd
from snowflake.connector import SnowflakeConnection
from snowflake.connector.pandas_tools import write_pandas

from .common import METADATA_COLUMNS, Check, IngestionError, log

METADATA_DDL = {
    "_INGEST_RUN_ID": "VARCHAR",
    "_INGESTED_AT": "TIMESTAMP_TZ",
    "_SOURCE_ID": "VARCHAR",
    "_SOURCE_VINTAGE": "VARCHAR",
    "_SOURCE_FILE": "VARCHAR",
    "_SOURCE_FILE_SHA256": "VARCHAR",
    "_SOURCE_ROW_NUMBER": "NUMBER(38,0)",
}


def _split(table: str) -> tuple[str, str]:
    schema, name = table.split(".")
    return schema, name


def existing_columns(conn: SnowflakeConnection, table: str) -> list[str] | None:
    schema, name = _split(table)
    cur = conn.cursor()
    cur.execute(
        """SELECT column_name FROM AUTONOMOUS_MOBILITY.INFORMATION_SCHEMA.COLUMNS
           WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position""",
        (schema, name),
    )
    cols = [r[0] for r in cur.fetchall()]
    return cols or None


def load_dataset(conn: SnowflakeConnection, ds: dict, run_id: str, extract,
                 succeeded_run_ids: set[str]) -> tuple[int, int, list[Check]]:
    """Load all frames. Returns (parsed_rows_loaded_to_temp, raw_rows_for_run, checks)."""
    checks: list[Check] = []
    table = ds["raw_table"]
    schema, name = _split(table)
    source_cols = list(extract.columns)
    variant = set(extract.variant_columns)
    ingested_at = datetime.now(timezone.utc).isoformat()

    cur = conn.cursor()
    cur.execute("USE SCHEMA AUTONOMOUS_MOBILITY.RAW")

    # 1. Stage all frames in one temporary table with explicit types, so a
    #    column that is entirely null in one frame cannot be mistyped.
    tmp = f"ZZ_TMP_LOAD_{uuid.uuid4().hex[:12].upper()}"
    tmp_ddl = [f'"{c}" VARCHAR' for c in source_cols]
    tmp_ddl += [f'"{c}" {"NUMBER(38,0)" if c == "_SOURCE_ROW_NUMBER" else "VARCHAR"}'
                for c in METADATA_COLUMNS]
    cur.execute(f'CREATE TEMPORARY TABLE {tmp} ({", ".join(tmp_ddl)})')
    staged = 0
    for i, frame in enumerate(extract.frames):
        if frame.empty:
            continue
        frame = frame.copy()
        missing = [c for c in source_cols if c not in frame.columns]
        if missing:
            raise IngestionError(f"frame {i} missing columns {missing[:5]}")
        frame[source_cols] = frame[source_cols].astype("string")
        frame["_INGEST_RUN_ID"] = run_id
        frame["_INGESTED_AT"] = ingested_at
        frame["_SOURCE_ID"] = ds["source_id"]
        frame["_SOURCE_VINTAGE"] = ds["vintage"]
        frame["_SOURCE_FILE"] = extract.snapshot_name
        frame["_SOURCE_FILE_SHA256"] = extract.sha256
        frame["_SOURCE_ROW_NUMBER"] = frame["_SOURCE_ROW_NUMBER"].astype("int64")
        frame = frame[source_cols + list(METADATA_COLUMNS)]
        ok, _, nrows, _ = write_pandas(
            conn, frame, tmp, database="AUTONOMOUS_MOBILITY", schema="RAW",
            auto_create_table=False, quote_identifiers=True, chunk_size=200_000,
        )
        if not ok:
            raise IngestionError("write_pandas reported failure")
        staged += nrows
        log.info("  staged %s rows (frame %d, total %s)", f"{nrows:,}", i, f"{staged:,}")
    if staged == 0:
        raise IngestionError("no rows to load")

    # 2. Create the RAW table, or check the existing one for schema drift.
    expected = source_cols + list(METADATA_COLUMNS)
    current = existing_columns(conn, table)
    if current is None:
        col_ddl = [f'"{c}" {"VARIANT" if c in variant else "VARCHAR"}' for c in source_cols]
        col_ddl += [f'"{c}" {t}' for c, t in METADATA_DDL.items()]
        comment = (f"RAW landing for {ds['source_id']} {ds['dataset']} | vintage {ds['vintage']} "
                   f"| grain: {ds['grain']} | source-aligned; values as strings")
        cur.execute(f'CREATE TABLE {table} ({", ".join(col_ddl)}) COMMENT = %s', (comment[:1000],))
        checks.append(Check("raw_table_created", "SCHEMA", "PASS", details=table))
    elif current != expected:
        added = [c for c in expected if c not in current]
        removed = [c for c in current if c not in expected]
        raise IngestionError(f"schema drift vs existing {table}: new={added[:10]} missing={removed[:10]}")
    else:
        checks.append(Check("raw_schema_unchanged", "SCHEMA", "PASS",
                            expected=len(expected), actual=len(current)))

    # 3. Remove orphan rows from earlier runs that never reached SUCCEEDED.
    cur.execute(f'SELECT DISTINCT "_INGEST_RUN_ID" FROM {table}')
    orphans = [r[0] for r in cur.fetchall() if r[0] not in succeeded_run_ids]
    if orphans:
        cur.execute(f'DELETE FROM {table} WHERE "_INGEST_RUN_ID" IN ({", ".join(["%s"] * len(orphans))})',
                    orphans)
        checks.append(Check("orphan_rows_removed", "IDEMPOTENCY", "WARN", actual=cur.rowcount,
                            details=f"rows from {len(orphans)} unfinished run(s) removed before load"))

    # 4. Append in one statement.
    select_cols = []
    for c in expected:
        if c in variant:
            select_cols.append(f'PARSE_JSON("{c}")')
        elif c == "_INGESTED_AT":
            select_cols.append(f'"{c}"::TIMESTAMP_TZ')
        else:
            select_cols.append(f'"{c}"')
    cur.execute(f'INSERT INTO {table} ({", ".join(chr(34) + c + chr(34) for c in expected)}) '
                f'SELECT {", ".join(select_cols)} FROM {tmp}')
    cur.execute(f"DROP TABLE IF EXISTS {tmp}")

    # 5. Count what landed for this run.
    cur.execute(f'SELECT COUNT(*) FROM {table} WHERE "_INGEST_RUN_ID" = %s', (run_id,))
    raw_rows = cur.fetchone()[0]
    return staged, raw_rows, checks


def delete_run_rows(conn: SnowflakeConnection, table: str, run_id: str) -> int:
    """Remove a failed run's rows so RAW never keeps unreconciled data."""
    if existing_columns(conn, table) is None:
        return 0
    cur = conn.cursor()
    cur.execute(f'DELETE FROM {table} WHERE "_INGEST_RUN_ID" = %s', (run_id,))
    return cur.rowcount or 0


def frame_from_rows(header: list[str], rows: list[list], row_numbers: list[int]) -> pd.DataFrame:
    """Build a string frame; `row_numbers` are the true source record numbers."""
    df = pd.DataFrame(rows, columns=header, dtype="object")
    df["_SOURCE_ROW_NUMBER"] = row_numbers
    return df
