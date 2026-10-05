-- MART_SIDEWALK_DELIVERY_FEATURES: the frozen PRE-REGULATORY sidewalk delivery robot feature set (Phase 6).
-- Grain: one row per frozen market (35).
-- Columns: keys, then exactly the ACTIVE sidewalk features in DIM_FEATURE (tested both ways), then
-- qa_* quality flags. Nothing is normalized, weighted, scored or ranked.
-- C4 Regulatory & Autonomy Readiness is PENDING PHASE 6.5.
-- Known correlated pair (reported, not hidden): pw_tract_density_log1p (C1) and
-- population_weighted_walkability (C5), Spearman 0.88: distinct concepts in distinct components.
select
    market_id,
    market_name,
    -- C1 Demand & market opportunity
    population_2025_log1p,
    pw_tract_density_log1p,
    restaurants_per_10k_pop,
    retail_establishments_per_10k_pop,
    median_household_income_usd,
    -- C2 Operating environment
    days_precip_ge_010_in,
    days_tmax_ge_90f,
    annual_snowfall_in,
    -- C3 Economic attractiveness
    courier_median_annual_wage_usd,
    -- C5 Infrastructure & mode fit
    population_weighted_walkability,
    -- QA
    density_known_gap_flag              as qa_density_known_gap_flag,
    transit_missing_population_share    as qa_walkability_transit_missing_population_share,
    climate_station_id                  as qa_climate_station_id,
    climate_fallback_flag               as qa_climate_station_fallback_flag,
    snow_fallback_flag                  as qa_snow_station_fallback_flag
from {{ ref('int_market__production_features') }}
