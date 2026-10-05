-- The approved market-selection rule (project_scope.md section 5), applied to the pinned PEP source:
-- Metropolitan Statistical Areas only, ranked by POPESTIMATE2025 descending, ranks 1-35 kept.
-- Grain: one row per market (expected exactly 35). rank() is used rather than row_number(),
-- so any population tie would surface as a duplicate rank and fail the tests.
with metros as (
    select
        cbsa_code,
        geography_name,
        population_estimate_2025,
        estimates_base_2020,
        source_vintage,
        source_file_sha256
    from {{ ref('stg_census__pep_cbsa_est2025') }}
    where geography_type = 'Metropolitan Statistical Area'
),

ranked as (
    select
        *,
        rank() over (order by population_estimate_2025 desc) as market_rank_2025
    from metros
)

select
    cbsa_code              as market_id,
    geography_name         as cbsa_name,
    market_rank_2025,
    population_estimate_2025 as population_2025,
    estimates_base_2020,
    source_vintage         as pep_vintage,
    source_file_sha256     as pep_file_sha256
from ranked
where market_rank_2025 <= 35
