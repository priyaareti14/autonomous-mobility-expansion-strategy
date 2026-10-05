-- S-19 FAA NASR APT_BASE, edition effective 2026-09-03.
-- Grain: one row per landing facility. airport_code (ARPT_ID, FAA location identifier) is unique.
-- site_no repeats once in this edition (23747.31, airport 9XS4 and heliport 16XA), so it is NOT a key.
-- County is published as a name, not a FIPS code; it is kept as published and not mapped (A-009).
select
    {{ clean_text('"ARPT_ID"') }}                     as airport_code,
    {{ clean_text('"ICAO_ID"') }}                     as icao_code,
    {{ clean_text('"SITE_NO"') }}                     as site_no,
    {{ clean_text('"SITE_TYPE_CODE"') }}              as site_type_code,
    {{ clean_text('"ARPT_NAME"') }}                   as facility_name,
    {{ clean_text('"CITY"') }}                        as city_published,
    {{ clean_text('"STATE_CODE"') }}                  as state_usps,
    {{ clean_text('"COUNTY_NAME"') }}                 as county_name_published,
    {{ clean_text('"COUNTY_ASSOC_STATE"') }}          as county_state_usps,
    {{ clean_text('"OWNERSHIP_TYPE_CODE"') }}         as ownership_type_code,
    {{ clean_text('"FACILITY_USE_CODE"') }}           as facility_use_code,
    {{ clean_text('"ARPT_STATUS"') }}                 as facility_status_code,
    {{ clean_text('"FAR_139_TYPE_CODE"') }}           as far_139_type_code,
    {{ to_number('"LAT_DECIMAL"') }}                  as latitude,
    {{ to_number('"LONG_DECIMAL"') }}                 as longitude,
    {{ to_number('"ELEV"') }}                         as elevation_ft,
    try_to_date({{ clean_text('"EFF_DATE"') }}, 'YYYY/MM/DD') as nasr_effective_date,
    {{ lineage_columns() }}
from {{ source('raw', 'FAA_NASR_APT_BASE_20260903') }}
