-- CONTRACT: pinned source editions stay pinned. Every NASR row is the 2026-09-03 edition, every
-- hourly-wind station has exactly 8,760 hours, and every staged source carries the vintage
-- registered in Phase 3.
select 'NASR edition' as check_name, airport_code as detail
from {{ ref('stg_faa__nasr_apt_base') }}
where nasr_effective_date <> '2026-09-03'::date or nasr_effective_date is null

union all
select 'hourly wind hours per station', station_id || ': ' || count(*)
from {{ ref('fct_station_hourly_wind_normals') }}
group by station_id
having count(*) <> 8760

union all
select 'vintage', 'stg_census__acs5_2024_tract_b01003: ' || source_vintage
from {{ ref('stg_census__acs5_2024_tract_b01003') }}
where source_vintage <> 'ACS5-2024'
group by source_vintage

union all
select 'vintage', 'stg_bls__oews_may2025_msa: ' || source_vintage
from {{ ref('stg_bls__oews_may2025_msa') }}
where source_vintage <> 'May2025'
group by source_vintage

union all
select 'vintage', 'stg_census__cbp_2023_msa: ' || source_vintage
from {{ ref('stg_census__cbp_2023_msa') }}
where source_vintage <> '2023'
group by source_vintage
