-- ROBOTAXI C5 STAYS ABSENT IN THE PUBLICATION LAYER (A-039): no robotaxi C5 component row, feature, or scenario
-- weight exists anywhere Power BI reads.
select 'robotaxi C5 component row' as issue, market_id as detail
from {{ ref('pbi_fct_market_component') }}
where mode = 'ROBOTAXI' and component = 'C5_INFRASTRUCTURE_AND_MODE_FIT'

union all
select 'robotaxi C5 feature', feature_key
from {{ ref('pbi_dim_feature') }}
where mode = 'ROBOTAXI' and component = 'C5_INFRASTRUCTURE_AND_MODE_FIT'

union all
select 'robotaxi C5 scenario weight', scenario_id
from {{ ref('pbi_fct_business_scenario') }}
where mode = 'ROBOTAXI' and c5_weight is not null

union all
select 'robotaxi mode declares C5', mode
from {{ ref('pbi_dim_mode') }}
where mode = 'ROBOTAXI' and (has_c5_component or active_component_count <> 4)
