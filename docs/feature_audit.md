# Feature Audit and Exploratory Data Analysis (Phase 5)

**Status:** Phase 5, in review · **Last updated:** 2026-10-05

## 1. Objective

This phase audits every candidate measure before any feature engineering. For each candidate it asks four questions:
- Is the measure complete, and does it vary across markets?
- Is it distinct from market size and from the other candidates?
- Is it at the right geography?
- Should it be **KEEP**, **MODIFY**, **DEFER** or **DROP** for each mode: robotaxi (RT), sidewalk delivery robot (SW) and drone delivery (DR)?

**Hard boundaries:**
- No readiness scores, component scores, weights, rankings or recommendations.
- No sensitivity simulations and no final clusters.
- No feature selection based on deployment evidence (A-015).
- No Snowflake write-back.

Mapping methods are compared in the companion [mapping_methodology.md](mapping_methodology.md).

**Reproduce:** `python scripts/run_feature_audit.py`. It reads the dbt warehouse read-only as AM_TRANSFORMER and writes only to `outputs/`.

**Code:** [src/analytics/](../src/analytics/)
- `feature_catalog.py`: candidate definitions
- `feature_audit.py`: statistics
- `mapping_evaluation.py`: method comparison
- `diagnostics.py`: charts and the clustering check
- `feature_decisions.py`: the decision table

## 2. Inputs and candidates

**Inputs:**
- `ANALYTICS.MART_MARKET_FEATURE_BASE` (35 markets, CBSA-native measures)
- `CORE.DIM_MARKET`
- lower-grain CORE/INTERMEDIATE facts for the mapping methods: tract population and land, block-group SLD, station normals and hourly wind, airports, and OEWS wages

**70 candidates audited:**

| Origin | Count | IDs | Examples |
|---|---|---|---|
| Mart columns | 35 | M01–M35 | population, ACS commute counts, CBP establishments, OEWS wages, land area |
| Intensity ratios computed from mart columns | 18 | I01–I18 | commute shares, establishments per capita, raw density |
| Mapping-derived | 17 | P01–P17 | population-weighted density, station weather, wind, enplanements, walkability |

By scale type: 41 INTENSITY, 26 ABSOLUTE, 3 STRUCTURAL.

**Expected direction:** every candidate's expected direction is recorded as either `HYPOTHESIS:…` or `UNRESOLVED`. **None is a confirmed scoring direction.**

## 3. Methodology

| Check | Rule (audit heuristic, not a decision rule) | Output |
|---|---|---|
| Inventory | n, missing, unique, p05–p95, mean, SD, CV, skew, zeros, negatives, max ÷ median | `feature_inventory.csv` |
| Missingness | Count, markets affected, cause class. Unacceptable if more than 20% of markets are missing | `missingness.csv`, figure 01 |
| Variation | Zero variance; near-zero variance (CV < 5%); fewer than 5 unique values | `variation_flags.csv` |
| Distribution | Skew > 1 with min ≥ 0 suggests LOG1P; max ÷ median > 5 suggests robust or percentile scaling later | figure 03, `transformation_hint` |
| Outliers | Beyond 3 × IQR, or robust z (MAD) > 3.5 | `outliers.csv` |
| Correlation | Pearson and Spearman (Spearman = Pearson on ranks); strong if \|r\| ≥ 0.80 | `correlation_*.csv`, `strong_correlation_pairs.csv`, figure 02 |
| Size duplication | \|Spearman ρ\| ≥ 0.90 with population 2025 | `size_duplication.csv`, figures 04a/04b |
| ACS reliability | CV = (MOE ÷ 1.645) ÷ estimate | `acs_reliability.csv` |
| Clustering feasibility | PCA, Hopkins, k-means silhouette, bootstrap stability | `clustering_feasibility.json`, figure 09 |

## 4. Missingness

Only **one** of the 70 candidates has missing values.

| Feature | Missing | Cause class | Acceptable? |
|---|---|---|---|
| `oews_annual_median_wage_taxi_drivers` (53-3054) | 28 of 35 (80%) | SOURCE_NOT_PUBLISHED: BLS does not publish this occupation for those metros (A-026) | **No.** DROP |

**Two cases are complete only because of a documented rule:**
- `annual_snowfall_in` is complete for 35 of 35 markets because of the S/P snow-flag rule and the 50 km fallback (mapping_methodology §2). A blank is never read as zero. If a value had stayed unpublished, its cause class would be SOURCE_NOT_PUBLISHED.
- New York's population-weighted density excludes the 14 Suffolk tracts. That is a disclosed GEOGRAPHY_GAP inside the measure, not a missing market value (§10).

No PIPELINE_ERROR or UNRESOLVED cause was found.

## 5. Variation and distributions

- **No zero-variance or near-zero-variance candidates.**
- `state_count` has only 4 distinct values. It is structural and relevant only to multi-state regulatory mapping (A-012).
- 45 candidates have skew > 1. This includes every absolute count, as expected for metro size, and several intensity measures:
  - transit share, car-free households, raw and population-weighted density
  - taxi/ride-hail share, couriers per capita, per-capita enplanements
  - snowfall
- These candidates carry a LOG1P or ROBUST_SCALE_LATER hint. Final transformations are Phase 6 decisions.

## 6. Outliers

There are 134 flags across 49 features. They are concentrated in the largest markets: New York 38, Los Angeles 28, Chicago 21, Boston 8, San Francisco 7, Miami 5.

Every flag was checked against its context, and **none is a data or unit error**. Examples:
- New York has a 24.1% transit commute share against a 1.5% median, and 30.8% of households have no vehicle.
- Cleveland has 63.8 in of lake-effect snowfall.
- Denver and Las Vegas show hub/tourism enplanements per resident (A-010).
- The size outliers are genuine.

**Implication:** outliers are real and must not be removed or winsorized silently. Phase 6 should use robust scaling or rank-based transforms so New York doesn't dominate.

## 7. Correlation and redundancy

**Strong pairs** (|r| ≥ 0.80 on either measure):
- 415 pairs in total: 403 on Pearson, 240 on Spearman.
- Most involve absolute counts that move with size.
- 40 pairs are between non-absolute (intensity or structural) candidates.
- The Pearson-only excess is outlier-driven, mostly by New York. One example is density vs transit share: Pearson 0.93, Spearman 0.77.

**Size duplication:** 15 candidates have |ρ| ≥ 0.90 with population, and every one is an absolute count:
- ACS population, households, workers, drove-alone and work-from-home counts
- vehicles, housing units, owner-occupied units
- CBP establishments and employment (all sectors, retail, food services, restaurants, couriers)
- restaurant employment

Their intensity counterparts are largely independent of size. Restaurants per 10k residents is the clearest example (figure 04b vs 04a).

**Notable non-size pairs** (Spearman):

| Pair | ρ | Handling |
|---|---|---|
| Raw density ~ restaurants per sq mi | 0.987 | Both depend on the same land-area denominator. Both are DROPped (BAD_GEOGRAPHY) |
| Population-weighted density ~ share of population in tracts ≥ 5,000 | 0.948 | Threshold share DEFERred (sensitivity) |
| Days Tmin ≤ 32 °F ~ annual snowfall | 0.948 | Freeze days DEFERred. Snowfall is kept |
| Walkability (population-weighted) ~ share most walkable | 0.912 | Share DEFERred |
| Light-truck wage ~ all-transportation wage | 0.910 | Both DEFERred |
| Annual mean temperature ~ snowfall | −0.888 | Mean temperature DROPped (non-monotonic direction) |
| Population-weighted density ~ walkability | 0.883 | **Both kept for sidewalk robots.** Phase 6 must treat them as one URBAN_FORM group (index, or keep one) |
| Income ~ light-truck / shuttle wage | 0.85 / 0.77 | LABOR_COST and INCOME_ECONOMICS must not double-count |
| Transit share ~ car-free households | 0.838 (Pearson 0.971) | Both DEFERred (direction unresolved) |

**Redundancy groups.** The |ρ| ≥ 0.80 graph chains into one large connected component through the size-linked counts, so it can't define groups on its own. Candidates are therefore assigned to conceptual groups, and empirical correlation is checked inside each group:

| Group | Members kept or modified | Note |
|---|---|---|
| MARKET_SCALE | `population_2025` | The single explicit scale measure. All other size-linked counts are DROPped |
| MOBILITY_DEMAND | `share_taxi_or_ride_hailing` (RT) | Transit, car-free and drove-alone shares DEFERred (direction unresolved) |
| URBAN_FORM | `pw_tract_density`, `walkability_pw_mean`, `share_single_family_detached`, `share_pop_tracts_lt_1000` | Density and walkability ρ 0.88. Detached share is drone-only |
| COMMERCIAL_INTENSITY | `establishments_per_1k_pop`, `retail_per_10k_pop`, `restaurants_per_10k_pop` | Check within-group correlation again in Phase 6 |
| AIRPORT_ACTIVITY | `enplanements_inside_cbsa_per_capita` (RT, MODIFY) | Hub caveat (A-010) |
| INCOME_ECONOMICS | `median_household_income_usd` | Cost-of-living adjustment unresolved |
| LABOR_COST | 53-3053 (RT), 43-5021 (SW/DR) | Correlated with income |
| WEATHER | precipitation days, heat days, snowfall; wind (DR, MODIFY) | Freeze days and total precipitation DEFERred as redundant |
| STRUCTURAL | — | `land_area`, `county_count` DROP; `state_count` DEFER to Phase 7 |

## 8. ACS reliability

| Estimate | Median CV | Max CV | Markets with CV > 15% |
|---|---|---|---|
| Taxi / ride-hailing commuters | 10.7% | 14.6% (Indianapolis) | 0 |
| Bicycle commuters | 7.4% | 15.5% (Nashville) | 2 |
| Public transportation | 3.9% | 8.3% | 0 |
| Walked | 3.2% | 5.8% | 0 |
| No-vehicle households | 1.8% | 3.2% | 0 |
| Median household income, mean travel time | < 1% | < 1% | 0 |

The taxi/ride-hail share is usable, but its sampling error is the largest of the kept candidates. The bicycle share is DROPped (PROXY_TOO_WEAK). Its reliability is borderline, but that is not the reason it was dropped.

## 9. Mapping-method recommendations (summary)

Detail is in [mapping_methodology.md](mapping_methodology.md). All recommendations are pending approval.

| Measure | Recommended | Rejected | Key evidence |
|---|---|---|---|
| Density (A-008) | D2 population-weighted tract density | D1 raw (ρ 0.57 with D2); D4 central county (ρ 0.40) | Riverside raw density is understated ×26.6 |
| Weather (A-007, A-021) | W5: first-order station ≤ 25 km, else nearest qualifying; snow S/P with 50 km fallback (Phase 6: "first-order" corrected to the NOAA HOMR class PLCD, see production_feature_layer.md §4a) | W1 (10 of 35 complete), W3 alone (Riverside 88 km), W4 ring mean | 32 of 35 first-order, max 24.5 km; snow 35 of 35 |
| Wind (A-027) | Nearest hourly station, **mph** (confirmed) | — | Austin 81.8 km flagged |
| Airports (A-009) | A1 inside-CBSA per capita | A2 80 km radius (double counts BWI, ONT, SNA, DCA) | ρ 0.994 with A4 |
| Walkability | NW1 population-weighted mean | — (all methods ρ ≥ 0.91) | Transit-data penalty (A-031) |
| Labor cost (A-026) | 53-3053 robotaxi; 43-5021 delivery | 53-3054 taxi (7 of 35) | — |

## 10. Tract-gap assessment (A-029)

The cause is corrected. The ACS 2020–2024 tract tables omit 14 Suffolk County tracts, while the county and CBSA totals include their population. The Gazetteer vintages for 2020–2024, and the ACS 2018–2022 tract tables, all list these tracts. This is not a tract revision. They held 77,579 people on 13.2 sq mi in the 2018–2022 tables.

Only New York is affected. Its population-weighted density changes by −0.31% if the tracts are added back for sensitivity. **Recommendation:** exclude them with disclosure and don't impute. CBSA-level measures are unaffected.

## 11. Decisions

The full table is `outputs/feature_audit.csv`: one row per candidate, with a status per mode, an overall decision, reason codes, rationale, transformation, source quality, geography quality and revisit phase. The build fails if any candidate lacks a decision.

The overall decision is the most active mode status, in the order KEEP > MODIFY > DEFER > DROP.

**Consistency rule:** an absolute count marked MODIFY ("convert to a share") can't be more active than its intensity counterpart for any mode.

**Overall:** KEEP 14 · MODIFY 8 · DEFER 23 · DROP 25.

| Mode | KEEP | MODIFY | DEFER | DROP |
|---|---|---|---|---|
| Robotaxi | 9 | 3 | 14 | 44 |
| Sidewalk robot | 11 | 3 | 20 | 36 |
| Drone | 10 | 6 | 12 | 42 |

### 11.1 KEEP or MODIFY by mode

| Group | Robotaxi | Sidewalk robot | Drone |
|---|---|---|---|
| Scale | population_2025 (LOG1P) | population_2025 | population_2025 |
| Mobility demand | share_taxi_or_ride_hailing | — | — |
| Urban form | pw_tract_density (LOG1P) | pw_tract_density, walkability_pw_mean | share_single_family_detached; *MODIFY* share_pop_tracts_lt_1000 (threshold to justify) |
| Commercial | establishments_per_1k_pop | establishments_per_1k_pop, retail_per_10k_pop, restaurants_per_10k_pop | same as sidewalk |
| Airport | *MODIFY* enplanements_inside_cbsa_per_capita (LOG1P, hub caveat) | — | — |
| Income | median_household_income_usd | median_household_income_usd | median_household_income_usd |
| Labor cost | OEWS 53-3053 shuttle/chauffeur wage | OEWS 43-5021 courier wage | OEWS 43-5021 courier wage |
| Weather | precip days ≥ 0.10 in, heat days, snowfall | same | same; *MODIFY* annual_mean_wind_mph (consider p90 hourly) |

The remaining MODIFY rows are the absolute counts whose per-capita form is kept. Examples: `cbp_establishments_restaurants` → `restaurants_per_10k_pop`, and `housing_units_1_detached` → `share_single_family_detached`. They aren't separate features.

### 11.2 DEFER (23) and why

| Reason | Features |
|---|---|
| UNCLEAR_DIRECTION | Transit, car-free, drove-alone and work-from-home shares, and their counts; mean travel time; couriers per capita and its count. For example, does high transit use help or hurt robotaxi demand? |
| REDUNDANT (sensitivity alternatives) | Freeze days (ρ 0.95 with snow), total precipitation, share of population in tracts ≥ 5,000, share most walkable, intersection density, food/beverage retail per capita and its count, walked share and its count, light-truck and all-transportation wages |
| WAIT_FOR_REGULATION | state_count (multi-state mapping, A-012, Phase 7) |

### 11.3 DROP (25) and why

| Reason | Features |
|---|---|
| REDUNDANT (scale duplicate, ρ ≥ 0.90 with population) | ACS population, households, workers, vehicles, housing units, CBP all-sector employment, food-services establishments, restaurant employment, OEWS employment counts, inside-CBSA enplanements (absolute) |
| BAD_GEOGRAPHY | raw density, restaurants per sq mi, central-county density |
| TOO_MISSING | 53-3054 taxi wage (7 of 35) |
| PROXY_TOO_WEAK / UNCLEAR_DIRECTION | bicycle count and share, owner-occupied units and share, persons per household, vehicles per household, fast-food wage, annual mean temperature, county count |
| NEEDS_AGGREGATION | land area (a denominator only) |

### 11.4 Transformation table (suggestions for Phase 6)

| Feature | Suggested transformation | Reason |
|---|---|---|
| population_2025 | LOG1P | Skewed and spans almost an order of magnitude (2.17 M–20.1 M) |
| pw_tract_density | LOG1P | Skewed. New York is 32,301 against a 4,638 median |
| enplanements_inside_cbsa_per_capita | LOG1P + hub caveat | Hub-inflated tail |
| share_taxi_or_ride_hailing | Robust scaling later | New York and DC tail |
| annual_snowfall_in | None (robust scaling later) | Many near-zero values; zero is a real value here |
| median_household_income_usd | None. Cost-of-living adjustment unresolved | BEA RPP availability ambiguous (S-11) |
| Commercial per-capita ratios, wages, weather days, walkability | None | Approximately symmetric |
| share_pop_tracts_lt_1000 | None. The threshold needs justification | Arbitrary cut point |
| annual_mean_wind_mph | None. Consider p90 hourly instead | Mean wind ≠ gust exposure (F19 PROXY) |

Normalization (z-score, robust scaling or percentile) is a Phase 6/7 choice and is deliberately not made here (A-016).

## 12. Clustering feasibility (diagnostic only)

**Setup:** 35 markets × 40 complete intensity candidates, robust-scaled.

| Diagnostic | Result |
|---|---|
| PCA | 5 components reach 80% of variance (figure 09) |
| Hopkins statistic (10 runs) | Mean 0.68 (0.63–0.74). Some structure, but weak (0.5 = random, close to 1 = strongly clustered) |
| k-means silhouette | k=2: 0.32 · k=3: 0.28 · k=4: 0.25 · k=5: 0.20 · k=6: 0.23 |
| Cluster sizes | k=2: 27 / 8. For k ≥ 3 there is always a singleton (New York) |
| Bootstrap co-membership stability | 0.79–0.84 |

**Conclusion:** clustering is only **weakly justified**. Silhouettes below 0.35 indicate weak structure, and k ≥ 3 isolates New York. If Phase 6 attempts it, it should use the reduced, de-duplicated KEEP set with robust scaling, and treat it as optional and descriptive. It is never a scoring input. No clusters or labels were created.

## 13. Regulatory evidence requirements (for the curation step, not scored)

Under the agreed sequencing (project_scope.md §14), regulatory evidence is curated after this audit and before Phase 7. It becomes a scored input only after its framework and measurement rules are finalized. The audit establishes that the curation step must capture the following.

**Robotaxi (state level):**
- Testing authorization, with and without a safety driver.
- Driverless (no human operator) deployment authorization.
- Commercial passenger service / fare-charging framework, including the TNC or AV-specific permit regime.
- State preemption of local AV regulation.
- Insurance and reporting requirements.

**Sidewalk delivery robot (PDD):**
- Is a personal delivery device statute present? Its effective date.
- Weight limit, speed limit, and sidewalk vs. crosswalk operation.
- Local authority to restrict or prohibit.
- Operator requirements (remote supervision, registration) and insurance minimums.

**Drone delivery:**
- Federal context only: Part 107/135 and BVLOS rulemaking status. It is identical across markets (A-022).
- State critical-infrastructure overflight restrictions.
- State preemption of local drone regulation.
- State drone-specific privacy or trespass laws.

**For every record:** citation, effective date, access date, verification status (A-011).

**Market mapping:** 11 of the 35 markets span more than one state (`state_count` > 1). The state-to-market rule is still open (A-012):
- principal-city state
- population-weighted state shares
- every state with a divergence flag

It must be decided before any ordinal translation. Population shares are already available from the PEP county rows.

## 14. Unresolved questions and Phase 6 inputs

1. **Approve the mapping methods:** D2, W5, A1 and NW1.
2. **Directions** for DEFERred mobility measures, such as transit share and car-free households for robotaxis. They need a documented rationale or stay out.
3. **URBAN_FORM:** density and walkability are correlated (ρ 0.88) for sidewalk robots. Combine them into an index or keep one.
4. **Cost-of-living adjustment** for income and wages. It depends on BEA RPP availability (S-11).
5. **Drone thresholds:** the low-density threshold for `share_pop_tracts_lt_1000`, and mean vs p90 wind.
6. **Hub inflation** of enplanements (A-010): accept with caveat, or use the A3 large/medium-hub variant.
7. **Clustering:** optional, on the reduced set only.

**Phase 6 inputs:**
- `outputs/feature_audit.csv` (KEEP/MODIFY rows by mode)
- the recommended mapping methods
- the transformation table above
- the redundancy groups
