-- PBI_FCT_MARKET_BASELINE: the frozen Phase 7 baseline (baseline_v1) per market and mode.
-- Grain: market_id x mode (105). Copied from ANALYTICS.FCT_READINESS_BASELINE without recalculation:
-- baseline score and rank stay NULL where Phase 7 left them NULL (incomplete regulatory evidence).
select
    market_id,
    mode,
    baseline_readiness_score,
    baseline_rank,
    baseline_rank_tied_flag,
    score_gap_to_preceding,
    score_complete_flag,
    c4_complete_flag                    as regulatory_complete_flag,
    non_regulatory_score,
    c4_score_verified                   as regulatory_score_verified,
    c4_evidence_coverage_pct            as regulatory_evidence_coverage_pct,
    c4_max_unknown_share                as regulatory_max_unknown_share,
    c4_unverified_states                as regulatory_unverified_states,
    c4_incomplete_reason                as regulatory_incomplete_reason,
    c4_decomposition                    as regulatory_decomposition,
    strongest_feature,
    weakest_feature,
    top_positive_contributors,
    top_constraints,
    model_version
from {{ ref('fct_readiness_baseline') }}
