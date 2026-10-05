# Mapping Methodology: Evaluation of Candidate Methods (Phase 5)

**Status:** Phase 5, in review · **Last updated:** 2026-10-05

This document compares candidate methods for turning sub-market or point data into one value per market (CBSA). It covers four measures: density, weather stations, airports and walkability. For each one it states the recommended method, why, and the rejected alternatives.

The recommendations are **pending approval**. Nothing here is a score, weight or ranking, and nothing has been written to Snowflake. Phase 6 implements the approved methods in dbt or Python.

**Reproduce:** `python scripts/run_feature_audit.py` (read-only, role AM_TRANSFORMER).
**Code:** [src/analytics/mapping_evaluation.py](../src/analytics/mapping_evaluation.py).
**Evidence files:** `outputs/density_methods.csv`, `weather_station_methods.csv`, `airport_methods.csv`, `airport_county_match.csv`, `walkability_methods.csv` and `mapping_diagnostics.csv`.

All rank correlations below are Spearman ρ across the 35 markets.

---

## 1. Population density (A-008)

**Inputs:**
- ACS 2020–2024 tract population (S-04)
- Gazetteer 2024 tract land area (S-05)
- EPA SLD block-group population and land area (S-21, 2018 inputs)
- the July 2023 county-to-CBSA delineation (S-02)

| Method | Definition | ρ with D2 | Verdict |
|---|---|---|---|
| D1 Raw MSA density | CBSA population ÷ CBSA land area | 0.565 | **Rejected.** Large rural counties dominate it. Riverside's raw density is 175/sq mi, but its typical resident lives at about 4,650/sq mi (×26.6). Las Vegas ×22.9, Denver ×14.5, Phoenix ×13.4, Portland ×13.1 |
| **D2 Population-weighted tract density** | Σ(tract pop × tract density) ÷ Σ tract pop, over tracts with an ACS population and land > 0 | — | **Recommended.** It measures the density the average resident experiences. Uses current tracts and the pinned ACS vintage |
| D3 Population-weighted block-group density | Same formula using SLD 2018 `TotPop` / `Ac_Land` × 640 | 0.990 | **Backup.** Finer grain, but its inputs are from 2018 and use 2010-based block groups (A-013) |
| D4 Central-county density | Density of the county containing the principal city | 0.398 | **Rejected.** It equals raw density for one- and two-county metros, and its value depends on where county lines happen to fall |
| D5 Share of population in tracts ≥ 2,500 / 5,000 / 10,000 per sq mi | Threshold shares | 0.948 (≥ 5,000) | **Sensitivity alternative.** The thresholds are arbitrary, so it is not the primary measure |
| `share_pop_tracts_lt_1000` | Share of population in tracts below 1,000 per sq mi | — | Kept as a separate **drone** candidate (low-density suburban fit). Its threshold must be justified in Phase 6 |

**D2 summary:**
- Median 4,638 per sq mi. The range runs from 1,934 to 32,301 (New York).
- 38,500 tracts used across the 35 markets.
- 65 tracts excluded because their land area is zero (water-only tracts).
- 14 excluded because they have no ACS record (see §1.1).
- D2 is right-skewed, so a log transform (LOG1P) is suggested for Phase 6.

### 1.1 Suffolk County, NY tract gap (A-029)

The cause has been corrected from the Phase 4 note. **This is not a tract revision.**
- Every Gazetteer vintage from 2020 to 2024 lists 385 Suffolk tracts, including the 14 in question.
- The ACS 5-year 2018–2022 tract tables also have 385. The 2019–2023 and 2020–2024 releases have 371.
- The neighbouring tracts did not absorb the missing population, so the tracts were not merged.
- The ACS 2020–2024 county total (1,530,146) and CBSA 35620 total (19,798,537) **do** include these people. Only the tract-level tables omit them.
- In the 2018–2022 tables, the 14 tracts held 77,579 people on 13.2 sq mi.
- Census has not published an explanation. The cause is recorded as **not officially established**.

**Impact:**
- Only the New York market is affected.
- NY D2 is 32,301 without the 14 tracts. Adding them back with their 2018–2022 populations, as a sensitivity check only, gives 32,203 (−0.31%).
- NY ranks first on D2 either way.

**Recommendation:** exclude the 14 tracts with disclosure. Do not impute them. The `has_acs_population = false` flag and the Phase 4 test already isolate them. CBSA-level counts are unaffected because they come from CBSA-level tables.

---

## 2. Weather station rule (A-007, A-021)

**Inputs:**
- NOAA annual/seasonal normals 1991–2020 (S-12): 15,616 stations
- hourly normals (S-13): 467 stations
- the CBSA internal point and population-weighted (PW) centroid from tract internal points

**Core elements:**
- annual precipitation
- days with precipitation ≥ 0.10 in
- days with Tmax ≥ 90 °F
- days with Tmin ≤ 32 °F
- annual mean temperature

**Qualifying station:** every core element is published, with completeness flag **S** or **R**. These are NCEI's "filled" normals:
- S (Standard) = at least 24 years of data
- R (Representative) = at least 10 years

Flag P (Provisional, at least 10 years, unfilled) and flag E (Estimated) do not qualify for the core elements.

**Snow rule:** snow qualifies with flag **S or P**.
- The archive has 4,970 P-flag and 779 S-flag snow normals, and no R flags.
- Requiring S/R would have rejected the published snow normals at Atlanta, Nashville, Seattle, Miami and Riverside.
- A blank snow value is **missing, not zero** (A-021).

| Rule | Definition | Result | Verdict |
|---|---|---|---|
| W1 | Nearest station of any kind to the CBSA internal point | Only **10 of 35** nearest stations are core-complete | **Rejected** |
| W2 | Nearest qualifying station to the PW centroid | Complete. In 7 markets it picks a cooperative station over a qualifying first-order station only 0.2–13.2 km farther (median 9.8 km). In the other 28 it matches W5 | Not preferred. Sensitivity variant |
| W3 | Nearest qualifying first-order (`USW`) station to the PW centroid, no distance cap | Riverside 88.0 km (Long Beach), Miami 33.5 km, Detroit 32.2 km | **Rejected** as the only rule |
| W4 | Mean of qualifying stations within 50 km | Mixes climates. Riverside heat days differ by 73 days across its stations; Las Vegas freeze days by 62 | **Rejected** |
| **W5 Hybrid** | First-order station ≤ 25 km from the PW centroid. Otherwise the nearest qualifying station (any network) | 32 of 35 markets get a first-order station (median 11.1 km, max 24.5 km Atlanta). Detroit (20.8 km), Miami (4.0 km) and Riverside (6.1 km) use cooperative stations | **Recommended** |

**Why W5 prefers first-order stations:** first-order (`USW`) stations belong to the primary NWS/FAA observing network, mostly airport ASOS sites with standardized instruments. They usually host the hourly wind normals too, so one station can supply every element. The 25 km cap stops a distant airport from standing in for a metro, which is the W3 failure.

**W5 snow:**
- If the W5 station's snow normal qualifies, use it (30 markets).
- Otherwise use the nearest qualifying snow station within 50 km. This applies to 5 markets, all within 16.7 km: Cincinnati, Los Angeles, Phoenix, San Diego and San Francisco.
- Otherwise the value is `SOURCE_NOT_PUBLISHED`. This case did not occur, so snow is resolved for 35 of 35 markets.

**W5 wind:**
- Wind comes from the nearest hourly-normals station to the PW centroid. The median distance is 11.1 km.
- **Flags:** Austin is 81.8 km away (USW00003902), and Miami is 34.4 km away.
- Annual mean wind ranges from 4.9 to 11.3 mph (median 8.05).
- 11 station-hours are missing in total.

**Wind unit:** confirmed as **mph** (closes the A-027 note).
- NCEI's hourly-normals documentation (Normals_HLY_Documentation §III.A) gives wind speed in miles per hour, or metres per second for metric output, to the nearest tenth.
- The landed values match NCEI's standard-output sample file 120 of 120.
- Direction codes run 1 = N … 8 = NW, and -9999 means missing.
- Oddity: the sample file reports pressure in hPa, so standard output is not imperial for every element. This doesn't affect wind.

**Limitations:**
- A single station is still a point, not a metro.
- W5 picks the station nearest the population centre, which is not necessarily representative of a large CBSA (Riverside spans desert and coast).
- Station choice is an A-007 sensitivity input for Phase 8.

---

## 3. Airport activity (A-009, A-010)

**Inputs:**
- FAA CY2025 enplanements (S-17): 516 airports
- NASR airport locations and county names (S-19)
- Gazetteer 2024 county FIPS (S-05)

**County matching:**
- Airports are assigned to counties by matching NASR county name + state against Gazetteer county names.
- The matching normalizes several patterns: suffixes, "SAINT" → "ST", "MC LEAN" → "MCLEAN", Dade → Miami-Dade, and Virginia independent cities.
- Result: 488 of 516 matched. The 28 unmatched are in territories, Connecticut planning regions or Alaska boroughs, none of which are in a project market.
- This is name matching, not the point-in-polygon method A-009 assumed. CBSA polygons are not in RAW. It is recorded as a limitation.

| Method | Definition | ρ with A1 (per capita) | Verdict |
|---|---|---|---|
| **A1 Inside-CBSA** | Enplanements at commercial-service airports in the CBSA's counties | — | **Recommended** |
| A2 Within 80 km | Every airport within 80 km of the PW centroid | 0.970 | **Rejected.** Double-counts: BWI counts for both Baltimore and Washington, ONT for both Los Angeles and Riverside, SNA for both Los Angeles and Riverside, and DCA for both Washington and Baltimore |
| A3 Large/medium hubs inside | A1 restricted to FAA hub type L/M | — | Diagnostic only |
| A4 Nearest market within 80 km | Each airport goes to one market: the one it is inside, otherwise the nearest market within 80 km. No double counting | 0.994 | **Sensitivity variant** |

**Edge cases from the brief:**
- **BWI** is in Anne Arundel County, inside **Baltimore** (12580). Under A1 it counts for Baltimore only.
- **ONT** is in San Bernardino County, inside **Riverside** (40140), not Los Angeles.
- **MHT** (Hillsborough, NH) and **ORH** (Worcester, MA) are outside every market. A4 assigns them to Boston.
- **PVD** (Kent, RI) is outside every market and more than 80 km from any PW centroid, so it is excluded under every method.
- **SJC** (Santa Clara) is in the San Jose CBSA, which is outside the universe (A-001). A4 assigns it to San Francisco.

**Per capita:**
- A1 enplanements per resident have ρ 0.306 with population, so per capita removes most of the size effect.
- The top values reflect connecting hubs and tourism: Denver 12.9, Las Vegas 11.0, Orlando 10.0, Charlotte 8.9, Atlanta 7.9.
- FAA data can't separate local from connecting passengers (A-010), so the feature is MODIFY with a hub caveat.
- The lowest value is Riverside at 1.08, because the large LA airports are outside it.

---

## 4. Walkability aggregation (A-013)

**Input:** the EPA National Walkability Index (NWI, 1–20) for 98,029 block groups in the 35 markets. It is mapped to markets through 2023 county FIPS, not the SLD's own CBSA field (A-006). 1,919 block groups carry a different CBSA code in that field.

| Method | Definition | ρ with NW1 |
|---|---|---|
| **NW1 Population-weighted mean** | Σ(NWI × pop) ÷ Σ pop | — |
| NW2 Simple mean | Unweighted block-group mean | 0.986 |
| NW3 Median | Unweighted median | 0.977 |
| NW4 Population-weighted median | | 0.988 |
| NW5 Share of population with NWI ≥ 15.26 ("most walkable") | EPA class break | 0.912 |
| NW6 Share of population with NWI ≥ 10.51 ("above average") | EPA class break | 0.990 |
| NW7 Central-county population-weighted mean | | 0.980 |
| D3B Population-weighted intersection density | SLD street-network input | 0.878 |

**Recommendation:** NW1, the population-weighted mean. It measures the environment the typical resident lives in, which matters for sidewalk delivery. Every method agrees closely (ρ ≥ 0.91), so the choice barely changes rank order. The simple mean exceeds the population-weighted mean by 0.02–0.72 points in every market.

**Limitations:**
- **Transit penalty.** EPA codes block groups without transit data as `D4A = -99999`, and they get the lowest transit rank inside the NWI. These block groups hold a median **45%** of residents per market (range 15.6%–79.5%). NWI therefore partly measures transit-data coverage. This is a new limitation (A-031).
- The index is relative, uses 2017–2020 inputs and doesn't measure sidewalks directly (A-013).
- NW1 has ρ 0.883 with population-weighted density (D2), so the two partly overlap within URBAN_FORM. This is handled in Phase 6.

---

## 5. Labor-cost mapping (A-026)

Wages come straight from BLS OEWS May 2025 at MSA grain, so no geographic mapping is needed. The choice is which occupation to use:

| Occupation | Markets published | Use |
|---|---|---|
| 53-3054 Taxi Drivers | **7 of 35** | **DROP** as a feature (too missing; ρ −0.28 with the 53-3053 shuttle wage on n = 7). Context only |
| 53-3053 Shuttle Drivers and Chauffeurs | 35 of 35 | **Robotaxi** labor-cost candidate |
| 43-5021 Couriers and Messengers | 35 of 35 | **Sidewalk/drone** labor-cost candidate. Least redundant with income (ρ 0.63) |
| 53-3033 Light Truck Drivers | 35 of 35 | DEFER (redundant with 43-5021) |
| 53-0000 Transportation occupations (all) | 35 of 35 | DEFER (broad group) |

Median household income has ρ 0.77–0.85 with these wage series. Phase 6 must not count income and labor cost as independent signals without checking.

---

## 6. Summary of recommendations (pending approval)

| Measure | Recommended | Sensitivity alternative | Assumption |
|---|---|---|---|
| Density | D2 population-weighted tract density, Suffolk 14 tracts excluded with disclosure | D3 block group; D5 ≥ 5,000 share | A-008, A-029 |
| Weather | W5 hybrid station rule, snow S/P with 50 km fallback | W2; W3 | A-007, A-021 |
| Wind | Nearest hourly station, in mph | p90 hourly mean | A-027 |
| Airports | A1 inside-CBSA enplanements per capita (hub caveat) | A4 nearest-market 80 km | A-009, A-010 |
| Walkability | NW1 population-weighted mean | NW5 share most walkable | A-013, A-031 |
| Labor cost | 53-3053 (robotaxi); 43-5021 (delivery) | 53-3033 | A-026 |
