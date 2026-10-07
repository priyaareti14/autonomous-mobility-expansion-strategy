-- LOW / UNVERIFIED EVIDENCE NEVER ENTERS THE BASE SCORE (Step 12, Step 26).
--   1. any market x mode with an UNKNOWN_OR_LOW_CONFIDENCE state row has no C4 score and no overall score;
--   2. no dimension score is computed from an incomplete dimension;
--   3. the weight-limit percentile is computed only over markets whose limit is fully verified;
--   4. the 10 robotaxi records that Phase 6.5b marked INCLUDE_ONLY_IN_SENSITIVITY are all classed
--      UNKNOWN_OR_LOW_CONFIDENCE (a guard against a silent eligibility change).
{% set sensitivity_only = ['RT-MA-02', 'RT-MA-03', 'RT-MA-06', 'RT-NJ-02', 'RT-NJ-03', 'RT-NJ-06',
                           'RT-OH-02', 'RT-OH-03', 'RT-OH-06', 'RT-NY-06'] %}
with unverified as (
    select distinct market_id, mode
    from {{ ref('int_regulatory__market_state_evidence') }}
    where base_evidence_class = 'UNKNOWN_OR_LOW_CONFIDENCE'
)

select 'market with unverified evidence has a base score' as issue, b.market_id, b.mode, null as detail
from {{ ref('fct_readiness_baseline') }} b
join unverified u on u.market_id = b.market_id and u.mode = b.mode
where b.c4_score_verified is not null or b.baseline_readiness_score is not null

union all
select 'incomplete dimension carries a score', market_id, mode, legal_dimension
from {{ ref('fct_regulatory_dimension_scores') }}
where not dimension_complete_flag and dimension_score is not null

union all
select 'weight percentile domain includes an unverified market', market_id, mode, legal_dimension
from {{ ref('fct_regulatory_dimension_scores') }}
where numeric_dimension_flag and ranking_value is not null and not dimension_complete_flag

union all
select 'sensitivity-only record is base-eligible', market_id, mode, evidence_id
from {{ ref('int_regulatory__market_state_evidence') }}
where evidence_id in ('{{ sensitivity_only | join("', '") }}')
  and base_evidence_class <> 'UNKNOWN_OR_LOW_CONFIDENCE'

union all
select 'LOW-confidence record classed as verified', market_id, mode, evidence_id
from {{ ref('int_regulatory__market_state_evidence') }}
where confidence = 'LOW' and base_evidence_class in ('VERIFIED_FAVORABLE', 'VERIFIED_NOT_FAVORABLE')
