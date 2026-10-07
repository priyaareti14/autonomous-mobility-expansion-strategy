-- PBI_DIM_SCENARIO: the approved named business-priority scenarios (Phase 8 contract). Grain: one row per
-- scenario_id (17: robotaxi 5, sidewalk 6, drone 6). These are scenario assumptions, not estimates of
-- business preferences. Robotaxi c5_weight is always NULL: there is no robotaxi C5 and no fake C5 scenario.
with c as (
    select
        *,
        regexp_replace(scenario_id, '^(ROBOTAXI|SIDEWALK|DRONE)_', '') as scenario_type
    from {{ ref('p8_scenario_contract') }}
)

select
    scenario_id,
    mode,
    scenario_name,
    scenario_type,
    case scenario_type
        when 'DEMAND_PRIORITY' then 'C1'
        when 'OPERATING_ENVIRONMENT_PRIORITY' then 'C2'
        when 'ECONOMIC_PRIORITY' then 'C3'
        when 'REGULATORY_PRIORITY' then 'C4'
        when 'INFRASTRUCTURE_PRIORITY' then 'C5'
    end                                                     as priority_component_code,
    c1_weight,
    c2_weight,
    c3_weight,
    c4_weight,
    c5_weight,
    scenario_type = 'NEUTRAL'                               as is_baseline_scenario,
    case scenario_type
        when 'NEUTRAL' then 0
        when 'DEMAND_PRIORITY' then 1
        when 'OPERATING_ENVIRONMENT_PRIORITY' then 2
        when 'ECONOMIC_PRIORITY' then 3
        when 'REGULATORY_PRIORITY' then 4
        when 'INFRASTRUCTURE_PRIORITY' then 5
    end                                                     as sort_order,
    description
from c
