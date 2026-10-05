-- Annual wind statistics per hourly-normals station (S-13).
-- Grain: one row per station with hourly wind normals (467).
-- Unit: miles per hour (confirmed in Phase 5, NCEI Normals_HLY_Documentation section III.A).
--
-- WHAT THE STATISTICS MEAN. Each HLY-WIND-AVGSPD value is the 1991-2020 climatological mean wind
-- speed for one hour of the normal year (8,760 values per station).
--   annual_mean_wind_mph: the mean of those 8,760 hourly normals = the station's climatological mean
--       wind speed. ADOPTED as the drone wind feature (a coarse proxy, see production_feature_layer.md).
--   p90_of_hourly_normals_mph_diagnostic: the 90th percentile of the 8,760 climatological HOURLY
--       MEANS. It describes the windiest hours of an average year, NOT the 90th percentile of observed
--       wind and NOT gust or extreme-wind frequency. Kept as a diagnostic only, under a name that says so.
--   Missing hours (-9999) are excluded from both statistics and counted.
select
    station_id,
    count(*)                                                       as hours,
    count_if(wind_avg_speed_is_missing)                            as missing_hours,
    avg(iff(wind_avg_speed_is_missing, null, wind_avg_speed))      as annual_mean_wind_mph,
    approx_percentile(iff(wind_avg_speed_is_missing, null, wind_avg_speed), 0.9)
                                                                   as p90_of_hourly_normals_mph_diagnostic,
    avg(iff(wind_pct_calm_is_missing, null, wind_pct_calm))        as mean_pct_calm_hours,
    'mph'                                                          as wind_speed_unit
from {{ ref('fct_station_hourly_wind_normals') }}
group by station_id
