-- PBI_DIM_REGULATORY_SCENARIO: the three Phase 8 regulatory-uncertainty bounds. Grain: one row per scenario.
-- Bounds on unresolved state evidence, NOT forecasts of the law; they are never averaged.
select 'REG_PESSIMISTIC' as regulatory_scenario, 'Pessimistic' as regulatory_scenario_name, 0.0::float as assumed_favorable_fraction,
       1 as sort_order, 'Unknown / LOW-confidence population share counted 0% favorable' as regulatory_scenario_description
union all
select 'REG_NEUTRAL', 'Neutral', 0.5, 2, 'Unknown / LOW-confidence population share counted 50% favorable'
union all
select 'REG_OPTIMISTIC', 'Optimistic', 1.0, 3, 'Unknown / LOW-confidence population share counted 100% favorable'
