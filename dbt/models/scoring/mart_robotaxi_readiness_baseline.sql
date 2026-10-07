-- MART_ROBOTAXI_READINESS_BASELINE: robotaxi baseline readiness (baseline_v1). Grain: one row per market (35).
-- Four active components at 25% each: C5 Infrastructure & Mode Fit has no active robotaxi feature and is
-- structurally absent (A-039): no proxy, no zero, no column. Scores are comparable WITHIN ROBOTAXI only.
{{ readiness_mart('ROBOTAXI', [
    'C1_DEMAND_AND_MARKET_OPPORTUNITY',
    'C2_OPERATING_ENVIRONMENT',
    'C3_ECONOMIC_ATTRACTIVENESS',
    'C4_REGULATORY_AND_AUTONOMY_READINESS'
]) }}
