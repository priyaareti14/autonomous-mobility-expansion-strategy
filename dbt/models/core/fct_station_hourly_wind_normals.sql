-- FCT_STATION_HOURLY_WIND_NORMALS: hourly 1991-2020 wind normals per station.
-- Grain: one row per station x hour of the normal year (8,760 per station; 467 stations).
-- Units as published by NCEI (the speed unit is to be confirmed before feature use).
-- No annual or seasonal wind statistic is computed: which statistic represents drone wind
-- suitability is a Phase 5/6 feature decision (F19, PROXY).
select
    station_id,
    normal_hour_label,
    normal_month,
    normal_day,
    normal_hour,
    wind_avg_speed,              wind_avg_speed_is_missing,              wind_avg_speed_comp_flag,
    wind_pct_calm,               wind_pct_calm_is_missing,               wind_pct_calm_comp_flag,
    wind_vector_direction_deg,   wind_vector_direction_deg_is_missing,   wind_vector_direction_deg_comp_flag,
    wind_vector_speed,           wind_vector_speed_is_missing,           wind_vector_speed_comp_flag,
    wind_prevailing_direction_code,  wind_prevailing_direction_code_is_missing,
    wind_prevailing_direction_pct,   wind_prevailing_direction_pct_is_missing,
    wind_secondary_direction_code,   wind_secondary_direction_code_is_missing,
    wind_secondary_direction_pct,    wind_secondary_direction_pct_is_missing,
    normals_period,
    source_vintage as normals_vintage
from {{ ref('stg_noaa__normals_hourly_wind') }}
