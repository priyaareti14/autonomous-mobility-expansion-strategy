-- =============================================================================
-- 05_ingestion_audit.sql
-- Autonomous Mobility Expansion Strategy: Phase 3 ingestion audit tables
--
-- Creates the three persistent audit tables in META. They hold metadata about
-- ingestion attempts only. They never hold source data, credentials or
-- secret-bearing URLs.
--
-- Run as : AM_INGESTOR. The role has USAGE + CREATE TABLE on META (script 02),
--          so it owns these tables and can insert into and update them.
--          AM_TRANSFORMER can read them through the META future SELECT grants
--          from script 02. No admin role is needed.
-- How    : executed by `python scripts/run_ingestion.py --setup-audit`, or run
--          manually in Snowsight after USE ROLE AM_INGESTOR.
-- Rerun  : safe. CREATE TABLE IF NOT EXISTS.
-- Note   : PRIMARY KEY constraints are informational (Snowflake does not
--          enforce them). Uniqueness is checked by the validation scripts.
-- =============================================================================

USE ROLE AM_INGESTOR;
USE WAREHOUSE AM_EXPANSION_WH;
USE SCHEMA AUTONOMOUS_MOBILITY.META;

-- -----------------------------------------------------------------------------
-- INGESTION_RUNS
-- Grain: one row per ingestion attempt for one dataset (source_id + dataset_id).
-- Lifecycle: inserted as STARTED, then updated to exactly one terminal status:
--   SUCCEEDED          rows loaded and reconciled
--   FAILED             error during acquisition, validation or load
--   BLOCKED            source refused automated access, or a pinned-vintage
--                      checksum changed (needs review)
--   SKIPPED_IDENTICAL  same source_id + dataset_id + vintage + SHA-256 already
--                      loaded successfully; nothing written to RAW
--   SUPERSEDED         a formerly SUCCEEDED run retired by an explicit, verified
--                      re-baseline (run_ingestion.py --rebaseline). The new
--                      snapshot's content was proven value-for-value identical
--                      before reloading, and this run's rows were deleted only
--                      after the replacement reconciled. error_class =
--                      'Rebaselined'; error_message_sanitized names the
--                      replacing run and the reason.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS INGESTION_RUNS (
    run_id                  VARCHAR       NOT NULL,
    source_id               VARCHAR       NOT NULL,   -- catalog ID, e.g. S-01
    dataset_id              VARCHAR       NOT NULL,   -- registry dataset key
    dataset_name            VARCHAR,
    source_vintage          VARCHAR       NOT NULL,
    source_url_sanitized    VARCHAR,                  -- never contains API keys
    access_method           VARCHAR,
    started_at              TIMESTAMP_TZ  NOT NULL,
    completed_at            TIMESTAMP_TZ,
    status                  VARCHAR       NOT NULL,
    local_snapshot_name     VARCHAR,                  -- filename only, no local path
    source_sha256           VARCHAR,
    source_bytes            NUMBER(38,0),
    source_row_count        NUMBER(38,0),             -- records read from the source
    parsed_row_count        NUMBER(38,0),             -- records successfully parsed
    rejected_row_count      NUMBER(38,0),             -- parsed records not loaded (see INGESTION_REJECTED_ROWS)
    raw_row_count           NUMBER(38,0),             -- rows counted in RAW after load
    snowflake_table         VARCHAR,
    pipeline_git_commit     VARCHAR,
    error_class             VARCHAR,
    error_message_sanitized VARCHAR,
    CONSTRAINT pk_ingestion_runs PRIMARY KEY (run_id)
)
COMMENT = 'Phase 3 ingestion audit: one row per dataset ingestion attempt';

-- -----------------------------------------------------------------------------
-- INGESTION_CHECKS
-- Grain: one row per validation or reconciliation check per ingestion run.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS INGESTION_CHECKS (
    run_id          VARCHAR       NOT NULL,
    source_id       VARCHAR       NOT NULL,
    dataset_id      VARCHAR       NOT NULL,
    check_name      VARCHAR       NOT NULL,
    check_type      VARCHAR       NOT NULL,   -- ACQUISITION / SCHEMA / INTEGRITY / RECONCILIATION / IDEMPOTENCY / SOURCE_SPECIFIC
    expected_value  VARCHAR,
    actual_value    VARCHAR,
    status          VARCHAR       NOT NULL,   -- PASS / WARN / FAIL
    details         VARCHAR,
    checked_at      TIMESTAMP_TZ  NOT NULL
)
COMMENT = 'Phase 3 ingestion audit: one row per check per ingestion run';

-- -----------------------------------------------------------------------------
-- INGESTION_REJECTED_ROWS
-- Grain: one row per source record parsed but not loaded to RAW.
-- Rows are never discarded silently: each rejection is kept with its reason.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS INGESTION_REJECTED_ROWS (
    run_id             VARCHAR       NOT NULL,
    source_id          VARCHAR       NOT NULL,
    dataset_id         VARCHAR       NOT NULL,
    source_row_number  NUMBER(38,0),
    reject_reason      VARCHAR       NOT NULL,
    record_text        VARCHAR,                -- original record content, for review
    rejected_at        TIMESTAMP_TZ  NOT NULL
)
COMMENT = 'Phase 3 ingestion audit: source records not loaded, with reason';
