# dbt Transformation Layer (Phase 4)

**Status:** Phase 4 · **Last updated:** 2026-10-05 · **Build:** `dbt build` 388/388 PASS (1 seed, 51 models, 336 tests), 0 warnings

Phase 4 turns the source-aligned RAW tables into tested, documented warehouse structures that can be traced back to the source. It **prepares** the data that the open analytical decisions depend on, but it **does not make those decisions**. There are no features, scores, weights, rankings, clusters or simulations.

---

## 1. Architecture

```
RAW (Phase 3, 25 tables)           source('raw', ...)    META (audit) ── source('meta', ...)
   │                                                        │ reconciliation test
   ▼  25 views ─ STAGING     typing, renaming, documented sentinels → null + flag
   │
   ▼  11 tables ─ INTERMEDIATE   official crosswalks, market universe, one-to-one ACS join,
   │                             CANDIDATE station/airport relationships (no selection)
   ▼  14 tables ─ CORE        dim_market, dim_weather_station, dim_airport,
   │                          brg_market_county, brg_market_state, 9 facts at their native grain
   ▼  1 table ─ ANALYTICS     mart_market_feature_base (35 rows, CBSA-native measures only)
```

| Item | Value |
|---|---|
| dbt | dbt-core **1.12.5**, dbt-snowflake **1.12.1**, Python 3.13.16. 1.12 is the current stable line; 2.0 is a release candidate. Both packages declare Python 3.13 |
| Connector | snowflake-connector-python 4.7.5, inside dbt-snowflake's accepted range (≥4.2, <5) |
| Target | `AUTONOMOUS_MOBILITY` on `AM_EXPANSION_WH` |
| Role | **AM_TRANSFORMER**, set explicitly in the profile. The service user's default role (AM_ANALYST) is unchanged, and no grants were changed |
| Authentication | Key pair (`private_key_path` + `private_key_passphrase`, both read from environment variables) |
| Profile | `dbt/profiles.yml` is git-ignored. It's a copy of `dbt/profiles.example.yml` and contains only `env_var()` references. `scripts/run_dbt.py` loads `.env` and runs dbt |
| Schemas | The existing STAGING, INTERMEDIATE, CORE and ANALYTICS schemas. `macros/generate_schema_name.sql` uses each configured schema name as-is, so dbt never tries to create `STAGING_CORE` and similar. AM_TRANSFORMER has no CREATE SCHEMA, and none was granted |
| Grants | Not managed by dbt. All six schemas are managed-access, so access comes from the Phase 2 future grants: AM_ANALYST automatically reads CORE and ANALYTICS |
| Docs | `persist_docs` writes model and column descriptions into Snowflake comments. `dbt docs generate` builds the site in `dbt/target/` (git-ignored; regenerate with `python scripts/run_dbt.py docs generate`, then view with `python scripts/run_dbt.py docs serve`) |

## 2. Layers

### STAGING (views, one per RAW table)
- **Allowed:** snake_case renaming, trimming, blank → null, technical casting, and documented sentinels → null with an explicit flag column. Identifier representation is standardized (`cbsa_code`, `county_fips`, `tract_geoid`, `airport_code`, `station_id`), and lineage metadata is carried unchanged.
- **Not done:** joins, filters, market mapping or derived measures.
- **Exposed columns:** only the source columns catalogued in `data_sources.md`. RAW keeps everything.
- **Source codes handled:**
  - ACS negative codes: `-555555555` on 110 tract MOEs.
  - NOAA `-9999` (missing) and `-7777` (trace). These get *separate* flags, so missing stays distinguishable from trace.
  - OEWS `*`, `**` and `#`, kept in `*_marker` columns.
  - EPA `D4A -99999`, recorded as `d4a_no_transit_data`.
  - The FAA hub text `'None'` becomes null, with the original kept in `hub_type_published`.
- **Freshness:** **not configured.** Every source is a pinned vintage, so a freshness test would only report that a historical vintage is old. Re-acquisition is controlled by the Phase 3 checksum rules.

### INTERMEDIATE (tables)
- **Official, objective relationships only:**
  - county → CBSA (July 2023 delineation)
  - tract → county → CBSA
  - block group → county → CBSA (A-006)
- **The approved selection rule:** `int_market__universe_ranked`.
- **A one-to-one join of the 12 ACS tables** of the same dataset.
- **Candidate tables**, holding every market × station and every market × airport pair with great-circle distance to the CBSA's Gazetteer internal point. **No row is selected.** These exist so Phase 5 can evaluate the open rules (A-007, A-009) with data rather than guesses.

### CORE (tables)
Dimensions describe entities and facts hold measures. Every fact keeps its **native** grain. Anything that can't yet be legitimately stated at market level (weather, airports, block groups, tracts) stays at station, airport, block-group or tract level.

### ANALYTICS
`mart_market_feature_base` is **not** the readiness feature matrix. It exposes only measures that are **published natively at CBSA level**, so no aggregation choice is involved.

## 3. Dimensional model and grain

| Model | Type | Grain | Key | Main measures / attributes | Vintage |
|---|---|---|---|---|---|
| `dim_market` | Dimension | Market (35) | `market_id` (CBSA) | Name, 2025 population, selection rank, title states, county/state counts, land area | PEP V2025, July 2023 delineation, Gazetteer 2024 |
| `dim_weather_station` | Dimension | Station (15,656) | `station_id` | Name, coordinates, elevation, which products it has | Normals 1991–2020 |
| `dim_airport` | Dimension | NASR facility (19,411) | `airport_code` | Type, status, coordinates, published county name | NASR 2026-09-03 |
| `brg_market_county` | Bridge | Market × county (319) | `market_id, county_fips` | Central/outlying, county population, land area | PEP V2025, July 2023 |
| `brg_market_state` | Bridge | Market × state (51) | `market_id, state_fips` | State population and share (**observed; not a regulatory mapping**) | PEP V2025 |
| `fct_market_population_estimates` | Fact | Market × year (210) | `market_id, estimate_year` | Population (persons) | PEP V2025 |
| `fct_market_acs_demographics` | Fact | Market × ACS period (35) | `market_id` | Catalogued ACS counts, medians and minutes, each with MOE | ACS 5-yr 2020–2024 |
| `fct_market_business_patterns` | Fact | Market × NAICS code (57,791) | `market_id, naics_code` | Establishments, employment, payroll ($1,000), noise flags | CBP 2023 |
| `fct_market_occupation_wages` | Fact | Market × SOC code (24,338) | `market_id, occupation_code` | Employment, wage percentiles (USD), BLS markers | OEWS May 2025 |
| `fct_tract_population_land` | Fact | Tract in a market (38,579) | `tract_geoid` | Population (+ MOE), land and water area (sq mi). Inputs for density A-008 | ACS 2020–2024, Gazetteer 2024 |
| `fct_block_group_built_environment` | Fact | Block group in a market (98,029) | `block_group_geoid10` | D1B, D1C, D2A, D2B, D3B, D4A (+ no-transit flag), NatWalkInd | SLD v3.0 |
| `fct_station_climate_normals` | Fact | Station × normals period (15,616) | `station_id` | 11 annual elements, each with published / missing / trace / completeness / years | Normals 1991–2020 |
| `fct_station_hourly_wind_normals` | Fact | Station × hour (4,090,920) | `station_id, normal_hour_label` | Wind speed, direction and calm (units as published, to be confirmed) | Normals 1991–2020 |
| `fct_airport_enplanements` | Fact | Airport × CY2025 (516) | `airport_code` | Enplanements, hub type, service level | FAA CY2025 |
| `mart_market_feature_base` | Mart | Market (35) | `market_id` | CBSA-native candidate measures (82 columns) | Mixed (columns carry their vintage) |

**No `DIM_DATE`.** Every source is a single vintage. The one multi-year fact uses an integer `estimate_year`, in line with the Phase 1 decision.

## 4. DIM_MARKET design

- **Built from data:** `int_market__universe_ranked` applies the approved rule to the pinned PEP file: Metropolitan Statistical Areas only, ranked by `POPESTIMATE2025` descending, ranks 1–35. `rank()` is used, so a population tie would surface as a duplicate rank and fail the tests.
- **Proven against the contract:** the seed `frozen_market_universe.csv` is generated from the `project_scope.md` §6 table. `assert_dim_market_matches_frozen_seed` returns any difference in code, name, population or rank, and passes with 0. The dimension is never just a copy of the seed.
- **Pinned source:** `assert_pep_vintage_pinned` checks the vintage (V2025) and the Phase 1 SHA-256.
- **Descriptive attributes only.** `principal_state_usps` is the first state in the CBSA title. It describes the market and is **not** the state-to-market regulatory rule (A-012 open).

## 5. Test coverage by contract

| Model / area | Contracts protected |
|---|---|
| RAW sources (73 tests) | Key columns not null; unique where the source grain is unique; known LSAD values |
| Staging (all 25) | **Row-for-row with RAW and META** (singular test). Grain keys unique (single or composite). Identifier shapes (5-digit CBSA/county, 11-digit tract, 12-digit block group). Coordinates in range. Non-negative counts and plausible bounds. Accepted category values (CBSA type, central/outlying, noise flags, OEWS area type and markers, FAA service level and hub) |
| `dim_market` | Exactly 35 rows; `market_id` unique, not null, CBSA-shaped; rank unique within 1–35; population > 0; identical to the approved seed; PEP vintage and checksum pinned |
| Crosswalks | No row loss (`equal_row_count`); county keys exist in the official crosswalk; market counties equal the delineation's counties for the 35 markets |
| Bridges | Market and county/state grain unique; populations reconcile to market totals; shares sum to 1 (floating point) |
| Facts | Documented grain unique; `market_id` → `dim_market`, `station_id` → `dim_weather_station`, `airport_code` → `dim_airport`; 210 / 35 / 516 row counts; 8,760 hours per wind station; FAA hub counts equal the sheet's published subtotals; tract coverage gap limited to the known 14 Suffolk tracts |
| Mart | Exactly 35 rows, one per `dim_market` row; `market_id` unique and related |
| Phase boundary | `assert_no_scoring_in_phase4_outputs`: no score, weight, readiness, normalized, cluster or (non-source) rank column in CORE or ANALYTICS |

There are 327 generic and 9 singular tests. The count is a by-product; each test exists for one of the contracts above.

## 6. Lineage

`source()` is used only in staging, and in the two reconciliation tests that compare against RAW and META. Every downstream model uses `ref()`, giving lineage RAW → `stg_*` → `int_*` → `dim/brg/fct_*` → `mart_*`. No model hard-codes a relation name. The full graph is in the generated dbt docs.

## 7. Unresolved analytical decisions: prepared, not decided

| Decision | What Phase 4 provides | Deferred to |
|---|---|---|
| Weather station → market (A-007), missing snow (A-021) | `dim_weather_station`, station-level normals with published / missing / trace / completeness flags, `int_weather__station_market_candidates` (distances, no selection). Snow normals exist at 5,749 stations | Phase 5 |
| Airport → market (A-009), hub inflation (A-010) | `dim_airport`, `fct_airport_enplanements`, `int_airports__airport_market_candidates` (distances, state hint, no assignment). Point-in-polygon would need TIGER (S-07, deferred) | Phase 5 |
| Density definition (A-008) | `fct_tract_population_land` (population, MOE and land area per tract); Gazetteer CBSA land area in `dim_market`. No density computed | Phase 5–6 |
| Walkability / built-environment aggregation | `fct_block_group_built_environment` at block-group grain | Phase 5–6 |
| Multi-state regulation (A-012) | `brg_market_state` (observed shares only) | Evidence curation step → Phase 7 |
| Feature redundancy (A-014), ratios and per-capita measures | Raw counts and denominators in the mart | Phase 5 |
| Weights and scores (A-016) | Nothing (guarded by test) | Phase 7–8 |

## 8. Phase 3 warnings: disposition

| # | Phase 3 WARN | Disposition | Detail |
|---|---|---|---|
| 1 | S-02 delineation: 3 rejected rows | EXPECTED_SOURCE_LIMITATION | Blank and note rows, not counties. The delineation and PEP county sets match exactly (`assert_market_counties_match_delineation`) |
| 2 | S-05 Gazetteer CBSA: whitespace trimmed | RESOLVED_BY_DBT | Trimmed values cast cleanly; coordinates and areas typed and range-tested |
| 3 | S-05 Gazetteer counties: whitespace trimmed (+ `+179.62` longitude) | RESOLVED_BY_DBT | `try_to_double` parses the leading `+`; longitude range test passes |
| 4 | S-05 Gazetteer tracts: whitespace trimmed | RESOLVED_BY_DBT | As #2. **Plus a new related finding:** 14 Suffolk County tracts have no ACS record (A-029), tested |
| 5 | S-13 hourly normals: wind-only projection | EXPECTED_SOURCE_LIMITATION | A-027 stands. The `-9999` sentinels (6,746) are now null + `*_is_missing` (RESOLVED_BY_DBT for sentinel handling). The speed unit is to be confirmed in Phase 5 |
| 6 | S-17 FAA: 6 summary rows rejected | EXPECTED_SOURCE_LIMITATION | The airport fact reproduces the published hub subtotals exactly (tested) |
| 7 | S-19 NASR: `SITE_NO` repeat | EXPECTED_SOURCE_LIMITATION | `site_no` is documented as non-unique and has no uniqueness test. `airport_code` is the tested key |

None require a fix. All 7 remain recorded in META, and dbt doesn't hide any of them.

## 9. Phase 4 boundaries

- **Phase 4 created:** dbt project, source declarations, 25 staging views, 11 intermediate tables, 14 core tables, 1 mart, 1 seed, and 336 tests.
- **Phase 4 did not create:**
  - EDA or feature selection
  - ratios, indices or normalization
  - station, airport or density decisions
  - readiness scores, weights or rankings (other than the documented population-based selection rank)
  - clusters or simulations
  - deployment-based anything
  - Power BI
  - CI

## 10. Running it

```
copy dbt\profiles.example.yml dbt\profiles.yml    # once; holds only env_var() references (git-ignored)
python scripts/run_dbt.py debug                     # connection check (AM_TRANSFORMER)
python scripts/run_dbt.py build                     # seed + models + all tests
python scripts/run_dbt.py docs generate             # dbt docs into dbt/target/ (git-ignored)
```
