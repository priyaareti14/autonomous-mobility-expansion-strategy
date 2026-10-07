-- PBI_DIM_FEATURE: every scored model input, per mode. Grain: one row per mode x input (feature_key).
-- 30 active contract features + 7 regulatory dimensions = 37 rows. feature_key = mode || '|' || feature_id,
-- because feature ids repeat across modes (e.g. PF01).
-- One row per input: attributes are constant per mode x input, except the weight-limit unit, which is NULL
-- in markets where the limit does not apply (hence max()).
with inputs as (
    select mode, feature_id, max(feature_name) as feature_name, max(component) as component,
           max(direction) as direction, max(transformation) as transformation, max(unit) as unit,
           max(score_method) as score_method
    from {{ ref('fct_feature_scores') }}
    group by mode, feature_id
)

select
    i.mode || '|' || i.feature_id                                           as feature_key,
    i.mode,
    i.feature_id,
    i.feature_name,
    initcap(replace(i.feature_name, '_', ' '))                              as feature_label,
    i.component,
    i.direction,
    i.transformation,
    i.unit,
    i.score_method,
    coalesce(f.description, r.business_interpretation)                      as feature_description,
    coalesce(f.vintage, 'Regulatory evidence as of 2026-10-05')             as source_vintage,
    coalesce(f.limitation, r.known_limitation)                              as known_limitation,
    iff(i.component = 'C4_REGULATORY_AND_AUTONOMY_READINESS', true, false)  as regulatory_input_flag
from inputs i
left join {{ ref('dim_feature') }} f on f.mode = i.mode and f.feature_id = i.feature_id
left join {{ ref('pbi_regulatory_dimension_labels') }} r on r.mode = i.mode and r.feature_id = i.feature_id
