-- ROBUSTNESS PUBLICATION (Phase 9): the published Phase 8 metrics are internally consistent and tied to the
-- Phase 7 baseline.
--   * the robustness baseline rank equals the Phase 7 baseline rank;
--   * weight-draw metrics exist exactly for markets with a complete baseline score;
--   * ranks lie within 1..n_ranked_markets; best <= median <= worst; 90% interval inside best..worst;
--   * top-k frequencies are in [0,1] and nested (top1 <= top3 <= top5 <= top10).
with r as (
    select * from {{ ref('pbi_fct_market_robustness') }}
)

select 'baseline rank differs from Phase 7' as issue, r.market_id, r.mode
from r
join {{ ref('fct_readiness_baseline') }} b on b.market_id = r.market_id and b.mode = r.mode
where not equal_null(r.baseline_rank, b.baseline_rank)

union all
select 'weight-draw metrics present iff score complete violated', market_id, mode
from r
where (mean_rank is not null) <> score_complete_flag or (top_1_frequency is not null) <> score_complete_flag

union all
select 'rank outside 1..n_ranked or misordered', market_id, mode
from r
where mean_rank is not null
  and (best_rank < 1 or worst_rank > n_ranked_markets or best_rank > median_rank or median_rank > worst_rank
       or rank_90pct_low < best_rank or rank_90pct_high > worst_rank)

union all
select 'top-k frequencies out of range or not nested', market_id, mode
from r
where mean_rank is not null
  and (top_1_frequency < 0 or top_10_frequency > 1 or top_1_frequency > top_3_frequency
       or top_3_frequency > top_5_frequency or top_5_frequency > top_10_frequency)
