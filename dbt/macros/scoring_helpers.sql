{#- Phase 7 scoring helpers (docs/readiness_model.md). -#}

{#- The active model features of a mode are exactly the feature columns of its Phase 6 mode mart
    (keys and qa_* excluded). assert_mode_marts_match_feature_contract already proves those columns
    equal the ACTIVE contract features, and assert_feature_scores_match_contract proves the scored set
    equals them again, so no feature can be added or dropped silently. -#}
{% macro phase7_feature_columns(mart) %}
    {%- if execute -%}
        {%- set out = [] -%}
        {%- for c in adapter.get_columns_in_relation(ref(mart)) -%}
            {%- set n = c.name | lower -%}
            {%- if n not in ['market_id', 'market_name'] and not n.startswith('qa_') -%}
                {%- do out.append(n) -%}
            {%- endif -%}
        {%- endfor -%}
        {{ return(out) }}
    {%- else -%}
        {{ return([]) }}
    {%- endif -%}
{% endmacro %}

{#- Untransformed value of a feature, kept next to the model value for traceability (Step 6).
    Only the LOG1P features differ; every other feature is used as productionized. -#}
{% macro phase7_raw_column(feature) %}
    {%- set raw = {
        'population_2025_log1p': 'population_2025',
        'pw_tract_density_log1p': 'population_weighted_tract_density',
        'enplanements_per_resident_log1p': 'enplanements_per_resident'
    } -%}
    {{ return(raw.get(feature, feature)) }}
{% endmacro %}

{#- Average-rank percentile on 0-100 (ties share the mean of the positions they occupy):
      average_rank = (rank_asc + n + 1 - rank_desc) / 2
      percentile   = 100 * (average_rank - 1) / (n - 1)
    Computed in FLOAT: Snowflake NUMBER division keeps only 6 decimals (1/3 = 0.333333), which would
    break exact reconciliation. -#}
{% macro phase7_average_rank(rank_asc, rank_desc, n) -%}
    (({{ rank_asc }} + {{ n }} + 1 - {{ rank_desc }})::float / 2)
{%- endmacro %}

{% macro phase7_percentile(rank_asc, rank_desc, n) -%}
    iff({{ n }} > 1, 100 * ({{ phase7_average_rank(rank_asc, rank_desc, n) }} - 1) / ({{ n }} - 1)::float, null)
{%- endmacro %}

{% macro phase7_c4() %}C4_REGULATORY_AND_AUTONOMY_READINESS{% endmacro %}
