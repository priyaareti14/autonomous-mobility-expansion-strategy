-- PHASE 7 INPUT FREEZE: the scored inputs are EXACTLY the frozen contracts, both ways.
--   * non-regulatory inputs = DIM_FEATURE rows with production_status ACTIVE (30: 10 per mode)
--   * regulatory inputs     = regulatory_feature_contract rows with candidate_status ACTIVE_CANDIDATE (7)
-- No feature can be added, dropped or re-assigned to another component silently.
with scored as (
    select distinct mode, feature_id, component
    from {{ ref('fct_feature_scores') }}
),

expected as (
    select mode, feature_id, component
    from {{ ref('dim_feature') }}
    where production_status = 'ACTIVE'
    union all
    select mode, feature_id, '{{ phase7_c4() }}'
    from {{ ref('regulatory_feature_contract') }}
    where candidate_status = 'ACTIVE_CANDIDATE'
)

select 'contract input not scored' as issue, e.mode, e.feature_id, e.component
from expected e
left join scored s on s.mode = e.mode and s.feature_id = e.feature_id and s.component = e.component
where s.feature_id is null

union all

select 'scored input not in a contract', s.mode, s.feature_id, s.component
from scored s
left join expected e on e.mode = s.mode and e.feature_id = s.feature_id and e.component = s.component
where e.feature_id is null
