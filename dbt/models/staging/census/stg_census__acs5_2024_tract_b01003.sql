-- S-04 ACS 5-year 2020-2024 B01003 total population, every census tract.
-- Grain: one row per 2020 census tract (50 states + DC + Puerto Rico).
-- 110 tracts publish MOE = -555555555 (Census code: estimate controlled to
-- official totals, no sampling MOE). The MOE becomes null and is flagged.
select
    {{ clean_text('"STATE"') }} || {{ clean_text('"COUNTY"') }} || {{ clean_text('"TRACT"') }} as tract_geoid,
    {{ clean_text('"STATE"') }}                                      as state_fips,
    {{ clean_text('"STATE"') }} || {{ clean_text('"COUNTY"') }}      as county_fips,
    {{ clean_text('"GEO_ID"') }}                                     as acs_geo_id,
    {{ clean_text('"NAME"') }}                                       as acs_geography_name,
    {{ acs_value('"B01003_001E"') }}                                 as total_population,
    {{ acs_value('"B01003_001M"') }}                                 as total_population_moe,
    {{ acs_is_special_code('"B01003_001E"') }}                       as total_population_is_special_code,
    {{ acs_is_special_code('"B01003_001M"') }}                       as total_population_moe_is_special_code,
    'ACS5-2024'                                                      as acs_period,
    {{ lineage_columns() }}
from {{ source('raw', 'CENSUS_ACS5_2024_TRACT_B01003') }}
