# Ingestion Pipeline (Phase 3)

**Status:** Phase 3 · **Last updated:** 2026-10-05

Phase 3 lands the approved structured public sources in Snowflake `RAW`, unchanged in meaning and grain, with a full audit trail in `META`. It **ends at validated, reconciled RAW tables**. There are no joins, no market mapping, no features, no scores and no dbt models.

---

## 1. Flow

```
config/ingestion_sources.json   (registry, derived from docs/data_sources.md)
          │
          ▼  scripts/run_ingestion.py   (role AM_INGESTOR, secondary roles NONE)
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ 1 ACQUIRE    HTTP / Census API / ArcGIS REST from the official endpoint │
 │ 2 VERIFY     status, payload type (not HTML), expected file/vintage     │
 │ 3 SNAPSHOT   data/raw/<source_id>/<name>  + SHA-256 + bytes             │
 │ 4 IDEMPOTENT same source+dataset+vintage+SHA already loaded? → SKIP     │
 │              same pin, different SHA? → BLOCKED (drift), RAW untouched │
 │ 5 VALIDATE   pass 1: required columns, keys, source-specific checks     │
 │              any FAIL → FAILED, nothing loaded                         │
 │ 6 LOAD       pass 2: temp table → single INSERT into RAW.<table>        │
 │ 7 RECONCILE  source − rejected = parsed = RAW rows for this run         │
 │              mismatch → this run's rows deleted, FAILED                │
 │ 8 AUDIT      META.INGESTION_RUNS / _CHECKS / _REJECTED_ROWS             │
 └─────────────────────────────────────────────────────────────────────────┘
          │
          ▼  scripts/validate_raw_landing.py   (role AM_TRANSFORMER)
     PASS / WARN / FAIL per dataset
```

A failure in one dataset is audited, and the run moves on to the next. One source can never corrupt another.

## 2. Code layout

| Path | Responsibility |
|---|---|
| `config/ingestion_sources.json` | Registry: one entry per dataset (source ID, vintage, endpoint, grain, RAW table, required columns, natural key), plus the list of sources deliberately not ingested and why. No secrets |
| `src/ingestion/common.py` | Secret redaction, logging filter, HTTP with retries (401/403/429 → BLOCKED, never worked around), SHA-256, snapshot cache, Snowflake-safe column names |
| `src/ingestion/audit.py` | Writes the META audit trail; looks up prior successful loads |
| `src/ingestion/loaders.py` | Temp-table staging, RAW table creation, schema-drift check, orphan cleanup, single-statement append, per-run row count |
| `src/ingestion/sources/_tabular.py` | Two-pass streaming validation and frame generation shared by every connector |
| `src/ingestion/sources/{census,noaa,faa,epa,bls}.py` | Source-specific acquisition and integrity checks |
| `src/ingestion/source_registry.py` | Loads and expands the registry (one entry per ACS table group) |
| `scripts/run_ingestion.py` | CLI: `--setup-audit`, `--list`, `--datasets …`, `--all`, `--simulate-drift` |
| `scripts/validate_raw_landing.py` | Independent post-load validation, run as the downstream role |
| `snowflake/setup/05_ingestion_audit.sql` | META audit tables (run as AM_INGESTOR) |
| `snowflake/validation/02_validate_raw_landing.sql` | Read-only Snowsight inspection queries |

## 3. Local raw cache

- Snapshots go to `data/raw/<source_id>/`, with names following `<SOURCE_ID>_<VINTAGE>_<DATASET>.<ext>`. The folder is **git-ignored** and never committed.
- API responses are saved as canonical compact JSON. The ArcGIS EPA pages are saved as NDJSON ordered by `OBJECTID`, so the checksum is stable between runs.
- The SHA-256 and byte size of every snapshot are recorded in `META.INGESTION_RUNS`. No credential ever appears in a filename, URL or log.

## 4. RAW conventions

| Rule | Implementation |
|---|---|
| Source-aligned | One RAW table per source dataset. Native geography and grain are preserved, and nothing is filtered to the 35 markets |
| Typing | Every source value is `VARCHAR`, holding its text as published. Analytical casting is left to dbt STAGING. NOAA annual records are `VARIANT` (see §8) |
| Column names | Uppercased. `%` becomes `PCT`; other non-alphanumeric runs become `_`; a leading digit gets a `C_` prefix. Collisions fail the load. Every rename is recorded as a check (`column_names_normalized`) |
| Lineage metadata on every row | `_INGEST_RUN_ID`, `_INGESTED_AT`, `_SOURCE_ID`, `_SOURCE_VINTAGE`, `_SOURCE_FILE`, `_SOURCE_FILE_SHA256`, `_SOURCE_ROW_NUMBER` (the true source record number) |
| Table comment | Source, dataset, vintage and grain |
| No business logic | No joins, no derived metrics, no imputation, no outlier removal, no market mapping |

## 5. META audit tables

| Table | Grain | Purpose |
|---|---|---|
| `META.INGESTION_RUNS` | One row per dataset ingestion attempt | Status lifecycle `STARTED` → `SUCCEEDED` / `FAILED` / `BLOCKED` / `SKIPPED_IDENTICAL`. A `SUCCEEDED` run can later become `SUPERSEDED`, but only through a verified re-baseline (§6.1). Records the sanitized URL, snapshot name, SHA-256, bytes, source / parsed / rejected / RAW counts, git commit, error class and sanitized message |
| `META.INGESTION_CHECKS` | One row per check per run | Check type (ACQUISITION, SCHEMA, INTEGRITY, SOURCE_SPECIFIC, RECONCILIATION, IDEMPOTENCY), expected and actual values, PASS / WARN / FAIL |
| `META.INGESTION_REJECTED_ROWS` | One row per source record not loaded | Source row number, reason and original record text, so nothing is discarded silently |

All three tables are owned by AM_INGESTOR. AM_TRANSFORMER reads them through the Phase 2 future grants. They contain no secrets.

## 6. Checksum and idempotency strategy

- **Identical rerun:** if the same `source_id` + `dataset_id` + vintage + SHA-256 has already loaded successfully, the run is recorded as `SKIPPED_IDENTICAL` and RAW is not touched.
- **Same pin, different content:** the run is recorded as `BLOCKED` (`ChecksumDrift`), RAW is not touched, and the data needs review. A frozen vintage is never silently replaced.
- **Phase 1 pin:** PEP is also checked against the SHA-256 recorded in Phase 1 (`BF6FAD83…1852`).
- **Orphan protection:** before any load, rows in the target table from runs that never reached `SUCCEEDED` are deleted. A WARN check records this.
- **Failed reconciliation:** the run's own rows are deleted before it is marked `FAILED`.
- **Drift test:** `--simulate-drift` deliberately alters the computed checksum (labelled TEST ONLY in META) to show that drift is detected.
- **Snapshot preservation:** snapshots are held in memory until the run outcome is known.
  - SUCCEEDED or SKIPPED_IDENTICAL: written to the deterministic name.
  - FAILED or BLOCKED: written beside it as `<name>.rejected-<sha12>`.
  - A drifted retrieval therefore never overwrites the snapshot that was loaded. This was added after the first full rerun exposed the problem; see §6.1.

### 6.1 Real drift event and re-baseline (2026-10-05)

1. **The event.** The first full rerun reported real `ChecksumDrift` on S-04 (tract B01003). A value-by-value comparison of the new response with RAW showed **identical content**: the same 85,382 GEO_IDs and 0 value differences. Only the **row order** returned by the Census API had changed (first difference within Alaska). The rerun had also overwritten the local cached snapshot.
2. **Evidence restored.** The loaded snapshot was rebuilt from RAW in `_SOURCE_ROW_NUMBER` order. It reproduced the loaded SHA-256 **byte for byte** (`6E29FD71…`), which also shows that RAW is a lossless copy of the retrieval. The drifted retrieval is kept as `.rejected-1CEB9743A613`.
3. **Canonicalization (owner-approved).** All Census API snapshots (S-03, S-04) are now **sorted by GEO_ID before hashing**, so the checksum depends on content only. Byte-level drift detection still applies.
4. **Re-baseline mechanism.** `run_ingestion.py --datasets … --rebaseline "<reason>"` reloads a drifted dataset **only if** the new content's order-independent fingerprint equals the RAW rows already loaded. The sequence:
   - The new snapshot loads and reconciles first.
   - Only then is the prior run marked `SUPERSEDED` and its rows deleted.
   - If the content differs, it refuses and the run is `BLOCKED`.
   - It cannot be combined with `--all`.
5. **Result.** 5 API datasets were re-baselined: B01003, B19013, B25046 and B08013 (CBSA level) and S-04. The other 8 were already in GEO_ID order, so their canonical bytes matched and they were skipped. A further rerun of all 13 API datasets returned **13/13 SKIPPED_IDENTICAL**.

## 7. Roles and secret handling

- **Ingestion** runs as **AM_INGESTOR**, using an explicit role override on a connection whose default role is AM_ANALYST, with `USE SECONDARY ROLES NONE`. It wrote only to RAW and META. No grants were changed.
- **Validation** runs as **AM_TRANSFORMER**, which proves that the downstream role can read everything landed.
- **Census API key:** read from the environment only. It is never printed, logged, stored or committed.
  - The key is removed by value and as a `key=` parameter from every log record, audit field and error message.
  - URL-bearing `requests` errors are replaced with sanitized messages.
  - Third-party HTTP loggers are held at WARNING.
- **Verification:** a scan of every META text column for the key value or a `key=` parameter returned 0 rows.

## 8. Source-by-source status

| Source | Dataset → RAW table | Rows | Status | Notes |
|---|---|---:|---|---|
| S-01 | PEP V2025 → `CENSUS_PEP_CBSA_EST2025` | 2,806 | SUCCEEDED | Matches the Phase 1 SHA-256 and the frozen top 35 exactly |
| S-02 | Delineation Jul-2023 → `CENSUS_CBSA_DELINEATION_2023` | 1,915 | SUCCEEDED | 3 non-data rows rejected (1 blank, 2 source notes) |
| S-03 | ACS 5-yr 2024, 11 table groups → `CENSUS_ACS5_2024_CBSA_<table>` | 935 each | SUCCEEDED | Whole-table `group()` calls: estimates, MOEs and annotations |
| S-03 | ACS 5-yr 2024 S0801 subset → `CENSUS_ACS5_2024_CBSA_S0801_SUBSET` | 935 | SUCCEEDED | `S0801_C01_046E/M` only |
| S-04 | ACS 5-yr 2024 B01003 tracts → `CENSUS_ACS5_2024_TRACT_B01003` | 85,382 | SUCCEEDED | 52 state-level calls (incl. DC, PR) |
| S-05 | Gazetteer 2024 → `CENSUS_GAZETTEER_2024_{CBSA,COUNTIES,TRACTS}` | 935 / 3,222 / 85,396 | SUCCEEDED | Whitespace padding trimmed (WARN) |
| S-08 | CBP 2023 MSA → `CENSUS_CBP_2023_MSA` | 576,818 | SUCCEEDED | |
| S-09 | OEWS May 2025 MSA → `BLS_OEWS_MAY2025_MSA` | 150,023 | SUCCEEDED | Accessible with the descriptive User-Agent; MSA workbook only |
| S-12 | Normals annual/seasonal → `NOAA_NORMALS_1991_2020_ANNUALSEASONAL` | 15,616 | SUCCEEDED | `STATION` + full record as `VARIANT` (2,140 distinct source columns) |
| S-13 | Normals hourly → `NOAA_NORMALS_1991_2020_HOURLY_WIND` | 4,090,920 | SUCCEEDED | Wind projection, 38 of 113 columns (A-027) |
| S-17 | FAA CY2025 commercial service → `FAA_ENPLANEMENTS_CY2025_COMMERCIAL_SERVICE` | 516 | SUCCEEDED | 6 summary rows rejected; they reconcile to 516 |
| S-19 | NASR APT_BASE 2026-09-03 → `FAA_NASR_APT_BASE_20260903` | 19,411 | SUCCEEDED | Key `ARPT_ID`; `SITE_NO` repeat flagged (WARN) |
| S-21 (+S-22) | EPA SLD v3 layer 10 → `EPA_SLD_V3_BLOCK_GROUP` | 220,134 | SUCCEEDED | Attributes only; includes `NatWalkInd` (S-22); count reconciled to the service |

### Not ingested (deliberately)

| Source | Reason |
|---|---|
| S-07 TIGER shapes | GO crosswalk, deferred. Geometry is needed only for the open airport, station and airspace mapping decisions (A-007, A-009), and would add a GIS dependency. To be revisited when those decisions are made |
| S-22 National Walkability Index | Covered by S-21 (`NatWalkInd`). A separate copy would duplicate RAW |
| PROXY sources (S-06, S-10, S-11, S-14, S-18, S-23–S-25) | Not yet required by an approved feature, or tied to an open decision |
| DROP sources (S-15, S-16, S-20, S-26, S-27, S-34) | Dropped in Phase 1 |
| Regulatory evidence (S-28–S-33) | Requires manual, cited curation (schema in `data_sources.md` §7.4). Not automated, and no evidence file curated yet. **Deferred by owner decision** (`project_scope.md` §14) to a dedicated curation step after the dbt and feature-audit work, before Phase 7. May become a scored input only after the framework and measurement rules are finalized |
| Deployment evidence (S-35–S-39) | Manual curation (§8.3), same dedicated step. **External validation only, never a scoring input** |

### Audit totals at the end of Phase 3

**91** ingestion runs and **1,104** checks:

| Status | Runs | What they were |
|---:|---:|---|
| SUCCEEDED | 25 | The current loads, one per RAW table |
| SKIPPED_IDENTICAL | 52 | Reruns |
| SUPERSEDED | 5 | Re-baselined loads |
| FAILED | 7 | Development-time validation catches and one transient EPA 502. All were fixed and reloaded; none left rows behind |
| BLOCKED | 2 | One simulated drift test (labelled TEST ONLY) and the real S-04 order drift |

**9** rejected rows, every one with its reason:
- Delineation: 1 blank row and 2 note rows.
- FAA: 6 summary rows.

## 9. Differences from the Phase 1 research

These are recorded in `data_sources.md` §11:
- BLS was accessible.
- The FAA sheet contains 6 summary rows.
- NASR `SITE_NO` is not unique.
- The Gazetteer pads its values and writes positive longitudes with `+`.
- The hourly normals use a different column naming.
- The annual normals' columns vary by station.
- The EPA service returned transient 502 errors.
- The Census API's row order is not stable (§6.1).

## 10. What Phase 3 deliberately does not do

- Join sources, or map stations, airports, block groups, tracts or regulations to markets.
- Filter any source to the 35 markets. Presence checks for the 35 are validation only.
- Cast types, impute, trim outliers, normalize or engineer features. The only exceptions are the documented technical normalizations above.
- Create dbt models, or anything in STAGING, INTERMEDIATE, CORE or ANALYTICS.
- Score or rank anything.
