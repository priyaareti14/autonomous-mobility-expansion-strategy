-- CONTRACT (A-006, verified in Phase 3): for the 35 markets, the counties in PEP (BRG_MARKET_COUNTY)
-- are exactly the counties the July 2023 delineation assigns to those CBSAs.
-- Returns counties present on one side only.
with bridge as (
    select market_id, county_fips from {{ ref('brg_market_county') }}
),
official as (
    select x.cbsa_code as market_id, x.county_fips
    from {{ ref('int_geo__county_cbsa_2023') }} x
    inner join {{ ref('dim_market') }} d on d.market_id = x.cbsa_code
)
(select 'bridge only' as side, * from bridge minus select 'bridge only', * from official)
union all
(select 'delineation only' as side, * from official minus select 'delineation only', * from bridge)
