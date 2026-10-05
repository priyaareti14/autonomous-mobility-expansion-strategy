-- Official tract -> county -> CBSA crosswalk. Tracts nest exactly in counties, and the
-- county -> CBSA step uses the July 2023 delineation.
-- Grain: one row per 2020 census tract in the 2024 Gazetteer (85,396). Tracts outside any CBSA
-- keep cbsa_code null (is_in_cbsa = false): nothing is dropped.
select
    t.tract_geoid,
    t.county_fips,
    t.state_usps,
    x.cbsa_code,
    x.is_metropolitan,
    x.cbsa_code is not null as is_in_cbsa
from {{ ref('stg_census__gazetteer_2024_tracts') }} t
left join {{ ref('int_geo__county_cbsa_2023') }} x
    on x.county_fips = t.county_fips
