-- NW1 POPULATION-WEIGHTED WALKABILITY (approved Phase 5 method).
-- Grain: one row per market (35).
-- Formula: sum(NatWalkInd_b x TotPop_b) / sum(TotPop_b) over the market's EPA SLD v3.0 block groups
-- with a published National Walkability Index (1-20, relative national rank) and population > 0.
-- Geography: block group -> county FIPS -> CBSA under the July 2023 delineation (Phase 4 bridge,
-- int_geo__block_group_cbsa_2023). EPA's own pre-2023 CBSA field is never used (A-006);
-- block_groups_sld_cbsa_differs counts where it would have disagreed.
-- A-031 (kept visible): block groups without transit data (D4A = -99999) receive EPA's lowest transit
-- rank inside the index. transit_missing_population_share is the share of residents affected.
with bg as (
    select * from {{ ref('fct_block_group_built_environment') }}
),

used as (
    select * from bg
    where national_walkability_index is not null and total_population_sld > 0
)

select
    d.market_id,
    u.population_weighted_walkability,
    u.population_covered,
    t.population_total_sld,
    u.population_covered / nullif(t.population_total_sld, 0)        as population_coverage_pct,
    t.block_groups_total,
    u.block_groups_used,
    t.block_groups_zero_population,
    t.block_groups_missing_index,
    t.block_groups_missing_index_with_population,
    u.transit_missing_population / nullif(u.population_covered, 0)  as transit_missing_population_share,
    t.block_groups_sld_cbsa_differs,
    'county FIPS -> July 2023 delineation (int_geo__block_group_cbsa_2023)' as geography_bridge,
    'EPA SLD v3.0 (2017-2020 inputs, 2018 population)'              as walkability_vintage
from {{ ref('dim_market') }} d
left join (
    select
        market_id,
        sum(national_walkability_index * total_population_sld) / sum(total_population_sld) as population_weighted_walkability,
        sum(total_population_sld)                                    as population_covered,
        count(*)                                                     as block_groups_used,
        sum(iff(d4a_no_transit_data, total_population_sld, 0))      as transit_missing_population
    from used
    group by market_id
) u on u.market_id = d.market_id
left join (
    select
        market_id,
        count(*)                                                     as block_groups_total,
        sum(total_population_sld)                                    as population_total_sld,
        count_if(coalesce(total_population_sld, 0) <= 0)             as block_groups_zero_population,
        count_if(national_walkability_index is null)                 as block_groups_missing_index,
        count_if(national_walkability_index is null and total_population_sld > 0) as block_groups_missing_index_with_population,
        count_if(cbsa_code_differs_from_sld)                         as block_groups_sld_cbsa_differs
    from bg
    group by market_id
) t on t.market_id = d.market_id
