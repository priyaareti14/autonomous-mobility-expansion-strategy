"""Phase 3 ingestion runner: public source -> snapshot -> validation -> Snowflake RAW -> META audit.

Usage (repository root, .venv active):
    python scripts/run_ingestion.py --setup-audit           # create META audit tables (idempotent)
    python scripts/run_ingestion.py --list                  # show registered datasets
    python scripts/run_ingestion.py --datasets S-01 census_acs5_2024_cbsa_tables_b01003
    python scripts/run_ingestion.py --all
    python scripts/run_ingestion.py --datasets S-01 --simulate-drift   # drift-detection test

Selection accepts dataset_ids, source IDs (S-xx) or a dataset_id prefix.
Runs as AM_INGESTOR with secondary roles disabled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.audit import Audit  # noqa: E402
from src.ingestion.common import (BlockedError, Check, configure_logging,  # noqa: E402
                                  finalize_snapshots, git_commit, log, sanitize)
from src.ingestion.loaders import delete_run_rows, load_dataset  # noqa: E402
from src.ingestion.source_registry import load_registry, not_ingested  # noqa: E402
from src.ingestion.sources import bls, census, epa, faa, noaa  # noqa: E402
from src.utils.snowflake_connection import get_connection  # noqa: E402

ROLE = "AM_INGESTOR"
AUDIT_SQL = Path(__file__).resolve().parents[1] / "snowflake" / "setup" / "05_ingestion_audit.sql"

EXTRACTORS = {
    "census_pep_cbsa_v2025": census.pep,
    "census_cbsa_delineation_2023": census.delineation,
    "census_acs5_2024_cbsa_s0801_subset": census.acs_cbsa,
    "census_acs5_2024_tract_b01003": census.acs_tract,
    "census_cbp_2023_msa": census.cbp,
    "bls_oews_may2025_msa": bls.oews,
    "noaa_normals_1991_2020_annualseasonal": noaa.annual_seasonal,
    "noaa_normals_1991_2020_hourly_wind": noaa.hourly_wind,
    "faa_enplanements_cy2025_commercial_service": faa.enplanements,
    "faa_nasr_apt_base_20260903": faa.nasr_apt_base,
    "epa_sld_v3_block_group": epa.sld,
}


def extractor_for(ds: dict):
    if ds["access_method"] == "census_api_group":
        return census.acs_cbsa
    if ds["dataset_id"].startswith("census_gazetteer_2024_"):
        return census.gazetteer
    return EXTRACTORS[ds["dataset_id"]]


def setup_audit(conn) -> None:
    sql = AUDIT_SQL.read_text(encoding="utf-8")
    sql = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    for stmt in (s.strip() for s in sql.split(";")):
        if stmt:
            conn.cursor().execute(stmt)
    log.info("META audit tables ready (%s)", AUDIT_SQL.name)


def select(registry: list[dict], wanted: list[str]) -> list[dict]:
    chosen = [d for d in registry
              if any(w == d["dataset_id"] or w == d["source_id"] or d["dataset_id"].startswith(w)
                     for w in wanted)]
    unknown = [w for w in wanted if not any(
        w == d["dataset_id"] or w == d["source_id"] or d["dataset_id"].startswith(w) for d in registry)]
    if unknown:
        raise SystemExit(f"unknown dataset selection: {unknown}")
    return chosen


def ingest(conn, audit: Audit, ds: dict, simulate_drift: bool, rebaseline_reason: str | None = None) -> dict:
    """Run one dataset, then write its snapshot according to the outcome."""
    result = {"status": "FAILED"}
    try:
        result = _ingest(conn, audit, ds, simulate_drift, rebaseline_reason)
        return result
    finally:
        written = finalize_snapshots(result["status"])
        if written and result["status"] not in ("SUCCEEDED", "SKIPPED_IDENTICAL"):
            log.warning("  snapshot kept for review, loaded snapshot untouched: %s", ", ".join(written))


def content_fingerprint(ex) -> str:
    """Order-independent SHA-256 over every accepted record's values."""
    rejected = {r.row_number for r in ex.rejects}
    lines = sorted(json.dumps(values, ensure_ascii=False)
                   for row_no, values, _ in ex.record_factory()
                   if values is not None and row_no not in rejected)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest().upper()


def raw_fingerprint(conn, ds: dict, columns: list[str], run_id: str) -> str:
    """The same fingerprint over the RAW rows a prior run loaded."""
    cur = conn.cursor()
    cols = ", ".join(f'"{c}"' for c in columns)
    cur.execute(f'SELECT {cols} FROM {ds["raw_table"]} WHERE "_INGEST_RUN_ID" = %s', (run_id,))
    lines = sorted(json.dumps(list(r), ensure_ascii=False) for r in cur.fetchall())
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest().upper()


def _ingest(conn, audit: Audit, ds: dict, simulate_drift: bool, rebaseline_reason: str | None = None) -> dict:
    started = time.time()
    run_id = audit.start_run(ds)
    log.info("[%s] %s -> %s (run %s)", ds["source_id"], ds["dataset_id"], ds["raw_table"], run_id[:8])
    result = {"dataset_id": ds["dataset_id"], "source_id": ds["source_id"], "table": ds["raw_table"]}
    ex = None
    try:
        ex = extractor_for(ds)(ds)
        checks: list[Check] = list(ex.checks)
        checks.append(Check("snapshot_sha256_recorded", "IDEMPOTENCY", "PASS", actual=ex.sha256,
                            details=f"{ex.snapshot_name}, {ex.snapshot_bytes:,} bytes"))
        if simulate_drift:
            ex.sha256 = hashlib.sha256((ex.sha256 + "|simulated-drift").encode()).hexdigest().upper()
            checks.append(Check("simulated_drift_test", "IDEMPOTENCY", "WARN",
                                details="TEST ONLY: checksum deliberately altered to exercise drift detection"))

        prior = audit.prior_success(ds)
        common = dict(local_snapshot_name=ex.snapshot_name, source_sha256=ex.sha256,
                      source_bytes=ex.snapshot_bytes, source_row_count=ex.source_row_count,
                      source_url_sanitized=ex.url_sanitized)
        if prior and prior.sha256 == ex.sha256:
            checks.append(Check("identical_snapshot_already_loaded", "IDEMPOTENCY", "PASS",
                                expected=prior.sha256, actual=ex.sha256,
                                details=f"prior run {prior.run_id}; RAW left unchanged"))
            audit.add_checks(run_id, ds, checks)
            audit.finish_run(run_id, "SKIPPED_IDENTICAL", **common, raw_row_count=0)
            return {**result, "status": "SKIPPED_IDENTICAL", "secs": time.time() - started}
        supersede_prior = None
        if prior and prior.sha256 != ex.sha256 and rebaseline_reason:
            new_fp = content_fingerprint(ex)
            old_fp = raw_fingerprint(conn, ds, ex.columns, prior.run_id)
            same = new_fp == old_fp
            checks.append(Check("rebaseline_content_equivalence", "IDEMPOTENCY", "PASS" if same else "FAIL",
                                expected=f"loaded content {old_fp[:16]}", actual=f"new content {new_fp[:16]}",
                                details=f"order-independent fingerprint of all loaded values vs run "
                                        f"{prior.run_id}; reason: {rebaseline_reason}"))
            if same:
                supersede_prior = prior.run_id
                log.info("  re-baseline: content identical to run %s; loading canonical snapshot", prior.run_id[:8])
        if prior and prior.sha256 != ex.sha256 and not supersede_prior:
            checks.append(Check("pinned_vintage_checksum_drift", "IDEMPOTENCY", "FAIL",
                                expected=prior.sha256, actual=ex.sha256,
                                details=f"same source/dataset/vintage as run {prior.run_id} but different "
                                        f"content; RAW not modified; review required"))
            audit.add_checks(run_id, ds, checks)
            audit.finish_run(run_id, "BLOCKED", **common, error_class="ChecksumDrift",
                             error_message_sanitized="pinned snapshot changed since last successful load")
            return {**result, "status": "BLOCKED", "reason": "checksum drift", "secs": time.time() - started}

        failed = [c for c in checks if c.status == "FAIL"]
        if failed:
            audit.add_checks(run_id, ds, checks)
            audit.add_rejects(run_id, ds, ex.rejects)
            audit.finish_run(run_id, "FAILED", **common, error_class="ValidationFailed",
                             error_message_sanitized="; ".join(c.name for c in failed))
            return {**result, "status": "FAILED", "reason": "validation", "secs": time.time() - started}

        parsed = ex.source_row_count - len(ex.rejects)
        staged, raw_rows, load_checks = load_dataset(conn, ds, run_id, ex, audit.succeeded_run_ids(ds["raw_table"]))
        checks += load_checks
        recon_ok = staged == parsed and raw_rows == staged
        checks.append(Check("source_to_raw_reconciliation", "RECONCILIATION", "PASS" if recon_ok else "FAIL",
                            expected=f"source {ex.source_row_count} - rejected {len(ex.rejects)} = {parsed}",
                            actual=f"staged {staged}, RAW {raw_rows}"))
        audit.add_checks(run_id, ds, checks)
        audit.add_rejects(run_id, ds, ex.rejects)
        if not recon_ok:
            removed = delete_run_rows(conn, ds["raw_table"], run_id)
            audit.finish_run(run_id, "FAILED", **common, parsed_row_count=parsed,
                             rejected_row_count=len(ex.rejects), raw_row_count=raw_rows,
                             error_class="ReconciliationFailed",
                             error_message_sanitized=f"counts differ; {removed} rows of this run removed")
            return {**result, "status": "FAILED", "reason": "reconciliation", "secs": time.time() - started}
        if supersede_prior:
            # Only after the new load reconciled: retire the prior run and remove its rows.
            audit.supersede(supersede_prior, run_id, rebaseline_reason)
            removed = delete_run_rows(conn, ds["raw_table"], supersede_prior)
            audit.add_checks(run_id, ds, [Check(
                "rebaseline_prior_rows_removed", "IDEMPOTENCY", "PASS", actual=removed,
                details=f"run {supersede_prior} marked SUPERSEDED; its rows deleted after this run reconciled")])
        audit.finish_run(run_id, "SUCCEEDED", **common, parsed_row_count=parsed,
                         rejected_row_count=len(ex.rejects), raw_row_count=raw_rows)
        warns = sum(c.status == "WARN" for c in checks)
        log.info("  SUCCEEDED: %s rows, %d rejected, %d warning(s), %.0fs",
                 f"{raw_rows:,}", len(ex.rejects), warns, time.time() - started)
        return {**result, "status": "SUCCEEDED", "rows": raw_rows, "rejected": len(ex.rejects),
                "secs": time.time() - started}

    except Exception as exc:  # noqa: BLE001 - every failure is audited, then the next source runs
        status = "BLOCKED" if isinstance(exc, BlockedError) else "FAILED"
        message = sanitize(f"{exc}")
        log.error("  %s: %s: %s", status, type(exc).__name__, message)
        log.debug(sanitize(traceback.format_exc()))
        try:
            delete_run_rows(conn, ds["raw_table"], run_id)
            if ex is not None:
                audit.add_checks(run_id, ds, ex.checks)
                audit.add_rejects(run_id, ds, ex.rejects)
            audit.finish_run(run_id, status, error_class=type(exc).__name__,
                             error_message_sanitized=message,
                             **({"local_snapshot_name": ex.snapshot_name, "source_sha256": ex.sha256,
                                 "source_bytes": ex.snapshot_bytes} if ex else {}))
        except Exception as audit_exc:  # noqa: BLE001
            log.error("  could not record audit outcome: %s", sanitize(audit_exc))
        return {**result, "status": status, "reason": message[:160], "secs": time.time() - started}


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 3 ingestion runner")
    p.add_argument("--setup-audit", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--all", action="store_true")
    p.add_argument("--datasets", nargs="*", default=[])
    p.add_argument("--simulate-drift", action="store_true",
                   help="TEST ONLY: alter the computed checksum to exercise drift detection")
    p.add_argument("--rebaseline", metavar="REASON",
                   help="On checksum drift, reload ONLY if the new content is value-for-value identical "
                        "to what is loaded (order-independent); the prior run becomes SUPERSEDED")
    args = p.parse_args()
    if args.rebaseline and (args.all or not args.datasets):
        p.error("--rebaseline requires an explicit --datasets selection")
    configure_logging()

    registry = load_registry()
    if args.list:
        for d in registry:
            print(f"{d['source_id']:<5} {d['dataset_id']:<48} {d['raw_table']}")
        for n in not_ingested():
            print(f"not ingested: {n['source_id']}: {n['reason']}")
        return 0

    chosen = registry if args.all else select(registry, args.datasets)
    if not chosen and not args.setup_audit:
        p.error("nothing selected: use --all, --datasets or --setup-audit")

    with get_connection(role=ROLE) as conn:
        cur = conn.cursor()
        cur.execute("USE SECONDARY ROLES NONE")
        cur.execute("SELECT CURRENT_ROLE()")
        role = cur.fetchone()[0]
        if role != ROLE:
            raise SystemExit(f"expected role {ROLE}, got {role}")
        if args.setup_audit:
            setup_audit(conn)
        audit = Audit(conn, git_commit())
        results = [ingest(conn, audit, ds, args.simulate_drift, args.rebaseline) for ds in chosen]

    if results:
        print("\nSummary")
        for r in results:
            extra = f"{r.get('rows', 0):>10,} rows" if r["status"] == "SUCCEEDED" else r.get("reason", "")
            print(f"  {r['status']:<18} {r['source_id']:<5} {r['dataset_id']:<48} {extra}")
    bad = [r for r in results if r["status"] in ("FAILED",)]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
