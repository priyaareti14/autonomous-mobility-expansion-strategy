-- PUBLICATION RECONCILIATION (Phase 9): the Power BI baseline, component and feature facts are exact copies of
-- the Phase 7 scoring relations. Every value is compared NULL-safely, so a NULL that Phase 7 left NULL (an
-- incomplete regulatory market) can never be filled in, and no row can be gained or lost.
with base as (
    select b.market_id, b.mode
    from {{ ref('fct_readiness_baseline') }} b
    full outer join {{ ref('pbi_fct_market_baseline') }} p on p.market_id = b.market_id and p.mode = b.mode
    where b.market_id is null or p.market_id is null
       or not equal_null(p.baseline_readiness_score, b.baseline_readiness_score)
       or not equal_null(p.baseline_rank, b.baseline_rank)
       or not equal_null(p.score_complete_flag, b.score_complete_flag)
       or not equal_null(p.regulatory_complete_flag, b.c4_complete_flag)
       or not equal_null(p.non_regulatory_score, b.non_regulatory_score)
       or not equal_null(p.regulatory_score_verified, b.c4_score_verified)
       or not equal_null(p.regulatory_evidence_coverage_pct, b.c4_evidence_coverage_pct)
),

comp as (
    select c.market_id, c.mode, c.component
    from {{ ref('fct_component_scores') }} c
    full outer join {{ ref('pbi_fct_market_component') }} p
      on p.market_id = c.market_id and p.mode = c.mode and p.component = c.component
    where c.market_id is null or p.market_id is null
       or not equal_null(p.component_score, c.component_score)
       or not equal_null(p.component_weight, c.component_weight)
       or not equal_null(p.component_contribution, c.component_contribution)
       or not equal_null(p.component_complete_flag, c.component_complete_flag)
),

feat as (
    select f.market_id, f.mode, f.feature_id
    from {{ ref('fct_feature_scores') }} f
    full outer join {{ ref('pbi_fct_market_feature_contribution') }} p
      on p.market_id = f.market_id and p.mode = f.mode and p.feature_id = f.feature_id
    where f.market_id is null or p.market_id is null
       or not equal_null(p.raw_value, f.raw_value)
       or not equal_null(p.transformed_value, f.transformed_value)
       or not equal_null(p.feature_score, f.feature_score)
       or not equal_null(p.feature_weight, f.feature_weight)
       or not equal_null(p.weighted_feature_contribution, f.weighted_feature_contribution)
       or not equal_null(p.contribution_to_overall, f.contribution_to_overall)
)

select 'baseline differs from FCT_READINESS_BASELINE' as issue, market_id, mode, null as detail from base
union all
select 'component differs from FCT_COMPONENT_SCORES', market_id, mode, component from comp
union all
select 'feature differs from FCT_FEATURE_SCORES', market_id, mode, feature_id from feat
