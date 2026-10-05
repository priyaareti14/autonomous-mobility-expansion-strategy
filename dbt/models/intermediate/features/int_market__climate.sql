-- Market-level climate features under the W5 station rule.
-- Grain: one row per market (35).
-- Only the Phase 5 KEEP/MODIFY climate measures are carried:
--   days_precip_ge_010_in  (ANN-PRCP-AVGNDS-GE010HI, days/yr)   from the GENERAL_CLIMATE station
--   days_tmax_ge_90f       (ANN-TMAX-AVGNDS-GRTH090, days/yr)   from the GENERAL_CLIMATE station
--   annual_snowfall_in     (ANN-SNOW-NORMAL, inches)            from the SNOW station
--   annual_mean_wind_mph   (mean of HLY-WIND-AVGSPD, mph)       from the WIND station
-- Deferred or dropped in Phase 5 and therefore NOT carried: annual precipitation, freeze days and
-- mean temperature. The p90-of-hourly-normals wind statistic is carried only as a labelled diagnostic.
-- Every value is traceable to its station, rule, distance and completeness flag.
with sel as (
    select * from {{ ref('int_weather__market_station_selection') }}
),

g as (select * from sel where station_role = 'GENERAL_CLIMATE'),
s as (select * from sel where station_role = 'SNOW'),
w as (select * from sel where station_role = 'WIND')

select
    g.market_id,
    qg.days_precip_ge_010_in,
    qg.days_tmax_ge_90f,
    qs.annual_snowfall_in,
    ws.annual_mean_wind_mph,
    ws.p90_of_hourly_normals_mph_diagnostic,
    -- lineage: general climate station
    g.station_id                         as climate_station_id,
    g.station_name                       as climate_station_name,
    g.station_type                       as climate_station_type,
    g.distance_km                        as climate_station_distance_km,
    g.selection_rule                     as climate_selection_rule,
    g.fallback_flag                      as climate_fallback_flag,
    qg.days_precip_ge_010_in_comp_flag   as days_precip_ge_010_in_comp_flag,
    qg.days_tmax_ge_90f_comp_flag        as days_tmax_ge_90f_comp_flag,
    -- lineage: snow station
    s.station_id                         as snow_station_id,
    s.distance_km                        as snow_station_distance_km,
    s.selection_rule                     as snow_selection_rule,
    s.fallback_flag                      as snow_fallback_flag,
    qs.annual_snowfall_in_comp_flag      as annual_snowfall_in_comp_flag,
    -- lineage: wind station
    w.station_id                         as wind_station_id,
    w.station_name                       as wind_station_name,
    w.distance_km                        as wind_station_distance_km,
    w.same_as_general_station            as wind_station_same_as_climate_station,
    w.distance_exceeds_25km_flag         as wind_station_distance_flag,
    ws.missing_hours                     as wind_missing_hours,
    'NOAA Normals 1991-2020'             as climate_vintage
from g
inner join s on s.market_id = g.market_id
inner join w on w.market_id = g.market_id
left join {{ ref('int_weather__station_qualification') }} qg on qg.station_id = g.station_id
left join {{ ref('int_weather__station_qualification') }} qs on qs.station_id = s.station_id
left join {{ ref('int_weather__station_wind_summary') }} ws on ws.station_id = w.station_id
