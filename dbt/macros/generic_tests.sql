{#
  Project generic tests. Each one protects a data contract named in the
  model YAML. dbt_utils would provide similar tests; these few are written
  here to avoid adding a package dependency for five short macros.
#}

{# Composite natural key is unique: the documented grain #}
{% test unique_combination_of_columns(model, combination_of_columns) %}
select {{ combination_of_columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ combination_of_columns | join(', ') }}
having count(*) > 1
{% endtest %}

{# Value within an inclusive range; nulls are allowed (missingness is tested separately) #}
{% test values_between(model, column_name, min_value, max_value) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} is not null
  and ({{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }})
{% endtest %}

{# Identifier shape, e.g. a 5-digit CBSA code; nulls allowed #}
{% test matches_regex(model, column_name, pattern) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} is not null
  and not regexp_like({{ column_name }}, '{{ pattern }}')
{% endtest %}

{# Exact row count, e.g. the frozen 35-market universe #}
{% test row_count_equals(model, expected) %}
select count(*) as actual_rows
from {{ model }}
having count(*) <> {{ expected }}
{% endtest %}

{# Same row count as another relation: no silent row loss across layers #}
{% test equal_row_count(model, compare_model) %}
with a as (select count(*) as n from {{ model }}),
     b as (select count(*) as n from {{ compare_model }})
select a.n as model_rows, b.n as compare_rows
from a cross join b
where a.n <> b.n
{% endtest %}
