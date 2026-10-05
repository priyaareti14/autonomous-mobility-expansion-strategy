-- S-05 Census 2024 Gazetteer, counties. Grain: one row per county (county-equivalent).
select
    {{ clean_text('"GEOID"') }}               as county_fips,
    {{ clean_text('"USPS"') }}                as state_usps,
    {{ clean_text('"ANSICODE"') }}            as county_ansi_code,
    {{ clean_text('"NAME"') }}                as county_name,
    {{ to_number('"ALAND"') }}                as land_area_sq_m,
    {{ to_number('"AWATER"') }}               as water_area_sq_m,
    {{ to_number('"ALAND_SQMI"') }}           as land_area_sq_mi,
    {{ to_number('"AWATER_SQMI"') }}          as water_area_sq_mi,
    {{ to_number('"INTPTLAT"') }}             as internal_point_latitude,
    {{ to_number('"INTPTLONG"') }}            as internal_point_longitude,
    {{ lineage_columns() }}
from {{ source('raw', 'CENSUS_GAZETTEER_2024_COUNTIES') }}
