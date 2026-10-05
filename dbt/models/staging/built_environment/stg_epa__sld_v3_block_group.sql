-- S-21 EPA Smart Location Database v3.0 (includes S-22 NatWalkInd).
-- Grain: one row per 2010-based census block group (2019 TIGER).
-- Exposes identifiers and the catalogued variables (F22, F41-F43) plus their components.
-- D4A = -99999 is EPA's code for "no transit service data" (125,941 block groups). It becomes null
-- and is flagged, so it is never read as a distance.
-- The source's own CBSA field follows a pre-2023 delineation and is kept only as
-- cbsa_code_sld_pre2023. Mapping uses the 2023 county crosswalk downstream (A-006).
select
    {{ clean_text('"GEOID10"') }}                         as block_group_geoid10,
    {{ clean_text('"GEOID20"') }}                         as block_group_geoid20_published,
    {{ clean_text('"STATEFP"') }}                         as state_fips,
    {{ clean_text('"STATEFP"') }} || {{ clean_text('"COUNTYFP"') }} as county_fips,
    {{ clean_text('"TRACTCE"') }}                         as tract_code,
    {{ clean_text('"BLKGRPCE"') }}                        as block_group_code,
    {{ clean_text('"CBSA"') }}                            as cbsa_code_sld_pre2023,
    {{ to_number('"TOTPOP"') }}                           as total_population_sld,
    {{ to_number('"COUNTHU"') }}                          as housing_units_sld,
    {{ to_number('"HH"') }}                               as households_sld,
    {{ to_number('"TOTEMP"') }}                           as total_employment_sld,
    {{ to_number('"AC_TOTAL"') }}                         as total_acres,
    {{ to_number('"AC_LAND"') }}                          as land_acres,
    {{ to_number('"AC_UNPR"') }}                          as unprotected_land_acres,
    {{ to_number('"D1B"') }}                              as d1b_gross_population_density,
    {{ to_number('"D1C"') }}                              as d1c_gross_employment_density,
    {{ to_number('"D2A_EPHHM"') }}                        as d2a_employment_household_entropy,
    {{ to_number('"D2B_E8MIXA"') }}                       as d2b_employment_entropy_8_tier,
    {{ to_number('"D3B"') }}                              as d3b_street_intersection_density,
    iff({{ to_number('"D4A"') }} = -99999, null, {{ to_number('"D4A"') }}) as d4a_distance_to_transit_m,
    coalesce({{ to_number('"D4A"') }} = -99999, false)    as d4a_no_transit_data,
    {{ to_number('"D2A_RANKED"') }}                       as d2a_ranked,
    {{ to_number('"D2B_RANKED"') }}                       as d2b_ranked,
    {{ to_number('"D3B_RANKED"') }}                       as d3b_ranked,
    {{ to_number('"D4A_RANKED"') }}                       as d4a_ranked,
    {{ to_number('"NATWALKIND"') }}                       as national_walkability_index,
    {{ to_number('"PCT_AO0"') }}                          as pct_zero_car_households_sld,
    'SLD-v3.0'                                            as sld_version,
    {{ lineage_columns() }}
from {{ source('raw', 'EPA_SLD_V3_BLOCK_GROUP') }}
