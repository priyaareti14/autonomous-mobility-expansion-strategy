-- REGULATORY COVERAGE RECONCILES (Step 11): in every market x mode x dimension the population shares add up.
--   favorable + unfavorable + unknown/LOW + not applicable = 1
--   unfavorable = absence + explicit + unclear + scope-limited
--   evidence_coverage_pct = 100 x (1 - unknown/LOW)
{% set tol = var('score_tolerance') %}
select market_id, mode, legal_dimension, 'shares do not sum to 1' as issue
from {{ ref('fct_regulatory_dimension_scores') }}
where abs(verified_favorable_share + verified_unfavorable_share + unknown_or_low_confidence_share
          + not_applicable_share - 1) > {{ tol }}
   or abs(total_population_share - 1) > {{ tol }}

union all
select market_id, mode, legal_dimension, 'unfavorable share does not decompose'
from {{ ref('fct_regulatory_dimension_scores') }}
where abs(verified_unfavorable_share - (verified_absence_share + verified_explicit_unfavorable_share
          + verified_unclear_share + verified_scope_limited_share)) > {{ tol }}

union all
select market_id, mode, legal_dimension, 'coverage inconsistent with unknown share'
from {{ ref('fct_regulatory_dimension_scores') }}
where abs(evidence_coverage_pct - 100 * (1 - unknown_or_low_confidence_share)) > {{ tol }}

union all
select market_id, mode, legal_dimension, 'not-applicable share outside the numeric dimension'
from {{ ref('fct_regulatory_dimension_scores') }}
where not numeric_dimension_flag and not_applicable_share > {{ tol }}
