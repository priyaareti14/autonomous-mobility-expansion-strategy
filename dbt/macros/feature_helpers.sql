{#
  Phase 6 feature-layer helpers.
#}

{# A SQL IN-list of string literals from a dbt list var, e.g. ('S', 'R') #}
{% macro in_list(values) -%}
    ({%- for v in values -%}'{{ v }}'{%- if not loop.last %}, {% endif -%}{%- endfor -%})
{%- endmacro %}
