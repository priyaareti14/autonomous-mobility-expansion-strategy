# dbt Cross-Layer Reconciliation (Phase 4)

**Status:** Phase 4 · **Measured:** 2026-10-05, after a passing `dbt build` (388/388)

Row counts for every lineage path, RAW → STAGING → INTERMEDIATE → CORE / ANALYTICS. Every count change is explained, and no row is dropped silently.

**Enforced by tests, not only documented here:**

| Contract | Test |
|---|---|
| STAGING = RAW = META `raw_row_count`, for all 25 sources | `assert_staging_reconciles_to_raw_and_meta` |
| Crosswalks keep every input row | `equal_row_count` on the tract and block-group crosswalks |
| Fixed-size outputs (35 markets, 319 market counties, 210 population rows, 516 airports, 18,060 airport candidates, 935 ACS CBSAs) | `row_count_equals` |
| Market populations reconcile to county and state sums; state shares sum to 1 | `assert_market_population_reconciles` |
| FAA hub counts match the sheet's published subtotals | `assert_faa_hub_counts_match_published_subtotals` |
| Every market tract is kept, and the only ACS gap is the 14 known Suffolk County, NY tracts | `assert_tract_coverage_anomaly_is_known` |

## 1. RAW → STAGING (1:1 by design)

| RAW table | RAW | STAGING model | STAGING |
|---|---:|---|---:|
| CENSUS_PEP_CBSA_EST2025 | 2,806 | stg_census__pep_cbsa_est2025 | 2,806 |
| CENSUS_CBSA_DELINEATION_2023 | 1,915 | stg_census__cbsa_delineation_2023 | 1,915 |
| CENSUS_ACS5_2024_CBSA_* (12 tables) | 935 each | stg_census__acs5_2024_cbsa_* (12) | 935 each |
| CENSUS_ACS5_2024_TRACT_B01003 | 85,382 | stg_census__acs5_2024_tract_b01003 | 85,382 |
| CENSUS_GAZETTEER_2024_CBSA / COUNTIES / TRACTS | 935 / 3,222 / 85,396 | stg_census__gazetteer_2024_* | 935 / 3,222 / 85,396 |
| CENSUS_CBP_2023_MSA | 576,818 | stg_census__cbp_2023_msa | 576,818 |
| BLS_OEWS_MAY2025_MSA | 150,023 | stg_bls__oews_may2025_msa | 150,023 |
| NOAA_NORMALS_1991_2020_ANNUALSEASONAL | 15,616 | stg_noaa__normals_annualseasonal | 15,616 |
| NOAA_NORMALS_1991_2020_HOURLY_WIND | 4,090,920 | stg_noaa__normals_hourly_wind | 4,090,920 |
| FAA_ENPLANEMENTS_CY2025_COMMERCIAL_SERVICE | 516 | stg_faa__enplanements_cy2025 | 516 |
| FAA_NASR_APT_BASE_20260903 | 19,411 | stg_faa__nasr_apt_base | 19,411 |
| EPA_SLD_V3_BLOCK_GROUP | 220,134 | stg_epa__sld_v3_block_group | 220,134 |

Staging changes **values, not rows**. Documented source codes become null, and a flag is kept beside each one:

| Source | Code → null | Rows affected | Flag column |
|---|---|---:|---|
| ACS tract MOE | `-555555555` | 110 tracts | `*_moe_is_special_code` |
| NOAA hourly | `-9999` | 6,746 station-hours | `*_is_missing` |
| OEWS | `*`, `**`, `#` | — | `*_marker` |
| EPA SLD `D4A` | `-99999` | 125,941 block groups | `d4a_no_transit_data` |
| FAA hub | the text `'None'` | — | `hub_type_published` keeps the original |

## 2. STAGING → INTERMEDIATE

| Model | Input | Rows | Change and reason |
|---|---|---:|---|
| int_geo__county_cbsa_2023 | delineation 1,915 | 1,915 | None (1:1) |
| int_market__universe_ranked | PEP 2,806 | 35 | **Selection rule:** 387 MSA rows kept (micro, division and county rows excluded), then ranks 1–35 |
| int_market__counties | PEP county rows, 35 markets | 319 | County rows of the 35 markets only |
| int_market__state_population | 319 market counties | 51 | Grouped by market × state: 35 markets + 16 extra state memberships across the 11 multi-state markets |
| int_geo__tract_cbsa_2023 | Gazetteer tracts 85,396 | 85,396 | None. 79,399 tracts fall in a CBSA; 5,997 are outside every CBSA (`cbsa_code` null, kept) |
| int_geo__block_group_cbsa_2023 | SLD 220,134 | 220,134 | None. 200,564 map to a 2023 CBSA; 19,570 don't (rural block groups, plus 2,581 Connecticut block groups whose legacy county codes have no 2023 county: no project market is in CT). 10,180 carry an SLD CBSA that differs from 2023; 1,919 of those are in the 35 markets |
| int_acs__cbsa_measures | 12 ACS tables × 935 | 935 | One-to-one join on the CBSA code (same ACS dataset) |
| int_weather__stations | annual 15,616 + hourly 467 stations | 15,656 | Union: 427 hourly stations also have annual normals; 40 are hourly-only |
| int_weather__station_market_candidates | 35 × 15,656 | 547,960 | Cartesian **candidates** with distances, no selection (A-007) |
| int_airports__commercial_service | FAA 516 ⋈ NASR | 516 | All 516 match NASR on `airport_code` |
| int_airports__airport_market_candidates | 35 × 516 | 18,060 | Cartesian **candidates** with distances, no assignment (A-009) |

## 3. → CORE

| Model | Input | Rows | Change and reason |
|---|---|---:|---|
| dim_market | int_market__universe_ranked | 35 | None. Proven identical to the approved seed |
| brg_market_county | int_market__counties | 319 | None |
| brg_market_state | int_market__state_population | 51 | None |
| fct_market_population_estimates | 35 MSA rows × 6 years | 210 | Unpivot (wide years → rows) |
| fct_market_acs_demographics | int_acs__cbsa_measures 935 | 35 | Restricted to the market universe (900 non-project CBSAs excluded) |
| fct_market_business_patterns | CBP 576,818 | 57,791 | Restricted to the market universe; all NAICS levels kept |
| fct_market_occupation_wages | OEWS 150,023 | 24,338 | Restricted to the market universe; all occupations kept |
| fct_tract_population_land | tract crosswalk 85,396 | 38,579 | Tracts in the 35 markets. 14 have no ACS record (A-029); 65 have zero land area (both flagged, kept) |
| fct_block_group_built_environment | block-group crosswalk 220,134 | 98,029 | Block groups whose county is in a market (2023 delineation); all 35 markets present |
| dim_weather_station | int_weather__stations | 15,656 | None |
| fct_station_climate_normals | staging 15,616 | 15,616 | None |
| fct_station_hourly_wind_normals | staging 4,090,920 | 4,090,920 | None (8,760 hours × 467 stations, tested) |
| dim_airport | NASR 19,411 | 19,411 | None |
| fct_airport_enplanements | FAA 516 | 516 | None |

## 4. → ANALYTICS

| Model | Input | Rows | Note |
|---|---|---:|---|
| mart_market_feature_base | dim_market + CBSA-native facts | 35 | 82 columns. No imputation, and every gap is visible: the 53-3054 Taxi Drivers occupation is published for only 7 of the 35 markets (`oews_taxi_drivers_published = false` for 28). No other key candidate measure is null |

## 5. Rows not loaded upstream (Phase 3, kept in META)

There are 9 rejected source records:
- **Delineation:** 1 blank row and 2 note rows.
- **FAA:** 6 summary rows, which the hub-count test reproduces exactly.

They are in `META.INGESTION_REJECTED_ROWS` with reasons. Phase 4 drops no further rows: every reduction above is a documented selection, market restriction, grouping or unpivot.

## How to re-measure

```
python scripts/run_dbt.py build                # rebuilds and re-runs every reconciliation test
```
Row counts come from `INFORMATION_SCHEMA.TABLES.ROW_COUNT` (tables) or `COUNT(*)` (views).
