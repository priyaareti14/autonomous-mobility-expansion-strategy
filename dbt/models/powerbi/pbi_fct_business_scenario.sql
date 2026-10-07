-- PBI_FCT_BUSINESS_SCENARIO: Phase 8 named business-priority scenario results.
-- Grain: market_id x scenario_id (595; scenario_id identifies the mode). Score and rank are NULL for markets
-- without a complete baseline score. NEUTRAL = the Phase 7 baseline.
select
    s.market_id,
    s.mode,
    s.scenario_id,
    s.score                                 as scenario_score,
    s.rank                                  as scenario_rank,
    s.baseline_rank,
    s.rank_change_vs_baseline,
    c.c1_weight,
    c.c2_weight,
    c.c3_weight,
    c.c4_weight,
    c.c5_weight
from {{ ref('p8_business_scenarios') }} s
join {{ ref('p8_scenario_contract') }} c on c.scenario_id = s.scenario_id
