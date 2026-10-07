# DAX Measures (Phase 9)

Create these in a dedicated **Measures** table (Enter data → one dummy column → hide it), in Power BI Desktop. Table names are the renamed Power BI names in [docs/powerbi_semantic_model.md](../docs/powerbi_semantic_model.md) §2.

**Conventions:**
- **Market-level measures** return a value only when exactly one market and one mode are in context, and blank otherwise. Summing or averaging scores across markets or modes would be meaningless, and combining modes is forbidden.
- **Ranks** are the published Phase 7/8 ranks; only the user-defined What-If rank (§5) is computed in DAX.
- **Labels.** Every visual that uses §5 must carry the label **"USER-DEFINED SCENARIO — NOT BASELINE"**.

DAX syntax follows current Power BI Desktop semantics. Validate each measure with the QA in §7 after creating it.

## 1. Context guards

```dax
One Market One Mode =
HASONEVALUE ( Market[market_id] ) && HASONEVALUE ( Mode[mode] )
```

```dax
Selected Mode =
SELECTEDVALUE ( Mode[mode] )
```

## 2. Baseline (Phase 7)

```dax
Selected Baseline Score =
IF ( [One Market One Mode], SELECTEDVALUE ( Baseline[baseline_readiness_score] ) )
-- blank = not determinable from verified evidence (incomplete regulatory evidence); never show as 0

Selected Baseline Rank =
IF ( [One Market One Mode], SELECTEDVALUE ( Baseline[baseline_rank] ) )

Baseline Rank Label =
VAR r = [Selected Baseline Rank]
RETURN
    IF (
        [One Market One Mode],
        IF ( ISBLANK ( r ), "Not ranked (regulatory evidence incomplete)", "#" & FORMAT ( r, "0" ) )
    )

Non-Regulatory Score =
IF ( [One Market One Mode], SELECTEDVALUE ( Baseline[non_regulatory_score] ) )
-- diagnostic only: not a readiness score, never ranked

Regulatory Coverage % =
IF ( [One Market One Mode], DIVIDE ( SELECTEDVALUE ( Baseline[regulatory_evidence_coverage_pct] ), 100 ) )

Markets Evaluated =
DISTINCTCOUNT ( Baseline[market_id] )

Markets With Complete Score =
CALCULATE ( DISTINCTCOUNT ( Baseline[market_id] ), Baseline[score_complete_flag] = TRUE () )

Share Of Markets Scored =
DIVIDE ( [Markets With Complete Score], [Markets Evaluated] )
```

## 3. Components and features

```dax
Component Score =
IF (
    [One Market One Mode] && HASONEVALUE ( Component[component] ),
    SELECTEDVALUE ( 'Component Scores'[component_score] )
)

Component Contribution =
IF (
    [One Market One Mode] && HASONEVALUE ( Component[component] ),
    SELECTEDVALUE ( 'Component Scores'[component_contribution] )
)
-- In a stacked bar (axis = market, legend = component) the segments add up to the baseline score.

Feature Score =
IF (
    HASONEVALUE ( Market[market_id] ) && HASONEVALUE ( Feature[feature_key] ),
    SELECTEDVALUE ( 'Feature Contribution'[feature_score] )
)

Feature Contribution =
IF (
    [One Market One Mode],
    SUM ( 'Feature Contribution'[contribution_to_overall] )
)
-- Additive: over all features of one market and mode it equals the baseline score (complete markets).

Feature Points Below Maximum =
IF ( [One Market One Mode], SUM ( 'Feature Contribution'[points_below_maximum] ) )
```

## 4. Robustness (Phase 8)

```dax
Mean Sensitivity Rank =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[mean_rank] ) )

Median Sensitivity Rank =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[median_rank] ) )

Best Rank =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[best_rank] ) )

Worst Rank =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[worst_rank] ) )

Rank Range =
[Worst Rank] - [Best Rank]
-- spread across the 10,000 weight draws; blank for markets without a complete score

Rank 90% Low =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[rank_90pct_low] ) )

Rank 90% High =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[rank_90pct_high] ) )

Rank Standard Deviation =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[rank_std] ) )

Top 5 Frequency =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[top_5_frequency] ) )
-- "share of tested weight configurations", never "probability of being best"

Top 10 Frequency =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[top_10_frequency] ) )

Robustness Flags =
IF ( [One Market One Mode], SELECTEDVALUE ( Robustness[pattern_flags] ) )

Regulatory Rank Low =
IF (
    [One Market One Mode],
    CALCULATE ( MIN ( 'Regulatory Uncertainty'[scenario_rank] ), REMOVEFILTERS ( 'Regulatory Scenario' ) )
)

Regulatory Rank High =
IF (
    [One Market One Mode],
    CALCULATE ( MAX ( 'Regulatory Uncertainty'[scenario_rank] ), REMOVEFILTERS ( 'Regulatory Scenario' ) )
)

Regulatory Rank Range =
[Regulatory Rank High] - [Regulatory Rank Low]
-- ranks among all 35 markets under the three bounds; never averaged into one rank

Regulatory Bound Score =
IF (
    [One Market One Mode] && HASONEVALUE ( 'Regulatory Scenario'[regulatory_scenario] ),
    SELECTEDVALUE ( 'Regulatory Uncertainty'[scenario_score] )
)

Regulatory Bound Rank =
IF (
    [One Market One Mode] && HASONEVALUE ( 'Regulatory Scenario'[regulatory_scenario] ),
    SELECTEDVALUE ( 'Regulatory Uncertainty'[scenario_rank] )
)

Most Robust Leader =
-- market(s) with the highest top-5 frequency in the selected mode (ties listed); label it exactly so
VAR _m = [Selected Mode]
VAR _best =
    CALCULATE ( MAX ( Robustness[top_5_frequency] ), REMOVEFILTERS ( Market ) )
VAR _leaders =
    -- iterate the markets: a filter on Robustness would not flow back to Market (single-direction relationship)
    FILTER (
        ALL ( Market[market_id], Market[market_short_name] ),
        CALCULATE ( MAX ( Robustness[top_5_frequency] ) ) = _best
    )
RETURN
    IF (
        NOT ISBLANK ( _m ) && NOT ISBLANK ( _best ),
        CONCATENATEX ( _leaders, Market[market_short_name], ", ", Market[market_short_name], ASC )
    )
```

## 5. Scenarios

### 5.1 Named business scenarios (precomputed, validated in Phase 8)

```dax
Scenario Score =
IF (
    HASONEVALUE ( Market[market_id] ) && HASONEVALUE ( Scenario[scenario_id] ),
    SELECTEDVALUE ( 'Business Scenario'[scenario_score] )
)

Scenario Rank =
IF (
    HASONEVALUE ( Market[market_id] ) && HASONEVALUE ( Scenario[scenario_id] ),
    SELECTEDVALUE ( 'Business Scenario'[scenario_rank] )
)

Scenario Rank Movement vs Neutral =
-- NEUTRAL = the Phase 7 baseline; negative = the market moves up
IF (
    NOT ISBLANK ( [Scenario Rank] ),
    [Scenario Rank]
        - CALCULATE (
            SELECTEDVALUE ( 'Business Scenario'[scenario_rank] ),
            REMOVEFILTERS ( Scenario ),
            Scenario[is_baseline_scenario] = TRUE ()
        )
)

Scenario Score Movement vs Neutral =
IF (
    NOT ISBLANK ( [Scenario Score] ),
    [Scenario Score]
        - CALCULATE (
            SELECTEDVALUE ( 'Business Scenario'[scenario_score] ),
            REMOVEFILTERS ( Scenario ),
            Scenario[is_baseline_scenario] = TRUE ()
        )
)
```

### 5.2 User-defined What-If weights (USER-DEFINED SCENARIO — NOT BASELINE)

**Parameters.** Create five numeric What-If parameters (*Modeling → New parameter → Numeric range*): **W C1, W C2, W C3, W C4, W C5**.
- Minimum 0, maximum 100, increment 5, default 20.
- Each creates a disconnected table with a `… Value` measure.

**Normalization.** Weights are normalized over the **active** components of the selected mode:

```
normalized_weight_i = user_weight_i / SUM(active user weights)
```

Robotaxi uses C1–C4 only, so W C5 is ignored. With all sliders equal, the result is the baseline.

```dax
W Active Total =
VAR _m = [Selected Mode]
RETURN
    'W C1'[W C1 Value] + 'W C2'[W C2 Value] + 'W C3'[W C3 Value] + 'W C4'[W C4 Value]
        + IF ( _m = "ROBOTAXI", 0, 'W C5'[W C5 Value] )

Normalized Weight C1 = DIVIDE ( 'W C1'[W C1 Value], [W Active Total] )
Normalized Weight C2 = DIVIDE ( 'W C2'[W C2 Value], [W Active Total] )
Normalized Weight C3 = DIVIDE ( 'W C3'[W C3 Value], [W Active Total] )
Normalized Weight C4 = DIVIDE ( 'W C4'[W C4 Value], [W Active Total] )
Normalized Weight C5 =
IF ( [Selected Mode] = "ROBOTAXI", BLANK (), DIVIDE ( 'W C5'[W C5 Value], [W Active Total] ) )

Dynamic Scenario Score =
-- USER-DEFINED SCENARIO — NOT BASELINE.
-- Weighted mean of the published Phase 7 component scores with the user's normalized weights.
-- Blank when the market has no complete score (incomplete C4 is never filled in) or all weights are 0.
VAR _m = [Selected Mode]
VAR w1 = 'W C1'[W C1 Value]
VAR w2 = 'W C2'[W C2 Value]
VAR w3 = 'W C3'[W C3 Value]
VAR w4 = 'W C4'[W C4 Value]
VAR w5 = IF ( _m = "ROBOTAXI", 0, 'W C5'[W C5 Value] )
VAR _total = w1 + w2 + w3 + w4 + w5
VAR _missing =
    -- ISBLANK row by row: a filter such as [component_score] = BLANK() would also match genuine 0 scores
    COUNTROWS (
        FILTER (
            CALCULATETABLE ( 'Component Scores', REMOVEFILTERS ( Component ) ),
            ISBLANK ( 'Component Scores'[component_score] )
        )
    )
VAR _weighted =
    CALCULATE (
        SUMX (
            'Component Scores',
            'Component Scores'[component_score]
                * SWITCH (
                    'Component Scores'[component_code],
                    "C1", w1, "C2", w2, "C3", w3, "C4", w4, "C5", w5,
                    0
                )
        ),
        REMOVEFILTERS ( Component )
    )
RETURN
    IF (
        [One Market One Mode] && _total > 0 && _missing = 0,
        DIVIDE ( _weighted, _total )
    )

Dynamic Rank =
-- USER-DEFINED SCENARIO — NOT BASELINE. Competition rank among markets with a dynamic score.
VAR _s = [Dynamic Scenario Score]
RETURN
    IF (
        NOT ISBLANK ( _s ),
        RANKX (
            FILTER ( ALLSELECTED ( Market ), NOT ISBLANK ( [Dynamic Scenario Score] ) ),
            ROUND ( [Dynamic Scenario Score], 6 ),
            ROUND ( _s, 6 ),
            DESC,
            SKIP
        )
    )

Dynamic Rank Movement vs Baseline =
IF ( NOT ISBLANK ( [Dynamic Rank] ), [Dynamic Rank] - [Selected Baseline Rank] )

Dynamic Score Movement vs Baseline =
IF ( NOT ISBLANK ( [Dynamic Scenario Score] ), [Dynamic Scenario Score] - [Selected Baseline Score] )

Scenario Label =
"USER-DEFINED SCENARIO — NOT BASELINE"
```

## 6. Deployment validation (external validation only)

```dax
Deployment Present =
IF (
    [One Market One Mode],
    IF ( SELECTEDVALUE ( 'Deployment Validation'[deployment_present] ), "Yes", "No recorded deployment" )
)
-- "No recorded deployment" is NOT evidence that a market is unsuitable

Deployment Status =
IF ( [One Market One Mode], SELECTEDVALUE ( 'Deployment Validation'[deployment_status] ) )

Markets With Deployment =
CALCULATE (
    DISTINCTCOUNT ( 'Deployment Validation'[market_id] ),
    'Deployment Validation'[deployment_present] = TRUE ()
)
```

## 7. Measure QA (run in Power BI Desktop after building)

Run these in a table visual, with Mode set to each mode in turn:

1. **Baseline score and rank.** `Selected Baseline Score` and `Selected Baseline Rank` equal `outputs/phase7/{mode}_baseline.csv` for every market. Unranked markets are blank, never 0:

| Mode | Unranked markets |
|---|---|
| Robotaxi | 6 |
| Sidewalk | 4 |
| Drone | 10 |

2. **What-If baseline match.** With W C1–W C5 all at 20, `Dynamic Scenario Score` equals `Selected Baseline Score` to 6 decimals, and `Dynamic Rank` equals `Selected Baseline Rank`. Robotaxi ignores W C5, so changing W C5 must not change any robotaxi value.
3. **What-If named-scenario match.** Set W C1 = 40 and W C2 = W C3 = W C4 = W C5 = 15. This reproduces the named DEMAND_PRIORITY scenario for sidewalk and drone, so `Dynamic Rank` = `Scenario Rank` with Scenario = *_DEMAND_PRIORITY.
4. **Feature contributions.** Over a market's features, `Feature Contribution` adds up to its baseline score.
5. **Regulatory ranks.** `Regulatory Rank Low` and `Regulatory Rank High` for robotaxi Boston are 4 and 20.
6. **Robust leader.** `Most Robust Leader` for robotaxi lists Los Angeles and San Francisco (both 100% top-5).
