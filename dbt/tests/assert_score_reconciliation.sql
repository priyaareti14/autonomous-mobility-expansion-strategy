-- SCORE RECONCILIATION (docs/score_reconciliation.md): every published number is the exact sum of its parts.
--   component_score          = sum(weighted_feature_contribution)            per market x mode x component
--   baseline_readiness_score = sum(component_contribution)                   per market x mode
--   baseline_readiness_score = sum(contribution_to_overall) over features    per market x mode
--   mode marts               = FCT_READINESS_BASELINE (score, rank, components)
{% set tol = var('score_tolerance') %}
with feat as (
    select market_id, mode, component,
           sum(weighted_feature_contribution) as weighted_sum,
           sum(contribution_to_overall)       as overall_part
    from {{ ref('fct_feature_scores') }}
    group by 1, 2, 3
),

comp as (
    select * from {{ ref('fct_component_scores') }}
),

base as (
    select * from {{ ref('fct_readiness_baseline') }}
),

marts as (
    select 'ROBOTAXI' as mode, market_id, baseline_readiness_score, baseline_rank,
           c1_demand_score, c4_regulatory_score
    from {{ ref('mart_robotaxi_readiness_baseline') }}
    union all
    select 'SIDEWALK_DELIVERY', market_id, baseline_readiness_score, baseline_rank, c1_demand_score, c4_regulatory_score
    from {{ ref('mart_sidewalk_delivery_readiness_baseline') }}
    union all
    select 'DRONE_DELIVERY', market_id, baseline_readiness_score, baseline_rank, c1_demand_score, c4_regulatory_score
    from {{ ref('mart_drone_delivery_readiness_baseline') }}
)

select 'component score != sum of weighted feature contributions' as issue, c.market_id, c.mode, c.component
from comp c
join feat f on f.market_id = c.market_id and f.mode = c.mode and f.component = c.component
where c.component_score is not null and abs(c.component_score - f.weighted_sum) > {{ tol }}

union all
select 'overall score != sum of component contributions', b.market_id, b.mode, null
from base b
join (select market_id, mode, sum(component_contribution) as s from comp group by 1, 2) c
  on c.market_id = b.market_id and c.mode = b.mode
where b.baseline_readiness_score is not null and abs(b.baseline_readiness_score - c.s) > {{ tol }}

union all
select 'overall score != sum of feature contributions to overall', b.market_id, b.mode, null
from base b
join (select market_id, mode, sum(overall_part) as s from feat group by 1, 2) f
  on f.market_id = b.market_id and f.mode = b.mode
where b.baseline_readiness_score is not null and abs(b.baseline_readiness_score - f.s) > {{ tol }}

union all
select 'mode mart differs from FCT_READINESS_BASELINE', m.market_id, m.mode, null
from marts m
join base b on b.market_id = m.market_id and b.mode = m.mode
where not equal_null(round(m.baseline_readiness_score, 9), round(b.baseline_readiness_score, 9))
   or not equal_null(m.baseline_rank, b.baseline_rank)

union all
select 'mode mart component differs from FCT_COMPONENT_SCORES', m.market_id, m.mode, c.component
from marts m
join comp c on c.market_id = m.market_id and c.mode = m.mode
where (c.component = 'C1_DEMAND_AND_MARKET_OPPORTUNITY' and not equal_null(round(m.c1_demand_score, 9), round(c.component_score, 9)))
   or (c.component = '{{ phase7_c4() }}' and not equal_null(round(m.c4_regulatory_score, 9), round(c.component_score, 9)))
