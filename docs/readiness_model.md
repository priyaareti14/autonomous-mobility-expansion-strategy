# Readiness Model: Baseline Construction (Phase 7, baseline_v1)

**Status:** Phase 7 deliverable (in review) · **Model version:** `baseline_v1` · **Model-input commit:** `55b1cb4` · **Evidence as of:** 2026-10-05

## 1. Objective

Convert the approved Phase 6 production features and the verified Phase 6.5/6.5b regulatory evidence into a transparent, reproducible **baseline** readiness score for each of the 35 markets, separately for each mode:
- robotaxi
- sidewalk delivery robot
- drone delivery

Phase 7 produces feature scores, component scores, baseline readiness scores, **baseline** within-mode ranks, score decompositions and evidence-coverage diagnostics.

A baseline rank is **not a recommendation**. Phase 8 tests whether it is robust. No sensitivity simulation, deployment comparison or tuning happens here.

## 2. Model philosophy

The model applies a decision framework fixed before the results were seen, then reports what it produces:
- **No tuning to outcomes.** No feature, direction, transformation or weight was chosen, changed or kept because of where any operator runs. Deployment evidence is not read by any Phase 7 model or script (§12).
- **Surprises are reported, not fixed.** Markets that rank unexpectedly high or low stay where they are. Phase 8 tests whether the result is robust (Step 37).
- **Every number decomposes.** Every score is an exact weighted sum of its parts, reconciled to 1e-6 by dbt tests and by an independent Python recomputation ([score_reconciliation.md](score_reconciliation.md)).
- **Unknowns stay unknown.** Low-confidence or unretrievable regulatory evidence never becomes a 0, a 50 or a prohibition (§7).

## 3. Frozen inputs

| Input | File | Role |
|---|---|---|
| Feature contract | `dbt/seeds/feature_contract.csv` | The 30 ACTIVE features (10 per mode), their component, transformation and direction |
| Regulatory contract | `config/regulatory_feature_contract.csv` | The 7 ACTIVE_CANDIDATE dimensions, favorable statuses and mapping method |
| Phase 6.5b eligibility | `outputs/phase65/phase7_regulatory_eligibility.csv` | Base-model eligibility of the robotaxi records |
| Regulatory evidence | `evidence/regulatory_evidence.csv` | State records (enters dbt as a generated seed, A-057) |

- All four are unchanged since commit `55b1cb4`. `scripts/run_phase7_scoring_qa.py` verifies this against git on every run and records LF-normalized SHA-256 checksums in `outputs/phase7/model_metadata.json`.
- `assert_feature_scores_match_contract` fails if a scored input differs from the contracts in either direction, so no feature can be added or dropped silently.

**Changes made in Phase 7 (OLD → NEW, with reason):**

| Item | OLD | NEW | Reason |
|---|---|---|---|
| Active features | 30 (Phase 6 contract) | 30, unchanged | No change |
| Regulatory dimensions | 7 ACTIVE_CANDIDATE | 7, unchanged | No change |
| Eligibility rule scope | Defined for the 3 active robotaxi dimensions (Phase 6.5b) | The same rule applied to all 7 dimensions in all modes | One rule for every mode; 11 sidewalk/drone records become ineligible (A-051) |
| Nevada PDD (SW-NV-01) | `STATUTE_AUTHORIZES`, favorable | Evidence code unchanged; not favorable in the base model | A-046 required a scope adjustment for the campus-only statute |
| Absence in scoring (A-043) | Ordinal level between authorization and prohibition | Verified favorable share: absence and explicit restriction both contribute 0, reported separately | Phase 7 brief Step 10; A-055 |
| Evidence landing | RAW ingestion planned (regulatory_handoff.md §5.4) | Deterministic dbt seeds generated from `evidence/`, `--check` verified | A-057 |
| Guard `assert_no_scoring_columns` | No score/weight/rank column anywhere in INTERMEDIATE, CORE, ANALYTICS | Allowed only in the 7 named Phase 7 scoring relations; cluster and deployment columns still forbidden everywhere | Phase 7 creates scores; the guard is narrowed, not removed |
| Guard `assert_no_deployment_evidence_in_feature_layer` | Covered the feature marts and DIM_FEATURE | Also covers every scoring relation | Deployment evidence must not enter scoring either |

## 4. Active features and transformations

Only transformations approved in Phase 6 are used, and they were applied before Phase 7 (`INT_MARKET__PRODUCTION_FEATURES`). Phase 7 reads the model values from the Phase 6 mode marts, and keeps the untransformed value beside every score for traceability:
- `LOG1P`: population (PF01), population-weighted density (PF02), enplanements per resident (PF04);
- `PER_CAPITA` and `POPULATION_WEIGHTED`: already productionized;
- every other feature: as published.

| Mode | C1 Demand & market opportunity | C2 Operating environment | C3 Economic attractiveness | C5 Infrastructure & mode fit |
|---|---|---|---|---|
| Robotaxi | PF01 population (log), PF02 PW density (log), PF03 taxi/ride-hail share, PF04 enplanements per resident (log), PF05 household income | PF11 precipitation days, PF12 90°F days, PF13 snowfall | PF06 establishments per 1k, PF09 shuttle/chauffeur wage | **structurally absent** (§6) |
| Sidewalk | PF01, PF02, PF07 retail per 10k, PF08 restaurants per 10k, PF05 | PF11, PF12, PF13 | PF10 courier wage | PF15 population-weighted walkability |
| Drone | PF01, PF07, PF08, PF05 | PF11, PF12, PF13, PF14 mean wind | PF10 courier wage | PF16 single-family detached share |

**Directions** come from the contract only:
- **Lower is more favorable:** the weather friction measures (PF11–PF14).
- **Higher is more favorable:** every other feature, including the wage features. A higher human-labor cost means a larger automation saving, as approved in Phase 5/6.

No direction was inferred from outcomes, and every active feature has one.

## 5. Normalization: average-rank percentile

For each mode and feature, across the 35 markets, using the transformed value *x*:

```
average_rank(x) = (rank_asc + n + 1 − rank_desc) / 2      (ties share the mean of the positions they occupy)
percentile      = 100 × (average_rank − 1) / (n − 1)        (0 = lowest market, 100 = highest)
feature_score   = percentile          if HIGHER_IS_MORE_FAVORABLE
                = 100 − percentile    if LOWER_IS_MORE_FAVORABLE
```

**Why percentiles:**
- there are only 35 markets;
- there are strong real outliers (New York, Los Angeles; Phase 5 §8);
- many distributions are skewed;
- percentiles are bounded, robust to extreme magnitude and directly interpretable ("better than x% of markets").

The computation is deterministic: there is no random tie-breaking, and it runs in FLOAT, because Snowflake NUMBER division keeps 6 decimals.

**What percentiles lose.** Magnitude is discarded (A-049): every feature averages exactly 50. Percentiles are **not** claimed to be objectively superior; they are the transparent baseline. Raw, transformed and percentile values are all kept, so Phase 8 can compare magnitude-sensitive alternatives.

## 6. Components and baseline weights

```
feature_weight            = 1 / (number of the component's inputs in the base calculation)
component_score           = Σ feature_score × feature_weight          (= arithmetic mean under equal weights)
component_weight          = 1 / (number of active components of the mode)
baseline_readiness_score  = Σ component_score × component_weight      (0–100)
```

| Mode | Active components | Component weight |
|---|---|---|
| Robotaxi | C1, C2, C3, C4 | 25% each |
| Sidewalk delivery | C1, C2, C3, C4, C5 | 20% each |
| Drone delivery | C1, C2, C3, C4, C5 | 20% each |

**Robotaxi C5** has no active feature: its candidates are DEFERRED because their direction is unresolved (A-039). It is **structurally absent**:
- no C5 input, component row or mart column exists (`assert_robotaxi_c5_absent`);
- it is not set to 0;
- no proxy or redistributed feature replaces it;
- C1–C4 carry 25% each.

Equal weights are a neutral baseline, **not** a claim that the components are equally important (A-050).

## 7. Regulatory component (C4)

### 7.1 Inputs and eligibility

- **Dimensions.** Only the seven ACTIVE_CANDIDATE dimensions are used:
  - robotaxi: driverless operation, commercial passenger service, local authority;
  - sidewalk: PDD legal status, local authority, maximum weight;
  - drone: state preemption of local regulation.
- **Federal drone dimensions** are CONTEXT_ONLY and add nothing across markets.
- **Mapping.** States map to markets with the Phase 6.5 A-012 contract. The market × status composition built in dbt equals `outputs/phase65/market_regulatory_summary.csv` exactly (QA check, 245 of 245).
- **Base-model eligibility** (Phase 6.5b rule, every mode): a state record is eligible only if it is `VERIFIED_PRIMARY` **and** MEDIUM or HIGH confidence. Each state row of a market is then classed as one of:
  - `VERIFIED_FAVORABLE`
  - `VERIFIED_NOT_FAVORABLE`, split into absence, explicit, unclear and scope-limited
  - `UNKNOWN_OR_LOW_CONFIDENCE`
  - `NOT_APPLICABLE` (weight limit only)

### 7.2 Scoring semantics: operational quantities, never averaged legal codes

- **Categorical permission and authority dimensions:** `dimension_score = 100 × verified favorable population share` (PEP 2025 state shares from `BRG_MARKET_STATE`). Example: in Washington (DC-VA-MD-WV), the driverless share is the population living in states whose verified status is in the favorable set.
- **SW_MAX_WEIGHT** (`MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES`):
  - The market value is the lowest verified limit among the market's states that have a verified general PDD authorization. `NO_LIMIT_STATED` counts as unconstrained and ranks above every number.
  - It is scored by the same average-rank percentile among the 22 markets where a limit applies.
  - Where no state authorizes PDDs, the dimension is **NOT APPLICABLE**: it has no score, and C4 averages the other two dimensions (A-053).
- **C4 score** = equal-weight mean of the market's applicable dimensions.
- **Shares reconcile.** In every market × dimension, favorable + unfavorable + unknown/LOW + not applicable = 1 (`assert_regulatory_shares_reconcile`).
- **Readable decomposition.** Each dimension carries a `decomposition_text`. Chicago (IL 92.3% NOT_AUTHORIZED, IN 7.7% no specific statute): `RT_DRIVERLESS_OPERATION: 0.0% verified favorable; 100.0% verified not favorable (absence 7.7%, explicit 92.3%, unclear 0.0%, scope-limited 0.0%); 0.0% unknown or LOW confidence`.

### 7.3 Incomplete regulation: no score, no rank, no imputation

**Rule.** If any population share of a market has unknown or ineligible evidence on **any** C4 dimension:
- `c4_complete_flag = FALSE`;
- `c4_score_verified`, `baseline_readiness_score` and `baseline_rank` are **NULL**.

There is no imputation, no neutral 50, no zero and no silent renormalization (`assert_incomplete_c4_has_no_base_score`, `assert_low_evidence_never_enters_base_score`).

**What is still published.** `non_regulatory_score`, the equal-weight mean of the non-C4 components, is a **diagnostic** for every market. It is not a readiness score and is not ranked. This avoids penalizing markets simply because government evidence could not be retrieved.

| Mode | Complete C4 (scored and ranked) | Incomplete C4 (score and rank NULL) | Records causing incompleteness |
|---|---|---|---|
| Robotaxi | 29 | Boston, Cincinnati, Cleveland, Columbus, New York, Philadelphia | RT-MA-02/03/06, RT-OH-02/03/06, RT-NJ-02/03/06, RT-NY-06: the 10 Phase 6.5b sensitivity-only records |
| Sidewalk | 31 | Chicago, Cincinnati, Indianapolis, Nashville | SW-IN-01/04/09, SW-TN-01/04/09 |
| Drone | 25 | Atlanta, Boston, Chicago, Los Angeles, Nashville, Riverside, Sacramento, St. Louis, San Diego, San Francisco | DR-CA-02, DR-GA-02, DR-IL-02, DR-MA-02, DR-TN-02 |

Per-market detail is in `outputs/phase7/regulatory_coverage_by_market.csv` (states, ineligible evidence IDs, unknown share), and `figures/04_regulatory_evidence_coverage.png` shows the same.

## 8. Ranking and decomposition

- **Baseline rank.** Within each mode, only markets with a complete score are ranked. Rank 1 is the highest score. Ties, compared at 6 decimals, share a rank (standard competition ranking; `assert_baseline_rank_valid`). The only tie is drone: Denver and Las Vegas share rank 15.
- **Per scored market.** The mart records:
  - the score gap to the preceding market;
  - the strongest and weakest features;
  - the three largest positive contributors (`contribution_to_overall`, in points);
  - the three largest constraints (`points_below_maximum` = (100 − score) × feature weight × component weight, i.e. the points lost against a perfect score).

These are arithmetic decompositions of the score, not narrative explanations.

## 9. dbt objects (RAW → … → ANALYTICS features → ANALYTICS scores)

| Object | Grain | Rows |
|---|---|---|
| `INTERMEDIATE.REGULATORY_STATE_EVIDENCE` (seed) | mode × dimension × state | 204 |
| `INTERMEDIATE.REGULATORY_FEATURE_CONTRACT` (seed) | regulatory feature | 28 |
| `INTERMEDIATE.REGULATORY_SCOPE_ADJUSTMENTS` (seed) | evidence record | 1 |
| `INTERMEDIATE.INT_REGULATORY__MARKET_STATE_EVIDENCE` | market × mode × dimension × state | 357 |
| `ANALYTICS.FCT_REGULATORY_DIMENSION_SCORES` | market × mode × dimension | 245 |
| `ANALYTICS.FCT_FEATURE_SCORES` | market × mode × input (30 features + 7 dimensions) | 1,295 |
| `ANALYTICS.FCT_COMPONENT_SCORES` | market × mode × active component | 490 |
| `ANALYTICS.FCT_READINESS_BASELINE` | market × mode | 105 |
| `ANALYTICS.MART_ROBOTAXI_READINESS_BASELINE` | market | 35 |
| `ANALYTICS.MART_SIDEWALK_DELIVERY_READINESS_BASELINE` | market | 35 |
| `ANALYTICS.MART_DRONE_DELIVERY_READINESS_BASELINE` | market | 35 |

Every scoring relation records `model_version` and `model_input_commit` (dbt vars). The machine-readable outputs, diagnostics and figures are in `outputs/phase7/`, written by `scripts/run_phase7_scoring_qa.py`, which reads from Snowflake and writes nothing back.

## 10. Interpretation rules

1. **Readiness scores are mode-specific.** A robotaxi 80 is not comparable with a drone 80. No combined, averaged or "best overall autonomy city" score exists (`assert_no_cross_mode_combined_score`), and none may be built without an explicit business decision on how modes combine.
2. **A score is relative.** It reflects standing among these 35 markets on these inputs. It is not an absolute measure of readiness.
3. **A baseline rank is not a recommendation.** It is untested until Phase 8. Use "baseline rank", never "final rank".
4. **A NULL score means "not determinable from verified evidence"**, not "unready".
5. **Correlation, not causation.** No score explains why operators do or do not serve a market.
6. **Not legal advice.** The regulatory inputs are an analytical classification (regulatory_methodology.md).

## 11. Baseline diagnostics (analysed, not tuned)

Source: `outputs/phase7/score_distribution.csv`, `variance_contribution.csv`, `component_correlation.csv` and `figures/`.

| Mode | Scored | Min | Median | Max | Std | Median adjacent gap |
|---|---|---|---|---|---|---|
| Robotaxi | 29 | 17.6 | 54.9 | 91.8 | 15.3 | 1.30 |
| Sidewalk | 31 | 25.9 | 51.5 | 72.1 | 11.4 | 0.86 |
| Drone | 25 | 25.1 | 47.5 | 65.1 | 10.7 | 1.31 |

**Share of baseline-score variance by component (complete markets):**

| Mode | C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|
| Robotaxi | 18% | 17% | 20% | **45%** | n/a |
| Sidewalk | 22% | 12% | 34% | **−7%** | 38% |
| Drone | 8% | 4% | 24% | **62%** | 1% |

- **C4 dominates drone and robotaxi variance despite equal weights.** Its verified favorable shares are near-binary (0 or 100 for most single-state markets), while C1 and C2 average several percentiles and are compressed. This is **true variation in the evidence**, not an implementation error: every score reconciles exactly. Weights were not changed (A-054).
- **Sidewalk C4 runs against the other components.** The California markets lead on demand, wage and walkability but have no PDD statute (C4 = 0). This partially offsets their lead.
- **Single-feature components** (sidewalk and drone C3 and C5) keep the full 0–100 spread, so they carry more influence than multi-feature components (A-050).
- **No implementation issue was found.** No component is duplicated, there are no suspicious ties (one exact tie in drone), and no scores are compressed by error.

## 12. Deployment evidence and boundaries

- No Phase 7 model, seed or script reads `evidence/deployment_evidence.csv` or any deployment source.
- The leak guard now covers every scoring relation.
- Phase 7 performed **no** Monte Carlo or weight simulation, rank-stability analysis, deployment comparison or tuning, built no Power BI artifact, and makes no robustness or causal claim.

## 13. Limitations

The register entries that matter most for interpreting baseline_v1:

| ID | Limitation |
|---|---|
| A-049 | Percentiles lose magnitude |
| A-050 | Equal weights are not equal influence |
| A-051 | The strict eligibility rule leaves Atlanta's drone C4 incomplete |
| A-052 | Even a small unknown population share blocks a market's score |
| A-053 | The weight limit is scored only where PDDs are authorized |
| A-054 | C4 variance dominance |
| A-055 | Absence is scored the same as explicit restriction |
| A-056 | Robotaxi driverless and commercial dimensions are correlated; local authority is unconditional |
| A-057 | Seed landing |
| A-042 | Blocked hosts |
| A-047 | No municipal ordinances |
| A-002 | A CBSA is not a service area |
| A-010 | Hub enplanements include connecting passengers |

## 14. Phase 8 handoff (not executed in Phase 7)

| # | Sensitivity | Starting point |
|---|---|---|
| 1 | Alternative normalization: winsorized min-max (e.g. 5th–95th percentile), robust z (median/MAD) | `raw_value` / `transformed_value` in `FCT_FEATURE_SCORES` |
| 2 | Component-weight scenarios (business-priority profiles) | `FCT_COMPONENT_SCORES` |
| 3 | Monte Carlo / Dirichlet (simplex) random component weights | same |
| 4 | Regulatory uncertainty for the unscored markets: treat each LOW / unverified record as favorable, as unfavorable, and at its coded status; the confidence-only eligibility reading (A-051); Nevada unadjusted (A-046); absence partial credit (A-043/A-055) | `INT_REGULATORY__MARKET_STATE_EVIDENCE`, `regulatory_scope_adjustments` |
| 5 | Drop-one: income (PF05) vs occupational wage (PF09/PF10); robotaxi commercial vs driverless (A-056) | feature contract |
| 6 | Airport A4 (80 km radius) in place of A1 (PX03) | DIAGNOSTIC feature |
| 7 | Density backup: block-group SLD density (PX02) or raw MSA density (PX01) | DIAGNOSTIC features |
| 8 | Weather station / wind: W2/W3 station variants, p90 wind (PX04) | DIAGNOSTIC feature, A-007 |
| 9–12 | For every market and mode: top-5 frequency, mean and median rank, rank standard deviation, best and worst rank | scenario outputs |
| 13 | Deployment reasonableness validation, **only after** the Phase 8 results are frozen | docs/deployment_validation_plan.md |
