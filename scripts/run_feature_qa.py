"""Phase 6 feature QA and reconciliation (read-only, AM_TRANSFORMER).

For every ACTIVE production feature in each mode mart: count, missing, min, median, mean, max,
std, unique values, plus checks for impossible values, infinities, duplicate markets and per-capita
denominators. Re-runs Pearson and Spearman correlation inside each final mode feature set and
reports every |Spearman rho| >= 0.80 pair (QA only: nothing is removed automatically).
Also writes the mapping reconciliation counts (stations, airports, tracts, block groups).

Nothing is written to Snowflake. No scores, weights or rankings.

Usage (repository root, .venv active):
    python scripts/run_feature_qa.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.analytics.data_access import Warehouse  # noqa: E402

OUT = ROOT / "outputs" / "phase6"
MARTS = {"ROBOTAXI": "MART_ROBOTAXI_FEATURES", "SIDEWALK_DELIVERY": "MART_SIDEWALK_DELIVERY_FEATURES",
         "DRONE_DELIVERY": "MART_DRONE_DELIVERY_FEATURES"}
STRONG = 0.80
DB = "AUTONOMOUS_MOBILITY"


def feature_stats(mode: str, df: pd.DataFrame, feats: pd.DataFrame) -> list[dict]:
    rows = []
    for f in feats.itertuples():
        v = pd.to_numeric(df[f.feature_name], errors="coerce").astype(float)
        share_like = f.unit.startswith("share")
        impossible = int(((v < 0) | (share_like & (v > 1))).sum())
        rows.append({"mode": mode, "feature_id": f.feature_id, "feature_name": f.feature_name,
                     "component": f.component, "unit": f.unit, "direction": f.direction,
                     "transformation": f.transformation, "count": int(v.notna().sum()),
                     "missing": int(v.isna().sum()), "min": v.min(), "median": v.median(), "mean": v.mean(),
                     "max": v.max(), "std": v.std(ddof=1), "unique_values": int(v.nunique()),
                     "infinite_values": int(np.isinf(v).sum()), "impossible_values": impossible})
    return rows


def strong_pairs(mode: str, df: pd.DataFrame, cols: list[str]) -> tuple[list[dict], pd.DataFrame]:
    x = df[cols].astype(float)
    pear, spear = x.corr(), x.rank().corr()          # Spearman = Pearson on ranks
    rows = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            if abs(spear.loc[a, b]) >= STRONG or abs(pear.loc[a, b]) >= STRONG:
                rows.append({"mode": mode, "feature_a": a, "feature_b": b,
                             "pearson": round(pear.loc[a, b], 3), "spearman": round(spear.loc[a, b], 3),
                             "spearman_ge_080": abs(spear.loc[a, b]) >= STRONG})
    return rows, spear.round(3)


def reconciliation(wh: Warehouse) -> pd.DataFrame:
    q = lambda sql: wh.query(sql).iloc[0, 0]  # noqa: E731
    I, C = f"{DB}.INTERMEDIATE", f"{DB}.CORE"
    rows = [
        ("density", "market tracts (Gazetteer 2024, July 2023 delineation)",
         q(f"select sum(tract_count) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("density", "tracts with ACS 2020-2024 population", q(f"select sum(tracts_with_population) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("density", "tracts missing ACS population (A-029, New York only)", q(f"select sum(tracts_missing_population) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("density", "zero-land-area tracts excluded", q(f"select sum(tracts_zero_land_area) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("density", "tracts used in D2", q(f"select sum(tracts_used) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("density", "tract population used in D2", q(f"select sum(population_used) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("density", "ACS CBSA population, 35 markets", q(f"select sum(acs_cbsa_total_population) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("density", "minimum population coverage (New York)", q(f"select min(population_coverage_pct) from {I}.INT_MARKET__POPULATION_WEIGHTED_DENSITY")),
        ("weather", "stations considered per market (with coordinates)", q(f"select max(stations_considered) from {I}.INT_WEATHER__MARKET_STATION_SELECTION")),
        ("weather", "core-qualifying stations", q(f"select count_if(is_core_qualifying) from {I}.INT_WEATHER__STATION_QUALIFICATION")),
        ("weather", "snow-qualifying stations", q(f"select count_if(is_snow_qualifying) from {I}.INT_WEATHER__STATION_QUALIFICATION")),
        ("weather", "hourly-wind stations", q(f"select count_if(has_hourly_wind_normals) from {I}.INT_WEATHER__STATION_QUALIFICATION")),
        ("weather", "stations classified PLCD by NOAA HOMR (as of 2020-12-31)", q(f"select count_if(is_plcd) from {I}.INT_WEATHER__STATION_CLASS")),
        ("weather", "core-qualifying PLCD stations", q(f"select count_if(is_core_qualifying and is_plcd) from {I}.INT_WEATHER__STATION_QUALIFICATION")),
        ("weather", "core-qualifying WBAN-numbered ('USW') stations that are NOT PLCD", q(f"select count_if(is_core_qualifying and is_wban_numbered and not is_plcd) from {I}.INT_WEATHER__STATION_QUALIFICATION")),
        ("weather", "normals stations without an EMSHR record", q(f"select count_if(not has_emshr_record) from {I}.INT_WEATHER__STATION_CLASS")),
        ("weather", "markets: PLCD station within 25 km", q(f"select count_if(selection_rule = 'PLCD_WITHIN_25KM') from {I}.INT_WEATHER__MARKET_STATION_SELECTION")),
        ("weather", "markets: nearest qualifying any-network fallback", q(f"select count_if(selection_rule = 'NEAREST_QUALIFYING_ANY_NETWORK') from {I}.INT_WEATHER__MARKET_STATION_SELECTION")),
        ("weather", "markets: snow from the climate station", q(f"select count_if(selection_rule = 'SAME_AS_GENERAL_STATION') from {I}.INT_WEATHER__MARKET_STATION_SELECTION")),
        ("weather", "markets: snow fallback within 50 km", q(f"select count_if(selection_rule = 'SNOW_FALLBACK_WITHIN_50KM') from {I}.INT_WEATHER__MARKET_STATION_SELECTION")),
        ("weather", "markets: snow not published", q(f"select count_if(selection_rule = 'SOURCE_NOT_PUBLISHED') from {I}.INT_WEATHER__MARKET_STATION_SELECTION")),
        ("weather", "markets: wind station > 25 km", q(f"select count_if(station_role = 'WIND' and distance_exceeds_25km_flag) from {I}.INT_WEATHER__MARKET_STATION_SELECTION")),
        ("airports", "commercial-service airports (FAA CY2025)", q(f"select count(*) from {C}.FCT_AIRPORT_ENPLANEMENTS")),
        ("airports", "airports with an official county (Census Geocoder)", q(f"select count(county_fips) from {I}.INT_AIRPORTS__AIRPORT_MARKET_ASSIGNMENT")),
        ("airports", "airports inside a frozen market (A1)", q(f"select count(a1_market_id) from {I}.INT_AIRPORTS__AIRPORT_MARKET_ASSIGNMENT")),
        ("airports", "enplanements at A1 airports", q(f"select sum(enplanements_cy2025) from {I}.INT_AIRPORTS__AIRPORT_MARKET_ASSIGNMENT where a1_market_id is not null")),
        ("airports", "enplanements summed over markets", q(f"select sum(enplanements_cy2025) from {I}.INT_MARKET__AIRPORT_ACTIVITY")),
        ("airports", "airports whose NASR county name differs from the official county",
         q(f"select count_if(upper(regexp_replace(county_name_official, ' (County|Parish|Borough|Census Area|Municipio|city)$', '')) "
           f"<> upper(county_name_nasr)) from {I}.INT_AIRPORTS__AIRPORT_MARKET_ASSIGNMENT where a1_market_id is not null")),
        ("walkability", "market block groups (SLD v3.0)", q(f"select sum(block_groups_total) from {I}.INT_MARKET__WALKABILITY")),
        ("walkability", "block groups used (index published, population > 0)", q(f"select sum(block_groups_used) from {I}.INT_MARKET__WALKABILITY")),
        ("walkability", "block groups with zero population", q(f"select sum(block_groups_zero_population) from {I}.INT_MARKET__WALKABILITY")),
        ("walkability", "populated block groups missing the index", q(f"select sum(block_groups_missing_index_with_population) from {I}.INT_MARKET__WALKABILITY")),
        ("walkability", "SLD population covered / total", q(f"select sum(population_covered) / sum(population_total_sld) from {I}.INT_MARKET__WALKABILITY")),
        ("walkability", "block groups whose SLD CBSA differs from 2023 (not used)", q(f"select sum(block_groups_sld_cbsa_differs) from {I}.INT_MARKET__WALKABILITY")),
    ]
    return pd.DataFrame(rows, columns=["area", "measure", "value"])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    wh = Warehouse()
    try:
        dim = wh.query(f"select * from {DB}.ANALYTICS.DIM_FEATURE")
        stats, pairs, problems = [], [], []
        dim_market = wh.query(f"select market_id from {DB}.CORE.DIM_MARKET")
        for mode, table in MARTS.items():
            df = wh.query(f"select * from {DB}.ANALYTICS.{table}")
            feats = dim[(dim["mode"] == mode) & (dim["production_status"] == "ACTIVE")].sort_values("feature_id")
            if len(df) != 35 or df["market_id"].duplicated().any() or set(df["market_id"]) != set(dim_market["market_id"]):
                problems.append(f"{mode}: market grain broken")
            s = feature_stats(mode, df, feats)
            stats += s
            for r in s:
                if r["missing"] or r["infinite_values"] or r["impossible_values"]:
                    problems.append(f"{mode}.{r['feature_name']}: missing/inf/impossible")
            p, spear = strong_pairs(mode, df, list(feats["feature_name"]))
            pairs += p
            spear.to_csv(OUT / f"spearman_{mode.lower()}.csv")
        denominators = wh.query(f"""
            select min(d.population_2025) as min_population, min(a.workers_16_plus) as min_workers,
                   min(a.housing_units_total) as min_housing_units
            from {DB}.CORE.DIM_MARKET d join {DB}.CORE.FCT_MARKET_ACS_DEMOGRAPHICS a using (market_id)""")
        if (denominators.iloc[0] <= 0).any():
            problems.append("a per-capita denominator is not positive")
        recon = reconciliation(wh)
    finally:
        wh.close()

    st = pd.DataFrame(stats)
    st.round(6).to_csv(OUT / "feature_qa_stats.csv", index=False, lineterminator="\n")
    pr = pd.DataFrame(pairs, columns=["mode", "feature_a", "feature_b", "pearson", "spearman", "spearman_ge_080"])
    pr.to_csv(OUT / "final_strong_correlation_pairs.csv", index=False, lineterminator="\n")
    recon.to_csv(OUT / "feature_reconciliation.csv", index=False, lineterminator="\n")

    print("active features by mode:", st.groupby("mode").size().to_dict())
    print("denominators (min):", denominators.iloc[0].to_dict(), "| per-capita denominators > 0:", bool((denominators.iloc[0] > 0).all()))
    print("QA problems:", problems or "none")
    print("strong pairs (|r| or |rho| >= 0.80):")
    print(pr.to_string(index=False) if len(pr) else "  none")
    print(recon.to_string(index=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
