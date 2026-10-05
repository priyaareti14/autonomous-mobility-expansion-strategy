"""Phase 6: freeze the approved Phase 5 decision table and build the production feature contract.

1. Validates outputs/feature_audit.csv (the approved Phase 5 artifact) and records its SHA-256.
   The build stops if the file changed since approval or fails any integrity rule.
2. Writes dbt/seeds/feature_contract.csv: one row per feature x mode that Phase 6 carries
   (ACTIVE, DIAGNOSTIC, DEFERRED or explicitly DROPPED).
3. Writes outputs/phase6/phase5_to_phase6_crosswalk.csv (all 70 x 3 Phase 5 feature-mode pairs and
   what happened to each) and outputs/phase6/decision_changes.csv (OLD_DECISION / NEW_DECISION / REASON).

No Snowflake access. No weights, scores or rankings.

Usage (repository root, .venv active):
    python scripts/build_feature_contract.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "outputs" / "feature_audit.csv"
CONTRACT = ROOT / "dbt" / "seeds" / "feature_contract.csv"
OUT = ROOT / "outputs" / "phase6"

# SHA-256 of outputs/feature_audit.csv as approved and committed with Phase 5 (6e40d2b).
APPROVED_PHASE5_SHA256 = "3CC26A6C01CEB3D630070F7386C8A2A43355A382C3D4EB8899F09E3BC9517DAF"

MODES = {"RT": "ROBOTAXI", "SW": "SIDEWALK_DELIVERY", "DR": "DRONE_DELIVERY"}
STATUS_COL = {"RT": "robotaxi_status", "SW": "sidewalk_status", "DR": "drone_status"}
COMPONENTS = {
    "C1": "C1_DEMAND_AND_MARKET_OPPORTUNITY",
    "C2": "C2_OPERATING_ENVIRONMENT",
    "C3": "C3_ECONOMIC_ATTRACTIVENESS",
    "C4": "C4_REGULATORY_AND_AUTONOMY_READINESS",
    "C5": "C5_INFRASTRUCTURE_AND_MODE_FIT",
}
ACS = ("S-03", "ACS 5-year 2020-2024")
PEP = ("S-01", "PEP Vintage 2025")
CBP = ("S-08 + S-01", "CBP 2023 / PEP V2025")
OEWS = ("S-09", "OEWS May 2025")
NOAA = ("S-12", "NOAA Normals 1991-2020")
LINE = "INTERMEDIATE.int_market__production_features"

# --------------------------------------------------------------------------------------------------
# Production feature definitions (base features shared across modes).
# phase5: the Phase 5 feature name whose decision this feature implements.
# --------------------------------------------------------------------------------------------------
BASE = {
    "PF01": dict(feature_name="population_2025_log1p", phase5="population_2025",
                 description="Natural log of (1 + PEP July 2025 resident population): addressable market size",
                 source=PEP, unit="ln(persons)", transformation="LOG1P",
                 direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="More residents = larger addressable market; log reflects diminishing marginal value of size across a 9x range",
                 lineage=f"dim_market -> {LINE}",
                 limitation="Metro-wide count; early services cover only part of a CBSA (A-002)"),
    "PF02": dict(feature_name="pw_tract_density_log1p", phase5="pw_tract_density",
                 description="Natural log of (1 + population-weighted tract density, D2): density experienced by the average resident",
                 source=("S-04 + S-05", "ACS 2020-2024 tracts / Gazetteer 2024"), unit="ln(persons per sq mi)",
                 transformation="POPULATION_WEIGHTED + LOG1P", direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="Denser demand means shorter trips/deliveries and higher vehicle utilization",
                 lineage=f"fct_tract_population_land -> int_market__population_weighted_density -> {LINE}",
                 limitation="New York excludes 14 Suffolk tracts without ACS records, not imputed (A-029, -0.31%)"),
    "PF03": dict(feature_name="share_taxi_or_ride_hailing", phase5="share_taxi_or_ride_hailing",
                 description="Share of workers 16+ commuting by taxicab or ride-hailing (ACS B08301_016 / B08301_001)",
                 source=ACS, unit="share (0-1)", transformation="PER_CAPITA", direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="Revealed local demand for hailed, paid point-to-point rides",
                 lineage=f"fct_market_acs_demographics -> {LINE}",
                 limitation="Commute trips only; pandemic-era window (A-018); largest sampling error of the kept measures (CV <= 14.6%)"),
    "PF04": dict(feature_name="enplanements_per_resident_log1p", phase5="enplanements_inside_cbsa_per_capita",
                 description="Natural log of (1 + CY2025 enplanements at commercial-service airports inside the market's official counties per resident): market-embedded airport activity (A1)",
                 source=("S-17 + S-40 + S-01", "FAA CY2025 / Census Geocoder ACS2024 / PEP V2025"),
                 unit="ln(enplanements per resident)", transformation="PER_CAPITA + LOG1P",
                 direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="Airport trips are a core paid ride segment; log damps connecting-hub inflation",
                 lineage=f"int_airports__airport_market_assignment -> int_market__airport_activity -> {LINE}",
                 limitation="Includes connecting passengers at hubs (A-010); not the full aviation catchment (A-009)"),
    "PF05": dict(feature_name="median_household_income_usd", phase5="median_household_income_usd",
                 description="ACS median household income (2024 inflation-adjusted USD): customer purchasing power",
                 source=ACS, unit="USD", transformation="NONE", direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="Higher purchasing power supports paying for premium on-demand services",
                 lineage=f"fct_market_acs_demographics -> {LINE}",
                 limitation="Nominal; no regional price-parity adjustment (A-036); correlated with wages (A-035)"),
    "PF06": dict(feature_name="establishments_per_1k_pop", phase5="establishments_per_1k_pop",
                 description="All-sector business establishments (CBP 2023) per 1,000 residents: commercial activity",
                 source=CBP, unit="establishments per 1,000 residents", transformation="PER_CAPITA",
                 direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="More businesses per resident = more work, errand and business trip attractors",
                 lineage=f"fct_market_business_patterns -> {LINE}",
                 limitation="Establishment counts are not trip volumes; CBP noise infusion; 2023 counts over 2025 population (A-003)"),
    "PF07": dict(feature_name="retail_establishments_per_10k_pop", phase5="retail_per_10k_pop",
                 description="Retail trade establishments (NAICS 44-45, CBP 2023) per 10,000 residents: retail delivery origins",
                 source=CBP, unit="establishments per 10,000 residents", transformation="PER_CAPITA",
                 direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="More retail merchants per resident = more potential delivery origins",
                 lineage=f"fct_market_business_patterns -> {LINE}",
                 limitation="Counts are not order volumes (A-019)"),
    "PF08": dict(feature_name="restaurants_per_10k_pop", phase5="restaurants_per_10k_pop",
                 description="Restaurants and other eating places (NAICS 7225, CBP 2023) per 10,000 residents: food delivery origins",
                 source=CBP, unit="establishments per 10,000 residents", transformation="PER_CAPITA",
                 direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="More restaurants per resident = more potential food delivery origins",
                 lineage=f"fct_market_business_patterns -> {LINE}",
                 limitation="Counts are not order volumes (A-019)"),
    "PF09": dict(feature_name="shuttle_chauffeur_median_annual_wage_usd",
                 phase5="oews_annual_median_wage_shuttle_drivers_chauffeurs",
                 description="OEWS annual median wage, 53-3053 Shuttle Drivers and Chauffeurs: cost of the human-driver alternative",
                 source=OEWS, unit="USD per year", transformation="NONE", direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="A costlier human driver raises the economic value of driverless operation",
                 lineage=f"fct_market_occupation_wages -> int_market__labor_cost -> {LINE}",
                 limitation="Excludes self-employed ride-hail drivers (A-017); scheduled-service occupation, not taxi (53-3054 dropped)"),
    "PF10": dict(feature_name="courier_median_annual_wage_usd", phase5="oews_annual_median_wage_couriers_messengers",
                 description="OEWS annual median wage, 43-5021 Couriers and Messengers: cost of the human delivery alternative",
                 source=OEWS, unit="USD per year", transformation="NONE", direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="A costlier human courier raises the economic value of autonomous delivery",
                 lineage=f"fct_market_occupation_wages -> int_market__labor_cost -> {LINE}",
                 limitation="Employee couriers only; app-based gig couriers excluded (A-017)"),
    "PF11": dict(feature_name="days_precip_ge_010_in", phase5="days_precip_ge_010_in",
                 description="Normal days per year with precipitation >= 0.10 in at the W5 climate station",
                 source=NOAA, unit="days per year", transformation="NONE", direction="LOWER_IS_MORE_FAVORABLE",
                 direction_rationale="Wet days degrade sensors and traction and interrupt operations",
                 lineage=f"fct_station_climate_normals -> int_weather__market_station_selection -> int_market__climate -> {LINE}",
                 limitation="One station represents the metro (A-007)"),
    "PF12": dict(feature_name="days_tmax_ge_90f", phase5="days_tmax_ge_90f",
                 description="Normal days per year with maximum temperature >= 90 F at the W5 climate station",
                 source=NOAA, unit="days per year", transformation="NONE", direction="LOWER_IS_MORE_FAVORABLE",
                 direction_rationale="Heat stresses batteries, electronics and sensors",
                 lineage=f"fct_station_climate_normals -> int_weather__market_station_selection -> int_market__climate -> {LINE}",
                 limitation="One station represents the metro (A-007)"),
    "PF13": dict(feature_name="annual_snowfall_in", phase5="annual_snowfall_in",
                 description="Normal annual snowfall at the W5 snow station",
                 source=NOAA, unit="inches per year", transformation="NONE", direction="LOWER_IS_MORE_FAVORABLE",
                 direction_rationale="Snow obscures lane markings, blocks sidewalks and grounds small aircraft",
                 lineage=f"fct_station_climate_normals -> int_weather__market_station_selection -> int_market__climate -> {LINE}",
                 limitation="5 markets use a snow station other than the climate station (<= 16.7 km, A-021)"),
    "PF14": dict(feature_name="annual_mean_wind_mph", phase5="annual_mean_wind_mph",
                 description="Climatological mean wind speed: mean of the 8,760 hourly normals (HLY-WIND-AVGSPD) at the nearest hourly-normals station",
                 source=("S-13", "NOAA Hourly Normals 1991-2020"), unit="mph", transformation="NONE",
                 direction="LOWER_IS_MORE_FAVORABLE",
                 direction_rationale="Higher mean wind implies more frequent exceedance of small-UAS wind limits (coarse proxy)",
                 lineage=f"fct_station_hourly_wind_normals -> int_weather__station_wind_summary -> int_market__climate -> {LINE}",
                 limitation="PROXY: not gusts or extremes; Austin station 81.8 km and Miami 34.4 km away (A-030)"),
    "PF15": dict(feature_name="population_weighted_walkability", phase5="walkability_pw_mean",
                 description="Population-weighted mean EPA National Walkability Index (1-20) over the market's block groups (NW1)",
                 source=("S-21/S-22", "EPA SLD v3.0"), unit="index 1-20", transformation="POPULATION_WEIGHTED",
                 direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="Connected, mixed-use, pedestrian-scale streets suit sidewalk robots",
                 lineage=f"fct_block_group_built_environment -> int_market__walkability -> {LINE}",
                 limitation="Relative index, 2017-2020 inputs (A-013); no-transit-data penalty (A-031)"),
    "PF16": dict(feature_name="share_single_family_detached", phase5="share_single_family_detached",
                 description="Share of housing units that are 1-unit detached (ACS B25024): yard-delivery, suburban-structure fit",
                 source=ACS, unit="share (0-1)", transformation="PER_CAPITA", direction="HIGHER_IS_MORE_FAVORABLE",
                 direction_rationale="Detached homes offer yard or driveway drop zones that drone delivery requires",
                 lineage=f"fct_market_acs_demographics -> {LINE}",
                 limitation="Lot size and tree cover unobserved; continuous measure chosen over a density threshold (A-037)"),
}

# Active features per mode and their single canonical component.
ACTIVE = {
    "RT": {"PF01": "C1", "PF02": "C1", "PF03": "C1", "PF04": "C1", "PF05": "C1",
           "PF06": "C3", "PF09": "C3", "PF11": "C2", "PF12": "C2", "PF13": "C2"},
    "SW": {"PF01": "C1", "PF02": "C1", "PF07": "C1", "PF08": "C1", "PF05": "C1",
           "PF10": "C3", "PF11": "C2", "PF12": "C2", "PF13": "C2", "PF15": "C5"},
    "DR": {"PF01": "C1", "PF07": "C1", "PF08": "C1", "PF05": "C1",
           "PF10": "C3", "PF11": "C2", "PF12": "C2", "PF13": "C2", "PF14": "C2", "PF16": "C5"},
}

# Diagnostic and explicitly dropped rows (never scoring inputs).
NON_ACTIVE = [
    # (feature_id, mode, component, status, feature_name, phase5_name, description, unit, reason)
    ("PF06", "SW", "C3", "DIAGNOSTIC", None, None, None, None,
     "Retail and restaurants are subsets of all establishments: the nested measures are kept as the delivery-specific signals"),
    ("PF06", "DR", "C3", "DIAGNOSTIC", None, None, None, None,
     "Retail and restaurants are subsets of all establishments: the nested measures are kept as the delivery-specific signals"),
    ("PX01", "RT", "C1", "DIAGNOSTIC", "raw_msa_density_diagnostic", "raw_density_per_sq_mi",
     "PEP 2025 population / CBSA land area (D1)", "persons per sq mi",
     "Rejected density method (rho 0.57 with D2); diagnostic only"),
    ("PX02", "RT", "C1", "DIAGNOSTIC", "pw_block_group_density_sld2018_diagnostic", None,
     "Population-weighted block-group density, EPA SLD 2018 inputs (D3)", "persons per sq mi",
     "Backup density method (rho 0.99 with D2); sensitivity only"),
    ("PX03", "RT", "C1", "DIAGNOSTIC", "a4_enplanements_per_resident_diagnostic", None,
     "A4 enplanements per resident: inside-market airports, else nearest market centre within 80 km",
     "enplanements per resident", "A4 sensitivity alternative to A1 (rho 0.994); not a production feature"),
    ("PX04", "DR", "C2", "DIAGNOSTIC", "p90_of_hourly_normals_mph_diagnostic", None,
     "90th percentile of the 8,760 climatological hourly mean wind speeds", "mph",
     "Not an extreme-wind percentile: a percentile of hourly MEANS; rejected as the wind feature"),
    ("PD90", "DR", "C5", "DROPPED", "share_pop_tracts_lt_1000", "share_pop_tracts_lt_1000",
     "Share of residents in tracts below 1,000 persons per sq mi", "share (0-1)",
     "No operational or literature basis for a drone threshold; the 1,000/sq mi figure is a former Census urban-core criterion, not a drone limit. Continuous share_single_family_detached represents the concept"),
    ("PD91", "RT", "C3", "DROPPED", "oews_annual_median_wage_taxi_drivers", "oews_annual_median_wage_taxi_drivers",
     "OEWS annual median wage, 53-3054 Taxi Drivers", "USD per year",
     "Published for 7 of 35 markets (TOO_MISSING); never imputed; replaced by 53-3053"),
]

# Phase 5 DEFER features: canonical component they would belong to if ever activated, per mode.
DEFER_COMPONENT = {
    "mean_travel_time_minutes": "C1", "share_drove_alone": "C1", "share_public_transportation": "C1",
    "share_walked": "C5", "share_worked_from_home": "C1", "share_households_no_vehicle": "C1",
    "food_bev_retail_per_10k_pop": "C1", "couriers_per_100k_pop": "C3",
    "oews_annual_median_wage_light_truck_drivers": "C3", "transportation_occupations_median_wage": "C3",
    "state_count": "C4", "share_pop_tracts_ge_5000": "C5", "annual_precip_in": "C2", "days_tmin_le_32f": "C2",
    "share_pop_most_walkable": "C5", "intersection_density_pw_mean": "C5", "walkability_pw_mean": "C5",
    "pw_tract_density": "C5",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def freeze(audit: pd.DataFrame, digest: str) -> dict:
    problems = []
    if len(audit) != 70 or audit["feature_name"].duplicated().any():
        problems.append("expected 70 unique features")
    for c in ["decision", "decision_reason", "rationale"] + list(STATUS_COL.values()):
        if audit[c].isna().any() or (audit[c].astype(str).str.strip() == "").any():
            problems.append(f"blank {c}")
    allowed = {"KEEP", "MODIFY", "DEFER", "DROP"}
    counts = {}
    for m, c in STATUS_COL.items():
        bad = set(audit[c]) - allowed
        if bad:
            problems.append(f"{c} has {bad}")
        vc = audit[c].value_counts().to_dict()
        if sum(vc.values()) != 70:
            problems.append(f"{c} statuses do not sum to 70")
        counts[MODES[m]] = vc
    order = ["KEEP", "MODIFY", "DEFER", "DROP"]
    overall = audit[list(STATUS_COL.values())].apply(lambda r: next(s for s in order if s in set(r)), axis=1)
    if (overall != audit["decision"]).any():
        problems.append("overall decision inconsistent with mode statuses")
    if problems:
        raise SystemExit("Phase 5 decision table failed validation: " + "; ".join(problems))
    return {"artifact": "outputs/feature_audit.csv", "sha256": digest, "features": len(audit),
            "overall_decision_counts": audit["decision"].value_counts().to_dict(),
            "mode_status_counts": counts, "validation": "PASS"}


def build_contract(audit: pd.DataFrame) -> list[dict]:
    p5 = audit.set_index("feature_name")
    rows = []

    def row(fid, mode, comp, status, **kw):
        b = BASE.get(fid, {})
        p5name = kw.get("phase5", b.get("phase5"))
        src = kw.get("source", b.get("source", ("", "")))
        rows.append({
            "feature_id": fid, "feature_name": kw.get("feature_name") or b.get("feature_name"),
            "description": kw.get("description") or b.get("description"),
            "mode": MODES[mode], "component": COMPONENTS[comp],
            "source_id": src[0], "source_vintage": src[1],
            "unit": kw.get("unit") or b.get("unit"), "grain": "market (CBSA)",
            "transformation": kw.get("transformation", b.get("transformation", "NONE")),
            "direction": kw.get("direction", b.get("direction", "DEFER")),
            "direction_rationale": kw.get("direction_rationale", b.get("direction_rationale", "")),
            "missingness_policy": kw.get("missingness_policy",
                                         "REQUIRED_COMPLETE: no nulls allowed; no imputation" if status == "ACTIVE"
                                         else "NOT_IN_MODE_MART"),
            "lineage_model": kw.get("lineage", b.get("lineage", "not built (inactive)")),
            "phase5_feature_name": p5name,
            "phase5_status": p5.loc[p5name, STATUS_COL[mode]] if p5name in p5.index else "N/A",
            "production_status": status,
            "active_pre_regulation_flag": status == "ACTIVE",
            "known_limitation": kw.get("limitation", b.get("limitation", "")),
        })

    for mode, feats in ACTIVE.items():
        for fid, comp in feats.items():
            row(fid, mode, comp, "ACTIVE")
    for fid, mode, comp, status, name, p5name, desc, unit, reason in NON_ACTIVE:
        kw = {"limitation": reason, "direction": "NOT_APPLICABLE",
              "direction_rationale": "Not a scoring input", "transformation": "NONE"}
        if name:
            kw.update(feature_name=name, description=desc, unit=unit, phase5=p5name,
                      source=("various", "see lineage"),
                      lineage=f"{LINE}" if status == "DIAGNOSTIC" else "not built (dropped)")
        row(fid, mode, comp, status, **kw)

    # Phase 5 DEFER intensity features stay DEFERRED (direction or methodology unresolved).
    n = 0
    for name, r in p5.iterrows():
        for mode, col in STATUS_COL.items():
            if r[col] != "DEFER" or str(r["recommended_transformation"]).startswith("PER_CAPITA"):
                continue
            n += 1
            row(f"PD{n:02d}", mode, DEFER_COMPONENT[name], "DEFERRED", feature_name=name, phase5=name,
                description=f"Phase 5 candidate {r['feature_id']} ({name}); not engineered in Phase 6",
                unit="see feature_audit.csv", source=(str(r["source"]), "see feature_audit.csv"),
                direction="CONTEXT_DEPENDENT_OR_DEFER", direction_rationale=str(r["decision_reason"]),
                limitation=str(r["rationale"]))
    return rows


def crosswalk(audit: pd.DataFrame, contract: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, changes = [], []
    by = {(r.phase5_feature_name, r.mode): r for r in contract.itertuples()}
    for r in audit.itertuples():
        for mode, col in STATUS_COL.items():
            old = getattr(r, col)
            c = by.get((r.feature_name, MODES[mode]))
            tf = str(r.recommended_transformation)
            if c is not None:
                new, detail = c.production_status, f"{c.feature_id} {c.feature_name} ({c.component})"
            elif old == "DROP":
                new, detail = "DROPPED_IN_PHASE5", r.decision_reason
            elif tf.startswith("PER_CAPITA -> "):
                new, detail = "REPRESENTED_BY_INTENSITY_FORM", tf.split("-> ")[1]
            else:
                raise SystemExit(f"no Phase 6 disposition for {r.feature_name} / {mode} (Phase 5 {old})")
            rows.append({"phase5_feature_id": r.feature_id, "phase5_feature_name": r.feature_name,
                         "mode": MODES[mode], "phase5_status": old, "phase6_disposition": new, "detail": detail})
            changed = (old in ("KEEP", "MODIFY") and new not in ("ACTIVE", "REPRESENTED_BY_INTENSITY_FORM")) or \
                      (old in ("DEFER", "DROP") and new == "ACTIVE")
            if changed:
                changes.append({"feature": r.feature_name, "mode": MODES[mode], "OLD_DECISION": old,
                                "NEW_DECISION": new, "REASON": c.known_limitation if c is not None else detail})
    return pd.DataFrame(rows), pd.DataFrame(changes)


def main() -> int:
    digest = sha256(AUDIT)
    if digest != APPROVED_PHASE5_SHA256:
        raise SystemExit(f"outputs/feature_audit.csv changed since Phase 5 approval: {digest}")
    audit = pd.read_csv(AUDIT)
    frozen = freeze(audit, digest)
    contract = pd.DataFrame(build_contract(audit))
    if contract.duplicated(["feature_id", "mode"]).any():
        raise SystemExit("duplicate feature_id x mode in contract")
    if contract.duplicated(["feature_name", "mode"]).any():
        raise SystemExit("duplicate feature_name x mode in contract")
    active = contract[contract.production_status == "ACTIVE"]
    if (active.direction.isin(["HIGHER_IS_MORE_FAVORABLE", "LOWER_IS_MORE_FAVORABLE"]) == False).any():  # noqa: E712
        raise SystemExit("an ACTIVE feature lacks a resolved direction")
    xw, changes = crosswalk(audit, contract)

    OUT.mkdir(parents=True, exist_ok=True)
    contract.to_csv(CONTRACT, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    xw.to_csv(OUT / "phase5_to_phase6_crosswalk.csv", index=False, lineterminator="\n")
    changes.to_csv(OUT / "decision_changes.csv", index=False, lineterminator="\n")
    (OUT / "phase5_decision_freeze.json").write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")

    print(f"Phase 5 decision table: {frozen['validation']} | sha256 {digest}")
    print("contract rows:", contract.production_status.value_counts().to_dict())
    print("active per mode:", active.groupby("mode").size().to_dict())
    print("crosswalk:", xw.phase6_disposition.value_counts().to_dict())
    print("decision changes:", len(changes))
    for c in changes.itertuples():
        print(f"  {c.feature} / {c.mode}: {c.OLD_DECISION} -> {c.NEW_DECISION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
