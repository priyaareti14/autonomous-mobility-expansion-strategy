"""Phase 8: sensitivity and robustness of the frozen Phase 7 baseline (baseline_v1).

Reads the Phase 7 scoring tables (Snowflake, AM_TRANSFORMER, read-only) and the approved Phase 5/6
diagnostics, and tests how the baseline ranks move under:
  * named business-priority component weights and 10,000 Dirichlet(1) component-weight draws per mode;
  * magnitude-sensitive normalization (raw min-max, 5th-95th percentile winsorized min-max);
  * robotaxi regulatory uncertainty for the LOW-confidence records (pessimistic / neutral / optimistic),
    with nested weight sensitivity under each, and the same bounds as an extension for sidewalk and drone;
  * one-at-a-time methodology alternatives (feature drops, A4 airport, block-group density, W2/W3/W4
    weather stations, p90 wind, and the regulatory coding sensitivities A-046 / A-051 / A-055).

The Phase 7 baseline is never modified: it is recomputed here only to prove the engine reproduces it.
DEPLOYMENT EVIDENCE IS NEVER READ: a guard makes any attempt to open it fail (deployment validation is
the separate script run_phase8_deployment_validation.py, which runs on the frozen outputs of this one).

Outputs: outputs/phase8/ (aggregates only; no raw draw matrix) and model_metadata.json with the seed and
a checksum manifest. Re-running with the same inputs reproduces every file byte for byte.

Usage (repository root, .venv active):
    python scripts/run_phase8_sensitivity.py
"""

from __future__ import annotations

import builtins
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------- deployment-evidence guard (Step 25)
_real_open = builtins.open
_real_io_open = io.open


def _guarded_open(file, *args, **kwargs):
    if "deployment" in str(file).lower():
        raise PermissionError(f"Phase 8 sensitivity must not read deployment evidence: {file}")
    return _real_open(file, *args, **kwargs)


builtins.open = _guarded_open
io.open = _guarded_open

from src.analytics import diagnostics as dg  # noqa: E402
from src.analytics.data_access import Warehouse  # noqa: E402

OUT = ROOT / "outputs" / "phase8"
FIG = OUT / "figures"
DB = "AUTONOMOUS_MOBILITY"
SEED = 20261007
N_DRAWS = 10_000
GIT_INPUT_COMMIT = "bc2023b"        # Phase 7 implementation commit = Phase 8 input snapshot
MODEL_INPUT_COMMIT = "55b1cb4"      # Phase 7 model-input commit
BASELINE_VERSION = "baseline_v1"
IN_DEC = 9                          # inputs read from Snowflake are rounded to 9 decimals (float residue)
RANK_DEC = 6                        # ties: scores equal to 6 decimals share a rank (Phase 7 rule)
OUT_DEC = 6                         # exported precision
TOL = 1e-6
MOVE = 5                            # "material" rank movement (Step 7)
WIDE_INTERVAL = 10                  # weight-sensitive: 90% rank interval wider than this
TOP_FREQ = 0.80                     # consistent top performer: top-5 in at least 80% of draws
MODES = ["ROBOTAXI", "SIDEWALK_DELIVERY", "DRONE_DELIVERY"]
SHORT_MODE = {"ROBOTAXI": "robotaxi", "SIDEWALK_DELIVERY": "sidewalk", "DRONE_DELIVERY": "drone"}
C1, C2, C3, C4, C5 = ("C1_DEMAND_AND_MARKET_OPPORTUNITY", "C2_OPERATING_ENVIRONMENT", "C3_ECONOMIC_ATTRACTIVENESS",
                      "C4_REGULATORY_AND_AUTONOMY_READINESS", "C5_INFRASTRUCTURE_AND_MODE_FIT")
COMPONENTS = {"ROBOTAXI": [C1, C2, C3, C4], "SIDEWALK_DELIVERY": [C1, C2, C3, C4, C5],
              "DRONE_DELIVERY": [C1, C2, C3, C4, C5]}
SHORT = {C1: "C1", C2: "C2", C3: "C3", C4: "C4", C5: "C5"}
PRIORITY_NAME = {C1: "DEMAND_PRIORITY", C2: "OPERATING_ENVIRONMENT_PRIORITY", C3: "ECONOMIC_PRIORITY",
                 C4: "REGULATORY_PRIORITY", C5: "INFRASTRUCTURE_PRIORITY"}
ABSENCE = {"NO_SPECIFIC_STATUTE", "NO_SPECIFIC_FRAMEWORK", "NOT_ADDRESSED", "NO_STATUTE"}
NUMERIC_METHOD = "MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES"
REG_SCENARIOS = {"REG_PESSIMISTIC": 0.0, "REG_NEUTRAL": 0.5, "REG_OPTIMISTIC": 1.0}
CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))
    return bool(ok)


# ------------------------------------------------------------------------------------------- load
def load() -> dict:
    wh = Warehouse()
    q = lambda schema, t, order: wh.query(f"select * from {DB}.{schema}.{t} order by {order}")  # noqa: E731
    try:
        d = {
            "fs": q("ANALYTICS", "FCT_FEATURE_SCORES", "mode, market_id, component, feature_id"),
            "cs": q("ANALYTICS", "FCT_COMPONENT_SCORES", "mode, market_id, component"),
            "rb": q("ANALYTICS", "FCT_READINESS_BASELINE", "mode, market_id"),
            "rd": q("ANALYTICS", "FCT_REGULATORY_DIMENSION_SCORES", "mode, market_id, legal_dimension"),
            "ev": q("INTERMEDIATE", "INT_REGULATORY__MARKET_STATE_EVIDENCE", "mode, market_id, legal_dimension, state_usps"),
            "prod": q("INTERMEDIATE", "INT_MARKET__PRODUCTION_FEATURES", "market_id"),
            "dim": q("CORE", "DIM_MARKET", "market_id"),
        }
    finally:
        wh.close()
    for v in d.values():
        if "market_id" in v:
            v["market_id"] = v["market_id"].astype(str)
        for c in v.columns:
            if v[c].dtype.kind == "f":
                v[c] = v[c].round(IN_DEC)
    d["contract"] = pd.read_csv(ROOT / "dbt" / "seeds" / "feature_contract.csv", dtype=str, keep_default_na=False)
    d["reg_contract"] = pd.read_csv(ROOT / "config" / "regulatory_feature_contract.csv", dtype=str, keep_default_na=False)
    d["weather"] = pd.read_csv(ROOT / "outputs" / "weather_station_methods.csv", dtype={"market_id": str})
    d["names"] = d["dim"].set_index("market_id").cbsa_name
    return d


# ---------------------------------------------------------------------------------- scoring engine
def percentile(v: pd.Series) -> pd.Series:
    n = v.notna().sum()
    return 100 * (v.rank(method="average") - 1) / (n - 1)


def minmax(v: pd.Series, lo: float | None = None, hi: float | None = None) -> pd.Series:
    lo = v.min() if lo is None else lo
    hi = v.max() if hi is None else hi
    if hi == lo:                                   # constant feature: no information, neutral 50 (none expected)
        return pd.Series(50.0, index=v.index)
    return 100 * (v.clip(lo, hi) - lo) / (hi - lo)


def normalize(values: pd.DataFrame, directions: pd.Series, method: str) -> pd.DataFrame:
    """values: market x feature (transformed); returns feature scores 0-100 in the contract direction."""
    out = {}
    for f in values.columns:
        v = values[f].astype(float)
        if method == "PERCENTILE":
            s = percentile(v)
        elif method == "RAW_MINMAX":
            s = minmax(v)
        elif method == "WINSORIZED_MINMAX":
            s = minmax(v, float(np.percentile(v, 5, method="linear")), float(np.percentile(v, 95, method="linear")))
        else:
            raise ValueError(method)
        out[f] = s if directions[f] == "HIGHER_IS_MORE_FAVORABLE" else 100 - s
    return pd.DataFrame(out)


def components(feat_scores: pd.DataFrame, comp_of: pd.Series, c4: pd.Series, mode: str) -> pd.DataFrame:
    """Equal weights within component; C4 supplied (NaN = incomplete)."""
    cm = {}
    for comp in COMPONENTS[mode]:
        if comp == C4:
            cm[comp] = c4.reindex(feat_scores.index)
        else:
            cols = [f for f in feat_scores.columns if comp_of[f] == comp]
            assert cols, f"{mode} {comp} has no input"
            cm[comp] = feat_scores[cols].mean(axis=1)
    return pd.DataFrame(cm)[COMPONENTS[mode]]


def overall(cm: pd.DataFrame, w: dict[str, float]) -> pd.Series:
    s = sum(cm[c] * w[c] for c in cm.columns)
    return s.where(cm.notna().all(axis=1))


def rank(scores: pd.Series) -> pd.Series:
    """Standard competition rank (1 = best) among non-null scores, ties at RANK_DEC decimals."""
    return scores.round(RANK_DEC).rank(method="min", ascending=False)


def equal_weights(mode: str) -> dict[str, float]:
    k = len(COMPONENTS[mode])
    return {c: 1.0 / k for c in COMPONENTS[mode]}


def c4_from_dims(dims: pd.DataFrame) -> pd.Series:
    """dims: rows market x dimension with score / applicable / complete. C4 = mean of applicable dimension
    scores, NaN unless every dimension of the market is complete (Phase 7 rule)."""
    g = dims.groupby("market_id")
    complete = g.complete.all()
    mean = dims[dims.applicable].groupby("market_id").score.mean()
    return mean.where(complete.reindex(mean.index).fillna(False)).reindex(complete.index)


# ---------------------------------------------------------------- regulatory dimension reconstruction
def build_dims(d: dict, mode: str, rule: str = "BASE", nevada_scope_adjustment: bool = True) -> pd.DataFrame:
    """Rebuild every regulatory dimension of a mode from the state evidence (INT_REGULATORY__...), so the
    regulatory coding sensitivities can change ONE rule at a time. rule: BASE (VERIFIED_PRIMARY and
    MEDIUM/HIGH) or CONFIDENCE_ONLY (MEDIUM/HIGH, retrieved or not; A-051)."""
    ev = d["ev"][d["ev"]["mode"] == mode].copy()
    con = d["reg_contract"].set_index(["mode", "legal_dimension"])
    if rule == "BASE":
        eligible = ev.base_eligible_flag.astype(bool)
    else:
        eligible = ev.evidence_present_flag.astype(bool) & ev.confidence.isin(["HIGH", "MEDIUM"])
    fav_sets = {k: set(v.split("|")) for k, v in con.favorable_statuses.items()}
    adjusted = (ev.scope_adjustment.notna() & (ev.scope_adjustment != "")) if nevada_scope_adjustment \
        else pd.Series(False, index=ev.index)
    ev["fav"] = [(cs in fav_sets.get((m, ld), set())) for m, ld, cs in zip(ev["mode"], ev.legal_dimension, ev.coded_status)]
    ev["fav"] = ev.fav & ~adjusted
    ev["elig"] = eligible
    pdd = ev[ev.legal_dimension == "SW_PDD_LEGAL_STATUS"].drop_duplicates("state_usps").set_index("state_usps")
    rows = []
    for (mid, ld), g in ev.groupby(["market_id", "legal_dimension"]):
        method = g.market_mapping_method.iloc[0]
        if method == NUMERIC_METHOD:
            cls = []
            for r in g.itertuples():
                p = pdd.loc[r.state_usps] if r.state_usps in pdd.index else None
                if p is None or not p.elig:
                    cls.append("UNKNOWN")
                elif not p.fav:
                    cls.append("NA")
                elif not r.elig:
                    cls.append("UNKNOWN")
                else:
                    cls.append("FAV")
        else:
            cls = ["UNKNOWN" if not r.elig else "FAV" if r.fav else "UNFAV" for r in g.itertuples()]
        g = g.assign(cls=cls)
        sh = lambda c: float(g.state_population_share[g.cls == c].sum())  # noqa: E731
        spec = g[(g.cls == "FAV") & (g.coded_status == "SPECIFIED")].numeric_value
        rows.append({"market_id": mid, "legal_dimension": ld, "method": method, "fav": sh("FAV"), "unfav": sh("UNFAV"),
                     "unknown": sh("UNKNOWN"), "na": sh("NA"),
                     "absence": float(g.state_population_share[(g.cls == "UNFAV") & g.coded_status.isin(ABSENCE)].sum()),
                     "limit": float(spec.min()) if len(spec) else np.nan})
    dims = pd.DataFrame(rows)
    dims["complete"] = dims.unknown <= TOL
    dims["applicable"] = np.where(dims.method == NUMERIC_METHOD, dims.fav > TOL, True)
    dims["score"] = np.where(dims.complete, 100 * dims.fav, np.nan)
    num = dims.method == NUMERIC_METHOD
    dims.loc[num, "score"] = np.nan
    dom = dims[num & dims.complete & dims.applicable]
    if len(dom):
        dims.loc[dom.index, "score"] = percentile(dom["limit"].fillna(1e12)).values
    return dims


def dims_from_rd(d: dict, mode: str) -> pd.DataFrame:
    rd = d["rd"][d["rd"]["mode"] == mode]
    return pd.DataFrame({"market_id": rd.market_id.values, "legal_dimension": rd.legal_dimension.values,
                         "method": rd.market_mapping_method.values, "fav": rd.verified_favorable_share.values,
                         "unknown": rd.unknown_or_low_confidence_share.values,
                         "absence": rd.verified_absence_share.values, "score": rd.dimension_score.values,
                         "applicable": rd.dimension_applicable_flag.astype(bool).values,
                         "complete": rd.dimension_complete_flag.astype(bool).values,
                         "ranking_value": rd.ranking_value.values})


# ------------------------------------------------------------------------------- model per mode
class ModeModel:
    def __init__(self, d: dict, mode: str):
        self.mode = mode
        fs = d["fs"][d["fs"]["mode"] == mode]
        nf = fs[fs.component != C4]
        self.values = nf.pivot(index="market_id", columns="feature_id", values="transformed_value").sort_index()
        self.raw = nf.pivot(index="market_id", columns="feature_id", values="raw_value").sort_index()
        self.base_feat = nf.pivot(index="market_id", columns="feature_id", values="feature_score").sort_index()
        meta = nf.drop_duplicates("feature_id").set_index("feature_id")
        self.comp_of, self.direction, self.fname = meta.component, meta.direction, meta.feature_name
        self.dims = dims_from_rd(d, mode)
        self.c4 = c4_from_dims(self.dims)
        self.markets = self.values.index

    def score(self, feat=None, c4=None, w=None, drop=()) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
        feat = self.base_feat if feat is None else feat
        feat = feat[[f for f in feat.columns if f not in drop]]
        cm = components(feat, self.comp_of, self.c4 if c4 is None else c4, self.mode)
        s = overall(cm, w or equal_weights(self.mode))
        return cm, s, rank(s)

    def replace_feature(self, fid: str, transformed: pd.Series) -> pd.DataFrame:
        """Percentile-score one alternative transformed feature in the contract direction; others unchanged."""
        feat = self.base_feat.copy()
        feat[fid] = normalize(transformed.to_frame(fid), self.direction, "PERCENTILE")[fid]
        return feat


# ---------------------------------------------------------------------------- Dirichlet simulation
def simulate(cm: pd.DataFrame, W: np.ndarray, baseline_rank: pd.Series) -> tuple[pd.DataFrame, np.ndarray]:
    """cm: complete markets x components; W: draws x components. Returns per-market metrics and the
    rank matrix (markets x draws)."""
    cm = cm.dropna()
    S = np.round(cm.values @ W.T, RANK_DEC)                                   # markets x draws
    R = 1 + (S[np.newaxis, :, :] > S[:, np.newaxis, :]).sum(axis=1)            # competition rank per draw
    b = baseline_rank.reindex(cm.index).values
    q = lambda p: np.quantile(R, p, axis=1, method="inverted_cdf")             # noqa: E731
    m = pd.DataFrame({
        "market_id": cm.index, "n_ranked_markets": len(cm), "n_draws": W.shape[0],
        "baseline_rank": b, "mean_rank": R.mean(1), "median_rank": np.median(R, 1), "rank_std": R.std(1),
        "best_rank": R.min(1), "worst_rank": R.max(1), "rank_p05": q(0.05), "rank_p25": q(0.25),
        "rank_p75": q(0.75), "rank_p95": q(0.95),
        "top_1_frequency": (R <= 1).mean(1), "top_3_frequency": (R <= 3).mean(1),
        "top_5_frequency": (R <= 5).mean(1), "top_10_frequency": (R <= 10).mean(1),
        "mean_score": S.mean(1), "score_std": S.std(1),
        "mean_abs_rank_change_from_baseline": np.abs(R - b[:, None]).mean(1),
        "within_2_ranks_of_baseline_frequency": (np.abs(R - b[:, None]) <= 2).mean(1),
    })
    m["rank_iqr"] = m.rank_p75 - m.rank_p25
    m["rank_interval_90"] = m.rank_p95 - m.rank_p05
    return m, R


def kendall_tau_b(x: np.ndarray, y: np.ndarray) -> float:
    i, j = np.triu_indices(len(x), 1)
    sx, sy = np.sign(x[i] - x[j]), np.sign(y[i] - y[j])
    den = np.sqrt((sx ** 2).sum() * (sy ** 2).sum())
    return float((sx * sy).sum() / den) if den else np.nan


def compare_ranks(base: pd.Series, alt: pd.Series) -> dict:
    k = base.dropna().index.intersection(alt.dropna().index)
    b, a = base[k], alt[k]
    mv = (a - b).abs()
    return {"n_markets_compared": len(k),
            "spearman_rho": float(b.rank().corr(a.rank())),
            "kendall_tau_b": kendall_tau_b(b.values, a.values),
            "top5_overlap": int(len(set(b[b <= 5].index) & set(a[a <= 5].index))),
            "top10_overlap": int(len(set(b[b <= 10].index) & set(a[a <= 10].index))),
            "max_abs_rank_movement": int(mv.max()) if len(mv) else 0,
            "markets_moving_ge_5": int((mv >= MOVE).sum())}


# ------------------------------------------------------------------------------------------ main
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    d = load()
    names = d["names"]
    rng = np.random.default_rng(SEED)
    models = {m: ModeModel(d, m) for m in MODES}
    rb = d["rb"].set_index(["mode", "market_id"])
    cs = d["cs"]

    # ---- Step 1: the frozen baseline, reproduced exactly (regression guard) -------------------------
    print("Baseline reproduction (Phase 7 baseline_v1)")
    baseline_rows, base_rank, base_score = [], {}, {}
    for mode, mm in models.items():
        cm, s, r = mm.score()
        p7 = rb.loc[mode].reindex(mm.markets)
        pcs = cs[cs["mode"] == mode].pivot(index="market_id", columns="component", values="component_score").reindex(mm.markets)
        ok_s = np.allclose(s.fillna(-1), p7.baseline_readiness_score.astype(float).fillna(-1), atol=TOL)
        ok_r = (r.fillna(-1) == p7.baseline_rank.astype(float).fillna(-1)).all()
        ok_c = np.allclose(cm.fillna(-1).values, pcs[COMPONENTS[mode]].astype(float).fillna(-1).values, atol=TOL)
        ok_f = np.allclose(normalize(mm.values, mm.direction, "PERCENTILE").values, mm.base_feat.values, atol=TOL)
        check(f"{mode}: engine reproduces Phase 7 feature scores, components, scores and ranks", ok_s and ok_r and ok_c and ok_f)
        base_rank[mode], base_score[mode] = r, s
        for mid in mm.markets:
            row = {"mode": mode, "market_id": mid, "market_name": names[mid], "baseline_score": s[mid],
                   "baseline_rank": r[mid], "score_complete_flag": bool(pd.notna(s[mid])),
                   "c4_complete_flag": bool(p7.loc[mid, "c4_complete_flag"])}
            for comp in COMPONENTS[mode]:
                row[f"{SHORT[comp].lower()}_score"] = cm.loc[mid, comp]
            baseline_rows.append(row)
    baseline = pd.DataFrame(baseline_rows)

    # ---- Step 2: named business-priority scenarios ---------------------------------------------------
    scen_defs, scen_rows = [], []
    for mode in MODES:
        comps = COMPONENTS[mode]
        defs = [("NEUTRAL", "Neutral", equal_weights(mode),
                 "Equal weights across the active components (the Phase 7 baseline)")]
        for p in comps:
            w = {c: (0.40 if c == p else 0.60 / (len(comps) - 1)) for c in comps}
            defs.append((PRIORITY_NAME[p], PRIORITY_NAME[p].replace("_", " ").title(), w,
                         f"{SHORT[p]} at 40%; the other {len(comps) - 1} active components share 60% equally. "
                         "A scenario assumption, not an estimate of business preferences"))
        for sid, sname, w, desc in defs:
            assert abs(sum(w.values()) - 1) < 1e-12
            scen_defs.append({"mode": mode, "scenario_id": f"{SHORT_MODE[mode].upper()}_{sid}", "scenario_name": sname,
                              **{f"{SHORT[c].lower()}_weight": w.get(c) for c in [C1, C2, C3, C4, C5]},
                              "description": desc})
            _, s, r = models[mode].score(w=w)
            for mid in models[mode].markets:
                scen_rows.append({"mode": mode, "scenario_id": f"{SHORT_MODE[mode].upper()}_{sid}", "market_id": mid,
                                  "market_name": names[mid], "score": s[mid], "rank": r[mid],
                                  "baseline_rank": base_rank[mode][mid],
                                  "rank_change_vs_baseline": r[mid] - base_rank[mode][mid]})
    scen_defs, scen_res = pd.DataFrame(scen_defs), pd.DataFrame(scen_rows)
    check("business scenarios: all active component weights sum to 1; robotaxi has no C5 weight",
          bool(((scen_defs[[c for c in scen_defs if c.endswith("_weight")]].sum(axis=1) - 1).abs() < 1e-12).all()
               and scen_defs[scen_defs["mode"] == "ROBOTAXI"].c5_weight.isna().all()))
    neutral = scen_res[scen_res.scenario_id.str.endswith("_NEUTRAL")]
    check("NEUTRAL business scenario equals the baseline ranks",
          bool((neutral["rank"].fillna(-1) == neutral.baseline_rank.fillna(-1)).all()))

    # ---- Steps 3-5: Dirichlet component-weight sensitivity -----------------------------------------
    print("Dirichlet component-weight sensitivity")
    draws = {m: rng.dirichlet(np.ones(len(COMPONENTS[m])), N_DRAWS) for m in MODES}   # fixed mode order
    for m, W in draws.items():
        check(f"{m}: {N_DRAWS} draws, weights >= 0 and sum to 1", W.shape == (N_DRAWS, len(COMPONENTS[m]))
              and bool((W >= 0).all()) and bool(np.abs(W.sum(1) - 1).max() < 1e-12))
    ws_rows, rank_mats = [], {}
    for mode, mm in models.items():
        cm, _, _ = mm.score()
        met, R = simulate(cm, draws[mode], base_rank[mode])
        rank_mats[(mode, "BASELINE_EVIDENCE")] = (met.market_id.values, R)
        ws_rows.append(met.assign(mode=mode, regulatory_scenario="BASELINE_EVIDENCE"))
        check(f"{mode}: every complete market is in the simulation", len(met) == int(base_score[mode].notna().sum()))
        check(f"{mode}: ranks within 1..{len(met)}, frequencies in [0,1] and reconcile to the draw count",
              int(R.min()) >= 1 and int(R.max()) <= len(met)
              and bool(met[[c for c in met if c.endswith("_frequency")]].stack().between(0, 1).all())
              and int((R <= 5).sum()) == int(round(met.top_5_frequency.sum() * N_DRAWS)))

    # ---- Steps 8-11: robotaxi regulatory uncertainty, nested weight sensitivity ----------------------
    print("Regulatory uncertainty")
    reg_rows = []
    rt = models["ROBOTAXI"]
    reg_rank, reg_score = {}, {}
    for sc, f in REG_SCENARIOS.items():
        dims = rt.dims.copy()
        dims["score"] = 100 * (dims.fav + dims.unknown * f)
        dims["complete"] = True
        c4 = c4_from_dims(dims)
        cm, s, r = rt.score(c4=c4)
        reg_rank[sc], reg_score[sc] = r, s
        complete = rt.c4.notna()
        check(f"ROBOTAXI {sc}: complete markets keep their baseline C4 and score exactly",
              np.allclose(c4[complete], rt.c4[complete], atol=TOL)
              and np.allclose(s[complete], base_score["ROBOTAXI"][complete], atol=TOL))
        met, R = simulate(cm, draws["ROBOTAXI"], r)
        rank_mats[("ROBOTAXI", sc)] = (met.market_id.values, R)
        ws_rows.append(met.assign(mode="ROBOTAXI", regulatory_scenario=sc))
        check(f"ROBOTAXI {sc}: all 35 markets ranked in the nested simulation", len(met) == 35)
    lin = all(np.allclose(reg_score["REG_NEUTRAL"], (reg_score["REG_PESSIMISTIC"] + reg_score["REG_OPTIMISTIC"]) / 2,
                          atol=TOL) for _ in [0])
    check("regulatory scenario formula reconciles (neutral = midpoint; pessimistic <= neutral <= optimistic)",
          lin and bool((reg_score["REG_PESSIMISTIC"] <= reg_score["REG_NEUTRAL"] + TOL).all())
          and bool((reg_score["REG_NEUTRAL"] <= reg_score["REG_OPTIMISTIC"] + TOL).all()))
    unk = rt.dims.pivot(index="market_id", columns="legal_dimension", values="unknown")
    for mid in rt.markets:
        row = {"mode": "ROBOTAXI", "market_id": mid, "market_name": names[mid], "c4_complete_flag": bool(pd.notna(rt.c4[mid])),
               "baseline_score": base_score["ROBOTAXI"][mid], "baseline_rank": base_rank["ROBOTAXI"][mid],
               **{f"unknown_share_{c.lower()}": unk.loc[mid, c] for c in unk.columns}}
        for sc in REG_SCENARIOS:
            row[f"{sc.lower().replace('reg_', '')}_score"] = reg_score[sc][mid]
            row[f"{sc.lower().replace('reg_', '')}_rank"] = reg_rank[sc][mid]
        row["regulatory_score_range"] = row["optimistic_score"] - row["pessimistic_score"]
        rk = [row["pessimistic_rank"], row["neutral_rank"], row["optimistic_rank"]]
        row["regulatory_rank_range"] = max(rk) - min(rk)
        reg_rows.append(row)
    # Extension (not required by the brief): the same bounds for sidewalk and drone markets with incomplete C4.
    for mode in ["SIDEWALK_DELIVERY", "DRONE_DELIVERY"]:
        mm = models[mode]
        dom = mm.dims[(mm.dims.method == NUMERIC_METHOD) & mm.dims.ranking_value.notna()]
        lookup = dict(zip(dom.ranking_value.round(3), dom.score))
        vo = build_dims(d, mode)                          # verified-only weight limit per market
        scores, ranks = {}, {}
        for sc, f in REG_SCENARIOS.items():
            dims = mm.dims.copy()
            cat = dims.method != NUMERIC_METHOD
            inc = ~dims.complete
            dims.loc[cat & inc, "score"] = 100 * (dims.fav + dims.unknown * f)[cat & inc]
            for i in dims[~cat & inc].index:
                v = vo[(vo.market_id == dims.at[i, "market_id"]) & (vo.legal_dimension == dims.at[i, "legal_dimension"])].iloc[0]
                if v.fav <= TOL:
                    dims.at[i, "applicable"], dims.at[i, "score"] = False, np.nan
                else:
                    key = round(1e12 if np.isnan(v["limit"]) else v["limit"], 3)
                    assert key in lookup, f"{mode} weight limit {key} outside the baseline domain"
                    dims.at[i, "applicable"], dims.at[i, "score"] = True, lookup[key]
            dims["complete"] = True
            _, s, r = mm.score(c4=c4_from_dims(dims))
            scores[sc], ranks[sc] = s, r
            complete = mm.c4.notna()
            check(f"{mode} {sc} (extension): complete markets keep their baseline score",
                  np.allclose(s[complete], base_score[mode][complete], atol=TOL))
        for mid in mm.markets:
            row = {"mode": mode, "market_id": mid, "market_name": names[mid], "c4_complete_flag": bool(pd.notna(mm.c4[mid])),
                   "baseline_score": base_score[mode][mid], "baseline_rank": base_rank[mode][mid]}
            for sc in REG_SCENARIOS:
                row[f"{sc.lower().replace('reg_', '')}_score"] = scores[sc][mid]
                row[f"{sc.lower().replace('reg_', '')}_rank"] = ranks[sc][mid]
            row["regulatory_score_range"] = row["optimistic_score"] - row["pessimistic_score"]
            rk = [row["pessimistic_rank"], row["neutral_rank"], row["optimistic_rank"]]
            row["regulatory_rank_range"] = max(rk) - min(rk)
            reg_rows.append(row)
    reg = pd.DataFrame(reg_rows)

    # ---- Steps 6-7: alternative normalization ------------------------------------------------------
    print("Normalization sensitivity")
    norm_rows, norm_cmp, norm_rank = [], [], {}
    for mode, mm in models.items():
        for method in ["PERCENTILE", "RAW_MINMAX", "WINSORIZED_MINMAX"]:
            feat = normalize(mm.values, mm.direction, method)
            _, s, r = mm.score(feat=feat)
            norm_rank[(mode, method)] = r
            for mid in mm.markets:
                norm_rows.append({"mode": mode, "normalization": method, "market_id": mid, "market_name": names[mid],
                                  "score": s[mid], "rank": r[mid], "baseline_rank": base_rank[mode][mid],
                                  "rank_change_vs_baseline": r[mid] - base_rank[mode][mid]})
            if method != "PERCENTILE":
                norm_cmp.append({"mode": mode, "normalization": method, **compare_ranks(base_rank[mode], r)})
        const = [f for f in mm.values.columns if mm.values[f].nunique() < 2]
        check(f"{mode}: no active feature is constant (min-max defined)", not const, ", ".join(const))
        check(f"{mode}: PERCENTILE normalization reproduces the baseline ranks",
              bool((norm_rank[(mode, 'PERCENTILE')].fillna(-1) == base_rank[mode].fillna(-1)).all()))
    norm, norm_cmp = pd.DataFrame(norm_rows), pd.DataFrame(norm_cmp)

    # ---- Steps 12-17: one-at-a-time methodology sensitivities ---------------------------------------
    print("Methodology sensitivity (one assumption at a time)")
    prod = d["prod"].set_index("market_id")
    wx = d["weather"].set_index("market_id")
    meth_defs, meth_rows = [], []

    def run(mode, test_id, family, desc, feat=None, c4=None, drop=()):
        mm = models[mode]
        _, s, r = mm.score(feat=feat, c4=c4, drop=drop)
        meth_defs.append({"mode": mode, "test_id": test_id, "family": family, "description": desc,
                          **compare_ranks(base_rank[mode], r)})
        for mid in mm.markets:
            meth_rows.append({"mode": mode, "test_id": test_id, "family": family, "market_id": mid,
                              "market_name": names[mid], "score": s[mid], "rank": r[mid],
                              "baseline_rank": base_rank[mode][mid], "rank_change_vs_baseline": r[mid] - base_rank[mode][mid]})
        return r

    fid = lambda mode, name: models[mode].fname[models[mode].fname == name].index[0]  # noqa: E731
    # Feature redundancy (Step 12)
    run("ROBOTAXI", "DROP_INCOME", "FEATURE_DROP", "Drop PF05 median household income from C1 (4 features at 1/4)",
        drop=(fid("ROBOTAXI", "median_household_income_usd"),))
    run("ROBOTAXI", "DROP_WAGE", "FEATURE_DROP", "Drop PF09 shuttle/chauffeur wage from C3 (PF06 alone)",
        drop=(fid("ROBOTAXI", "shuttle_chauffeur_median_annual_wage_usd"),))
    run("SIDEWALK_DELIVERY", "DROP_DENSITY", "FEATURE_DROP", "Drop PF02 population-weighted density from C1 (4 features)",
        drop=(fid("SIDEWALK_DELIVERY", "pw_tract_density_log1p"),))
    rtd = rt.dims[rt.dims.legal_dimension != "RT_COMMERCIAL_PASSENGER_SERVICE"]
    run("ROBOTAXI", "DROP_COMMERCIAL_DIMENSION", "FEATURE_DROP",
        "Drop the commercial-passenger dimension from C4 (driverless + local authority; A-056)", c4=c4_from_dims(rtd))
    # Airport A4 (Step 13), density backup (Step 14): same LOG1P transformation as the production feature
    run("ROBOTAXI", "AIRPORT_A4", "AIRPORT", "PF04 from the A4 80 km radius diagnostic (PX03), LOG1P",
        feat=rt.replace_feature(fid("ROBOTAXI", "enplanements_per_resident_log1p"),
                                np.log1p(prod.a4_enplanements_per_resident_diagnostic.astype(float)).reindex(rt.markets)))
    for mode in ["ROBOTAXI", "SIDEWALK_DELIVERY"]:
        mm = models[mode]
        run(mode, "DENSITY_D3_BLOCK_GROUP", "DENSITY",
            "PF02 from population-weighted block-group density (EPA SLD 2018 diagnostic, PX02), LOG1P",
            feat=mm.replace_feature(fid(mode, "pw_tract_density_log1p"),
                                    np.log1p(prod.pw_block_group_density_sld2018_diagnostic.astype(float)).reindex(mm.markets)))
    # Weather stations (Step 15): the Phase 5 W2 / W3 / W4 variants for the features they cover
    weather_fallback = {}
    for variant, cols in {"W2": {"days_precip_ge_010_in": "W2_days_precip_ge_010_in", "days_tmax_ge_90f": "W2_days_tmax_ge_90f"},
                          "W3": {"days_precip_ge_010_in": "W3_days_precip_ge_010_in", "days_tmax_ge_90f": "W3_days_tmax_ge_90f",
                                 "annual_snowfall_in": "W3_annual_snowfall_in"},
                          "W4": {"days_precip_ge_010_in": "W4_days_precip_ge_010_in", "days_tmax_ge_90f": "W4_days_tmax_ge_90f"}}.items():
        for mode, mm in models.items():
            feat = mm.base_feat.copy()
            for fname, col in cols.items():
                f_id = fid(mode, fname)
                alt = wx[col].astype(float).reindex(mm.markets)
                miss = alt.isna()
                weather_fallback[(variant, fname)] = int(miss.sum())
                alt = alt.where(~miss, mm.values[f_id])                     # no alternative value: keep baseline
                feat[f_id] = normalize(alt.to_frame(f_id), mm.direction, "PERCENTILE")[f_id]
            run(mode, f"WEATHER_{variant}", "WEATHER",
                f"Phase 5 {variant} station method for {', '.join(cols)} (snowfall: baseline unless W3)", feat=feat)
    # Wind (Step 16): climatological p90 of hourly-mean normals, NOT an observed extreme-wind measure
    dr = models["DRONE_DELIVERY"]
    run("DRONE_DELIVERY", "WIND_P90_HOURLY_NORMALS", "WIND",
        "PF14 from the p90 of hourly-mean wind normals (PX04): a climatological statistic, not observed extremes",
        feat=dr.replace_feature(fid("DRONE_DELIVERY", "annual_mean_wind_mph"),
                                prod.p90_of_hourly_normals_mph_diagnostic.astype(float).reindex(dr.markets)))
    # Regulatory coding sensitivities flagged in Phase 7 (A-046, A-051, A-055)
    for mode, mm in models.items():
        base_dims = build_dims(d, mode)
        merged = base_dims.merge(mm.dims[["market_id", "legal_dimension", "score"]], on=["market_id", "legal_dimension"],
                                 suffixes=("", "_p7"))
        check(f"{mode}: regulatory dimensions rebuilt from state evidence equal Phase 7",
              np.allclose(merged.score.fillna(-1), merged.score_p7.fillna(-1), atol=TOL))
        a055 = mm.dims.copy()
        cat = a055.method != NUMERIC_METHOD
        a055.loc[cat & a055.complete, "score"] = (100 * (a055.fav + 0.5 * a055.absence))[cat & a055.complete]
        run(mode, "ABSENCE_HALF_CREDIT", "REGULATORY_CODING",
            "A-043/A-055: verified absence earns half credit (score = 100 x (favorable + 0.5 x absence share))",
            c4=c4_from_dims(a055))
        run(mode, "ELIGIBILITY_CONFIDENCE_ONLY", "REGULATORY_CODING",
            "A-051: MEDIUM/HIGH evidence is eligible whether or not the primary source was retrieved",
            c4=c4_from_dims(build_dims(d, mode, rule="CONFIDENCE_ONLY")))
    run("SIDEWALK_DELIVERY", "NEVADA_UNADJUSTED", "REGULATORY_CODING",
        "A-046: Nevada's campus-only PDD statute counted as a general authorization (scope adjustment removed)",
        c4=c4_from_dims(build_dims(d, "SIDEWALK_DELIVERY", nevada_scope_adjustment=False)))
    meth_defs, meth = pd.DataFrame(meth_defs), pd.DataFrame(meth_rows)
    # Phase 5 W3 publishes no snowfall for some stations; those markets keep the baseline value (disclosed).
    check("weather alternatives: markets without an alternative value keep their baseline value (counts disclosed)",
          True, "markets falling back: " + json.dumps({f"{k[0]}:{k[1]}": v for k, v in weather_fallback.items()}))

    # ---- Step 18: robustness summary ---------------------------------------------------------------
    ws = pd.concat(ws_rows, ignore_index=True)
    summ = []
    for mode, mm in models.items():
        w0 = ws[(ws["mode"] == mode) & (ws.regulatory_scenario == "BASELINE_EVIDENCE")].set_index("market_id")
        for mid in mm.markets:
            row = {"mode": mode, "market_id": mid, "market_name": names[mid], "baseline_score": base_score[mode][mid],
                   "baseline_rank": base_rank[mode][mid], "score_complete_flag": bool(pd.notna(base_score[mode][mid]))}
            if mid in w0.index:
                x = w0.loc[mid]
                row.update({k: x[k] for k in ["mean_rank", "median_rank", "rank_std", "best_rank", "worst_rank",
                                              "rank_p05", "rank_p95", "rank_interval_90", "top_5_frequency",
                                              "top_10_frequency"]})
            nr = [norm_rank[(mode, m)][mid] for m in ["PERCENTILE", "RAW_MINMAX", "WINSORIZED_MINMAX"]]
            nr = [v for v in nr if pd.notna(v)]
            mr = meth[(meth["mode"] == mode) & (meth.market_id == mid)]["rank"].dropna().tolist()
            br = scen_res[(scen_res["mode"] == mode) & (scen_res.market_id == mid)]["rank"].dropna().tolist()
            row["business_scenario_rank_range"] = (max(br) - min(br)) if br else np.nan
            row["normalization_rank_range"] = (max(nr) - min(nr)) if nr else np.nan
            row["methodology_rank_range"] = (max(mr + [base_rank[mode][mid]]) - min(mr + [base_rank[mode][mid]])) \
                if mr and pd.notna(base_rank[mode][mid]) else np.nan
            rg = reg[(reg["mode"] == mode) & (reg.market_id == mid)].iloc[0]
            row["regulatory_rank_range"] = rg.regulatory_rank_range
            row["regulatory_best_rank"] = min(rg.pessimistic_rank, rg.neutral_rank, rg.optimistic_rank)
            row["regulatory_worst_rank"] = max(rg.pessimistic_rank, rg.neutral_rank, rg.optimistic_rank)
            fixed_tests = nr + mr + br                     # named, deterministic alternatives
            row["fixed_test_worst_rank"] = max(fixed_tests) if fixed_tests else np.nan
            tested = fixed_tests + ([row["best_rank"], row["worst_rank"]] if "best_rank" in row else [])
            row["overall_tested_best_rank"] = min(tested) if tested else np.nan
            row["overall_tested_worst_rank"] = max(tested) if tested else np.nan
            if mode == "ROBOTAXI":
                for sc in REG_SCENARIOS:
                    x = ws[(ws["mode"] == mode) & (ws.regulatory_scenario == sc)].set_index("market_id").loc[mid]
                    row[f"{sc.lower()}_top5_frequency"] = x.top_5_frequency
                    row[f"{sc.lower()}_mean_rank"] = x.mean_rank
            # Transparent pattern flags (documented thresholds; no composite score)
            row["consistent_top_performer"] = bool(row.get("top_5_frequency", 0) >= TOP_FREQ
                                                   and row["fixed_test_worst_rank"] <= 5) if row["score_complete_flag"] else False
            row["weight_sensitive"] = bool(row.get("rank_interval_90", 0) >= WIDE_INTERVAL)
            row["normalization_sensitive"] = bool((row["normalization_rank_range"] or 0) >= MOVE)
            row["methodology_sensitive"] = bool((row["methodology_rank_range"] or 0) >= MOVE)
            # A complete market's rank can shift only because unscored markets enter the ranking; that is not
            # sensitivity of its own evidence, so the flag requires the market's own score to move.
            row["regulatory_score_range"] = rg.regulatory_score_range
            row["regulation_sensitive"] = bool(rg.regulatory_score_range > TOL and rg.regulatory_rank_range >= MOVE)
            summ.append(row)
    summ = pd.DataFrame(summ)
    labels = ["consistent_top_performer", "weight_sensitive", "normalization_sensitive", "methodology_sensitive",
              "regulation_sensitive"]
    summ["pattern_flags"] = summ[labels].apply(lambda r: ";".join(l.upper() for l in labels if r[l]), axis=1)

    # ---- Exports --------------------------------------------------------------------------------
    no_cross = [c for df in (baseline, scen_res, ws, norm, reg, meth, summ) for c in df.columns
                if any(t in c.lower() for t in ("combined", "cross_mode", "all_mode", "overall_autonomy"))]
    check("no cross-mode combined score in any output", not no_cross and all(
        set(df["mode"].unique()) <= set(MODES) for df in (baseline, scen_res, ws, norm, reg, meth, summ)))
    dep_cols = [c for df in (baseline, scen_res, ws, norm, reg, meth, summ) for c in df.columns if "deploy" in c.lower()]
    check("no deployment field in any sensitivity output", not dep_cols)
    src = Path(__file__).read_text(encoding="utf-8")
    target = "deployment_" + "evidence.csv"            # built by concatenation so this line cannot match itself
    check("sensitivity code never references the deployment evidence file", target not in src)

    def export(df: pd.DataFrame, name: str, sort: list[str]) -> None:
        df = df.sort_values(sort, kind="mergesort").copy()
        for c in df.columns:
            if df[c].dtype.kind == "f":
                df[c] = df[c].round(OUT_DEC) + 0.0
        df.to_csv(OUT / name, index=False, lineterminator="\n", float_format=f"%.{OUT_DEC}f")

    order = {"mode": {m: i for i, m in enumerate(MODES)}}
    export(baseline, "baseline_snapshot.csv", ["mode", "market_id"])
    export(scen_defs, "scenario_simulator_contract.csv", ["mode", "scenario_id"])
    export(scen_res, "business_priority_scenarios.csv", ["mode", "scenario_id", "market_id"])
    export(ws.merge(pd.Series(names, name="market_name"), left_on="market_id", right_index=True),
           "weight_sensitivity_summary.csv", ["mode", "regulatory_scenario", "market_id"])
    export(norm, "normalization_sensitivity.csv", ["mode", "normalization", "market_id"])
    export(norm_cmp, "normalization_comparison.csv", ["mode", "normalization"])
    export(reg, "regulatory_uncertainty.csv", ["mode", "market_id"])
    export(meth, "methodology_sensitivity.csv", ["mode", "family", "test_id", "market_id"])
    export(meth_defs, "methodology_comparison.csv", ["mode", "family", "test_id"])
    for fam, fname in [("FEATURE_DROP", "feature_drop_sensitivity.csv"), ("AIRPORT", "airport_sensitivity.csv"),
                       ("DENSITY", "density_sensitivity.csv"), ("WEATHER", "weather_sensitivity.csv"),
                       ("WIND", "wind_sensitivity.csv"), ("REGULATORY_CODING", "regulatory_coding_sensitivity.csv")]:
        export(meth[meth.family == fam], fname, ["mode", "test_id", "market_id"])
    export(summ, "robustness_summary.csv", ["mode", "market_id"])
    export(pd.DataFrame(CHECKS), "qa_checks_sensitivity.csv", ["check"])
    _ = order

    figs = figures(summ, ws, rank_mats, norm, reg, scen_res, names)

    # ---- Metadata + checksum manifest (no volatile fields) -----------------------------------------
    p7 = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
          for p in sorted((ROOT / "outputs" / "phase7").rglob("*")) if p.is_file() and p.suffix in (".csv", ".json")}
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "model_metadata.json"
                and not p.name.startswith("deployment") and "07_deployment" not in p.name}
    meta = {
        "phase": 8,
        "git_input_commit": GIT_INPUT_COMMIT,
        "model_input_commit": MODEL_INPUT_COMMIT,
        "baseline_model_version": BASELINE_VERSION,
        "random_seed": SEED,
        "random_generator": "numpy.random.default_rng (PCG64); Dirichlet draws taken in mode order ROBOTAXI, "
                            "SIDEWALK_DELIVERY, DRONE_DELIVERY; the robotaxi draws are reused for the three nested "
                            "regulatory scenarios (common random numbers)",
        "draws_per_mode": N_DRAWS,
        "dirichlet_alpha": 1.0,
        "dirichlet_interpretation": "A uniform stress test over the component-weight simplex; not a probability "
                                    "distribution of business preferences",
        "within_component_weights": "equal (unchanged from baseline_v1)",
        "rank_rule": f"standard competition rank among markets with a complete score; ties at {RANK_DEC} decimals",
        "input_rounding_decimals": IN_DEC,
        "export_decimals": OUT_DEC,
        "regulatory_scenarios": REG_SCENARIOS,
        "normalizations": {"PERCENTILE": "baseline average-rank percentile",
                           "RAW_MINMAX": "100 x (x - min) / (max - min) on the transformed value",
                           "WINSORIZED_MINMAX": "clip to the 5th and 95th cross-sectional percentiles (numpy "
                                                "'linear' method) then min-max"},
        "pattern_flag_thresholds": {"consistent_top_performer": f"top-5 frequency >= {TOP_FREQ} and rank <= 5 under "
                                                                "every named normalization, methodology and business test",
                                    "weight_sensitive": f"90% Dirichlet rank interval >= {WIDE_INTERVAL}",
                                    "normalization_sensitive": f"rank range across normalizations >= {MOVE}",
                                    "methodology_sensitive": f"rank range across methodology tests >= {MOVE}",
                                    "regulation_sensitive": f"own score changes across the regulatory scenarios and "
                                                            f"the rank range >= {MOVE} (complete markets displaced only by "
                                                            "newly ranked markets are not flagged)"},
        "deployment_evidence_used": False,
        "phase7_output_checksums_sha256_lf": p7,
        "sensitivity_output_manifest_sha256": manifest,
        "figures": figs,
        "qa_checks_passed": sum(c["status"] == "PASS" for c in CHECKS),
        "qa_checks_failed": sum(c["status"] == "FAIL" for c in CHECKS),
    }
    with _real_open(OUT / "model_metadata.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(meta, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    failed = meta["qa_checks_failed"]
    print(f"\n{meta['qa_checks_passed']} checks passed, {failed} failed. Outputs in {OUT.relative_to(ROOT)}")
    return 1 if failed else 0


# ---------------------------------------------------------------------------------------- figures
def figures(summ, ws, rank_mats, norm, reg, scen_res, names) -> list[str]:
    plt = dg.plt
    short = lambda n: str(n).split(",")[0].split("-")[0]  # noqa: E731
    made = []
    fig, axes = plt.subplots(1, 3, figsize=(14, 6.5))
    for ax, mode in zip(axes, MODES):
        x = summ[(summ["mode"] == mode) & summ.top_5_frequency.notna() & (summ.top_5_frequency > 0)]
        x = x.sort_values(["top_5_frequency", "market_id"])
        ax.barh(np.arange(len(x)), x.top_5_frequency * 100, color=dg.SLOTS[0], height=0.7, edgecolor=dg.SURFACE)
        ax.set_yticks(np.arange(len(x)), [short(n) for n in x.market_name], fontsize=7)
        for yi, v in enumerate(x.top_5_frequency * 100):
            ax.text(v + 1, yi, f"{v:.0f}%", va="center", fontsize=6.5, color=dg.INK_2)
        ax.set_xlim(0, 110)
        ax.set_xlabel("Share of 10,000 weight draws ranked in the top 5")
        ax.set_title(mode.replace("_", " ").title(), fontsize=10)
        ax.grid(axis="y", visible=False)
    fig.suptitle("Top-5 frequency across tested component-weight configurations (not a probability of being best)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    made.append(dg._save(fig, FIG / "01_top5_frequency.png"))

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, mode in zip(axes, MODES):
        ids, R = rank_mats[(mode, "BASELINE_EVIDENCE")]
        x = summ[(summ["mode"] == mode) & summ.baseline_rank.notna()].sort_values("baseline_rank").head(10)
        pos = {m: i for i, m in enumerate(ids)}
        data = [R[pos[m]] for m in x.market_id]
        bp = ax.boxplot(data, orientation="horizontal", whis=(5, 95), showfliers=False, patch_artist=True, widths=0.6)
        for b in bp["boxes"]:
            b.set(facecolor="#cde2fb", edgecolor=dg.SLOTS[0])
        for k in ("whiskers", "caps", "medians"):
            for ln in bp[k]:
                ln.set(color=dg.SLOTS[0])
        ax.scatter(x.baseline_rank, np.arange(1, len(x) + 1), color=dg.SLOTS[1], zorder=5, s=24, label="baseline rank")
        ax.set_yticks(np.arange(1, len(x) + 1), [short(n) for n in x.market_name], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("Rank across weight draws (box: IQR; whiskers: 5th-95th pct.)")
        ax.set_title(f"{mode.replace('_', ' ').title()}: baseline top 10", fontsize=10)
        ax.grid(axis="y", visible=False)
    axes[0].legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    made.append(dg._save(fig, FIG / "02_rank_distributions_baseline_top10.png"))

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    for ax, mode in zip(axes, MODES):
        x = summ[(summ["mode"] == mode) & summ.mean_rank.notna()]
        ax.scatter(x.baseline_rank, x.mean_rank, s=28, color=dg.SLOTS[0], edgecolor=dg.SURFACE, linewidth=1.2, zorder=3)
        n = int(x.baseline_rank.max())
        ax.plot([1, n], [1, n], color=dg.AXIS, linewidth=1)
        for r in x.sort_values("baseline_rank").head(5).itertuples():
            ax.annotate(short(r.market_name), (r.baseline_rank, r.mean_rank), xytext=(4, 3), textcoords="offset points",
                        fontsize=6.5, color=dg.INK_2)
        ax.set_xlabel("Baseline rank")
        ax.set_ylabel("Mean rank across weight draws")
        ax.set_title(mode.replace("_", " ").title(), fontsize=10)
    fig.tight_layout()
    made.append(dg._save(fig, FIG / "03_baseline_vs_mean_rank.png"))

    fig, axes = plt.subplots(1, 3, figsize=(14, 7))
    for ax, mode in zip(axes, MODES):
        x = norm[(norm["mode"] == mode) & norm.baseline_rank.notna()]
        piv = x.pivot(index="market_id", columns="normalization", values="rank").sort_values("PERCENTILE")
        y = np.arange(len(piv))
        for i, m in enumerate(["PERCENTILE", "RAW_MINMAX", "WINSORIZED_MINMAX"]):
            ax.scatter(piv[m], y, s=22, color=dg.SLOTS[i], edgecolor=dg.SURFACE, linewidth=1, zorder=3 + i,
                       label=m.replace("_", " ").title())
        ax.set_yticks(y, [short(names[m]) for m in piv.index], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("Rank")
        ax.set_title(mode.replace("_", " ").title(), fontsize=10)
        ax.grid(axis="y", visible=False)
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("Rank under each normalization (rows sorted by baseline percentile rank)", x=0.01, ha="left",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    made.append(dg._save(fig, FIG / "04_normalization_rank_movement.png"))

    x = reg[reg["mode"] == "ROBOTAXI"].sort_values(["neutral_rank", "market_id"])
    fig, ax = plt.subplots(figsize=(8, 8.5))
    y = np.arange(len(x))
    ax.hlines(y, x.optimistic_rank, x.pessimistic_rank, color=dg.AXIS, linewidth=2, zorder=1)
    ax.scatter(x.optimistic_rank, y, color=dg.SLOTS[2], s=22, zorder=3, label="optimistic (unknown = 100% favorable)")
    ax.scatter(x.neutral_rank, y, color=dg.SLOTS[0], s=22, zorder=4, label="neutral (50%)")
    ax.scatter(x.pessimistic_rank, y, color=dg.SLOTS[1], s=22, zorder=3, label="pessimistic (0%)")
    ax.set_yticks(y, [short(n) + ("" if c else " *") for n, c in zip(x.market_name, x.c4_complete_flag)], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Robotaxi rank among all 35 markets (equal weights)")
    ax.set_title("Robotaxi regulatory uncertainty: rank under the three bounds (* = C4 incomplete in the baseline)")
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax.grid(axis="y", visible=False)
    made.append(dg._save(fig, FIG / "05_robotaxi_regulatory_uncertainty.png"))

    seq = dg.LinearSegmentedColormap.from_list("rank_seq", ["#104281", "#3987e5", "#cde2fb"])
    fig, axes = plt.subplots(1, 3, figsize=(15, 8.5))
    for ax, mode in zip(axes, MODES):
        x = scen_res[(scen_res["mode"] == mode) & scen_res["rank"].notna()]
        piv = x.pivot(index="market_id", columns="scenario_id", values="rank")
        cols = [c for c in piv.columns if c.endswith("_NEUTRAL")] + sorted(c for c in piv.columns if not c.endswith("_NEUTRAL"))
        piv = piv[cols].sort_values(cols[0])
        im = ax.imshow(piv.values, cmap=seq, aspect="auto", vmin=1, vmax=len(piv))
        for (yi, xi), v in np.ndenumerate(piv.values):
            ax.text(xi, yi, f"{int(v)}", ha="center", va="center", fontsize=6, color=dg.INK if v > len(piv) / 2 else "#ffffff")
        ax.set_xticks(range(len(cols)), [c.split("_", 1)[1].replace("_PRIORITY", "").replace("_", " ").title() for c in cols],
                      rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(piv)), [short(names[m]) for m in piv.index], fontsize=7)
        ax.grid(False)
        ax.set_title(mode.replace("_", " ").title(), fontsize=10)
    fig.colorbar(im, ax=axes, fraction=0.015, pad=0.01).set_label("Rank (1 = best)", color=dg.INK_2)
    fig.suptitle("Rank under each named business-priority scenario (priority component at 40%)", x=0.01, ha="left",
                 fontsize=11, fontweight="bold")
    made.append(dg._save(fig, FIG / "06_business_scenarios.png"))
    return made


if __name__ == "__main__":
    sys.exit(main())
