{#
  Use the configured custom schema EXACTLY (STAGING, INTERMEDIATE, CORE,
  ANALYTICS) instead of dbt's default "<target_schema>_<custom_schema>"
  concatenation.

  Why: the six schemas are created and owned by AM_ADMIN (Phase 2), and the
  dbt role AM_TRANSFORMER deliberately lacks CREATE SCHEMA. dbt's default
  behavior would try to create STAGING_CORE and similar schemas, which would
  fail, and should.
  Models with no custom schema fall back to the target schema (STAGING).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema | trim | upper }}
    {%- else -%}
        {{ custom_schema_name | trim | upper }}
    {%- endif -%}
{%- endmacro %}
