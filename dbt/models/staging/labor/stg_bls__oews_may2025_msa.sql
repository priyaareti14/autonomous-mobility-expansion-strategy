-- S-09 BLS OEWS May 2025, metropolitan areas (cross-industry, all ownerships).
-- Grain: one row per metro area x SOC occupation.
-- BLS markers are preserved in *_marker columns; the numeric column is null when a marker is published:
--   '*'  wage estimate not available     '**' employment estimate not available
--   '#'  wage at or above the top-coded value
-- A null wage is therefore NOT a low wage (A-026).
{% set numeric_cols = [
    ('TOT_EMP', 'total_employment'), ('EMP_PRSE', 'employment_prse'),
    ('JOBS_1000', 'jobs_per_1000'), ('LOC_QUOTIENT', 'location_quotient'),
    ('H_MEAN', 'hourly_mean_wage_usd'), ('A_MEAN', 'annual_mean_wage_usd'), ('MEAN_PRSE', 'mean_wage_prse'),
    ('H_PCT10', 'hourly_wage_p10_usd'), ('H_PCT25', 'hourly_wage_p25_usd'), ('H_MEDIAN', 'hourly_median_wage_usd'),
    ('H_PCT75', 'hourly_wage_p75_usd'), ('H_PCT90', 'hourly_wage_p90_usd'),
    ('A_PCT10', 'annual_wage_p10_usd'), ('A_PCT25', 'annual_wage_p25_usd'), ('A_MEDIAN', 'annual_median_wage_usd'),
    ('A_PCT75', 'annual_wage_p75_usd'), ('A_PCT90', 'annual_wage_p90_usd')
] %}
select
    {{ clean_text('"AREA"') }}           as cbsa_code,
    {{ clean_text('"AREA_TITLE"') }}     as area_title,
    {{ clean_text('"AREA_TYPE"') }}      as area_type_code,
    {{ clean_text('"PRIM_STATE"') }}     as primary_state_usps,
    {{ clean_text('"NAICS"') }}          as naics_code,
    {{ clean_text('"I_GROUP"') }}        as industry_group,
    {{ clean_text('"OWN_CODE"') }}       as ownership_code,
    {{ clean_text('"OCC_CODE"') }}       as occupation_code,
    {{ clean_text('"OCC_TITLE"') }}      as occupation_title,
    {{ clean_text('"O_GROUP"') }}        as occupation_group,
{%- for src, alias in numeric_cols %}
    {{ to_number('"' ~ src ~ '"') }}     as {{ alias }},
    iff(trim("{{ src }}") in ('*', '**', '#'), trim("{{ src }}"), null) as {{ alias }}_marker,
{%- endfor %}
    upper(trim("ANNUAL")) = 'TRUE'       as is_annual_only,
    upper(trim("HOURLY")) = 'TRUE'       as is_hourly_only,
    'May2025'                            as oews_reference_period,
    {{ lineage_columns() }}
from {{ source('raw', 'BLS_OEWS_MAY2025_MSA') }}
