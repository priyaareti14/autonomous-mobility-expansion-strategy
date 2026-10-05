-- PHASE BOUNDARY GUARD: no readiness score, weight, normalized index or ranking column exists in
-- CORE or ANALYTICS during Phase 4. market_rank_2025 (the documented population-based selection
-- rule) and EPA's published *_ranked inputs are the only allowed 'rank' columns.
select table_schema, table_name, column_name
from {{ target.database }}.information_schema.columns
where table_schema in ('CORE', 'ANALYTICS')
  and (
        column_name ilike '%score%'
     or column_name ilike '%weight%'
     or column_name ilike '%readiness%'
     or column_name ilike '%normalized%'
     or column_name ilike '%cluster%'
     or (column_name ilike '%rank%'
         and column_name not in ('MARKET_RANK_2025', 'ENPLANEMENT_RANK_CY2025',
                                 'D2A_RANKED', 'D2B_RANKED', 'D3B_RANKED', 'D4A_RANKED'))
  )
