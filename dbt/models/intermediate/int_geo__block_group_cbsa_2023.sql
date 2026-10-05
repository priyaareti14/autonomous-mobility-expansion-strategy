-- EPA SLD block group -> county -> CBSA (July 2023 delineation), via county FIPS (A-006).
-- Grain: one row per SLD block group (2010-based, 220,134).
-- The SLD's own pre-2023 CBSA code is carried only for comparison: cbsa_code_differs_from_sld
-- shows where it disagrees with the 2023 delineation. It is never used for mapping.
-- Block groups whose county is outside every 2023 CBSA keep cbsa_code null.
select
    b.block_group_geoid10,
    b.county_fips,
    b.state_fips,
    x.cbsa_code,
    x.is_metropolitan,
    b.cbsa_code_sld_pre2023,
    coalesce(b.cbsa_code_sld_pre2023, '') <> coalesce(x.cbsa_code, '') as cbsa_code_differs_from_sld,
    x.cbsa_code is not null as is_in_cbsa
from {{ ref('stg_epa__sld_v3_block_group') }} b
left join {{ ref('int_geo__county_cbsa_2023') }} x
    on x.county_fips = b.county_fips
