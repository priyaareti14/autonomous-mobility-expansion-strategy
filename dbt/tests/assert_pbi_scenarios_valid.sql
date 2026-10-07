-- SCENARIO CONTRACT (Phase 9 / Phase 8 What-If): every named scenario's active component weights are
-- non-negative and sum to 1; robotaxi has no C5 weight and no infrastructure scenario; each mode has exactly one
-- NEUTRAL scenario, whose ranks equal the Phase 7 baseline ranks.
{% set tol = var('score_tolerance') %}
with s as (
    select * from {{ ref('pbi_dim_scenario') }}
)

select 'weights do not sum to 1' as issue, scenario_id as detail
from s
where abs(coalesce(c1_weight, 0) + coalesce(c2_weight, 0) + coalesce(c3_weight, 0) + coalesce(c4_weight, 0)
          + coalesce(c5_weight, 0) - 1) > {{ tol }}

union all
select 'negative weight', scenario_id
from s
where least(coalesce(c1_weight, 0), coalesce(c2_weight, 0), coalesce(c3_weight, 0), coalesce(c4_weight, 0),
            coalesce(c5_weight, 0)) < 0

union all
select 'robotaxi C5 weight or infrastructure scenario', scenario_id
from s
where mode = 'ROBOTAXI' and (c5_weight is not null or priority_component_code = 'C5')

union all
select 'missing C5 weight for a 5-component mode', scenario_id
from s
where mode <> 'ROBOTAXI' and c5_weight is null

union all
select 'not exactly one NEUTRAL scenario', mode
from s
group by mode
having count_if(is_baseline_scenario) <> 1

union all
select 'NEUTRAL scenario rank differs from the Phase 7 baseline rank', f.market_id || ' ' || f.mode
from {{ ref('pbi_fct_business_scenario') }} f
join s on s.scenario_id = f.scenario_id and s.is_baseline_scenario
join {{ ref('fct_readiness_baseline') }} b on b.market_id = f.market_id and b.mode = f.mode
where not equal_null(f.scenario_rank, b.baseline_rank)
   or (b.baseline_readiness_score is null) <> (f.scenario_score is null)
   -- the Phase 8 export keeps 6 decimals, so the copied score can differ from Phase 7 by at most 5e-7
   or abs(coalesce(f.scenario_score, 0) - coalesce(b.baseline_readiness_score, 0)) > 0.000001
