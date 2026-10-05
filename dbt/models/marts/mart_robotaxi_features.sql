-- MART_ROBOTAXI_FEATURES: the frozen PRE-REGULATORY robotaxi feature set (Phase 6).
-- Grain: one row per frozen market (35).
-- Columns: keys, then exactly the ACTIVE robotaxi features in DIM_FEATURE (tested both ways), then
-- qa_* quality flags. Feature values are model inputs as defined in the contract (LOG1P where
-- stated); NOTHING is normalized, weighted, scored or ranked. C4 Regulatory & Autonomy Readiness
-- is PENDING PHASE 6.5; C5 Infrastructure & Mode Fit has no active robotaxi feature (candidates DEFERRED).
select
    market_id,
    market_name,
    -- C1 Demand & market opportunity
    population_2025_log1p,
    pw_tract_density_log1p,
    share_taxi_or_ride_hailing,
    enplanements_per_resident_log1p,
    median_household_income_usd,
    -- C2 Operating environment
    days_precip_ge_010_in,
    days_tmax_ge_90f,
    annual_snowfall_in,
    -- C3 Economic attractiveness
    shuttle_chauffeur_median_annual_wage_usd,
    establishments_per_1k_pop,
    -- QA
    density_known_gap_flag              as qa_density_known_gap_flag,
    taxi_commuters_cv                   as qa_taxi_commuters_cv,
    commercial_airport_count            as qa_commercial_airport_count,
    included_airport_codes              as qa_included_airport_codes,
    climate_station_id                  as qa_climate_station_id,
    climate_fallback_flag               as qa_climate_station_fallback_flag,
    snow_fallback_flag                  as qa_snow_station_fallback_flag
from {{ ref('int_market__production_features') }}
