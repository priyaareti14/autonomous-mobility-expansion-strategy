-- PHASE BOUNDARY GUARD (Phases 4-6): no readiness score, feature weight, normalized index, ranking,
-- cluster label or deployment field exists in INTERMEDIATE, CORE or ANALYTICS before Phase 7.
-- Allowed exceptions, each a documented non-scoring concept:
--   rank:   market_rank / market_rank_2025 (the population-based universe rule), FAA's published
--           enplanement rank, EPA's published *_ranked SLD inputs, distance_rank in candidate tables;
--   weight: population weighting of a measure (POPULATION_WEIGHTED*, TRACTS_WEIGHTED), never a
--           feature weight.
select table_schema, table_name, column_name
from {{ target.database }}.information_schema.columns
where table_schema in ('INTERMEDIATE', 'CORE', 'ANALYTICS')
  and (
        column_name ilike '%score%'
     or column_name ilike '%readiness%'
     or column_name ilike '%normalized%'
     or column_name ilike '%cluster%'
     or column_name ilike '%archetype%'
     or column_name ilike '%kmeans%'
     or column_name ilike '%deployment%'
     or (column_name ilike '%weight%'
         and column_name not ilike 'POPULATION_WEIGHTED%'
         and column_name <> 'TRACTS_WEIGHTED')
     or (column_name ilike '%rank%'
         and column_name not in ('MARKET_RANK', 'MARKET_RANK_2025', 'ENPLANEMENT_RANK_CY2025', 'DISTANCE_RANK',
                                 'D2A_RANKED', 'D2B_RANKED', 'D3B_RANKED', 'D4A_RANKED'))
  )
