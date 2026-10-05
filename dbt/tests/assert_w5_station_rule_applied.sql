-- W5 RULE CONTRACT: every selected station satisfies the documented rule, and no better candidate
-- was skipped. Constants come from dbt_project.yml vars.
with sel as (
    select s.*, q.is_core_qualifying, q.is_snow_qualifying, q.is_plcd, q.has_hourly_wind_normals
    from {{ ref('int_weather__market_station_selection') }} s
    left join {{ ref('int_weather__station_qualification') }} q on q.station_id = s.station_id
)

select market_id, station_role, 'general station not core-qualifying' as issue
from sel where station_role = 'GENERAL_CLIMATE' and not coalesce(is_core_qualifying, false)

union all
select market_id, station_role, 'PLCD rule used but station not PLCD (HOMR) or beyond cap'
from sel where selection_rule like 'PLCD_WITHIN_%'
  and (not is_plcd or distance_km > {{ var('w5_plcd_max_km') }})

union all
select market_id, station_role, 'fallback used although a PLCD candidate existed within the cap'
from sel where selection_rule = 'NEAREST_QUALIFYING_ANY_NETWORK' and plcd_candidates_within_cap > 0

union all
select market_id, station_role, 'PLCD candidate existed but rule did not use it'
from sel where station_role = 'GENERAL_CLIMATE' and plcd_candidates_within_cap > 0
  and selection_rule not like 'PLCD_WITHIN_%'

union all
select market_id, station_role, 'station type label disagrees with the HOMR class'
from sel where station_type <> iff(coalesce(is_plcd, false), 'PLCD', 'NON_PLCD')

union all
select market_id, station_role, 'snow station not snow-qualifying'
from sel where station_role = 'SNOW' and station_id is not null and not coalesce(is_snow_qualifying, false)

union all
select market_id, station_role, 'snow fallback beyond cap'
from sel where station_role = 'SNOW' and selection_rule like 'SNOW_FALLBACK_%'
  and distance_km > {{ var('w5_snow_fallback_max_km') }}

union all
select market_id, station_role, 'snow value absent but a qualifying snow station existed within the cap'
from sel where station_role = 'SNOW' and selection_rule = 'SOURCE_NOT_PUBLISHED' and snow_candidates_within_cap > 0

union all
select market_id, station_role, 'wind station has no hourly wind normals'
from sel where station_role = 'WIND' and not coalesce(has_hourly_wind_normals, false)

union all
select market_id, null, 'market does not have exactly one station per role'
from sel group by market_id having count(*) <> 3 or count(distinct station_role) <> 3
