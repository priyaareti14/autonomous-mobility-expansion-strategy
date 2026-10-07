# KPI Dictionary (Phase 9)

Every KPI shown on the dashboard. The DAX is in [powerbi/measures.md](../powerbi/measures.md). Field-level documentation is in [powerbi/data_dictionary.csv](../powerbi/data_dictionary.csv).

**Filter behaviour.** All market-level KPIs require exactly **one market and one mode** in context, and return blank otherwise. A KPI is never aggregated across markets or modes.

| KPI | Business definition | Formula | Source table | Grain | Filter behaviour | Limitations |
|---|---|---|---|---|---|---|
| **Baseline Score** | How ready a market looks for one mode under the approved baseline model, relative to the other 34 markets | Σ component score × equal component weight (Phase 7) | Baseline | market × mode | One market, one mode; blank when not determinable | Relative and mode-specific; blank ≠ unready |
| **Baseline Rank** | Position among markets with a complete baseline score | Competition rank of the baseline score (ties at 6 decimals) | Baseline | market × mode | Same | Covers 29 / 31 / 25 markets; not a recommendation until read with robustness |
| **Mean / Median Sensitivity Rank** | Typical position when component priorities vary | Mean / median rank over 10,000 Dirichlet(1) weight draws | Robustness | market × mode | Same | Treats all weight mixes as equally plausible |
| **Best / Worst Rank** | Most and least favourable position under any tested weight mix | Min / max rank over the 10,000 draws | Robustness | market × mode | Same | Extreme weightings included |
| **Rank Range** | How far the rank can move with weights | Worst − Best rank | Robustness | market × mode | Same | Sensitive to extreme draws; use the 90% interval for typical spread |
| **Rank Standard Deviation** | Typical rank volatility across weight mixes | SD of the 10,000 draw ranks | Robustness | market × mode | Same | |
| **Top-5 Frequency** | How often the market lands in the top 5 when priorities vary | Share of the 10,000 draws with rank ≤ 5 | Robustness | market × mode | Same | **Not** a probability of being best; frequency across tested configurations |
| **Top-10 Frequency** | As above, top 10 | Share of the 10,000 draws with rank ≤ 10 | Robustness | market × mode | Same | Same |
| **Robustness Flags** | Approved Phase 8 patterns | CONSISTENT_TOP_PERFORMER, WEIGHT_SENSITIVE, NORMALIZATION_SENSITIVE, METHODOLOGY_SENSITIVE, REGULATION_SENSITIVE (thresholds in A-066) | Robustness | market × mode | Same | Aids, not tiers; no composite score |
| **Regulatory Rank Low / High** | Best and worst rank across the pessimistic, neutral and optimistic bounds for unresolved state law | Min / max of the three bound ranks (all 35 markets ranked) | Regulatory Uncertainty | market × mode × bound | One market, one mode; ignores the bound slicer | Bounds, not forecasts; never averaged |
| **Regulatory Rank Range** | How much unresolved regulation could move the market | High − Low | Regulatory Uncertainty | market × mode | Same | Complete markets can shift slightly as unscored markets enter the ranking |
| **Regulatory Coverage %** | Share of the market's population whose regulatory status is verified | Mean evidence coverage across the mode's regulatory dimensions | Baseline | market × mode | One market, one mode | Below 100% ⇒ market unranked |
| **Markets Scored** | How many markets have a complete baseline score | Count of markets with `score_complete_flag` | Baseline | mode | Mode filter | |
| **Most Robust Leader** | Market(s) with the highest top-5 frequency in the mode | argmax Top-5 Frequency (ties listed) | Robustness | mode | Mode filter | A frequency leader, not "the best city" |
| **Component Score / Contribution** | Score of a readiness component and the points it adds | Phase 7 component score; score × weight | Component Scores | market × mode × component | One market, mode, component | Robotaxi has no C5 |
| **Feature Contribution** | Points an input adds to the baseline score | feature score × feature weight × component weight | Feature Contribution | market × input | One market, one mode; additive | Percentile scores lose magnitude (A-049) |
| **Scenario Score / Rank** | Position under an approved named business-priority scenario | Phase 8 precomputed (priority component 40%) | Business Scenario | market × scenario | One market, one scenario | A scenario assumption, not a preference estimate |
| **Scenario Rank Movement vs Neutral** | How the named scenario moves the market | Scenario rank − NEUTRAL (baseline) rank | Business Scenario | market × scenario | Same | |
| **Dynamic Scenario Score / Rank** | **USER-DEFINED SCENARIO — NOT BASELINE**: position under the user's weights | Σ component score × user weight / Σ active user weights; competition rank | Component Scores + What-If parameters | market × mode | One market, one mode, any weights | Unranked markets stay unranked; equal weights = baseline |
| **Deployment Present** | Whether a current commercial or limited-commercial autonomous service is recorded in the market | Open-ended COMMERCIAL / LIMITED_COMMERCIAL record resolved to the market (broad cohort) | Deployment Validation | market × mode | One market, one mode | **External validation only.** Not ground truth or accuracy. Presence = some service, not full coverage. No record ≠ unsuitable. Evidence as of 2026-10-05 |
| **Deployment Status** | Deployment cohort of the market | Current commercial / pilot-testing-announced / ended-paused only / other / none | Deployment Validation | market × mode | Same | Same |
