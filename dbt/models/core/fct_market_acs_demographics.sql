-- FCT_MARKET_ACS_DEMOGRAPHICS: catalogued ACS 5-year 2020-2024 measures for the 35 markets.
-- Grain: one row per market x ACS period (one period: ACS5-2024), so 35 rows.
-- Units: persons, households, housing units, vehicles, USD (2024 inflation-adjusted) and minutes,
-- as named in each column. Every estimate keeps its margin of error and special-code flags.
-- Transformation: market-universe restriction only. Values are the published CBSA estimates:
-- no shares, ratios or per-capita values are derived here (that is Phase 5/6 feature work).
-- Limitation: the 2020-2024 window includes pandemic years (A-018).
select
    a.cbsa_code as market_id,
    a.*
        exclude (cbsa_code)
from {{ ref('int_acs__cbsa_measures') }} a
inner join {{ ref('dim_market') }} d
    on d.market_id = a.cbsa_code
