-- FCT_COMPONENT_SCORES: component scores per market and mode.
-- Grain: one row per market x mode x ACTIVE component (robotaxi C1-C4: C5 has no active feature and is
-- structurally absent, never zero; sidewalk and drone C1-C5).
--   component_score        = sum of weighted feature contributions (equal weights: arithmetic mean), 0-100
--   component_weight       = 1 / number of active components of the mode (baseline_v1, equal)
--   component_contribution = component_score * component_weight
-- C4 has a score only when every regulatory dimension of the market is complete; otherwise it is
-- NULL / INCOMPLETE (no imputation, no neutral 50, no zero).
-- non_regulatory_component_weight re-weights C1-C3/C5 equally for the diagnostic non-regulatory score.
with f as (
    select * from {{ ref('fct_feature_scores') }}
),

c4_coverage as (
    select market_id, mode, avg(evidence_coverage_pct) as evidence_coverage_pct
    from {{ ref('fct_regulatory_dimension_scores') }}
    group by 1, 2
),

agg as (
    select
        market_id,
        mode,
        component,
        count(*)                                                        as input_count,
        count_if(in_base_flag)                                          as feature_count,
        sum(feature_weight)                                             as feature_weight_sum,
        sum(weighted_feature_contribution)                              as weighted_contribution_sum,
        max(active_component_count)                                     as active_component_count,
        max(component_weight)                                           as component_weight,
        booland_agg(input_complete_flag)                                as all_inputs_complete_flag
    from f
    group by 1, 2, 3
)

select
    a.market_id,
    a.mode,
    a.component,
    a.input_count,
    a.feature_count,
    a.feature_weight_sum,
    a.all_inputs_complete_flag                                          as component_complete_flag,
    iff(a.all_inputs_complete_flag, a.weighted_contribution_sum, null)  as component_score,
    a.component_weight,
    component_score * a.component_weight                                as component_contribution,
    iff(a.component = '{{ phase7_c4() }}', null, 1::float / (a.active_component_count - 1)) as non_regulatory_component_weight,
    a.active_component_count,
    iff(a.component = '{{ phase7_c4() }}', c.evidence_coverage_pct, null) as evidence_coverage_pct,
    '{{ var("model_version") }}'                                        as model_version,
    '{{ var("model_input_commit") }}'                                   as model_input_commit
from agg a
left join c4_coverage c on c.market_id = a.market_id and c.mode = a.mode
