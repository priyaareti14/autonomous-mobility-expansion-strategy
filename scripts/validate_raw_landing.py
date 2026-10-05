"""Phase 3 validation: verify every registered dataset's RAW landing against META.

Runs as AM_TRANSFORMER (the downstream read-only consumer of RAW and META),
which also proves that dbt's role can read what ingestion landed.

Per dataset it reports:
  * latest ingestion status and the latest SUCCEEDED run
  * RAW table row count and number of distinct load runs (expected 1)
  * reconciliation: source rows - rejected = parsed = RAW rows for that run
  * checksum: META SHA-256 vs the local snapshot (and the Phase 1 pin where set)
  * duplicate natural keys in RAW
  * required fields present, and key fields non-null

Verdict per dataset: PASS / WARN / FAIL. Exits non-zero if any FAIL.
No secrets or account identifiers are printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.common import RAW_CACHE, sha256_bytes, snowflake_column  # noqa: E402
from src.ingestion.source_registry import load_registry  # noqa: E402
from src.utils.snowflake_connection import get_connection  # noqa: E402

DB = "AUTONOMOUS_MOBILITY"
# Sources that cannot be acquired automatically; BLOCKED is the expected,
# documented state rather than a defect.
EXPECTED_BLOCKED = {"bls_oews_may2025_msa"}


def q(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


def validate(cur, ds: dict) -> dict:
    r = {"dataset": ds["dataset_id"], "source": ds["source_id"], "table": ds["raw_table"],
         "vintage": ds["vintage"], "issues": [], "warnings": []}
    runs = q(cur, f"""SELECT run_id, status, source_sha256, source_row_count, parsed_row_count,
                             rejected_row_count, raw_row_count, error_class
                      FROM {DB}.META.INGESTION_RUNS WHERE dataset_id = %s
                      ORDER BY started_at DESC""", (ds["dataset_id"],))
    if not runs:
        r["verdict"], r["latest"] = "FAIL", "NEVER RUN"
        r["issues"].append("no ingestion attempt recorded")
        return r
    r["latest"] = runs[0][1]
    ok_runs = [x for x in runs if x[1] == "SUCCEEDED"]
    if not ok_runs:
        if ds["dataset_id"] in EXPECTED_BLOCKED and runs[0][1] == "BLOCKED":
            r["verdict"] = "WARN"
            r["warnings"].append(f"BLOCKED by source ({runs[0][7]}); documented, no RAW table")
        else:
            r["verdict"] = "FAIL"
            r["issues"].append(f"no SUCCEEDED run (latest {runs[0][1]})")
        return r
    run_id, _, sha, src_rows, parsed, rejected, raw_meta, _ = ok_runs[0]
    r.update(source_rows=src_rows, rejected=rejected, raw_meta=raw_meta)

    # RAW table: total rows, rows per run.
    schema, name = ds["raw_table"].split(".")
    cols = [c[0] for c in q(cur, f"""SELECT column_name FROM {DB}.INFORMATION_SCHEMA.COLUMNS
                                      WHERE table_schema=%s AND table_name=%s""", (schema, name))]
    if not cols:
        r["verdict"] = "FAIL"
        r["issues"].append("RAW table missing")
        return r
    r["columns"] = len(cols)
    by_run = q(cur, f'SELECT "_INGEST_RUN_ID", COUNT(*) FROM {DB}.{ds["raw_table"]} GROUP BY 1')
    r["raw_rows"] = sum(n for _, n in by_run)
    r["load_runs"] = len(by_run)
    if len(by_run) != 1 or by_run[0][0] != run_id:
        r["issues"].append(f"RAW holds {len(by_run)} load run(s); expected only {run_id[:8]}")
    if not (src_rows - rejected == parsed == raw_meta == r["raw_rows"]):
        r["issues"].append(f"reconciliation: source {src_rows} - rejected {rejected} vs parsed {parsed}, "
                           f"META RAW {raw_meta}, actual RAW {r['raw_rows']}")
    r["recon"] = "OK" if not any(i.startswith("reconciliation") for i in r["issues"]) else "MISMATCH"

    # Checksum vs local snapshot (and Phase 1 pin).
    snap = RAW_CACHE / ds["source_id"] / ds["snapshot_name"]
    if snap.exists():
        local = sha256_bytes(snap.read_bytes())
        r["checksum"] = "MATCH" if local == sha else "DIFFERS"
        if local != sha:
            r["issues"].append("local snapshot SHA-256 differs from the loaded snapshot")
    else:
        r["checksum"] = "NO LOCAL COPY"
        r["warnings"].append("local snapshot not present (cache is optional)")
    if ds.get("expected_sha256") and ds["expected_sha256"] != sha:
        r["issues"].append("loaded SHA-256 differs from the Phase 1 pinned checksum")

    # Duplicate natural keys and required fields.
    key = [snowflake_column(k) for k in ds.get("natural_key", [])]
    if key:
        k = ", ".join(f'"{c}"' for c in key)
        dups = q(cur, f'SELECT COUNT(*) FROM (SELECT {k} FROM {DB}.{ds["raw_table"]} '
                      f'GROUP BY {k} HAVING COUNT(*) > 1)')[0][0]
        r["duplicates"] = dups
        if dups:
            r["issues"].append(f"{dups} duplicate natural key(s)")
    else:
        r["duplicates"] = "n/a"
    required = [snowflake_column(c) for c in ds["required_columns"]]
    if ds["access_method"] == "noaa_tar_variant":
        required = ["STATION", "RECORD"]          # other required fields live inside RECORD
    missing = [c for c in required if c not in cols]
    not_null = [snowflake_column(c) for c in ds.get("key_not_null", ds.get("natural_key", []))]
    nulls = 0
    if not_null:
        cond = " OR ".join(f'"{c}" IS NULL' for c in not_null)
        nulls = q(cur, f'SELECT COUNT(*) FROM {DB}.{ds["raw_table"]} WHERE {cond}')[0][0]
    r["required"] = "OK" if not missing and not nulls else f"missing={missing} null_keys={nulls}"
    if missing or nulls:
        r["issues"].append(f"required fields: {r['required']}")

    warn_checks = q(cur, f"""SELECT COUNT(*) FROM {DB}.META.INGESTION_CHECKS
                             WHERE run_id = %s AND status = 'WARN'""", (run_id,))[0][0]
    if warn_checks:
        r["warnings"].append(f"{warn_checks} WARN check(s) recorded at load")
    if rejected:
        r["warnings"].append(f"{rejected} rejected row(s), recorded with reasons")
    r["verdict"] = "FAIL" if r["issues"] else ("WARN" if r["warnings"] else "PASS")
    return r


def main() -> int:
    registry = load_registry()
    with get_connection(role="AM_TRANSFORMER") as conn:
        cur = conn.cursor()
        cur.execute("USE SECONDARY ROLES NONE")
        results = [validate(cur, ds) for ds in registry]

    print(f"{'VERDICT':<7} {'SRC':<5} {'DATASET':<46} {'LATEST':<18} {'SOURCE':>9} {'REJ':>4} "
          f"{'RAW':>9} {'RUNS':>4} {'RECON':<8} {'CHECKSUM':<13} {'DUPS':>4} REQUIRED")
    for r in results:
        print(f"{r['verdict']:<7} {r['source']:<5} {r['dataset']:<46} {r['latest']:<18} "
              f"{str(r.get('source_rows', '-')):>9} {str(r.get('rejected', '-')):>4} "
              f"{str(r.get('raw_rows', '-')):>9} {str(r.get('load_runs', '-')):>4} "
              f"{r.get('recon', '-'):<8} {r.get('checksum', '-'):<13} {str(r.get('duplicates', '-')):>4} "
              f"{r.get('required', '-')}")
        for i in r["issues"]:
            print(f"        ISSUE: {i}")
        for w in r["warnings"]:
            print(f"        note : {w}")
    counts = {v: sum(r["verdict"] == v for r in results) for v in ("PASS", "WARN", "FAIL")}
    print(f"\nOverall: {counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL "
          f"across {len(results)} datasets")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
