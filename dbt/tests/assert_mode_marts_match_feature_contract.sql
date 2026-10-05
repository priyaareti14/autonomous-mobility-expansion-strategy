-- CONTRACT: each mode mart holds EXACTLY its ACTIVE features from DIM_FEATURE, plus the keys
-- (market_id, market_name) and qa_* fields. Fails if an active feature is missing from its mart, or
-- if a mart carries any other column (an unapproved feature, a score, a weight or a rank).
-- The marts are read through information_schema, so their build order is declared explicitly:
-- depends_on: {{ ref('mart_robotaxi_features') }}
-- depends_on: {{ ref('mart_sidewalk_delivery_features') }}
-- depends_on: {{ ref('mart_drone_delivery_features') }}
{% set marts = [
    ('ROBOTAXI', 'mart_robotaxi_features'),
    ('SIDEWALK_DELIVERY', 'mart_sidewalk_delivery_features'),
    ('DRONE_DELIVERY', 'mart_drone_delivery_features')
] %}
with mart_columns as (
{%- for mode, model in marts %}
    select '{{ mode }}' as mode, lower(column_name) as column_name
    from {{ target.database }}.information_schema.columns
    where table_schema = 'ANALYTICS' and table_name = upper('{{ model }}')
    {% if not loop.last %}union all{% endif %}
{%- endfor %}
),

active as (
    select mode, lower(feature_name) as column_name
    from {{ ref('dim_feature') }}
    where production_status = 'ACTIVE'
)

select 'active feature missing from mart' as issue, a.mode, a.column_name
from active a
left join mart_columns m on m.mode = a.mode and m.column_name = a.column_name
where m.column_name is null

union all

select 'mart column is not an active contract feature', m.mode, m.column_name
from mart_columns m
left join active a on a.mode = m.mode and a.column_name = m.column_name
where a.column_name is null
  and m.column_name not in ('market_id', 'market_name')
  and not startswith(m.column_name, 'qa_')
-- A missing mart fails the first check: every mode has active features.
