-- REGULATORY UNCERTAINTY PUBLICATION (Phase 9): three bounds per market and mode, never averaged.
--   * markets with complete regulatory evidence have the same score under all three bounds, equal to the
--     Phase 7 baseline score, and the backed-out regulatory_score equals the Phase 7 C4 (tolerance 1e-4: the
--     Phase 8 export keeps 6 decimals and the back-out divides by the C4 weight);
--   * pessimistic <= neutral <= optimistic, and neutral is the midpoint (the formula is linear);
--   * robotaxi rows carry the nested weight-sensitivity metrics; sidewalk/drone rows do not.
with r as (
    select * from {{ ref('pbi_fct_regulatory_uncertainty') }}
),

w as (
    select market_id, mode,
           max(iff(regulatory_scenario = 'REG_PESSIMISTIC', scenario_score, null)) as pes,
           max(iff(regulatory_scenario = 'REG_NEUTRAL', scenario_score, null))     as neu,
           max(iff(regulatory_scenario = 'REG_OPTIMISTIC', scenario_score, null))  as opt,
           count(*)                                                                 as n
    from r
    group by 1, 2
)

select 'not exactly three bounds' as issue, market_id, mode from w where n <> 3
union all
select 'bounds out of order or neutral not the midpoint', market_id, mode
from w
where pes > neu + 0.00001 or neu > opt + 0.00001 or abs(neu - (pes + opt) / 2) > 0.00001
union all
select 'complete market score differs from the Phase 7 baseline', r.market_id, r.mode
from r
join {{ ref('fct_readiness_baseline') }} b on b.market_id = r.market_id and b.mode = r.mode
where r.regulatory_complete_flag and abs(r.scenario_score - b.baseline_readiness_score) > 0.00001
union all
select 'backed-out regulatory score differs from the Phase 7 C4', r.market_id, r.mode
from r
join {{ ref('fct_readiness_baseline') }} b on b.market_id = r.market_id and b.mode = r.mode
where r.regulatory_complete_flag and abs(r.regulatory_score - b.c4_score_verified) > 0.0001
union all
select 'nested weight sensitivity missing (robotaxi) or present (other modes)', market_id, mode
from r
where (mode = 'ROBOTAXI') <> (nested_top_5_frequency is not null)
