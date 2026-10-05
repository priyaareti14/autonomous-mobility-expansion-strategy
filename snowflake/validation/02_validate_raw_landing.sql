-- =============================================================================
-- 02_validate_raw_landing.sql
-- Autonomous Mobility Expansion Strategy: Phase 3 RAW landing inspection
--
-- Read-only: creates nothing and changes nothing.
-- The automated equivalent is scripts/validate_raw_landing.py.
--
-- Run as : AM_TRANSFORMER (reads RAW and META through future grants), or AM_ADMIN.
-- =============================================================================

USE ROLE AM_TRANSFORMER;
USE WAREHOUSE AM_EXPANSION_WH;
USE DATABASE AUTONOMOUS_MOBILITY;

-- 1. RAW tables, row counts and column counts.
--    Expect: one table per registered dataset; no ZZ_TMP_LOAD_* leftovers.
SELECT t.table_name,
       t.row_count,
       (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c
         WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS column_count,
       t.comment
FROM INFORMATION_SCHEMA.TABLES t
WHERE t.table_schema = 'RAW'
ORDER BY t.table_name;

-- 2. No project tables outside RAW and META (Phase 3 boundary).
--    Expect: zero rows.
SELECT table_schema, table_name
FROM INFORMATION_SCHEMA.TABLES
WHERE table_schema IN ('STAGING', 'INTERMEDIATE', 'CORE', 'ANALYTICS');

-- 3. Ingestion attempts by status.
SELECT status, COUNT(*) AS runs
FROM META.INGESTION_RUNS
GROUP BY status
ORDER BY status;

-- 4. Latest attempt and latest SUCCEEDED run per dataset.
SELECT dataset_id,
       source_id,
       source_vintage,
       MAX_BY(status, started_at)                                   AS latest_status,
       MAX(IFF(status = 'SUCCEEDED', completed_at, NULL))           AS last_success_at,
       MAX_BY(IFF(status = 'SUCCEEDED', raw_row_count, NULL),
              IFF(status = 'SUCCEEDED', completed_at, NULL))        AS raw_rows_loaded,
       MAX_BY(IFF(status = 'SUCCEEDED', source_sha256, NULL),
              IFF(status = 'SUCCEEDED', completed_at, NULL))        AS loaded_sha256,
       COUNT(*)                                                     AS attempts
FROM META.INGESTION_RUNS
GROUP BY dataset_id, source_id, source_vintage
ORDER BY source_id, dataset_id;

-- 5. Reconciliation of every SUCCEEDED run.
--    Expect: recon_ok = TRUE everywhere (source - rejected = parsed = RAW).
SELECT dataset_id, snowflake_table, source_row_count, rejected_row_count,
       parsed_row_count, raw_row_count,
       (source_row_count - rejected_row_count = parsed_row_count
        AND parsed_row_count = raw_row_count) AS recon_ok
FROM META.INGESTION_RUNS
WHERE status = 'SUCCEEDED'
ORDER BY source_id, dataset_id;

-- 6. Unexpected duplicate loads: more than one SUCCEEDED run for the same
--    dataset and vintage. Expect: zero rows (reruns are SKIPPED_IDENTICAL).
SELECT dataset_id, source_vintage, COUNT(*) AS succeeded_runs
FROM META.INGESTION_RUNS
WHERE status = 'SUCCEEDED'
GROUP BY dataset_id, source_vintage
HAVING COUNT(*) > 1;

-- 7. Checksum drift or blocked attempts (review list).
SELECT started_at, dataset_id, status, error_class, error_message_sanitized
FROM META.INGESTION_RUNS
WHERE status IN ('BLOCKED', 'FAILED')
ORDER BY started_at;

-- 8. Non-PASS checks on the latest SUCCEEDED run of each dataset
--    (documented warnings: trimming, projections, source anomalies).
WITH latest AS (
    SELECT dataset_id, MAX_BY(run_id, completed_at) AS run_id
    FROM META.INGESTION_RUNS WHERE status = 'SUCCEEDED' GROUP BY dataset_id
)
SELECT k.dataset_id, k.check_name, k.status, k.actual_value, LEFT(k.details, 300) AS details
FROM META.INGESTION_CHECKS k JOIN latest l ON k.run_id = l.run_id
WHERE k.status <> 'PASS'
ORDER BY k.dataset_id, k.check_name;

-- 9. Rejected rows, with reasons.
SELECT dataset_id, reject_reason, COUNT(*) AS rows_rejected,
       ANY_VALUE(LEFT(record_text, 200)) AS example
FROM META.INGESTION_REJECTED_ROWS
WHERE run_id IN (SELECT run_id FROM META.INGESTION_RUNS WHERE status = 'SUCCEEDED')
GROUP BY dataset_id, reject_reason
ORDER BY dataset_id;

-- 10. Spot check: every RAW row carries its lineage metadata
--     (example table; repeat for others as needed). Expect: zero.
SELECT COUNT(*) AS rows_missing_lineage
FROM RAW.CENSUS_PEP_CBSA_EST2025
WHERE "_INGEST_RUN_ID" IS NULL OR "_SOURCE_FILE_SHA256" IS NULL OR "_SOURCE_ROW_NUMBER" IS NULL;
