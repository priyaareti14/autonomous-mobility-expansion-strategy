"""Generate the Phase 7 regulatory dbt seeds from the version-controlled evidence.

evidence/regulatory_evidence.csv and config/regulatory_feature_contract.csv stay the single sources
of truth. This script projects them into dbt seeds so the readiness model can read them through dbt
(seed -> INTERMEDIATE -> ANALYTICS) instead of from loose files:

  dbt/seeds/regulatory_state_evidence.csv    state-level records of the ACTIVE_CANDIDATE dimensions only
  dbt/seeds/regulatory_feature_contract.csv  the regulatory contract (definitions only)

The projection is deterministic (sorted, fixed columns, LF line endings), so --check can prove the
committed seeds still match their sources. Deployment evidence is never read.

Usage (repository root, .venv active):
    python scripts/build_regulatory_seed.py           # (re)write the seeds
    python scripts/build_regulatory_seed.py --check   # exit 1 if a seed is stale
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "regulatory_evidence.csv"
CONTRACT = ROOT / "config" / "regulatory_feature_contract.csv"
SEEDS = ROOT / "dbt" / "seeds"

EVIDENCE_COLS = ["evidence_id", "mode", "state_usps", "state_fips", "legal_dimension", "coded_status",
                 "numeric_value", "unit", "effective_date", "evidence_as_of", "access_date", "source_type",
                 "verification_status", "second_source_status", "confidence"]
CONTRACT_COLS = ["feature_id", "mode", "legal_dimension", "source_level", "favorable_statuses",
                 "market_mapping_method", "direction", "active_candidate_flag", "candidate_status"]


def build() -> dict[str, str]:
    con = pd.read_csv(CONTRACT, dtype=str, keep_default_na=False)
    active = con[con.candidate_status == "ACTIVE_CANDIDATE"]
    ev = pd.read_csv(EVIDENCE, dtype=str, keep_default_na=False)
    ev = ev[(ev.jurisdiction_type == "STATE")
            & ev.set_index(["mode", "legal_dimension"]).index.isin(active.set_index(["mode", "legal_dimension"]).index)]
    ev = ev.rename(columns={"jurisdiction": "state_usps"})[EVIDENCE_COLS]
    assert not ev.duplicated(["mode", "legal_dimension", "state_usps"]).any(), "duplicate state evidence"
    out = {}
    for name, df, key in (("regulatory_state_evidence", ev, ["mode", "legal_dimension", "state_usps"]),
                          ("regulatory_feature_contract", con[CONTRACT_COLS], ["feature_id"])):
        buf = io.StringIO()
        df.sort_values(key).to_csv(buf, index=False, lineterminator="\n")
        out[name] = buf.getvalue()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if a committed seed differs from its source")
    args = ap.parse_args()
    stale = []
    for name, text in build().items():
        path = SEEDS / f"{name}.csv"
        if args.check:
            if not path.exists() or path.read_bytes().decode("utf-8") != text:
                stale.append(name)
        else:
            path.write_bytes(text.encode("utf-8"))
            print(f"wrote {path.relative_to(ROOT)} ({text.count(chr(10)) - 1} rows)")
    if args.check:
        print("seeds match sources" if not stale else f"STALE seeds: {stale}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
