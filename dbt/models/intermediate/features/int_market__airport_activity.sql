-- A1 MARKET-EMBEDDED AIRPORT ACTIVITY.
-- Grain: one row per market (35).
-- enplanements_per_resident = CY2025 enplanements at commercial-service airports physically inside the
-- market's official counties (int_airports__airport_market_assignment.a1_market_id) / PEP 2025 population.
-- Connecting-hub traffic is included and cannot be separated (A-010).
-- A4 columns are a labelled sensitivity diagnostic, not a production feature.
with a as (
    select * from {{ ref('int_airports__airport_market_assignment') }}
),

a1 as (
    select
        a1_market_id                                                             as market_id,
        count(*)                                                                 as commercial_airport_count,
        count_if(service_level_code = 'P')                                       as primary_airport_count,
        count_if(hub_type_code in ('L', 'M'))                                    as large_medium_hub_count,
        sum(enplanements_cy2025)                                                 as enplanements_cy2025,
        listagg(airport_code, ';') within group (order by airport_code)          as included_airport_codes
    from a
    where a1_market_id is not null
    group by a1_market_id
),

a4 as (
    select
        a4_market_id_diagnostic                                                  as market_id,
        sum(enplanements_cy2025)                                                 as a4_enplanements_cy2025_diagnostic,
        listagg(airport_code, ';') within group (order by airport_code)          as a4_airport_codes_diagnostic
    from a
    where a4_market_id_diagnostic is not null
    group by a4_market_id_diagnostic
)

select
    d.market_id,
    d.population_2025,
    coalesce(a1.commercial_airport_count, 0)                                     as commercial_airport_count,
    coalesce(a1.primary_airport_count, 0)                                        as primary_airport_count,
    coalesce(a1.large_medium_hub_count, 0)                                       as large_medium_hub_count,
    coalesce(a1.enplanements_cy2025, 0)                                          as enplanements_cy2025,
    a1.included_airport_codes,
    coalesce(a1.enplanements_cy2025, 0) / d.population_2025                      as enplanements_per_resident,
    a4.a4_enplanements_cy2025_diagnostic,
    a4.a4_airport_codes_diagnostic,
    a4.a4_enplanements_cy2025_diagnostic / d.population_2025                     as a4_enplanements_per_resident_diagnostic,
    'FAA CY2025 / PEP V2025'                                                     as airport_vintage
from {{ ref('dim_market') }} d
left join a1 on a1.market_id = d.market_id
left join a4 on a4.market_id = d.market_id
