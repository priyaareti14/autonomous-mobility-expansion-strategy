-- A1 EDGE CASES (approved in Phase 5, re-proven on the hardened county-FIPS key).
-- Airports are assigned by the official county containing their reference point, never by the
-- city they "serve". Expected market (null = outside every frozen market under A1):
--   BWI Baltimore 12580 (Anne Arundel Co.), not Washington
--   DCA Washington 47900 (Arlington Co., VA)
--   ONT Riverside 40140 (San Bernardino Co.), not Los Angeles
--   SNA Los Angeles 31080 (Orange Co. is an official county of the LA MSA)
--   MHT outside (Hillsborough Co., NH: Manchester-Nashua MSA), not Boston
--   ORH outside (Worcester Co., MA: Worcester MSA), not Boston
--   SJC outside (Santa Clara Co.: San Jose MSA, outside the universe), not San Francisco
--   PVD outside (Kent Co., RI: Providence MSA)
-- Plus: every airport is counted for at most one market, and market totals reconcile to airports.
with expected as (
    select * from (values
        ('BWI', '12580'), ('DCA', '47900'), ('ONT', '40140'), ('SNA', '31080'),
        ('MHT', null), ('ORH', null), ('SJC', null), ('PVD', null)
    ) as v (airport_code, expected_market_id)
),

a as (
    select * from {{ ref('int_airports__airport_market_assignment') }}
)

select 'edge case' as issue, e.airport_code, e.expected_market_id, a.a1_market_id::varchar as actual
from expected e
left join a on a.airport_code = e.airport_code
where a.airport_code is null
   or not equal_null(a.a1_market_id, e.expected_market_id)

union all

select 'airport assigned more than once', airport_code, null, count(*)::varchar
from a
group by airport_code
having count(*) > 1

union all

select 'market enplanements do not reconcile to assigned airports', null, null,
       (select sum(enplanements_cy2025) from {{ ref('int_market__airport_activity') }})::varchar
where (select sum(enplanements_cy2025) from {{ ref('int_market__airport_activity') }})
   <> (select sum(enplanements_cy2025) from a where a1_market_id is not null)
