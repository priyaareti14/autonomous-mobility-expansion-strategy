"""Phase 5 evaluation of the deferred mapping decisions:
density (A-008), weather station (A-007/A-021), airport (A-009) and built-environment
aggregation.

Every method is computed side by side for all 35 markets so the choice rests on
evidence. These are exploratory candidate measures: they stay local (outputs/) and
are not published to Snowflake.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

EARTH_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------------------
# Shared geography: population-weighted centroid from ACS tracts
# ---------------------------------------------------------------------------
def tracts(wh) -> pd.DataFrame:
    return wh.table("CORE", "FCT_TRACT_POPULATION_LAND")


def pw_centroids(wh) -> pd.DataFrame:
    """Population-weighted mean of tract internal points (tracts with ACS population)."""
    t = tracts(wh)
    t = t[t["has_acs_population"] & (t["total_population"] > 0)]
    g = t.groupby("market_id")
    return pd.DataFrame({
        "pw_lat": g.apply(lambda d: np.average(d["internal_point_latitude"], weights=d["total_population"])),
        "pw_lon": g.apply(lambda d: np.average(d["internal_point_longitude"], weights=d["total_population"])),
    })


# ---------------------------------------------------------------------------
# A-008 density
# ---------------------------------------------------------------------------
def density_methods(wh, dim: pd.DataFrame) -> pd.DataFrame:
    t = tracts(wh)
    valid = t[t["has_acs_population"] & (t["land_area_sq_mi"] > 0)].copy()
    valid["tract_density"] = valid["total_population"] / valid["land_area_sq_mi"]

    def pwd(d):
        return np.average(d["tract_density"], weights=d["total_population"]) if d["total_population"].sum() else np.nan

    out = pd.DataFrame(index=dim.index)
    out["D1_raw_msa_density"] = dim["population_2025"] / dim["land_area_sq_mi"]
    out["D2_pw_tract_density"] = valid.groupby("market_id").apply(pwd)

    bg = wh.table("CORE", "FCT_BLOCK_GROUP_BUILT_ENVIRONMENT")
    bg = bg[(bg["land_acres"] > 0) & (bg["total_population_sld"] > 0)].copy()
    bg["bg_density"] = bg["total_population_sld"] / (bg["land_acres"] / 640.0)
    out["D3_pw_block_group_density_sld2018"] = bg.groupby("market_id").apply(
        lambda d: np.average(d["bg_density"], weights=d["total_population_sld"]))

    cty = wh.table("CORE", "BRG_MARKET_COUNTY")
    central = cty[cty["central_outlying"] == "Central"].groupby("market_id")
    out["D4_central_county_density"] = central["county_population_2025"].sum() / central["county_land_area_sq_mi"].sum()

    for thr in (2500, 5000, 10000):
        hi = valid.assign(h=valid["tract_density"] >= thr)
        out[f"D5_share_pop_tracts_ge_{thr}"] = hi.groupby("market_id").apply(
            lambda d: d.loc[d["h"], "total_population"].sum() / d["total_population"].sum())
    low = valid.assign(l=valid["tract_density"] < 1000)
    out["share_pop_tracts_lt_1000"] = low.groupby("market_id").apply(
        lambda d: d.loc[d["l"], "total_population"].sum() / d["total_population"].sum())

    # Diagnostics
    out["pw_to_raw_ratio"] = out["D2_pw_tract_density"] / out["D1_raw_msa_density"]
    land_share_zero = t.groupby("market_id").apply(lambda d: (d["land_area_sq_mi"] == 0).sum())
    out["tracts_used"] = valid.groupby("market_id").size()
    out["tracts_zero_land_excluded"] = land_share_zero
    out["tracts_without_acs"] = t[~t["has_acs_population"]].groupby("market_id").size().reindex(out.index).fillna(0)
    return out


# ---------------------------------------------------------------------------
# A-007 / A-021 weather station
# ---------------------------------------------------------------------------
CORE_ELEMENTS = ["annual_precip_in", "days_precip_ge_010_in", "days_tmax_ge_90f", "days_tmin_le_32f",
                 "annual_mean_temp_f"]
SNOW_ELEMENTS = ["annual_snowfall_in", "days_snowfall_ge_1_in", "days_snow_depth_ge_1_in"]
# NCEI completeness flags (annual/seasonal readme): S Standard (WMO, >=24 yrs, gaps filled),
# R Representative (WMO, >=10 yrs, gaps filled), P Provisional (>=10 yrs, gaps NOT fillable),
# E Estimated (>=2 yrs). "Qualifying" = S or R: both meet WMO availability standards with gaps filled.
GOOD_FLAGS = {"S", "R"}
SNOW_FLAGS = {"S", "P"}
FIRST_ORDER_MAX_KM = 25       # beyond this, a first-order airport station is a different climate setting
SNOW_FALLBACK_MAX_KM = 50      # snow borrowed from a nearby station only within this distance


def station_table(wh) -> pd.DataFrame:
    st = wh.table("CORE", "DIM_WEATHER_STATION").set_index("station_id")
    cn = wh.table("CORE", "FCT_STATION_CLIMATE_NORMALS").set_index("station_id")
    df = st.join(cn, how="left")
    df["core_complete"] = np.logical_and.reduce(
        [df[e].notna() & df[f"{e}_comp_flag"].isin(GOOD_FLAGS) for e in CORE_ELEMENTS])
    # Snow normals are almost never S/R (of 5,749 publishing stations: 4,970 'P', 779 'S', no 'R'),
    # because NCEI cannot gap-fill snow. Qualifying snow therefore = S or P (>=10 yrs).
    df["snow_complete"] = np.logical_and.reduce(
        [df[e].notna() & df[f"{e}_comp_flag"].isin(SNOW_FLAGS) for e in SNOW_ELEMENTS[:2]])
    df["first_order"] = df.index.str.startswith("USW")
    return df


def weather_methods(wh, dim: pd.DataFrame, cent: pd.DataFrame, radius_km: float = 50.0
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    st = station_table(wh)
    st = st[st["latitude"].notna()]
    rows, detail = [], []
    for m, r in dim.iterrows():
        c = cent.loc[m]
        d_pw = haversine_km(c["pw_lat"], c["pw_lon"], st["latitude"].values, st["longitude"].values)
        d_ip = haversine_km(r["internal_point_latitude"], r["internal_point_longitude"],
                            st["latitude"].values, st["longitude"].values)
        s = st.assign(dist_pw=d_pw, dist_ip=d_ip)

        def pick(mask, by):
            cand = s[mask].sort_values(by)
            return cand.iloc[0] if len(cand) else None

        w1 = pick(np.ones(len(s), bool), "dist_ip")                       # nearest any station to internal point
        w2 = pick(s["core_complete"].values, "dist_pw")                    # nearest qualifying to PW centroid
        w3 = pick((s["core_complete"] & s["first_order"]).values, "dist_pw")  # nearest qualifying first-order
        ring = s[s["core_complete"] & (s["dist_pw"] <= radius_km)]
        snow_src = pick(s["snow_complete"].values, "dist_pw")             # nearest station with snow normals
        rec = {"market_id": m, "cbsa_name": r["cbsa_name"]}
        for tag, w in (("W1", w1), ("W2", w2), ("W3", w3)):
            rec[f"{tag}_station"] = w.name if w is not None else None
            rec[f"{tag}_distance_km"] = round(float(w["dist_pw" if tag != "W1" else "dist_ip"]), 1) if w is not None else None
            rec[f"{tag}_core_complete"] = bool(w["core_complete"]) if w is not None else False
            rec[f"{tag}_snow_published"] = bool(w["annual_snowfall_in_is_published"]) if w is not None else False
        rec["W3_has_hourly_wind"] = bool(w3["has_hourly_wind_normals"]) if w3 is not None else False
        rec["W4_stations_within_radius"] = int(len(ring))
        for e in CORE_ELEMENTS:
            rec[f"W3_{e}"] = w3[e] if w3 is not None else np.nan
            rec[f"W4_{e}"] = ring[e].mean() if len(ring) else np.nan
            rec[f"W2_{e}"] = w2[e] if w2 is not None else np.nan
        rec["W3_annual_snowfall_in"] = w3["annual_snowfall_in"] if w3 is not None else np.nan
        # W5 (candidate recommendation): element-specific hybrid rule.
        #   core temp/precip: nearest qualifying FIRST-ORDER station within FIRST_ORDER_MAX_KM of the
        #                     PW centroid, else nearest qualifying station of any network;
        #   snow:             the W5 station if it publishes qualifying snow, else the nearest
        #                     qualifying snow station within SNOW_FALLBACK_MAX_KM, else UNPUBLISHED;
        #   wind:             nearest station with hourly wind normals (a different product/network).
        fo = s[(s["core_complete"] & s["first_order"]).values & (s["dist_pw"] <= FIRST_ORDER_MAX_KM).values]
        w5 = fo.sort_values("dist_pw").iloc[0] if len(fo) else w2
        rec["W5_station"] = w5.name if w5 is not None else None
        rec["W5_rule"] = "first-order <= %d km" % FIRST_ORDER_MAX_KM if len(fo) else "nearest qualifying (any network)"
        rec["W5_distance_km"] = round(float(w5["dist_pw"]), 1) if w5 is not None else None
        for e in CORE_ELEMENTS:
            rec[f"W5_{e}"] = w5[e] if w5 is not None else np.nan
        snow_near = s[s["snow_complete"].values & (s["dist_pw"] <= SNOW_FALLBACK_MAX_KM).values].sort_values("dist_pw")
        if w5 is not None and bool(w5["snow_complete"]):
            rec["W5_snow_station"], rec["W5_snow_rule"] = w5.name, "same station"
            rec["W5_annual_snowfall_in"], rec["W5_snow_distance_km"] = w5["annual_snowfall_in"], rec["W5_distance_km"]
        elif len(snow_near):
            sn = snow_near.iloc[0]
            rec["W5_snow_station"], rec["W5_snow_rule"] = sn.name, f"fallback <= {SNOW_FALLBACK_MAX_KM} km"
            rec["W5_annual_snowfall_in"], rec["W5_snow_distance_km"] = sn["annual_snowfall_in"], round(float(sn["dist_pw"]), 1)
        else:
            rec["W5_snow_station"], rec["W5_snow_rule"] = None, "UNPUBLISHED within %d km" % SNOW_FALLBACK_MAX_KM
            rec["W5_annual_snowfall_in"], rec["W5_snow_distance_km"] = np.nan, None
        wind_st = pick(s["has_hourly_wind_normals"].values, "dist_pw")
        rec["W5_wind_station"] = wind_st.name if wind_st is not None else None
        rec["W5_wind_distance_km"] = round(float(wind_st["dist_pw"]), 1) if wind_st is not None else None
        rec["snow_fallback_station"] = snow_src.name if snow_src is not None else None
        rec["snow_fallback_distance_km"] = round(float(snow_src["dist_pw"]), 1) if snow_src is not None else None
        rec["snow_fallback_annual_snowfall_in"] = snow_src["annual_snowfall_in"] if snow_src is not None else np.nan
        rec["snow_fallback_days_snowfall_ge_1_in"] = snow_src["days_snowfall_ge_1_in"] if snow_src is not None else np.nan
        rows.append(rec)
        detail.append(ring.assign(market_id=m)[["market_id", "dist_pw", "first_order"] + CORE_ELEMENTS])
    return pd.DataFrame(rows).set_index("market_id"), pd.concat(detail)


def hourly_wind_summary(wh, station_ids: list[str]) -> pd.DataFrame:
    ids = ",".join(f"'{s}'" for s in station_ids if s)
    if not ids:
        return pd.DataFrame()
    return wh.query(f"""
        select station_id,
               avg(wind_avg_speed)                         as annual_mean_wind_mph,
               approx_percentile(wind_avg_speed, 0.9)      as p90_hourly_mean_wind_mph,
               avg(wind_pct_calm)                          as mean_pct_calm,
               count_if(wind_avg_speed_is_missing)         as missing_hours
        from AUTONOMOUS_MOBILITY.CORE.FCT_STATION_HOURLY_WIND_NORMALS
        where station_id in ({ids})
        group by station_id""").set_index("station_id")


# ---------------------------------------------------------------------------
# A-009 airports
# ---------------------------------------------------------------------------
_COUNTY_SUFFIX = re.compile(r"\b(COUNTY|PARISH|BOROUGH|CENSUS AREA|CITY AND BOROUGH|MUNICIPALITY)\b")
_ALIASES = {("FL", "DADE"): "MIAMI-DADE"}   # NASR uses the pre-1997 name for Miami-Dade County


def _norm_county(name: str) -> str:
    s = (name or "").upper().replace(".", "").replace("'", "").replace("SAINT ", "ST ").strip()
    s = re.sub(r"\bMC\s+", "MC", s)            # NASR 'MC LEAN' vs Gazetteer 'McLean'
    s = _COUNTY_SUFFIX.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def airport_county_match(wh) -> pd.DataFrame:
    """Match commercial-service airports to a county FIPS by published county name + state.

    Name matching is used only because NASR publishes names, not FIPS codes. Every
    unmatched or ambiguous airport is reported, not hidden.
    """
    ap = wh.query("""
        select e.airport_code, e.enplanements_cy2025, e.hub_type_code, e.service_level_code,
               a.facility_name, a.state_usps, a.county_name_published, a.county_state_usps,
               a.latitude, a.longitude
        from AUTONOMOUS_MOBILITY.CORE.FCT_AIRPORT_ENPLANEMENTS e
        join AUTONOMOUS_MOBILITY.CORE.DIM_AIRPORT a using (airport_code)""")
    cty = wh.query("""select county_fips, state_usps, county_name from AUTONOMOUS_MOBILITY.STAGING.stg_census__gazetteer_2024_counties""")
    cty["key"] = cty["county_name"].map(_norm_county)
    # independent cities are published as e.g. 'Baltimore city'; keep a 'CITY' variant key
    cty["is_city"] = cty["county_name"].str.upper().str.endswith(" CITY")
    lookup = {}
    for _, r in cty.iterrows():
        lookup.setdefault((r["state_usps"], r["key"]), []).append(r["county_fips"])
    out = []
    for _, a in ap.iterrows():
        st = a["county_state_usps"] or a["state_usps"]
        key = _norm_county(a["county_name_published"])
        key = _ALIASES.get((st, key), key)
        hits = lookup.get((st, key), []) or lookup.get((st, key + " CITY"), [])   # VA independent cities
        if len(hits) > 1:   # county and independent city share a name (e.g. St. Louis, Baltimore)
            non_city = [h for h in hits if not cty.set_index("county_fips").loc[h, "is_city"]]
            hits = non_city if len(non_city) == 1 else hits
        out.append({**a.to_dict(), "county_fips": hits[0] if len(hits) == 1 else None,
                    "match_status": "MATCHED" if len(hits) == 1 else ("AMBIGUOUS" if hits else "UNMATCHED")})
    return pd.DataFrame(out)


def airport_methods(wh, dim: pd.DataFrame, cent: pd.DataFrame, ap: pd.DataFrame, radius_km: float = 80.0
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    cty = wh.table("CORE", "BRG_MARKET_COUNTY")[["market_id", "county_fips"]]
    ap = ap.merge(cty, on="county_fips", how="left").rename(columns={"market_id": "inside_market_id"})
    rows, assign = [], []
    # Nearest-centroid assignment (service-area logic, no double counting), within the radius
    dist = pd.DataFrame({m: haversine_km(cent.loc[m, "pw_lat"], cent.loc[m, "pw_lon"],
                                         ap["latitude"].values, ap["longitude"].values) for m in dim.index},
                        index=ap["airport_code"])
    nearest_m = dist.idxmin(axis=1)
    nearest_d = dist.min(axis=1)
    for m, r in dim.iterrows():
        inside = ap[ap["inside_market_id"] == m]
        within = ap[dist[m].values <= radius_km]
        primary_lm = inside[inside["hub_type_code"].isin(["L", "M"])]
        served = ap[(nearest_m.values == m) & (nearest_d.values <= radius_km)]
        rows.append({
            "market_id": m, "cbsa_name": r["cbsa_name"], "population_2025": r["population_2025"],
            "A1_inside_cbsa_enplanements": inside["enplanements_cy2025"].sum(),
            "A1_airports": ";".join(sorted(inside["airport_code"])),
            "A2_within_80km_enplanements": within["enplanements_cy2025"].sum(),
            "A2_airports": ";".join(sorted(within["airport_code"])),
            "A3_large_medium_hub_inside_enplanements": primary_lm["enplanements_cy2025"].sum(),
            "A4_nearest_market_80km_enplanements": served["enplanements_cy2025"].sum(),
            "A4_airports": ";".join(sorted(served["airport_code"])),
        })
    for code in ap["airport_code"]:
        markets_within = [m for m in dim.index if dist.loc[code, m] <= radius_km]
        assign.append({"airport_code": code, "markets_within_80km": ";".join(markets_within),
                       "n_markets_within_80km": len(markets_within)})
    res = pd.DataFrame(rows).set_index("market_id")
    for c in ("A1_inside_cbsa_enplanements", "A2_within_80km_enplanements", "A4_nearest_market_80km_enplanements"):
        res[c.replace("_enplanements", "_per_capita")] = res[c] / res["population_2025"]
    return res, ap.merge(pd.DataFrame(assign), on="airport_code")


# ---------------------------------------------------------------------------
# Built environment / walkability aggregation
# ---------------------------------------------------------------------------
def _wq(values, weights, q=0.5):
    o = np.argsort(values)
    v, w = np.asarray(values)[o], np.asarray(weights)[o]
    cw = np.cumsum(w) / w.sum()
    return float(v[np.searchsorted(cw, q)])


def walkability_methods(wh) -> pd.DataFrame:
    bg = wh.table("CORE", "FCT_BLOCK_GROUP_BUILT_ENVIRONMENT")
    cty = wh.table("CORE", "BRG_MARKET_COUNTY")[["market_id", "county_fips", "central_outlying"]]
    bg = bg.merge(cty, on=["market_id", "county_fips"], how="left")
    b = bg[bg["national_walkability_index"].notna()]
    bp = b[b["total_population_sld"] > 0]
    g, gp = b.groupby("market_id"), bp.groupby("market_id")
    out = pd.DataFrame({
        "NW1_pop_weighted_mean": gp.apply(lambda d: np.average(d["national_walkability_index"], weights=d["total_population_sld"])),
        "NW2_simple_mean": g["national_walkability_index"].mean(),
        "NW3_median": g["national_walkability_index"].median(),
        "NW4_pop_weighted_median": gp.apply(lambda d: _wq(d["national_walkability_index"], d["total_population_sld"])),
        "NW5_share_pop_most_walkable_ge_15_26": gp.apply(
            lambda d: d.loc[d["national_walkability_index"] >= 15.26, "total_population_sld"].sum() / d["total_population_sld"].sum()),
        "NW6_share_pop_above_avg_ge_10_51": gp.apply(
            lambda d: d.loc[d["national_walkability_index"] >= 10.51, "total_population_sld"].sum() / d["total_population_sld"].sum()),
        "NW7_central_counties_pop_weighted_mean": bp[bp["central_outlying"] == "Central"].groupby("market_id").apply(
            lambda d: np.average(d["national_walkability_index"], weights=d["total_population_sld"])),
        "D3B_pop_weighted_intersection_density": gp.apply(
            lambda d: np.average(d["d3b_street_intersection_density"].fillna(0), weights=d["total_population_sld"])),
        "D4A_share_pop_no_transit_data": gp.apply(
            lambda d: d.loc[d["d4a_no_transit_data"], "total_population_sld"].sum() / d["total_population_sld"].sum()),
        "block_groups": g.size(),
        "block_groups_zero_pop": b[b["total_population_sld"] <= 0].groupby("market_id").size(),
        "block_groups_sld_cbsa_differs": bg[bg["cbsa_code_differs_from_sld"]].groupby("market_id").size(),
    })
    out["block_groups_zero_pop"] = out["block_groups_zero_pop"].fillna(0)
    out["block_groups_sld_cbsa_differs"] = out["block_groups_sld_cbsa_differs"].fillna(0)
    out["mean_minus_pw_mean"] = out["NW2_simple_mean"] - out["NW1_pop_weighted_mean"]
    return out
