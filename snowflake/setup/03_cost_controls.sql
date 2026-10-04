-- =============================================================================
-- 03_cost_controls.sql
-- Autonomous Mobility Expansion Strategy: warehouse cost guardrail
--
-- STATUS: quota of 10 credits/month approved by the project owner (2026-10-01).
--
-- What this does
--   Creates a warehouse-level resource monitor and attaches it to
--   AM_EXPANSION_WH. It caps monthly compute credits for this project's
--   warehouse only. The warehouse's AUTO_SUSPEND = 60 (script 01) is the
--   first line of defense and applies whether or not this monitor exists.
--
-- What it does NOT do (documented Snowflake behavior)
--   * It does not cover serverless features, AI services or cloud-services
--     credits. A warehouse-level monitor can monitor cloud-services usage but
--     cannot suspend it.
--   * It does not cover other warehouses in the account (for example a
--     default COMPUTE_WH).
--   * Suspension is not instantaneous; usage can slightly exceed the quota,
--     even with SUSPEND_IMMEDIATE.
--   * Notifications reach only account administrators who enabled
--     notifications in Snowsight (user menu > Profile > Notifications).
--
-- Run as : ACCOUNTADMIN (only account administrators can create resource
--          monitors and assign them to warehouses)
-- Order  : after 01 and 02
-- Rerun  : CREATE ... IF NOT EXISTS leaves an existing monitor unchanged.
--          To change the quota later, use:
--            ALTER RESOURCE MONITOR AM_EXPANSION_RM SET CREDIT_QUOTA = <n>;
-- =============================================================================

USE ROLE ACCOUNTADMIN;

CREATE RESOURCE MONITOR IF NOT EXISTS AM_EXPANSION_RM WITH
    CREDIT_QUOTA    = 10            -- approved development cap (credits per month)
    FREQUENCY       = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
        ON  50 PERCENT DO NOTIFY
        ON  75 PERCENT DO NOTIFY
        ON  90 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND             -- let running queries finish, then suspend
        ON 110 PERCENT DO SUSPEND_IMMEDIATE;  -- hard stop: cancel running queries

ALTER WAREHOUSE AM_EXPANSION_WH SET RESOURCE_MONITOR = AM_EXPANSION_RM;

-- Optional: let the project admin role see monitor usage without ACCOUNTADMIN.
GRANT MONITOR ON RESOURCE MONITOR AM_EXPANSION_RM TO ROLE AM_ADMIN;
