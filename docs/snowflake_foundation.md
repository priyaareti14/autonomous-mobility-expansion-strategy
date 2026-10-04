# Snowflake Warehouse Foundation

**Status:** Phase 2 · **Last updated:** 2026-10-01

This document describes the Snowflake foundation that later phases build on. Phase 2 creates **infrastructure only**: compute, a database, layered schemas, roles, grants, authentication and cost controls. No project data is loaded, no dbt models exist, and no analysis has been performed.

---

## 1. Why Snowflake

The project needs one analytical source of truth that serves three consumers:
1. Python ingestion, which writes source-aligned data (Phase 3).
2. dbt, which transforms it into tested, documented models (Phase 4).
3. Python analytics and Power BI, which read curated outputs (Phases 5–10).

Snowflake separates storage from compute, so the warehouse can stay suspended (and cost nothing) between runs. Its role-based access control lets each pipeline stage get only the privileges it needs. Python analytical outputs are written back to Snowflake, not to loose CSV files, so Power BI reads every number from one governed place.

## 2. Planned data flow

Only the parts marked **[Phase 2]** exist so far. Everything else is planned.

```
Public sources (Census, NOAA, FAA, EPA, official regulatory sources)
      │
      ▼
Python ingestion + validation                      [Phase 3: planned]
      │   role: AM_INGESTOR
      ▼
AUTONOMOUS_MOBILITY.RAW   ◄──►  META (audit, reconciliation)      [Phase 2: schemas exist, empty]
      │
      ▼   role: AM_TRANSFORMER
dbt  STAGING ──► INTERMEDIATE ──► CORE (dims / facts)  [Phase 4: planned]
                                     │
                                     ▼
                                 ANALYTICS (marts)
      ▲                              │
      │   Python EDA, scoring,       │
      └── sensitivity (write-back) ◄─┘                  [Phases 5–9: planned]
                                     │
                                     ▼   role: AM_ANALYST
                                 Power BI               [Phase 10: planned]
```

## 3. Objects

### 3.1 Database and schemas

Database: **`AUTONOMOUS_MOBILITY`** (default 1-day Time Travel retention).

| Schema | Purpose | Written by | Read by |
|---|---|---|---|
| `RAW` | Source-aligned landing tables with minimal transformation | AM_INGESTOR (Phase 3) | AM_TRANSFORMER |
| `META` | Ingestion audit, load metadata, row-count reconciliation | AM_INGESTOR (Phase 3) | AM_TRANSFORMER |
| `STAGING` | dbt staging models: typed, renamed, standardized | AM_TRANSFORMER (Phase 4) | AM_TRANSFORMER |
| `INTERMEDIATE` | dbt reusable joins and aggregations | AM_TRANSFORMER (Phase 4) | AM_TRANSFORMER |
| `CORE` | Dimensions and subject-area facts with documented grain | AM_TRANSFORMER (Phase 4) | AM_TRANSFORMER, AM_ANALYST |
| `ANALYTICS` | Decision-ready marts and persisted Python outputs | AM_TRANSFORMER (Phases 4, 9) | AM_TRANSFORMER, AM_ANALYST |

- All six schemas are **managed access** schemas. Only the schema owner (`AM_ADMIN`) or a role with `MANAGE GRANTS` can grant privileges on objects inside them. The ingestion process and dbt therefore cannot hand out ad-hoc access to the tables they create. All access comes from the central future grants in `02_roles_and_grants.sql`.
- The auto-created `PUBLIC` schema is not used, and no project role has access to it.

### 3.2 Warehouse

| Setting | Value | Reason |
|---|---|---|
| Name | `AM_EXPANSION_WH` | Project-scoped, so cost is attributable |
| `WAREHOUSE_SIZE` | `XSMALL` | Smallest size. The data is small (35 markets, tens of MB), and nothing so far requires more |
| `AUTO_SUSPEND` | `60` seconds | Billing is per second with a 60-second minimum each time the warehouse resumes, so suspending sooner saves nothing. Snowflake's suspend check runs about every 30 seconds |
| `AUTO_RESUME` | `TRUE` | Queries start the warehouse on demand, with no manual start/stop |
| `INITIALLY_SUSPENDED` | `TRUE` | Creating the warehouse consumes no credits |
| `STATEMENT_TIMEOUT_IN_SECONDS` | `1800` | Guards against runaway queries. The account default is 2 days |
| Generation | Snowflake default (Gen2 where the region supports it) | Not overridden |

This is a development workload: short, bursty runs (ingestion, `dbt build`, simulations) separated by long idle periods. A minimal size combined with fast auto-suspend fits that pattern. Resize only if Phase 3–9 timings show a measured need.

## 4. Role architecture

```
AM_INGESTOR ────┐
AM_TRANSFORMER ─┼──► AM_ADMIN ──► SYSADMIN
AM_ANALYST ─────┘
```

| Role | Responsibility | Key privileges | Deliberately excluded |
|---|---|---|---|
| `AM_ADMIN` | Project administration | Owns the database, the six schemas, the warehouse and the three functional roles. Inherits all functional roles | No account-level privileges; not granted to the service user |
| `AM_INGESTOR` | Python ingestion (Phase 3) | Warehouse and database `USAGE`; on RAW and META: `USAGE`, `CREATE TABLE`, `CREATE STAGE`, `CREATE FILE FORMAT`. Owns the tables it creates | Any access to STAGING, INTERMEDIATE, CORE or ANALYTICS |
| `AM_TRANSFORMER` | dbt (Phase 4) and Python write-back (Phase 9) | `SELECT` on current and future tables/views in RAW and META. `USAGE`, `CREATE TABLE`, `CREATE VIEW` on STAGING, INTERMEDIATE, CORE and ANALYTICS. Owns the models it creates | Writing to RAW or META; `CREATE SCHEMA`/`CREATE DATABASE` |
| `AM_ANALYST` | Power BI and analysis | `SELECT` on current and future tables/views in CORE and ANALYTICS | RAW, META, STAGING and INTERMEDIATE; all writes |

**Design notes:**
- **Functional roles roll up to `AM_ADMIN`, and `AM_ADMIN` rolls up to `SYSADMIN`.** This is Snowflake's recommended pattern, so system administrators keep control of everything the project creates.
- **`AM_ADMIN` owns the functional roles,** so it can grant them to users. `AM_ADMIN` itself is owned by `SECURITYADMIN`, so it cannot re-grant itself.
- **Only schema-level future grants are used.** When database-level and schema-level future grants overlap, Snowflake applies the schema-level ones and ignores the rest. Using one level keeps the result predictable.
- **No CI role yet.** It is deferred to Phase 12.
- **Phase 9 write-back:** Python outputs will be written to ANALYTICS using `AM_TRANSFORMER`. If Phase 9 shows that a separate role is warranted, that will be proposed then.

## 5. Authentication

| Item | Decision |
|---|---|
| Programmatic identity | Service user **`AM_SVC_DEV`**, `TYPE = SERVICE` (`04_service_user.sql`) |
| Why a service user | Snowflake blocks password authentication for non-human users, and requires MFA for human password logins. A service user keeps automation separate from your personal login and cannot have a password |
| Method | Key-pair (JWT): a 2048-bit RSA key in encrypted PKCS#8 format, protected with **AES-256-CBC**. That is the cipher dbt documents for encrypted keys, so the same key works in Phase 4 |
| Roles held | `AM_INGESTOR`, `AM_TRANSFORMER`, `AM_ANALYST`. **Not** `AM_ADMIN` or any system role |
| Default role | `AM_ANALYST`, the least privileged. Elevated work requires an explicit role |
| Secondary roles | `DEFAULT_SECONDARY_ROLES = ()`. Snowflake's default for new users is `('ALL')`, which lets every granted role authorize SELECT and DML in every session. That would blur role boundaries and make privilege tests meaningless |
| Private key location | `%USERPROFILE%\.snowflake\keys\`: outside the repository and outside OneDrive, with access restricted to the Windows user |
| Passphrase | Stored only in the git-ignored local `.env` (`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`) |
| Rotation | Register the new public key in `RSA_PUBLIC_KEY_2`, switch the local key, then `UNSET RSA_PUBLIC_KEY`. Snowflake's named key pairs (`ALTER USER … ADD KEY PAIR`) are an alternative |

**Trade-off recorded:** keeping the passphrase in `.env` on the same machine as the key protects against copying the key file on its own, but not against full compromise of the local machine. That level of protection is acceptable for a local development portfolio project. CI (Phase 12) will use repository secrets instead.

## 6. Cost controls

| Control | Status | Detail |
|---|---|---|
| `AUTO_SUSPEND = 60` / `AUTO_RESUME = TRUE` | Configured (script 01) | Primary control. Idle compute is never billed for more than about a minute |
| Statement timeout | Configured (script 01) | 1800 seconds |
| Resource monitor `AM_EXPANSION_RM` | **Active (verified 2026-10-04): 10 credits/month** (script 03) | Warehouse-level, monthly reset. Notifications at 50/75/90%, `SUSPEND` at 100%, `SUSPEND_IMMEDIATE` at 110%. Created by ACCOUNTADMIN |

What the resource monitor does **not** cover (documented Snowflake behavior):
- Serverless features, AI services and cloud-services credits. It can monitor cloud-services usage but cannot suspend it.
- Other warehouses in the account, such as a default `COMPUTE_WH`.
- Instant stops: suspension takes effect with a delay, so usage can slightly exceed the quota.

Notifications reach only account administrators who have enabled them in Snowsight (user menu → Profile).

## 7. Naming conventions

| Object | Convention | Example |
|---|---|---|
| Project roles | `AM_<FUNCTION>` | `AM_TRANSFORMER` |
| Service users | `AM_SVC_<PURPOSE>` | `AM_SVC_DEV` |
| Warehouse | `AM_<PURPOSE>_WH` | `AM_EXPANSION_WH` |
| Resource monitor | `AM_<PURPOSE>_RM` | `AM_EXPANSION_RM` |
| Schemas | Layer name, uppercase | `STAGING` |
| Temporary validation objects | `ZZ_PHASE<n>_*`, always dropped | `ZZ_PHASE2_PRIV_CHECK` |
| Table names (Phase 3+) | `RAW.<SOURCE>_<DATASET>`, `CORE.DIM_*` / `CORE.FCT_*`, `ANALYTICS.MART_*` | Set in Phases 3–4 |
| Key column | `market_id` = 5-digit CBSA code, stored as a string | See `project_scope.md` §4 |

## 8. Environment variables

These are defined in `.env.example` (names only). Real values go in the git-ignored `.env`.

| Variable | Required | Value for this project |
|---|---|---|
| `SNOWFLAKE_ACCOUNT` | Yes | Account identifier in `orgname-accountname` form (no `.snowflakecomputing.com`) |
| `SNOWFLAKE_USER` | Yes | `AM_SVC_DEV` |
| `SNOWFLAKE_PRIVATE_KEY_PATH` | Yes | Absolute path to the private key, **outside the repo** (the connection helper refuses a key inside the repo). Wrap Windows paths in **single quotes**. In double quotes, `python-dotenv` reads backslashes as escape sequences; for example, `\a` in `\am_svc_dev…` became a bell character during Phase 2 setup |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | If the key is encrypted | Key passphrase |
| `SNOWFLAKE_ROLE` | No (default `AM_ANALYST`) | Role for the session |
| `SNOWFLAKE_WAREHOUSE` | No (default `AM_EXPANSION_WH`) | |
| `SNOWFLAKE_DATABASE` | No (default `AUTONOMOUS_MOBILITY`) | |
| `CENSUS_API_KEY` | Phase 3 | Census Data API key |

## 9. Setup and validation procedure

Run the setup scripts in Snowsight, using a user that can assume SYSADMIN, SECURITYADMIN and ACCOUNTADMIN:

| Step | File | Run as | Notes |
|---|---|---|---|
| 1 | `snowflake/setup/01_foundation.sql` | SYSADMIN | Warehouse, database, schemas |
| 2 | `snowflake/setup/02_roles_and_grants.sql` | SECURITYADMIN → SYSADMIN → AM_ADMIN (switched in the script) | Roles, ownership, grants |
| 3 | `snowflake/setup/03_cost_controls.sql` | ACCOUNTADMIN | Resource monitor (approved quota: 10) |
| 4 | Generate the key pair locally | Your Windows user | Outside the repo; see the Phase 2 instructions |
| 5 | `snowflake/setup/04_service_user.sql` | SECURITYADMIN → AM_ADMIN | Paste the public key body at run time; never commit it |
| 6 | `snowflake/validation/01_validate_foundation.sql` | AM_ADMIN (+ SECURITYADMIN/ACCOUNTADMIN) | Read-only checks |
| 7 | `python scripts/validate_snowflake_connection.py` | Service user (all three functional roles in turn) | Automated connection, object and privilege tests |

The Python validation script:
1. Connects with the key pair and prints the session context. Account and user are masked unless `--show-identifiers` is passed.
2. Confirms the schemas, warehouse settings and roles exist, and that the project schemas contain no tables.
3. Confirms the service user holds the three functional roles and no admin role.
4. Runs allow/deny privilege tests for each role on **empty, temporary** `ZZ_PHASE2_PRIV_CHECK` objects. It tests the future grants and managed access, with secondary roles disabled.
5. Drops every check object and confirms none remain.

It exits non-zero if any check fails.

### 9.1 Phase 2 validation result (2026-10-04)

| Area | Result |
|---|---|
| Key-pair connection as `AM_SVC_DEV` (`TYPE = SERVICE`) | Connected. Snowflake 10.35.101, region AWS_CA_CENTRAL_1 |
| Foundation objects (6 schemas, warehouse settings, 4 roles) | All present. Warehouse X-Small / 60 s / auto-resume |
| Project tables before tests | 0 |
| Service-user roles | Holds the 3 functional roles; does not hold AM_ADMIN or any system role |
| Privilege tests | 24 allow/deny tests passed: ingestor confined to RAW/META; transformer reads RAW/META through future grants, cannot write them, builds all 4 downstream schemas; analyst reads CORE/ANALYTICS through future grants only; managed access blocked an owner's ad-hoc grant (error 3509) |
| Cleanup | 0 check objects remaining |
| **Total** | **46/46 checks passed** |

On the first run, one check was misreported: the managed-access denial returned error 3509, which the script didn't yet treat as a denial. The script was corrected; Snowflake behaved as designed.

**Admin-only checks.** The service user deliberately has no admin roles, so these were run manually by the project owner in Snowsight with `01_validate_foundation.sql` and confirmed on 2026-10-04:
- `AM_EXPANSION_WH` has `STATEMENT_TIMEOUT_IN_SECONDS = 1800`.
- Resource monitor `AM_EXPANSION_RM` is active with a 10-credit monthly quota.

## 10. Security rules

- No passwords, private keys, passphrases, tokens or account identifiers in the repository, in SQL or in Python.
- `.env`, `*.p8`, `*.pem`, `*.key` and `profiles.yml` are git-ignored.
- Private keys live outside the repository. The connection helper refuses a key path inside the repo.
- Only the **public** key is ever registered with Snowflake. It is pasted at run time and not committed.
- The validation output masks account and user by default.
- ACCOUNTADMIN is used only for the resource monitor, never by automation.

## 11. What Phase 2 deliberately does NOT do

- Load, download or stage any project dataset.
- Create any project table, view, stage or file format. The only objects created are temporary validation objects, which are dropped.
- Create dbt projects, models, `profiles.yml` or CI workflows.
- Perform EDA, feature engineering, scoring, clustering or sensitivity analysis.
- Create a CI role or CI user.
- Resize the warehouse or enable any paid serverless feature.
