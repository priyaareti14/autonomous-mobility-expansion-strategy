# Production Feature Layer (Phase 6)

**Status:** Phase 6, in review · **Last updated:** 2026-10-05

## 1. Purpose

This phase answers one question: *what exact, defensible, reproducible feature values will the later readiness model consume?*

It turns the approved Phase 5 decisions into tested dbt models in Snowflake, and it freezes a **pre-regulatory** feature set for each mode.

**Hard boundaries:**
- No scores, component scores, weights, rankings, normalization, sensitivity runs or cluster labels.
- No deployment evidence.
- Regulatory features are pending the Phase 6.5 curation step.

Related documents:
- [feature_redundancy_resolution.md](feature_redundancy_resolution.md): which signal represents each concept
- [feature_engineering_reconciliation.md](feature_engineering_reconciliation.md): lineage and counts
- [regulatory_handoff.md](regulatory_handoff.md): the data contract for Phase 6.5
- [mapping_methodology.md](mapping_methodology.md): the Phase 5 method evaluation

**Reproduce:**

```
python scripts/build_feature_contract.py    # freeze Phase 5, build the contract seed + crosswalk
python scripts/run_dbt.py build             # 590 nodes: seeds, models, tests
python scripts/run_feature_qa.py            # feature QA, final correlations, reconciliation counts
```

## 2. Frozen Phase 5 decision table (Step 1)

`outputs/feature_audit.csv` is the approved Phase 5 artifact, committed in `6e40d2b`.

| Check | Result |
|---|---|
| SHA-256 | `3CC26A6C01CEB3D630070F7386C8A2A43355A382C3D4EB8899F09E3BC9517DAF` |
| Unchanged since commit `6e40d2b` | Yes (`git diff` empty) |
| 70 unique features, each with a decision, reason codes and rationale | PASS |
| Mode statuses each sum to 70 | PASS. Robotaxi 9 KEEP / 3 MODIFY / 14 DEFER / 44 DROP; sidewalk 11 / 3 / 20 / 36; drone 10 / 6 / 12 / 42 |
| Overall decision consistent with the mode statuses | PASS |

`scripts/build_feature_contract.py` stops if the checksum or any rule changes. The result is recorded in `outputs/phase6/phase5_decision_freeze.json`.

**Every Phase 5 feature × mode pair (210) has a recorded disposition** in `outputs/phase6/phase5_to_phase6_crosswalk.csv`:

| Disposition | Pairs |
|---|---|
| ACTIVE | 30 |
| REPRESENTED_BY_INTENSITY_FORM (absolute count → its per-capita form) | 21 |
| DIAGNOSTIC | 3 |
| DEFERRED | 34 |
| DROPPED (Phase 6) | 2 |
| DROPPED_IN_PHASE5 | 120 |

### 2.1 Decision changes (explicit, not silent)

| Feature | Mode | OLD_DECISION | NEW_DECISION | REASON |
|---|---|---|---|---|
| `establishments_per_1k_pop` | Sidewalk | KEEP | DIAGNOSTIC | Retail and restaurant establishments are *subsets* of all establishments. Keeping all three would put mathematically nested counts in the delivery demand signal. The two delivery-specific measures are kept |
| `establishments_per_1k_pop` | Drone | KEEP | DIAGNOSTIC | Same reason |
| `share_pop_tracts_lt_1000` | Drone | MODIFY | DROPPED | No operational or literature basis for a drone density threshold (§6.8). The continuous `share_single_family_detached` represents the concept |

Every other KEEP or MODIFY was implemented as decided. A MODIFY on an absolute count meant "use its per-capita form", and that is what was done.

## 3. Architecture and lineage

```
RAW (Phase 3, + S-40 and S-41 in Phase 6)
 → STAGING (1:1 typed views)
 → CORE native-grain facts (tracts, block groups, stations, airports, wages, ACS, CBP)
 → INTERMEDIATE.features   mapping and feature engineering (one model per approved method)
 → ANALYTICS               MART_ROBOTAXI_FEATURES · MART_SIDEWALK_DELIVERY_FEATURES ·
                           MART_DRONE_DELIVERY_FEATURES · DIM_FEATURE
```

| Model | Grain | Purpose |
|---|---|---|
| `int_market__population_center` | market | Population-weighted centre (reference point for W5 and A4) |
| `int_market__population_weighted_density` | market | D2 density, coverage counts, A-029 flag, D1 and D3 diagnostics |
| `int_weather__station_qualification` | station | W5 definitions applied to every station |
| `int_weather__market_station_selection` | market × station role | W5 selection with rule, distance and completeness flag |
| `int_weather__station_wind_summary` | hourly station | Mean wind (mph) and the labelled p90 diagnostic |
| `int_market__climate` | market | Climate features with station lineage |
| `int_airports__airport_market_assignment` | airport | A1 on official county FIPS; A4 diagnostic |
| `int_market__airport_activity` | market | A1 enplanements per resident, airport counts and codes |
| `int_market__walkability` | market | NW1 and the A-031 field |
| `int_market__labor_cost` | market | 53-3053 and 43-5021 wages |
| `int_market__production_features` | market | Every production value plus QA; the marts select from it |
| `feature_contract` (seed) → `DIM_FEATURE` | feature × mode | Machine-readable contract and dictionary |

**Rule constants** live once, in `dbt_project.yml` `vars`:
- `w5_plcd_max_km: 25`
- `w5_station_class_as_of: 2020-12-31`
- `w5_snow_fallback_max_km: 50`
- `w5_core_flags: [S, R]`
- `w5_snow_flags: [S, P]`
- `a4_radius_km: 80`

The models and the tests read the same values.

**Feature contract location.** The brief suggested `config/feature_contract.csv`. I put the contract at `dbt/seeds/feature_contract.csv` instead, because a seed is version-controlled *and* loaded into Snowflake. That lets dbt tests enforce it against the marts.

## 4. Controlled source extension: S-40 (Census Geocoder)

**Why it was needed.** A1 needs each airport's county. NASR APT_BASE publishes the county only as a **name** plus state; it has no FIPS code. Phase 5 matched names (A-032). The brief ranks the options: county FIPS, then a validated state + county identifier, then a coordinate-to-county relationship, then a name match as a last resort. NASR offers neither of the first two, so Phase 6 uses option 3.

**Source:**
- U.S. Census Bureau Geocoder, `geographies/coordinates`
- benchmark `Public_AR_Current`, vintage **`ACS2024_Current`**: the same county boundaries as Gazetteer 2024
- no API key

**Input:** each FAA commercial-service airport's NASR reference point. The coordinates are read from the **pinned** Phase 3 snapshots, S-17 and S-19, whose SHA-256 values are verified before any request is sent. Only public airport coordinates leave the machine.

**Ingestion framework:**
- registry entry `census_geocoder_airport_county_acs2024`
- extractor `src/ingestion/sources/census_geocoder.py`
- RAW `CENSUS_GEOCODER_AIRPORT_COUNTY_ACS2024`
- META run and checks
- snapshot checksum
- dbt source, staging and tests
- staging ↔ RAW ↔ META reconciliation

The snapshot drops the service's internal object IDs, so an unchanged answer always produces the same checksum.

**Result:**
- 516 of 516 airports returned exactly one county (0 warnings).
- A second run was `SKIPPED_IDENTICAL`, so the answers are deterministic.
- The 28 airports the name match had missed (territories, Alaska, Connecticut planning regions) now resolve.

**What it changed.** Compared with the Phase 5 name match, 6 airports were in a different county. NASR's county name is the airport's *associated* county, not the county containing its reference point.
- **ATL** is physically in **Clayton** County, not Fulton.
- **PHL** is in **Delaware** County, not Philadelphia.
- GSP, SRQ, ROA and AKP: outside the universe.

**No project-market assignment changed**, because ATL and PHL stay inside their markets. Inside the 35 markets, only ATL and PHL differ in county; STL, BLV and MIA differ only in spelling.

**Limitation.** The NASR reference point is a single point. An airport whose land spans two counties is placed in the county containing that point; DFW, for example, is placed in Tarrant. That can't move an airport between markets unless the county line is also a CBSA line. No project airport is in that position.

## 4a. Controlled source extension: S-41 (NOAA HOMR station class)

**Why it was needed.** W5 prefers a "first-order" station, and the first implementation took that class from the identifier prefix `USW`. NOAA's GHCN-Daily readme (§IV, the station-ID format) defines the third character as "a network code that identifies the **station numbering system** used", and `W` as "WBAN identification number". So `USW` only means a U.S. station numbered by WBAN. It is a numbering system, not a station class, and it was not used further.

**Authoritative classification.** NOAA NCEI's Historical Observing Metadata Repository (HOMR) publishes the Enhanced Master Station History Report (EMSHR).
- Its field `TYPE` is the "station type and/or platforms station participates in", per history period.
- Reference Table B of `MSHR_Enhanced_Lite_Table.txt` defines **`PLCD` = "Primary Local Climatological Data"**, separately from `ASOS`, `AWOS`, `AIRWAYS`, `COOP` and `MILITARY`.
- None of HOMR's documentation files uses the phrase "First Order". This project therefore says **PLCD** and does not claim First Order status.

**Source and pinning.**
- `https://www.ncei.noaa.gov/access/homr/file/emshr_lite.txt.zip`, edition **202609** (zip member `emshr_lite_202609.txt`).
- Landed through the ingestion framework: registry `noaa_homr_emshr_lite_202609`, extractor `src/ingestion/sources/noaa_homr.py`, RAW `NOAA_HOMR_EMSHR_LITE_202609`, META, checksum, dbt source / staging / tests / reconciliation.
- 311,054 records, 0 rejected. 2 WARNs come from one Svalbard record whose name holds a line break.
- The rerun was `SKIPPED_IDENTICAL`. Because NCEI republishes the file in place, the run fails if the edition changes.

**Class date.** HOMR first records PLCD in periods beginning 2017-10-01. W5 takes the class in the period containing **2020-12-31**, the last day of the 1991–2020 normals (var `w5_station_class_as_of`).
- Every market selects the same station whether the class is taken on that date or as "PLCD at any point in 1991–2020".
- Taking the *current* class would change one market, Los Angeles: Civic Center (USW00093134) lost PLCD in May 2024. That is recorded as a sensitivity (A-041).

**Effect** (`int_weather__station_class`):
- 269 normals stations are PLCD, of which 265 are core-qualifying.
- **207 core-qualifying `USW` stations are not PLCD**, so the prefix rule had treated many non-PLCD stations as preferred.
- 38 normals stations have no EMSHR record; none is near a market centre, and they are treated as not PLCD.

## 5. Approved methods as implemented

### 5.1 D2 population-weighted tract density (A-008)

```
d_i = p_i / a_i                    tract density, persons per sq mi
D2  = Σ p_i · d_i  /  Σ p_i         over tracts with an ACS population and land area > 0
```

| Element | Definition |
|---|---|
| Numerator | Σ of tract population × tract density |
| Denominator | Σ of tract population |
| p_i | ACS 2020–2024 5-year B01003_001E, tract (S-04) |
| a_i | Gazetteer 2024 `ALAND_SQMI` (S-05) |
| Tract → market | Official tract → county → CBSA, July 2023 delineation |
| Zero land area | 65 water-only tracts excluded (density undefined). None holds ACS population (tested) |
| Missing population | 14 Suffolk County, NY tracts (A-029) excluded and **not imputed**. New York's coverage is 99.61% (77,579 residents short); the estimated effect on its D2 is **−0.31%** (Phase 5) |
| Diagnostics only | `raw_msa_density_diagnostic` (D1) and `pw_block_group_density_sld2018_diagnostic` (D3). Neither enters any mart |

**Reproduction and tests.**
- D2 reproduces the Phase 5 values exactly (maximum relative difference 2e-8).
- Tests cover:
  - 35 markets
  - density > 0
  - the known gap exists only for New York, and has exactly 14 tracts
  - every other market's tracts sum to 100% of its ACS CBSA population
  - New York's gap stays open (proof of no imputation)

### 5.2 W5 weather station rule (A-007, A-021)

These definitions are explicit in `int_weather__station_qualification` and in the `vars`:

| Term | Definition |
|---|---|
| **Core element** | The 5 annual normals the climate features need: `ANN-PRCP-NORMAL`, `ANN-PRCP-AVGNDS-GE010HI`, `ANN-TMAX-AVGNDS-GRTH090`, `ANN-TMIN-AVGNDS-LSTH032`, `ANN-TAVG-NORMAL` |
| **Core-qualifying station** | Publishes all 5 with a value and NCEI completeness flag **S** (≥ 24 years, gap-filled) or **R** (≥ 10 years, gap-filled) |
| **Snow-qualifying station** | Publishes `ANN-SNOW-NORMAL` and `ANN-SNOW-AVGNDS-GE010TI` with flag **S or P**. NCEI cannot gap-fill snow, so no snow normal carries R. A blank is missing, never zero. No snow normal in the archive is trace |
| **PLCD station** | NOAA HOMR (S-41) lists the station as **PLCD, Primary Local Climatological Data**, in its EMSHR history period containing 2020-12-31 (`int_weather__station_class`). The `USW` prefix (WBAN numbering) is carried as `is_wban_numbered` for description only and is never used by the rule |
| **Distance** | Great-circle km (Snowflake `HAVERSINE`) from the market's population-weighted centre. Ties break on station ID |

**Selection by role** (`int_weather__market_station_selection`, 105 rows = 35 markets × 3 roles):

| Role | Rule | Markets |
|---|---|---|
| GENERAL_CLIMATE | Nearest core-qualifying PLCD station ≤ 25 km (`PLCD_WITHIN_25KM`) | **30** |
| | Otherwise the nearest core-qualifying station of any network (`NEAREST_QUALIFYING_ANY_NETWORK`) | **5**: Detroit 20.8 km, Miami 4.0 km, Riverside 6.1 km, Denver 9.5 km (Denver-Stapleton / Central Park; DEN Intl is PLCD but beyond 25 km), Kansas City 10.7 km (Downtown AP; MCI is PLCD but beyond 25 km) |
| SNOW | The climate station, if it is snow-qualifying (`SAME_AS_GENERAL_STATION`) | 30 |
| | Otherwise the nearest snow-qualifying station ≤ 50 km (`SNOW_FALLBACK_WITHIN_50KM`) | **5**: Los Angeles, Phoenix, Sacramento, San Diego, San Francisco, all ≤ 16.7 km |
| | Otherwise `SOURCE_NOT_PUBLISHED` | 0 |
| WIND | Nearest station with hourly wind normals (`NEAREST_HOURLY_WIND_STATION`), not distance-capped | Median 11.1 km. **Austin 81.8 km** (Robert Gray AAF) and **Miami 34.4 km** (Miami Intl) are flagged and kept visible (A-030) |

**Preserved per market:**
- station ID, name and type
- distance
- selection rule and fallback flag
- completeness flag
- whether the snow or wind station differs from the climate station
- the number of candidates considered

**Tests.** `assert_w5_station_rule_applied` proves:
- every choice satisfies its rule;
- no PLCD candidate within 25 km was skipped, and every station's type label matches its HOMR class;
- no snow candidate within 50 km was ignored;
- each market has exactly one station per role.

`assert_station_class_known_cases` pins the HOMR interpretation for 8 stations: CVG, Sacramento Executive, DEN; Lunken, Sacramento 5 ESE, Denver Central Park, Kansas City Downtown; and LA Civic Center, PLCD on the class date but not today.

**Correction relative to the first Phase 6 build (USW-prefix rule):** 99 of 105 selections are unchanged.

| Market | Role | Before (USW prefix) | After (HOMR PLCD) | Feature values |
|---|---|---|---|---|
| Cincinnati 17140 | GENERAL_CLIMATE | USW00093812 Lunken Field, 10.8 km (not PLCD) | **USW00093814 Cincinnati/Northern KY Intl (CVG), 24.45 km, PLCD** | precip days 80.0 → **82.6**; 90 °F days 26.7 → **22.1** |
| Cincinnati 17140 | SNOW | USC00331515 fallback, 14.3 km | **USW00093814 (same as climate station)** | snowfall 16.0 → **23.3 in** |
| Sacramento 40900 | GENERAL_CLIMATE | USW00023271 Sacramento 5 ESE, 11.3 km (not PLCD) | **USW00023232 Sacramento Executive AP, 19.88 km, PLCD** | precip days 38.0 → **37.3**; 90 °F days 89.9 → **75.6** |
| Sacramento 40900 | SNOW | USW00023271 (same as climate station) | USW00023271, now a **fallback** (the PLCD station is not snow-qualifying) | snowfall unchanged |
| Denver 19740 | GENERAL_CLIMATE | USW00023062, labelled first-order | same station, now **`NEAREST_QUALIFYING_ANY_NETWORK`** (not PLCD) | unchanged |
| Kansas City 28140 | GENERAL_CLIMATE | USW00013988, labelled first-order | same station, now **`NEAREST_QUALIFYING_ANY_NETWORK`** (not PLCD) | unchanged |

Wind stations and values are unchanged in all 35 markets (largest difference 1.8e-15, floating-point aggregation order).

### 5.3 A1 market-embedded airport activity (A-009; A-032 hardened)

- An airport belongs to the frozen market whose **official counties contain its reference point** (S-40 county FIPS → July 2023 delineation).
- `enplanements_per_resident` = CY2025 enplanements at those airports ÷ PEP 2025 population.
- It measures **market-embedded** airport activity, not a metro's full aviation catchment.
- **A4** is diagnostic only: inside-market airports, otherwise the nearest market centre within 80 km.

**Edge cases.** All are tested in `assert_airport_a1_edge_cases`:

| Airport | Official county | A1 market | Note |
|---|---|---|---|
| BWI | Anne Arundel, MD | **Baltimore 12580** | Not Washington |
| DCA | Arlington, VA | **Washington 47900** | |
| ONT | San Bernardino, CA | **Riverside 40140** | Not Los Angeles |
| SNA | Orange, CA | **Los Angeles 31080** | Orange County is an official county of the LA MSA |
| MHT | Hillsborough, NH | **none** | Manchester-Nashua MSA. A4 diagnostic: Boston |
| ORH | Worcester, MA | **none** | Worcester MSA. A4 diagnostic: Boston |
| SJC | Santa Clara, CA | **none** | San Jose MSA, outside the universe. A4 diagnostic: San Francisco |
| PVD | Kent, RI | **none** | Providence MSA; 83 km from the nearest centre, so excluded even from A4 |

**Double counting.** The airport-level grain makes each airport countable at most once (tested). Market totals reconcile exactly to the assigned airports: 67 airports, 772,732,731 enplanements.

**Phase 5 → Phase 6 A4 correction (diagnostic only).** The Phase 5 *code* assigned A4 by nearest centre alone. The Phase 5 *documentation* said "inside first, otherwise nearest within 80 km". Phase 6 implements the documented rule. The only effect is STC, which is inside the Minneapolis CBSA but 87 km from its centre: it now appears in Minneapolis's A4 list. A1 is unaffected.

### 5.4 NW1 population-weighted walkability

```
NW1 = Σ NatWalkInd_b · TotPop_b / Σ TotPop_b     over the market's SLD block groups with a published index and population > 0
```

- **Geography:** block group → county FIPS → CBSA under the July 2023 delineation (the Phase 4 bridge). EPA's own pre-2023 CBSA field is never used. It disagrees for 1,919 block groups.
- **Coverage:**
  - 98,029 block groups in the markets
  - 97,740 used
  - 289 have zero population
  - none with population lacks the index
  - population coverage = **100%** (tested, so no silent loss)
- **A-031 stays visible.** `transit_missing_population_share` is the share of residents in block groups with no transit data. EPA gives these the lowest transit rank inside the index. The median is about 45% and the range 15.6%–79.5%. It is exposed in the sidewalk mart as `qa_walkability_transit_missing_population_share`.

### 5.5 Labor cost (Step 11)

Definitions were verified against O\*NET, the U.S. Department of Labor's database built on the SOC 2018 codes that OEWS uses:

| Occupation | SOC 2018 / O\*NET definition | Production use |
|---|---|---|
| 53-3053 Shuttle Drivers and Chauffeurs | "Drive a motor vehicle to transport passengers on a planned or scheduled basis. May collect a fare. Includes nonemergency medical transporters and hearse drivers." | **Robotaxi** C3, cost of the human-driver alternative. Published for 35 of 35 markets |
| 43-5021 Couriers and Messengers | "Pick up and deliver messages, documents, packages, and other items between offices or departments within an establishment or directly to other business concerns, traveling by foot, bicycle, motorcycle, automobile, or public conveyance." | **Sidewalk and drone** C3, cost of the human delivery alternative. Published for 35 of 35 markets |
| 53-3054 Taxi Drivers | "Drive a motor vehicle to transport passengers on an unplanned basis and charge a fare, usually based on a meter." | **Not used.** Published for 7 of 35 markets. Contract row `PD91` is DROPPED; it is never imputed |

**Limitations:**
- 53-3053 is a *scheduled-service* occupation. It is the closest passenger-driving occupation with full coverage, not an exact taxi equivalent.
- OEWS excludes the self-employed, so app-based ride-hail drivers and couriers are largely missing (A-017).
- Every production wage carries no BLS marker (tested).

## 6. Resolved questions

### 6.1 Income vs wage (Step 12)

The two are correlated: ρ 0.77 for robotaxi (Pearson 0.86) and ρ 0.63 for delivery. They still measure **different things**:
- **Median household income** is customer purchasing power, the ability to pay for a premium on-demand service. It goes in **C1 Demand & Market Opportunity**.
- **Occupation wage** is the operator's cost of the human alternative that automation replaces. It goes in **C3 Economic Attractiveness**.

Both stay, in **different components**, so neither component counts "metro affluence" twice. This is documented as A-035.

The correlation is reported, not hidden. Phase 8 sensitivity should include a drop-one test of the pair.

### 6.2 Cost-of-living adjustment (Step 13)

**Decision: no adjustment.** Phase 8 may test it as a sensitivity only if an official source is later verified (A-036).

- **Wages:** the comparison that matters is a *nominal* local human wage against automation costs that are largely priced nationally (vehicles, compute, remote operations). Deflating wages by local prices would understate the labor saving exactly where it is largest. So nominal is the right concept.
- **Income:** fares and delivery fees are set in local prices, so nominal income is a coherent measure of the ability to pay local prices. A real-income adjustment is a reasonable alternative view, not a correction.
- **Source:** the only approved candidate, BEA Regional Price Parities (S-11), is a PROXY in `data_sources.md`. BEA has announced it will discontinue its MSA statistics, and 2024 MSA RPP availability is ambiguous. No third-party source was added.

### 6.3 Wind metric (Step 7)

**What the source holds.** Each `HLY-WIND-AVGSPD` value is the 1991–2020 *climatological mean* wind speed for one hour of the normal year: 8,760 values per station, in mph (confirmed in Phase 5).

**What "90th percentile" would mean.** The 90th percentile of those 8,760 values is a percentile of hourly **means**, i.e. the windiest hours of an average year. It is **not** the 90th percentile of observed wind, and it says nothing about gusts or extreme-wind frequency. Labelling it an extreme-wind percentile would overstate it. It is kept only as `p90_of_hourly_normals_mph_diagnostic` (contract row PX04, DIAGNOSTIC).

**Selected: `annual_mean_wind_mph`.** This is ONE primary drone wind feature.

| Item | Value |
|---|---|
| Unit | mph |
| Source fields | `HLY-WIND-AVGSPD` (missing `-9999` hours excluded and counted: 11 station-hours in total) |
| Business interpretation | Climatological mean wind speed. A higher mean implies more frequent exceedance of small-UAS wind limits. Under the usual Rayleigh/Weibull description of wind speeds, the chance of exceeding a fixed limit rises with the mean |
| Status | Active **PROXY**, direction LOWER_IS_MORE_FAVORABLE |
| Limitations | Not gusts, turbulence or extremes; the distribution's shape varies by site; one station per metro; the station is 81.8 km away for Austin and 34.4 km for Miami (A-030) |

### 6.4 Drone low-density methodology (Step 8)

I followed the brief's reasoning order:
1. **Is a continuous density variable adequate?** No, for drones. Population-weighted density is not monotonic for drone fit: dense cores lack drop zones and very sparse areas lack demand. Its direction is context-dependent, so `pw_tract_density` stays DEFERRED for drones.
2. **Is a share measure more meaningful?** Yes. The concept is the suburban structure that allows yard and driveway delivery. The share of housing units that are **1-unit detached** (ACS B25024) measures it directly and needs no threshold. It is the active drone C5 feature, `share_single_family_detached`.
3. **Is there a defensible threshold?** None found. The 1,000 persons per sq mi figure behind `share_pop_tracts_lt_1000` resembles a former Census urban-core criterion. That criterion defines urbanization, not a drone operating limit.

**Result:** `share_pop_tracts_lt_1000` changes from MODIFY to **DROPPED** (§2.1). No sample quantile was turned into an "operational" threshold. This is recorded as A-037.

### 6.5 Directions (Step 14)

Every ACTIVE feature has a direction and a written rationale in `DIM_FEATURE` (columns `direction`, `direction_rationale`).
- No direction was inferred from correlation with deployments.
- Features whose direction is unresolved stay DEFERRED (`CONTEXT_DEPENDENT_OR_DEFER`) and are not in any mart. Examples: transit share, car-free households, drove-alone share, travel time, intersection density, drone density.

## 7. Final pre-regulatory feature sets (Steps 15–17)

There are 10 active features per mode. Every feature belongs to exactly one component per mode (tested).

### 7.1 Robotaxi: `ANALYTICS.MART_ROBOTAXI_FEATURES`

| ID | Feature | Component | Unit | Direction | Transformation |
|---|---|---|---|---|---|
| PF01 | `population_2025_log1p` | C1 | ln(persons) | Higher | LOG1P |
| PF02 | `pw_tract_density_log1p` | C1 | ln(persons / sq mi) | Higher | POPULATION_WEIGHTED + LOG1P |
| PF03 | `share_taxi_or_ride_hailing` | C1 | share | Higher | PER_CAPITA |
| PF04 | `enplanements_per_resident_log1p` | C1 | ln(enplanements / resident) | Higher | PER_CAPITA + LOG1P |
| PF05 | `median_household_income_usd` | C1 | USD | Higher | NONE |
| PF11 | `days_precip_ge_010_in` | C2 | days / yr | Lower | NONE |
| PF12 | `days_tmax_ge_90f` | C2 | days / yr | Lower | NONE |
| PF13 | `annual_snowfall_in` | C2 | inches / yr | Lower | NONE |
| PF09 | `shuttle_chauffeur_median_annual_wage_usd` | C3 | USD / yr | Higher | NONE |
| PF06 | `establishments_per_1k_pop` | C3 | per 1,000 residents | Higher | PER_CAPITA |

### 7.2 Sidewalk delivery robot: `ANALYTICS.MART_SIDEWALK_DELIVERY_FEATURES`

| ID | Feature | Component | Unit | Direction | Transformation |
|---|---|---|---|---|---|
| PF01 | `population_2025_log1p` | C1 | ln(persons) | Higher | LOG1P |
| PF02 | `pw_tract_density_log1p` | C1 | ln(persons / sq mi) | Higher | POPULATION_WEIGHTED + LOG1P |
| PF08 | `restaurants_per_10k_pop` | C1 | per 10,000 residents | Higher | PER_CAPITA |
| PF07 | `retail_establishments_per_10k_pop` | C1 | per 10,000 residents | Higher | PER_CAPITA |
| PF05 | `median_household_income_usd` | C1 | USD | Higher | NONE |
| PF11 | `days_precip_ge_010_in` | C2 | days / yr | Lower | NONE |
| PF12 | `days_tmax_ge_90f` | C2 | days / yr | Lower | NONE |
| PF13 | `annual_snowfall_in` | C2 | inches / yr | Lower | NONE |
| PF10 | `courier_median_annual_wage_usd` | C3 | USD / yr | Higher | NONE |
| PF15 | `population_weighted_walkability` | C5 | index 1–20 | Higher | POPULATION_WEIGHTED |

### 7.3 Drone delivery: `ANALYTICS.MART_DRONE_DELIVERY_FEATURES`

| ID | Feature | Component | Unit | Direction | Transformation |
|---|---|---|---|---|---|
| PF01 | `population_2025_log1p` | C1 | ln(persons) | Higher | LOG1P |
| PF08 | `restaurants_per_10k_pop` | C1 | per 10,000 residents | Higher | PER_CAPITA |
| PF07 | `retail_establishments_per_10k_pop` | C1 | per 10,000 residents | Higher | PER_CAPITA |
| PF05 | `median_household_income_usd` | C1 | USD | Higher | NONE |
| PF11 | `days_precip_ge_010_in` | C2 | days / yr | Lower | NONE |
| PF12 | `days_tmax_ge_90f` | C2 | days / yr | Lower | NONE |
| PF13 | `annual_snowfall_in` | C2 | inches / yr | Lower | NONE |
| PF14 | `annual_mean_wind_mph` | C2 | mph | Lower | NONE (PROXY) |
| PF10 | `courier_median_annual_wage_usd` | C3 | USD / yr | Higher | NONE |
| PF16 | `share_single_family_detached` | C5 | share | Higher | PER_CAPITA |

### 7.4 Component coverage (Step 16)

| Component | Robotaxi | Sidewalk robot | Drone |
|---|---|---|---|
| C1 Demand & Market Opportunity | 5 | 5 | 4 |
| C2 Operating Environment | 3 | 3 | 4 |
| C3 Economic Attractiveness | 2 | 1 | 1 |
| C4 Regulatory & Autonomy Readiness | **PENDING PHASE 6.5** | **PENDING PHASE 6.5** | **PENDING PHASE 6.5** |
| C5 Infrastructure & Mode Fit | **0: gap** | 1 | 1 |

**The robotaxi C5 gap is deliberate.** Its candidates are intersection density, car dependence or vehicle availability, and walkability. All are DEFERRED because their direction for robotaxis is unresolved: a denser street grid means more trip demand *and* harder driving. Airport activity and density already sit in C1 as demand. No unrelated proxy was added to fill the gap, so Phase 7 must handle an empty robotaxi C5 explicitly.

### 7.5 Transformations (Step 17)

| Transformation | Applied to | Why it is defensible |
|---|---|---|
| PER_CAPITA | Shares, establishment rates, enplanements per resident | Converts size-driven counts into intensity (Phase 5 found 15 counts with ρ ≥ 0.90 against population) |
| POPULATION_WEIGHTED | Density (D2), walkability (NW1) | Measures what the average resident experiences, not the county footprint |
| LOG1P | Population; D2 density; enplanements per resident | Right-skewed, multiplicative quantities spanning large ranges (population 2.2–20.1 M; D2 1,934–32,301). The log expresses diminishing marginal value and damps connecting-hub inflation (A-010). ln(1 + x) ≈ ln(x) for every value here |
| NONE | All other features | Roughly symmetric, or zero is meaningful (snowfall) |

**Not created:** min-max 0–100, percentiles, z-scores, robust scaling or any weighted value. Normalization is a Phase 7 scoring-method decision (A-016).

## 8. Marts and dictionary (Steps 18–19)

| Object | Rows | Columns |
|---|---|---|
| `ANALYTICS.MART_ROBOTAXI_FEATURES` | 35 | 19: 2 keys + 10 features + 7 `qa_*` |
| `ANALYTICS.MART_SIDEWALK_DELIVERY_FEATURES` | 35 | 17: 2 + 10 + 5 |
| `ANALYTICS.MART_DRONE_DELIVERY_FEATURES` | 35 | 18: 2 + 10 + 6 |
| `ANALYTICS.DIM_FEATURE` | 72 | 19 |

DIM_FEATURE holds 72 feature × mode rows: 30 ACTIVE, 6 DIAGNOSTIC, 34 DEFERRED and 2 DROPPED.

**QA fields:**
- the density gap flag
- the taxi-commuter CV
- airport count and codes
- climate station ID and fallback flags
- the walkability transit-missing share
- wind station ID, distance and distance flag

**Mart tests:**
- 35 rows, equal to DIM_MARKET
- `market_id` unique, not null and related to DIM_MARKET
- every active feature not null
- `assert_mode_marts_match_feature_contract`: a mart holds *exactly* its active contract features plus keys and `qa_*` columns, so no unapproved column can appear
- `assert_no_scoring_columns` (extended from Phase 4 to INTERMEDIATE, CORE and ANALYTICS): no score, readiness, normalized, cluster, archetype, k-means, deployment, feature-weight or rank column

**DIM_FEATURE tests (`assert_feature_contract_integrity`):**
- every active feature has a resolved direction and full metadata
- `feature_id` and `feature_name` are unique within each mode
- no active C4 feature
- the active flag is consistent with the status
- no weight, score or rank column

## 9. Feature QA (Step 21)

`scripts/run_feature_qa.py` writes `outputs/phase6/feature_qa_stats.csv` and `final_strong_correlation_pairs.csv`, plus per-mode Spearman matrices.

**Findings:**
- All 30 mode × feature values are complete: 0 missing, 0 infinite, 0 impossible (negative, or a share above 1).
- No duplicate markets.
- Every per-capita denominator is positive: population ≥ 2,165,775; workers ≥ 1,045,338; housing units ≥ 897,206.

**Final strong pairs** (reported for QA; nothing removed automatically):

| Mode | Pair | Spearman | Pearson | Handling |
|---|---|---|---|---|
| Sidewalk | `pw_tract_density_log1p` (C1) ~ `population_weighted_walkability` (C5) | **0.883** | 0.858 | Kept. Distinct concepts (demand concentration vs pedestrian network) in distinct components, and NWI contains no population-density input. Phase 8 drop-one sensitivity |
| Robotaxi | `median_household_income_usd` (C1) ~ `shuttle_chauffeur_median_annual_wage_usd` (C3) | 0.771 | **0.855** | Below 0.80 on Spearman. Pearson is driven by high-cost coastal metros. Distinct roles (§6.1) |

No drone pair reaches |ρ| ≥ 0.80. The highest are income ~ courier wage (0.63) and snowfall ~ wind (0.58).

## 10. Clustering: evaluated, not adopted (Step 22)

Phase 5 found:
- a Hopkins statistic of about 0.68
- silhouettes of 0.20–0.32 for k = 2–6
- a New York singleton whenever k ≥ 3
- five principal components needed for about 80% of the variance

The evidence for stable, useful market archetypes is weak, so clustering is **EVALUATED — NOT ADOPTED AS CORE METHOD** (A-033).
- No cluster labels, archetype names, k-means outputs or cluster features exist.
- `assert_no_scoring_columns` rejects any such column.

## 11. What Phase 6 deliberately does not contain

- Scores, component scores, weights, weighted averages, rankings or top-N lists.
- Scenario weights or sensitivity runs.
- 0–100 normalization.
- Power BI.
- Deployment evidence, or deployment-based feature selection.
- Regulatory values (§7.4; see [regulatory_handoff.md](regulatory_handoff.md)).
- Multi-state regulatory mapping. `BRG_MARKET_STATE` and its observed population shares are preserved unchanged, and A-012 stays open for Phase 6.5.
