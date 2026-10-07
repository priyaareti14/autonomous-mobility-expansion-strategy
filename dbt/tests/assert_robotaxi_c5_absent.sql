-- ROBOTAXI C5 IS STRUCTURALLY ABSENT (A-039): no C5 input, component, score or column exists for robotaxi.
-- It is excluded, never a zero, a proxy or a redistributed feature.
-- depends_on: {{ ref('mart_robotaxi_readiness_baseline') }}
select 'robotaxi C5 input' as issue, market_id, feature_id as detail
from {{ ref('fct_feature_scores') }}
where mode = 'ROBOTAXI' and component = 'C5_INFRASTRUCTURE_AND_MODE_FIT'

union all
select 'robotaxi C5 component', market_id, component
from {{ ref('fct_component_scores') }}
where mode = 'ROBOTAXI' and component = 'C5_INFRASTRUCTURE_AND_MODE_FIT'

union all
select 'robotaxi C5 column', table_name, column_name
from {{ target.database }}.information_schema.columns
where table_schema = 'ANALYTICS' and table_name = 'MART_ROBOTAXI_READINESS_BASELINE'
  and column_name ilike 'C5%'
