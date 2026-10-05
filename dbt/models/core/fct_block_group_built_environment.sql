-- FCT_BLOCK_GROUP_BUILT_ENVIRONMENT: EPA SLD v3.0 built-environment measures (with the National
-- Walkability Index) for block groups in the 35 markets.
-- Grain: one row per SLD block group (2010-based) whose county lies in a frozen market under the
-- July 2023 delineation.
-- Units as published by EPA: densities per acre, D4A in metres, NatWalkInd on a 1-20 relative scale.
-- No market-level aggregation is done here: population-weighting choices belong to Phase 5/6.
-- Limitations: 2017-2020 inputs and 2018 population weights (A-013). D4A 'no transit data' is flagged.
select
    b.block_group_geoid10,
    x.cbsa_code                              as market_id,
    b.county_fips,
    b.state_fips,
    b.cbsa_code_sld_pre2023,
    x.cbsa_code_differs_from_sld,
    b.total_population_sld,
    b.housing_units_sld,
    b.households_sld,
    b.total_employment_sld,
    b.total_acres,
    b.land_acres,
    b.unprotected_land_acres,
    b.d1b_gross_population_density,
    b.d1c_gross_employment_density,
    b.d2a_employment_household_entropy,
    b.d2b_employment_entropy_8_tier,
    b.d3b_street_intersection_density,
    b.d4a_distance_to_transit_m,
    b.d4a_no_transit_data,
    b.d2a_ranked,
    b.d2b_ranked,
    b.d3b_ranked,
    b.d4a_ranked,
    b.national_walkability_index,
    b.pct_zero_car_households_sld,
    b.sld_version
from {{ ref('stg_epa__sld_v3_block_group') }} b
inner join {{ ref('int_geo__block_group_cbsa_2023') }} x
    on x.block_group_geoid10 = b.block_group_geoid10
inner join {{ ref('dim_market') }} d
    on d.market_id = x.cbsa_code
