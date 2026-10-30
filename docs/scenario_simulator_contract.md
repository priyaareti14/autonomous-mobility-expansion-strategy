# Scenario Simulator Contract (Power BI handoff, Phase 8)

**Status:** Phase 8 deliverable. This is a **contract only**, written before the report existed. The final PBIX implements the named business-priority and regulatory scenarios only; the custom What-If weight table and user-entered weight vectors described here were not implemented.

## 1. The What-If scenario table

**File:** `outputs/phase8/scenario_simulator_contract.csv`
**Grain:** one row per mode × named scenario (5 robotaxi + 6 sidewalk + 6 drone = 17 rows).

| Column | Type | Rule |
|---|---|---|
| `mode` | text | ROBOTAXI, SIDEWALK_DELIVERY or DRONE_DELIVERY |
| `scenario_id` | text | Unique, e.g. `SIDEWALK_REGULATORY_PRIORITY` |
| `scenario_name` | text | Display name |
| `c1_weight` … `c5_weight` | decimal 0–1 | Weights of the active components |
| `description` | text | What the scenario assumes; every row says it is an assumption, not an estimate of preferences |

**Invariants** (checked by `run_phase8_sensitivity.py`):
- The active component weights of every row sum to exactly 1.
- No weight is negative.
- **Robotaxi `c5_weight` is always null.** C5 is structurally absent (A-039), so there is no robotaxi INFRASTRUCTURE_PRIORITY scenario. The simulator must never default a missing weight to 0 or treat C5 as present.
- `NEUTRAL` equals the Phase 7 baseline weights (25% for robotaxi; 20% for sidewalk and drone) and reproduces the baseline ranks exactly.

**Scoring rule for any user-entered weight vector w** (the simulator must reproduce the baseline when w = NEUTRAL):

```
score(market, mode) = Σ over active components c of  w_c × component_score(market, mode, c)
```

- `component_score` comes from `outputs/phase7/component_scores.csv` (or `ANALYTICS.FCT_COMPONENT_SCORES`).
- Markets whose C4 is incomplete have no score under any weights. Their regulatory bounds are shown from `regulatory_uncertainty.csv` instead.
- Ranks use standard competition ranking among markets with a score, with ties at 6 decimals.
- User weights must be renormalized to sum to 1 over the active components before scoring.
- **Scores are never combined across modes.**

## 2. Compact datasets for the future semantic model

All files are small, deterministic CSVs with one documented grain. No 10,000-draw matrix is exported; the seed reproduces it.

| Dataset | File | Grain | Rows |
|---|---|---|---|
| Baseline scores and ranks | `outputs/phase7/{robotaxi,sidewalk,drone}_baseline.csv` | market (per mode) | 35 each |
| Component scores | `outputs/phase7/component_scores.csv` | market × mode × component | 490 |
| Feature contributions | `outputs/phase7/feature_scores.csv` | market × mode × input | 1,295 |
| Regulatory coverage | `outputs/phase7/regulatory_coverage.csv` | market × mode × dimension | 245 |
| Robustness statistics | `outputs/phase8/robustness_summary.csv` | market × mode | 105 |
| Weight-sensitivity detail | `outputs/phase8/weight_sensitivity_summary.csv` | market × mode × regulatory scenario | 190 |
| Business-scenario results | `outputs/phase8/business_priority_scenarios.csv` | market × mode × scenario | 595 |
| Regulatory uncertainty | `outputs/phase8/regulatory_uncertainty.csv` | market × mode | 105 |
| Normalization and methodology tests | `outputs/phase8/normalization_sensitivity.csv`, `methodology_sensitivity.csv` | market × mode × test | 315 / 840 |
| Deployment validation status | `outputs/phase8/deployment_validation.csv` | market × mode | 105 |
| Deployment mismatch review | `outputs/phase8/deployment_mismatch_review.csv` | market × mode (mismatches only) | 34 |

**Required display rules:**
- Label ranks as **baseline rank** or **sensitivity rank**.
- Label frequencies as "share of tested weight configurations".
- Show deployment presence only as a separate external-validation layer, never as an input or a target.

## 3. Snowflake handoff

**Done in Phase 9:** these summaries now land as generated dbt seeds and `ANALYTICS.PBI_*` tables ([powerbi_semantic_model.md](powerbi_semantic_model.md)). **Phase 8 itself wrote nothing to Snowflake.** Write-back of these compact summaries was the Phase 9 scope ("analytical output write-back + reconciliation"). When it happens, it should land through the controlled dbt seed architecture as small reproducible tables, never as ad hoc tables or Monte Carlo rows:
- market × mode robustness;
- market × mode × named scenario;
- market × mode regulatory uncertainty;
- deployment validation summary.
