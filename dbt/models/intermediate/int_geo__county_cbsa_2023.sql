-- Official county -> CBSA crosswalk (OMB July 2023 delineation).
-- Grain: one row per county (county-equivalent) that belongs to a CBSA.
-- Counties outside every CBSA do not appear in the delineation file and so are absent here.
select
    county_fips,
    state_fips,
    county_code,
    county_name,
    state_name,
    cbsa_code,
    cbsa_title,
    cbsa_type,
    cbsa_type = 'Metropolitan Statistical Area'      as is_metropolitan,
    metro_division_code,
    metro_division_title,
    csa_code,
    csa_title,
    central_outlying,
    source_vintage                                   as delineation_vintage
from {{ ref('stg_census__cbsa_delineation_2023') }}
