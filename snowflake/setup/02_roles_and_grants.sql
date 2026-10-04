-- =============================================================================
-- 02_roles_and_grants.sql
-- Autonomous Mobility Expansion Strategy: role-based access control
--
-- Role hierarchy (arrow = "is granted to"):
--
--     AM_INGESTOR ─┐
--     AM_TRANSFORMER ┼──> AM_ADMIN ──> SYSADMIN
--     AM_ANALYST ──┘
--
--   AM_ADMIN       Project administrator. Owns the database, schemas, warehouse
--                  and the three functional roles. No account-level privileges.
--   AM_INGESTOR    Python ingestion (Phase 3). Writes RAW and META only.
--   AM_TRANSFORMER dbt (Phase 4). Reads RAW and META; builds STAGING,
--                  INTERMEDIATE, CORE and ANALYTICS.
--   AM_ANALYST     BI and analysis. Read-only on CORE and ANALYTICS.
--
-- Run as : SECURITYADMIN, then SYSADMIN, then AM_ADMIN, as switched below.
--          Every section starts with USE ROLE. ACCOUNTADMIN is not required.
-- Order  : after 01_foundation.sql
-- Rerun  : designed to be rerunnable. CREATE ROLE IF NOT EXISTS; re-granting
--          an existing privilege is a no-op.
--          Section A uses SECURITYADMIN (MANAGE GRANTS) rather than USERADMIN,
--          so it still works after the functional roles have moved to AM_ADMIN.
--          Section B still works after the transfer because SYSADMIN inherits
--          AM_ADMIN (the new owner).
--          First run verified 2026-10-04 (46/46 automated checks). A second
--          rerun has not yet been exercised.
-- =============================================================================


-- =============================================================================
-- Section A: create roles and the hierarchy (SECURITYADMIN)
--   SECURITYADMIN inherits USERADMIN (CREATE ROLE) and holds MANAGE GRANTS.
-- =============================================================================
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS AM_ADMIN
    COMMENT = 'Autonomous Mobility project administrator (no account-level privileges)';
CREATE ROLE IF NOT EXISTS AM_INGESTOR
    COMMENT = 'Python ingestion: write RAW and META';
CREATE ROLE IF NOT EXISTS AM_TRANSFORMER
    COMMENT = 'dbt transformation: read RAW/META, build STAGING/INTERMEDIATE/CORE/ANALYTICS';
CREATE ROLE IF NOT EXISTS AM_ANALYST
    COMMENT = 'Read-only access to curated CORE and ANALYTICS';

-- Functional roles roll up to AM_ADMIN, and AM_ADMIN rolls up to SYSADMIN
-- (Snowflake's recommended pattern), so system administrators keep control.
GRANT ROLE AM_INGESTOR    TO ROLE AM_ADMIN;
GRANT ROLE AM_TRANSFORMER TO ROLE AM_ADMIN;
GRANT ROLE AM_ANALYST     TO ROLE AM_ADMIN;
GRANT ROLE AM_ADMIN       TO ROLE SYSADMIN;

-- AM_ADMIN owns the three functional roles, so it can grant them to users.
-- AM_ADMIN itself stays owned by SECURITYADMIN, so it cannot modify or
-- re-grant its own role.
GRANT OWNERSHIP ON ROLE AM_INGESTOR    TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON ROLE AM_TRANSFORMER TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON ROLE AM_ANALYST     TO ROLE AM_ADMIN COPY CURRENT GRANTS;


-- =============================================================================
-- Section B: hand project objects to AM_ADMIN (SYSADMIN, current owner)
-- =============================================================================
USE ROLE SYSADMIN;

GRANT OWNERSHIP ON WAREHOUSE AM_EXPANSION_WH     TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON DATABASE  AUTONOMOUS_MOBILITY TO ROLE AM_ADMIN COPY CURRENT GRANTS;

GRANT OWNERSHIP ON SCHEMA AUTONOMOUS_MOBILITY.RAW          TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AUTONOMOUS_MOBILITY.STAGING      TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AUTONOMOUS_MOBILITY.INTERMEDIATE TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AUTONOMOUS_MOBILITY.CORE         TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS    TO ROLE AM_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA AUTONOMOUS_MOBILITY.META         TO ROLE AM_ADMIN COPY CURRENT GRANTS;


-- =============================================================================
-- Section C: functional privileges (AM_ADMIN, as owner)
--   Only schema-level future grants are used: when both database- and
--   schema-level future grants exist, the schema-level ones win and the
--   database-level ones are ignored. Using one level keeps the result
--   predictable.
-- =============================================================================
USE ROLE AM_ADMIN;

-- C1. Compute and database entry for all functional roles ---------------------
GRANT USAGE ON WAREHOUSE AM_EXPANSION_WH     TO ROLE AM_INGESTOR;
GRANT USAGE ON WAREHOUSE AM_EXPANSION_WH     TO ROLE AM_TRANSFORMER;
GRANT USAGE ON WAREHOUSE AM_EXPANSION_WH     TO ROLE AM_ANALYST;

GRANT USAGE ON DATABASE AUTONOMOUS_MOBILITY  TO ROLE AM_INGESTOR;
GRANT USAGE ON DATABASE AUTONOMOUS_MOBILITY  TO ROLE AM_TRANSFORMER;
GRANT USAGE ON DATABASE AUTONOMOUS_MOBILITY  TO ROLE AM_ANALYST;

-- C2. AM_INGESTOR: create and own landing objects in RAW and META --------------
--     CREATE STAGE and CREATE FILE FORMAT support connector bulk loads (temporary
--     stage + file format); Phase 3 confirms the exact load method. Tables it
--     creates, it owns, so it can insert, replace and drop them. It gets no
--     access to any downstream schema.
GRANT USAGE, CREATE TABLE, CREATE STAGE, CREATE FILE FORMAT
    ON SCHEMA AUTONOMOUS_MOBILITY.RAW  TO ROLE AM_INGESTOR;
GRANT USAGE, CREATE TABLE, CREATE STAGE, CREATE FILE FORMAT
    ON SCHEMA AUTONOMOUS_MOBILITY.META TO ROLE AM_INGESTOR;

-- C3. AM_TRANSFORMER: read RAW and META (current and future objects) -----------
GRANT USAGE ON SCHEMA AUTONOMOUS_MOBILITY.RAW  TO ROLE AM_TRANSFORMER;
GRANT USAGE ON SCHEMA AUTONOMOUS_MOBILITY.META TO ROLE AM_TRANSFORMER;

GRANT SELECT ON ALL    TABLES IN SCHEMA AUTONOMOUS_MOBILITY.RAW  TO ROLE AM_TRANSFORMER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA AUTONOMOUS_MOBILITY.RAW  TO ROLE AM_TRANSFORMER;
GRANT SELECT ON ALL    VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.RAW  TO ROLE AM_TRANSFORMER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.RAW  TO ROLE AM_TRANSFORMER;

GRANT SELECT ON ALL    TABLES IN SCHEMA AUTONOMOUS_MOBILITY.META TO ROLE AM_TRANSFORMER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA AUTONOMOUS_MOBILITY.META TO ROLE AM_TRANSFORMER;
GRANT SELECT ON ALL    VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.META TO ROLE AM_TRANSFORMER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.META TO ROLE AM_TRANSFORMER;

-- C4. AM_TRANSFORMER: build the transformation and curated layers -------------
--     It owns what it creates (dbt tables and views), so dbt can replace and
--     drop its own models. No CREATE SCHEMA on the database: schemas are fixed
--     here, and Phase 4 will configure dbt to target them.
GRANT USAGE, CREATE TABLE, CREATE VIEW ON SCHEMA AUTONOMOUS_MOBILITY.STAGING      TO ROLE AM_TRANSFORMER;
GRANT USAGE, CREATE TABLE, CREATE VIEW ON SCHEMA AUTONOMOUS_MOBILITY.INTERMEDIATE TO ROLE AM_TRANSFORMER;
GRANT USAGE, CREATE TABLE, CREATE VIEW ON SCHEMA AUTONOMOUS_MOBILITY.CORE         TO ROLE AM_TRANSFORMER;
GRANT USAGE, CREATE TABLE, CREATE VIEW ON SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS    TO ROLE AM_TRANSFORMER;

-- C5. AM_ANALYST: read-only on curated layers (current and future objects) -----
GRANT USAGE ON SCHEMA AUTONOMOUS_MOBILITY.CORE      TO ROLE AM_ANALYST;
GRANT USAGE ON SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS TO ROLE AM_ANALYST;

GRANT SELECT ON ALL    TABLES IN SCHEMA AUTONOMOUS_MOBILITY.CORE      TO ROLE AM_ANALYST;
GRANT SELECT ON FUTURE TABLES IN SCHEMA AUTONOMOUS_MOBILITY.CORE      TO ROLE AM_ANALYST;
GRANT SELECT ON ALL    VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.CORE      TO ROLE AM_ANALYST;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.CORE      TO ROLE AM_ANALYST;

GRANT SELECT ON ALL    TABLES IN SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS TO ROLE AM_ANALYST;
GRANT SELECT ON FUTURE TABLES IN SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS TO ROLE AM_ANALYST;
GRANT SELECT ON ALL    VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS TO ROLE AM_ANALYST;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS TO ROLE AM_ANALYST;

-- Deliberately NOT granted:
--   * any project role -> RAW/STAGING/INTERMEDIATE access for AM_ANALYST
--   * AM_INGESTOR      -> any downstream schema
--   * AM_TRANSFORMER   -> write access to RAW or META
--   * CREATE SCHEMA / CREATE DATABASE / account-level privileges to any project role
--   * MODIFY / OPERATE on the warehouse to functional roles (USAGE suffices; AUTO_RESUME starts it)
