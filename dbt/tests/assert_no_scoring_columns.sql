-- PHASE BOUNDARY GUARD. Phases 4-6: no readiness score, feature weight, normalized index, ranking,
-- cluster label or deployment field anywhere in INTERMEDIATE, CORE or ANALYTICS.
-- Phase 7 (baseline_v1) narrows the guard rather than removing it:
--   * score / readiness / weight / rank columns are allowed ONLY in the named Phase 7 scoring relations
--     below (ANALYTICS). They stay forbidden in every other relation, including the Phase 6 feature
--     marts, DIM_FEATURE, INTERMEDIATE and CORE;
--   * cluster, archetype, k-means and deployment columns stay forbidden EVERYWHERE, scoring included.
-- Allowed exceptions outside the scoring relations, each a documented non-scoring concept:
--   rank:   market_rank / market_rank_2025 (the population-based universe rule), FAA's published
--           enplanement rank, EPA's published *_ranked SLD inputs, distance_rank in candidate tables;
--   weight: population weighting of a measure (POPULATION_WEIGHTED*, TRACTS_WEIGHTED), never a
--           feature weight.
-- The scoring relations are read through information_schema, so their build order is declared:
-- depends_on: {{ ref('fct_feature_scores') }}
-- depends_on: {{ ref('fct_component_scores') }}
-- depends_on: {{ ref('fct_readiness_baseline') }}
-- depends_on: {{ ref('mart_robotaxi_readiness_baseline') }}
-- depends_on: {{ ref('mart_sidewalk_delivery_readiness_baseline') }}
-- depends_on: {{ ref('mart_drone_delivery_readiness_baseline') }}
{% set scoring_relations = ['FCT_REGULATORY_DIMENSION_SCORES', 'FCT_FEATURE_SCORES', 'FCT_COMPONENT_SCORES',
                            'FCT_READINESS_BASELINE', 'MART_ROBOTAXI_READINESS_BASELINE',
                            'MART_SIDEWALK_DELIVERY_READINESS_BASELINE', 'MART_DRONE_DELIVERY_READINESS_BASELINE'] %}
select table_schema, table_name, column_name, 'scoring column outside the Phase 7 scoring relations' as issue
from {{ target.database }}.information_schema.columns
where table_schema in ('INTERMEDIATE', 'CORE', 'ANALYTICS')
  and not (table_schema = 'ANALYTICS' and table_name in ('{{ scoring_relations | join("', '") }}'))
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

select table_schema, table_name, column_name, 'cluster or deployment column' as issue
from {{ target.database }}.information_schema.columns
where table_schema in ('INTERMEDIATE', 'CORE', 'ANALYTICS')
  and (
        column_name ilike '%cluster%'
     or column_name ilike '%archetype%'
     or column_name ilike '%kmeans%'
     or column_name ilike '%deployment%'
  )
