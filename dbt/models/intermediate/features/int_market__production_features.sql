-- PRODUCTION FEATURE VALUES, all modes, before any scoring (Phase 6).
-- Grain: one row per market (35).
-- Every column is either a production feature listed in seeds/feature_contract.csv, the untransformed
-- value behind a transformed feature, or a QA/lineage field. Mode marts select from here.
-- Transformations are limited to those approved in the contract: PER_CAPITA, POPULATION_WEIGHTED
-- (in the upstream mapping models) and LOG1P. Nothing is normalized, scaled, weighted or ranked.
-- All ratios are computed in FLOAT: Snowflake NUMBER / NUMBER division would round to 6 decimals.
with d as (
    select market_id, cbsa_name, population_2025::float as population_2025
    from {{ ref('dim_market') }}
),

acs as (
    select
        market_id,
        workers_taxi_or_ride_hailing::float          as workers_taxi_or_ride_hailing,
        workers_taxi_or_ride_hailing_moe::float      as workers_taxi_or_ride_hailing_moe,
        workers_16_plus::float                       as workers_16_plus,
        median_household_income_usd::float           as median_household_income_usd,
        housing_units_1_detached::float              as housing_units_1_detached,
        housing_units_total::float                   as housing_units_total
    from {{ ref('fct_market_acs_demographics') }}
),

cbp as (
    select
        market_id,
        max(iff(naics_code = '------', establishments, null))::float as establishments_all_sectors,
        max(iff(naics_code = '44----', establishments, null))::float as establishments_retail_trade,
        max(iff(naics_code = '7225//', establishments, null))::float as establishments_restaurants
    from {{ ref('fct_market_business_patterns') }}
    group by market_id
)

select
    d.market_id,
    d.cbsa_name                                                            as market_name,

    -- Demand & market opportunity
    d.population_2025,
    ln(1 + d.population_2025)                                              as population_2025_log1p,
    den.population_weighted_tract_density,
    ln(1 + den.population_weighted_tract_density)                          as pw_tract_density_log1p,
    acs.workers_taxi_or_ride_hailing / acs.workers_16_plus                 as share_taxi_or_ride_hailing,
    air.enplanements_per_resident::float                                   as enplanements_per_resident,
    ln(1 + air.enplanements_per_resident::float)                           as enplanements_per_resident_log1p,
    acs.median_household_income_usd,
    cbp.establishments_retail_trade / d.population_2025 * 10000            as retail_establishments_per_10k_pop,
    cbp.establishments_restaurants / d.population_2025 * 10000             as restaurants_per_10k_pop,

    -- Economic attractiveness
    cbp.establishments_all_sectors / d.population_2025 * 1000              as establishments_per_1k_pop,
    lab.shuttle_chauffeur_median_annual_wage_usd::float                    as shuttle_chauffeur_median_annual_wage_usd,
    lab.courier_median_annual_wage_usd::float                              as courier_median_annual_wage_usd,

    -- Operating environment
    cl.days_precip_ge_010_in,
    cl.days_tmax_ge_90f,
    cl.annual_snowfall_in,
    cl.annual_mean_wind_mph,

    -- Infrastructure & mode fit
    wk.population_weighted_walkability,
    acs.housing_units_1_detached / acs.housing_units_total                 as share_single_family_detached,

    -- Diagnostics (contract status DIAGNOSTIC: never independent scoring signals)
    den.raw_msa_density_diagnostic,
    den.pw_block_group_density_sld2018_diagnostic,
    air.a4_enplanements_per_resident_diagnostic,
    cl.p90_of_hourly_normals_mph_diagnostic,

    -- QA and lineage
    den.known_gap_flag                                                     as density_known_gap_flag,
    den.population_coverage_pct                                            as density_population_coverage_pct,
    (acs.workers_taxi_or_ride_hailing_moe / 1.645) / acs.workers_taxi_or_ride_hailing as taxi_commuters_cv,
    air.commercial_airport_count,
    air.included_airport_codes,
    cl.climate_station_id,
    cl.climate_station_distance_km,
    cl.climate_fallback_flag,
    cl.snow_station_id,
    cl.snow_fallback_flag,
    cl.wind_station_id,
    cl.wind_station_distance_km,
    cl.wind_station_distance_flag,
    wk.transit_missing_population_share,
    lab.shuttle_chauffeur_wage_marker,
    lab.courier_wage_marker
from d
left join acs on acs.market_id = d.market_id
left join cbp on cbp.market_id = d.market_id
left join {{ ref('int_market__population_weighted_density') }} den on den.market_id = d.market_id
left join {{ ref('int_market__airport_activity') }} air on air.market_id = d.market_id
left join {{ ref('int_market__climate') }} cl on cl.market_id = d.market_id
left join {{ ref('int_market__walkability') }} wk on wk.market_id = d.market_id
left join {{ ref('int_market__labor_cost') }} lab on lab.market_id = d.market_id
