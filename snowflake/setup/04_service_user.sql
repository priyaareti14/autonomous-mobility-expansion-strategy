-- =============================================================================
-- 04_service_user.sql
-- Autonomous Mobility Expansion Strategy: development service user
--
-- Why a service user
--   Snowflake blocks password authentication for non-human users, and human
--   (PERSON) users must use MFA. Python now, and dbt in Phase 4, need
--   non-interactive access. A dedicated TYPE = SERVICE user with key-pair
--   authentication keeps automation separate from the human login. The user
--   cannot have a password.
--
-- Scope
--   One local-development service user, holding the three functional roles
--   but NOT AM_ADMIN. The default role is the least-privileged AM_ANALYST, so
--   every elevated action needs an explicit USE ROLE. A separate CI user and
--   role are deferred to Phase 12.
--
-- Secondary roles
--   New users default to DEFAULT_SECONDARY_ROLES = ('ALL'), which would let
--   every granted role authorize SELECT and DML in every session. That makes
--   per-role privilege checks meaningless, so it is set to () here: only the
--   active primary role authorizes statements.
--
-- Public key
--   Replace <PUBLIC_KEY_BODY> at run time with the body of the PUBLIC key file
--   (the base64 text between the BEGIN/END PUBLIC KEY lines, without those
--   lines). The public key is not secret, but it is still not committed.
--   The PRIVATE key never goes into Snowflake, this file or the repository.
--
-- Run as : SECURITYADMIN for user creation (inherits USERADMIN's CREATE USER),
--          then AM_ADMIN to grant its own functional roles
-- Order  : after 01 and 02 (03 is independent)
-- Rerun  : CREATE USER IF NOT EXISTS leaves an existing user unchanged, so the
--          key and defaults are re-applied with ALTER USER below.
-- =============================================================================

USE ROLE SECURITYADMIN;

CREATE USER IF NOT EXISTS AM_SVC_DEV
    TYPE                    = SERVICE
    DEFAULT_ROLE            = AM_ANALYST
    DEFAULT_WAREHOUSE       = AM_EXPANSION_WH
    DEFAULT_NAMESPACE       = AUTONOMOUS_MOBILITY
    DEFAULT_SECONDARY_ROLES = ()
    COMMENT = 'Autonomous Mobility project: local development service user (key-pair only)';

-- Re-applied on every run so key rotation and defaults are idempotent.
ALTER USER AM_SVC_DEV SET
    RSA_PUBLIC_KEY          = '<PUBLIC_KEY_BODY>'
    DEFAULT_SECONDARY_ROLES = ();

-- Role grants, made by the role owner (AM_ADMIN owns the functional roles).
USE ROLE AM_ADMIN;

GRANT ROLE AM_INGESTOR    TO USER AM_SVC_DEV;
GRANT ROLE AM_TRANSFORMER TO USER AM_SVC_DEV;
GRANT ROLE AM_ANALYST     TO USER AM_SVC_DEV;

-- Check that the registered key matches the local public key. Compare
-- RSA_PUBLIC_KEY_FP with the fingerprint printed by the key-generation step.
USE ROLE SECURITYADMIN;
DESC USER AM_SVC_DEV
  ->> SELECT "property", "value" FROM $1
      WHERE "property" IN ('TYPE','DEFAULT_ROLE','DEFAULT_WAREHOUSE',
                           'DEFAULT_SECONDARY_ROLES','RSA_PUBLIC_KEY_FP','HAS_PASSWORD');
