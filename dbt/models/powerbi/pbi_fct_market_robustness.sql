-- PBI_FCT_MARKET_ROBUSTNESS: Phase 8 robustness per market and mode. Grain: market_id x mode (105).
-- Copied from the committed Phase 8 outputs (robustness_summary + the BASELINE_EVIDENCE rows of
-- weight_sensitivity_summary, 10,000 Dirichlet draws, seed 20261007). Frequencies are shares of tested weight
-- configurations, not probabilities. Weight-draw metrics are NULL for markets without a complete baseline score.
-- Flags are the approved Phase 8 pattern flags; no composite robustness score exists.
select
    r.market_id,
    r.mode,
    r.baseline_rank,
    r.baseline_score,
    r.score_complete_flag,
    w.n_ranked_markets,
    w.n_draws,
    r.mean_rank,
    r.median_rank,
    r.rank_std,
    r.best_rank,
    r.worst_rank,
    w.top_1_frequency,
    w.top_3_frequency,
    r.top_5_frequency,
    r.top_10_frequency,
    w.rank_iqr,
    r.rank_p05                              as rank_90pct_low,
    r.rank_p95                              as rank_90pct_high,
    r.rank_interval_90,
    w.within_2_ranks_of_baseline_frequency,
    w.mean_abs_rank_change_from_baseline,
    w.mean_score                            as mean_sensitivity_score,
    w.score_std                             as sensitivity_score_std,
    r.business_scenario_rank_range,
    r.normalization_rank_range,
    r.methodology_rank_range,
    r.regulatory_rank_range,
    r.regulatory_best_rank,
    r.regulatory_worst_rank,
    r.regulatory_score_range,
    r.fixed_test_worst_rank,
    r.overall_tested_best_rank,
    r.overall_tested_worst_rank,
    r.consistent_top_performer,
    r.weight_sensitive,
    r.normalization_sensitive,
    r.methodology_sensitive,
    r.regulation_sensitive,
    r.pattern_flags
from {{ ref('p8_robustness_summary') }} r
left join {{ ref('p8_weight_sensitivity') }} w
  on w.mode = r.mode and w.market_id = r.market_id and w.regulatory_scenario = 'BASELINE_EVIDENCE'
