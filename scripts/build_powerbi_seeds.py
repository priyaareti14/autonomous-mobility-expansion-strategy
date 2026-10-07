"""Generate the Phase 9 publication seeds from the committed Phase 8 outputs.

The Phase 8 results (outputs/phase8/, commit 7438ee7) are the single source of truth. This script projects
the compact, decision-relevant files into dbt seeds (dbt/seeds/phase8/), so the Power BI publication layer
can read them through dbt (seed -> ANALYTICS.PBI_*) instead of loose files. It never recomputes anything:
columns are copied verbatim (market names are dropped because DIM_MARKET carries them).

It also writes pbi_regulatory_dimension_labels.csv: display labels of the 7 active regulatory dimensions,
taken verbatim from config/regulatory_feature_contract.csv.

Not published: draw matrices (none exist), QA check files, metadata, figures, the per-test methodology
detail and the normalization detail (summarised in the robustness ranges).

Usage (repository root, .venv active):
    python scripts/build_powerbi_seeds.py           # (re)write the seeds
    python scripts/build_powerbi_seeds.py --check   # exit 1 if a seed differs from its source
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs" / "phase8"
DST = ROOT / "dbt" / "seeds" / "phase8"

# seed name -> source file. Every column except market_name is kept, in source order.
SEEDS = {
    "p8_robustness_summary": "robustness_summary.csv",
    "p8_weight_sensitivity": "weight_sensitivity_summary.csv",
    "p8_business_scenarios": "business_priority_scenarios.csv",
    "p8_scenario_contract": "scenario_simulator_contract.csv",
    "p8_regulatory_uncertainty": "regulatory_uncertainty.csv",
    "p8_deployment_validation": "deployment_validation.csv",
    "p8_deployment_mismatch": "deployment_mismatch_review.csv",
}
DROP = {"market_name"}


def project(text: str) -> str:
    """Drop the DROP columns from a CSV without re-parsing values (bytes of kept fields are unchanged)."""
    import csv
    import io

    rows = list(csv.reader(io.StringIO(text)))
    keep = [i for i, c in enumerate(rows[0]) if c not in DROP]
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    for r in rows:
        w.writerow([r[i] for i in keep])
    return out.getvalue()


def regulatory_labels() -> str:
    """Display labels for the 7 active regulatory dimensions, from the committed contract (definitions only)."""
    import csv
    import io

    con = ROOT / "config" / "regulatory_feature_contract.csv"
    rows = list(csv.DictReader(io.StringIO(con.read_bytes().decode("utf-8").replace("\r\n", "\n"))))
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["mode", "feature_id", "legal_dimension", "business_interpretation", "known_limitation"])
    for r in sorted((r for r in rows if r["candidate_status"] == "ACTIVE_CANDIDATE"), key=lambda r: r["feature_id"]):
        w.writerow([r["mode"], r["feature_id"], r["legal_dimension"], r["business_interpretation"], r["known_limitation"]])
    return out.getvalue()


def build() -> dict[str, str]:
    seeds = {name: project((SRC / src).read_bytes().decode("utf-8").replace("\r\n", "\n"))
             for name, src in SEEDS.items()}
    seeds["pbi_regulatory_dimension_labels"] = regulatory_labels()
    return seeds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if a committed seed differs from its source")
    args = ap.parse_args()
    DST.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, text in build().items():
        path = DST / f"{name}.csv"
        if args.check:
            if not path.exists() or path.read_bytes().decode("utf-8").replace("\r\n", "\n") != text:
                stale.append(name)
        else:
            path.write_bytes(text.encode("utf-8"))
            print(f"wrote {path.relative_to(ROOT)} ({text.count(chr(10)) - 1} rows)")
    if args.check:
        print("phase8 seeds match outputs/phase8" if not stale else f"STALE seeds: {stale}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
