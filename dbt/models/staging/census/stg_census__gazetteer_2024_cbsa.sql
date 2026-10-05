-- S-05 Census 2024 Gazetteer, CBSAs. Grain: one row per CBSA.
-- cbsa_type_code: 1 = Metropolitan, 2 = Micropolitan (Gazetteer coding).
-- Positive longitudes are published with a leading '+'; try_to_double accepts it.
select
    {{ clean_text('"GEOID"') }}               as cbsa_code,
    {{ clean_text('"CSAFP"') }}               as csa_code,
    {{ clean_text('"NAME"') }}                as cbsa_name,
    {{ clean_text('"CBSA_TYPE"') }}           as cbsa_type_code,
    {{ to_number('"ALAND"') }}                as land_area_sq_m,
    {{ to_number('"AWATER"') }}               as water_area_sq_m,
    {{ to_number('"ALAND_SQMI"') }}           as land_area_sq_mi,
    {{ to_number('"AWATER_SQMI"') }}          as water_area_sq_mi,
    {{ to_number('"INTPTLAT"') }}             as internal_point_latitude,
    {{ to_number('"INTPTLONG"') }}            as internal_point_longitude,
    {{ lineage_columns() }}
from {{ source('raw', 'CENSUS_GAZETTEER_2024_CBSA') }}
