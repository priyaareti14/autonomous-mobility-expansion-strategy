-- DIM_FEATURE: machine-readable feature dictionary for the pre-regulatory production feature layer.
-- Grain: one row per feature x mode (feature_id + mode is unique).
-- Source of truth: seeds/feature_contract.csv, generated from the frozen Phase 5 decision table by
-- scripts/build_feature_contract.py. Holds definitions only: no weights, scores or rankings.
-- production_status: ACTIVE (a column of the mode mart), DIAGNOSTIC (sensitivity only), DEFERRED
-- (direction or methodology unresolved), DROPPED (explicitly removed in Phase 6 or kept for the record).
select
    feature_id,
    feature_name,
    mode,
    component,
    unit,
    direction,
    direction_rationale,
    transformation,
    source_id,
    source_vintage                         as vintage,
    description,
    known_limitation                       as limitation,
    missingness_policy,
    lineage_model,
    grain,
    phase5_feature_name,
    phase5_status,
    production_status,
    active_pre_regulation_flag
from {{ ref('feature_contract') }}
