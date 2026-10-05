-- CANDIDATE relationships between every weather station and every frozen market. NO SELECTION.
-- Grain: one row per market x station (35 x all stations).
-- distance_km is the great-circle distance from the station to the CBSA's Gazetteer internal
-- point. The internal point is a geographic reference point, not a population centroid; it
-- is not the station-selection rule.
-- The station-to-market rule is OPEN (A-007, data_sources.md section 5): primary first-order airport
-- station, mean of in-CBSA stations, or population-weighted nearest station. In-polygon tests
-- need TIGER CBSA boundaries (S-07, deferred). This table only makes candidates comparable in Phase 5.
select
    m.market_id,
    s.station_id,
    s.station_name,
    s.has_annual_normals,
    s.has_hourly_wind_normals,
    haversine(g.internal_point_latitude, g.internal_point_longitude, s.latitude, s.longitude) as distance_km,
    row_number() over (partition by m.market_id
                       order by haversine(g.internal_point_latitude, g.internal_point_longitude,
                                          s.latitude, s.longitude), s.station_id) as distance_rank
from {{ ref('int_market__universe_ranked') }} m
inner join {{ ref('stg_census__gazetteer_2024_cbsa') }} g
    on g.cbsa_code = m.market_id
cross join {{ ref('int_weather__stations') }} s
where s.latitude is not null and s.longitude is not null
