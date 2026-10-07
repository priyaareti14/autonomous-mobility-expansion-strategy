-- PBI_FCT_MARKET_FEATURE_CONTRIBUTION: Phase 7 feature-level explainability.
-- Grain: market_id x mode x input (feature_key; 1,295 = 35 x 37). Values copied from FCT_FEATURE_SCORES.
select
    market_id,
    mode,
    mode || '|' || feature_id               as feature_key,
    feature_id,
    component,
    direction,
    raw_value,
    transformed_value,
    feature_score,
    feature_weight,
    weighted_feature_contribution,
    contribution_to_overall,
    points_below_maximum,
    in_base_flag
from {{ ref('fct_feature_scores') }}
