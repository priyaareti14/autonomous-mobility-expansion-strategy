-- FCT_FEATURE_SCORES: directionally aligned feature scores and their weighted contributions.
-- Grain: one row per market x mode x model input (35 markets x (30 active features + 7 regulatory
-- dimensions) = 1,295 rows).
--
-- Non-regulatory features (C1, C2, C3, C5): read from the Phase 6 mode marts (the frozen feature
-- layer), raw value from INT_MARKET__PRODUCTION_FEATURES. Score = average-rank percentile of the
-- transformed value across the 35 markets, 0-100; reversed (100 - p) for LOWER_IS_MORE_FAVORABLE.
-- Regulatory dimensions (C4): from FCT_REGULATORY_DIMENSION_SCORES (verified favorable population
-- share, or the percentile of the verified weight limit).
--
-- Weights (baseline_v1): equal within a component over its inputs IN the base calculation:
--   feature_weight            = 1 / (number of base inputs of the market's component)
--   weighted_contribution     = feature_score * feature_weight      (sums to the component score)
--   component_weight          = 1 / (number of active components of the mode)
--   contribution_to_overall   = weighted_contribution * component_weight (sums to the overall score)
-- A C4 input is in the base only when the market's C4 is complete and the dimension applies.
-- If C4 is incomplete, no C4 input carries a weight and no input carries an overall contribution.
-- depends_on: {{ ref('mart_robotaxi_features') }}
-- depends_on: {{ ref('mart_sidewalk_delivery_features') }}
-- depends_on: {{ ref('mart_drone_delivery_features') }}
-- depends_on: {{ ref('int_market__production_features') }}
{% set marts = [
    ('ROBOTAXI', 'mart_robotaxi_features'),
    ('SIDEWALK_DELIVERY', 'mart_sidewalk_delivery_features'),
    ('DRONE_DELIVERY', 'mart_drone_delivery_features')
] %}
with feature_values as (
{%- set parts = [] %}
{%- for mode, mart in marts %}
    {%- for col in phase7_feature_columns(mart) %}
        {%- do parts.append(
            "select m.market_id, '" ~ mode ~ "' as mode, '" ~ col ~ "' as feature_name, "
            ~ "p." ~ phase7_raw_column(col) ~ "::float as raw_value, m." ~ col ~ "::float as transformed_value "
            ~ "from " ~ ref(mart) ~ " m join " ~ ref('int_market__production_features') ~ " p on p.market_id = m.market_id") %}
    {%- endfor %}
{%- endfor %}
{%- if parts %}
    {{ parts | join('\n    union all\n    ') }}
{%- else %}
    select null::varchar as market_id, null::varchar as mode, null::varchar as feature_name,
           null::float as raw_value, null::float as transformed_value
    where false
{%- endif %}
),

contract as (
    select feature_id, feature_name, mode, component, direction, transformation, unit, vintage as source_vintage
    from {{ ref('dim_feature') }}
    where production_status = 'ACTIVE'
),

ranked as (
    select
        v.market_id,
        v.mode,
        c.feature_id,
        v.feature_name,
        c.component,
        v.raw_value,
        v.transformed_value,
        c.direction,
        c.transformation,
        c.unit,
        c.source_vintage,
        count(v.transformed_value) over (partition by v.mode, c.feature_id)                       as n_markets,
        rank() over (partition by v.mode, c.feature_id order by v.transformed_value asc)          as rank_asc,
        rank() over (partition by v.mode, c.feature_id order by v.transformed_value desc)         as rank_desc
    from feature_values v
    join contract c on c.mode = v.mode and c.feature_name = v.feature_name
),

non_regulatory as (
    select
        market_id,
        mode,
        feature_id,
        feature_name,
        component,
        raw_value,
        transformed_value,
        direction,
        transformation,
        unit,
        source_vintage,
        'PERCENTILE_AVERAGE_RANK'                                                                  as score_method,
        n_markets,
        {{ phase7_average_rank('rank_asc', 'rank_desc', 'n_markets') }}                            as average_rank,
        {{ phase7_percentile('rank_asc', 'rank_desc', 'n_markets') }}                              as percentile_ascending,
        case direction
            when 'HIGHER_IS_MORE_FAVORABLE' then percentile_ascending
            when 'LOWER_IS_MORE_FAVORABLE'  then 100 - percentile_ascending
        end                                                                                        as feature_score,
        n_markets + 2 - rank_asc - rank_desc                                                       as tied_market_count,
        true                                                                                       as input_applicable_flag,
        true                                                                                       as input_complete_flag
    from ranked
),

regulatory as (
    select
        market_id,
        mode,
        regulatory_feature_id                                                                      as feature_id,
        lower(legal_dimension)                                                                     as feature_name,
        '{{ phase7_c4() }}'                                                                        as component,
        iff(numeric_dimension_flag, most_restrictive_verified_limit, verified_favorable_share)     as raw_value,
        iff(numeric_dimension_flag, ranking_value, 100 * verified_favorable_share)                 as transformed_value,
        iff(numeric_dimension_flag, 'HIGHER_LIMIT_MORE_FAVORABLE', 'HIGHER_VERIFIED_FAVORABLE_SHARE_MORE_FAVORABLE') as direction,
        iff(numeric_dimension_flag, 'MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES', 'POPULATION_SHARE_BY_STATUS') as transformation,
        iff(numeric_dimension_flag, limit_unit, 'share of market population (0-1)')                as unit,
        'Evidence as of 2026-10-05 (Phase 6.5b)'                                                   as source_vintage,
        score_method,
        numeric_scored_market_count                                                                as n_markets,
        average_rank,
        null::float                                                                                as percentile_ascending,
        dimension_score                                                                            as feature_score,
        null::number                                                                               as tied_market_count,
        dimension_applicable_flag                                                                  as input_applicable_flag,
        dimension_complete_flag                                                                    as input_complete_flag
    from {{ ref('fct_regulatory_dimension_scores') }}
),

all_inputs as (
    select * from non_regulatory
    union all
    select * from regulatory
),

c4_status as (
    select market_id, mode, booland_agg(dimension_complete_flag) as c4_complete_flag
    from {{ ref('fct_regulatory_dimension_scores') }}
    group by 1, 2
),

in_base as (
    select
        a.*,
        s.c4_complete_flag,
        iff(a.component = '{{ phase7_c4() }}', s.c4_complete_flag and a.input_applicable_flag, true) as in_base_flag
    from all_inputs a
    join c4_status s on s.market_id = a.market_id and s.mode = a.mode
),

weighted as (
    select
        *,
        count_if(in_base_flag) over (partition by market_id, mode, component)                     as component_base_input_count,
        count(distinct component) over (partition by market_id, mode)                              as active_component_count
    from in_base
)

select
    market_id,
    mode,
    feature_id,
    feature_name,
    component,
    raw_value,
    transformed_value,
    direction,
    transformation,
    unit,
    source_vintage,
    score_method,
    n_markets,
    average_rank,
    percentile_ascending,
    feature_score,
    tied_market_count,
    input_applicable_flag,
    input_complete_flag,
    in_base_flag,
    iff(in_base_flag, 1::float / component_base_input_count, null)                                as feature_weight,
    feature_score * feature_weight                                                                 as weighted_feature_contribution,
    active_component_count,
    1::float / active_component_count                                                              as component_weight,
    iff(c4_complete_flag, weighted_feature_contribution * component_weight, null)                  as contribution_to_overall,
    iff(c4_complete_flag, (100 - feature_score) * feature_weight * component_weight, null)         as points_below_maximum,
    '{{ var("model_version") }}'                                                                   as model_version,
    '{{ var("model_input_commit") }}'                                                              as model_input_commit
from weighted
