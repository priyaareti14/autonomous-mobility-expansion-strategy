-- READINESS SCORES ARE MODE-SPECIFIC (Step 30): no relation combines modes into one score.
--   * no ANALYTICS column names a combined / cross-mode / all-mode / overall-autonomy measure;
--   * every score row belongs to exactly one of the three modes;
--   * no ANALYTICS relation is a combined or cross-mode table.
-- depends_on: {{ ref('fct_readiness_baseline') }}
-- depends_on: {{ ref('mart_robotaxi_readiness_baseline') }}
-- depends_on: {{ ref('mart_sidewalk_delivery_readiness_baseline') }}
-- depends_on: {{ ref('mart_drone_delivery_readiness_baseline') }}
select 'cross-mode column' as issue, table_name as object, column_name as detail
from {{ target.database }}.information_schema.columns
where table_schema = 'ANALYTICS'
  and (column_name ilike '%combined%' or column_name ilike '%cross_mode%' or column_name ilike '%all_mode%'
       or column_name ilike '%multimodal%' or column_name ilike '%autonomy_score%' or column_name ilike '%overall_autonomy%')

union all
select 'cross-mode relation', table_name, null
from {{ target.database }}.information_schema.tables
where table_schema = 'ANALYTICS'
  and (table_name ilike '%COMBINED%' or table_name ilike '%CROSS_MODE%' or table_name ilike '%ALL_MODE%')

union all
select 'score row without a single mode', market_id, mode
from {{ ref('fct_readiness_baseline') }}
where mode not in ('ROBOTAXI', 'SIDEWALK_DELIVERY', 'DRONE_DELIVERY') or mode is null
