"""META audit trail: INGESTION_RUNS, INGESTION_CHECKS, INGESTION_REJECTED_ROWS."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from snowflake.connector import SnowflakeConnection

from .common import Check, Reject, sanitize

META = "AUTONOMOUS_MOBILITY.META"
MAX_MESSAGE = 2000


@dataclass
class PriorLoad:
    run_id: str
    sha256: str
    raw_table: str
    raw_row_count: int


class Audit:
    def __init__(self, conn: SnowflakeConnection, git_commit: str):
        self.conn = conn
        self.git_commit = git_commit

    # -- runs ----------------------------------------------------------------
    def start_run(self, ds: dict) -> str:
        run_id = str(uuid.uuid4())
        self._exec(
            f"""INSERT INTO {META}.INGESTION_RUNS
                (run_id, source_id, dataset_id, dataset_name, source_vintage,
                 source_url_sanitized, access_method, started_at, status,
                 snowflake_table, pipeline_git_commit)
                SELECT %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), 'STARTED', %s, %s""",
            (run_id, ds["source_id"], ds["dataset_id"], ds["dataset"], ds["vintage"],
             sanitize(ds.get("url") or ds.get("endpoint") or ""), ds["access_method"],
             ds["raw_table"], self.git_commit),
        )
        return run_id

    def finish_run(self, run_id: str, status: str, **fields) -> None:
        allowed = {
            "local_snapshot_name", "source_sha256", "source_bytes", "source_row_count",
            "parsed_row_count", "rejected_row_count", "raw_row_count",
            "error_class", "error_message_sanitized", "source_url_sanitized",
        }
        sets, values = ["status = %s", "completed_at = CURRENT_TIMESTAMP()"], [status]
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"unknown audit field {key}")
            if key in ("error_message_sanitized", "source_url_sanitized") and value is not None:
                value = sanitize(value)[:MAX_MESSAGE]
            sets.append(f"{key} = %s")
            values.append(value)
        values.append(run_id)
        self._exec(f"UPDATE {META}.INGESTION_RUNS SET {', '.join(sets)} WHERE run_id = %s", values)

    def supersede(self, prior_run_id: str, new_run_id: str, reason: str) -> None:
        """Retire a SUCCEEDED run after a verified re-baseline (its rows are deleted by the caller)."""
        self._exec(
            f"""UPDATE {META}.INGESTION_RUNS
                SET status = 'SUPERSEDED', error_class = 'Rebaselined',
                    error_message_sanitized = %s
                WHERE run_id = %s AND status = 'SUCCEEDED'""",
            (sanitize(f"superseded by run {new_run_id}: {reason}")[:MAX_MESSAGE], prior_run_id),
        )

    def prior_success(self, ds: dict) -> PriorLoad | None:
        """Most recent SUCCEEDED load for the same source, dataset and vintage."""
        cur = self.conn.cursor()
        cur.execute(
            f"""SELECT run_id, source_sha256, snowflake_table, raw_row_count
                FROM {META}.INGESTION_RUNS
                WHERE source_id = %s AND dataset_id = %s AND source_vintage = %s
                  AND status = 'SUCCEEDED'
                ORDER BY completed_at DESC LIMIT 1""",
            (ds["source_id"], ds["dataset_id"], ds["vintage"]),
        )
        row = cur.fetchone()
        return PriorLoad(*row) if row else None

    def succeeded_run_ids(self, raw_table: str) -> set[str]:
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT run_id FROM {META}.INGESTION_RUNS WHERE snowflake_table = %s AND status = 'SUCCEEDED'",
            (raw_table,),
        )
        return {r[0] for r in cur.fetchall()}

    # -- checks and rejects -----------------------------------------------------
    def add_checks(self, run_id: str, ds: dict, checks: list[Check]) -> None:
        if not checks:
            return
        rows = [
            (run_id, ds["source_id"], ds["dataset_id"], c.name, c.check_type,
             None if c.expected is None else sanitize(c.expected)[:MAX_MESSAGE],
             None if c.actual is None else sanitize(c.actual)[:MAX_MESSAGE],
             c.status, sanitize(c.details)[:MAX_MESSAGE])
            for c in checks
        ]
        self.conn.cursor().executemany(
            f"""INSERT INTO {META}.INGESTION_CHECKS
                (run_id, source_id, dataset_id, check_name, check_type, expected_value,
                 actual_value, status, details, checked_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())""",
            rows,
        )

    def add_rejects(self, run_id: str, ds: dict, rejects: list[Reject]) -> None:
        if not rejects:
            return
        rows = [(run_id, ds["source_id"], ds["dataset_id"], r.row_number, r.reason,
                 sanitize(r.record_text)[:MAX_MESSAGE]) for r in rejects]
        self.conn.cursor().executemany(
            f"""INSERT INTO {META}.INGESTION_REJECTED_ROWS
                (run_id, source_id, dataset_id, source_row_number, reject_reason,
                 record_text, rejected_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())""",
            rows,
        )

    def _exec(self, sql: str, params) -> None:
        self.conn.cursor().execute(sql, params)
