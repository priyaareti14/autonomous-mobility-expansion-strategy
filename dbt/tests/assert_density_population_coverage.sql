-- D2 MISSINGNESS CONTRACT (A-029): the only market with missing tract population is New York
-- (35620), with exactly the 14 known Suffolk tracts, and their population is NOT imputed.
-- Every other market's tracts account for 100% of its ACS CBSA population.
select market_id, 'unexpected tract population gap' as issue, tracts_missing_population::varchar as detail
from {{ ref('int_market__population_weighted_density') }}
where (market_id <> '35620' and (tracts_missing_population <> 0 or known_gap_flag))
   or (market_id = '35620' and (tracts_missing_population <> 14 or not known_gap_flag))

union all
select market_id, 'tract population does not reconcile to ACS CBSA total', population_coverage_pct::varchar
from {{ ref('int_market__population_weighted_density') }}
where market_id <> '35620' and abs(1 - population_coverage_pct) > 1e-9

union all
-- Not imputed: New York's tract population stays short of its CBSA total by roughly the size of the
-- 14 tracts (77,579 people in ACS 2018-2022). Imputation would close the gap; a gap below 50,000
-- (well under the tracts' size) therefore fails.
select market_id, 'New York coverage implies imputation', population_coverage_pct::varchar
from {{ ref('int_market__population_weighted_density') }}
where market_id = '35620' and acs_cbsa_total_population - population_used < 50000

union all
select market_id, 'zero-land tract holds population', zero_land_tracts_with_population::varchar
from {{ ref('int_market__population_weighted_density') }}
where zero_land_tracts_with_population > 0
