# Feature Engineering Reconciliation (Phase 6)

**Status:** Phase 6, in review · **Last updated:** 2026-10-05

This document traces every production feature to its RAW source, with counts for each mapping-sensitive step.

The counts come from `scripts/run_feature_qa.py` (`outputs/phase6/feature_reconciliation.csv`) and from dbt tests that fail if any count drifts. Earlier layers are covered by [dbt_reconciliation.md](dbt_reconciliation.md) (RAW → ANALYTICS row counts) and [ingestion_pipeline.md](ingestion_pipeline.md) (source → RAW).

## 1. Lineage by feature

All mode marts select from `INTERMEDIATE.int_market__production_features` (`ipf` below).

| Feature | RAW | STAGING | CORE (native grain) | INTERMEDIATE mapping | ANALYTICS |
|---|---|---|---|---|---|
| `population_2025_log1p` | CENSUS_PEP_CBSA_EST2025 | stg_census__pep_cbsa_est2025 | dim_market | ipf | all three mode marts |
| `pw_tract_density_log1p` | CENSUS_ACS5_2024_TRACT_B01003, CENSUS_GAZETTEER_2024_TRACTS, CENSUS_CBSA_DELINEATION_2023 | stg_census__acs5_2024_tract_b01003, stg_census__gazetteer_2024_tracts | fct_tract_population_land | int_market__population_weighted_density → ipf | robotaxi, sidewalk |
| `share_taxi_or_ride_hailing` | CENSUS_ACS5_2024_CBSA_B08301 | stg_census__acs5_2024_cbsa_b08301 | fct_market_acs_demographics | ipf | robotaxi |
| `enplanements_per_resident_log1p` | FAA_ENPLANEMENTS_CY2025_COMMERCIAL_SERVICE, FAA_NASR_APT_BASE_20260903, **CENSUS_GEOCODER_AIRPORT_COUNTY_ACS2024** | stg_faa__enplanements_cy2025, stg_faa__nasr_apt_base, stg_census__geocoder_airport_county_acs2024 | fct_airport_enplanements, dim_airport | int_airports__airport_market_assignment → int_market__airport_activity → ipf | robotaxi |
| `median_household_income_usd` | CENSUS_ACS5_2024_CBSA_B19013 | stg_census__acs5_2024_cbsa_b19013 | fct_market_acs_demographics | ipf | all three |
| `establishments_per_1k_pop`, `retail_establishments_per_10k_pop`, `restaurants_per_10k_pop` | CENSUS_CBP_2023_MSA | stg_census__cbp_2023_msa | fct_market_business_patterns | ipf | robotaxi; sidewalk and drone |
| `shuttle_chauffeur_median_annual_wage_usd`, `courier_median_annual_wage_usd` | BLS_OEWS_MAY2025_MSA | stg_bls__oews_may2025_msa | fct_market_occupation_wages | int_market__labor_cost → ipf | robotaxi; sidewalk and drone |
| `days_precip_ge_010_in`, `days_tmax_ge_90f`, `annual_snowfall_in` | NOAA_NORMALS_1991_2020_ANNUALSEASONAL, **NOAA_HOMR_EMSHR_LITE_202609** (station class) | stg_noaa__normals_annualseasonal, stg_noaa__homr_emshr_lite_202609 | fct_station_climate_normals, dim_weather_station | int_weather__station_class → int_weather__station_qualification → int_weather__market_station_selection → int_market__climate → ipf | all three |
| `annual_mean_wind_mph` | NOAA_NORMALS_1991_2020_HOURLY_WIND | stg_noaa__normals_hourly_wind | fct_station_hourly_wind_normals | int_weather__station_wind_summary → int_market__climate → ipf | drone |
| `population_weighted_walkability` | EPA_SLD_V3_BLOCK_GROUP | stg_epa__sld_v3_block_group | fct_block_group_built_environment | int_market__walkability → ipf | sidewalk |
| `share_single_family_detached` | CENSUS_ACS5_2024_CBSA_B25024 | stg_census__acs5_2024_cbsa_b25024 | fct_market_acs_demographics | ipf | drone |

Every model above sits in one dbt DAG (`source()` / `ref()` only), so `dbt docs` shows the same lineage graphically.

## 2. Mapping-sensitive counts

### 2.1 Density (D2)

| Measure | Count |
|---|---|
| Tracts in the 35 markets (Gazetteer 2024, July 2023 delineation) | 38,579 |
| Tracts with an ACS 2020–2024 population | 38,565 |
| Tracts without ACS population (14 Suffolk County, NY; A-029) | 14 |
| Zero-land-area tracts excluded (all with zero population) | 65 |
| **Tracts used in D2** | **38,500** |
| Tract population used | 162,717,360 |
| ACS CBSA population, 35 markets | 162,794,939 |
| Difference (the 14 Suffolk tracts, not imputed) | 77,579 |
| Population coverage: New York / every other market | 99.61% / 100% |

38,579 − 14 − 65 = 38,500, and 162,794,939 − 162,717,360 = 77,579. Both reconcile exactly.

### 2.2 Weather (W5)

| Measure | Count |
|---|---|
| Stations considered per market (any normals product, with coordinates) | 15,656 |
| Core-qualifying stations (5 core elements, flags S/R) | 3,376 |
| Snow-qualifying stations (flags S/P) | 5,749 |
| Hourly-wind stations | 467 |
| Stations classified PLCD by NOAA HOMR on 2020-12-31 (S-41) | 269 |
| Core-qualifying PLCD stations | 265 |
| Core-qualifying WBAN-numbered (`USW`) stations that are not PLCD | 207 |
| Normals stations without an EMSHR record (treated as not PLCD) | 38 |
| Station selections (35 markets × 3 roles) | 105 |
| Climate station: PLCD ≤ 25 km / any-network fallback | 30 / 5 |
| Snow station: same as climate / fallback ≤ 50 km / not published | 30 / 5 / 0 |
| Wind station > 25 km (Austin 81.8, Miami 34.4) | 2 |
| Selections identical to the Phase 5 W5 evaluation (which used the `USW` prefix) | 99 of 105. Changed: Cincinnati climate + snow, Sacramento climate + snow (stations); Denver and Kansas City climate (rule label only) |

### 2.3 Airports (A1)

| Measure | Count |
|---|---|
| FAA CY2025 commercial-service airports | 516 |
| Airports with an official county from the Census Geocoder (S-40) | 516 |
| Airports inside a frozen market | 67 |
| Enplanements at those airports | 772,732,731 |
| Enplanements summed over the 35 markets | 772,732,731 (reconciles; no double counting) |
| In-market airports whose NASR county name differs from the official county | 5: ATL (Fulton vs Clayton) and PHL (Philadelphia vs Delaware) differ in county; STL, BLV and MIA differ in spelling only |
| Phase 5 A1 airport lists reproduced | 35 of 35 markets |

### 2.4 Walkability (NW1)

| Measure | Count |
|---|---|
| SLD v3.0 block groups in the markets (county FIPS bridge) | 98,029 |
| Used (index published, population > 0) | 97,740 |
| Zero population | 289 |
| Populated block groups missing the index | 0 |
| SLD population covered | 100% |
| Block groups whose own SLD CBSA field disagrees with 2023 (field not used) | 1,919 |

## 3. Reproduction of Phase 5 values

| Measure | Max relative difference, Phase 6 dbt vs Phase 5 Python | Note |
|---|---|---|
| D2 density, D3 diagnostic | 2e-8 | Floating point |
| Precipitation days, heat days, snowfall | 0 for 33 markets | Cincinnati and Sacramento changed with the PLCD correction (production_feature_layer.md §5.2) |
| Mean wind, walkability, enplanements per resident | ≤ 1.5e-4 | The Phase 5 CSVs were rounded to 3–4 decimals |
| A1 airport lists | identical | |
| A4 diagnostic lists | 1 market differs (Minneapolis adds STC) | Phase 6 follows the documented A4 rule (production_feature_layer.md §5.3) |

## 4. Earlier layers after Phase 6

| Check | Result |
|---|---|
| `dbt build` | 590 / 590 PASS: 2 seeds, 69 models, 519 tests (Phase 4: 388) |
| RAW validation | 19 PASS, 8 WARN, 0 FAIL across 27 datasets. 7 WARNs are the unchanged Phase 3 ones; the 8th is S-41's documented malformed Svalbard record. S-40 PASS |
| Staging ↔ RAW ↔ META reconciliation | PASS for all 27 RAW tables, S-40 and S-41 included |
| Snowflake connection validation | 45 / 45 |
| Phase 5 feature audit rerun | 35 markets, 70 candidates, same decisions. `feature_audit.csv` byte-identical (SHA-256 `3CC26A6C…7DAF`) |
