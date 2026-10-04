-- =============================================================================
-- 01_validate_foundation.sql
-- Autonomous Mobility Expansion Strategy: read-only foundation checks
--
-- Read-only. Creates nothing and changes nothing. Run after setup 01, 02 and
-- 04 (and 03 if approved). Each block states its expected result.
-- The automated equivalent, including privilege tests, is
-- scripts/validate_snowflake_connection.py.
--
-- Run as : AM_ADMIN (blocks 1-6); ACCOUNTADMIN for block 7 (resource monitor)
-- =============================================================================

USE ROLE AM_ADMIN;
USE WAREHOUSE AM_EXPANSION_WH;

-- 1. Warehouse configuration
--    Expect: size X-Small, auto_suspend 60, auto_resume true, owner AM_ADMIN,
--            resource_monitor AM_EXPANSION_RM (only if 03 was run)
SHOW WAREHOUSES LIKE 'AM_EXPANSION_WH';
SELECT "name", "size", "auto_suspend", "auto_resume", "owner", "resource_monitor"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

SHOW PARAMETERS LIKE 'STATEMENT_TIMEOUT_IN_SECONDS' IN WAREHOUSE AM_EXPANSION_WH;
--    Expect: value 1800

-- 2. Database and schemas
--    Expect: exactly RAW, STAGING, INTERMEDIATE, CORE, ANALYTICS, META
--            (plus PUBLIC and INFORMATION_SCHEMA), all six managed access,
--            owned by AM_ADMIN
SHOW SCHEMAS IN DATABASE AUTONOMOUS_MOBILITY;
SELECT "name", "owner", "options"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "name" IN ('RAW','STAGING','INTERMEDIATE','CORE','ANALYTICS','META')
ORDER BY "name";

-- 3. No project data yet
--    Expect: zero rows (Phase 2 creates no tables or views)
SELECT table_schema, table_name, table_type
FROM AUTONOMOUS_MOBILITY.INFORMATION_SCHEMA.TABLES
WHERE table_schema IN ('RAW','STAGING','INTERMEDIATE','CORE','ANALYTICS','META');

-- 4. Role hierarchy
--    Expect: AM_INGESTOR, AM_TRANSFORMER, AM_ANALYST granted to AM_ADMIN;
--            AM_ADMIN granted to SYSADMIN
SHOW GRANTS OF ROLE AM_ADMIN;
SHOW GRANTS OF ROLE AM_INGESTOR;
SHOW GRANTS OF ROLE AM_TRANSFORMER;
SHOW GRANTS OF ROLE AM_ANALYST;

-- 5. Privileges per functional role
SHOW GRANTS TO ROLE AM_INGESTOR;     -- expect: WH usage, DB usage, RAW+META usage/create table/stage/file format
SHOW GRANTS TO ROLE AM_TRANSFORMER;  -- expect: WH/DB usage, RAW+META usage, 4 build schemas usage/create table/view
SHOW GRANTS TO ROLE AM_ANALYST;      -- expect: WH/DB usage, CORE+ANALYTICS usage only

-- 6. Future grants
SHOW FUTURE GRANTS IN SCHEMA AUTONOMOUS_MOBILITY.RAW;        -- expect: SELECT tables/views -> AM_TRANSFORMER
SHOW FUTURE GRANTS IN SCHEMA AUTONOMOUS_MOBILITY.META;       -- expect: SELECT tables/views -> AM_TRANSFORMER
SHOW FUTURE GRANTS IN SCHEMA AUTONOMOUS_MOBILITY.CORE;       -- expect: SELECT tables/views -> AM_ANALYST
SHOW FUTURE GRANTS IN SCHEMA AUTONOMOUS_MOBILITY.ANALYTICS;  -- expect: SELECT tables/views -> AM_ANALYST
SHOW FUTURE GRANTS IN SCHEMA AUTONOMOUS_MOBILITY.STAGING;    -- expect: none
SHOW FUTURE GRANTS IN SCHEMA AUTONOMOUS_MOBILITY.INTERMEDIATE; -- expect: none

-- 7. Service user and resource monitor (ACCOUNTADMIN or SECURITYADMIN)
USE ROLE SECURITYADMIN;
SHOW GRANTS TO USER AM_SVC_DEV;      -- expect: AM_INGESTOR, AM_TRANSFORMER, AM_ANALYST (not AM_ADMIN)

USE ROLE ACCOUNTADMIN;
SHOW RESOURCE MONITORS LIKE 'AM_EXPANSION_RM';   -- expect one row only if 03 was approved and run
