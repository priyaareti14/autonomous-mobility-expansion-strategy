# Deployment Validation Plan (Phase 6.5 → Phase 8)

**Status:** Phase 6.5 deliverable · **Deployment evidence as of:** 2026-10-05 (`DEPLOYMENT_EVIDENCE_AS_OF`)

## 1. Purpose and the one rule

`evidence/deployment_evidence.csv` records where autonomous-mobility operators publicly run, test, have announced or have ended services. Its only purpose is **external validation**, answering one question:

> *Do externally observed deployment choices broadly align with the model?*

**The one rule: deployment evidence never enters the model.**

| Not acceptable | Acceptable |
|---|---|
| Tuning weights until known deployment markets rank highly | Comparing model-high markets with observed deployments, after the model is frozen |
| Selecting or dropping features because they match or mismatch operator locations | Identifying surprising mismatches in both directions |
| Using deployment presence as ground truth, a label or a target | Discussing whether operators appear to favour similar conditions to the model's components |
| Coding any regulatory field from deployment presence (a Waymo service does not make a state's law favourable) | Investigating outliers, with explanations recorded as findings rather than model changes |
| Adding any deployment-derived column to a feature mart | |

Enforcement:
- `dbt/tests/assert_no_deployment_evidence_in_feature_layer.sql` fails if any operator or deployment term appears in the columns of the three mode marts or DIM_FEATURE, if DIM_FEATURE cites deployment sources (S-35 to S-39), or if a deployment table appears in ANALYTICS.
- `scripts/validate_evidence.py` rejects operator sources (`OPERATOR_OFFICIAL`) as regulatory evidence.

## 2. Why deployment is not ground truth

Deployment choices reflect much more than market readiness:
- company headquarters and history;
- partner availability (Uber, Lyft, Walmart, DoorDash);
- fleet supply and capital;
- mapping investment already made;
- regulatory relationships;
- the order in which a company happens to scale.

The modelled universe also excludes markets where operators are present: San Jose (41940, rank 36), College Station TX and Lockeford CA (A-001). A mismatch is therefore information to explain, not an error to fix.

## 3. Phase 8 procedure (after the readiness model and sensitivity analysis are frozen)

1. **Freeze first.** The Phase 7 model and its Phase 8 sensitivity results are frozen, with their git commit recorded, before any deployment comparison is run.
2. **Current-presence indicator per market and mode,** derived only for the comparison:
   - count `COMMERCIAL` and `LIMITED_COMMERCIAL` rows whose `end_date` is blank and whose `market_resolution` is not `OUTSIDE_UNIVERSE`;
   - report `TESTING`, `PILOT` and `ANNOUNCED` separately;
   - exclude `ENDED` and `PAUSED`.
3. **Comparison.** Cross-tabulate model tiers (from the frozen output) with presence. Report descriptive agreement (e.g. the share of present markets in the model's upper group) and list every mismatch in both directions:
   - "model-high, no deployment";
   - "deployment, model-low".
4. **Mismatch review.** For each mismatch, record plausible non-model explanations from §2, and any model limitation it reveals (e.g. A-039, the empty robotaxi C5 component).
5. **No feedback.** Findings are documented in the case study. Any model change prompted by them would be a new, separately justified phase decision, with the deployment comparison re-run afterwards, and disclosed.

## 4. Interpreting the evidence correctly

- **Geography is partial.** Most services cover a core part of a CBSA (`WITHIN_MARKET_PARTIAL`, `CITY_ONLY`). Presence means "some service in the market", never "the market is served".
- **One market can hold several rows** (operators, platforms, phases). Count markets, not rows.
- **Status is as of 2026-10-05.** Historical services are kept as separate `ENDED` rows; announcements are `ANNOUNCED`, not service.
- **Evidence quality varies.** `verification_status` distinguishes operator and regulator sources (`VERIFIED_PRIMARY`) from press- or Wikipedia-based rows (`SECONDARY_ONLY`), which are mostly historical (Cruise, Argo) or testing-stage (Zoox). The comparison must report results with and without `SECONDARY_ONLY` rows.
- **Platform rows** (Uber, Lyft, DoorDash, Walmart) describe distribution, not a separate deployment.

## 5. What the curated evidence contains (as of 2026-10-05)

**Size and coverage:**
- **180 records, 23 operators** (`evidence/deployment_evidence.csv`).
- **Robotaxi:** Waymo, Zoox, Tesla, May Mobility, Avride, Motional, Nuro; Cruise and Argo AI (ended).
- **Sidewalk:** Serve Robotics, Coco Robotics, Avride, Starship Technologies, Kiwibot, Cartken; Amazon Scout (ended).
- **Drone:** Wing, Zipline, Amazon Prime Air, Flytrex, Manna, Matternet; DroneUp (ended).

**Markets with current `COMMERCIAL` or `LIMITED_COMMERCIAL` service** (open-ended, inside the universe):

| Mode | Markets |
|---|---|
| Robotaxi | **15**: Atlanta, Austin, Dallas, Denver, Houston, Las Vegas, Los Angeles, Miami, Nashville, Orlando, Phoenix, San Antonio, San Diego, San Francisco, Tampa |
| Sidewalk delivery | **8**: Atlanta, Chicago, Dallas, Los Angeles, Miami, New York (Jersey City), Philadelphia, Washington |
| Drone delivery | **11**: Atlanta, Charlotte, Cleveland, Dallas, Detroit, Houston, Kansas City, Orlando, Phoenix, San Antonio, Tampa |

**Historical, paused and ended** records are kept separately: 30 rows (robotaxi 17, sidewalk 7, drone 6). Examples: Cruise's 2023 suspension, Argo AI's 2022 shutdown, Starship's 2026 US campus wind-down, Amazon Scout, and DroneUp's hub closures.

**Market resolution** is mostly partial:

| Resolution | Rows |
|---|---|
| `WITHIN_MARKET_PARTIAL` | 98 |
| `CITY_ONLY` | 51 |
| `CAMPUS_OR_SITE` | 8 |
| `MULTI_MARKET` (e.g. Bay Area service reaching San Jose, outside the universe) | 6 |
| `OUTSIDE_UNIVERSE` | 5 |
| `UNRESOLVED` | 12 |

**Verification:** 115 records are `VERIFIED_PRIMARY` (operator, SEC-filing or regulator sources) and 65 are not (A-048).
