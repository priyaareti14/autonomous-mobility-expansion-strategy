-- Observed state composition of each market: PEP 2025 county populations summed by state.
-- Grain: one row per market x state.
-- This is OBSERVED population data. It does NOT decide how state regulation maps to a
-- multi-state market (A-012 stays open for Phase 7).
with by_state as (
    select
        market_id,
        state_fips,
        state_usps,
        sum(county_population_2025) as state_population_2025,
        count(*)                    as county_count
    from {{ ref('int_market__counties') }}
    group by market_id, state_fips, state_usps
)

select
    market_id,
    state_fips,
    state_usps,
    state_population_2025,
    county_count,
    -- Floating-point division: NUMBER/NUMBER in Snowflake rounds to 6 decimal places, which made
    -- shares sum to 1.000001 (caught by assert_market_population_reconciles).
    state_population_2025::float
        / sum(state_population_2025::float) over (partition by market_id) as population_share_2025
from by_state
