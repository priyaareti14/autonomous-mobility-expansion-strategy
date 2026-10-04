-- =============================================================================
-- 01_foundation.sql
-- Autonomous Mobility Expansion Strategy: Snowflake warehouse foundation
--
-- Creates the compute warehouse, the project database and its six layered
-- schemas. Creates no tables and loads no data. Data arrives in Phase 3.
--
-- Run as : SYSADMIN (holds CREATE WAREHOUSE / CREATE DATABASE by default)
-- Order  : run first, before 02_roles_and_grants.sql
-- Rerun  : safe. Every statement uses IF NOT EXISTS, so existing objects are
--          left untouched. A rerun does not reapply changed settings; to
--          change a warehouse setting later, use ALTER WAREHOUSE.
-- =============================================================================

USE ROLE SYSADMIN;

-- -----------------------------------------------------------------------------
-- Warehouse
--   XSMALL       : smallest size; the datasets are small (tens of MB, 35 markets).
--   AUTO_SUSPEND : 60 s. Billing is per second with a 60 s minimum per resume,
--                  so suspending sooner saves nothing.
--   AUTO_RESUME  : queries wake the warehouse, so nobody has to start it by hand.
--   INITIALLY_SUSPENDED : creating the warehouse consumes no credits.
--   STATEMENT_TIMEOUT_IN_SECONDS : 1800 s cap on runaway queries
--                  (account default is 172800 s = 2 days).
--   GENERATION is left at the Snowflake default (Gen2 where available).
-- -----------------------------------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS AM_EXPANSION_WH WITH
    WAREHOUSE_SIZE               = 'XSMALL'
    AUTO_SUSPEND                 = 60
    AUTO_RESUME                  = TRUE
    INITIALLY_SUSPENDED          = TRUE
    STATEMENT_TIMEOUT_IN_SECONDS = 1800
    COMMENT = 'Autonomous Mobility Expansion portfolio project: development compute';

-- -----------------------------------------------------------------------------
-- Database
--   Default Time Travel retention (1 day) is kept.
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS AUTONOMOUS_MOBILITY
    COMMENT = 'Autonomous Mobility Expansion portfolio project (independent analysis; not affiliated with any operator)';

USE DATABASE AUTONOMOUS_MOBILITY;

-- -----------------------------------------------------------------------------
-- Schemas
--   WITH MANAGED ACCESS: only the schema owner (AM_ADMIN after script 02) or a
--   role with MANAGE GRANTS can grant privileges on objects in the schema.
--   Object creators (ingestion, dbt) therefore cannot hand out ad-hoc access;
--   all access goes through the future grants defined centrally in script 02.
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS RAW WITH MANAGED ACCESS
    COMMENT = 'Source-aligned landing layer, loaded by Python ingestion (Phase 3)';

CREATE SCHEMA IF NOT EXISTS STAGING WITH MANAGED ACCESS
    COMMENT = 'dbt staging models: typed, renamed, standardized (Phase 4)';

CREATE SCHEMA IF NOT EXISTS INTERMEDIATE WITH MANAGED ACCESS
    COMMENT = 'dbt intermediate models: reusable joins and aggregations (Phase 4)';

CREATE SCHEMA IF NOT EXISTS CORE WITH MANAGED ACCESS
    COMMENT = 'Dimensional layer: dimensions and subject-area facts with documented grain';

CREATE SCHEMA IF NOT EXISTS ANALYTICS WITH MANAGED ACCESS
    COMMENT = 'Decision-ready marts and persisted Python analytical outputs';

CREATE SCHEMA IF NOT EXISTS META WITH MANAGED ACCESS
    COMMENT = 'Pipeline metadata: ingestion audit and reconciliation';

-- The auto-created PUBLIC schema is not used. It is left in place (dropping
-- it is optional) and no project role is granted access to it.
