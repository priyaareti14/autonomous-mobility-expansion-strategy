"""Phase 5 feature-audit statistics: inventory, missingness, variation, distribution,
outliers, correlation and market-size duplication.

Nothing here scores, weights or ranks markets. Outputs describe the candidate
measures so Phase 6 can decide how to engineer them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .feature_catalog import INTENSITY_CANDIDATES, MART_CANDIDATES, Candidate

# Thresholds are audit heuristics, not decision rules. Each flag is reviewed
# with its context before any KEEP/MODIFY/DEFER/DROP decision.
MISSING_UNACCEPTABLE = 0.20      # > 20% of markets missing
NEAR_ZERO_CV = 0.05              # coefficient of variation < 5%
SKEW_HIGH = 1.0
REDUNDANCY_R = 0.80
SIZE_DUP_RHO = 0.90
MAD_Z = 3.5


def load_mart(wh) -> pd.DataFrame:
    df = wh.table("ANALYTICS", "MART_MARKET_FEATURE_BASE").set_index("market_id").sort_index()
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c])
            except (ValueError, TypeError):
                pass
    return df


def add_intensity(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in INTENSITY_CANDIDATES:
        num, den, mult = c.formula
        out[c.column] = out[num].astype(float) / out[den].astype(float) * mult
    return out


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
def _stats(s: pd.Series) -> dict:
    v = pd.to_numeric(s, errors="coerce").astype(float)
    nn = v.dropna()
    mean = nn.mean() if len(nn) else np.nan
    sd = nn.std(ddof=1) if len(nn) > 1 else np.nan
    return {
        "n": int(len(v)),
        "missing_count": int(v.isna().sum()),
        "missing_pct": round(float(v.isna().mean()) * 100, 1),
        "unique_values": int(nn.nunique()),
        "min": nn.min() if len(nn) else np.nan,
        "p05": nn.quantile(0.05) if len(nn) else np.nan,
        "p25": nn.quantile(0.25) if len(nn) else np.nan,
        "median": nn.median() if len(nn) else np.nan,
        "mean": mean,
        "p75": nn.quantile(0.75) if len(nn) else np.nan,
        "p95": nn.quantile(0.95) if len(nn) else np.nan,
        "max": nn.max() if len(nn) else np.nan,
        "std": sd,
        "cv": (sd / mean) if mean not in (0, np.nan) and pd.notna(mean) and mean != 0 else np.nan,
        "skewness": float(nn.skew()) if len(nn) > 2 else np.nan,
        "zero_count": int((nn == 0).sum()),
        "negative_count": int((nn < 0).sum()),
        "max_to_median": (nn.max() / nn.median()) if len(nn) and nn.median() not in (0,) else np.nan,
    }


def all_candidates() -> list[Candidate]:
    return MART_CANDIDATES + INTENSITY_CANDIDATES


def inventory(df: pd.DataFrame, extra: list[Candidate] | None = None) -> pd.DataFrame:
    rows = []
    for c in all_candidates() + (extra or []):
        if c.column not in df.columns:
            continue
        rows.append({
            "feature_id": c.feature_id, "feature_name": c.column, "meaning": c.meaning,
            "source": c.source, "vintage": c.vintage, "component": c.component,
            "modes": ",".join(c.modes), "unit": c.unit, "kind": c.kind, "scale_type": c.scale_type,
            "origin": c.origin, "expected_direction": c.direction, "source_limitation": c.limitation,
            **_stats(df[c.column]),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Missingness
# ---------------------------------------------------------------------------
def missingness(df: pd.DataFrame, inv: pd.DataFrame, causes: dict[str, str]) -> pd.DataFrame:
    """One row per feature with any missing value; cause class from `causes` (else UNRESOLVED)."""
    rows = []
    for _, r in inv.iterrows():
        col = r["feature_name"]
        miss = df.index[df[col].isna()].tolist()
        rows.append({
            "feature_name": col, "missing_count": len(miss), "missing_pct": r["missing_pct"],
            "markets_affected": ";".join(miss),
            "cause_class": "NONE" if not miss else causes.get(col, "UNRESOLVED"),
            "unacceptable": r["missing_pct"] / 100 > MISSING_UNACCEPTABLE,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Variation, distribution and transformation hints
# ---------------------------------------------------------------------------
def variation_flags(inv: pd.DataFrame) -> pd.DataFrame:
    out = inv[["feature_name", "unique_values", "cv"]].copy()
    out["zero_variance"] = out["unique_values"] <= 1
    out["near_zero_variance"] = out["cv"].abs() < NEAR_ZERO_CV
    out["low_unique"] = out["unique_values"] < 5
    return out


def transformation_hint(r: pd.Series) -> str:
    """Audit suggestion only. The final transformation is a Phase 6 decision."""
    if r["scale_type"] == "STRUCTURAL":
        return "NONE (structural/denominator)"
    hints = []
    if r["scale_type"] == "ABSOLUTE":
        hints.append("PER_CAPITA or keep as explicit SCALE")
    if pd.notna(r["skewness"]) and r["skewness"] > SKEW_HIGH and r["min"] >= 0:
        hints.append("LOG1P")
    if pd.notna(r["max_to_median"]) and r["max_to_median"] > 5:
        hints.append("ROBUST_SCALE_LATER or PERCENTILE_LATER")
    if r["expected_direction"] == "UNRESOLVED":
        hints.append("DIRECTION UNRESOLVED")
    return "; ".join(hints) if hints else "NONE"


# ---------------------------------------------------------------------------
# Outliers (IQR + robust z / MAD)
# ---------------------------------------------------------------------------
def outliers(df: pd.DataFrame, cols: list[str], names: pd.Series) -> pd.DataFrame:
    rows = []
    for col in cols:
        v = pd.to_numeric(df[col], errors="coerce").astype(float)
        nn = v.dropna()
        if nn.nunique() < 3:
            continue
        q1, q3 = nn.quantile([0.25, 0.75])
        iqr = q3 - q1
        med = nn.median()
        mad = (nn - med).abs().median()
        for m, x in nn.items():
            iqr_flag = iqr > 0 and (x < q1 - 3 * iqr or x > q3 + 3 * iqr)
            rz = 0.6745 * (x - med) / mad if mad > 0 else 0.0
            if iqr_flag or abs(rz) > MAD_Z:
                rows.append({"feature_name": col, "market_id": m, "cbsa_name": names.get(m),
                             "value": x, "median": med, "robust_z": round(rz, 2),
                             "beyond_3iqr": bool(iqr_flag)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Correlation, redundancy and size duplication
# ---------------------------------------------------------------------------
def correlations(df: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = df[cols].apply(pd.to_numeric, errors="coerce").astype(float)
    return x.corr(method="pearson"), x.corr(method="spearman")


def strong_pairs(pear: pd.DataFrame, spear: pd.DataFrame, threshold: float = REDUNDANCY_R) -> pd.DataFrame:
    cols = list(pear.columns)
    rows = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            p, s = pear.loc[a, b], spear.loc[a, b]
            if (pd.notna(p) and abs(p) >= threshold) or (pd.notna(s) and abs(s) >= threshold):
                rows.append({"feature_a": a, "feature_b": b, "pearson": round(p, 3), "spearman": round(s, 3)})
    return pd.DataFrame(rows).sort_values("spearman", key=lambda s: -s.abs()) if rows else pd.DataFrame()


def redundancy_components(spear: pd.DataFrame, threshold: float = REDUNDANCY_R) -> list[list[str]]:
    """Connected components of the |rho| >= threshold graph: empirical redundancy clusters."""
    cols = list(spear.columns)
    adj = {c: {d for d in cols if d != c and pd.notna(spear.loc[c, d]) and abs(spear.loc[c, d]) >= threshold}
           for c in cols}
    seen, comps = set(), []
    for c in cols:
        if c in seen:
            continue
        stack, comp = [c], []
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            comp.append(n)
            stack.extend(adj[n] - seen)
        if len(comp) > 1:
            comps.append(sorted(comp))
    return comps


def size_duplication(df: pd.DataFrame, cols: list[str], size_col: str = "population_2025") -> pd.DataFrame:
    size = df[size_col].astype(float)
    rows = []
    for col in cols:
        if col == size_col:
            continue
        v = pd.to_numeric(df[col], errors="coerce").astype(float)
        ok = v.notna()
        if ok.sum() < 5:
            continue
        rho = v[ok].rank().corr(size[ok].rank())      # Spearman = Pearson on ranks (no scipy needed)
        r_log = np.log(v[ok].clip(lower=1e-9)).corr(np.log(size[ok])) if (v[ok] > 0).all() else np.nan
        rows.append({"feature_name": col, "spearman_vs_population": round(rho, 3),
                     "pearson_log_vs_log_population": round(r_log, 3) if pd.notna(r_log) else np.nan,
                     "duplicates_market_size": abs(rho) >= SIZE_DUP_RHO})
    return pd.DataFrame(rows)


def moe_quality(df: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """ACS reliability: coefficient of variation = (MOE/1.645)/estimate."""
    rows = []
    for est, moe in pairs:
        cv = (df[moe] / 1.645) / df[est]
        rows.append({"feature_name": est, "cv_median": round(cv.median(), 4), "cv_max": round(cv.max(), 4),
                     "markets_cv_over_15pct": int((cv > 0.15).sum()),
                     "worst_market": cv.idxmax() if cv.notna().any() else None})
    return pd.DataFrame(rows)
