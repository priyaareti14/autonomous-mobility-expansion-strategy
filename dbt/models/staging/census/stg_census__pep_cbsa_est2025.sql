-- S-01 Census PEP Vintage 2025 population totals.
-- Grain: one row per geography row as published (CBSA, Metropolitan Division,
-- or county within a CBSA). geography_type distinguishes them. No filtering
-- here: the market universe is selected in intermediate.
select
    {{ clean_text('"CBSA"') }}                 as cbsa_code,
    {{ clean_text('"MDIV"') }}                 as metro_division_code,
    {{ clean_text('"STCOU"') }}                as county_fips,
    {{ clean_text('"NAME"') }}                 as geography_name,
    {{ clean_text('"LSAD"') }}                 as geography_type,
    {{ to_integer('"ESTIMATESBASE2020"') }}    as estimates_base_2020,
    {{ to_integer('"POPESTIMATE2020"') }}      as population_estimate_2020,
    {{ to_integer('"POPESTIMATE2021"') }}      as population_estimate_2021,
    {{ to_integer('"POPESTIMATE2022"') }}      as population_estimate_2022,
    {{ to_integer('"POPESTIMATE2023"') }}      as population_estimate_2023,
    {{ to_integer('"POPESTIMATE2024"') }}      as population_estimate_2024,
    {{ to_integer('"POPESTIMATE2025"') }}      as population_estimate_2025,
    {{ lineage_columns() }}
from {{ source('raw', 'CENSUS_PEP_CBSA_EST2025') }}
