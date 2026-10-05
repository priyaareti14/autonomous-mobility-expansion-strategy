-- FCT_MARKET_OCCUPATION_WAGES: BLS OEWS May 2025 employment and wages for the 35 markets.
-- Grain: one row per market x SOC occupation code (every published occupation and group level).
-- Units: persons (employment), USD (hourly and annual wages), percent (PRSE).
-- Transformation: market-universe restriction only. BLS markers stay in *_marker columns.
-- Limitations (A-017, A-026): excludes the self-employed (gig drivers). Many occupations are not
-- published for every metro: 53-3054 Taxi Drivers appears for only 11 of 393 metros. A missing
-- occupation row or a null wage is NOT a low wage.
select
    o.cbsa_code as market_id,
    o.*
        exclude (cbsa_code, ingest_run_id, ingested_at, source_id, source_file, source_file_sha256, source_row_number)
from {{ ref('stg_bls__oews_may2025_msa') }} o
inner join {{ ref('dim_market') }} d
    on d.market_id = o.cbsa_code
