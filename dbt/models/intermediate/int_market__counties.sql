-- County membership of the 35 frozen markets: PEP county rows joined to the official
-- delineation attributes and Gazetteer 2024 land area. All joins use county FIPS codes.
-- Grain: one row per market x county.
with market_counties as (
    select
        p.cbsa_code                  as market_id,
        p.county_fips,
        p.geography_name             as county_name_pep,
        p.population_estimate_2025   as county_population_2025
    from {{ ref('stg_census__pep_cbsa_est2025') }} p
    inner join {{ ref('int_market__universe_ranked') }} m
        on m.market_id = p.cbsa_code
    where p.geography_type = 'County or equivalent'
)

select
    mc.market_id,
    mc.county_fips,
    d.state_fips,
    g.state_usps,
    mc.county_name_pep,
    d.county_name                    as county_name_delineation,
    d.central_outlying,
    d.metro_division_code,
    mc.county_population_2025,
    g.land_area_sq_mi                as county_land_area_sq_mi,
    g.water_area_sq_mi               as county_water_area_sq_mi
from market_counties mc
left join {{ ref('int_geo__county_cbsa_2023') }} d
    on d.county_fips = mc.county_fips
left join {{ ref('stg_census__gazetteer_2024_counties') }} g
    on g.county_fips = mc.county_fips
