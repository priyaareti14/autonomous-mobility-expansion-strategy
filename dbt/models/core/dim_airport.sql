-- DIM_AIRPORT: every NASR landing facility (edition 2026-09-03).
-- Grain: one row per facility; airport_code = FAA location identifier (unique).
-- Airports are NOT assigned to markets (A-009): candidate distances are in
-- INTERMEDIATE.int_airports__airport_market_candidates.
select
    airport_code,
    icao_code,
    site_no,
    site_type_code,
    facility_name,
    city_published,
    state_usps,
    county_name_published,
    county_state_usps,
    ownership_type_code,
    facility_use_code,
    facility_status_code,
    far_139_type_code,
    latitude,
    longitude,
    elevation_ft,
    nasr_effective_date,
    source_vintage as nasr_vintage
from {{ ref('stg_faa__nasr_apt_base') }}
