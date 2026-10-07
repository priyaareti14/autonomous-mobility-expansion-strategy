-- PBI_DIM_MARKET: the 35 frozen markets for Power BI. Grain: one row per market (market_id).
-- Location = the population-weighted centre of the market's tracts (better than the CBSA internal point for
-- a metro map). Reporting dimension only: no scores.
select
    d.market_id,
    d.cbsa_name                                                         as market_name,
    trim(split_part(split_part(d.cbsa_name, ',', 1), '-', 1))           as market_short_name,
    d.principal_state_usps,
    d.states_by_county_membership                                       as states,
    d.state_count,
    d.is_multi_state,
    u.market_rank                                                       as population_rank_2025,
    u.population_2025,
    pc.pw_center_latitude                                               as latitude,
    pc.pw_center_longitude                                              as longitude
from {{ ref('dim_market') }} d
join {{ ref('frozen_market_universe') }} u on u.market_id = d.market_id
join {{ ref('int_market__population_center') }} pc on pc.market_id = d.market_id
