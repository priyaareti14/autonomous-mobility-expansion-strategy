-- S-13 NOAA U.S. Climate Normals 1991-2020, hourly wind (projected at ingestion, A-027).
-- Grain: one row per station x hour of the normal year ('MM-DDTHH:00:00'; 8,760 per station).
-- -9999 (missing: 6,746 station-hours, comp flag blank) becomes null and is flagged.
-- Speed units are as published by NCEI. The unit (believed mph) is to be confirmed against the NCEI
-- hourly normals documentation before any feature uses it (Phase 5).
{% set elements = [
    ('HLY_WIND_AVGSPD', 'wind_avg_speed'),
    ('HLY_WIND_PCTCLM', 'wind_pct_calm'),
    ('HLY_WIND_VCTDIR', 'wind_vector_direction_deg'),
    ('HLY_WIND_VCTSPD', 'wind_vector_speed'),
    ('HLY_WIND_1STDIR', 'wind_prevailing_direction_code'),
    ('HLY_WIND_1STPCT', 'wind_prevailing_direction_pct'),
    ('HLY_WIND_2NDDIR', 'wind_secondary_direction_code'),
    ('HLY_WIND_2NDPCT', 'wind_secondary_direction_pct')
] %}
select
    {{ clean_text('"STATION"') }}                       as station_id,
    {{ clean_text('"NAME"') }}                          as station_name,
    {{ to_number('"LATITUDE"') }}                       as latitude,
    {{ to_number('"LONGITUDE"') }}                      as longitude,
    {{ to_number('"ELEVATION"') }}                      as elevation_m,
    {{ clean_text('"DATE"') }}                          as normal_hour_label,
    try_to_number(substr(trim("DATE"), 1, 2))           as normal_month,
    try_to_number(substr(trim("DATE"), 4, 2))           as normal_day,
    try_to_number(substr(trim("DATE"), 7, 2))           as normal_hour,
{%- for src, alias in elements %}
    {{ noaa_value('"' ~ src ~ '"') }}                   as {{ alias }},
    {{ noaa_is_missing('"' ~ src ~ '"') }}              as {{ alias }}_is_missing,
    {{ clean_text('"COMP_FLAG_' ~ src ~ '"') }}         as {{ alias }}_comp_flag,
{%- endfor %}
    '1991-2020'                                         as normals_period,
    {{ lineage_columns() }}
from {{ source('raw', 'NOAA_NORMALS_1991_2020_HOURLY_WIND') }}
