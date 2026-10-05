"""Phase 5: reproducible feature audit and mapping-method evaluation.

Reads the dbt warehouse (read-only, AM_TRANSFORMER) and writes derived, small,
reproducible outputs to outputs/ (CSV + PNG figures). Nothing is written to
Snowflake. Nothing is scored, weighted or ranked.

Usage (repository root, .venv active):
    python scripts/run_feature_audit.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.analytics import diagnostics as dg  # noqa: E402
from src.analytics import feature_audit as fa  # noqa: E402
from src.analytics import mapping_evaluation as me  # noqa: E402
from src.analytics.data_access import Warehouse  # noqa: E402
from src.analytics.feature_decisions import (MAPPING_CANDIDATES, MISSING_CAUSES,  # noqa: E402
                                             build_decision_table)

OUT = ROOT / "outputs"
FIG = OUT / "figures"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    wh = Warehouse()
    try:
        mart = fa.load_mart(wh)
        dim = wh.table("CORE", "DIM_MARKET").set_index("market_id").sort_index()
        assert len(mart) == 35 and len(dim) == 35 and set(mart.index) == set(dim.index), "35-market universe broken"
        df = fa.add_intensity(mart)
        names = dim["cbsa_name"]

        # ---------------- mapping-method evaluation ----------------
        cent = me.pw_centroids(wh)
        dens = me.density_methods(wh, dim)
        weather, weather_ring = me.weather_methods(wh, dim, cent)
        wind = me.hourly_wind_summary(wh, weather["W5_wind_station"].dropna().tolist())
        weather = weather.join(wind[["annual_mean_wind_mph", "p90_hourly_mean_wind_mph", "mean_pct_calm",
                                     "missing_hours"]], on="W5_wind_station")
        ap_match = me.airport_county_match(wh)
        airports, ap_detail = me.airport_methods(wh, dim, cent, ap_match)
        walk = me.walkability_methods(wh)
        wages = wh.query("""
            select market_id, occupation_code, occupation_title, annual_median_wage_usd,
                   annual_median_wage_usd_marker, total_employment
            from AUTONOMOUS_MOBILITY.CORE.FCT_MARKET_OCCUPATION_WAGES
            where occupation_code in ('53-0000','53-3031','53-3033','53-3053','53-3054','43-5021','35-3023','00-0000')""")
        wage_wide = wages.pivot(index="market_id", columns="occupation_code", values="annual_median_wage_usd")

        # Mapping-derived candidate measures joined for the audit (local only).
        mapped = pd.DataFrame(index=dim.index)
        mapped["pw_tract_density"] = dens["D2_pw_tract_density"]
        mapped["central_county_density"] = dens["D4_central_county_density"]
        mapped["share_pop_tracts_ge_5000"] = dens["D5_share_pop_tracts_ge_5000"]
        mapped["share_pop_tracts_lt_1000"] = dens["share_pop_tracts_lt_1000"]
        for e in me.CORE_ELEMENTS:                     # W5 = candidate recommended station rule
            mapped[e] = weather[f"W5_{e}"]
        mapped["annual_snowfall_in"] = weather["W5_annual_snowfall_in"]
        mapped["annual_mean_wind_mph"] = weather["annual_mean_wind_mph"]
        mapped["enplanements_inside_cbsa_per_capita"] = airports["A1_inside_cbsa_per_capita"]
        mapped["enplanements_inside_cbsa"] = airports["A1_inside_cbsa_enplanements"]
        mapped["walkability_pw_mean"] = walk["NW1_pop_weighted_mean"]
        mapped["share_pop_most_walkable"] = walk["NW5_share_pop_most_walkable_ge_15_26"]
        mapped["intersection_density_pw_mean"] = walk["D3B_pop_weighted_intersection_density"]
        mapped["transportation_occupations_median_wage"] = wage_wide["53-0000"]
        df = df.join(mapped)

        # ---------------- feature audit ----------------
        inv = fa.inventory(df, MAPPING_CANDIDATES)
        inv["transformation_hint"] = inv.apply(fa.transformation_hint, axis=1)
        miss = fa.missingness(df, inv, MISSING_CAUSES)
        var = fa.variation_flags(inv)
        numeric = inv.loc[inv["scale_type"] != "STRUCTURAL", "feature_name"].tolist()
        outl = fa.outliers(df, numeric, names)
        pear, spear = fa.correlations(df, numeric)
        pairs = fa.strong_pairs(pear, spear)
        comps = fa.redundancy_components(spear)
        size = fa.size_duplication(df, numeric)
        moe = fa.moe_quality(df, [(c, f"{c}_moe") for c in [
            "median_household_income_usd", "workers_taxi_or_ride_hailing", "workers_bicycle", "workers_walked",
            "workers_public_transportation", "households_no_vehicle", "mean_travel_time_minutes"]])

        intensity_cols = [c for c in inv.loc[inv["scale_type"] == "INTENSITY", "feature_name"]
                          if df[c].notna().all()]
        clus = dg.clustering_feasibility(df[intensity_cols].astype(float))

        decisions = build_decision_table(inv, miss, size, comps)

        # ---------------- outputs ----------------
        inv.to_csv(OUT / "feature_inventory.csv", index=False)
        miss.to_csv(OUT / "missingness.csv", index=False)
        var.to_csv(OUT / "variation_flags.csv", index=False)
        outl.to_csv(OUT / "outliers.csv", index=False)
        pear.round(3).to_csv(OUT / "correlation_pearson.csv")
        spear.round(3).to_csv(OUT / "correlation_spearman.csv")
        pairs.to_csv(OUT / "strong_correlation_pairs.csv", index=False)
        size.to_csv(OUT / "size_duplication.csv", index=False)
        moe.to_csv(OUT / "acs_reliability.csv", index=False)
        dens.join(names).round(4).to_csv(OUT / "density_methods.csv")
        weather.round(3).to_csv(OUT / "weather_station_methods.csv")
        airports.round(4).to_csv(OUT / "airport_methods.csv")
        ap_detail.to_csv(OUT / "airport_county_match.csv", index=False)
        walk.join(names).round(4).to_csv(OUT / "walkability_methods.csv")
        wages.to_csv(OUT / "wage_coverage.csv", index=False)
        decisions.to_csv(OUT / "feature_audit.csv", index=False)
        with open(OUT / "clustering_feasibility.json", "w", encoding="utf-8") as f:
            json.dump({k: (v.round(4).tolist() if isinstance(v, np.ndarray) else v) for k, v in clus.items()},
                      f, indent=2, default=str)
        diag = pd.concat({"density": dens.drop(columns=[c for c in dens.columns if c.startswith("tracts")]),
                          "airport": airports.select_dtypes("number")}, axis=1)
        diag.columns = [f"{a}__{b}" for a, b in diag.columns]
        diag.join(names).round(4).to_csv(OUT / "mapping_diagnostics.csv")

        # ---------------- figures ----------------
        figs = [
            dg.missingness_chart(miss, FIG / "01_missingness.png"),
            dg.correlation_heatmap(spear, FIG / "02_spearman_correlation.png",
                                   "Spearman correlation among candidate measures (35 markets)"),
            dg.distributions(df, numeric, FIG / "03_distributions.png"),
            dg.scatter_pair(df["population_2025"], df["cbp_establishments_restaurants"], names,
                            FIG / "04a_scale_restaurants_vs_population.png",
                            "Absolute restaurant count tracks market size", "Population 2025 (log)",
                            "Restaurants, NAICS 7225 (log)", logx=True, logy=True),
            dg.scatter_pair(df["population_2025"], df["restaurants_per_10k_pop"], names,
                            FIG / "04b_intensity_restaurants_vs_population.png",
                            "Restaurants per 10,000 residents is largely independent of size",
                            "Population 2025 (log)", "Restaurants per 10k residents", logx=True),
            dg.scatter_pair(dens["D1_raw_msa_density"], dens["D2_pw_tract_density"], names,
                            FIG / "05_density_raw_vs_population_weighted.png",
                            "Raw MSA density vs population-weighted tract density",
                            "Raw density, persons / sq mi (log)", "Population-weighted density (log)",
                            logx=True, logy=True, diagonal=True),
            dg.dot_comparison(weather.join(names, rsuffix="_n").assign(cbsa_name=names),
                              ["W1_distance_km", "W3_distance_km", "W5_distance_km"],
                              ["W1 nearest any station to CBSA internal point (rejected)",
                               "W3 nearest qualifying first-order station, no distance cap",
                               "W5 recommended: first-order <= 25 km, else nearest qualifying"],
                              FIG / "06_weather_station_distance.png",
                              "Distance to the candidate station under each rule", "km"),
            dg.scatter_pair(airports["A1_inside_cbsa_per_capita"], airports["A2_within_80km_per_capita"], names,
                            FIG / "07_airport_inside_vs_radius.png",
                            "Enplanements per resident: inside CBSA vs within 80 km",
                            "Inside-CBSA enplanements per resident", "Within-80 km enplanements per resident",
                            diagonal=True, label_extremes=6),
            dg.scatter_pair(walk["NW2_simple_mean"], walk["NW1_pop_weighted_mean"], names,
                            FIG / "08_walkability_simple_vs_pop_weighted.png",
                            "Walkability: simple block-group mean vs population-weighted mean",
                            "Simple mean of NatWalkInd", "Population-weighted mean of NatWalkInd", diagonal=True),
            dg.scree(clus["pca_explained"], FIG / "09_pca_scree.png"),
        ]

        # ---------------- console summary ----------------
        print(f"markets: {len(df)} | candidates audited: {len(inv)} | figures: {len(figs)}")
        print("missing (>0):", miss.loc[miss.missing_count > 0, ["feature_name", "missing_count", "cause_class"]]
              .to_string(index=False))
        print("near-zero / low-unique:", var.loc[var.near_zero_variance | var.low_unique, "feature_name"].tolist())
        print("strong pairs:", len(pairs), "| redundancy components:", len(comps))
        for c in comps:
            print("  component:", c)
        print("duplicates market size:", size.loc[size.duplicates_market_size, "feature_name"].tolist())
        print("outlier flags:", len(outl), "| features with flags:", outl["feature_name"].nunique() if len(outl) else 0)
        print("clustering:", {k: clus[k] for k in ("n_markets", "n_features", "pcs_for_80pct")},
              "hopkins mean", round(float(np.mean(clus["hopkins"])), 3),
              "silhouette", {k: round(v, 3) for k, v in clus["silhouette"].items()},
              "stability", {k: round(v, 3) for k, v in clus["co_membership_stability"].items()},
              "sizes", clus["cluster_sizes"])
        print("decision counts:", decisions["decision"].value_counts().to_dict())
        return 0
    finally:
        wh.close()


if __name__ == "__main__":
    sys.exit(main())
