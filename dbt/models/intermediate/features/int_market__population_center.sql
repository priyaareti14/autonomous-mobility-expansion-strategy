-- Population-weighted (PW) centre of each market: the reference point for the W5 station rule and
-- the A4 airport diagnostic.
-- Grain: one row per market (35).
-- Formula: PW latitude = sum(tract internal-point latitude x tract population) / sum(tract population),
-- and the same for longitude, over tracts with an ACS 2020-2024 population > 0. The 14 Suffolk
-- County tracts without ACS records (A-029) carry no weight; nothing is imputed.
-- A weighted mean of coordinates is accurate at metro scale (tens of km); it is not a geodesic centroid.
select
    market_id,
    sum(internal_point_latitude * total_population) / sum(total_population)   as pw_center_latitude,
    sum(internal_point_longitude * total_population) / sum(total_population)  as pw_center_longitude,
    count(*)                                                                    as tracts_weighted,
    sum(total_population)                                                       as population_weighted
from {{ ref('fct_tract_population_land') }}
where has_acs_population
  and total_population > 0
group by market_id
