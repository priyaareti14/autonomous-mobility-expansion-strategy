-- S-08 County Business Patterns 2023, metropolitan-area file.
-- Grain: one row per CBSA x NAICS code (all NAICS levels, as published).
-- NAICS codes are published padded ('------' = all sectors, '44----' = sector 44-45,
-- '722///' = 3-digit 722). naics_code keeps the published form;
-- naics_code_trimmed removes the padding characters.
-- Payroll is published in $1,000. Noise flags (G < 2%, H 2-5%, J >= 5%) are kept.
select
    {{ clean_text('"MSA"') }}                                          as cbsa_code,
    {{ clean_text('"NAICS"') }}                                        as naics_code,
    nullif(replace(replace({{ clean_text('"NAICS"') }}, '-', ''), '/', ''), '') as naics_code_trimmed,
    {{ clean_text('"NAICS"') }} = '------'                             as is_all_sectors,
    {{ to_integer('"EST"') }}                                          as establishments,
    {{ to_integer('"EMP"') }}                                          as employment_mid_march,
    {{ clean_text('"EMP_NF"') }}                                       as employment_noise_flag,
    {{ to_integer('"QP1"') }}                                          as payroll_q1_thousands_usd,
    {{ clean_text('"QP1_NF"') }}                                       as payroll_q1_noise_flag,
    {{ to_integer('"AP"') }}                                           as payroll_annual_thousands_usd,
    {{ clean_text('"AP_NF"') }}                                        as payroll_annual_noise_flag,
    {{ to_integer('"N_5"') }}                                          as establishments_lt_5_employees,
    {{ to_integer('"N5_9"') }}                                         as establishments_5_9_employees,
    {{ to_integer('"N10_19"') }}                                       as establishments_10_19_employees,
    {{ to_integer('"N20_49"') }}                                       as establishments_20_49_employees,
    {{ to_integer('"N50_99"') }}                                       as establishments_50_99_employees,
    {{ to_integer('"N100_249"') }}                                     as establishments_100_249_employees,
    {{ to_integer('"N250_499"') }}                                     as establishments_250_499_employees,
    {{ to_integer('"N500_999"') }}                                     as establishments_500_999_employees,
    {{ to_integer('"N1000"') }}                                        as establishments_1000_plus_employees,
    '2023'                                                             as cbp_year,
    {{ lineage_columns() }}
from {{ source('raw', 'CENSUS_CBP_2023_MSA') }}
