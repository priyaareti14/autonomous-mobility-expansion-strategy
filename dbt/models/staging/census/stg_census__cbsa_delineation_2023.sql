-- S-02 OMB / Census July 2023 delineation (list1_2023).
-- Grain: one row per county (county-equivalent) within a CBSA.
select
    {{ clean_text('"CBSA_CODE"') }}                                  as cbsa_code,
    {{ clean_text('"METROPOLITAN_DIVISION_CODE"') }}                 as metro_division_code,
    {{ clean_text('"CSA_CODE"') }}                                   as csa_code,
    {{ clean_text('"CBSA_TITLE"') }}                                 as cbsa_title,
    {{ clean_text('"METROPOLITAN_MICROPOLITAN_STATISTICAL_AREA"') }} as cbsa_type,
    {{ clean_text('"METROPOLITAN_DIVISION_TITLE"') }}                as metro_division_title,
    {{ clean_text('"CSA_TITLE"') }}                                  as csa_title,
    {{ clean_text('"COUNTY_COUNTY_EQUIVALENT"') }}                   as county_name,
    {{ clean_text('"STATE_NAME"') }}                                 as state_name,
    {{ clean_text('"FIPS_STATE_CODE"') }}                            as state_fips,
    {{ clean_text('"FIPS_COUNTY_CODE"') }}                           as county_code,
    {{ clean_text('"FIPS_STATE_CODE"') }} || {{ clean_text('"FIPS_COUNTY_CODE"') }} as county_fips,
    {{ clean_text('"CENTRAL_OUTLYING_COUNTY"') }}                    as central_outlying,
    {{ lineage_columns() }}
from {{ source('raw', 'CENSUS_CBSA_DELINEATION_2023') }}
