-- D2 POPULATION-WEIGHTED TRACT DENSITY (approved Phase 5 method, A-008).
-- Grain: one row per market (35).
--
-- Formula, over tracts i in the market with an ACS population and land area > 0:
--     tract density d_i = p_i / a_i                (persons per sq mi)
--     D2 = sum(p_i * d_i) / sum(p_i)               (density experienced by the average resident)
--   p_i: ACS 2020-2024 5-year tract population (B01003_001E, S-04)
--   a_i: Gazetteer 2024 tract land area, sq mi (ALAND_SQMI, S-05)
--   tract -> market: official tract -> county -> CBSA crosswalk (July 2023 delineation)
-- Zero-land-area tracts (water-only) are excluded: their density is undefined. They hold no ACS
-- population in the 35 markets (tested).
-- Missing population: the 14 Suffolk County, NY tracts without ACS 2020-2024 records (A-029) are
-- excluded and NOT imputed. Phase 5 estimated their effect on New York's D2 at -0.31% (32,301 without
-- them vs 32,203 with their ACS 2018-2022 populations, sensitivity only).
--
-- Diagnostics only (never independent scoring signals):
--   raw_msa_density_diagnostic: PEP 2025 population / CBSA land area (D1, rejected in Phase 5)
--   pw_block_group_density_sld2018_diagnostic: the same formula on EPA SLD block groups (D3, 2018 inputs)
with tracts as (
    select * from {{ ref('fct_tract_population_land') }}
),

tract_summary as (
    select
        market_id,
        count(*)                                                        as tract_count,
        count_if(has_acs_population)                                    as tracts_with_population,
        count_if(not has_acs_population)                                as tracts_missing_population,
        count_if(is_zero_land_area)                                     as tracts_zero_land_area,
        count_if(is_zero_land_area and coalesce(total_population, 0) > 0) as zero_land_tracts_with_population,
        count_if(has_acs_population and not is_zero_land_area)          as tracts_used,
        sum(iff(has_acs_population, total_population, 0))               as tract_population_total,
        sum(iff(has_acs_population and not is_zero_land_area, total_population, 0)) as population_used,
        sum(iff(has_acs_population and not is_zero_land_area,
                total_population * (total_population / land_area_sq_mi), 0))       as population_x_density,
        sum(iff(not has_acs_population, land_area_sq_mi, 0))            as land_sq_mi_missing_population
    from tracts
    group by market_id
),

block_groups as (
    select
        market_id,
        sum(total_population_sld * (total_population_sld / (land_acres / 640.0)))
            / nullif(sum(total_population_sld), 0)                      as pw_block_group_density_sld2018_diagnostic
    from {{ ref('fct_block_group_built_environment') }}
    where land_acres > 0 and total_population_sld > 0
    group by market_id
)

select
    d.market_id,
    t.population_x_density / nullif(t.population_used, 0)              as population_weighted_tract_density,
    t.tract_count,
    t.tracts_with_population,
    t.tracts_missing_population,
    t.tracts_zero_land_area,
    t.zero_land_tracts_with_population,
    t.tracts_used,
    t.population_used,
    a.total_population                                                  as acs_cbsa_total_population,
    t.population_used / a.total_population                              as population_coverage_pct,
    t.land_sq_mi_missing_population,
    t.tracts_missing_population > 0                                     as known_gap_flag,
    iff(t.tracts_missing_population > 0,
        'A-029: ' || t.tracts_missing_population || ' Suffolk County NY tracts have no ACS 2020-2024 '
        || 'record; excluded, not imputed (Phase 5 estimated impact on D2: -0.31%)', null) as known_gap_note,
    d.population_2025 / d.land_area_sq_mi                               as raw_msa_density_diagnostic,
    b.pw_block_group_density_sld2018_diagnostic,
    'ACS5-2024 tracts / Gazetteer 2024'                                 as density_vintage
from {{ ref('dim_market') }} d
left join tract_summary t on t.market_id = d.market_id
left join block_groups b on b.market_id = d.market_id
left join {{ ref('fct_market_acs_demographics') }} a on a.market_id = d.market_id
