-- INCOMPLETE REGULATION (Steps 13-14, 17): a market whose C4 is incomplete has NO C4 score, NO baseline
-- readiness score and NO baseline rank; a complete market has all three. A rank exists only where a score
-- exists, and the diagnostic non-regulatory score exists for every market.
select 'incomplete C4 carries a score or rank' as issue, market_id, mode
from {{ ref('fct_readiness_baseline') }}
where not c4_complete_flag
  and (c4_score_verified is not null or baseline_readiness_score is not null or baseline_rank is not null)

union all
select 'complete market without score or rank', market_id, mode
from {{ ref('fct_readiness_baseline') }}
where score_complete_flag and (baseline_readiness_score is null or baseline_rank is null)

union all
select 'rank without score', market_id, mode
from {{ ref('fct_readiness_baseline') }}
where baseline_rank is not null and baseline_readiness_score is null

union all
select 'score_complete_flag disagrees with C4 completeness', market_id, mode
from {{ ref('fct_readiness_baseline') }}
where score_complete_flag <> c4_complete_flag

union all
select 'missing non-regulatory diagnostic score', market_id, mode
from {{ ref('fct_readiness_baseline') }}
where non_regulatory_score is null

union all
select 'input of an incomplete market carries a weight or overall contribution', f.market_id, f.mode
from {{ ref('fct_feature_scores') }} f
join {{ ref('fct_readiness_baseline') }} b on b.market_id = f.market_id and b.mode = f.mode
where not b.c4_complete_flag
  and ((f.component = '{{ phase7_c4() }}' and f.feature_weight is not null)
       or f.contribution_to_overall is not null)
