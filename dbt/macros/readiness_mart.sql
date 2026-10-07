{#- Wide per-mode baseline readiness mart: one row per market (35), component scores and contributions
    pivoted next to the score, rank, coverage and decomposition. Robotaxi has no C5 column: the component
    is structurally absent (A-039), not zero. -#}
{% macro readiness_mart(mode, components) %}
{%- set labels = {
    'C1_DEMAND_AND_MARKET_OPPORTUNITY': 'c1_demand',
    'C2_OPERATING_ENVIRONMENT': 'c2_operating_environment',
    'C3_ECONOMIC_ATTRACTIVENESS': 'c3_economic_attractiveness',
    'C4_REGULATORY_AND_AUTONOMY_READINESS': 'c4_regulatory',
    'C5_INFRASTRUCTURE_AND_MODE_FIT': 'c5_infrastructure_mode_fit'
} -%}
with b as (
    select * from {{ ref('fct_readiness_baseline') }} where mode = '{{ mode }}'
),

c as (
    select
        market_id
    {%- for comp in components %},
        max(iff(component = '{{ comp }}', component_score, null))        as {{ labels[comp] }}_score,
        max(iff(component = '{{ comp }}', component_contribution, null)) as {{ labels[comp] }}_contribution
    {%- endfor %}
    from {{ ref('fct_component_scores') }}
    where mode = '{{ mode }}'
    group by market_id
)

select
    b.market_id,
    b.market_name,
    b.baseline_readiness_score,
    b.baseline_rank,
    b.baseline_rank_tied_flag,
    b.score_gap_to_preceding,
    b.score_complete_flag,
    b.rank_complete_flag,
    {%- for comp in components %}
    c.{{ labels[comp] }}_score,
    c.{{ labels[comp] }}_contribution,
    {%- endfor %}
    b.non_regulatory_score,
    b.c4_score_verified,
    b.c4_evidence_coverage_pct,
    b.c4_complete_flag,
    b.c4_incomplete_reason,
    b.c4_unverified_states,
    b.c4_decomposition,
    b.strongest_feature,
    b.weakest_feature,
    b.top_positive_contributors,
    b.top_constraints,
    b.model_version,
    b.model_input_commit
from b
join c on c.market_id = b.market_id
{% endmacro %}
