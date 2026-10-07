# Power BI Dashboard Specification (Phase 9)

**Status:** Phase 9 deliverable (in review). This is a specification only; the report is built by hand ([powerbi/BUILD_GUIDE.md](../powerbi/BUILD_GUIDE.md)).

**Question the report answers:**

> *"Which markets look attractive for each autonomous mode, and how robust is that conclusion?"*

**Global rules:**
- **Modes.** One mode at a time. Never one "best city overall" and never a combined score.
- **Rank labels.** Every rank is labelled **Baseline rank** or **Sensitivity / scenario rank**.
- **Unranked markets.** Markets with incomplete regulatory evidence show "Not ranked (regulatory evidence incomplete)" and their regulatory range, never a 0.
- **Deployment** appears only on validation visuals, never next to a score as if it were an input.
- **Frequencies** read as "share of tested weight configurations".

## Page 1 — Executive Overview

**Header:** *Autonomous Mobility Expansion Strategy*
**Subtitle:** *Data-driven market prioritization across 35 U.S. metros*
**Slicer:** Mode, single select; default Robotaxi.

| Element | Content | Measures / fields |
|---|---|---|
| KPI cards (4) | 35 Markets · 3 Mobility Modes · **Most Robust Leader** (selected mode) · **Markets Scored** with complete regulatory evidence (e.g. "29 of 35") | `Markets Evaluated`, `Most Robust Leader`, `Markets With Complete Score`, `Share Of Markets Scored` |
| U.S. map | Bubble map at `latitude`/`longitude`. Size = Top-5 Frequency; colour = Baseline Rank (sequential blue, darker = better); grey = not ranked | `Top 5 Frequency`, `Selected Baseline Rank` |
| Top markets bar/table | Top 10 by Baseline Rank: Baseline Rank, Top-5 Frequency, Rank Range, flags | `Selected Baseline Rank`, `Top 5 Frequency`, `Rank Range`, `Robustness Flags` |
| Decision insight panel | Two text boxes: **Robust findings** and **Assumption-dependent findings** (text below) | static text from [robustness_and_sensitivity.md](robustness_and_sensitivity.md) §8 |

**Insight text** (from the committed Phase 8 findings):
- **Robust.** Robotaxi: San Francisco, Los Angeles and San Diego are top 5 in at least 96% of 10,000 weight configurations and in every named test. Drone: Pittsburgh, Portland and Dallas are top 10 in 94–96%.
- **Assumption-dependent.**
  - Robotaxi ranks 4–10 swing 10–13 ranks with weights.
  - Boston and New York (robotaxi) depend on unresolved state law.
  - Sidewalk leaders change under a regulatory priority.
  - 10 drone markets, including Los Angeles, San Francisco and Sacramento, are unscored pending California and other state evidence.

## Page 2 — Robotaxi

Mode is fixed to ROBOTAXI (page filter). The Market slicer is single select.

| Element | Content |
|---|---|
| Headline text | "San Francisco, Los Angeles and San Diego remain the stable leading group." This matches Phase 8; re-check after any refresh |
| Ranking table | All 35 markets. Baseline Rank (or "Not ranked"), Baseline Score, Mean / Best / Worst sensitivity rank, Top-5 and Top-10 Frequency, flags. Default sort: Baseline Rank, then Mean Rank |
| Rank-range chart | Horizontal dumbbell or error bar per market: `Rank 90% Low` to `Rank 90% High`, with a dot at Baseline Rank |
| Regulatory uncertainty | Dumbbell of `Regulatory Rank Low` to `Regulatory Rank High` with three markers (pessimistic, neutral, optimistic). **Boston must visibly show 4–20**, and New York 7–18; not a single rank |
| Component profile | Clustered bar of `Component Score` C1–C4 for the selected market vs the mode median (no C5) |
| Feature decomposition | Waterfall or bar of `Feature Contribution` by feature for the selected market (adds to the baseline score), plus `Feature Points Below Maximum` |
| Regulatory evidence | Text card with `regulatory_decomposition` and `regulatory_unverified_states` of the selected market |

## Page 3 — Autonomous Delivery

**Mode slicer:** SIDEWALK_DELIVERY or DRONE_DELIVERY, single select. Never both, and never a combined score.

| Element | Content |
|---|---|
| Ranking table | As on page 2, for the selected delivery mode |
| Robustness | Top-5 Frequency bar (top 15) and rank 90% interval |
| Operating environment | Feature scores for the C2 features (precipitation days, 90°F days, snowfall; drone: mean wind) for the selected market vs mode median |
| Infrastructure & mode fit | C5 score and its feature: walkability (sidewalk) or single-family share (drone) |
| Regulatory uncertainty | Rank range across the three bounds (for drone, many large-market ranges: Los Angeles, San Francisco, Sacramento) |
| Deployment validation | Separate strip plot: Top-10 Frequency by `deployment_status`. Title: "External validation: not model accuracy" |

## Page 4 — Market Comparison

**Slicers:** Mode (single select) and Market (multi-select, 2–4 markets, enforced with a visual-level Top N filter or user guidance).

| Element | Content |
|---|---|
| Component profile | Clustered bar of `Component Score` per component, one colour per market. Robotaxi shows C1–C4 only |
| Rank statistics table | Baseline Rank, Mean, Median, Best, Worst, Rank Range, Top-5 / Top-10 Frequency, Regulatory Rank Low–High |
| Strengths and constraints | Table of `strongest_feature`, `weakest_feature`, `top_positive_contributors`, `top_constraints` (the actual point contributions) |
| Regulatory evidence | `regulatory_decomposition`, coverage %, unverified states |
| Deployment presence | `Deployment Present` and `Deployment Status`, labelled "external validation" |

## Page 5 — Scenario Simulator

**Slicers:**
- Mode, single select;
- **Named scenario** (Scenario[scenario_name], single select; robotaxi lists 5 scenarios, others 6);
- five What-If weight sliders (W C1–W C5). W C5 is greyed and ignored for robotaxi.

| Element | Content |
|---|---|
| Banner | Measure `Scenario Label`: **"SCENARIO RESULT — NOT BASELINE"** on the custom-weight visuals |
| Named-scenario ranking | `Scenario Rank`, `Scenario Score`, `Scenario Rank Movement vs Neutral`, `Scenario Score Movement vs Neutral` |
| Custom-weight ranking | `Dynamic Rank`, `Dynamic Scenario Score`, `Dynamic Rank Movement vs Baseline`, `Dynamic Score Movement vs Baseline` |
| Weight display | Donut or bar of `Normalized Weight C1–C5` (only active components) |
| Note | "Equal sliders reproduce the Phase 7 baseline. Unranked markets stay unranked under any weights." |

## Page 6 — Methodology / Data Quality

Keep it concise: one text panel and two small visuals.

| Topic | Content |
|---|---|
| Universe | 35 fixed MSAs (PEP Vintage 2025), keyed by CBSA |
| Data | Public sources (Census, BLS, NOAA, FAA, EPA, state law). Snowflake RAW → dbt → curated marts |
| Features | 10 approved features per mode; robotaxi has no C5 |
| Scoring | Percentile scores; equal weights within and across components (baseline) |
| Robustness | 10,000 Dirichlet weight configurations per mode; normalization and methodology alternatives; regulatory bounds |
| Regulation | Verified state evidence only. Low-confidence evidence leaves a market **unranked**, never zero |
| Deployment | Compared only after the model was frozen. External validation, not accuracy |
| Limitations | CBSA ≠ service area; no municipal ordinances; state evidence gaps (MA, NJ, OH robotaxi; CA, GA, IL, MA, TN drone; IN, TN sidewalk); scores are relative and mode-specific |
| Visuals | Bar of `Share Of Markets Scored` by mode; table of the regulatory unverified states |

## Interactions and tooltips

- **Cross-filtering.** The map and the tables cross-filter each other. Leave the rank-range visuals as filter targets only, so they don't filter the tables.
- **Tooltip page (Market tooltip).** Baseline Rank, Top-5 Frequency, Rank Range, Regulatory Rank Low–High and Deployment Status for the hovered market.
- **Drill-through.** From any market row on pages 1–3 to page 4, with that market pre-selected.
