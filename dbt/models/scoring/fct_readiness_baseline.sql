-- FCT_READINESS_BASELINE: baseline readiness score, BASELINE rank and score decomposition.
-- Grain: one row per market x mode (35 x 3 = 105). Scores are MODE-SPECIFIC: never compare or combine
-- them across modes (docs/readiness_model.md §10).
--   baseline_readiness_score = sum of component contributions, 0-100, ONLY if every component is
--                              complete; NULL when C4 is incomplete (no rank either)
--   baseline_rank            = rank among the complete markets of the mode (1 = highest score);
--                              ties (equal to 6 decimals) share a rank (standard competition ranking)
--   non_regulatory_score     = equal-weight mean of the non-C4 components: a DIAGNOSTIC for every market,
--                              not a readiness score and not ranked
-- A baseline rank is not a recommendation: Phase 8 tests its robustness first.
with comp as (
    select * from {{ ref('fct_component_scores') }}
),

feat as (
    select * from {{ ref('fct_feature_scores') }}
),

market_level as (
    select
        market_id,
        mode,
        max(active_component_count)                                                         as active_component_count,
        booland_agg(component_complete_flag)                                                as score_complete_flag,
        sum(component_contribution)                                                         as component_contribution_sum,
        sum(iff(component <> '{{ phase7_c4() }}', component_score * non_regulatory_component_weight, 0)) as non_regulatory_score,
        sum(component_weight)                                                               as component_weight_sum,
        max(iff(component = '{{ phase7_c4() }}', component_score, null))                    as c4_score_verified,
        max(iff(component = '{{ phase7_c4() }}', evidence_coverage_pct, null))              as c4_evidence_coverage_pct,
        booland_agg(iff(component = '{{ phase7_c4() }}', component_complete_flag, true))    as c4_complete_flag,
        listagg(iff(component_complete_flag, null, component), ', ') within group (order by component) as incomplete_components
    from comp
    group by 1, 2
),

c4_detail as (
    select
        market_id,
        mode,
        listagg(decomposition_text, ' | ') within group (order by legal_dimension)          as c4_decomposition,
        listagg(iff(dimension_complete_flag, null, legal_dimension || ' (' || ineligible_evidence_ids || ')'), '; ')
            within group (order by legal_dimension)                                         as c4_incomplete_reason,
        max(unknown_or_low_confidence_share)                                                as c4_max_unknown_share
    from {{ ref('fct_regulatory_dimension_scores') }}
    group by 1, 2
),

-- The set of states whose evidence keeps a market's C4 incomplete: normalized, de-duplicated BEFORE
-- aggregation, then listed alphabetically ("NJ, NY"). NULL when every state is verified.
c4_unverified_state_set as (
    select distinct market_id, mode, upper(trim(state_usps)) as state_usps
    from {{ ref('int_regulatory__market_state_evidence') }}
    where base_evidence_class = 'UNKNOWN_OR_LOW_CONFIDENCE'
),

c4_unverified as (
    select
        market_id,
        mode,
        listagg(state_usps, ', ') within group (order by state_usps)                       as c4_unverified_states
    from c4_unverified_state_set
    group by 1, 2
),

-- Feature-level decomposition over the inputs that carry a score in the market's calculation.
feat_ranked as (
    select
        market_id,
        mode,
        feature_name,
        feature_score,
        contribution_to_overall,
        points_below_maximum,
        row_number() over (partition by market_id, mode order by feature_score desc, feature_id)       as strongest_rn,
        row_number() over (partition by market_id, mode order by feature_score asc, feature_id)        as weakest_rn,
        row_number() over (partition by market_id, mode order by contribution_to_overall desc nulls last, feature_id) as contributor_rn,
        row_number() over (partition by market_id, mode order by points_below_maximum desc nulls last, feature_id)   as constraint_rn
    from feat
    where feature_score is not null and (in_base_flag or component <> '{{ phase7_c4() }}')
),

feat_summary as (
    select
        market_id,
        mode,
        max(iff(strongest_rn = 1, feature_name || ' (' || to_varchar(round(feature_score, 1), 'FM990.0') || ')', null)) as strongest_feature,
        max(iff(weakest_rn = 1, feature_name || ' (' || to_varchar(round(feature_score, 1), 'FM990.0') || ')', null))   as weakest_feature,
        listagg(iff(contributor_rn <= 3 and contribution_to_overall is not null,
                    feature_name || ' +' || to_varchar(round(contribution_to_overall, 2), 'FM990.00') || ' pts', null), '; ')
            within group (order by contributor_rn)                                          as top_positive_contributors,
        listagg(iff(constraint_rn <= 3 and points_below_maximum is not null,
                    feature_name || ' -' || to_varchar(round(points_below_maximum, 2), 'FM990.00') || ' pts', null), '; ')
            within group (order by constraint_rn)                                           as top_constraints
    from feat_ranked
    group by 1, 2
),

scored as (
    select
        m.*,
        iff(m.score_complete_flag, m.component_contribution_sum, null)                      as baseline_readiness_score
    from market_level m
),

ranked as (
    select
        s.*,
        iff(baseline_readiness_score is null, null,
            rank() over (partition by mode, baseline_readiness_score is null
                         order by round(baseline_readiness_score, 6) desc))                 as baseline_rank,
        iff(baseline_readiness_score is null, null,
            count(*) over (partition by mode, round(baseline_readiness_score, 6)) > 1)      as baseline_rank_tied_flag,
        iff(baseline_readiness_score is null, null,
            lag(baseline_readiness_score) over (partition by mode, baseline_readiness_score is null
                                                order by baseline_readiness_score desc, market_id)
            - baseline_readiness_score)                                                     as score_gap_to_preceding
    from scored s
)

select
    r.market_id,
    d.cbsa_name                                                                             as market_name,
    r.mode,
    r.baseline_readiness_score,
    r.baseline_rank,
    r.baseline_rank_tied_flag,
    r.score_gap_to_preceding,
    r.score_complete_flag,
    r.baseline_rank is not null                                                             as rank_complete_flag,
    r.non_regulatory_score,
    r.c4_score_verified,
    r.c4_evidence_coverage_pct,
    r.c4_complete_flag,
    c.c4_max_unknown_share,
    c.c4_incomplete_reason,
    u.c4_unverified_states,
    c.c4_decomposition,
    r.incomplete_components,
    r.active_component_count,
    r.component_weight_sum,
    fs.strongest_feature,
    fs.weakest_feature,
    fs.top_positive_contributors,
    fs.top_constraints,
    '{{ var("model_version") }}'                                                            as model_version,
    '{{ var("model_input_commit") }}'                                                       as model_input_commit
from ranked r
join {{ ref('dim_market') }} d on d.market_id = r.market_id
left join c4_detail c on c.market_id = r.market_id and c.mode = r.mode
left join c4_unverified u on u.market_id = r.market_id and u.mode = r.mode
left join feat_summary fs on fs.market_id = r.market_id and fs.mode = r.mode
