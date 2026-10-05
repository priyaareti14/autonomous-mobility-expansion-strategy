"""Catalog of Phase 5 candidate measures.

Three kinds of candidate are audited:
  * MART: published, CBSA-native measures in ANALYTICS.MART_MARKET_FEATURE_BASE.
  * INTENSITY: exploratory ratios of mart measures (per capita, shares). They
    are computed in memory for the scale-vs-intensity review and are NOT
    published to Snowflake.
  * MAPPING: candidate market measures produced by the mapping-method
    evaluation (density, weather, airports, built environment). Also local only.

Expected direction: a candidate gets HYPOTHESIS:<direction> only where a direction
was stated in the Phase 1 hypotheses. Otherwise it is UNRESOLVED. No direction is
final and none implies a weight.
Components: C1 Demand & Market Opportunity, C2 Operating Environment, C3 Economic
Attractiveness, C4 Regulatory & Autonomy Readiness, C5 Infrastructure & Mode Fit.
Modes: RT robotaxi, SW sidewalk robot, DR drone.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Candidate:
    feature_id: str
    column: str
    meaning: str
    source: str
    vintage: str
    component: str
    modes: tuple[str, ...]
    unit: str
    kind: str                     # OBSERVED / DERIVED
    scale_type: str               # ABSOLUTE / INTENSITY / STRUCTURAL
    origin: str                   # MART / INTENSITY / MAPPING
    direction: str = "UNRESOLVED"
    limitation: str = ""
    formula: tuple = field(default=())   # (numerator, denominator, multiplier) for INTENSITY


U = "UNRESOLVED"
ACS = ("S-03 ACS 5-yr", "2020-2024")
CBP = ("S-08 CBP", "2023")
OEWS = ("S-09 OEWS", "May 2025")

MART_CANDIDATES: list[Candidate] = [
    Candidate("M01", "population_2025", "Resident population, July 1 2025", "S-01 PEP", "V2025", "C1",
              ("RT", "SW", "DR"), "persons", "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "Estimate, not a count"),
    Candidate("M02", "acs_total_population", "ACS total population (B01003)", *ACS, "C1", ("RT", "SW", "DR"),
              "persons", "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "Pooled 2020-2024; duplicates M01 conceptually"),
    Candidate("M03", "total_households", "Households (B11001)", *ACS, "C1", ("DR", "SW"), "households",
              "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND", ""),
    Candidate("M04", "median_household_income_usd", "Median household income, 2024 USD (B19013)", *ACS, "C3",
              ("RT", "SW", "DR"), "USD", "OBSERVED", "INTENSITY", "MART", "HYPOTHESIS:HIGHER_MORE_ABILITY_TO_PAY",
              "Not cost-of-living adjusted (BEA RPP deferred)"),
    Candidate("M05", "workers_16_plus", "Workers 16+ (B08301)", *ACS, "C1", ("RT",), "persons", "OBSERVED",
              "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND", "Pandemic-era WFH (A-018)"),
    Candidate("M06", "workers_drove_alone", "Workers who drove alone", *ACS, "C1", ("RT",), "persons",
              "OBSERVED", "ABSOLUTE", "MART", U, "Direction ambiguous: car dependence vs. substitutable trips"),
    Candidate("M07", "workers_public_transportation", "Workers commuting by public transport", *ACS, "C1",
              ("RT",), "persons", "OBSERVED", "ABSOLUTE", "MART", U, "Complement vs. substitute (F07)"),
    Candidate("M08", "workers_taxi_or_ride_hailing", "Workers commuting by taxi or ride-hailing", *ACS, "C1",
              ("RT",), "persons", "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "Small counts, large MOE; commute trips only"),
    Candidate("M09", "workers_bicycle", "Workers commuting by bicycle", *ACS, "C5", ("SW",), "persons",
              "OBSERVED", "ABSOLUTE", "MART", U, "Small counts"),
    Candidate("M10", "workers_walked", "Workers who walked to work", *ACS, "C5", ("SW",), "persons",
              "OBSERVED", "ABSOLUTE", "MART", U, "Small counts"),
    Candidate("M11", "workers_worked_from_home", "Workers who worked from home", *ACS, "C1", ("SW", "DR"),
              "persons", "OBSERVED", "ABSOLUTE", "MART", U, "Pandemic-era inflation (A-018)"),
    Candidate("M12", "mean_travel_time_minutes", "Mean travel time to work (S0801)", *ACS, "C1", ("RT",),
              "minutes", "OBSERVED", "INTENSITY", "MART", U, "Demand vs. congestion ambiguity (F08)"),
    Candidate("M13", "households_no_vehicle", "Households with no vehicle (B08201)", *ACS, "C5", ("RT", "SW"),
              "households", "OBSERVED", "ABSOLUTE", "MART", U, "Dominated by NYC"),
    Candidate("M14", "aggregate_vehicles_available", "Aggregate vehicles available (B25046)", *ACS, "C5",
              ("RT",), "vehicles", "OBSERVED", "ABSOLUTE", "MART", U, "Scale-driven"),
    Candidate("M15", "housing_units_total", "Housing units (B25024)", *ACS, "C1", ("DR",), "housing units",
              "OBSERVED", "ABSOLUTE", "MART", U, "Scale-driven"),
    Candidate("M16", "housing_units_1_detached", "Single-family detached housing units", *ACS, "C5", ("DR",),
              "housing units", "OBSERVED", "ABSOLUTE", "MART", U, "Lot size and tree cover unobserved"),
    Candidate("M17", "owner_occupied_units", "Owner-occupied housing units (B25003)", *ACS, "C5", ("DR",),
              "housing units", "OBSERVED", "ABSOLUTE", "MART", U, "Weak proxy (F47)"),
    Candidate("M18", "cbp_establishments_all_sectors", "Business establishments, all sectors", *CBP, "C3",
              ("RT", "SW", "DR"), "establishments", "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "Excludes self-employed; noise infusion"),
    Candidate("M19", "cbp_employment_all_sectors", "Employment, all sectors (mid-March)", *CBP, "C3",
              ("RT", "SW", "DR"), "persons", "OBSERVED", "ABSOLUTE", "MART", U, "Scale-driven"),
    Candidate("M20", "cbp_establishments_retail_trade", "Retail trade establishments (NAICS 44-45)", *CBP, "C1",
              ("SW", "DR"), "establishments", "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "Establishments are not delivery volume (A-019)"),
    Candidate("M21", "cbp_establishments_food_beverage_retail", "Food & beverage retail establishments (445)",
              *CBP, "C1", ("SW", "DR"), "establishments", "OBSERVED", "ABSOLUTE", "MART",
              "HYPOTHESIS:HIGHER_MORE_DEMAND", "A-019"),
    Candidate("M22", "cbp_establishments_food_services_drinking", "Food services & drinking places (722)", *CBP,
              "C1", ("SW", "DR"), "establishments", "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "A-019"),
    Candidate("M23", "cbp_establishments_restaurants", "Restaurants and other eating places (7225)", *CBP, "C1",
              ("SW", "DR"), "establishments", "OBSERVED", "ABSOLUTE", "MART", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "Subset of M22"),
    Candidate("M24", "cbp_establishments_couriers_messengers", "Courier & messenger establishments (492)", *CBP,
              "C3", ("SW", "DR"), "establishments", "OBSERVED", "ABSOLUTE", "MART", U,
              "Incumbent delivery capacity; direction unclear"),
    Candidate("M25", "cbp_employment_restaurants", "Restaurant employment (7225)", *CBP, "C1", ("SW", "DR"),
              "persons", "OBSERVED", "ABSOLUTE", "MART", U, "Scale-driven"),
    Candidate("M26", "oews_annual_median_wage_shuttle_drivers_chauffeurs",
              "Median annual wage, shuttle drivers & chauffeurs (53-3053)", *OEWS, "C3", ("RT",), "USD",
              "OBSERVED", "INTENSITY", "MART", "HYPOTHESIS:HIGHER_HUMAN_COST_FAVORS_AUTOMATION",
              "Excludes self-employed (A-017)"),
    Candidate("M27", "oews_annual_median_wage_taxi_drivers", "Median annual wage, taxi drivers (53-3054)", *OEWS,
              "C3", ("RT",), "USD", "OBSERVED", "INTENSITY", "MART", "HYPOTHESIS:HIGHER_HUMAN_COST_FAVORS_AUTOMATION",
              "Published for 7 of 35 markets (A-026)"),
    Candidate("M28", "oews_annual_median_wage_couriers_messengers",
              "Median annual wage, couriers & messengers (43-5021)", *OEWS, "C3", ("SW", "DR"), "USD", "OBSERVED",
              "INTENSITY", "MART", "HYPOTHESIS:HIGHER_HUMAN_COST_FAVORS_AUTOMATION", "A-017"),
    Candidate("M29", "oews_annual_median_wage_light_truck_drivers",
              "Median annual wage, light truck drivers (53-3033)", *OEWS, "C3", ("SW", "DR"), "USD", "OBSERVED",
              "INTENSITY", "MART", "HYPOTHESIS:HIGHER_HUMAN_COST_FAVORS_AUTOMATION", "A-017"),
    Candidate("M30", "oews_annual_median_wage_fast_food_counter_workers",
              "Median annual wage, fast food & counter workers (35-3023)", *OEWS, "C3", ("SW",), "USD",
              "OBSERVED", "INTENSITY", "MART", U, "Not a delivery occupation; general low-wage labor context"),
    Candidate("M31", "oews_employment_shuttle_drivers_chauffeurs", "Employment, shuttle drivers & chauffeurs",
              *OEWS, "C1", ("RT",), "persons", "OBSERVED", "ABSOLUTE", "MART", U, "Scale-driven"),
    Candidate("M32", "oews_employment_couriers_messengers", "Employment, couriers & messengers", *OEWS, "C1",
              ("SW", "DR"), "persons", "OBSERVED", "ABSOLUTE", "MART", U, "Scale-driven"),
    Candidate("M33", "land_area_sq_mi", "CBSA land area", "S-05 Gazetteer", "2024", "C5", ("RT", "SW", "DR"),
              "sq mi", "OBSERVED", "STRUCTURAL", "MART", U, "County-based footprint; a denominator, not a feature"),
    Candidate("M34", "county_count", "Counties in the CBSA", "S-02 delineation", "2023-07", "C5",
              ("RT", "SW", "DR"), "count", "OBSERVED", "STRUCTURAL", "MART", U, "Administrative structure only"),
    Candidate("M35", "state_count", "States the CBSA spans", "S-01/S-05", "2025", "C4", ("RT", "SW", "DR"),
              "count", "OBSERVED", "STRUCTURAL", "MART", U, "Regulatory complexity context (A-012)"),
]

# Exploratory intensity counterparts (local only). formula = (numerator, denominator, multiplier).
INTENSITY_CANDIDATES: list[Candidate] = [
    Candidate("I01", "raw_density_per_sq_mi", "Population per sq mi of CBSA land (raw MSA density)",
              "S-01 + S-05", "2025/2024", "C1", ("RT", "SW", "DR"), "persons / sq mi", "DERIVED", "INTENSITY",
              "INTENSITY", U, "Distorted by large outlying counties (A-008)",
              ("population_2025", "land_area_sq_mi", 1)),
    Candidate("I02", "share_drove_alone", "Share of workers driving alone", *ACS, "C1", ("RT",), "share",
              "DERIVED", "INTENSITY", "INTENSITY", U, "", ("workers_drove_alone", "workers_16_plus", 1)),
    Candidate("I03", "share_public_transportation", "Share of workers using public transport", *ACS, "C1",
              ("RT",), "share", "DERIVED", "INTENSITY", "INTENSITY", U, "",
              ("workers_public_transportation", "workers_16_plus", 1)),
    Candidate("I04", "share_taxi_or_ride_hailing", "Share of workers commuting by taxi/ride-hailing", *ACS, "C1",
              ("RT",), "share", "DERIVED", "INTENSITY", "INTENSITY", "HYPOTHESIS:HIGHER_MORE_DEMAND",
              "Large relative MOE", ("workers_taxi_or_ride_hailing", "workers_16_plus", 1)),
    Candidate("I05", "share_walked", "Share of workers walking to work", *ACS, "C5", ("SW",), "share", "DERIVED",
              "INTENSITY", "INTENSITY", U, "", ("workers_walked", "workers_16_plus", 1)),
    Candidate("I06", "share_bicycle", "Share of workers cycling to work", *ACS, "C5", ("SW",), "share", "DERIVED",
              "INTENSITY", "INTENSITY", U, "", ("workers_bicycle", "workers_16_plus", 1)),
    Candidate("I07", "share_worked_from_home", "Share of workers working from home", *ACS, "C1", ("SW", "DR"),
              "share", "DERIVED", "INTENSITY", "INTENSITY", U, "A-018",
              ("workers_worked_from_home", "workers_16_plus", 1)),
    Candidate("I08", "share_households_no_vehicle", "Share of households with no vehicle", *ACS, "C5",
              ("RT", "SW"), "share", "DERIVED", "INTENSITY", "INTENSITY", U, "",
              ("households_no_vehicle", "households_vehicle_universe", 1)),
    Candidate("I09", "vehicles_per_household", "Vehicles available per household", *ACS, "C5", ("RT",),
              "vehicles / household", "DERIVED", "INTENSITY", "INTENSITY", U, "",
              ("aggregate_vehicles_available", "households_vehicle_universe", 1)),
    Candidate("I10", "share_single_family_detached", "Share of housing units that are 1-unit detached", *ACS,
              "C5", ("DR",), "share", "DERIVED", "INTENSITY", "INTENSITY", "HYPOTHESIS:HIGHER_BETTER_DRONE_FIT",
              "Lot size unobserved (F46)", ("housing_units_1_detached", "housing_units_total", 1)),
    Candidate("I11", "share_owner_occupied", "Share of occupied units owner-occupied", *ACS, "C5", ("DR",),
              "share", "DERIVED", "INTENSITY", "INTENSITY", U, "Weak proxy (F47)",
              ("owner_occupied_units", "occupied_housing_units", 1)),
    Candidate("I12", "establishments_per_1k_pop", "Business establishments per 1,000 residents", *CBP, "C3",
              ("RT", "SW", "DR"), "per 1,000", "DERIVED", "INTENSITY", "INTENSITY", U, "",
              ("cbp_establishments_all_sectors", "population_2025", 1000)),
    Candidate("I13", "retail_per_10k_pop", "Retail establishments per 10,000 residents", *CBP, "C1", ("SW", "DR"),
              "per 10,000", "DERIVED", "INTENSITY", "INTENSITY", U, "A-019",
              ("cbp_establishments_retail_trade", "population_2025", 10000)),
    Candidate("I14", "food_bev_retail_per_10k_pop", "Food & beverage retailers per 10,000 residents", *CBP, "C1",
              ("SW", "DR"), "per 10,000", "DERIVED", "INTENSITY", "INTENSITY", U, "A-019",
              ("cbp_establishments_food_beverage_retail", "population_2025", 10000)),
    Candidate("I15", "restaurants_per_10k_pop", "Restaurants per 10,000 residents", *CBP, "C1", ("SW", "DR"),
              "per 10,000", "DERIVED", "INTENSITY", "INTENSITY", U, "A-019",
              ("cbp_establishments_restaurants", "population_2025", 10000)),
    Candidate("I16", "restaurants_per_sq_mi", "Restaurants per sq mi of CBSA land", *CBP, "C1", ("SW",),
              "per sq mi", "DERIVED", "INTENSITY", "INTENSITY", U, "Same county-footprint distortion as I01",
              ("cbp_establishments_restaurants", "land_area_sq_mi", 1)),
    Candidate("I17", "couriers_per_100k_pop", "Courier establishments per 100,000 residents", *CBP, "C3",
              ("SW", "DR"), "per 100,000", "DERIVED", "INTENSITY", "INTENSITY", U, "",
              ("cbp_establishments_couriers_messengers", "population_2025", 100000)),
    Candidate("I18", "persons_per_household", "Persons per household", *ACS, "C1", ("DR",),
              "persons / household", "DERIVED", "INTENSITY", "INTENSITY", U, "",
              ("acs_total_population", "total_households", 1)),
]

MART_BY_COLUMN = {c.column: c for c in MART_CANDIDATES}
