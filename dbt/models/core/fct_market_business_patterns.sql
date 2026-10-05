-- FCT_MARKET_BUSINESS_PATTERNS: County Business Patterns 2023 for the 35 markets.
-- Grain: one row per market x NAICS code, every published NAICS level ('------' = all sectors).
-- Units: establishments (count), mid-March employment (persons), payroll ($1,000).
-- Transformation: market-universe restriction only, with noise-infusion flags kept.
-- Limitation: establishments are not delivery demand (A-019). CBP excludes the self-employed
-- and most government.
select
    c.cbsa_code                     as market_id,
    c.naics_code,
    c.naics_code_trimmed,
    c.is_all_sectors,
    c.establishments,
    c.employment_mid_march,
    c.employment_noise_flag,
    c.payroll_annual_thousands_usd,
    c.payroll_annual_noise_flag,
    c.payroll_q1_thousands_usd,
    c.payroll_q1_noise_flag,
    c.establishments_lt_5_employees,
    c.establishments_5_9_employees,
    c.establishments_10_19_employees,
    c.establishments_20_49_employees,
    c.establishments_50_99_employees,
    c.establishments_100_249_employees,
    c.establishments_250_499_employees,
    c.establishments_500_999_employees,
    c.establishments_1000_plus_employees,
    c.cbp_year,
    c.source_vintage                as cbp_vintage
from {{ ref('stg_census__cbp_2023_msa') }} c
inner join {{ ref('dim_market') }} d
    on d.market_id = c.cbsa_code
