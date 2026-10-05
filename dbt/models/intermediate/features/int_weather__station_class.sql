-- Authoritative NOAA station class for every normals station (W5 rule input).
-- Grain: one row per normals station (dim_weather_station).
--
-- is_plcd: HOMR (S-41) lists the station as PLCD (Primary Local Climatological Data) in a history
--   period that contains w5_station_class_as_of (2020-12-31, the last day of the 1991-2020 normals).
--   HOMR first records PLCD in periods beginning 2017-10-01, so the date must fall after that.
--   Using the station's CURRENT class instead would differ for one selected station: Los Angeles
--   Civic Center (USW00093134) lost PLCD in May 2024.
-- is_wban_numbered: the GHCN-Daily network code is W ('USW' prefix), meaning the station is
--   identified by a WBAN number (GHCN-Daily readme, section IV). That is a numbering system, NOT
--   a station class: it is kept as a descriptive attribute only and is never used by W5.
-- Stations absent from EMSHR (38 of 15,656, none near a market centre) are not PLCD.
with periods as (
    select *
    from {{ ref('stg_noaa__homr_emshr_lite_202609') }}
    where ghcnd_id is not null
      and period_begin_date <= '{{ var("w5_station_class_as_of") }}'::date
      and period_end_date   >= '{{ var("w5_station_class_as_of") }}'::date
),

as_of as (
    select
        ghcnd_id,
        boolor_agg(is_plcd)                                                   as is_plcd,
        boolor_agg(is_asos)                                                   as is_asos,
        boolor_agg(is_awos)                                                   as is_awos,
        listagg(distinct station_types, ' | ') within group (order by station_types) as station_types_as_of
    from periods
    group by ghcnd_id
),

current_class as (
    select ghcnd_id, boolor_agg(is_plcd) as is_plcd_current
    from {{ ref('stg_noaa__homr_emshr_lite_202609') }}
    where ghcnd_id is not null and is_open_period
    group by ghcnd_id
),

in_emshr as (
    select distinct ghcnd_id from {{ ref('stg_noaa__homr_emshr_lite_202609') }} where ghcnd_id is not null
)

select
    s.station_id,
    e.ghcnd_id is not null                         as has_emshr_record,
    coalesce(a.is_plcd, false)                     as is_plcd,
    coalesce(a.is_asos, false)                     as is_asos,
    coalesce(a.is_awos, false)                     as is_awos,
    coalesce(c.is_plcd_current, false)             as is_plcd_current,
    a.station_types_as_of,
    '{{ var("w5_station_class_as_of") }}'::date    as station_class_as_of,
    s.station_id like 'USW%'                       as is_wban_numbered
from {{ ref('dim_weather_station') }} s
left join in_emshr e on e.ghcnd_id = s.station_id
left join as_of a on a.ghcnd_id = s.station_id
left join current_class c on c.ghcnd_id = s.station_id
