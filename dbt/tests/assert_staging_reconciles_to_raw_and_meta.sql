-- CROSS-LAYER RECONCILIATION: for every RAW table, rows in STAGING = rows in RAW = raw_row_count
-- recorded by the latest SUCCEEDED ingestion run in META. Staging is 1:1 with RAW (no filtering),
-- so any difference is silent row loss or duplication.
{% set pairs = [
    ('CENSUS_PEP_CBSA_EST2025', 'stg_census__pep_cbsa_est2025'),
    ('CENSUS_CBSA_DELINEATION_2023', 'stg_census__cbsa_delineation_2023'),
    ('CENSUS_ACS5_2024_CBSA_B01003', 'stg_census__acs5_2024_cbsa_b01003'),
    ('CENSUS_ACS5_2024_CBSA_B11001', 'stg_census__acs5_2024_cbsa_b11001'),
    ('CENSUS_ACS5_2024_CBSA_B19013', 'stg_census__acs5_2024_cbsa_b19013'),
    ('CENSUS_ACS5_2024_CBSA_B08301', 'stg_census__acs5_2024_cbsa_b08301'),
    ('CENSUS_ACS5_2024_CBSA_B08201', 'stg_census__acs5_2024_cbsa_b08201'),
    ('CENSUS_ACS5_2024_CBSA_B25044', 'stg_census__acs5_2024_cbsa_b25044'),
    ('CENSUS_ACS5_2024_CBSA_B25046', 'stg_census__acs5_2024_cbsa_b25046'),
    ('CENSUS_ACS5_2024_CBSA_B08013', 'stg_census__acs5_2024_cbsa_b08013'),
    ('CENSUS_ACS5_2024_CBSA_B08303', 'stg_census__acs5_2024_cbsa_b08303'),
    ('CENSUS_ACS5_2024_CBSA_B25024', 'stg_census__acs5_2024_cbsa_b25024'),
    ('CENSUS_ACS5_2024_CBSA_B25003', 'stg_census__acs5_2024_cbsa_b25003'),
    ('CENSUS_ACS5_2024_CBSA_S0801_SUBSET', 'stg_census__acs5_2024_cbsa_s0801_subset'),
    ('CENSUS_ACS5_2024_TRACT_B01003', 'stg_census__acs5_2024_tract_b01003'),
    ('CENSUS_GAZETTEER_2024_CBSA', 'stg_census__gazetteer_2024_cbsa'),
    ('CENSUS_GAZETTEER_2024_COUNTIES', 'stg_census__gazetteer_2024_counties'),
    ('CENSUS_GAZETTEER_2024_TRACTS', 'stg_census__gazetteer_2024_tracts'),
    ('CENSUS_CBP_2023_MSA', 'stg_census__cbp_2023_msa'),
    ('BLS_OEWS_MAY2025_MSA', 'stg_bls__oews_may2025_msa'),
    ('NOAA_NORMALS_1991_2020_ANNUALSEASONAL', 'stg_noaa__normals_annualseasonal'),
    ('NOAA_NORMALS_1991_2020_HOURLY_WIND', 'stg_noaa__normals_hourly_wind'),
    ('FAA_ENPLANEMENTS_CY2025_COMMERCIAL_SERVICE', 'stg_faa__enplanements_cy2025'),
    ('FAA_NASR_APT_BASE_20260903', 'stg_faa__nasr_apt_base'),
    ('EPA_SLD_V3_BLOCK_GROUP', 'stg_epa__sld_v3_block_group')
] %}
with meta as (
    select snowflake_table, raw_row_count
    from {{ source('meta', 'INGESTION_RUNS') }}
    where status = 'SUCCEEDED'
    qualify row_number() over (partition by snowflake_table order by completed_at desc) = 1
),
counts as (
{%- for raw_table, stg in pairs %}
    select '{{ raw_table }}' as raw_table,
           (select count(*) from {{ source('raw', raw_table) }}) as raw_rows,
           (select count(*) from {{ ref(stg) }})                as staging_rows
    {% if not loop.last %}union all{% endif %}
{%- endfor %}
)
select c.raw_table, c.raw_rows, c.staging_rows, m.raw_row_count as meta_raw_rows
from counts c
left join meta m on m.snowflake_table = 'RAW.' || c.raw_table
where c.staging_rows <> c.raw_rows
   or m.raw_row_count is null
   or m.raw_row_count <> c.raw_rows
