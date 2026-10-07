-- PBI_FCT_REGULATORY_UNCERTAINTY: Phase 8 regulatory bounds in long form.
-- Grain: market_id x mode x regulatory_scenario (315 = 105 x 3). The three bounds are never averaged.
-- Score and rank are the committed Phase 8 values (equal weights; all 35 markets ranked).
-- regulatory_score (C4 under the bound) is backed out algebraically from the published score, without
-- re-modelling:  C4 = (score - sum of non-C4 component contributions) / C4 weight,  using the Phase 7
-- component scores and baseline weights. For complete markets it equals the Phase 7 C4 (tested).
-- Robotaxi rows also carry the nested 10,000-draw weight sensitivity under each bound.
with long as (
    select market_id, mode, c4_complete_flag, baseline_score, baseline_rank, regulatory_score_range,
           regulatory_rank_range, 'REG_PESSIMISTIC' as regulatory_scenario, pessimistic_score as scenario_score,
           pessimistic_rank as scenario_rank
    from {{ ref('p8_regulatory_uncertainty') }}
    union all
    select market_id, mode, c4_complete_flag, baseline_score, baseline_rank, regulatory_score_range,
           regulatory_rank_range, 'REG_NEUTRAL', neutral_score, neutral_rank
    from {{ ref('p8_regulatory_uncertainty') }}
    union all
    select market_id, mode, c4_complete_flag, baseline_score, baseline_rank, regulatory_score_range,
           regulatory_rank_range, 'REG_OPTIMISTIC', optimistic_score, optimistic_rank
    from {{ ref('p8_regulatory_uncertainty') }}
),

parts as (
    select
        market_id,
        mode,
        sum(iff(component <> 'C4_REGULATORY_AND_AUTONOMY_READINESS', component_score * component_weight, 0)) as non_regulatory_contribution,
        max(iff(component = 'C4_REGULATORY_AND_AUTONOMY_READINESS', component_weight, null))                as c4_weight
    from {{ ref('fct_component_scores') }}
    group by 1, 2
)

select
    l.market_id,
    l.mode,
    l.regulatory_scenario,
    d.assumed_favorable_fraction,
    l.c4_complete_flag                                                  as regulatory_complete_flag,
    l.scenario_score,
    l.scenario_rank,
    (l.scenario_score - p.non_regulatory_contribution) / p.c4_weight   as regulatory_score,
    b.c4_evidence_coverage_pct                                          as regulatory_evidence_coverage_pct,
    b.c4_max_unknown_share                                              as regulatory_max_unknown_share,
    l.baseline_score,
    l.baseline_rank,
    l.regulatory_score_range,
    l.regulatory_rank_range,
    w.top_5_frequency                                                   as nested_top_5_frequency,
    w.top_10_frequency                                                  as nested_top_10_frequency,
    w.mean_rank                                                         as nested_mean_rank,
    w.median_rank                                                       as nested_median_rank,
    w.best_rank                                                         as nested_best_rank,
    w.worst_rank                                                        as nested_worst_rank
from long l
join {{ ref('pbi_dim_regulatory_scenario') }} d on d.regulatory_scenario = l.regulatory_scenario
join parts p on p.market_id = l.market_id and p.mode = l.mode
join {{ ref('fct_readiness_baseline') }} b on b.market_id = l.market_id and b.mode = l.mode
left join {{ ref('p8_weight_sensitivity') }} w
  on w.market_id = l.market_id and w.mode = l.mode and w.regulatory_scenario = l.regulatory_scenario
