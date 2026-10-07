-- INT_REGULATORY__MARKET_STATE_EVIDENCE: the verified regulatory evidence behind every market.
-- Grain: one row per market x mode x ACTIVE_CANDIDATE legal dimension x state (BRG_MARKET_STATE).
--
-- Inputs (Phase 6.5 / 6.5b, frozen at commit 55b1cb4):
--   regulatory_state_evidence    state records of the 7 active dimensions (seed generated from evidence/)
--   regulatory_feature_contract  favorable statuses and the A-012 mapping method per dimension
--   regulatory_scope_adjustments documented base-model treatments (A-046 Nevada PDD scope)
--
-- Base-model eligibility (the Phase 6.5b rule, applied to every mode): a state record is eligible
-- only if it is VERIFIED_PRIMARY with MEDIUM or HIGH confidence. Ineligible records are classed
-- UNKNOWN_OR_LOW_CONFIDENCE: never favorable, never unfavorable, never zero.
--
-- base_evidence_class, one per state row:
--   VERIFIED_FAVORABLE        eligible and in the contract's favorable statuses (numeric dimension:
--                             the limit applies and is verified)
--   VERIFIED_NOT_FAVORABLE    eligible and not favorable (reason in not_favorable_reason)
--   UNKNOWN_OR_LOW_CONFIDENCE evidence missing or not base-eligible
--   NOT_APPLICABLE            numeric PDD limit in a state without a (general) PDD authorization
-- Nothing here is a score: shares and classes only.
with contract as (
    select
        feature_id                       as regulatory_feature_id,
        mode,
        legal_dimension,
        market_mapping_method,
        split(favorable_statuses, '|')   as favorable_statuses
    from {{ ref('regulatory_feature_contract') }}
    where candidate_status = 'ACTIVE_CANDIDATE'
),

evidence as (
    select
        e.*,
        e.confidence in ('HIGH', 'MEDIUM') and e.verification_status = 'VERIFIED_PRIMARY' as base_eligible_flag
    from {{ ref('regulatory_state_evidence') }} e
),

graded as (
    select
        e.*,
        a.base_model_treatment                                            as scope_adjustment,
        array_contains(e.coded_status::variant, c.favorable_statuses)
            and a.evidence_id is null                                     as favorable_code_flag
    from evidence e
    join contract c
      on c.mode = e.mode and c.legal_dimension = e.legal_dimension
    left join {{ ref('regulatory_scope_adjustments') }} a
      on a.evidence_id = e.evidence_id
),

-- Where does a PDD weight limit apply? Only in states whose PDD authorization is itself verified.
pdd as (
    select state_usps, base_eligible_flag as pdd_eligible_flag, favorable_code_flag as pdd_authorized_flag
    from graded
    where legal_dimension = 'SW_PDD_LEGAL_STATUS'
),

grid as (
    select b.market_id, b.state_usps, b.state_fips, b.population_share_2025, c.*
    from {{ ref('brg_market_state') }} b
    cross join contract c
),

classed as (
    select
        g.market_id,
        g.mode,
        g.legal_dimension,
        g.regulatory_feature_id,
        g.market_mapping_method,
        g.state_usps,
        g.state_fips,
        g.population_share_2025                                           as state_population_share,
        e.evidence_id,
        e.coded_status,
        e.numeric_value,
        e.unit,
        e.confidence,
        e.verification_status,
        e.source_type,
        e.effective_date,
        e.evidence_as_of,
        e.evidence_id is not null                                         as evidence_present_flag,
        coalesce(e.base_eligible_flag, false)                             as base_eligible_flag,
        e.scope_adjustment,
        iff(g.market_mapping_method = 'MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES',
            p.pdd_authorized_flag, null)                                  as pdd_authorized_flag,
        case
            when g.market_mapping_method = 'MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES' then
                case
                    when not coalesce(p.pdd_eligible_flag, false)   then 'UNKNOWN_OR_LOW_CONFIDENCE'
                    when not p.pdd_authorized_flag                  then 'NOT_APPLICABLE'
                    when not coalesce(e.base_eligible_flag, false)  then 'UNKNOWN_OR_LOW_CONFIDENCE'
                    else 'VERIFIED_FAVORABLE'
                end
            when not coalesce(e.base_eligible_flag, false) then 'UNKNOWN_OR_LOW_CONFIDENCE'
            when e.favorable_code_flag                      then 'VERIFIED_FAVORABLE'
            else 'VERIFIED_NOT_FAVORABLE'
        end                                                               as base_evidence_class
    from grid g
    left join graded e
      on e.mode = g.mode and e.legal_dimension = g.legal_dimension and e.state_usps = g.state_usps
    left join pdd p
      on p.state_usps = g.state_usps
)

select
    *,
    -- Why a verified record is not favorable. ABSENCE is silence in state law (A-043): neither
    -- permission nor prohibition, reported separately from explicit restrictions.
    case
        when base_evidence_class <> 'VERIFIED_NOT_FAVORABLE' then null
        when scope_adjustment is not null then 'SCOPE_LIMITED'
        when coded_status in ('NO_SPECIFIC_STATUTE', 'NO_SPECIFIC_FRAMEWORK', 'NOT_ADDRESSED', 'NO_STATUTE')
            then 'ABSENCE'
        when coded_status = 'UNCLEAR' then 'UNCLEAR'
        else 'EXPLICIT_NOT_FAVORABLE'
    end                                                                   as not_favorable_reason
from classed
