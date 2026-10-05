-- DIM_MARKET: the frozen project market universe (project_scope.md section 5-6).
-- Grain: one row per market. Exactly 35 rows; market_id = 5-digit CBSA code (July 2023 delineation).
-- Derived from the pinned PEP Vintage 2025 ranking (int_market__universe_ranked). A singular test
-- proves it is identical to the approved seed frozen_market_universe (code, name, population, rank).
-- Only descriptive attributes are held here. principal_state_usps comes from the CBSA title (the
-- first state listed); it describes the market and is NOT a regulatory mapping (A-012 open).
with markets as (
    select * from {{ ref('int_market__universe_ranked') }}
),

county_summary as (
    select
        market_id,
        count(*)                                        as county_count,
        count_if(central_outlying = 'Central')          as central_county_count,
        count(distinct state_usps)                      as state_count,
        listagg(distinct state_usps, ',') within group (order by state_usps) as states_by_county_membership
    from {{ ref('int_market__counties') }}
    group by market_id
),

geo as (
    select cbsa_code, csa_code, land_area_sq_mi, water_area_sq_mi,
           internal_point_latitude, internal_point_longitude
    from {{ ref('stg_census__gazetteer_2024_cbsa') }}
)

select
    m.market_id,
    m.cbsa_name,
    m.market_rank_2025,
    m.population_2025,
    m.estimates_base_2020,
    trim(split_part(split_part(m.cbsa_name, ', ', -1), '-', 1)) as principal_state_usps,
    trim(split_part(m.cbsa_name, ', ', -1))                     as states_in_title,
    c.states_by_county_membership,
    c.state_count,
    c.state_count > 1                                           as is_multi_state,
    c.county_count,
    c.central_county_count,
    g.csa_code,
    g.land_area_sq_mi,
    g.water_area_sq_mi,
    g.internal_point_latitude,
    g.internal_point_longitude,
    true                                                        as is_frozen_market_universe,
    m.pep_vintage,
    m.pep_file_sha256,
    'OMB Bulletin 23-01 (July 2023)'                            as delineation_vintage
from markets m
left join county_summary c on c.market_id = m.market_id
left join geo g on g.cbsa_code = m.market_id
