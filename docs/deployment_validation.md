# Deployment Validation: External Reasonableness Check (Phase 8)

**Status:** Phase 8 deliverable (in review) · **Deployment evidence:** `evidence/deployment_evidence.csv`, committed in Phase 6.5, evidence date **2026-10-05**, not refreshed · **Method:** [deployment_validation_plan.md](deployment_validation_plan.md)

## 1. What this is, and what it is not

This compares where operators publicly run commercial services with where the model places markets. It is an **external reasonableness check**:
- It is **not model accuracy**.
- Deployment presence is **not ground truth**.
- A market with **no recorded deployment is not evidence of unsuitability**. Deployment reflects operator footprint, partnerships, capital, sequencing and city-level design, which this model does not observe.

## 2. Freeze and no-leakage proof

The comparison runs in its own script (`scripts/run_phase8_deployment_validation.py`), strictly after the sensitivity analysis.

1. **Guarded sensitivity code.** `scripts/run_phase8_sensitivity.py` installs a file-open guard that raises an error if anything tries to open a deployment file. A self-check also confirms its source never names the deployment evidence file (`qa_checks_sensitivity.csv`). No sensitivity output has a deployment column.
2. **Freeze before reading.** The validation script checks every sensitivity output against the SHA-256 manifest in `outputs/phase8/model_metadata.json` before it reads any deployment record: 23 files, all matching.
3. **Committed evidence only.** The deployment file must be the committed Phase 6.5 version, with no local edits and the evidence date on every record.
4. **Freeze after.** After the comparison, the manifest is checked again and is unchanged. Results are in `deployment_qa_checks.csv`, 5 of 5 PASS.
5. **dbt guard.** `assert_no_deployment_evidence_in_feature_layer` still covers every feature and scoring relation.

Nothing in this comparison changes, or can change, a weight, feature, score or rank.

## 3. Cohorts (`deployment_cohorts.csv`)

**Primary cohort:**
- status `COMMERCIAL` or `LIMITED_COMMERCIAL`;
- open-ended (`end_date` blank);
- resolved to one in-universe market (`WITHIN_MARKET_PARTIAL` or `CITY_ONLY`).

**Variants:**
- *primary, verified*: `VERIFIED_PRIMARY` records only (A-048);
- *broad*: also `CAMPUS_OR_SITE` and `MULTI_MARKET`.

**Kept separately and never merged into the primary cohort:** `PILOT`, `TESTING`, `ANNOUNCED`, `PAUSED`, `ENDED`, `UNKNOWN`. Each market × mode is placed in one cohort, in priority order:
1. current commercial;
2. pilot, testing or announced;
3. ended or paused only;
4. other record only;
5. no recorded deployment.

**Geography.** The dataset has **no whole-market category**. Every in-universe record covers part of a CBSA, so presence means "some service in the market", never "the market is served". `OUTSIDE_UNIVERSE` and `UNRESOLVED` records have no market and are excluded. Markets are counted, not rows.

| Mode | Current commercial markets (primary) | Primary, verified only | Of which unscored (C4 incomplete) |
|---|---|---|---|
| Robotaxi | 15 | 14 | 0 |
| Sidewalk | 8 | 7 | 1 (Chicago) |
| Drone | 11 | 11 | 1 (Atlanta) |

## 4. Descriptive comparison (`deployment_validation_summary.csv`, `deployment_validation_by_cohort.csv`)

Primary cohort, among ranked markets:

| Measure | Robotaxi | Sidewalk | Drone |
|---|---|---|---|
| Median baseline rank: deployment markets | 9 | 10 | 10 |
| Median baseline rank: no recorded deployment | 22.5 | 18.5 | 15 |
| Median mean Dirichlet rank: deployment / none | 11.5 / 21.1 | 11.2 / 16.3 | 12.9 / 14.2 |
| Median top-10 frequency: deployment / none | 0.45 / 0.09 | 0.44 / 0.21 | 0.37 / 0.27 |
| Share of deployment markets in the baseline top 5 | 33% | 14% | 20% |
| Share of deployment markets in the baseline top 10 | 60% | 57% | 50% |
| Baseline top-5 markets with a deployment | 5 of 5 | 1 of 5 | 2 of 5 |
| Baseline top-10 markets with a deployment | 9 of 10 | 4 of 10 | 5 of 10 |
| Share of ranked markets with a deployment | 52% | 23% | 40% |

The verified-only variant gives the same picture: robotaxi median rank 8.5, top-10 share 64%.

**Reading:**
- **Robotaxi.** Current commercial markets sit clearly higher in the model than markets without deployments, and all 5 baseline top-5 markets have one. Markets with only testing, pilot or announced activity have a median baseline rank of 22.
- **Sidewalk and drone.** Deployment markets are higher on median, but the separation is smaller. Drone medians are 10 vs 15 for baseline rank, and only 12.9 vs 14.2 for mean Dirichlet rank. The model's sidewalk top 5 is mostly California markets without a PDD statute or a recorded commercial service.

## 5. Mismatch review (`deployment_mismatch_review.csv`)

**Thresholds** (fixed in advance; recorded in `deployment_validation_manifest.json`):
- *high model* = top 10 in at least 50% of weight draws;
- *low model* = top 10 in at most 10% of draws.

Explanations are **candidate prompts for review**, not findings, and no weight was changed to remove any mismatch.

| Category | Robotaxi | Sidewalk | Drone |
|---|---|---|---|
| High model, deployment present | San Francisco, Los Angeles, San Diego, Denver, Miami, Phoenix, Tampa | Los Angeles, Washington, Miami | Dallas, Detroit, Houston, Phoenix |
| High model, **no recorded deployment** | Sacramento (testing, pilot or announced recorded) | San Francisco, Seattle (past service ended), Las Vegas, San Diego, Portland, Boston, Denver | Pittsburgh (nothing recorded), Portland and Austin (testing, pilot or announced recorded), Washington |
| Low model, **deployment present** | Houston (weakest: C3 economic), San Antonio (C1 demand), Nashville (C1 demand) | Atlanta (weakest: C5 walkability) | Charlotte, Cleveland (weakest: C4 regulatory; state law silent on preemption) |
| Unscored (C4 incomplete), deployment present | none | Chicago | Atlanta |

**Interpretation of the mismatches:**
- **Low model, deployment present.** These are markets where operators chose something the model does not reward:
  - *Robotaxi:* Waymo and Tesla in Texas and Tennessee metros, where the model's demand and economic components are middling, while state law is favorable.
  - *Sidewalk:* Serve in Atlanta, where walkability is low.
  - *Drone:* Wing and Zipline in Charlotte and Cleveland, where state preemption of local rules is not addressed.

  Plausible non-model explanations:
  - operator headquarters and expansion sequencing;
  - partner networks (Uber, DoorDash, Walmart);
  - city-level permits that the state variables do not capture;
  - service areas far smaller than the MSA. Most rows are `WITHIN_MARKET_PARTIAL` or `CITY_ONLY`, and many involve a single operator.
- **High model, no recorded deployment.** These are model-favoured markets without a current commercial service. They are the candidates the model surfaces. They are *not* errors, and they need Phase 9+ business review.
  - Portland and Austin (drone) and Sacramento (robotaxi) already show testing, pilot or announced activity. Pittsburgh, the drone baseline leader, has no recorded drone activity of any kind.
  - The sidewalk gap is concentrated in California and Seattle, where the model's top markets lack PDD statutes (C4 = 0, or low for Seattle).
- **Unscored markets with deployments.** Atlanta (drone) and Chicago (sidewalk) show that the strict evidence rule leaves real deployment markets unranked. That is consistent with A-051 and A-052, not a model failure.

## 6. Limitations

- Deployment evidence is partial and dated 2026-10-05. 65 of the 180 records are not primary-verified (A-048).
- CBSA presence is not service coverage (A-002).
- Thresholds for "high" and "low" model positions are fixed conventions (A-065).
- No causal claim is made in either direction.
