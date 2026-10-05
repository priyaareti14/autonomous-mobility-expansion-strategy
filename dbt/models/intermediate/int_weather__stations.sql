-- Every weather station in either normals product, with its attributes.
-- Grain: one row per station_id (annual/seasonal 15,616, plus 40 hourly-only stations).
-- Attributes come from the annual record where present, otherwise from the hourly product.
with annual as (
    select station_id, station_name, latitude, longitude, elevation_m
    from {{ ref('stg_noaa__normals_annualseasonal') }}
),

hourly as (
    select station_id,
           any_value(station_name) as station_name,
           any_value(latitude)     as latitude,
           any_value(longitude)    as longitude,
           any_value(elevation_m)  as elevation_m,
           count(*)                as hourly_rows
    from {{ ref('stg_noaa__normals_hourly_wind') }}
    group by station_id
)

select
    coalesce(a.station_id, h.station_id)       as station_id,
    coalesce(a.station_name, h.station_name)   as station_name,
    coalesce(a.latitude, h.latitude)           as latitude,
    coalesce(a.longitude, h.longitude)         as longitude,
    coalesce(a.elevation_m, h.elevation_m)     as elevation_m,
    a.station_id is not null                   as has_annual_normals,
    h.station_id is not null                   as has_hourly_wind_normals,
    coalesce(h.hourly_rows, 0)                 as hourly_wind_rows
from annual a
full outer join hourly h
    on h.station_id = a.station_id
