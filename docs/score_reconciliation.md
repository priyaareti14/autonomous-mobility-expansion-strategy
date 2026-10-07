# Score Reconciliation (Phase 7, baseline_v1)

**Status:** Phase 7 deliverable (in review) · **Model-input commit:** `55b1cb4`

Every published score is an exact, reproducible sum of its parts. Two independent mechanisms prove it:
1. **dbt tests**, which run on every `dbt build` against the Snowflake tables;
2. **an independent Python recomputation** (`scripts/run_phase7_scoring_qa.py`), which rebuilds every number from the source files and the Phase 6 feature marts *without* reading the dbt scoring logic, then compares.

**Tolerance:** 1e-6 on the 0–100 scale (`score_tolerance` in `dbt_project.yml`). All arithmetic runs in FLOAT; Snowflake NUMBER division keeps only 6 decimals and would leave a 1e-4 residue (it did in the first build, and was fixed before any result was read).

## 1. Identities

| Level | Identity | dbt test | Python check |
|---|---|---|---|
| Feature | `feature_score` = average-rank percentile (reversed for LOWER_IS_MORE_FAVORABLE) | `assert_feature_score_direction` (monotone in value, equal values equal scores, mean 50) | recomputed with `pandas.rank(method="average")` |
| Feature weights | Σ `feature_weight` = 1 in every scored component | `assert_model_weights_sum_to_one` | yes |
| Component | `component_score` = Σ `weighted_feature_contribution` | `assert_score_reconciliation` | yes |
| Component weights | Σ `component_weight` = 1 per market × mode (robotaxi 4 components, others 5) | `assert_model_weights_sum_to_one` | yes |
| Overall | `baseline_readiness_score` = Σ `component_contribution` = Σ feature `contribution_to_overall` | `assert_score_reconciliation` | yes |
| Regulatory shares | favorable + unfavorable + unknown/LOW + not applicable = 1; unfavorable = absence + explicit + unclear + scope-limited | `assert_regulatory_shares_reconcile` | recomputed from `evidence/regulatory_evidence.csv` directly |
| Rank | standard competition rank on the score (6 decimals), complete markets only | `assert_baseline_rank_valid` | `rank(method="min")` |
| Marts | each mode mart = `FCT_READINESS_BASELINE` and `FCT_COMPONENT_SCORES` | `assert_score_reconciliation` | yes |

## 2. Independent recomputation: results

`outputs/phase7/score_reconciliation.csv` (40 checks, all PASS):

| Check | Rows compared | Max absolute difference |
|---|---|---|
| Feature scores, raw and transformed values (vs Phase 6 mode marts) | 1,050 | ≤ 1e-12 |
| Regulatory shares (favorable, unfavorable, unknown, not applicable) and dimension scores | 245 | ≤ 1e-12 |
| State evidence classes (seed path vs evidence-file path) | 357 | exact |
| Component scores and contributions | 490 | ≤ 1e-12 |
| Baseline scores, non-regulatory scores, baseline ranks | 105 | ≤ 1e-12 |
| Robotaxi eligibility vs `outputs/phase65/phase7_regulatory_eligibility.csv` | 93 | 93 / 93 agree |
| Market status composition vs `outputs/phase65/market_regulatory_summary.csv` | 245 | 0 mismatches |
| Frozen inputs unchanged since 55b1cb4; seeds match sources | 3 + 2 seeds | exact |

PASS/FAIL is decided on the unrounded difference against the 1e-6 tolerance. The measured maxima were at most 1.42e-14. In the exported CSV, any difference below **1e-12 is written as exactly 0**. That floor is for export and reporting only: it removes insignificant floating-point summation residue, which varies between dbt builds because Snowflake's summation order varies, and it does not weaken the reconciliation test (§5).

## 3. Evidence boundaries proved by test

- **No LOW or unverified evidence in the base score.** `assert_low_evidence_never_enters_base_score` checks that:
  - every market with an UNKNOWN_OR_LOW_CONFIDENCE state row has no C4 and no baseline score;
  - no incomplete dimension carries a score;
  - the weight-limit percentile uses only fully verified markets;
  - the 10 Phase 6.5b sensitivity-only records are never classed as verified.
- **Incomplete C4 means NULL score and rank.** `assert_incomplete_c4_has_no_base_score` checks that the score and rank are NULL, that complete markets have both, and that no input of an incomplete market carries an overall contribution.
- **Robotaxi C5 absent:** `assert_robotaxi_c5_absent`.
- **Contracts frozen:** `assert_feature_scores_match_contract` (both directions).
- **No deployment fields** in any scoring relation: `assert_no_deployment_evidence_in_feature_layer`, extended.
- **No cross-mode combined score:** `assert_no_cross_mode_combined_score`.

## 4. How to reproduce

```
python scripts/build_regulatory_seed.py --check     # seeds match evidence/ and config/
python scripts/run_dbt.py build --threads 2          # builds and tests every model (680 nodes; Phase 7 adds 89)
python scripts/run_phase7_scoring_qa.py              # independent recomputation, exports, figures
```

## 5. Reproducibility: what was verified (2026-10-07)

**Verified result.** The 22 Phase 7 output files are byte-identical in all of these comparisons:
- across two independent fresh `dbt build --threads 2` runs, each followed by the QA script (22 of 22);
- across back-to-back QA runs on the same build (22 of 22);
- in a further QA run after the full validation suite (22 of 22).

The files are 13 CSVs, `model_metadata.json` and the 8 PNG figures. matplotlib's Agg PNG writer embeds no timestamp, so the images are byte-stable without any special handling. All runs passed 40/40 QA checks, and every dbt build passed 680/680.

**What makes the outputs deterministic.** None of these steps changes a score, weight, rank or tolerance:

| Mechanism | Where | What it guards against |
|---|---|---|
| Every read uses an explicit `ORDER BY` on the relation's grain; every export is sorted on its key with a stable sort | QA script | Snowflake row order |
| `c4_unverified_states` is a true set: states are normalized (`upper(trim())`), de-duplicated before aggregation, and listed with `LISTAGG(…) WITHIN GROUP (ORDER BY state_usps)`. It is NULL when no state is unverified | `FCT_READINESS_BASELINE`; tested by `assert_c4_unverified_states_is_sorted_set` | Ordering and duplicates (New York was "NJ, NY, NJ"; it is now "NJ, NY") |
| Spearman correlation: component scores are rounded to 9 decimals before ranking, ρ is exported with fixed 12 decimals, and the figure is drawn from that table | QA diagnostics only | Last-bit float differences between builds breaking genuine ties (ρ had moved by up to 0.0092) |
| Adjacent score gaps: scores rounded to 9 decimals before taking gaps, gaps rounded to 9 decimals, `+ 0.0` turns −0 into 0 | `score_distribution.csv` only | −0 vs 1.4e-14 residues between tied scores |
| `max_abs_diff` below 1e-12 is exported as 0.0 (an export floor only; PASS/FAIL uses the unrounded difference and the 1e-6 tolerance) | `score_reconciliation.csv` only | Summation residues of 1e-16 to 1.4e-14 that vary between builds |

**Metadata is deterministic.** `model_metadata.json` describes the frozen model-input snapshot only:
- `model_version` = baseline_v1;
- `git_input_commit` = 55b1cb4;
- `regulatory_evidence_as_of` and `deployment_evidence_as_of` = 2026-10-05;
- methods, contract checksums, dbt objects and QA counts.

It contains no run date and no repository HEAD, so it does not change when the calendar date changes or after Phase 7 is committed. The script prints the run time and HEAD to the console only.
