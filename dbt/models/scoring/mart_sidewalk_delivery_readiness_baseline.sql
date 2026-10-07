-- MART_SIDEWALK_DELIVERY_READINESS_BASELINE: sidewalk delivery robot baseline readiness (baseline_v1).
-- Grain: one row per market (35). Five active components at 20% each. Comparable WITHIN SIDEWALK DELIVERY only.
{{ readiness_mart('SIDEWALK_DELIVERY', [
    'C1_DEMAND_AND_MARKET_OPPORTUNITY',
    'C2_OPERATING_ENVIRONMENT',
    'C3_ECONOMIC_ATTRACTIVENESS',
    'C4_REGULATORY_AND_AUTONOMY_READINESS',
    'C5_INFRASTRUCTURE_AND_MODE_FIT'
]) }}
