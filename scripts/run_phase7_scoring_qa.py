"""Phase 7 baseline readiness model: independent QA, exports and diagnostics.

dbt computes the production scores (models/scoring). This script does NOT produce scores: it
  1. verifies the frozen model inputs (contracts and Phase 6.5b eligibility at commit 55b1cb4) and
     that the regulatory seeds still match evidence/;
  2. recomputes every feature, dimension, component and overall score, and every baseline rank,
     independently in pandas from the source files and the Phase 6 feature marts, and reconciles them
     with the dbt tables (Steps 23-26);
  3. exports the machine-readable outputs and diagnostics to outputs/phase7/ (Steps 28-33).

It reads with AM_TRANSFORMER and writes nothing to Snowflake. Deployment evidence is never read.
Exit code 1 if any check fails.

Usage (repository root, .venv active):
    python scripts/run_phase7_scoring_qa.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_regulatory_seed import SEEDS, build as build_seeds  # noqa: E402
from src.analytics import diagnostics as dg  # noqa: E402
from src.analytics.data_access import Warehouse  # noqa: E402

OUT = ROOT / "outputs" / "phase7"
FIG = OUT / "figures"
DB = "AUTONOMOUS_MOBILITY"
MODEL_VERSION = "baseline_v1"
INPUT_COMMIT = "55b1cb4"
EVIDENCE_AS_OF = "2026-10-05"   # frozen regulatory and deployment evidence date (Phase 6.5 / 6.5b)
TOL = 1e-6
CORR_INPUT_DECIMALS = 9      # component scores are rounded to this before ranking (diagnostic only)
CORR_OUTPUT_DECIMALS = 12    # exported Spearman rho precision
EXPORT_DIFF_FLOOR = 1e-12    # score_reconciliation.csv reporting floor only; the PASS/FAIL tolerance stays TOL
MODES = ["ROBOTAXI", "SIDEWALK_DELIVERY", "DRONE_DELIVERY"]
MODE_FILE = {"ROBOTAXI": "robotaxi", "SIDEWALK_DELIVERY": "sidewalk", "DRONE_DELIVERY": "drone"}
MARTS = {"ROBOTAXI": "MART_ROBOTAXI_FEATURES", "SIDEWALK_DELIVERY": "MART_SIDEWALK_DELIVERY_FEATURES",
         "DRONE_DELIVERY": "MART_DRONE_DELIVERY_FEATURES"}
BASELINES = {"ROBOTAXI": "MART_ROBOTAXI_READINESS_BASELINE",
             "SIDEWALK_DELIVERY": "MART_SIDEWALK_DELIVERY_READINESS_BASELINE",
             "DRONE_DELIVERY": "MART_DRONE_DELIVERY_READINESS_BASELINE"}
C4 = "C4_REGULATORY_AND_AUTONOMY_READINESS"
COMPONENTS = ["C1_DEMAND_AND_MARKET_OPPORTUNITY", "C2_OPERATING_ENVIRONMENT", "C3_ECONOMIC_ATTRACTIVENESS", C4,
              "C5_INFRASTRUCTURE_AND_MODE_FIT"]
SHORT = dict(zip(COMPONENTS, ["C1 Demand", "C2 Operating env.", "C3 Economic", "C4 Regulatory", "C5 Infra & fit"]))
# Categorical slots 1-5 of the dataviz reference palette in fixed order: the colour follows the component.
PALETTE5 = dg.SLOTS + ["#eda100", "#e87ba4"]
RAW_COLUMN = {"population_2025_log1p": "population_2025", "pw_tract_density_log1p": "population_weighted_tract_density",
              "enplanements_per_resident_log1p": "enplanements_per_resident"}
ABSENCE = {"NO_SPECIFIC_STATUTE", "NO_SPECIFIC_FRAMEWORK", "NOT_ADDRESSED", "NO_STATUTE"}
NUMERIC_METHOD = "MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES"
FROZEN = {
    "feature_contract": "dbt/seeds/feature_contract.csv",
    "regulatory_contract": "config/regulatory_feature_contract.csv",
    "regulatory_eligibility_phase65b": "outputs/phase65/phase7_regulatory_eligibility.csv",
}
CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "", n: int | None = None, max_abs_diff: float | None = None) -> bool:
    CHECKS.append({"check": name, "status": "PASS" if ok else "FAIL", "n_compared": n,
                   "max_abs_diff": max_abs_diff, "tolerance": TOL if max_abs_diff is not None else None,
                   "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))
    return ok


def compare(name: str, a: pd.Series, b: pd.Series, detail: str = "") -> bool:
    """Numeric equality within TOL, with nulls required in the same places."""
    a, b = a.astype(float), b.astype(float)
    null_mismatch = int((a.isna() != b.isna()).sum())
    diff = (a - b).abs().max() if (a.notna() & b.notna()).any() else 0.0
    diff = 0.0 if pd.isna(diff) else float(diff)
    return check(name, null_mismatch == 0 and diff <= TOL,
                 (detail + "; " if detail else "") + f"null mismatches {null_mismatch}", len(a), diff)


def sha256_text(path: Path) -> str:
    """Checksum of the LF-normalized content, so it is stable across Windows checkouts."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# --------------------------------------------------------------------------------------------- inputs
def verify_frozen_inputs() -> dict:
    print("Frozen model inputs (commit %s)" % INPUT_COMMIT)
    out = {}
    for key, rel in FROZEN.items():
        committed = hashlib.sha256(subprocess.run(["git", "show", f"{INPUT_COMMIT}:{rel}"], cwd=ROOT,
                                                  capture_output=True, check=True).stdout.replace(b"\r\n", b"\n")).hexdigest()
        current = sha256_text(ROOT / rel)
        check(f"frozen input unchanged since {INPUT_COMMIT}: {rel}", committed == current, f"sha256 {current[:16]}")
        out[key] = {"path": rel, "sha256_lf": current, "matches_commit": committed == current}
    stale = [n for n, t in build_seeds().items()
             if (SEEDS / f"{n}.csv").read_bytes().replace(b"\r\n", b"\n").decode("utf-8") != t]
    check("regulatory seeds match evidence/ and config/ (build_regulatory_seed --check)", not stale, f"stale: {stale}")
    for s in ("regulatory_state_evidence", "regulatory_feature_contract", "regulatory_scope_adjustments"):
        out[f"seed_{s}"] = {"path": f"dbt/seeds/{s}.csv", "sha256_lf": sha256_text(SEEDS / f"{s}.csv")}
    return out


def load(wh: Warehouse) -> dict[str, pd.DataFrame]:
    # Every read is ordered by the relation's documented grain, so no downstream computation depends on
    # the order in which Snowflake happens to return rows.
    q = lambda schema, t, order: wh.query(f"select * from {DB}.{schema}.{t} order by {order}")  # noqa: E731
    d = {m: q("ANALYTICS", t, "market_id") for m, t in MARTS.items()}
    d.update({
        "prod": q("INTERMEDIATE", "INT_MARKET__PRODUCTION_FEATURES", "market_id"),
        "brg": q("CORE", "BRG_MARKET_STATE", "market_id, state_usps"),
        "dim_market": q("CORE", "DIM_MARKET", "market_id"),
        "fs": q("ANALYTICS", "FCT_FEATURE_SCORES", "mode, market_id, component, feature_id"),
        "cs": q("ANALYTICS", "FCT_COMPONENT_SCORES", "mode, market_id, component"),
        "rd": q("ANALYTICS", "FCT_REGULATORY_DIMENSION_SCORES", "mode, market_id, legal_dimension"),
        "rb": q("ANALYTICS", "FCT_READINESS_BASELINE", "mode, market_id"),
        "ev_int": q("INTERMEDIATE", "INT_REGULATORY__MARKET_STATE_EVIDENCE",
                    "mode, market_id, legal_dimension, state_usps"),
    })
    for m, t in BASELINES.items():
        d[f"mart_{m}"] = q("ANALYTICS", t, "market_id")
    for k, v in d.items():
        if "market_id" in v:
            v["market_id"] = v["market_id"].astype(str)
    return d


# ------------------------------------------------------------------------ independent recomputation
def percentile(values: pd.Series) -> pd.Series:
    n = values.notna().sum()
    return 100 * (values.rank(method="average") - 1) / (n - 1)


def recompute_features(d) -> pd.DataFrame:
    con = pd.read_csv(ROOT / FROZEN["feature_contract"], dtype=str, keep_default_na=False)
    con = con[con.production_status == "ACTIVE"]
    rows = []
    for mode in MODES:
        mart = d[mode].set_index("market_id")
        prod = d["prod"].set_index("market_id")
        for f in con[con["mode"] == mode].itertuples():
            v = mart[f.feature_name].astype(float)
            p = percentile(v)
            score = p if f.direction == "HIGHER_IS_MORE_FAVORABLE" else 100 - p
            assert f.direction in ("HIGHER_IS_MORE_FAVORABLE", "LOWER_IS_MORE_FAVORABLE"), f.feature_id
            raw = prod.loc[v.index, RAW_COLUMN.get(f.feature_name, f.feature_name)].astype(float)
            rows.append(pd.DataFrame({"market_id": v.index, "mode": mode, "feature_id": f.feature_id,
                                      "feature_name": f.feature_name, "component": f.component,
                                      "direction": f.direction, "raw_value": raw.values,
                                      "transformed_value": v.values, "feature_score": score.values}))
    return pd.concat(rows, ignore_index=True)


def recompute_regulatory(d) -> tuple[pd.DataFrame, pd.DataFrame]:
    """From evidence/regulatory_evidence.csv directly (not the seed) and CORE.BRG_MARKET_STATE."""
    con = pd.read_csv(ROOT / FROZEN["regulatory_contract"], dtype=str, keep_default_na=False)
    con = con[con.candidate_status == "ACTIVE_CANDIDATE"]
    ev = pd.read_csv(ROOT / "evidence" / "regulatory_evidence.csv", dtype=str, keep_default_na=False)
    ev = ev[ev.jurisdiction_type == "STATE"].rename(columns={"jurisdiction": "state_usps"})
    adj = pd.read_csv(SEEDS / "regulatory_scope_adjustments.csv", dtype=str)
    ev["eligible"] = ev.confidence.isin(["HIGH", "MEDIUM"]) & (ev.verification_status == "VERIFIED_PRIMARY")
    fav = {(r.mode, r.legal_dimension): set(r.favorable_statuses.split("|")) for r in con.itertuples()}
    ev["favorable"] = [(s in fav.get((m, dim), set())) and (i not in set(adj.evidence_id))
                       for m, dim, s, i in zip(ev["mode"], ev.legal_dimension, ev.coded_status, ev.evidence_id)]
    pdd = ev[ev.legal_dimension == "SW_PDD_LEGAL_STATUS"].set_index("state_usps")
    evk = ev.set_index(["mode", "legal_dimension", "state_usps"])
    rows = []
    for c in con.itertuples():
        for b in d["brg"].itertuples():
            key = (c.mode, c.legal_dimension, b.state_usps)
            e = evk.loc[key] if key in evk.index else None
            if c.market_mapping_method == NUMERIC_METHOD:
                p = pdd.loc[b.state_usps] if b.state_usps in pdd.index else None
                if p is None or not p.eligible:
                    cls = "UNKNOWN_OR_LOW_CONFIDENCE"
                elif not p.favorable:
                    cls = "NOT_APPLICABLE"
                elif e is None or not e.eligible:
                    cls = "UNKNOWN_OR_LOW_CONFIDENCE"
                else:
                    cls = "VERIFIED_FAVORABLE"
            else:
                cls = ("UNKNOWN_OR_LOW_CONFIDENCE" if e is None or not e.eligible
                       else "VERIFIED_FAVORABLE" if e.favorable else "VERIFIED_NOT_FAVORABLE")
            reason = None
            if cls == "VERIFIED_NOT_FAVORABLE":
                reason = ("SCOPE_LIMITED" if e.evidence_id in set(adj.evidence_id) else "ABSENCE"
                          if e.coded_status in ABSENCE else "UNCLEAR" if e.coded_status == "UNCLEAR"
                          else "EXPLICIT_NOT_FAVORABLE")
            rows.append({"market_id": b.market_id, "mode": c.mode, "legal_dimension": c.legal_dimension,
                         "feature_id": c.feature_id, "method": c.market_mapping_method, "state_usps": b.state_usps,
                         "share": float(b.population_share_2025), "cls": cls, "reason": reason,
                         "coded_status": None if e is None else e.coded_status,
                         "numeric": None if e is None or e.numeric_value == "" else float(e.numeric_value),
                         "evidence_id": None if e is None else e.evidence_id})
    st = pd.DataFrame(rows)
    st["market_id"] = st["market_id"].astype(str)
    g = st.groupby(["market_id", "mode", "legal_dimension", "feature_id", "method"])
    dim = g.apply(lambda x: pd.Series({
        "fav": x.share[x.cls == "VERIFIED_FAVORABLE"].sum(),
        "unfav": x.share[x.cls == "VERIFIED_NOT_FAVORABLE"].sum(),
        "unknown": x.share[x.cls == "UNKNOWN_OR_LOW_CONFIDENCE"].sum(),
        "na": x.share[x.cls == "NOT_APPLICABLE"].sum(),
        "limit": x.numeric[(x.cls == "VERIFIED_FAVORABLE") & (x.coded_status == "SPECIFIED")].min(),
    }), include_groups=False).reset_index()
    dim["complete"] = dim.unknown <= TOL
    dim["applicable"] = np.where(dim.method == NUMERIC_METHOD, dim.fav > TOL, True)
    dim["score"] = np.where(dim.complete, 100 * dim.fav, np.nan)
    num = dim[(dim.method == NUMERIC_METHOD)]
    dom = num[num.complete & num.applicable].copy()
    dom["rv"] = dom["limit"].fillna(1e12)
    for (m, ld), grp in dom.groupby(["mode", "legal_dimension"]):
        dom.loc[grp.index, "pct"] = percentile(grp.rv)
    dim.loc[num.index, "score"] = np.nan
    dim.loc[dom.index, "score"] = dom.pct
    return st, dim


def recompute_scores(feat: pd.DataFrame, dim: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    c4c = dim.groupby(["market_id", "mode"]).complete.all().rename("c4_complete").reset_index()
    reg = dim.rename(columns={"score": "feature_score", "legal_dimension": "feature_name"})
    reg = reg.assign(component=C4, in_base=None)[["market_id", "mode", "feature_id", "component", "feature_score",
                                                   "complete", "applicable"]]
    nonreg = feat.assign(complete=True, applicable=True)[["market_id", "mode", "feature_id", "component",
                                                          "feature_score", "complete", "applicable"]]
    a = pd.concat([nonreg, reg], ignore_index=True).merge(c4c, on=["market_id", "mode"])
    a["in_base"] = np.where(a.component == C4, a.c4_complete & a.applicable, True)
    a["n_in"] = a.groupby(["market_id", "mode", "component"]).in_base.transform("sum")
    a["w"] = np.where(a.in_base, 1 / a.n_in, np.nan)
    a["wc"] = a.feature_score * a.w
    k = a.groupby(["market_id", "mode"]).component.transform("nunique")
    a["cw"] = 1 / k
    comp = a.groupby(["market_id", "mode", "component"]).agg(
        score=("wc", lambda s: s.sum(min_count=1)), complete=("complete", "all"), cw=("cw", "max")).reset_index()
    comp.loc[~comp.complete, "score"] = np.nan
    comp["contrib"] = comp.score * comp.cw
    mk = comp.groupby(["market_id", "mode"]).agg(complete=("complete", "all"), total=("contrib", "sum")).reset_index()
    mk["score"] = np.where(mk.complete, mk.total, np.nan)
    nr = comp[comp.component != C4].groupby(["market_id", "mode"]).score.mean().rename("non_reg").reset_index()
    mk = mk.merge(nr, on=["market_id", "mode"])
    mk["rank"] = mk.groupby("mode").score.transform(lambda s: s.round(6).rank(method="min", ascending=False))
    return comp, mk


# ----------------------------------------------------------------------------------------- checks
def reconcile(d, feat, st, dim, comp, mk) -> None:
    print("Independent recomputation vs dbt")
    k = ["market_id", "mode", "feature_id"]
    fs = d["fs"]
    m = feat.merge(fs, on=k, suffixes=("_py", "_dbt"))
    check("every active feature present in FCT_FEATURE_SCORES", len(m) == len(feat) == 1050, f"{len(m)} rows")
    compare("feature scores (percentile, direction)", m.feature_score_py, m.feature_score_dbt)
    compare("raw values", m.raw_value_py, m.raw_value_dbt)
    compare("transformed values (= Phase 6 mode marts)", m.transformed_value_py, m.transformed_value_dbt)

    rd = d["rd"].merge(dim, on=["market_id", "mode", "legal_dimension"])
    check("every regulatory market x dimension present", len(rd) == 245, f"{len(rd)} rows")
    compare("verified favorable share", rd.verified_favorable_share, rd.fav)
    compare("verified unfavorable share", rd.verified_unfavorable_share, rd.unfav)
    compare("unknown / LOW-confidence share", rd.unknown_or_low_confidence_share, rd.unknown)
    compare("not-applicable share", rd.not_applicable_share, rd.na)
    compare("regulatory dimension scores", rd.dimension_score, rd.score)
    check("dimension completeness flags", (rd.dimension_complete_flag == rd.complete).all())

    ce = d["ev_int"].merge(st, on=["market_id", "mode", "legal_dimension", "state_usps"])
    check("state evidence classes (dbt seed path = evidence file path)",
          len(ce) == 357 and (ce.base_evidence_class == ce.cls).all(), f"{len(ce)} rows")

    cs = d["cs"].merge(comp, on=["market_id", "mode", "component"])
    check("every active component present", len(cs) == 490, f"{len(cs)} rows")
    compare("component scores", cs.component_score, cs.score)
    compare("component contributions", cs.component_contribution, cs.contrib)

    rb = d["rb"].merge(mk, on=["market_id", "mode"])
    compare("baseline readiness scores", rb.baseline_readiness_score, rb.score)
    compare("non-regulatory diagnostic scores", rb.non_regulatory_score, rb.non_reg)
    compare("baseline ranks", rb.baseline_rank, rb["rank"])

    print("Internal reconciliation of the dbt tables")
    s = fs.groupby(["market_id", "mode", "component"]).weighted_feature_contribution.sum(min_count=1).rename("s")
    x = d["cs"].set_index(["market_id", "mode", "component"]).join(s)
    x = x[x.component_score.notna()]
    compare("component_score = sum(weighted_feature_contribution)", x.component_score, x.s)
    w = d["cs"][d["cs"].component_score.notna()]
    check("feature weights sum to 1 within every scored component",
          (w.feature_weight_sum - 1).abs().max() <= TOL, f"{len(w)} components")
    cw = d["cs"].groupby(["market_id", "mode"]).component_weight.sum()
    check("component weights sum to 1 within every market x mode", (cw - 1).abs().max() <= TOL, f"{len(cw)}")
    full = d["rb"][d["rb"].baseline_readiness_score.notna()].set_index(["market_id", "mode"])
    s2 = d["cs"].groupby(["market_id", "mode"]).component_contribution.sum()
    s3 = fs.groupby(["market_id", "mode"]).contribution_to_overall.sum()
    compare("overall = sum(component_contribution)", full.baseline_readiness_score, s2.loc[full.index])
    compare("overall = sum(feature contribution_to_overall)", full.baseline_readiness_score, s3.loc[full.index])
    for mode in MODES:
        mt = d[f"mart_{mode}"].set_index("market_id")
        b = d["rb"][d["rb"]["mode"] == mode].set_index("market_id").loc[mt.index]
        compare(f"{BASELINES[mode]} = FCT_READINESS_BASELINE", mt.baseline_readiness_score, b.baseline_readiness_score)


def eligibility_and_mapping(d, st) -> None:
    print("Regulatory eligibility and mapping")
    el = pd.read_csv(ROOT / FROZEN["regulatory_eligibility_phase65b"], dtype=str)
    s = st.drop_duplicates(["mode", "legal_dimension", "state_usps"]).set_index(["legal_dimension", "state_usps"])
    s = s[s["mode"] == "ROBOTAXI"]
    got = [("UNKNOWN" if s.loc[(r.dimension, r.state)].cls == "UNKNOWN_OR_LOW_CONFIDENCE" else "VERIFIED")
           for r in el.itertuples()]
    exp = ["UNKNOWN" if r.phase7_eligible == "INCLUDE_ONLY_IN_SENSITIVITY" else "VERIFIED" for r in el.itertuples()]
    check("robotaxi eligibility = Phase 6.5b phase7_regulatory_eligibility.csv (93 records)",
          got == exp and len(el) == 93, f"{sum(a == b for a, b in zip(got, exp))}/{len(el)} agree")
    low10 = {"RT-MA-02", "RT-MA-03", "RT-MA-06", "RT-NJ-02", "RT-NJ-03", "RT-NJ-06", "RT-OH-02", "RT-OH-03",
             "RT-OH-06", "RT-NY-06"}
    classes = set(st[st.evidence_id.isin(low10)].cls)
    check("the 10 sensitivity-only robotaxi records are never verified", classes == {"UNKNOWN_OR_LOW_CONFIDENCE"})
    il = st[(st.evidence_id == "RT-IL-02")].iloc[0]
    check("Illinois driverless = NOT_AUTHORIZED, verified, not favorable (EXPLICIT)",
          il.coded_status == "NOT_AUTHORIZED" and il.cls == "VERIFIED_NOT_FAVORABLE" and il.reason == "EXPLICIT_NOT_FAVORABLE")
    # The dbt state -> market composition must equal the committed Phase 6.5 mapping layer.
    summ = pd.read_csv(ROOT / "outputs" / "phase65" / "market_regulatory_summary.csv", dtype=str)
    summ["market_id"] = summ.market_id.astype(str)
    mism = 0
    tested = 0
    for r in summ[summ.legal_dimension.isin(st.legal_dimension.unique())].itertuples():
        comp = {}
        for part in r.status_composition_by_population.split("|"):
            k, v = part.rsplit(":", 1)
            comp[k] = float(v)
        x = st[(st.market_id == r.market_id) & (st.legal_dimension == r.legal_dimension)]
        mine = x.assign(cs=x.coded_status.fillna("NOT_APPLICABLE_NO_PDD_STATUTE")).groupby("cs").share.sum()
        tested += 1
        if set(mine.index) != set(comp) or any(abs(mine[k] - comp[k]) > 5e-5 for k in comp):
            mism += 1
    check("market status composition = Phase 6.5 market_regulatory_summary.csv", mism == 0 and tested == 245,
          f"{tested} market x dimension rows, {mism} mismatches")


def normalization_qa(d, feat) -> pd.DataFrame:
    names = d["dim_market"].set_index(d["dim_market"].market_id.astype(str)).cbsa_name
    rows = []
    for (mode, fid), g in feat.groupby(["mode", "feature_id"]):
        g = g.set_index("market_id")
        lo_raw, hi_raw = g.transformed_value.idxmin(), g.transformed_value.idxmax()
        lo_s, hi_s = g.feature_score.idxmin(), g.feature_score.idxmax()
        up = g.direction.iloc[0] == "HIGHER_IS_MORE_FAVORABLE"
        rho = g.transformed_value.rank().corr(g.feature_score.rank())
        rows.append({
            "mode": mode, "feature_id": fid, "feature_name": g.feature_name.iloc[0], "component": g.component.iloc[0],
            "direction": g.direction.iloc[0], "n_markets": len(g), "null_scores": int(g.feature_score.isna().sum()),
            "min_score": g.feature_score.min(), "max_score": g.feature_score.max(), "mean_score": g.feature_score.mean(),
            "tie_groups": int((g.transformed_value.value_counts() > 1).sum()),
            "lowest_raw_market": names[lo_raw], "lowest_raw_value": g.raw_value[lo_raw],
            "highest_raw_market": names[hi_raw], "highest_raw_value": g.raw_value[hi_raw],
            "lowest_score_market": names[lo_s], "highest_score_market": names[hi_s],
            "value_score_rank_correlation": rho,
            "direction_confirmed": bool((rho > 0.999) if up else (rho < -0.999)),
        })
    q = pd.DataFrame(rows)
    check("feature scores within 0-100 and not null", q.null_scores.sum() == 0 and q.min_score.min() >= 0
          and q.max_score.max() <= 100, f"{len(q)} mode x feature")
    check("direction applied for every feature (rank correlation +1 / -1)", q.direction_confirmed.all())
    return q


# ------------------------------------------------------------------------------------- diagnostics
def stats(s: pd.Series) -> dict:
    s = s.dropna().astype(float)
    # Adjacent gaps only (diagnostic): scores rounded to CORR_INPUT_DECIMALS first, so a tie stays an exact
    # tie whatever float residue a dbt build leaves; gaps rounded again, and + 0.0 turns a -0.0 into 0.0.
    srt = s.round(CORR_INPUT_DECIMALS).sort_values(ascending=False)
    gaps = (-srt.diff().dropna()).round(CORR_INPUT_DECIMALS) + 0.0
    return {"n": len(s), "min": s.min(), "max": s.max(), "range": s.max() - s.min(), "mean": s.mean(),
            "median": s.median(), "std": s.std(ddof=0), "iqr": s.quantile(0.75) - s.quantile(0.25),
            "adjacent_gap_min": gaps.min() if len(gaps) else np.nan,
            "adjacent_gap_median": gaps.median() if len(gaps) else np.nan,
            "adjacent_gap_max": gaps.max() if len(gaps) else np.nan,
            "exact_ties": int((s.round(6).value_counts() > 1).sum())}


def diagnostics(d) -> dict[str, pd.DataFrame]:
    rb, cs, fs = d["rb"], d["cs"], d["fs"]
    dist = []
    for mode in MODES:
        x = rb[rb["mode"] == mode]
        dist.append({"mode": mode, "measure": "baseline_readiness_score", **stats(x.baseline_readiness_score)})
        dist.append({"mode": mode, "measure": "non_regulatory_score (diagnostic, all 35)", **stats(x.non_regulatory_score)})
        for comp in COMPONENTS:
            c = cs[(cs["mode"] == mode) & (cs.component == comp)]
            if len(c):
                dist.append({"mode": mode, "measure": f"component: {comp}", **stats(c.component_score)})
    var_rows, corr_rows = [], []
    for mode in MODES:
        full = rb[(rb["mode"] == mode) & rb.baseline_readiness_score.notna()].market_id
        c = cs[(cs["mode"] == mode) & cs.market_id.isin(full)]
        wide = c.pivot(index="market_id", columns="component", values="component_contribution")
        total = wide.sum(axis=1)
        v = total.var(ddof=0)
        for comp in wide.columns:
            var_rows.append({"mode": mode, "level": "component", "item": comp,
                             "weight": c[c.component == comp].component_weight.iloc[0],
                             "score_std": c[c.component == comp].component_score.std(ddof=0),
                             "variance_share": np.cov(wide[comp], total, ddof=0)[0, 1] / v})
        f = fs[(fs["mode"] == mode) & fs.market_id.isin(full)]
        fw = f.pivot(index="market_id", columns="feature_name", values="contribution_to_overall").fillna(0)
        for col in fw.columns:
            var_rows.append({"mode": mode, "level": "feature", "item": col,
                             "weight": f[f.feature_name == col].feature_weight.mean() * f.component_weight.iloc[0],
                             "score_std": f[f.feature_name == col].feature_score.std(ddof=0),
                             "variance_share": np.cov(fw[col].loc[total.index], total, ddof=0)[0, 1] / v})
        # Spearman ranks are tie-sensitive. Snowflake float sums can differ in the last bit between dbt
        # builds (e.g. a C4 of 100 stored as 99.99999999999999), which would break or create ties, so the
        # scores are rounded to 9 decimals for this diagnostic only (stored scores are untouched), and rho
        # is exported at a fixed 12 decimals.
        sc = c.pivot(index="market_id", columns="component", values="component_score").sort_index()
        sc = sc[sorted(sc.columns)].round(CORR_INPUT_DECIMALS)
        rho = sc.rank().corr().round(CORR_OUTPUT_DECIMALS)
        for a in rho.index:
            for b in rho.columns:
                corr_rows.append({"mode": mode, "component_a": a, "component_b": b,
                                  "spearman_rho": float(rho.loc[a, b]), "n_markets": len(sc)})
    return {"score_distribution": pd.DataFrame(dist), "variance_contribution": pd.DataFrame(var_rows),
            "component_correlation": pd.DataFrame(corr_rows)}


# ---------------------------------------------------------------------------------------- figures
def figures(d, diag) -> list[str]:
    plt = dg.plt
    made = []
    rb, cs = d["rb"], d["cs"]
    short = lambda n: n.split(",")[0].split("-")[0]  # noqa: E731

    fig, axes = plt.subplots(1, 3, figsize=(13, 6.6), sharex=True)
    for ax, mode in zip(axes, MODES):
        x = rb[(rb["mode"] == mode) & rb.baseline_readiness_score.notna()].sort_values("baseline_readiness_score")
        y = np.arange(len(x))
        ax.scatter(x.baseline_readiness_score, y, s=30, color=dg.SLOTS[0], edgecolor=dg.SURFACE, linewidth=1.5, zorder=3)
        ax.set_yticks(y, [short(n) for n in x.market_name], fontsize=7)
        ax.set_xlim(0, 100)
        ax.grid(axis="y", visible=False)
        inc = rb[(rb["mode"] == mode) & rb.baseline_readiness_score.isna()]
        ax.set_title(f"{mode.replace('_', ' ').title()}: {len(x)} scored", fontsize=10)
        ax.text(0, -0.09, f"C4 incomplete, not scored ({len(inc)}): " + ", ".join(short(n) for n in inc.market_name),
                transform=ax.transAxes, fontsize=6.5, color=dg.INK_2, wrap=True, va="top")
        ax.set_xlabel("Baseline readiness score (0-100, within mode only)")
    fig.suptitle("Baseline readiness scores by mode (baseline_v1; not comparable across modes)", x=0.01, ha="left",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    made.append(dg._save(fig, FIG / "01_baseline_score_distribution.png"))

    fig, axes = plt.subplots(1, 3, figsize=(14, 6.8), sharex=True)
    for ax, mode in zip(axes, MODES):
        full = rb[(rb["mode"] == mode) & rb.baseline_readiness_score.notna()].sort_values("baseline_readiness_score")
        c = cs[(cs["mode"] == mode)].pivot(index="market_id", columns="component", values="component_contribution")
        c = c.loc[full.market_id]
        left = np.zeros(len(c))
        for i, comp in enumerate(COMPONENTS):
            if comp in c.columns:
                ax.barh(np.arange(len(c)), c[comp], left=left, color=PALETTE5[i], height=0.72,
                        edgecolor=dg.SURFACE, linewidth=1, label=SHORT[comp])
                left += c[comp].values
        ax.set_yticks(np.arange(len(c)), [short(n) for n in full.market_name], fontsize=7)
        ax.set_xlim(0, 100)
        ax.grid(axis="y", visible=False)
        ax.set_title(mode.replace("_", " ").title(), fontsize=10)
        ax.set_xlabel("Points contributed to the baseline score")
    axes[1].legend(frameon=False, fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.09))
    fig.suptitle("Component contributions to the baseline score (complete markets; equal component weights)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    made.append(dg._save(fig, FIG / "02_component_contributions.png"))

    seq = dg.LinearSegmentedColormap.from_list("blue_seq", ["#cde2fb", "#3987e5", "#104281"])
    fs = d["fs"]
    for i, mode in enumerate(MODES):
        f = fs[(fs["mode"] == mode)]
        order = f[["feature_id", "component"]].drop_duplicates().sort_values(["component", "feature_id"])
        piv = f.pivot(index="market_id", columns="feature_id", values="feature_score")[order.feature_id]
        names = rb[rb["mode"] == mode].set_index("market_id").sort_values("non_regulatory_score", ascending=False)
        piv = piv.loc[names.index]
        labels = [f"{fid} {f[f.feature_id == fid].feature_name.iloc[0][:26]}" for fid in piv.columns]
        fig, ax = plt.subplots(figsize=(0.5 * len(piv.columns) + 4, 9))
        im = ax.imshow(piv.values.astype(float), cmap=seq, vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(piv.columns)), labels, rotation=90, fontsize=7)
        ax.set_yticks(range(len(piv)), [short(n) for n in names.market_name], fontsize=7)
        ax.grid(False)
        cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cb.set_label("Feature score (0-100; blank = no score: C4 incomplete or not applicable)", color=dg.INK_2)
        ax.set_title(f"{mode.replace('_', ' ').title()}: feature scores (rows sorted by non-regulatory score)")
        made.append(dg._save(fig, FIG / f"03_feature_scores_{MODE_FILE[mode]}.png"))

    rd = d["rd"].copy()
    rd["col"] = rd["mode"].map({"ROBOTAXI": "RT", "SIDEWALK_DELIVERY": "SW", "DRONE_DELIVERY": "DR"}) + " " + \
        rd.legal_dimension.str.split("_", n=1).str[1].str.lower()
    piv = rd.pivot(index="market_id", columns="col", values="evidence_coverage_pct")
    names = d["dim_market"].set_index(d["dim_market"].market_id.astype(str)).cbsa_name
    piv = piv.loc[names.sort_values().index]
    fig, ax = plt.subplots(figsize=(8, 9.5))
    im = ax.imshow(piv.values, cmap=seq, vmin=0, vmax=100, aspect="auto")
    for (yi, xi), v in np.ndenumerate(piv.values):
        if v < 100 - TOL:
            ax.text(xi, yi, f"{v:.0f}", ha="center", va="center", fontsize=6.5, color=dg.INK)
    ax.set_xticks(range(len(piv.columns)), piv.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(piv)), [short(n) for n in names.loc[piv.index]], fontsize=7)
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Verified evidence coverage (% of market population); numbers mark incomplete cells", color=dg.INK_2)
    ax.set_title("Regulatory evidence coverage by market and dimension (base-model rule)")
    made.append(dg._save(fig, FIG / "04_regulatory_evidence_coverage.png"))

    cc = diag["component_correlation"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, mode in zip(axes, MODES):
        m = cc[cc["mode"] == mode].pivot(index="component_a", columns="component_b", values="spearman_rho")
        order = [c for c in COMPONENTS if c in m.index]
        m = m.loc[order, order]
        im = ax.imshow(m.values, cmap=dg.DIVERGING, vmin=-1, vmax=1)
        for (yi, xi), v in np.ndenumerate(m.values):
            ax.text(xi, yi, f"{v:.2f}", ha="center", va="center", fontsize=7, color=dg.INK)
        ax.set_xticks(range(len(order)), [SHORT[c] for c in order], rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(order)), [SHORT[c] for c in order], fontsize=7)
        ax.grid(False)
        ax.set_title(f"{mode.replace('_', ' ').title()} (n={int(cc[cc['mode'] == mode].n_markets.iloc[0])})", fontsize=10)
    fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02).set_label("Spearman rho (gray = none)", color=dg.INK_2)
    fig.suptitle("Component-score correlation among complete markets", x=0.01, ha="left", fontsize=11,
                 fontweight="bold")
    made.append(dg._save(fig, FIG / "05_component_correlation.png"))

    fig, axes = plt.subplots(3, 1, figsize=(9, 7.5), sharex=True)
    for ax, mode in zip(axes, MODES):
        x = rb[(rb["mode"] == mode) & rb.baseline_rank.notna()].sort_values(["baseline_rank", "market_id"])
        ax.bar(x.baseline_rank.iloc[1:], x.score_gap_to_preceding.iloc[1:], color=dg.SLOTS[0], width=0.7,
               edgecolor=dg.SURFACE, linewidth=1)
        ax.set_ylabel("Gap (points)")
        ax.set_title(f"{mode.replace('_', ' ').title()}: score gap to the preceding market", fontsize=10)
        ax.grid(axis="x", visible=False)
    axes[-1].set_xlabel("Baseline rank")
    fig.tight_layout()
    made.append(dg._save(fig, FIG / "06_rank_spacing.png"))
    return made


# ------------------------------------------------------------------------------------------- main
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = verify_frozen_inputs()
    wh = Warehouse()
    try:
        d = load(wh)
    finally:
        wh.close()
    for mode in MODES:
        check(f"{MARTS[mode]} has exactly 35 markets", len(d[mode]) == 35 and d[mode].market_id.nunique() == 35)

    feat = recompute_features(d)
    st, dim = recompute_regulatory(d)
    comp, mk = recompute_scores(feat, dim)
    reconcile(d, feat, st, dim, comp, mk)
    eligibility_and_mapping(d, st)
    nq = normalization_qa(d, feat)
    dep = [c for t in ("fs", "cs", "rd", "rb") for c in d[t].columns
           if any(w in c for w in ("deploy", "waymo", "zoox", "wing", "zipline", "serve", "operator"))]
    check("no deployment field in any score relation", not dep, ", ".join(dep))

    names = d["dim_market"].assign(market_id=d["dim_market"].market_id.astype(str))[["market_id", "cbsa_name"]] \
        .rename(columns={"cbsa_name": "market_name"})
    diag = diagnostics(d)

    # Exports ------------------------------------------------------------------------------------
    def save(df: pd.DataFrame, name: str, sort: list[str], float_format: str = "%.10g") -> None:
        df.sort_values(sort, kind="mergesort").to_csv(OUT / name, index=False, lineterminator="\n",
                                                      float_format=float_format)

    save(d["fs"].merge(names, on="market_id"), "feature_scores.csv", ["mode", "market_id", "component", "feature_id"])
    save(d["cs"].merge(names, on="market_id"), "component_scores.csv", ["mode", "market_id", "component"])
    for mode in MODES:
        mt = d[f"mart_{mode}"]
        # Ranked markets first (by baseline rank), then the C4-incomplete markets by name.
        mt = mt.iloc[np.lexsort((mt.market_name.values, mt.baseline_rank.fillna(999).values))]
        mt.to_csv(OUT / f"{MODE_FILE[mode]}_baseline.csv", index=False, lineterminator="\n", float_format="%.10g")
    cov = d["rd"].merge(names, on="market_id")
    save(cov, "regulatory_coverage.csv", ["mode", "market_id", "legal_dimension"])
    summ = d["rb"][["market_id", "market_name", "mode", "c4_complete_flag", "c4_evidence_coverage_pct",
                    "c4_max_unknown_share", "c4_unverified_states", "c4_incomplete_reason", "c4_score_verified",
                    "baseline_readiness_score", "baseline_rank", "non_regulatory_score", "c4_decomposition"]]
    save(summ, "regulatory_coverage_by_market.csv", ["mode", "market_id"])
    save(st.rename(columns={"share": "state_population_share", "cls": "base_evidence_class",
                            "reason": "not_favorable_reason"}), "regulatory_state_evidence_classes.csv",
         ["mode", "legal_dimension", "market_id", "state_usps"])
    save(nq, "normalization_qa.csv", ["mode", "component", "feature_id"])
    for k, v in diag.items():
        save(v, f"{k}.csv", list(v.columns[:3]),
             float_format=f"%.{CORR_OUTPUT_DECIMALS}f" if k == "component_correlation" else "%.10g")
    # The correlation figure is drawn from this same rounded, sorted table (diag["component_correlation"]).
    made = figures(d, diag)

    rb = d["rb"]
    meta = {
        "model_version": MODEL_VERSION,
        # Deterministic provenance only: this file describes the frozen model-input snapshot. The run time
        # and the repository HEAD are printed to the console, never written here (they change on every
        # new day or commit without any change to the model).
        "git_input_commit": INPUT_COMMIT,
        "regulatory_evidence_as_of": EVIDENCE_AS_OF,
        "deployment_evidence_as_of": EVIDENCE_AS_OF,
        "normalization_method": "Cross-sectional average-rank percentile across the 35 markets, 0-100: "
                                "score = 100 x (average_rank - 1) / (n - 1) on the transformed value; "
                                "LOWER_IS_MORE_FAVORABLE uses 100 - score",
        "tie_method": "Average rank (tied markets share the mean of the positions they occupy); baseline ranks use "
                      "standard competition ranking on scores rounded to 6 decimals",
        "feature_weight_method": "Equal within component: 1 / number of the component's inputs in the base calculation",
        "component_weight_method": "Equal across the mode's active components: robotaxi 1/4 (C1-C4), sidewalk and drone 1/5 (C1-C5)",
        "regulatory_scoring": "Categorical dimensions: 100 x verified favorable population share (PEP 2025, BRG_MARKET_STATE). "
                              "SW_MAX_WEIGHT: average-rank percentile of the most restrictive verified limit among the "
                              "market's PDD-authorizing states (NO_LIMIT_STATED ranked highest); not applicable where no "
                              "state authorizes PDDs. C4 = equal-weight mean of the applicable dimensions",
        "regulatory_eligibility_rule": "A state record enters the base model only if VERIFIED_PRIMARY with MEDIUM or HIGH "
                                       "confidence (Phase 6.5b rule, applied to every mode)",
        "missing_regulation_rule": "Any unknown or LOW-confidence population share in any C4 dimension makes C4 INCOMPLETE: "
                                   "C4, the baseline score and the baseline rank are NULL (no imputation, no 0, no 50). "
                                   "The non-regulatory score is published as a diagnostic",
        "scope_adjustments": pd.read_csv(SEEDS / "regulatory_scope_adjustments.csv", dtype=str)
                             [["evidence_id", "base_model_treatment", "assumption_id"]].to_dict("records"),
        "active_components": {m: sorted(d["cs"][d["cs"]["mode"] == m].component.unique()) for m in MODES},
        "active_features": {m: sorted(d["fs"][(d["fs"]["mode"] == m) & (d["fs"].component != C4)].feature_id.unique())
                            for m in MODES},
        "regulatory_dimensions": {m: sorted(d["rd"][d["rd"]["mode"] == m].legal_dimension.unique()) for m in MODES},
        "markets_with_full_baseline_score": {m: int(rb[(rb["mode"] == m)].baseline_readiness_score.notna().sum())
                                             for m in MODES},
        "checksums_sha256_lf": inputs,
        "dbt_objects": ["INTERMEDIATE.REGULATORY_STATE_EVIDENCE (seed)", "INTERMEDIATE.REGULATORY_FEATURE_CONTRACT (seed)",
                        "INTERMEDIATE.REGULATORY_SCOPE_ADJUSTMENTS (seed)",
                        "INTERMEDIATE.INT_REGULATORY__MARKET_STATE_EVIDENCE",
                        "ANALYTICS.FCT_REGULATORY_DIMENSION_SCORES", "ANALYTICS.FCT_FEATURE_SCORES",
                        "ANALYTICS.FCT_COMPONENT_SCORES", "ANALYTICS.FCT_READINESS_BASELINE",
                        "ANALYTICS.MART_ROBOTAXI_READINESS_BASELINE",
                        "ANALYTICS.MART_SIDEWALK_DELIVERY_READINESS_BASELINE",
                        "ANALYTICS.MART_DRONE_DELIVERY_READINESS_BASELINE"],
        "cross_mode_rule": "Readiness scores are mode-specific; no combined or cross-mode score exists",
        "deployment_evidence_used": False,
        "sensitivity_simulation_performed": False,
        "figures": made,
        "qa_checks_passed": sum(c["status"] == "PASS" for c in CHECKS),
        "qa_checks_failed": sum(c["status"] == "FAIL" for c in CHECKS),
    }
    # Export/reporting floor only: a residue below 1e-12 is floating-point summation noise (Snowflake's
    # summation order varies between builds) and is written as exactly 0.0. PASS/FAIL was already decided
    # in check()/compare() on the unfloored difference against TOL (1e-6), so the test is not weakened.
    report = pd.DataFrame(CHECKS)
    report["max_abs_diff"] = [(0.0 if abs(v) < EXPORT_DIFF_FLOOR else v) if v is not None and not pd.isna(v) else v
                              for v in report.max_abs_diff]
    report.to_csv(OUT / "score_reconciliation.csv", index=False, lineterminator="\n", float_format="%.3g")
    (OUT / "model_metadata.json").write_text(json.dumps(meta, indent=2, default=str) + "\n", encoding="utf-8")
    failed = meta["qa_checks_failed"]
    print(f"\n{meta['qa_checks_passed']} checks passed, {failed} failed. Outputs in {OUT.relative_to(ROOT)}")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f"run (not recorded in model_metadata.json): {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} | "
          f"repository HEAD {head} | model input commit {INPUT_COMMIT}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
