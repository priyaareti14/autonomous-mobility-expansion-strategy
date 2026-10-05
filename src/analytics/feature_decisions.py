"""Phase 5 feature-audit decisions (KEEP / MODIFY / DEFER / DROP), written after the evidence
in outputs/ was reviewed. Decisions are per candidate and per mode. None of them is a weight.
"""

from __future__ import annotations

import pandas as pd

from .feature_catalog import Candidate

# Mapping-derived candidates (computed in Phase 5 from CORE lower-grain facts; local only).
MAPPING_CANDIDATES: list[Candidate] = [
    Candidate("P01", "pw_tract_density", "Population-weighted tract density (ACS 2020-2024 / Gazetteer 2024)",
              "S-04 + S-05", "2024", "C1", ("RT", "SW"), "persons / sq mi", "DERIVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:HIGHER_MORE_DEMAND", "NY excludes 14 Suffolk tracts (A-029)"),
    Candidate("P02", "central_county_density", "Population density of the CBSA's central counties",
              "S-01 + S-02 + S-05", "2025", "C1", ("RT", "SW"), "persons / sq mi", "DERIVED", "INTENSITY",
              "MAPPING", "UNRESOLVED", "Urban-core proxy; true urban areas (S-06) not ingested"),
    Candidate("P03", "share_pop_tracts_ge_5000", "Share of residents in tracts >= 5,000 persons / sq mi",
              "S-04 + S-05", "2024", "C5", ("SW", "RT"), "share", "DERIVED", "INTENSITY", "MAPPING",
              "UNRESOLVED", "Threshold is a scoring choice (Phase 6)"),
    Candidate("P04", "share_pop_tracts_lt_1000", "Share of residents in tracts < 1,000 persons / sq mi",
              "S-04 + S-05", "2024", "C5", ("DR",), "share", "DERIVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:HIGHER_BETTER_DRONE_FIT", "Threshold is a scoring choice (Phase 6)"),
    Candidate("P05", "annual_precip_in", "Annual precipitation normal at the mapped station", "S-12 NOAA",
              "1991-2020", "C2", ("RT", "SW", "DR"), "inches", "OBSERVED", "INTENSITY", "MAPPING", "UNRESOLVED",
              "Station representativeness (A-007)"),
    Candidate("P06", "days_precip_ge_010_in", "Days per year with precipitation >= 0.10 in", "S-12 NOAA",
              "1991-2020", "C2", ("RT", "SW", "DR"), "days / yr", "OBSERVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:LOWER_EASIER_OPERATION", "A-007"),
    Candidate("P07", "days_tmax_ge_90f", "Days per year with Tmax >= 90 F", "S-12 NOAA", "1991-2020", "C2",
              ("RT", "SW", "DR"), "days / yr", "OBSERVED", "INTENSITY", "MAPPING", "HYPOTHESIS:LOWER_EASIER_OPERATION",
              "A-007"),
    Candidate("P08", "days_tmin_le_32f", "Days per year with Tmin <= 32 F", "S-12 NOAA", "1991-2020", "C2",
              ("RT", "SW", "DR"), "days / yr", "OBSERVED", "INTENSITY", "MAPPING", "HYPOTHESIS:LOWER_EASIER_OPERATION",
              "A-007"),
    Candidate("P09", "annual_mean_temp_f", "Annual mean temperature", "S-12 NOAA", "1991-2020", "C2",
              ("RT", "SW", "DR"), "deg F", "OBSERVED", "INTENSITY", "MAPPING", "UNRESOLVED",
              "Non-monotonic (both cold and heat stress)"),
    Candidate("P10", "annual_snowfall_in", "Annual snowfall normal at the mapped station", "S-12 NOAA",
              "1991-2020", "C2", ("RT", "SW", "DR"), "inches", "OBSERVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:LOWER_EASIER_OPERATION", "Not published at some stations (A-021)"),
    Candidate("P11", "annual_mean_wind_mph", "Annual mean of hourly mean wind speed (NCEI hourly normals)",
              "S-13 NOAA", "1991-2020", "C2", ("DR",), "mph", "DERIVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:LOWER_EASIER_DRONE_OPERATION", "Mean wind is not gust exposure (F19 PROXY)"),
    Candidate("P12", "enplanements_inside_cbsa_per_capita", "Commercial-service enplanements inside the CBSA per resident",
              "S-17 + S-19", "CY2025", "C1", ("RT",), "enplanements / resident", "DERIVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:HIGHER_MORE_DEMAND", "Hub connecting traffic inflates (A-010); boundary airports (A-009)"),
    Candidate("P13", "enplanements_inside_cbsa", "Commercial-service enplanements inside the CBSA", "S-17 + S-19",
              "CY2025", "C1", ("RT",), "enplanements", "DERIVED", "ABSOLUTE", "MAPPING",
              "HYPOTHESIS:HIGHER_MORE_DEMAND", "A-009, A-010"),
    Candidate("P14", "walkability_pw_mean", "Population-weighted mean National Walkability Index", "S-21/S-22 EPA",
              "SLD v3.0", "C5", ("SW", "RT"), "index 1-20", "DERIVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:HIGHER_BETTER_SIDEWALK_FIT", "Relative rank; 2017-2020 inputs (A-013)"),
    Candidate("P15", "share_pop_most_walkable", "Share of residents in 'most walkable' block groups (NWI >= 15.26)",
              "S-21/S-22 EPA", "SLD v3.0", "C5", ("SW",), "share", "DERIVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:HIGHER_BETTER_SIDEWALK_FIT", "EPA bin boundary; A-013"),
    Candidate("P16", "intersection_density_pw_mean", "Population-weighted street intersection density (D3B)",
              "S-21 EPA", "SLD v3.0", "C5", ("SW", "RT"), "intersections / sq mi", "DERIVED", "INTENSITY", "MAPPING",
              "UNRESOLVED", "Input of NWI (redundancy)"),
    Candidate("P17", "transportation_occupations_median_wage",
              "Median annual wage, all transportation & material moving occupations (53-0000)", "S-09 OEWS",
              "May 2025", "C3", ("RT", "SW", "DR"), "USD", "OBSERVED", "INTENSITY", "MAPPING",
              "HYPOTHESIS:HIGHER_HUMAN_COST_FAVORS_AUTOMATION", "Broad group incl. non-driving jobs"),
]

# Cause class for each candidate that has missing values (reviewed per feature).
MISSING_CAUSES = {
    "oews_annual_median_wage_taxi_drivers": "SOURCE_NOT_PUBLISHED",
    "annual_snowfall_in": "SOURCE_NOT_PUBLISHED",
}


# ---------------------------------------------------------------------------
# Decisions. Written after reviewing outputs/ (correlations, size duplication,
# missingness, outliers, mapping comparisons). Per mode: K=KEEP, M=MODIFY,
# D=DEFER, X=DROP. Every decision cites reason codes; no weights are implied.
#   feature: (RT, SW, DR, redundancy_group, recommended_transformation,
#             source_quality, geography_quality, reason_codes, rationale, phase_revisit)
# ---------------------------------------------------------------------------
K, M, D, X = "KEEP", "MODIFY", "DEFER", "DROP"
SPEC = {
    # ---- MARKET_SCALE: one explicit scale measure; every other absolute count duplicates it
    "population_2025": (K, K, K, "MARKET_SCALE", "LOG1P", "HIGH", "HIGH", "GOOD_SIGNAL",
        "The single explicit market-scale measure; every absolute count correlates rho>=0.90 with it.", 6),
    "acs_total_population": (X, X, X, "MARKET_SCALE", "NONE", "HIGH", "HIGH", "REDUNDANT",
        "rho 0.994 with PEP population; the PEP V2025 frozen-universe source is preferred.", 6),
    "total_households": (X, X, X, "MARKET_SCALE", "NONE", "HIGH", "HIGH", "REDUNDANT",
        "rho 0.973 with population; adds no distinct concept.", 6),
    "workers_16_plus": (X, X, X, "MARKET_SCALE", "NONE", "HIGH", "HIGH", "REDUNDANT",
        "rho 0.989 with population; used only as a denominator.", 6),
    "housing_units_total": (X, X, X, "MARKET_SCALE", "NONE", "HIGH", "HIGH", "REDUNDANT",
        "rho 0.972 with population; denominator only.", 6),
    "aggregate_vehicles_available": (X, X, X, "MARKET_SCALE", "NONE", "HIGH", "HIGH", "REDUNDANT",
        "rho 0.986 with population; intensity form is vehicles_per_household.", 6),
    "cbp_employment_all_sectors": (X, X, X, "MARKET_SCALE", "NONE", "MEDIUM", "HIGH", "REDUNDANT",
        "rho 0.955 with population.", 6),
    "cbp_employment_restaurants": (X, X, X, "MARKET_SCALE", "NONE", "MEDIUM", "HIGH", "REDUNDANT",
        "rho 0.968 with population.", 6),
    "oews_employment_shuttle_drivers_chauffeurs": (X, X, X, "MARKET_SCALE", "NONE", "MEDIUM", "HIGH",
        "REDUNDANT", "Employment count is scale; wage is the labor-cost signal.", 6),
    "oews_employment_couriers_messengers": (X, X, X, "MARKET_SCALE", "NONE", "MEDIUM", "HIGH", "REDUNDANT",
        "Employment count is scale; wage is the labor-cost signal.", 6),
    "enplanements_inside_cbsa": (X, X, X, "MARKET_SCALE", "NONE", "HIGH", "MEDIUM", "REDUNDANT",
        "Absolute enplanements rho 0.785 with population and dominated by hubs; per-resident form kept instead.", 6),
    # ---- absolute counts with an intensity counterpart -> MODIFY (use the counterpart)
    "workers_drove_alone": (M, X, X, "MOBILITY_DEMAND", "PER_CAPITA -> share_drove_alone", "HIGH", "HIGH",
        "REDUNDANT", "Absolute count is scale (rho 0.971); see share_drove_alone.", 6),
    "workers_public_transportation": (M, M, X, "MOBILITY_DEMAND", "PER_CAPITA -> share_public_transportation",
        "HIGH", "HIGH", "REDUNDANT", "Absolute count is scale; NYC robust z 107.", 6),
    "workers_taxi_or_ride_hailing": (M, X, X, "MOBILITY_DEMAND", "PER_CAPITA -> share_taxi_or_ride_hailing",
        "MEDIUM", "HIGH", "REDUNDANT", "Absolute count rho 0.815 with population; share form is distinct.", 6),
    "workers_walked": (X, M, X, "URBAN_FORM", "PER_CAPITA -> share_walked", "HIGH", "HIGH", "REDUNDANT",
        "Absolute count is scale; see share_walked.", 6),
    "workers_bicycle": (X, X, X, "URBAN_FORM", "NONE", "MEDIUM", "HIGH", "PROXY_TOO_WEAK",
        "Small counts (MOE CV up to 15.5%); weak conceptual link.", 6),
    "workers_worked_from_home": (X, M, M, "MOBILITY_DEMAND", "PER_CAPITA -> share_worked_from_home", "MEDIUM",
        "HIGH", "REDUNDANT", "Scale (rho 0.916); pandemic-era (A-018).", 6),
    "households_no_vehicle": (M, M, X, "MOBILITY_DEMAND", "PER_CAPITA -> share_households_no_vehicle", "HIGH",
        "HIGH", "REDUNDANT", "Absolute count dominated by NYC (robust z 41).", 6),
    "housing_units_1_detached": (X, X, M, "URBAN_FORM", "PER_CAPITA -> share_single_family_detached", "HIGH",
        "HIGH", "REDUNDANT", "Absolute count is scale (rho 0.885).", 6),
    "owner_occupied_units": (X, X, X, "URBAN_FORM", "NONE", "HIGH", "HIGH", "REDUNDANT;PROXY_TOO_WEAK",
        "Scale (rho 0.944); share form is a weak drone proxy too.", 6),
    "cbp_establishments_all_sectors": (M, M, M, "COMMERCIAL_INTENSITY", "PER_CAPITA -> establishments_per_1k_pop",
        "MEDIUM", "HIGH", "REDUNDANT", "Scale (rho 0.970).", 6),
    "cbp_establishments_retail_trade": (X, M, M, "COMMERCIAL_INTENSITY", "PER_CAPITA -> retail_per_10k_pop",
        "MEDIUM", "HIGH", "REDUNDANT", "Scale (rho 0.964).", 6),
    "cbp_establishments_food_beverage_retail": (X, M, M, "COMMERCIAL_INTENSITY",
        "PER_CAPITA -> food_bev_retail_per_10k_pop", "MEDIUM", "HIGH", "REDUNDANT", "Scale (rho 0.897).", 6),
    "cbp_establishments_food_services_drinking": (X, X, X, "COMMERCIAL_INTENSITY", "NONE", "MEDIUM", "HIGH",
        "REDUNDANT", "Superset of restaurants (7225), scale rho 0.969; restaurants is the cleaner concept.", 6),
    "cbp_establishments_restaurants": (X, M, M, "COMMERCIAL_INTENSITY", "PER_CAPITA -> restaurants_per_10k_pop",
        "MEDIUM", "HIGH", "REDUNDANT", "Scale (rho 0.974).", 6),
    "cbp_establishments_couriers_messengers": (X, M, M, "COMMERCIAL_INTENSITY",
        "PER_CAPITA -> couriers_per_100k_pop", "MEDIUM", "HIGH", "REDUNDANT", "Scale (rho 0.924).", 6),
    # ---- MOBILITY_DEMAND intensities
    "share_taxi_or_ride_hailing": (K, X, X, "MOBILITY_DEMAND", "ROBUST_SCALE_LATER", "MEDIUM", "HIGH",
        "GOOD_SIGNAL", "Revealed paid-ride commuting; distinct from density/walkability (rho 0.20-0.41); MOE CV <=14.6%.", 6),
    "share_drove_alone": (D, X, X, "MOBILITY_DEMAND", "UNRESOLVED", "HIGH", "HIGH", "UNCLEAR_DIRECTION",
        "Car dependence could mean substitutable trips or low willingness to switch.", 6),
    "share_public_transportation": (D, D, X, "MOBILITY_DEMAND", "LOG1P; ROBUST_SCALE_LATER", "HIGH", "HIGH",
        "UNCLEAR_DIRECTION;REDUNDANT", "Complement vs substitute unresolved; rho 0.84 with car-free households; NYC extreme (24%).", 6),
    "share_households_no_vehicle": (D, D, X, "MOBILITY_DEMAND", "LOG1P; ROBUST_SCALE_LATER", "HIGH", "HIGH",
        "UNCLEAR_DIRECTION;REDUNDANT", "rho 0.84 with transit share; NYC 31% vs 7% median.", 6),
    "vehicles_per_household": (X, X, X, "MOBILITY_DEMAND", "NONE", "HIGH", "HIGH", "REDUNDANT;UNCLEAR_DIRECTION",
        "Near-inverse of car-free households (rho -0.79).", 6),
    "share_worked_from_home": (X, D, D, "MOBILITY_DEMAND", "NONE", "MEDIUM", "HIGH", "UNCLEAR_DIRECTION",
        "Pandemic-era level (A-018); daytime-at-home delivery link is a hypothesis only.", 6),
    "mean_travel_time_minutes": (D, X, X, "MOBILITY_DEMAND", "UNRESOLVED", "HIGH", "HIGH",
        "UNCLEAR_DIRECTION", "Demand vs congestion ambiguity; rho 0.74 with population.", 6),
    "persons_per_household": (X, X, X, "MOBILITY_DEMAND", "NONE", "HIGH", "HIGH", "PROXY_TOO_WEAK",
        "No defensible link to any mode.", 6),
    # ---- AIRPORT_ACTIVITY
    "enplanements_inside_cbsa_per_capita": (M, X, X, "AIRPORT_ACTIVITY", "LOG1P; HUB_CAVEAT", "HIGH", "MEDIUM",
        "WAIT_FOR_MAPPING", "Method A1 recommended (rho 0.994 with A4); connecting-hub inflation (DEN 12.9, CLT 8.9) unresolved without O&D data.", 6),
    # ---- URBAN_FORM / density
    "raw_density_per_sq_mi": (X, X, X, "URBAN_FORM", "NONE", "HIGH", "LOW", "BAD_GEOGRAPHY",
        "County footprint distortion: Riverside 175 vs 4,651 pw (x26.6); rho 0.57 with pw density.", 6),
    "pw_tract_density": (K, K, D, "URBAN_FORM", "LOG1P", "HIGH", "HIGH", "GOOD_SIGNAL",
        "Preferred density method (A-008); NY excludes 14 tracts (-0.3% bound). Drone direction unresolved.", 6),
    "central_county_density": (X, X, X, "URBAN_FORM", "NONE", "HIGH", "LOW", "BAD_GEOGRAPHY",
        "Equals raw density for 1-2 county metros (Riverside, Phoenix, Las Vegas).", 6),
    "share_pop_tracts_ge_5000": (D, D, X, "URBAN_FORM", "NONE", "HIGH", "HIGH", "REDUNDANT",
        "rho 0.95 with pw density; kept as a sensitivity alternative.", 6),
    "share_pop_tracts_lt_1000": (X, X, M, "URBAN_FORM", "NONE (threshold to justify)", "HIGH", "HIGH",
        "GOOD_SIGNAL", "Low-density residential share; drone service-area fit; the 1,000/sq mi threshold is a Phase 6 choice.", 6),
    "share_single_family_detached": (X, X, K, "URBAN_FORM", "NONE", "HIGH", "HIGH", "GOOD_SIGNAL",
        "Yard/driveway drop-off fit (F46); rho 0.57 with low-density share, so partly distinct.", 6),
    "share_owner_occupied": (X, X, X, "URBAN_FORM", "NONE", "HIGH", "HIGH", "PROXY_TOO_WEAK", "Weak proxy (F47).", 6),
    "walkability_pw_mean": (D, K, X, "URBAN_FORM", "NONE", "MEDIUM", "HIGH", "GOOD_SIGNAL",
        "Recommended aggregation; all NWI aggregations agree rho>=0.90; 2017-2020 inputs (A-013).", 6),
    "share_pop_most_walkable": (X, D, X, "URBAN_FORM", "NONE", "MEDIUM", "HIGH", "REDUNDANT",
        "rho 0.91 with pw mean; alternative for concentrated walkable cores.", 6),
    "intersection_density_pw_mean": (D, D, X, "URBAN_FORM", "LOG1P", "MEDIUM", "HIGH", "REDUNDANT;UNCLEAR_DIRECTION",
        "NWI input (rho 0.88); road-complexity direction for robotaxi unresolved (F22).", 6),
    "share_walked": (X, D, X, "URBAN_FORM", "NONE", "HIGH", "HIGH", "REDUNDANT",
        "rho 0.84 with transit share, 0.69 with walkability.", 6),
    "share_bicycle": (X, X, X, "URBAN_FORM", "NONE", "MEDIUM", "HIGH", "PROXY_TOO_WEAK", "Tiny shares, MOE.", 6),
    # ---- COMMERCIAL_INTENSITY
    "establishments_per_1k_pop": (K, K, K, "COMMERCIAL_INTENSITY", "NONE", "MEDIUM", "HIGH", "GOOD_SIGNAL",
        "General commercial intensity; weakly related to income (rho 0.40).", 6),
    "retail_per_10k_pop": (X, K, K, "COMMERCIAL_INTENSITY", "NONE", "MEDIUM", "HIGH", "GOOD_SIGNAL",
        "Retail delivery opportunity; distinct from restaurants (rho 0.33). Establishments are not order volume (A-019).", 6),
    "food_bev_retail_per_10k_pop": (X, D, D, "COMMERCIAL_INTENSITY", "NONE", "MEDIUM", "HIGH", "REDUNDANT",
        "Overlaps retail (0.59) and restaurants (0.55); grocery-delivery alternative.", 6),
    "restaurants_per_10k_pop": (X, K, K, "COMMERCIAL_INTENSITY", "NONE", "MEDIUM", "HIGH", "GOOD_SIGNAL",
        "Prepared-food delivery opportunity; independent of size (see figure 04b).", 6),
    "restaurants_per_sq_mi": (X, X, X, "COMMERCIAL_INTENSITY", "NONE", "MEDIUM", "LOW", "BAD_GEOGRAPHY",
        "Same county-footprint distortion as raw density.", 6),
    "couriers_per_100k_pop": (X, D, D, "COMMERCIAL_INTENSITY", "UNRESOLVED", "MEDIUM", "HIGH", "UNCLEAR_DIRECTION",
        "Incumbent delivery capacity: competitor or ecosystem signal?", 6),
    # ---- INCOME / LABOR_COST
    "median_household_income_usd": (K, K, K, "INCOME_ECONOMICS", "NONE (consider COL adjustment)", "HIGH",
        "HIGH", "GOOD_SIGNAL", "Ability to pay; rho 0.77-0.85 with occupational wages, so do not stack with labor cost in one component.", 6),
    "oews_annual_median_wage_shuttle_drivers_chauffeurs": (K, X, X, "LABOR_COST", "NONE", "MEDIUM", "HIGH",
        "GOOD_SIGNAL", "Replacement for taxi wage: closest passenger-driving occupation, 35/35 coverage; excludes gig drivers (A-017).", 6),
    "oews_annual_median_wage_taxi_drivers": (X, X, X, "LABOR_COST", "NONE", "LOW", "HIGH", "TOO_MISSING",
        "Published for 7 of 35 markets; rho -0.28 with shuttle wage on n=7 (unreliable). Contextual only (A-026).", 6),
    "oews_annual_median_wage_couriers_messengers": (X, K, K, "LABOR_COST", "NONE", "MEDIUM", "HIGH", "GOOD_SIGNAL",
        "Human delivery labor cost; least redundant wage with income (rho 0.63).", 6),
    "oews_annual_median_wage_light_truck_drivers": (X, D, D, "LABOR_COST", "NONE", "MEDIUM", "HIGH", "REDUNDANT",
        "rho 0.85 with income and 0.91 with the 53-0000 group; backup delivery-labor measure.", 6),
    "oews_annual_median_wage_fast_food_counter_workers": (X, X, X, "LABOR_COST", "NONE", "MEDIUM", "HIGH",
        "PROXY_TOO_WEAK", "Not a delivery occupation; tracks the regional wage level.", 6),
    "transportation_occupations_median_wage": (D, D, D, "LABOR_COST", "NONE", "MEDIUM", "HIGH", "REDUNDANT",
        "Broad group incl. non-driving jobs; rho 0.91 with light-truck wage.", 6),
    # ---- WEATHER (W5 station rule)
    "days_precip_ge_010_in": (K, K, K, "WEATHER", "NONE", "HIGH", "MEDIUM", "GOOD_SIGNAL",
        "Operational wet days; W5 vs ring-mean rho 0.975.", 6),
    "annual_precip_in": (D, D, D, "WEATHER", "NONE", "HIGH", "MEDIUM", "REDUNDANT",
        "Totals are less operational than wet-day counts (rho 0.67).", 6),
    "days_tmax_ge_90f": (K, K, K, "WEATHER", "NONE", "HIGH", "MEDIUM", "GOOD_SIGNAL",
        "Heat stress; distinct from cold (rho -0.41).", 6),
    "days_tmin_le_32f": (D, D, D, "WEATHER", "NONE", "HIGH", "MEDIUM", "REDUNDANT",
        "rho 0.95 with snowfall; keep one of the two in a component.", 6),
    "annual_snowfall_in": (K, K, K, "WEATHER", "NONE", "HIGH", "MEDIUM", "GOOD_SIGNAL",
        "Snow resolved for 35/35 under W5 (A-021); direct operating hazard.", 6),
    "annual_mean_temp_f": (X, X, X, "WEATHER", "NONE", "HIGH", "MEDIUM", "UNCLEAR_DIRECTION;REDUNDANT",
        "Non-monotonic (both cold and heat stress); rho -0.89 with snowfall.", 6),
    "annual_mean_wind_mph": (X, X, M, "WEATHER", "NONE (consider p90 hourly)", "MEDIUM", "MEDIUM", "PROXY_TOO_WEAK",
        "Mean wind is a weak gust proxy; Austin's hourly station is 81.8 km away.", 6),
    # ---- STRUCTURAL
    "land_area_sq_mi": (X, X, X, "STRUCTURAL", "NONE", "HIGH", "HIGH", "NEEDS_AGGREGATION",
        "Denominator only; the county-based footprint is not a market property.", 6),
    "county_count": (X, X, X, "STRUCTURAL", "NONE", "HIGH", "HIGH", "PROXY_TOO_WEAK",
        "Administrative structure only.", 6),
    "state_count": (D, D, D, "STRUCTURAL", "NONE", "HIGH", "HIGH", "WAIT_FOR_REGULATION;NO_VARIATION",
        "Only 1-4 values; relevant to multi-state regulatory mapping (A-012) only.", 7),
}


def _overall(statuses: tuple[str, str, str]) -> str:
    for d in (K, M, D):
        if d in statuses:
            return d
    return X


def build_decision_table(inv: pd.DataFrame, miss: pd.DataFrame, size: pd.DataFrame,
                         comps: list[list[str]]) -> pd.DataFrame:
    missing = [f for f in inv["feature_name"] if f not in SPEC]
    if missing:
        raise ValueError(f"no decision recorded for: {missing}")
    sz = size.set_index("feature_name")["spearman_vs_population"]
    rows = []
    for _, r in inv.iterrows():
        rt, sw, dr, grp, tf, sq, gq, reasons, why, revisit = SPEC[r["feature_name"]]
        # An absolute count marked MODIFY survives only through its intensity counterpart, so it
        # cannot be more alive than that counterpart for any mode (MODIFY -> counterpart's status).
        if tf.startswith("PER_CAPITA -> "):
            target = tf.split("-> ", 1)[1]
            t_rt, t_sw, t_dr = SPEC[target][:3]
            rt, sw, dr = [s if s != M or t == K else t for s, t in ((rt, t_rt), (sw, t_sw), (dr, t_dr))]
            why = f"{why} Represented only through {target}; mode status capped at that feature's status."
        rows.append({
            "feature_id": r["feature_id"], "feature_name": r["feature_name"], "source": r["source"],
            "component": r["component"], "robotaxi_status": rt, "sidewalk_status": sw, "drone_status": dr,
            "missing_pct": r["missing_pct"], "spearman_vs_population": sz.get(r["feature_name"]),
            "skewness": round(r["skewness"], 2) if pd.notna(r["skewness"]) else None,
            "redundancy_group": grp, "recommended_transformation": tf,
            "direction_status": r["expected_direction"], "source_quality": sq, "geography_quality": gq,
            "decision": _overall((rt, sw, dr)), "decision_reason": reasons, "rationale": why,
            "phase_revisit": revisit,
        })
    return pd.DataFrame(rows)
