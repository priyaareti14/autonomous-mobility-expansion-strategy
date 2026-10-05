-- S-41 NOAA NCEI HOMR Enhanced Master Station History Report, Lite edition 202609.
-- Grain: one row per station history-period record, as published (no unique key: a station can
-- hold several records for one period). One record (row 295321, a Svalbard station whose name
-- contains a line break) has no parseable dates; it is kept, with null dates.
-- station_types: EMSHR field TYPE, "station type and/or platforms station participates in",
-- comma-delimited (Reference Table B of MSHR_Enhanced_Lite_Table.txt). Flags expose the codes the
-- W5 rule documents; the full list stays in station_types / station_type_list.
--   PLCD = Primary Local Climatological Data   ASOS = Automated Surface Observation System
--   AWOS = Airway Weather Observation          AIRWAYS = Surface Airways Observations
--   COOP = COOPerative station                 MILITARY = Military Bases
-- HOMR first records PLCD in periods beginning 2017-10-01; earlier periods do not carry the code.
with src as (
    select
        {{ clean_text('"NCDC"') }}                                         as ncdc_station_id,
        try_to_date({{ clean_text('"BEG_DT"') }}, 'YYYYMMDD')              as period_begin_date,
        try_to_date({{ clean_text('"END_DT"') }}, 'YYYYMMDD')              as period_end_date,
        {{ clean_text('"GHCND"') }}                                        as ghcnd_id,
        {{ clean_text('"WBAN"') }}                                         as wban_id,
        {{ clean_text('"COOP"') }}                                         as coop_id,
        {{ clean_text('"ICAO"') }}                                         as icao_id,
        {{ clean_text('"STATION_NAME"') }}                                 as station_name,
        {{ clean_text('"ST"') }}                                           as state_usps,
        {{ clean_text('"TYPE"') }}                                         as station_types,
        split({{ clean_text('"TYPE"') }}, ',')                             as station_type_list,
        {{ lineage_columns() }}
    from {{ source('raw', 'NOAA_HOMR_EMSHR_LITE_202609') }}
)

select
    ncdc_station_id,
    period_begin_date,
    period_end_date,
    period_end_date = '9999-12-31'::date                                   as is_open_period,
    ghcnd_id,
    wban_id,
    coop_id,
    icao_id,
    station_name,
    state_usps,
    station_types,
    station_type_list,
    coalesce(array_contains('PLCD'::variant, station_type_list), false)     as is_plcd,
    coalesce(array_contains('ASOS'::variant, station_type_list), false)     as is_asos,
    coalesce(array_contains('AWOS'::variant, station_type_list), false)     as is_awos,
    coalesce(array_contains('AIRWAYS'::variant, station_type_list), false)  as is_airways,
    coalesce(array_contains('COOP'::variant, station_type_list), false)     as is_coop,
    coalesce(array_contains('MILITARY'::variant, station_type_list), false) as is_military,
    ingest_run_id, ingested_at, source_id, source_vintage, source_file, source_file_sha256, source_row_number
from src
