-- PBI_DIM_COMPONENT: the five readiness components. Grain: one row per component.
-- Robotaxi uses C1-C4 only; facts simply have no robotaxi C5 rows.
select 'C1_DEMAND_AND_MARKET_OPPORTUNITY' as component, 'C1' as component_code, 'Demand & Market Opportunity' as component_name,
       1 as sort_order, 'Addressable demand: size, density, trip and spending intensity.' as component_description
union all
select 'C2_OPERATING_ENVIRONMENT', 'C2', 'Operating Environment', 2,
       'Weather friction: precipitation days, 90°F days, snowfall (drone: also mean wind).'
union all
select 'C3_ECONOMIC_ATTRACTIVENESS', 'C3', 'Economic Attractiveness', 3,
       'Labor-cost savings and business density.'
union all
select 'C4_REGULATORY_AND_AUTONOMY_READINESS', 'C4', 'Regulatory & Autonomy Readiness', 4,
       'Verified state law, as the share of market population in favorable jurisdictions (sidewalk: also the PDD weight limit).'
union all
select 'C5_INFRASTRUCTURE_AND_MODE_FIT', 'C5', 'Infrastructure & Mode Fit', 5,
       'Built-environment fit (sidewalk: walkability; drone: single-family detached share). Not available for robotaxi.'
