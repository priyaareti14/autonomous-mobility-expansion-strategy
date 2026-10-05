-- DATA CONTRACT (A-029): every market tract in the Gazetteer is kept in FCT_TRACT_POPULATION_LAND,
-- and the ONLY tracts without an ACS 2020-2024 population are the 14 known Suffolk County, NY
-- (36103) tracts. Any new coverage gap fails, so a source change cannot slip into the density
-- inputs unnoticed.
with market_tracts as (
    select x.tract_geoid
    from {{ ref('int_geo__tract_cbsa_2023') }} x
    inner join {{ ref('dim_market') }} d on d.market_id = x.cbsa_code
),
missing_from_fact as (
    select 'market tract missing from fact' as issue, m.tract_geoid
    from market_tracts m
    left join {{ ref('fct_tract_population_land') }} f on f.tract_geoid = m.tract_geoid
    where f.tract_geoid is null
),
unexpected_acs_gaps as (
    select 'tract without ACS outside known anomaly' as issue, tract_geoid
    from {{ ref('fct_tract_population_land') }}
    where not has_acs_population and county_fips <> '36103'
),
known_gap_count as (
    select 'known Suffolk gap count changed' as issue, count(*)::varchar as tract_geoid
    from {{ ref('fct_tract_population_land') }}
    where not has_acs_population
    having count(*) <> 14
)
select * from missing_from_fact
union all select * from unexpected_acs_gaps
union all select * from known_gap_count
