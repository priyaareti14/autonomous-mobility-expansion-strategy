-- DIM_WEATHER_STATION: every NOAA normals station (annual/seasonal and/or hourly).
-- Grain: one row per station_id. Stations are NOT assigned to markets (A-007): candidate
-- distances are in INTERMEDIATE.int_weather__station_market_candidates.
select
    station_id,
    station_name,
    latitude,
    longitude,
    elevation_m,
    has_annual_normals,
    has_hourly_wind_normals,
    hourly_wind_rows
from {{ ref('int_weather__stations') }}
