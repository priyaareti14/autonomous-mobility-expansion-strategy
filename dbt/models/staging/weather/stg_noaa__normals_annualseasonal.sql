-- S-12 NOAA U.S. Climate Normals 1991-2020, annual/seasonal (one VARIANT record per station).
-- Grain: one row per station.
-- Exposes the station attributes and the annual elements catalogued in data_sources.md (F13-F18 + mean
-- temperature). For each element:
--   <alias>               numeric value (null when unpublished, missing -9999 or trace -7777)
--   <alias>_is_published  the station publishes this element at all (stations differ)
--   <alias>_is_missing    published as -9999
--   <alias>_is_trace      published as -7777 (non-zero value that rounds to zero)
--   <alias>_comp_flag     completeness flag (S, R, P, E ...)
--   <alias>_years         years of record used
-- No station is selected and no market is assigned here (A-007, A-021 open).
{% set elements = [
    ('ANN-PRCP-NORMAL',          'annual_precip_in'),
    ('ANN-PRCP-AVGNDS-GE001HI',  'days_precip_ge_001_in'),
    ('ANN-PRCP-AVGNDS-GE010HI',  'days_precip_ge_010_in'),
    ('ANN-PRCP-AVGNDS-GE050HI',  'days_precip_ge_050_in'),
    ('ANN-PRCP-AVGNDS-GE100HI',  'days_precip_ge_100_in'),
    ('ANN-SNOW-NORMAL',          'annual_snowfall_in'),
    ('ANN-SNOW-AVGNDS-GE010TI',  'days_snowfall_ge_1_in'),
    ('ANN-SNWD-AVGNDS-GE001WI',  'days_snow_depth_ge_1_in'),
    ('ANN-TMAX-AVGNDS-GRTH090',  'days_tmax_ge_90f'),
    ('ANN-TMIN-AVGNDS-LSTH032',  'days_tmin_le_32f'),
    ('ANN-TAVG-NORMAL',          'annual_mean_temp_f')
] %}
select
    "STATION"                                              as station_id,
    nullif(trim(record:"NAME"::string), '')                as station_name,
    {{ to_number('record:"LATITUDE"::string') }}           as latitude,
    {{ to_number('record:"LONGITUDE"::string') }}          as longitude,
    {{ to_number('record:"ELEVATION"::string') }}          as elevation_m,
{%- for key, alias in elements %}
    {{ noaa_value('record:"' ~ key ~ '"::string') }}       as {{ alias }},
    record:"{{ key }}" is not null                         as {{ alias }}_is_published,
    {{ noaa_is_missing('record:"' ~ key ~ '"::string') }}  as {{ alias }}_is_missing,
    {{ noaa_is_trace('record:"' ~ key ~ '"::string') }}    as {{ alias }}_is_trace,
    nullif(trim(record:"comp_flag_{{ key }}"::string), '') as {{ alias }}_comp_flag,
    {{ to_integer('record:"years_' ~ key ~ '"::string') }} as {{ alias }}_years,
{%- endfor %}
    '1991-2020'                                            as normals_period,
    {{ lineage_columns() }}
from {{ source('raw', 'NOAA_NORMALS_1991_2020_ANNUALSEASONAL') }}
