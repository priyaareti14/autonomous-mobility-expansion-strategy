-- PBI_FCT_DEPLOYMENT_VALIDATION: EXTERNAL VALIDATION ONLY (Phase 8, deployment evidence as of 2026-10-05).
-- Grain: market_id x mode (105). The only publication relation allowed to hold deployment fields; no scoring
-- or robustness relation reads it (assert_no_deployment_evidence_in_feature_layer, assert_no_scoring_columns).
-- deployment_present = an open-ended COMMERCIAL / LIMITED_COMMERCIAL record resolved to this market (broad
-- cohort). Presence means "some service in the market", never "the market is served"; no recorded deployment
-- is NOT evidence of unsuitability. Not a measure of model accuracy.
select
    v.market_id,
    v.mode,
    v.current_commercial_broad                          as deployment_present,
    v.current_commercial_broad                          as commercial_or_limited_commercial_flag,
    v.current_commercial_primary                        as deployment_present_primary_cohort,
    v.current_commercial_primary_verified               as deployment_present_verified_only,
    v.deployment_cohort                                 as deployment_status,
    v.deployment_cohort <> 'NO_RECORDED_DEPLOYMENT'     as any_deployment_record,
    v.current_resolutions                               as market_resolution_quality,
    v.current_operators,
    v.pilot_present,
    v.testing_present,
    v.announced_present,
    v.paused_present,
    v.ended_present,
    v.unknown_present,
    m.category                                          as mismatch_category,
    m.weakest_component                                 as mismatch_weakest_component,
    m.candidate_explanations                            as mismatch_candidate_explanations
from {{ ref('p8_deployment_validation') }} v
left join {{ ref('p8_deployment_mismatch') }} m on m.mode = v.mode and m.market_id = v.market_id
