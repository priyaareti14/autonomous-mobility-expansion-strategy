-- CONTRACT: DIM_MARKET (derived from the pinned PEP ranking) is identical to the approved market
-- universe in docs/project_scope.md section 6 (seed frozen_market_universe): same code, name,
-- 2025 population and rank for all 35 markets.
-- Returns every row that is in one and not the other; the test passes only on zero rows.
with dim as (
    select market_id, cbsa_name, population_2025, market_rank_2025 as market_rank
    from {{ ref('dim_market') }}
),
seed as (
    select market_id, cbsa_name, population_2025, market_rank
    from {{ ref('frozen_market_universe') }}
)
(select 'in DIM_MARKET only' as side, * from dim minus select 'in DIM_MARKET only', * from seed)
union all
(select 'in approved seed only' as side, * from seed minus select 'in approved seed only', * from dim)
