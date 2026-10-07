-- BASELINE WEIGHTS: equal feature weights sum to 1 within every scored component; equal component
-- weights sum to 1 within every market x mode (robotaxi 4 components, sidewalk and drone 5); the
-- diagnostic non-regulatory weights sum to 1 over the non-C4 components.
with comp as (
    select * from {{ ref('fct_component_scores') }}
),

expected_components as (
    select 'ROBOTAXI' as mode, 4 as n union all
    select 'SIDEWALK_DELIVERY', 5 union all
    select 'DRONE_DELIVERY', 5
)

select 'feature weights do not sum to 1' as issue, market_id, mode, component, feature_weight_sum as value
from comp
where component_score is not null
  and abs(feature_weight_sum - 1) > {{ var('score_tolerance') }}

union all
select 'scored component without features', market_id, mode, component, feature_count
from comp
where component_score is not null and feature_count = 0

union all
select 'component weights do not sum to 1', market_id, mode, null, sum(component_weight)
from comp
group by market_id, mode
having abs(sum(component_weight) - 1) > {{ var('score_tolerance') }}

union all
select 'non-regulatory weights do not sum to 1', market_id, mode, null, sum(non_regulatory_component_weight)
from comp
group by market_id, mode
having abs(sum(non_regulatory_component_weight) - 1) > {{ var('score_tolerance') }}

union all
select 'unexpected number of active components', c.market_id, c.mode, null, count(*)
from comp c
join expected_components e on e.mode = c.mode
group by c.market_id, c.mode, e.n
having count(*) <> e.n
