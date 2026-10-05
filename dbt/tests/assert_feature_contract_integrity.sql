-- FEATURE METADATA INTEGRITY (DIM_FEATURE):
--   * every ACTIVE feature has a resolved direction (HIGHER/LOWER_IS_MORE_FAVORABLE), a unit, a
--     source, a lineage model and a description;
--   * a feature belongs to exactly one canonical component per mode (feature_id + mode and
--     feature_name + mode are unique);
--   * no ACTIVE feature sits in C4 Regulatory & Autonomy Readiness (pending Phase 6.5);
--   * the dictionary carries no weight, score or rank column.
with f as (select * from {{ ref('dim_feature') }})

select 'active feature with unresolved direction' as issue, mode, feature_name
from f where production_status = 'ACTIVE'
  and direction not in ('HIGHER_IS_MORE_FAVORABLE', 'LOWER_IS_MORE_FAVORABLE')

union all
select 'active feature missing metadata', mode, feature_name
from f where production_status = 'ACTIVE'
  and (unit is null or source_id is null or lineage_model is null or description is null
       or transformation is null or limitation is null)

union all
select 'feature_id not unique within mode', mode, feature_id
from f group by mode, feature_id having count(*) > 1

union all
select 'feature_name not unique within mode', mode, feature_name
from f group by mode, feature_name having count(*) > 1

union all
select 'active regulatory feature before Phase 6.5', mode, feature_name
from f where production_status = 'ACTIVE' and component = 'C4_REGULATORY_AND_AUTONOMY_READINESS'

union all
select 'active flag inconsistent with status', mode, feature_name
from f where active_pre_regulation_flag <> (production_status = 'ACTIVE')

union all
select 'forbidden metadata column', null, lower(column_name)
from {{ target.database }}.information_schema.columns
where table_schema = 'ANALYTICS' and table_name = 'DIM_FEATURE'
  and (column_name ilike '%weight%' or column_name ilike '%score%' or column_name ilike '%rank%')
