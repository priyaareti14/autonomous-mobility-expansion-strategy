-- MART_MARKET_FEATURE_BASE: trusted candidate measures at market level. NOT the readiness feature matrix.
-- Grain: one row per market (exactly 35).
--
-- Included: measures PUBLISHED NATIVELY AT CBSA LEVEL, so no geographic aggregation choice is involved:
--   PEP 2025 population, Gazetteer CBSA land area, ACS 2020-2024 counts and medians (with MOEs),
--   CBP 2023 establishments for the catalogued NAICS codes, and OEWS May 2025 wages for the
--   catalogued occupations (with BLS markers).
-- Deliberately EXCLUDED (open decisions or later phases):
--   weather (A-007 / A-021), airport demand (A-009), population-weighted or urban-core density
--   (A-008), walkability aggregation, regulation (evidence step, before Phase 7), deployment
--   evidence (external validation only), and every ratio, share, normalization, index, score
--   or rank.
-- No imputation: a missing value stays null and is visible to Phase 5.
{% set naics = [
    ('------', 'all_sectors'), ('44----', 'retail_trade'), ('445///', 'food_beverage_retail'),
    ('722///', 'food_services_drinking'), ('7225//', 'restaurants'), ('492///', 'couriers_messengers')
] %}
{% set occupations = [
    ('53-3053', 'shuttle_drivers_chauffeurs'), ('53-3054', 'taxi_drivers'),
    ('43-5021', 'couriers_messengers'), ('53-3033', 'light_truck_drivers'),
    ('35-3023', 'fast_food_counter_workers')
] %}
with acs as (
    select * from {{ ref('fct_market_acs_demographics') }}
),

cbp as (
    select
        market_id
    {%- for code, alias in naics %},
        max(iff(naics_code = '{{ code }}', establishments, null))        as cbp_establishments_{{ alias }},
        max(iff(naics_code = '{{ code }}', employment_mid_march, null))  as cbp_employment_{{ alias }}
    {%- endfor %}
    from {{ ref('fct_market_business_patterns') }}
    group by market_id
),

oews as (
    select
        market_id
    {%- for code, alias in occupations %},
        max(iff(occupation_code = '{{ code }}', annual_median_wage_usd, null))        as oews_annual_median_wage_{{ alias }},
        max(iff(occupation_code = '{{ code }}', annual_median_wage_usd_marker, null)) as oews_annual_median_wage_{{ alias }}_marker,
        max(iff(occupation_code = '{{ code }}', total_employment, null))              as oews_employment_{{ alias }},
        count_if(occupation_code = '{{ code }}') > 0                                  as oews_{{ alias }}_published
    {%- endfor %}
    from {{ ref('fct_market_occupation_wages') }}
    group by market_id
)

select
    d.market_id,
    d.cbsa_name,
    d.population_2025,
    d.land_area_sq_mi,
    d.water_area_sq_mi,
    d.county_count,
    d.state_count,
    d.is_multi_state,
    acs.acs_period,
    acs.total_population                    as acs_total_population,
    acs.total_population_moe                as acs_total_population_moe,
    acs.total_households,                   acs.total_households_moe,
    acs.median_household_income_usd,        acs.median_household_income_usd_moe,
    acs.workers_16_plus,                    acs.workers_16_plus_moe,
    acs.workers_drove_alone,                acs.workers_drove_alone_moe,
    acs.workers_public_transportation,      acs.workers_public_transportation_moe,
    acs.workers_taxi_or_ride_hailing,       acs.workers_taxi_or_ride_hailing_moe,
    acs.workers_bicycle,                    acs.workers_bicycle_moe,
    acs.workers_walked,                     acs.workers_walked_moe,
    acs.workers_worked_from_home,           acs.workers_worked_from_home_moe,
    acs.mean_travel_time_minutes,           acs.mean_travel_time_minutes_moe,
    acs.households_vehicle_universe,        acs.households_vehicle_universe_moe,
    acs.households_no_vehicle,              acs.households_no_vehicle_moe,
    acs.aggregate_vehicles_available,       acs.aggregate_vehicles_available_moe,
    acs.housing_units_total,                acs.housing_units_total_moe,
    acs.housing_units_1_detached,           acs.housing_units_1_detached_moe,
    acs.occupied_housing_units,             acs.occupied_housing_units_moe,
    acs.owner_occupied_units,               acs.owner_occupied_units_moe
{%- for code, alias in naics %},
    cbp.cbp_establishments_{{ alias }},
    cbp.cbp_employment_{{ alias }}
{%- endfor %}
{%- for code, alias in occupations %},
    oews.oews_annual_median_wage_{{ alias }},
    oews.oews_annual_median_wage_{{ alias }}_marker,
    oews.oews_employment_{{ alias }},
    oews.oews_{{ alias }}_published
{%- endfor %},
    d.pep_vintage,
    'ACS5-2024'                         as acs_vintage,
    '2023'                              as cbp_vintage,
    'May2025'                           as oews_vintage,
    '2024'                              as gazetteer_vintage
from {{ ref('dim_market') }} d
left join acs  on acs.market_id  = d.market_id
left join cbp  on cbp.market_id  = d.market_id
left join oews on oews.market_id = d.market_id
