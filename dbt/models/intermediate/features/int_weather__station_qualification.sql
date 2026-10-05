-- W5 station definitions, applied to every NOAA normals station. No market is involved yet.
-- Grain: one row per station (annual/seasonal and hourly-only stations, 15,656).
--
-- Definitions (approved W5 rule; constants in dbt_project.yml vars):
--   CORE ELEMENTS: the annual normals the climate features need:
--       ANN-PRCP-NORMAL, ANN-PRCP-AVGNDS-GE010HI, ANN-TMAX-AVGNDS-GRTH090, ANN-TMIN-AVGNDS-LSTH032,
--       ANN-TAVG-NORMAL (the same five elements evaluated in Phase 5).
--   CORE-QUALIFYING station: publishes all five with a numeric value and NCEI completeness flag
--       S (Standard: >= 24 years, gap-filled) or R (Representative: >= 10 years, gap-filled).
--   SNOW-QUALIFYING station: publishes ANN-SNOW-NORMAL and ANN-SNOW-AVGNDS-GE010TI with flag S or P
--       (P = Provisional, >= 10 years; NCEI cannot gap-fill snow, so no snow normal carries R).
--       A blank snow value is missing, never zero (A-021). No snow normal in the archive is trace (-7777).
--   PLCD station: NOAA HOMR lists the station as PLCD (Primary Local Climatological Data) in the
--       history period containing w5_station_class_as_of (2020-12-31), per int_weather__station_class
--       (source S-41, EMSHR TYPE). The station ID prefix is NOT used: 'USW' only means the station is
--       numbered by WBAN (GHCN-Daily readme section IV), and 207 core-qualifying 'USW' stations are not PLCD.
--   HOURLY-WIND station: has 1991-2020 hourly wind normals (S-13).
with s as (
    select * from {{ ref('dim_weather_station') }}
),

cls as (
    select * from {{ ref('int_weather__station_class') }}
),

n as (
    select * from {{ ref('fct_station_climate_normals') }}
)

select
    s.station_id,
    s.station_name,
    s.latitude,
    s.longitude,
    s.has_annual_normals,
    s.has_hourly_wind_normals,
    cls.is_plcd,
    cls.is_wban_numbered,
    cls.station_types_as_of,
    coalesce(
        (n.annual_precip_in is not null      and n.annual_precip_in_comp_flag      in {{ in_list(var('w5_core_flags')) }})
        and (n.days_precip_ge_010_in is not null and n.days_precip_ge_010_in_comp_flag in {{ in_list(var('w5_core_flags')) }})
        and (n.days_tmax_ge_90f is not null  and n.days_tmax_ge_90f_comp_flag      in {{ in_list(var('w5_core_flags')) }})
        and (n.days_tmin_le_32f is not null  and n.days_tmin_le_32f_comp_flag      in {{ in_list(var('w5_core_flags')) }})
        and (n.annual_mean_temp_f is not null and n.annual_mean_temp_f_comp_flag   in {{ in_list(var('w5_core_flags')) }}),
        false)                                                                   as is_core_qualifying,
    coalesce(
        (n.annual_snowfall_in is not null    and n.annual_snowfall_in_comp_flag    in {{ in_list(var('w5_snow_flags')) }})
        and (n.days_snowfall_ge_1_in is not null and n.days_snowfall_ge_1_in_comp_flag in {{ in_list(var('w5_snow_flags')) }}),
        false)                                                                   as is_snow_qualifying,
    n.annual_precip_in,          n.annual_precip_in_comp_flag,
    n.days_precip_ge_010_in,     n.days_precip_ge_010_in_comp_flag,     n.days_precip_ge_010_in_years,
    n.days_tmax_ge_90f,          n.days_tmax_ge_90f_comp_flag,          n.days_tmax_ge_90f_years,
    n.days_tmin_le_32f,          n.days_tmin_le_32f_comp_flag,
    n.annual_mean_temp_f,        n.annual_mean_temp_f_comp_flag,
    n.annual_snowfall_in,        n.annual_snowfall_in_comp_flag,        n.annual_snowfall_in_years,
    n.annual_snowfall_in_is_published,
    n.days_snowfall_ge_1_in,     n.days_snowfall_ge_1_in_comp_flag
from s
left join n on n.station_id = s.station_id
left join cls on cls.station_id = s.station_id
