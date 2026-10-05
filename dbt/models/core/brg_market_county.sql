-- Bridge: which counties make up each market (official July 2023 delineation, PEP county rows).
-- Grain: one row per market x county. Expected 319 rows for the 35 markets.
select
    market_id,
    county_fips,
    state_fips,
    state_usps,
    county_name_pep                 as county_name,
    central_outlying,
    metro_division_code,
    county_population_2025,
    county_land_area_sq_mi,
    county_water_area_sq_mi
from {{ ref('int_market__counties') }}
