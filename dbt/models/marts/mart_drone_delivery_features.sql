-- MART_DRONE_DELIVERY_FEATURES: the frozen PRE-REGULATORY drone delivery feature set (Phase 6).
-- Grain: one row per frozen market (35).
-- Columns: keys, then exactly the ACTIVE drone features in DIM_FEATURE (tested both ways), then
-- qa_* quality flags. Nothing is normalized, weighted, scored or ranked.
-- C4 Regulatory & Autonomy Readiness is PENDING PHASE 6.5.
-- Wind is a coarse PROXY (climatological mean wind speed); the wind station distance is kept visible.
select
    market_id,
    market_name,
    -- C1 Demand & market opportunity
    population_2025_log1p,
    restaurants_per_10k_pop,
    retail_establishments_per_10k_pop,
    median_household_income_usd,
    -- C2 Operating environment
    days_precip_ge_010_in,
    days_tmax_ge_90f,
    annual_snowfall_in,
    annual_mean_wind_mph,
    -- C3 Economic attractiveness
    courier_median_annual_wage_usd,
    -- C5 Infrastructure & mode fit
    share_single_family_detached,
    -- QA
    climate_station_id                  as qa_climate_station_id,
    climate_fallback_flag               as qa_climate_station_fallback_flag,
    snow_fallback_flag                  as qa_snow_station_fallback_flag,
    wind_station_id                     as qa_wind_station_id,
    wind_station_distance_km            as qa_wind_station_distance_km,
    wind_station_distance_flag          as qa_wind_station_distance_flag
from {{ ref('int_market__production_features') }}
