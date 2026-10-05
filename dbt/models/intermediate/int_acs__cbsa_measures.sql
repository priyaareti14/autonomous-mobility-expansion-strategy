-- The catalogued ACS 5-year 2020-2024 CBSA measures, one row per CBSA.
-- All 12 inputs are tables of the SAME ACS dataset and geography, joined on the CBSA code: a
-- one-to-one join, with no aggregation or derivation.
-- Grain: one row per CBSA (935 metro + micro).
{% set tables = [
    'stg_census__acs5_2024_cbsa_b11001', 'stg_census__acs5_2024_cbsa_b19013',
    'stg_census__acs5_2024_cbsa_b08301', 'stg_census__acs5_2024_cbsa_b08201',
    'stg_census__acs5_2024_cbsa_b25044', 'stg_census__acs5_2024_cbsa_b25046',
    'stg_census__acs5_2024_cbsa_b08013', 'stg_census__acs5_2024_cbsa_b08303',
    'stg_census__acs5_2024_cbsa_b25024', 'stg_census__acs5_2024_cbsa_b25003',
    'stg_census__acs5_2024_cbsa_s0801_subset'
] %}
{% set skip = ['cbsa_code', 'acs_geo_id', 'acs_geography_name', 'acs_period', 'ingest_run_id', 'ingested_at',
               'source_id', 'source_vintage', 'source_file', 'source_file_sha256', 'source_row_number'] %}
select
    b01003.cbsa_code,
    b01003.acs_geography_name,
    b01003.acs_period,
    b01003.total_population, b01003.total_population_moe,
    b01003.total_population_is_special_code, b01003.total_population_moe_is_special_code
{%- for t in tables %}
  {%- set alias = 't' ~ loop.index %}
  {%- for col in adapter.get_columns_in_relation(ref(t)) %}
    {%- if col.name | lower not in skip %},
    {{ alias }}.{{ col.name | lower }}
    {%- endif %}
  {%- endfor %}
{%- endfor %}
from {{ ref('stg_census__acs5_2024_cbsa_b01003') }} b01003
{%- for t in tables %}
inner join {{ ref(t) }} t{{ loop.index }}
    on t{{ loop.index }}.cbsa_code = b01003.cbsa_code
{%- endfor %}
