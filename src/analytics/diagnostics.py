"""Phase 5 diagnostic charts and the clustering-feasibility check.

Charts are static analysis artifacts (PNG); each one has a CSV "table twin" in
outputs/. Colors come from the dataviz reference palette: slot 1 blue for single
series, the first three slots (documented as validated all-pairs) for at most
three series, and the blue<->red diverging pair with a gray midpoint for
correlation. Node is not installed here, so the validator script was not re-run
and the palette's documented validation is relied on instead.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a"]          # blue, orange, aqua (first three: validated all-pairs)
DIVERGING = LinearSegmentedColormap.from_list(
    "blue_gray_red", ["#104281", "#3987e5", "#f0efec", "#e66767", "#a8201f"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "grid.linestyle": "-", "axes.spines.top": False, "axes.spines.right": False,
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 9,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})


def _save(fig, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path.name


def missingness_chart(miss: pd.DataFrame, path: Path) -> str:
    d = miss[miss["missing_count"] > 0].sort_values("missing_pct")
    fig, ax = plt.subplots(figsize=(7, max(1.6, 0.42 * len(d) + 1)))
    ax.barh(d["feature_name"], d["missing_pct"], color=SLOTS[0], height=0.55)
    for y, (v, n) in enumerate(zip(d["missing_pct"], d["missing_count"])):
        ax.text(v + 1, y, f"{v:.0f}% ({n} of 35)", va="center", color=INK_2, fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of the 35 markets missing")
    ax.set_title("Candidate measures with missing values")
    ax.grid(axis="y", visible=False)
    return _save(fig, path)


def correlation_heatmap(corr: pd.DataFrame, path: Path, title: str) -> str:
    n = len(corr)
    fig, ax = plt.subplots(figsize=(0.32 * n + 3, 0.32 * n + 2))
    im = ax.imshow(corr.values, cmap=DIVERGING, vmin=-1, vmax=1)
    ax.set_xticks(range(n), corr.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(n), corr.index, fontsize=7)
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Spearman rho (-1 to +1; gray = no association)", color=INK_2)
    ax.set_title(title)
    return _save(fig, path)


def distributions(df: pd.DataFrame, cols: list[str], path: Path) -> str:
    k = len(cols)
    ncol = 5
    nrow = int(np.ceil(k / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(13, 2.1 * nrow))
    for ax, c in zip(np.ravel(axes), cols):
        v = pd.to_numeric(df[c], errors="coerce").dropna()
        ax.hist(v, bins=12, color=SLOTS[0], edgecolor=SURFACE, linewidth=1)
        ax.set_title(c, fontsize=7.5, fontweight="normal")
        ax.tick_params(labelsize=6.5)
        ax.text(0.98, 0.92, f"skew {v.skew():.1f}", transform=ax.transAxes, ha="right", fontsize=7, color=INK_2)
    for ax in np.ravel(axes)[k:]:
        ax.set_visible(False)
    fig.suptitle("Distributions across the 35 markets (counts of markets per bin)", x=0.01, ha="left",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save(fig, path)


def scatter_pair(x, y, names, path: Path, title: str, xlabel: str, ylabel: str,
                 logx=False, logy=False, diagonal=False, label_extremes: int = 4) -> str:
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    ax.scatter(x, y, s=34, color=SLOTS[0], edgecolor=SURFACE, linewidth=1.5, zorder=3)
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    if diagonal:
        lo, hi = np.nanmin([np.nanmin(x), np.nanmin(y)]), np.nanmax([np.nanmax(x), np.nanmax(y)])
        ax.plot([lo, hi], [lo, hi], color=AXIS, linewidth=1, zorder=1)
        ax.text(hi, hi, " y = x", color=MUTED, fontsize=7, va="bottom")
    # Selective direct labels: the most extreme points by residual distance from the median
    s = pd.DataFrame({"x": x, "y": y, "n": names}).dropna()
    if len(s) and label_extremes:
        zx = (np.log(s["x"]) if logx else s["x"])
        zy = (np.log(s["y"]) if logy else s["y"])
        dist = ((zx - zx.median()) / (zx.std() or 1)) ** 2 + ((zy - zy.median()) / (zy.std() or 1)) ** 2
        # Alternate label offsets (above / below) in x order so neighbouring labels don't collide.
        chosen = s.loc[dist.nlargest(label_extremes).index].sort_values("x")
        for i, (_, r) in enumerate(chosen.iterrows()):
            ax.annotate(str(r["n"]).split(",")[0].split("-")[0], (r["x"], r["y"]),
                        xytext=(5, 5) if i % 2 == 0 else (5, -11),
                        textcoords="offset points", fontsize=7, color=INK_2)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return _save(fig, path)


def dot_comparison(df: pd.DataFrame, cols: list[str], labels: list[str], path: Path, title: str,
                   xlabel: str) -> str:
    d = df.sort_values(cols[0])
    fig, ax = plt.subplots(figsize=(7, 0.24 * len(d) + 1.4))
    y = np.arange(len(d))
    for i, (c, lab) in enumerate(zip(cols, labels)):
        ax.scatter(d[c], y, s=28, color=SLOTS[i], edgecolor=SURFACE, linewidth=1.2, label=lab, zorder=3 + i)
    ax.set_yticks(y, [n.split(",")[0][:28] for n in d["cbsa_name"]], fontsize=7)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.grid(axis="y", visible=False)
    return _save(fig, path)


def scree(ev: np.ndarray, path: Path) -> str:
    fig, ax = plt.subplots(figsize=(6, 3.4))
    k = np.arange(1, len(ev) + 1)
    ax.bar(k, ev * 100, color=SLOTS[0], width=0.6)
    ax.plot(k, np.cumsum(ev) * 100, color=INK_2, linewidth=2, marker="o", markersize=4)
    ax.set_xlabel("Principal component")
    ax.set_ylabel("% of variance (bars) / cumulative % (line)")
    ax.set_title("PCA of standardized intensity candidates (clustering feasibility)")
    ax.set_ylim(0, 105)
    return _save(fig, path)


# ---------------------------------------------------------------------------
# Clustering feasibility (diagnostic only: no final clusters, no labels)
# ---------------------------------------------------------------------------
def _standardize(x: pd.DataFrame) -> np.ndarray:
    z = (x - x.median()) / (x.quantile(0.75) - x.quantile(0.25)).replace(0, 1)   # robust scaling
    return z.values


def _kmeans(X, k, seeds=50, iters=100, rng=None):
    rng = rng or np.random.default_rng(0)
    best = None
    for _ in range(seeds):
        c = X[rng.choice(len(X), k, replace=False)]
        for _ in range(iters):
            lab = np.argmin(((X[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
            new = np.array([X[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
            if np.allclose(new, c):
                break
            c = new
        inertia = ((X - c[lab]) ** 2).sum()
        if best is None or inertia < best[0]:
            best = (inertia, lab)
    return best


def _silhouette(X, lab):
    D = np.sqrt(((X[:, None, :] - X[None]) ** 2).sum(-1))
    s = []
    for i in range(len(X)):
        same = lab == lab[i]
        a = D[i, same & (np.arange(len(X)) != i)].mean() if same.sum() > 1 else 0
        b = min(D[i, lab == j].mean() for j in set(lab) if j != lab[i])
        s.append((b - a) / max(a, b) if max(a, b) > 0 else 0)
    return float(np.mean(s))


def _hopkins(X, m=None, rng=None):
    """Hopkins statistic: ~0.5 for random uniform data, toward 1 for clustered data."""
    rng = rng or np.random.default_rng(1)
    n, d = X.shape
    m = m or max(5, n // 4)
    lo, hi = X.min(0), X.max(0)
    idx = rng.choice(n, m, replace=False)
    U = rng.uniform(lo, hi, size=(m, d))
    def nn(p, pool, exclude=None):
        dd = np.sqrt(((pool - p) ** 2).sum(1))
        if exclude is not None:
            dd[exclude] = np.inf
        return dd.min()
    u = sum(nn(U[i], X) for i in range(m))
    w = sum(nn(X[i], X, exclude=i) for i in idx)
    return float(u / (u + w))


def clustering_feasibility(x: pd.DataFrame, ks=range(2, 7)) -> dict:
    X = _standardize(x.dropna())
    n, d = X.shape
    Xc = X - X.mean(0)
    sv = np.linalg.svd(Xc, compute_uv=False)
    ev = sv ** 2 / (sv ** 2).sum()
    res = {"n_markets": n, "n_features": d, "pca_explained": ev,
           "pcs_for_80pct": int(np.searchsorted(np.cumsum(ev), 0.80) + 1),
           "hopkins": [_hopkins(X, rng=np.random.default_rng(s)) for s in range(10)]}
    sil, sizes, stability = {}, {}, {}
    for k in ks:
        inertia, lab = _kmeans(X, k)
        sil[k] = _silhouette(X, lab)
        sizes[k] = sorted(np.bincount(lab).tolist(), reverse=True)
        # stability: agreement of co-membership across bootstrap resamples (adjusted for chance poorly; diagnostic)
        agree = []
        rng = np.random.default_rng(k)
        base = lab[:, None] == lab[None]
        for _ in range(20):
            b = rng.choice(n, n, replace=True)
            _, lb = _kmeans(X[b], k, seeds=10, rng=rng)
            uniq = np.unique(b)
            pos = {v: np.where(b == v)[0][0] for v in uniq}
            lbu = np.array([lb[pos[v]] for v in uniq])
            co_b = lbu[:, None] == lbu[None]
            agree.append((co_b == base[np.ix_(uniq, uniq)]).mean())
        stability[k] = float(np.mean(agree))
    res.update(silhouette=sil, cluster_sizes=sizes, co_membership_stability=stability)
    return res
