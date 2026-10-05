-- S-40 Census Geocoder (geographies by coordinates, vintage ACS2024_Current): the county that
-- contains each FAA commercial-service airport's NASR reference point (Phase 6 source extension).
-- Grain: one row per commercial-service airport (516).
-- county_fips is the official 5-digit county GEOID returned by the Census service, so the airport
-- -> county relationship no longer depends on matching NASR county NAMES (A-032 hardened).
-- The NASR reference point is a single point: an airport whose land spans two counties (e.g. DFW)
-- is placed in the county containing that point.
select
    {{ clean_text('"AIRPORT_CODE"') }}               as airport_code,
    {{ to_number('"INPUT_LATITUDE"') }}              as input_latitude,
    {{ to_number('"INPUT_LONGITUDE"') }}             as input_longitude,
    {{ clean_text('"BENCHMARK_NAME"') }}             as geocoder_benchmark,
    {{ clean_text('"VINTAGE_NAME"') }}               as geocoder_vintage,
    {{ to_integer('"COUNTY_MATCH_COUNT"') }}         as county_match_count,
    {{ clean_text('"COUNTY_GEOID"') }}               as county_fips,
    {{ clean_text('"COUNTY_STATE"') }}               as state_fips,
    {{ clean_text('"COUNTY_NAME"') }}                as county_name,
    {{ clean_text('"COUNTY_COUNTYNS"') }}            as county_gnis_code,
    {{ clean_text('"COUNTY_FUNCSTAT"') }}            as county_functional_status,
    {{ lineage_columns() }}
from {{ source('raw', 'CENSUS_GEOCODER_AIRPORT_COUNTY_ACS2024') }}
