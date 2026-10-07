-- PHASE BOUNDARY GUARD. Phases 4-6: no readiness score, feature weight, normalized index, ranking,
-- cluster label or deployment field anywhere in INTERMEDIATE, CORE or ANALYTICS.
-- Phase 7 (baseline_v1) narrowed the guard rather than removing it; Phase 9 narrows it again, by name only:
--   * score / readiness / weight / rank columns are allowed ONLY in the named relations below:
--     the Phase 7 scoring relations and the Phase 9 Power BI publication relations (ANALYTICS), and the
--     generated Phase 8 seeds (INTERMEDIATE). They stay forbidden everywhere else, including the Phase 6
--     feature marts, DIM_FEATURE, the other INTERMEDIATE models and CORE;
--   * deployment columns are allowed ONLY in the external-validation relations (the two deployment seeds and
--     ANALYTICS.PBI_FCT_DEPLOYMENT_VALIDATION); cluster, archetype and k-means columns stay forbidden everywhere.
-- Allowed exceptions outside the scoring relations, each a documented non-scoring concept:
--   rank:   market_rank / market_rank_2025 (the population-based universe rule), FAA's published
--           enplanement rank, EPA's published *_ranked SLD inputs, distance_rank in candidate tables;
--   weight: population weighting of a measure (POPULATION_WEIGHTED*, TRACTS_WEIGHTED), never a
--           feature weight.
-- The checked relations are read through information_schema, so their build order is declared:
-- depends_on: {{ ref('fct_feature_scores') }}
-- depends_on: {{ ref('fct_component_scores') }}
-- depends_on: {{ ref('fct_readiness_baseline') }}
-- depends_on: {{ ref('mart_robotaxi_readiness_baseline') }}
-- depends_on: {{ ref('mart_sidewalk_delivery_readiness_baseline') }}
-- depends_on: {{ ref('mart_drone_delivery_readiness_baseline') }}
-- depends_on: {{ ref('pbi_fct_market_baseline') }}
-- depends_on: {{ ref('pbi_fct_market_component') }}
-- depends_on: {{ ref('pbi_fct_market_feature_contribution') }}
-- depends_on: {{ ref('pbi_fct_market_robustness') }}
-- depends_on: {{ ref('pbi_fct_business_scenario') }}
-- depends_on: {{ ref('pbi_fct_regulatory_uncertainty') }}
-- depends_on: {{ ref('pbi_fct_deployment_validation') }}
-- depends_on: {{ ref('pbi_dim_scenario') }}
-- depends_on: {{ ref('pbi_dim_market') }}
-- depends_on: {{ ref('pbi_dim_feature') }}
{% set analytics_scoring = ['FCT_REGULATORY_DIMENSION_SCORES', 'FCT_FEATURE_SCORES', 'FCT_COMPONENT_SCORES',
                            'FCT_READINESS_BASELINE', 'MART_ROBOTAXI_READINESS_BASELINE',
                            'MART_SIDEWALK_DELIVERY_READINESS_BASELINE', 'MART_DRONE_DELIVERY_READINESS_BASELINE',
                            'PBI_DIM_MARKET', 'PBI_DIM_FEATURE', 'PBI_DIM_SCENARIO', 'PBI_FCT_MARKET_BASELINE', 'PBI_FCT_MARKET_COMPONENT',
                            'PBI_FCT_MARKET_FEATURE_CONTRIBUTION', 'PBI_FCT_MARKET_ROBUSTNESS',
                            'PBI_FCT_BUSINESS_SCENARIO', 'PBI_FCT_REGULATORY_UNCERTAINTY',
                            'PBI_FCT_DEPLOYMENT_VALIDATION'] %}
{% set intermediate_scoring = ['P8_ROBUSTNESS_SUMMARY', 'P8_WEIGHT_SENSITIVITY', 'P8_BUSINESS_SCENARIOS',
                               'P8_SCENARIO_CONTRACT', 'P8_REGULATORY_UNCERTAINTY', 'P8_DEPLOYMENT_VALIDATION',
                               'P8_DEPLOYMENT_MISMATCH'] %}
{% set deployment_allowed = [('INTERMEDIATE', 'P8_DEPLOYMENT_VALIDATION'), ('INTERMEDIATE', 'P8_DEPLOYMENT_MISMATCH'),
                             ('ANALYTICS', 'PBI_FCT_DEPLOYMENT_VALIDATION')] %}
select table_schema, table_name, column_name, 'scoring column outside the named scoring / publication relations' as issue
from {{ target.database }}.information_schema.columns
where table_schema in ('INTERMEDIATE', 'CORE', 'ANALYTICS')
  and not (table_schema = 'ANALYTICS' and table_name in ('{{ analytics_scoring | join("', '") }}'))
  and not (table_schema = 'INTERMEDIATE' and table_name in ('{{ intermediate_scoring | join("', '") }}'))
  and (
        column_name ilike '%score%'
     or column_name ilike '%readiness%'
     or column_name ilike '%normalized%'
     or (column_name ilike '%weight%'
         and column_name not ilike 'POPULATION_WEIGHTED%'
         and column_name <> 'TRACTS_WEIGHTED')
     or (column_name ilike '%rank%'
         and column_name not in ('MARKET_RANK', 'MARKET_RANK_2025', 'ENPLANEMENT_RANK_CY2025', 'DISTANCE_RANK',
                                 'D2A_RANKED', 'D2B_RANKED', 'D3B_RANKED', 'D4A_RANKED'))
  )

union all

select table_schema, table_name, column_name, 'cluster column' as issue
from {{ target.database }}.information_schema.columns
where table_schema in ('INTERMEDIATE', 'CORE', 'ANALYTICS')
  and (column_name ilike '%cluster%' or column_name ilike '%archetype%' or column_name ilike '%kmeans%')

union all

select table_schema, table_name, column_name, 'deployment column outside the external-validation relations' as issue
from {{ target.database }}.information_schema.columns
where table_schema in ('INTERMEDIATE', 'CORE', 'ANALYTICS')
  and column_name ilike '%deployment%'
  and not ({% for s, t in deployment_allowed %}(table_schema = '{{ s }}' and table_name = '{{ t }}'){% if not loop.last %} or {% endif %}{% endfor %})
