-- FCT_TRACT_POPULATION_LAND: tract-level population (ACS 2020-2024) and land area (Gazetteer 2024)
-- for tracts in the 35 markets. These are the INPUTS for the open density decision (A-008):
-- no density or population-weighted statistic is computed here.
-- Grain: one row per 2020 census tract within a frozen market (via the official
-- tract -> county -> CBSA crosswalk).
-- Units: persons, square miles.
-- has_acs_population = false for the 14 Suffolk County, NY (36103) tracts that are in Gazetteer
-- 2024 but have no ACS 2020-2024 record (A-029). They are kept, not dropped.
select
    x.tract_geoid,
    x.cbsa_code                          as market_id,
    x.county_fips,
    t.state_usps,
    a.total_population,
    a.total_population_moe,
    a.total_population_moe_is_special_code,
    a.tract_geoid is not null            as has_acs_population,
    t.land_area_sq_mi,
    t.water_area_sq_mi,
    t.land_area_sq_mi = 0                as is_zero_land_area,
    t.internal_point_latitude,
    t.internal_point_longitude,
    'ACS5-2024'                          as acs_period,
    '2024'                               as gazetteer_vintage
from {{ ref('int_geo__tract_cbsa_2023') }} x
inner join {{ ref('dim_market') }} d
    on d.market_id = x.cbsa_code
inner join {{ ref('stg_census__gazetteer_2024_tracts') }} t
    on t.tract_geoid = x.tract_geoid
left join {{ ref('stg_census__acs5_2024_tract_b01003') }} a
    on a.tract_geoid = x.tract_geoid
