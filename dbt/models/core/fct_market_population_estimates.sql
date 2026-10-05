-- FCT_MARKET_POPULATION_ESTIMATES: PEP Vintage 2025 annual resident population estimates.
-- Grain: one row per market x estimate year (2020-2025, July 1). 35 x 6 = 210 rows.
-- Unit: persons. Transformation: PEP's wide year columns become rows (unpivot); values unchanged.
-- No date dimension is needed: the year is an integer attribute of the fact.
with metros as (
    select
        p.cbsa_code                 as market_id,
        p.source_vintage            as pep_vintage,
        p.population_estimate_2020  as y2020,
        p.population_estimate_2021  as y2021,
        p.population_estimate_2022  as y2022,
        p.population_estimate_2023  as y2023,
        p.population_estimate_2024  as y2024,
        p.population_estimate_2025  as y2025
    from {{ ref('stg_census__pep_cbsa_est2025') }} p
    inner join {{ ref('dim_market') }} d
        on d.market_id = p.cbsa_code
    where p.geography_type = 'Metropolitan Statistical Area'
)

select
    market_id,
    try_to_number(substr(year_col, 2)) as estimate_year,
    population_estimate,
    pep_vintage
from metros
    unpivot (population_estimate for year_col in (y2020, y2021, y2022, y2023, y2024, y2025))
