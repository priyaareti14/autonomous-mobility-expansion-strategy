"""Phase 8 external reasonableness check against the committed deployment evidence (Steps 20-25).

Runs ONLY after run_phase8_sensitivity.py has frozen the robustness results:
  1. verifies every sensitivity output against the SHA-256 manifest in outputs/phase8/model_metadata.json
     (proof that nothing below can feed back into the model or the sensitivity results);
  2. reads evidence/deployment_evidence.csv (committed Phase 6.5 dataset, evidence date 2026-10-05; never
     refreshed) and builds explicit status and geography cohorts;
  3. compares model results with deployment presence DESCRIPTIVELY. This is not accuracy: deployment presence
     is not ground truth, and no recorded deployment is not evidence that a market is unsuitable;
  4. lists mismatches with candidate (unverified) explanations, and re-verifies the manifest at the end.
Nothing here changes a weight, feature, score or rank.

Usage (repository root, .venv active, after run_phase8_sensitivity.py):
    python scripts/run_phase8_deployment_validation.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.analytics import diagnostics as dg  # noqa: E402

OUT = ROOT / "outputs" / "phase8"
EVIDENCE = ROOT / "evidence" / "deployment_evidence.csv"
EVIDENCE_AS_OF = "2026-10-05"
MODES = ["ROBOTAXI", "SIDEWALK_DELIVERY", "DRONE_DELIVERY"]
CURRENT = ["COMMERCIAL", "LIMITED_COMMERCIAL"]
OTHER_STATUSES = ["PILOT", "TESTING", "ANNOUNCED", "PAUSED", "ENDED", "UNKNOWN"]
# Market-resolution tiers. The dataset has no "whole market" category: every in-universe record covers part of
# a CBSA, so presence always means "some service in the market", never "the market is served".
RESOLVED_SINGLE = ["WITHIN_MARKET_PARTIAL", "CITY_ONLY"]          # primary validation tier
RESOLVED_BROAD = RESOLVED_SINGLE + ["CAMPUS_OR_SITE", "MULTI_MARKET"]
HIGH_TOP10 = 0.50     # high model position: top 10 in at least half of the weight draws
LOW_TOP10 = 0.10      # low model position: top 10 in at most 10% of the weight draws
OUT_DEC = 6
CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))
    return bool(ok)


def verify_manifest() -> dict:
    meta = json.loads((OUT / "model_metadata.json").read_text(encoding="utf-8"))
    man = meta["sensitivity_output_manifest_sha256"]
    bad = [p for p, h in man.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    return {"files": len(man), "mismatched": bad,
            "manifest_sha256": hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest()}


def export(df: pd.DataFrame, name: str, sort: list[str]) -> None:
    df = df.sort_values(sort, kind="mergesort").copy()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].round(OUT_DEC) + 0.0
    df.to_csv(OUT / name, index=False, lineterminator="\n", float_format=f"%.{OUT_DEC}f")


def main() -> int:
    print("Freeze check before reading deployment evidence")
    before = verify_manifest()
    check(f"all {before['files']} sensitivity outputs match their frozen checksums", not before["mismatched"],
          ", ".join(before["mismatched"]))
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(EVIDENCE.relative_to(ROOT))], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    check("deployment evidence is the committed Phase 6.5 file (no local edits)", dirty == "")

    rs = pd.read_csv(OUT / "robustness_summary.csv", dtype={"market_id": str})
    reg = pd.read_csv(OUT / "regulatory_uncertainty.csv", dtype={"market_id": str})
    dep = pd.read_csv(EVIDENCE, dtype=str, keep_default_na=False)
    check("deployment evidence date is 2026-10-05 for every record", set(dep.evidence_as_of) == {EVIDENCE_AS_OF})
    universe = set(rs.market_id)

    dep["current"] = dep.deployment_status.isin(CURRENT) & (dep.end_date == "")
    dep["in_universe"] = dep.market_id.isin(universe)
    rows = []
    for mode in MODES:
        dm = dep[(dep["mode"] == mode) & dep.in_universe]
        for mid in sorted(universe):
            x = dm[dm.market_id == mid]
            cur = x[x.current]
            row = {"mode": mode, "market_id": mid,
                   "current_commercial_primary": bool(cur.market_resolution.isin(RESOLVED_SINGLE).any()),
                   "current_commercial_primary_verified": bool((cur.market_resolution.isin(RESOLVED_SINGLE)
                                                                & (cur.verification_status == "VERIFIED_PRIMARY")).any()),
                   "current_commercial_broad": bool(cur.market_resolution.isin(RESOLVED_BROAD).any()),
                   "current_operators": ";".join(sorted(set(cur.operator))),
                   "current_resolutions": ";".join(sorted(set(cur.market_resolution)))}
            for s in OTHER_STATUSES:
                row[f"{s.lower()}_present"] = bool((x.deployment_status == s).any())
            row["ended_or_paused_only"] = bool(len(x) and not row["current_commercial_broad"]
                                               and x.deployment_status.isin(["ENDED", "PAUSED"]).all())
            row["deployment_cohort"] = ("CURRENT_COMMERCIAL" if row["current_commercial_broad"] else
                                        "PILOT_TESTING_OR_ANNOUNCED" if (row["pilot_present"] or row["testing_present"]
                                                                         or row["announced_present"]) else
                                        "ENDED_OR_PAUSED_ONLY" if row["ended_or_paused_only"] else
                                        "OTHER_RECORD_ONLY" if len(x) else "NO_RECORDED_DEPLOYMENT")
            rows.append(row)
    pres = pd.DataFrame(rows)
    keep = ["mode", "market_id", "market_name", "baseline_rank", "baseline_score", "score_complete_flag", "mean_rank",
            "median_rank", "top_5_frequency", "top_10_frequency", "rank_p05", "rank_p95", "regulatory_best_rank",
            "regulatory_worst_rank", "pattern_flags"]
    val = rs[keep].merge(pres, on=["mode", "market_id"], how="left")
    rneu = reg[["mode", "market_id", "neutral_rank"]].rename(columns={"neutral_rank": "regulatory_neutral_rank"})
    val = val.merge(rneu, on=["mode", "market_id"], how="left")
    check("every market x mode has one validation row", len(val) == 105 and not val.duplicated(["mode", "market_id"]).any())

    # Cohort counts (records and markets)
    coh = []
    for mode in MODES:
        dm = dep[dep["mode"] == mode]
        for status in CURRENT + OTHER_STATUSES:
            for res in sorted(dep.market_resolution.unique()):
                x = dm[(dm.deployment_status == status) & (dm.market_resolution == res)]
                if len(x):
                    coh.append({"mode": mode, "deployment_status": status, "market_resolution": res,
                                "open_ended_records": int((x.end_date == "").sum()), "records": len(x),
                                "in_universe_markets": int(x[x.in_universe].market_id.nunique())})
    coh = pd.DataFrame(coh)

    # Descriptive comparison per mode and cohort definition (markets, not rows)
    summ = []
    for mode in MODES:
        v = val[val["mode"] == mode]
        ranked = v[v.baseline_rank.notna()]
        n_ranked = len(ranked)
        top5 = set(ranked[ranked.baseline_rank <= 5].market_id)
        top10 = set(ranked[ranked.baseline_rank <= 10].market_id)
        for cohort in ["current_commercial_primary", "current_commercial_primary_verified", "current_commercial_broad"]:
            d_all = v[v[cohort]]
            d = ranked[ranked[cohort]]
            nd = ranked[~ranked[cohort]]
            summ.append({
                "mode": mode, "cohort": cohort, "deployment_markets": len(d_all),
                "deployment_markets_ranked": len(d), "deployment_markets_unscored_c4_incomplete": len(d_all) - len(d),
                "ranked_markets": n_ranked,
                "median_baseline_rank_deployment": d.baseline_rank.median(),
                "median_baseline_rank_no_recorded_deployment": nd.baseline_rank.median(),
                "median_mean_rank_deployment": d.mean_rank.median(),
                "median_mean_rank_no_recorded_deployment": nd.mean_rank.median(),
                "median_top10_frequency_deployment": d.top_10_frequency.median(),
                "median_top10_frequency_no_recorded_deployment": nd.top_10_frequency.median(),
                "share_of_deployment_markets_in_baseline_top5": len(set(d.market_id) & top5) / len(d) if len(d) else np.nan,
                "share_of_deployment_markets_in_baseline_top10": len(set(d.market_id) & top10) / len(d) if len(d) else np.nan,
                "baseline_top5_with_deployment": len(set(d.market_id) & top5),
                "baseline_top10_with_deployment": len(set(d.market_id) & top10),
                "share_of_ranked_markets_with_deployment": len(d) / n_ranked if n_ranked else np.nan,
            })
    summ = pd.DataFrame(summ)
    # Model position by deployment cohort (all markets; incomplete C4 markets use the regulatory neutral rank only)
    by_status = (val.groupby(["mode", "deployment_cohort"])
                 .agg(markets=("market_id", "count"), ranked_markets=("baseline_rank", "count"),
                      median_baseline_rank=("baseline_rank", "median"), median_mean_rank=("mean_rank", "median"),
                      median_top10_frequency=("top_10_frequency", "median"),
                      median_regulatory_neutral_rank=("regulatory_neutral_rank", "median"))
                 .reset_index())

    # Mismatch review (Step 24): candidate explanations are prompts for review, not findings.
    comp = {}
    for mode, short in [("ROBOTAXI", "robotaxi"), ("SIDEWALK_DELIVERY", "sidewalk"), ("DRONE_DELIVERY", "drone")]:
        b = pd.read_csv(ROOT / "outputs" / "phase7" / f"{short}_baseline.csv", dtype={"market_id": str})
        comp[mode] = b.set_index("market_id")
    mm = []
    for r in val.itertuples():
        deployed = bool(r.current_commercial_broad)
        if r.score_complete_flag and r.top_10_frequency >= HIGH_TOP10:
            cat = "HIGH_MODEL_DEPLOYMENT_PRESENT" if deployed else "HIGH_MODEL_NO_RECORDED_DEPLOYMENT"
        elif r.score_complete_flag and r.top_10_frequency <= LOW_TOP10 and deployed:
            cat = "LOW_MODEL_DEPLOYMENT_PRESENT"
        elif not r.score_complete_flag and deployed:
            cat = "UNSCORED_C4_INCOMPLETE_DEPLOYMENT_PRESENT"
        else:
            continue
        b = comp[r.mode].loc[r.market_id]
        scores = {c: b[c] for c in b.index if c.startswith("c") and c.endswith("_score") and pd.notna(b[c])}
        weakest = min(scores, key=scores.get) if scores else ""
        hints = []
        if cat == "HIGH_MODEL_NO_RECORDED_DEPLOYMENT":
            if r.testing_present or r.pilot_present or r.announced_present:
                hints.append("TESTING_PILOT_OR_ANNOUNCED_ACTIVITY_RECORDED")
            if r.ended_present or r.paused_present:
                hints.append("PAST_SERVICE_ENDED_OR_PAUSED")
            hints.append("OPERATOR_FOOTPRINT_OR_SEQUENCING (not observable in public data)")
        else:
            if deployed and set(str(r.current_resolutions).split(";")) <= set(RESOLVED_BROAD) - {"MULTI_MARKET"}:
                hints.append("SERVICE_GEOGRAPHY_NARROWER_THAN_MSA")
            if deployed and len(str(r.current_operators).split(";")) == 1:
                hints.append("SINGLE_OPERATOR_PRESENCE")
            if cat == "LOW_MODEL_DEPLOYMENT_PRESENT":
                hints.append(f"WEAKEST_COMPONENT_{weakest.replace('_score', '').upper()}")
                if pd.notna(b.get("c4_regulatory_score")) and b.get("c4_regulatory_score") < 50:
                    hints.append("REGULATION_NOT_CAPTURED_BY_STATE_VARIABLES_POSSIBLE")
                hints.append("BUSINESS_STRATEGY_PARTNERSHIP_OR_CAPITAL (not observable in public data)")
            if cat == "UNSCORED_C4_INCOMPLETE_DEPLOYMENT_PRESENT":
                hints.append("STATE_EVIDENCE_UNRESOLVED (see regulatory_uncertainty.csv)")
        mm.append({"mode": r.mode, "market_id": r.market_id, "market_name": r.market_name, "category": cat,
                   "baseline_rank": r.baseline_rank, "mean_rank": r.mean_rank, "top_10_frequency": r.top_10_frequency,
                   "regulatory_neutral_rank": r.regulatory_neutral_rank, "current_operators": r.current_operators,
                   "current_resolutions": r.current_resolutions, "weakest_component": weakest.replace("_score", ""),
                   "candidate_explanations": "; ".join(hints)})
    mm = pd.DataFrame(mm)

    export(val, "deployment_validation.csv", ["mode", "market_id"])
    export(summ, "deployment_validation_summary.csv", ["mode", "cohort"])
    export(by_status, "deployment_validation_by_cohort.csv", ["mode", "deployment_cohort"])
    export(coh, "deployment_cohorts.csv", ["mode", "deployment_status", "market_resolution"])
    export(mm, "deployment_mismatch_review.csv", ["mode", "category", "market_id"])
    figure(val)

    print("Freeze check after the comparison")
    after = verify_manifest()
    check("sensitivity outputs unchanged after the deployment comparison", not after["mismatched"]
          and after["manifest_sha256"] == before["manifest_sha256"])
    export(pd.DataFrame(CHECKS), "deployment_qa_checks.csv", ["check"])
    man = {"deployment_evidence_file": "evidence/deployment_evidence.csv",
           "deployment_evidence_sha256_lf": hashlib.sha256(EVIDENCE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
           "deployment_evidence_as_of": EVIDENCE_AS_OF, "verified_sensitivity_manifest_sha256": before["manifest_sha256"],
           "primary_cohort": {"statuses": CURRENT, "end_date": "blank (open-ended)", "market_resolution": RESOLVED_SINGLE},
           "broad_cohort_market_resolution": RESOLVED_BROAD,
           "mismatch_thresholds": {"high_model": f"top-10 frequency >= {HIGH_TOP10}", "low_model": f"top-10 frequency <= {LOW_TOP10}"},
           "interpretation": "External reasonableness check only; not accuracy; deployment presence is not ground truth",
           "qa_checks_passed": sum(c["status"] == "PASS" for c in CHECKS),
           "qa_checks_failed": sum(c["status"] == "FAIL" for c in CHECKS)}
    (OUT / "deployment_validation_manifest.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print(f"\n{man['qa_checks_passed']} checks passed, {man['qa_checks_failed']} failed.")
    return 1 if man["qa_checks_failed"] else 0


def figure(val: pd.DataFrame) -> None:
    plt = dg.plt
    order = ["CURRENT_COMMERCIAL", "PILOT_TESTING_OR_ANNOUNCED", "ENDED_OR_PAUSED_ONLY", "OTHER_RECORD_ONLY",
             "NO_RECORDED_DEPLOYMENT"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
    for ax, mode in zip(axes, MODES):
        v = val[(val["mode"] == mode) & val.mean_rank.notna()]
        for i, c in enumerate(order):
            x = v[v.deployment_cohort == c].mean_rank
            jitter = (np.arange(len(x)) % 5 - 2) * 0.06
            ax.scatter(x, np.full(len(x), i) + jitter, s=24, color=dg.SLOTS[0] if c == "CURRENT_COMMERCIAL" else dg.MUTED,
                       edgecolor=dg.SURFACE, linewidth=1, zorder=3)
            if len(x):
                ax.text(x.median(), i + 0.32, "median", fontsize=6, color=dg.INK_2, ha="center")
                ax.plot([x.median()] * 2, [i - 0.25, i + 0.25], color=dg.INK_2, linewidth=1.5)
        ax.set_yticks(range(len(order)), [o.replace("_", " ").lower() for o in order], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("Mean rank across 10,000 weight draws (complete markets)")
        ax.set_title(mode.replace("_", " ").title(), fontsize=10)
        ax.grid(axis="y", visible=False)
    fig.suptitle("Model position by deployment cohort (evidence as of 2026-10-05): a reasonableness check, not accuracy",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    dg._save(fig, OUT / "figures" / "07_deployment_validation.png")


if __name__ == "__main__":
    sys.exit(main())
