# Feature Redundancy Resolution (Phase 6)

**Status:** Phase 6, in review · **Last updated:** 2026-10-05

This document records how the Phase 5 redundancy findings became production choices. Each concept is represented by one signal per mode.

**Principle.** A variable is not removed *only* because it correlates with another. The decision combines:
- conceptual meaning (what business question the variable answers);
- mathematical relationship (nested counts, shared denominators, scale duplication);
- the measured correlation from Phase 5 (`outputs/strong_correlation_pairs.csv`, `outputs/size_duplication.csv`).

**Labels:**
- **PRIMARY**: the production feature for that concept and mode.
- **SUPPORTING / DIAGNOSTIC**: kept for sensitivity or QA, never a scoring input.
- **DROP_FROM_PRODUCTION**: not carried.

The authoritative per-feature record is `DIM_FEATURE` / `dbt/seeds/feature_contract.csv`. Every Phase 5 feature × mode disposition is in `outputs/phase6/phase5_to_phase6_crosswalk.csv`.

## 1. Redundancy groups

### MARKET_SCALE

Phase 5 found **15 features with |Spearman ρ| ≥ 0.90 against population**, all of them absolute counts.

| Role | Feature | Reason |
|---|---|---|
| PRIMARY (all modes) | `population_2025_log1p` | The single explicit measure of addressable market size |
| DROP_FROM_PRODUCTION | ACS population, households, workers 16+, drove-alone and WFH counts, vehicles, housing units, owner-occupied units, CBP all-sector / retail / food-service / restaurant / courier establishment counts, CBP employment, restaurant employment, OEWS employment counts, absolute inside-CBSA enplanements | Each is "market size" counted again. Where a count carries a distinct concept, its **per-capita form** represents it instead (§2) |

Population, employment, business counts and absolute airport passengers therefore do **not** enter as independent demand signals.

### MOBILITY_DEMAND

| Role | Feature | Reason |
|---|---|---|
| PRIMARY (robotaxi) | `share_taxi_or_ride_hailing` | Revealed demand for hailed paid rides; ρ 0.44 with population, so not a size proxy |
| DEFERRED | Transit share, car-free households share, drove-alone share, WFH share, mean travel time | Direction unresolved: transit both competes with and complements robotaxis. Transit ~ car-free households ρ 0.84 |

### URBAN_FORM

| Role | Feature | Reason |
|---|---|---|
| PRIMARY (robotaxi C1, sidewalk C1) | `pw_tract_density_log1p` (D2) | Demand concentration experienced by residents |
| SUPPORTING / DIAGNOSTIC | `raw_msa_density_diagnostic` (D1), `pw_block_group_density_sld2018_diagnostic` (D3) | D1 is distorted by county footprints (ρ 0.57 with D2). D3 is the same concept on older inputs (ρ 0.99): a sensitivity, not a second signal |
| PRIMARY (sidewalk C5) | `population_weighted_walkability` (NW1) | Pedestrian network suitability. **Correlated with D2 (ρ 0.88) but conceptually distinct and not mathematically related**: NWI's inputs are land-use mix, intersection density and transit distance, with no population density. They sit in different components. Phase 8 drop-one sensitivity |
| PRIMARY (drone C5) | `share_single_family_detached` | Yard and driveway delivery fit (continuous, no threshold) |
| DROP_FROM_PRODUCTION | `share_pop_tracts_lt_1000` | Arbitrary threshold (Phase 6 change). Overlaps the drone concept above |
| DEFERRED | `share_pop_tracts_ge_5000` (ρ 0.95 with D2), `share_pop_most_walkable` (ρ 0.91 with NW1), intersection density (an NWI input), walked share, D2 for drones (non-monotonic) | Redundant alternatives or unresolved direction |
| DROP (Phase 5) | Raw density, central-county density, restaurants per sq mi | Bad geography (county-footprint denominators) |

### COMMERCIAL_INTENSITY

| Role | Feature | Reason |
|---|---|---|
| PRIMARY (robotaxi C3) | `establishments_per_1k_pop` | General commercial activity: work, errand and business trip attractors |
| PRIMARY (sidewalk, drone C1) | `restaurants_per_10k_pop`, `retail_establishments_per_10k_pop` | Delivery merchants: food and retail delivery origins. ρ 0.33 with each other: distinct |
| SUPPORTING / DIAGNOSTIC (sidewalk, drone) | `establishments_per_1k_pop` | **Mathematically nested**: retail and restaurant establishments are subsets of all establishments (ρ 0.52 and 0.59). Including the total next to its parts would count the same merchants twice (Phase 6 change) |
| DEFERRED | Food & beverage retail per 10k (a subset of retail), couriers per 100k (direction unclear) | |

### AIRPORT_ACTIVITY

| Role | Feature | Reason |
|---|---|---|
| PRIMARY (robotaxi C1) | `enplanements_per_resident_log1p` (A1) | Market-embedded airport activity; ρ 0.31 with population after per-capita conversion |
| SUPPORTING / DIAGNOSTIC | `a4_enplanements_per_resident_diagnostic` (A4) | Same concept with a different boundary rule (ρ 0.994) |
| DROP_FROM_PRODUCTION | Absolute enplanements | Scale duplicate |

### INCOME_ECONOMICS and LABOR_COST

| Role | Feature | Component | Concept |
|---|---|---|---|
| PRIMARY (all modes) | `median_household_income_usd` | C1 | Customer purchasing power |
| PRIMARY (robotaxi) | `shuttle_chauffeur_median_annual_wage_usd` (53-3053) | C3 | Cost of the human-driver alternative |
| PRIMARY (sidewalk, drone) | `courier_median_annual_wage_usd` (43-5021) | C3 | Cost of the human courier alternative |
| DEFERRED | 53-3033 light-truck and 53-0000 all-transportation wages | | Redundant with the chosen wages (ρ 0.91 with each other) |
| DROP (Phase 5) | 53-3054 taxi wage (7 of 35 markets), 35-3023 fast-food wage | | Too missing; weak proxy |

**Income and wage are not double counting.** They answer different C1 and C3 questions (purchasing power vs cost of the alternative) and are kept in different components. Their correlation is reported (§3), not hidden.

### WEATHER

| Role | Feature | Reason |
|---|---|---|
| PRIMARY (all modes, C2) | `days_precip_ge_010_in`, `days_tmax_ge_90f`, `annual_snowfall_in` | Wet, heat and snow disruption; mutual |ρ| 0.41–0.54 |
| PRIMARY (drone, C2) | `annual_mean_wind_mph` | One wind signal (PROXY); ρ 0.58 with snowfall |
| SUPPORTING / DIAGNOSTIC | `p90_of_hourly_normals_mph_diagnostic` | A percentile of hourly means, not an extreme-wind statistic |
| DEFERRED | Freeze days (ρ 0.95 with snowfall), annual precipitation (redundant with precipitation days) | |
| DROP (Phase 5) | Annual mean temperature | Non-monotonic; ρ −0.89 with snowfall |

### STRUCTURAL

| Feature | Disposition |
|---|---|
| `state_count` | DEFERRED to Phase 6.5: multi-state regulatory mapping (A-012), not a scoring feature |
| Land area, county count | DROP (Phase 5): denominators or administrative structure only |

## 2. Scale vs intensity (Step 4)

Each approved absolute count gets one form in production:

| Absolute count | Production form | Why |
|---|---|---|
| Population (PEP 2025) | **ABSOLUTE** (log) | Size of the addressable market *is* the concept. A per-capita form is meaningless |
| Taxi / ride-hail commuters | **PER_CAPITA** (share of workers 16+) | The absolute count duplicates size (ρ ≥ 0.9). The share is revealed preference |
| All-sector establishments | **PER_CAPITA** (per 1,000), robotaxi only | Commercial intensity, independent of size |
| Retail establishments | **PER_CAPITA** (per 10,000) | Delivery origins per resident |
| Restaurant establishments | **PER_CAPITA** (per 10,000) | Delivery origins per resident |
| 1-unit detached housing units | **PER_CAPITA** (share of housing units) | Housing structure, not size |
| Enplanements (A1) | **PER_CAPITA** (per resident, log) | The absolute value duplicates size |
| Households, workers, vehicles, housing units, employment, OEWS employment, courier establishments | **NEITHER** | Size duplicates, or the per-capita form's direction is unresolved |

**No feature uses BOTH**, because no count has an absolute and a per-capita form that answer different business questions here. That keeps mathematically related pairs (a count and its rate, which share a numerator) out of every component.

## 3. Final correlation QA (production sets)

Phase 6 recomputed Pearson and Spearman correlation inside each final 10-feature set (`outputs/phase6/final_strong_correlation_pairs.csv`, `spearman_<mode>.csv`):

| Mode | Pairs with \|ρ\| ≥ 0.80 | Highest \|ρ\| |
|---|---|---|
| Robotaxi | none. Income ~ shuttle wage has Pearson 0.855 but ρ 0.771 | 0.77 |
| Sidewalk robot | **D2 density ~ walkability, ρ 0.883** (kept; §1 URBAN_FORM) | 0.88 |
| Drone | none | 0.63 (income ~ courier wage) |

No feature was removed because of these numbers. They are inputs to the Phase 7 scoring design and the Phase 8 sensitivity analysis.
