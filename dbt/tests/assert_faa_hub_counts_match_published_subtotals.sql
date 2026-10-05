-- RECONCILIATION: the FAA sheet's own summary rows (rejected at ingestion, kept in
-- META.INGESTION_REJECTED_ROWS) publish these subtotals: Large 30, Medium 35, Small 79,
-- Nonhub 258 (= 402 primary) and 114 nonprimary commercial-service airports, 516 in total.
-- The airport-level fact must reproduce them exactly.
with actual as (
    select coalesce(hub_type_code, 'NONPRIMARY') as hub_group, count(*) as airports
    from {{ ref('fct_airport_enplanements') }}
    group by 1
),
published as (
    select * from (values ('L', 30), ('M', 35), ('S', 79), ('N', 258), ('NONPRIMARY', 114))
        as p(hub_group, airports)
)
select coalesce(a.hub_group, p.hub_group) as hub_group, a.airports as actual, p.airports as published
from actual a
full outer join published p on p.hub_group = a.hub_group
where a.airports is distinct from p.airports
