-- Bridge: the observed state composition of each market (PEP 2025 county populations).
-- Grain: one row per market x state. Shares sum to 1 within each market.
-- OBSERVED data only: the regulatory state -> market rule stays open (A-012).
select
    market_id,
    state_fips,
    state_usps,
    state_population_2025,
    population_share_2025,
    county_count
from {{ ref('int_market__state_population') }}
