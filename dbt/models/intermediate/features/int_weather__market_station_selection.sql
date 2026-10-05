-- W5 WEATHER STATION SELECTION (approved Phase 5 rule, A-007 / A-021). Deterministic.
-- Grain: one row per market x station_role (35 x 3 = 105).
--
-- Distances: great-circle km (Snowflake HAVERSINE) from the market's population-weighted centre
-- (int_market__population_center) to each station. Ties break on station_id.
--
-- station_role GENERAL_CLIMATE (precipitation and temperature elements):
--   1. nearest CORE-QUALIFYING PLCD station (NOAA HOMR class) within w5_plcd_max_km (25 km)
--        -> selection_rule PLCD_WITHIN_25KM
--   2. otherwise the nearest CORE-QUALIFYING station of any network
--        -> selection_rule NEAREST_QUALIFYING_ANY_NETWORK (fallback_flag = true)
-- station_role SNOW:
--   1. the GENERAL_CLIMATE station, if it is SNOW-QUALIFYING        -> SAME_AS_GENERAL_STATION
--   2. otherwise the nearest SNOW-QUALIFYING station within 50 km    -> SNOW_FALLBACK_WITHIN_50KM
--   3. otherwise no station (value SOURCE_NOT_PUBLISHED, never zero)  -> SOURCE_NOT_PUBLISHED
-- station_role WIND:
--   the nearest station with hourly wind normals (a separate NCEI product) -> NEAREST_HOURLY_WIND_STATION.
--   It is not distance-capped; long distances are preserved and flagged (Austin, Miami).
-- Definitions of core-qualifying, snow-qualifying and PLCD: int_weather__station_qualification and
-- int_weather__station_class (PLCD as of 2020-12-31, HOMR S-41; never inferred from the 'USW' prefix).
with centers as (
    select * from {{ ref('int_market__population_center') }}
),

distances as (
    select
        c.market_id,
        s.*,
        haversine(c.pw_center_latitude, c.pw_center_longitude, s.latitude, s.longitude) as distance_km
    from centers c
    cross join {{ ref('int_weather__station_qualification') }} s
    where s.latitude is not null and s.longitude is not null
),

considered as (
    select
        market_id,
        count(*)                                                                         as stations_considered,
        count_if(is_core_qualifying)                                                     as core_qualifying_stations,
        count_if(is_core_qualifying and is_plcd
                 and distance_km <= {{ var('w5_plcd_max_km') }})                         as plcd_candidates_within_cap,
        count_if(is_snow_qualifying and distance_km <= {{ var('w5_snow_fallback_max_km') }}) as snow_candidates_within_cap,
        count_if(has_hourly_wind_normals)                                                as hourly_wind_stations
    from distances
    group by market_id
),

plcd as (
    select market_id, station_id, distance_km
    from distances
    where is_core_qualifying and is_plcd and distance_km <= {{ var('w5_plcd_max_km') }}
    qualify row_number() over (partition by market_id order by distance_km, station_id) = 1
),

any_network as (
    select market_id, station_id, distance_km
    from distances
    where is_core_qualifying
    qualify row_number() over (partition by market_id order by distance_km, station_id) = 1
),

general as (
    select
        c.market_id,
        'GENERAL_CLIMATE'                                                         as station_role,
        coalesce(f.station_id, a.station_id)                                      as station_id,
        coalesce(f.distance_km, a.distance_km)                                    as distance_km,
        iff(f.station_id is not null, 'PLCD_WITHIN_{{ var("w5_plcd_max_km") }}KM',
            'NEAREST_QUALIFYING_ANY_NETWORK')                                     as selection_rule,
        f.station_id is null                                                      as fallback_flag
    from centers c
    left join plcd f on f.market_id = c.market_id
    left join any_network a on a.market_id = c.market_id
),

snow_fallback as (
    select market_id, station_id, distance_km
    from distances
    where is_snow_qualifying and distance_km <= {{ var('w5_snow_fallback_max_km') }}
    qualify row_number() over (partition by market_id order by distance_km, station_id) = 1
),

snow as (
    select
        g.market_id,
        'SNOW'                                                                    as station_role,
        iff(q.is_snow_qualifying, g.station_id, sf.station_id)                    as station_id,
        iff(q.is_snow_qualifying, g.distance_km, sf.distance_km)                  as distance_km,
        case when q.is_snow_qualifying then 'SAME_AS_GENERAL_STATION'
             when sf.station_id is not null then 'SNOW_FALLBACK_WITHIN_{{ var("w5_snow_fallback_max_km") }}KM'
             else 'SOURCE_NOT_PUBLISHED' end                                      as selection_rule,
        not q.is_snow_qualifying                                                  as fallback_flag
    from general g
    inner join {{ ref('int_weather__station_qualification') }} q on q.station_id = g.station_id
    left join snow_fallback sf on sf.market_id = g.market_id
),

wind as (
    select
        market_id,
        'WIND'                                                                    as station_role,
        station_id,
        distance_km,
        'NEAREST_HOURLY_WIND_STATION'                                             as selection_rule,
        null::boolean                                                             as fallback_flag
    from distances
    where has_hourly_wind_normals
    qualify row_number() over (partition by market_id order by distance_km, station_id) = 1
),

selected as (
    select * from general
    union all select * from snow
    union all select * from wind
)

select
    sel.market_id,
    sel.station_role,
    sel.station_id,
    q.station_name,
    iff(q.is_plcd, 'PLCD', 'NON_PLCD')                                            as station_type,
    q.is_wban_numbered,
    q.station_types_as_of                                                         as homr_station_types_2020_12_31,
    round(sel.distance_km, 2)                                                     as distance_km,
    sel.selection_rule,
    coalesce(sel.fallback_flag, sel.station_id <> g.station_id)                   as fallback_flag,
    sel.station_id = g.station_id                                                 as same_as_general_station,
    case sel.station_role
        when 'GENERAL_CLIMATE' then 'CORE_ELEMENTS_FLAG_' || iff(q.is_core_qualifying, 'S_OR_R', 'NOT_QUALIFYING')
        when 'SNOW' then iff(sel.station_id is null, 'SNOW_NOT_PUBLISHED',
                             'SNOW_FLAG_' || q.annual_snowfall_in_comp_flag)
        when 'WIND' then iff(q.has_hourly_wind_normals, 'HOURLY_WIND_NORMALS', 'NO_HOURLY_WIND')
    end                                                                           as data_completeness_flag,
    sel.distance_km > {{ var('w5_plcd_max_km') }}                                 as distance_exceeds_25km_flag,
    c.stations_considered,
    c.core_qualifying_stations,
    c.plcd_candidates_within_cap,
    c.snow_candidates_within_cap,
    c.hourly_wind_stations
from selected sel
inner join general g on g.market_id = sel.market_id
left join {{ ref('int_weather__station_qualification') }} q on q.station_id = sel.station_id
inner join considered c on c.market_id = sel.market_id
