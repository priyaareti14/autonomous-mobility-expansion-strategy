-- DEPLOYMENT-LEAK GUARD (Phase 6.5): deployment evidence (sources S-35 to S-39 and the curated
-- evidence/deployment_evidence.csv) is EXTERNAL VALIDATION ONLY. It must never appear in the
-- production feature layer:
--   1. no column of the mode marts or DIM_FEATURE names an operator or a deployment concept;
--   2. no DIM_FEATURE row (name, description, source, lineage) cites a deployment source or operator;
--   3. no ANALYTICS relation is a deployment table.
-- Phase 7: check 1 also covers every baseline scoring relation (scores, ranks, decompositions).
-- depends_on: {{ ref('mart_robotaxi_features') }}
-- depends_on: {{ ref('mart_sidewalk_delivery_features') }}
-- depends_on: {{ ref('mart_drone_delivery_features') }}
-- depends_on: {{ ref('fct_regulatory_dimension_scores') }}
-- depends_on: {{ ref('fct_feature_scores') }}
-- depends_on: {{ ref('fct_component_scores') }}
-- depends_on: {{ ref('fct_readiness_baseline') }}
-- depends_on: {{ ref('mart_robotaxi_readiness_baseline') }}
-- depends_on: {{ ref('mart_sidewalk_delivery_readiness_baseline') }}
-- depends_on: {{ ref('mart_drone_delivery_readiness_baseline') }}
{% set terms = ['waymo', 'zoox', 'tesla', 'cruise', 'motional', 'may_mobility', 'avride', 'nuro', 'starship',
                'serve_robotics', 'coco', 'kiwibot', 'cartken', 'wing', 'zipline', 'prime_air', 'droneup',
                'flytrex', 'deploy', 'operator_present', 'commercial_service', 'av_presence', 'service_area',
                'launch'] %}
{% set feature_tables = ['MART_ROBOTAXI_FEATURES', 'MART_SIDEWALK_DELIVERY_FEATURES',
                         'MART_DRONE_DELIVERY_FEATURES', 'DIM_FEATURE',
                         'FCT_REGULATORY_DIMENSION_SCORES', 'FCT_FEATURE_SCORES', 'FCT_COMPONENT_SCORES',
                         'FCT_READINESS_BASELINE', 'MART_ROBOTAXI_READINESS_BASELINE',
                         'MART_SIDEWALK_DELIVERY_READINESS_BASELINE', 'MART_DRONE_DELIVERY_READINESS_BASELINE'] %}
with cols as (
    select table_name, lower(column_name) as column_name
    from {{ target.database }}.information_schema.columns
    where table_schema = 'ANALYTICS' and table_name in ('{{ feature_tables | join("', '") }}')
),

feature_text as (
    select feature_id, mode,
           lower(concat_ws(' ', feature_name, description, source_id, lineage_model, limitation)) as txt,
           source_id
    from {{ ref('dim_feature') }}
)

select 'deployment term in feature-layer column' as issue, table_name as object, column_name as detail
from cols
where {% for t in terms %}contains(column_name, '{{ t }}'){% if not loop.last %} or {% endif %}{% endfor %}

union all
select 'DIM_FEATURE cites a deployment source', feature_id || ' / ' || mode, source_id
from feature_text
where regexp_like(coalesce(source_id, ''), '.*S-3[5-9].*')

union all
select 'DIM_FEATURE mentions an operator or deployment', feature_id || ' / ' || mode, left(txt, 120)
from feature_text
where regexp_like(txt, '.*\\b(waymo|zoox|tesla|cruise|motional|may mobility|avride|nuro|starship|serve robotics|kiwibot|cartken|zipline|prime air|droneup|flytrex|deployment)\\b.*')

union all
select 'deployment relation in ANALYTICS', table_name, null
from {{ target.database }}.information_schema.tables
where table_schema = 'ANALYTICS'
  and (table_name ilike '%DEPLOY%' or table_name ilike '%OPERATOR%')
