-- A1 AIRPORT -> MARKET ASSIGNMENT (approved Phase 5 construct, A-009; geography key hardened, A-032).
-- Grain: one row per FAA CY2025 commercial-service airport (516).
--
-- Geography key: the official county FIPS code containing the airport's NASR reference point,
-- returned by the Census Geocoder (S-40, ACS 2024 boundaries). County FIPS -> CBSA uses the July 2023
-- delineation (int_geo__county_cbsa_2023). No county NAME is matched: NASR publishes names only, and
-- the Phase 5 name match (A-032) is retired. NASR's own county name is carried for comparison only.
--
-- a1_market_id: the frozen market whose official counties contain the airport, else null. Each
-- airport sits in exactly one county, so it can be counted for at most one market (tested).
-- It measures MARKET-EMBEDDED airport activity, not the full aviation catchment of a metro.
--
-- a4_market_id_diagnostic (A4, sensitivity only, never a production feature): a1_market_id if set;
-- otherwise the frozen market with the nearest population-weighted centre within a4_radius_km (80 km).
with airports as (
    select * from {{ ref('int_airports__commercial_service') }}
),

geo as (
    select * from {{ ref('stg_census__geocoder_airport_county_acs2024') }}
),

counties as (
    select county_fips, cbsa_code from {{ ref('int_geo__county_cbsa_2023') }}
),

markets as (
    select market_id from {{ ref('dim_market') }}
),

nearest_market as (
    select
        a.airport_code,
        c.market_id,
        haversine(c.pw_center_latitude, c.pw_center_longitude, a.latitude, a.longitude) as distance_km
    from airports a
    cross join {{ ref('int_market__population_center') }} c
    qualify row_number() over (partition by a.airport_code
                               order by haversine(c.pw_center_latitude, c.pw_center_longitude,
                                                  a.latitude, a.longitude), c.market_id) = 1
)

select
    a.airport_code,
    a.airport_name,
    a.state_usps,
    a.service_level_code,
    a.hub_type_code,
    a.enplanements_cy2025,
    a.latitude,
    a.longitude,
    g.county_fips,
    g.county_name                                         as county_name_official,
    a.county_name_published                               as county_name_nasr,
    x.cbsa_code,
    m.market_id                                           as a1_market_id,
    m.market_id is not null                               as is_inside_project_market,
    n.market_id                                           as nearest_market_id,
    round(n.distance_km, 2)                               as nearest_market_distance_km,
    coalesce(m.market_id,
             iff(n.distance_km <= {{ var('a4_radius_km') }}, n.market_id, null)) as a4_market_id_diagnostic,
    'COUNTY_FIPS_FROM_CENSUS_GEOCODER'                    as geography_key_method,
    g.geocoder_vintage
from airports a
inner join geo g on g.airport_code = a.airport_code
left join counties x on x.county_fips = g.county_fips
left join markets m on m.market_id = x.cbsa_code
left join nearest_market n on n.airport_code = a.airport_code
