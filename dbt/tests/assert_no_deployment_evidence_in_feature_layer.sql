-- DEPLOYMENT-LEAK GUARD (Phase 6.5): deployment evidence (sources S-35 to S-39 and the curated
-- evidence/deployment_evidence.csv) is EXTERNAL VALIDATION ONLY. It must never appear in the
-- production feature layer:
--   1. no column of the mode marts or DIM_FEATURE names an operator or a deployment concept;
--   2. no DIM_FEATURE row (name, description, source, lineage) cites a deployment source or operator;
--   3. no ANALYTICS relation is a deployment table.
-- Phase 7: check 1 also covers every baseline scoring relation (scores, ranks, decompositions).
-- Phase 9: check 1 also covers every Power BI publication relation except the single sanctioned
-- external-validation table PBI_FCT_DEPLOYMENT_VALIDATION, which is also the only deployment relation
-- allowed in ANALYTICS (check 3). Scoring and robustness relations never read it.
-- depends_on: {{ ref('pbi_dim_market') }}
-- depends_on: {{ ref('pbi_dim_feature') }}
-- depends_on: {{ ref('pbi_dim_scenario') }}
-- depends_on: {{ ref('pbi_fct_market_baseline') }}
-- depends_on: {{ ref('pbi_fct_market_component') }}
-- depends_on: {{ ref('pbi_fct_market_feature_contribution') }}
-- depends_on: {{ ref('pbi_fct_market_robustness') }}
-- depends_on: {{ ref('pbi_fct_business_scenario') }}
-- depends_on: {{ ref('pbi_fct_regulatory_uncertainty') }}
-- depends_on: {{ ref('pbi_fct_deployment_validation') }}
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
                         'MART_SIDEWALK_DELIVERY_READINESS_BASELINE', 'MART_DRONE_DELIVERY_READINESS_BASELINE',
                         'PBI_DIM_MARKET', 'PBI_DIM_MODE', 'PBI_DIM_COMPONENT', 'PBI_DIM_FEATURE', 'PBI_DIM_SCENARIO',
                         'PBI_DIM_REGULATORY_SCENARIO', 'PBI_FCT_MARKET_BASELINE', 'PBI_FCT_MARKET_COMPONENT',
                         'PBI_FCT_MARKET_FEATURE_CONTRIBUTION', 'PBI_FCT_MARKET_ROBUSTNESS',
                         'PBI_FCT_BUSINESS_SCENARIO', 'PBI_FCT_REGULATORY_UNCERTAINTY'] %}
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
  and table_name <> 'PBI_FCT_DEPLOYMENT_VALIDATION'
