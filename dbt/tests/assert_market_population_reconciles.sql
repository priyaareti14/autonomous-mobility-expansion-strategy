-- RECONCILIATION: each market's 2025 population equals (a) the sum of its county populations and
-- (b) the sum of its state shares, and state shares sum to 1. This is the Phase 1 check
-- ("county sums match every MSA total"), now enforced in the warehouse.
with county_sum as (
    select market_id, sum(county_population_2025) as county_total
    from {{ ref('brg_market_county') }} group by market_id
),
state_sum as (
    select market_id, sum(state_population_2025) as state_total, sum(population_share_2025) as share_total
    from {{ ref('brg_market_state') }} group by market_id
)
select d.market_id, d.population_2025, c.county_total, s.state_total, s.share_total
from {{ ref('dim_market') }} d
left join county_sum c on c.market_id = d.market_id
left join state_sum s on s.market_id = d.market_id
where c.county_total is null
   or c.county_total <> d.population_2025
   or s.state_total <> d.population_2025
   or abs(s.share_total - 1) > 1e-9
