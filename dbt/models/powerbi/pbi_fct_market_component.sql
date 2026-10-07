-- PBI_FCT_MARKET_COMPONENT: Phase 7 component scores. Grain: market_id x mode x component (490).
-- Robotaxi has no C5 rows (structurally absent). C4 score is NULL where regulatory evidence is incomplete.
select
    c.market_id,
    c.mode,
    c.component,
    d.component_code,
    c.component_score,
    c.component_weight,
    c.component_contribution,
    c.component_complete_flag,
    c.feature_count,
    c.evidence_coverage_pct             as regulatory_evidence_coverage_pct,
    c.non_regulatory_component_weight
from {{ ref('fct_component_scores') }} c
join {{ ref('pbi_dim_component') }} d on d.component = c.component
