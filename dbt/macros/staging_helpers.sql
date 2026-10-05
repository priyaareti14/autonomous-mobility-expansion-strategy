{# Phase 3 lineage metadata, carried unchanged into every staging model #}
{% macro lineage_columns() -%}
    "_INGEST_RUN_ID"          as ingest_run_id,
    "_INGESTED_AT"            as ingested_at,
    "_SOURCE_ID"              as source_id,
    "_SOURCE_VINTAGE"         as source_vintage,
    "_SOURCE_FILE"            as source_file,
    "_SOURCE_FILE_SHA256"     as source_file_sha256,
    "_SOURCE_ROW_NUMBER"      as source_row_number
{%- endmacro %}

{#
  ACS CBSA-level staging select. `variables` is a list of
  (acs_variable_without_suffix, column_alias) pairs. Only the variables
  catalogued in docs/data_sources.md are exposed; every one keeps its margin
  of error, and a flag records whether the MOE was a Census special code.
#}
{% macro acs_cbsa_staging(source_table, variables) -%}
select
    {{ clean_text('"METROPOLITAN_STATISTICAL_AREA_MICROPOLITAN_STATISTICAL_AREA"') }} as cbsa_code,
    {{ clean_text('"GEO_ID"') }}  as acs_geo_id,
    {{ clean_text('"NAME"') }}    as acs_geography_name,
{%- for var, alias in variables %}
    {{ acs_value('"' ~ var ~ 'E"') }}                    as {{ alias }},
    {{ acs_value('"' ~ var ~ 'M"') }}                    as {{ alias }}_moe,
    {{ acs_is_special_code('"' ~ var ~ 'E"') }}          as {{ alias }}_is_special_code,
    {{ acs_is_special_code('"' ~ var ~ 'M"') }}          as {{ alias }}_moe_is_special_code,
{%- endfor %}
    'ACS5-2024'                                          as acs_period,
    {{ lineage_columns() }}
from {{ source('raw', source_table) }}
{%- endmacro %}
