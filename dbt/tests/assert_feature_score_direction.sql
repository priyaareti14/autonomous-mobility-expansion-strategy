-- DIRECTION AND NORMALIZATION: every non-regulatory feature score is the average-rank percentile of its
-- transformed value, applied in the contract direction.
--   * no feature score is null (features are REQUIRED_COMPLETE);
--   * HIGHER_IS_MORE_FAVORABLE: a higher value never gets a lower score; LOWER_IS_MORE_FAVORABLE: the reverse;
--   * equal values get equal scores (deterministic ties);
--   * across the 35 markets the scores average exactly 50 (true of any average-rank percentile).
with f as (
    select * from {{ ref('fct_feature_scores') }}
    where component <> '{{ phase7_c4() }}'
),

ordered as (
    select
        *,
        lag(transformed_value) over (partition by mode, feature_id order by transformed_value, market_id) as prev_value,
        lag(feature_score) over (partition by mode, feature_id order by transformed_value, market_id)     as prev_score
    from f
)

select 'null feature score' as issue, mode, feature_id, market_id, feature_score
from f
where feature_score is null or transformed_value is null

union all
select 'direction violated', mode, feature_id, market_id, feature_score
from ordered
where prev_value is not null
  and transformed_value > prev_value
  and ((direction = 'HIGHER_IS_MORE_FAVORABLE' and feature_score <= prev_score)
       or (direction = 'LOWER_IS_MORE_FAVORABLE' and feature_score >= prev_score))

union all
select 'tied values scored differently', mode, feature_id, market_id, feature_score
from ordered
where prev_value is not null and transformed_value = prev_value and abs(feature_score - prev_score) > {{ var('score_tolerance') }}

union all
select 'feature scores do not average 50', mode, feature_id, null, avg(feature_score)
from f
group by mode, feature_id
having abs(avg(feature_score) - 50) > {{ var('score_tolerance') }}
