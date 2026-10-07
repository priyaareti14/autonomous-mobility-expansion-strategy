-- BASELINE RANK: within each mode, ranks follow standard competition ranking over the complete markets:
-- rank 1 is the highest score, each rank equals 1 + the number of markets with a strictly higher score
-- (to 6 decimals), and no rank exceeds the number of ranked markets.
with b as (
    select * from {{ ref('fct_readiness_baseline') }} where baseline_readiness_score is not null
),

expected as (
    select
        b1.market_id,
        b1.mode,
        b1.baseline_rank,
        1 + count(b2.market_id) as expected_rank
    from b b1
    left join b b2
      on b2.mode = b1.mode and round(b2.baseline_readiness_score, 6) > round(b1.baseline_readiness_score, 6)
    group by 1, 2, 3
)

select 'rank differs from competition rank' as issue, market_id, mode, baseline_rank, expected_rank
from expected
where baseline_rank <> expected_rank

union all
select 'rank exceeds ranked market count', market_id, mode, baseline_rank, null
from b
where baseline_rank > (select count(*) from b b2 where b2.mode = b.mode)
