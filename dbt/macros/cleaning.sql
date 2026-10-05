{#
  Source-level cleanup helpers used by the staging models. They do technical
  typing only (no business logic): trim, blank -> null, and documented source
  sentinels -> null. Every sentinel that is nulled is also exposed as a flag
  column in staging, so the information is never silently lost.
#}

{# Text: trim; blank -> null #}
{% macro clean_text(col) -%}
    nullif(trim({{ col }}), '')
{%- endmacro %}

{# Number: trim; non-numeric (including published markers) -> null #}
{% macro to_number(col) -%}
    try_to_double(nullif(trim({{ col }}), ''))
{%- endmacro %}

{% macro to_integer(col) -%}
    try_to_number(nullif(trim({{ col }}), ''), 38, 0)
{%- endmacro %}

{#
  ACS estimate or margin of error. Census publishes negative special codes,
  e.g. -555555555 (estimate controlled, so no MOE is published) and
  -666666666 (estimate not available). Every negative code -> null. Real ACS
  values used here (counts, dollars, minutes) cannot be negative.
#}
{% macro acs_value(col) -%}
    iff(try_to_double(nullif(trim({{ col }}), '')) < 0, null,
        try_to_double(nullif(trim({{ col }}), '')))
{%- endmacro %}

{% macro acs_is_special_code(col) -%}
    coalesce(try_to_double(nullif(trim({{ col }}), '')) < 0, false)
{%- endmacro %}

{#
  NOAA normals sentinels:
    -9999  missing (no normal computed)
    -7777  trace: a non-zero value that would round to zero
  Both become null in the numeric column. Separate flags (noaa_is_missing,
  noaa_is_trace) keep the distinction, so a later phase can decide how to
  treat trace values (e.g. as ~0). Staging does not make that choice.
#}
{% macro noaa_value(col) -%}
    iff(try_to_double(nullif(trim({{ col }}), '')) in (-9999, -7777), null,
        try_to_double(nullif(trim({{ col }}), '')))
{%- endmacro %}

{% macro noaa_is_missing(col) -%}
    coalesce(try_to_double(nullif(trim({{ col }}), '')) = -9999, false)
{%- endmacro %}

{% macro noaa_is_trace(col) -%}
    coalesce(try_to_double(nullif(trim({{ col }}), '')) = -7777, false)
{%- endmacro %}
