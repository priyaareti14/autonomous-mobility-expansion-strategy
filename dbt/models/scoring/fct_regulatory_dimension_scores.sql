-- FCT_REGULATORY_DIMENSION_SCORES: C4 Regulatory & Autonomy Readiness, one dimension at a time.
-- Grain: one row per market x mode x ACTIVE_CANDIDATE legal dimension (35 x 7 = 245 rows).
--
-- Population shares (PEP 2025, BRG_MARKET_STATE) reconcile to 1 in every row:
--   verified_favorable_share + verified_unfavorable_share + unknown_or_low_confidence_share
--   + not_applicable_share = 1
-- verified_unfavorable_share is split into absence / explicit / unclear / scope-limited.
--
-- dimension_score (0-100), only where the dimension is COMPLETE (no unknown or LOW-confidence share):
--   categorical (POPULATION_SHARE_BY_STATUS): 100 x verified_favorable_share
--   numeric (SW_MAX_WEIGHT, MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES): the market value is the
--     lowest verified limit among its PDD-authorizing states (NO_LIMIT_STATED = unconstrained, ranked
--     above every number); scored by the same average-rank percentile as the features, among the
--     markets where the limit applies. Markets with no authorizing state: NOT APPLICABLE (no score).
-- An incomplete dimension has NO score: LOW-confidence evidence is never turned into 0, 50 or a
-- prohibition (docs/readiness_model.md §7).
with s as (
    select * from {{ ref('int_regulatory__market_state_evidence') }}
),

agg as (
    select
        market_id,
        mode,
        legal_dimension,
        regulatory_feature_id,
        market_mapping_method,
        count(*)                                                                         as state_count,
        sum(iff(base_evidence_class = 'VERIFIED_FAVORABLE', state_population_share, 0))  as verified_favorable_share,
        sum(iff(base_evidence_class = 'VERIFIED_NOT_FAVORABLE', state_population_share, 0)) as verified_unfavorable_share,
        sum(iff(not_favorable_reason = 'ABSENCE', state_population_share, 0))            as verified_absence_share,
        sum(iff(not_favorable_reason = 'EXPLICIT_NOT_FAVORABLE', state_population_share, 0)) as verified_explicit_unfavorable_share,
        sum(iff(not_favorable_reason = 'UNCLEAR', state_population_share, 0))            as verified_unclear_share,
        sum(iff(not_favorable_reason = 'SCOPE_LIMITED', state_population_share, 0))      as verified_scope_limited_share,
        sum(iff(base_evidence_class = 'UNKNOWN_OR_LOW_CONFIDENCE', state_population_share, 0)) as unknown_or_low_confidence_share,
        sum(iff(base_evidence_class = 'NOT_APPLICABLE', state_population_share, 0))      as not_applicable_share,
        sum(state_population_share)                                                      as total_population_share,
        min(iff(base_evidence_class = 'VERIFIED_FAVORABLE' and coded_status = 'SPECIFIED', numeric_value, null))
                                                                                         as most_restrictive_verified_limit,
        max(iff(base_evidence_class = 'VERIFIED_FAVORABLE', unit, null))                 as limit_unit,
        listagg(state_usps || ' ' || coalesce(coded_status, 'NO_EVIDENCE')
                || iff(numeric_value is not null, ' ' || numeric_value::varchar || coalesce(' ' || unit, ''), '')
                || ' ' || to_varchar(round(100 * state_population_share, 1), 'FM990.0') || '% ['
                || base_evidence_class || coalesce('/' || not_favorable_reason, '') || ']', '; ')
            within group (order by state_population_share desc, state_usps)              as state_status_detail,
        listagg(iff(base_evidence_class = 'UNKNOWN_OR_LOW_CONFIDENCE',
                    coalesce(evidence_id, state_usps || ':NO_EVIDENCE'), null), ', ')
            within group (order by state_usps)                                           as ineligible_evidence_ids,
        listagg(iff(base_evidence_class = 'UNKNOWN_OR_LOW_CONFIDENCE', state_usps, null), ', ')
            within group (order by state_usps)                                           as ineligible_states,
        listagg(distinct evidence_id, ', ') within group (order by evidence_id)          as evidence_ids
    from s
    group by 1, 2, 3, 4, 5
),

flagged as (
    select
        *,
        unknown_or_low_confidence_share <= {{ var('score_tolerance') }}                  as dimension_complete_flag,
        iff(market_mapping_method = 'MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES',
            verified_favorable_share > {{ var('score_tolerance') }}, true)              as dimension_applicable_flag,
        market_mapping_method = 'MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES'       as numeric_dimension_flag,
        iff(market_mapping_method = 'MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES'
                and verified_favorable_share > {{ var('score_tolerance') }}
                and most_restrictive_verified_limit is null, true, false)                as no_limit_stated_flag
    from agg
),

-- Numeric dimension: average-rank percentile among the markets where the limit applies and is verified.
numeric_values as (
    select
        market_id,
        mode,
        legal_dimension,
        iff(no_limit_stated_flag, 1e12, most_restrictive_verified_limit)                 as ranking_value
    from flagged
    where numeric_dimension_flag and dimension_complete_flag and dimension_applicable_flag
),

numeric_ranked as (
    select
        *,
        count(*) over (partition by mode, legal_dimension)                               as n_markets,
        rank() over (partition by mode, legal_dimension order by ranking_value asc)      as rank_asc,
        rank() over (partition by mode, legal_dimension order by ranking_value desc)     as rank_desc
    from numeric_values
),

numeric_scored as (
    select
        *,
        {{ phase7_average_rank('rank_asc', 'rank_desc', 'n_markets') }}                  as average_rank,
        {{ phase7_percentile('rank_asc', 'rank_desc', 'n_markets') }}                    as percentile_score
    from numeric_ranked
)

select
    f.market_id,
    f.mode,
    f.legal_dimension,
    f.regulatory_feature_id,
    f.market_mapping_method,
    iff(f.numeric_dimension_flag, 'PERCENTILE_AVERAGE_RANK', 'VERIFIED_FAVORABLE_POPULATION_SHARE') as score_method,
    f.state_count,
    f.verified_favorable_share,
    f.verified_unfavorable_share,
    f.verified_absence_share,
    f.verified_explicit_unfavorable_share,
    f.verified_unclear_share,
    f.verified_scope_limited_share,
    f.unknown_or_low_confidence_share,
    f.not_applicable_share,
    f.total_population_share,
    100 * (1 - f.unknown_or_low_confidence_share)                                        as evidence_coverage_pct,
    f.unknown_or_low_confidence_share > {{ var('score_tolerance') }}                     as low_confidence_flag,
    f.dimension_complete_flag,
    f.dimension_applicable_flag,
    f.numeric_dimension_flag,
    f.most_restrictive_verified_limit,
    f.limit_unit,
    f.no_limit_stated_flag,
    n.ranking_value,
    n.n_markets                                                                          as numeric_scored_market_count,
    n.average_rank,
    case
        when not f.dimension_complete_flag then null
        when f.numeric_dimension_flag then n.percentile_score
        else 100 * f.verified_favorable_share
    end                                                                                  as dimension_score,
    -- Human-readable decomposition of the number (Step 27).
    case
        when f.numeric_dimension_flag then
            f.legal_dimension || ': '
            || case
                   when not f.dimension_complete_flag then 'INCOMPLETE (unknown or LOW-confidence evidence for '
                        || to_varchar(round(100 * f.unknown_or_low_confidence_share, 1), 'FM990.0') || '% of population: '
                        || f.ineligible_states || ')'
                   when not f.dimension_applicable_flag then 'NOT APPLICABLE (no verified general PDD authorization in the market)'
                   when f.no_limit_stated_flag then 'no weight limit stated in the authorizing states'
                   else 'most restrictive verified limit ' || f.most_restrictive_verified_limit::varchar || ' ' || f.limit_unit
               end
            || '; limit applies to ' || to_varchar(round(100 * f.verified_favorable_share, 1), 'FM990.0')
            || '% of population, not applicable to ' || to_varchar(round(100 * f.not_applicable_share, 1), 'FM990.0') || '%'
        else
            f.legal_dimension || ': '
            || to_varchar(round(100 * f.verified_favorable_share, 1), 'FM990.0') || '% verified favorable; '
            || to_varchar(round(100 * f.verified_unfavorable_share, 1), 'FM990.0') || '% verified not favorable (absence '
            || to_varchar(round(100 * f.verified_absence_share, 1), 'FM990.0') || '%, explicit '
            || to_varchar(round(100 * f.verified_explicit_unfavorable_share, 1), 'FM990.0') || '%, unclear '
            || to_varchar(round(100 * f.verified_unclear_share, 1), 'FM990.0') || '%, scope-limited '
            || to_varchar(round(100 * f.verified_scope_limited_share, 1), 'FM990.0') || '%); '
            || to_varchar(round(100 * f.unknown_or_low_confidence_share, 1), 'FM990.0') || '% unknown or LOW confidence'
            || iff(f.dimension_complete_flag, '', ' (INCOMPLETE: ' || f.ineligible_states || ')')
    end                                                                                  as decomposition_text,
    f.state_status_detail,
    f.ineligible_evidence_ids,
    f.ineligible_states,
    f.evidence_ids,
    '{{ var("model_version") }}'                                                         as model_version,
    '{{ var("model_input_commit") }}'                                                    as model_input_commit
from flagged f
left join numeric_scored n
  on n.market_id = f.market_id and n.mode = f.mode and n.legal_dimension = f.legal_dimension
