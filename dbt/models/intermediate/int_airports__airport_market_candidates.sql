-- CANDIDATE relationships between every commercial-service airport and every frozen market.
-- NO ASSIGNMENT.
-- Grain: one row per market x commercial-service airport (35 x 516).
-- distance_km is measured from the CBSA's Gazetteer internal point to the airport's NASR coordinates.
-- airport_state_in_market flags airports in a state that contains some of the market's
-- counties. That is a weak hint, not a mapping.
-- The airport-to-market rule is OPEN (A-009): point-in-polygon needs TIGER boundaries (S-07,
-- deferred), and boundary airports (e.g. BWI, ONT, MHT/PVD) need a documented decision.
-- Nothing here is aggregated to a market.
with market_states as (
    select distinct market_id, state_usps from {{ ref('int_market__counties') }}
)

select
    m.market_id,
    a.airport_code,
    a.airport_name,
    a.state_usps                       as airport_state_usps,
    a.hub_type_code,
    a.service_level_code,
    a.enplanements_cy2025,
    haversine(g.internal_point_latitude, g.internal_point_longitude, a.latitude, a.longitude) as distance_km,
    row_number() over (partition by m.market_id
                       order by haversine(g.internal_point_latitude, g.internal_point_longitude,
                                          a.latitude, a.longitude), a.airport_code) as distance_rank,
    ms.state_usps is not null          as airport_state_in_market
from {{ ref('int_market__universe_ranked') }} m
inner join {{ ref('stg_census__gazetteer_2024_cbsa') }} g
    on g.cbsa_code = m.market_id
cross join {{ ref('int_airports__commercial_service') }} a
left join market_states ms
    on ms.market_id = m.market_id and ms.state_usps = a.state_usps
where a.latitude is not null and a.longitude is not null
