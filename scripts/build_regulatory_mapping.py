"""Phase 6.5: reproducible market -> regulatory-evidence mapping (A-012). No scores.

Inputs:
  CORE.BRG_MARKET_STATE / CORE.DIM_MARKET (read-only, AM_TRANSFORMER)
  evidence/regulatory_evidence.csv (validated by scripts/validate_evidence.py)
  config/regulatory_feature_contract.csv (mapping method per legal dimension)

Outputs (outputs/phase65/):
  jurisdiction_inventory.csv      one row per market x state: population share, principal-state flag
  market_regulatory_mapping.csv   one row per market x mode x legal_dimension x state: the state's coded
                                  status, its evidence id and confidence, the mapping method and the
                                  future aggregation rule from the contract, and a QA flag
  market_regulatory_summary.csv   one row per market x mode x legal_dimension: status composition by
                                  population share, whether states differ, principal / dominant state
                                  status and, for numeric limits, the most restrictive permitting value
  multistate_analysis.csv         the 11 multi-state markets: dimensions on which their states differ

Status composition is a descriptive population share, not a score; nothing is weighted or ranked.

Usage (repository root, .venv active):
    python scripts/build_regulatory_mapping.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.analytics.data_access import Warehouse  # noqa: E402

EVID = ROOT / "evidence" / "regulatory_evidence.csv"
CONTRACT = ROOT / "config" / "regulatory_feature_contract.csv"
OUT = ROOT / "outputs" / "phase65"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    wh = Warehouse()
    try:
        brg = wh.query("""
            select b.market_id, d.cbsa_name, d.principal_state_usps, b.state_fips, b.state_usps,
                   b.population_share_2025, b.state_population_2025, b.county_count
            from AUTONOMOUS_MOBILITY.CORE.BRG_MARKET_STATE b
            join AUTONOMOUS_MOBILITY.CORE.DIM_MARKET d using (market_id)""")
    finally:
        wh.close()
    brg["market_id"] = brg["market_id"].astype(str)
    assert brg.market_id.nunique() == 35, "market universe broken"
    brg["is_principal_state"] = brg.state_usps == brg.principal_state_usps
    brg["n_states"] = brg.groupby("market_id").state_usps.transform("count")
    rank = brg.sort_values(["market_id", "population_share_2025"], ascending=[True, False])
    brg["is_dominant_state"] = brg.index.isin(rank.groupby("market_id").head(1).index)
    brg.sort_values(["market_id", "population_share_2025"], ascending=[True, False]).to_csv(
        OUT / "jurisdiction_inventory.csv", index=False, lineterminator="\n")

    ev = pd.read_csv(EVID, dtype=str, keep_default_na=False)
    ev = ev[ev.jurisdiction_type == "STATE"]
    con = pd.read_csv(CONTRACT, dtype=str, keep_default_na=False)
    mapped = con[con.market_mapping_method != "CONTEXT_ONLY"]

    # Protocol section 3.2: a state with no PDD statute has no rows for the PDD operating conditions
    # (weight, speed, operator, insurance, registration). That is not-applicable, not missing evidence.
    pdd = ev[ev.legal_dimension == "SW_PDD_LEGAL_STATUS"].set_index("jurisdiction").coded_status.to_dict()
    rows = []
    for c in mapped.itertuples(index=False):
        e = ev[(ev["mode"] == c.mode) & (ev.legal_dimension == c.legal_dimension)].drop_duplicates("jurisdiction")
        e = e.set_index("jurisdiction")
        for b in brg.itertuples(index=False):
            has = b.state_usps in e.index
            r = e.loc[b.state_usps] if has else None
            not_applicable = (not has and c.mode == "SIDEWALK_DELIVERY"
                              and pdd.get(b.state_usps) in ("NO_STATUTE", "STATUTE_PROHIBITS", "UNCLEAR"))
            rows.append({
                "market_id": b.market_id, "cbsa_name": b.cbsa_name, "mode": c.mode,
                "legal_dimension": c.legal_dimension, "regulatory_feature_id": c.feature_id,
                "state_usps": b.state_usps, "state_fips": b.state_fips,
                "state_population_share": round(float(b.population_share_2025), 6),
                "is_principal_state": b.is_principal_state, "is_dominant_state": b.is_dominant_state,
                "state_status": r.coded_status if has else ("NOT_APPLICABLE_NO_PDD_STATUTE" if not_applicable
                                                             else "MISSING_EVIDENCE"),
                "state_numeric_value": r.numeric_value if has else "",
                "unit": r.unit if has else "",
                "evidence_id": r.evidence_id if has else "",
                "evidence_confidence": r.confidence if has else "",
                "market_mapping_method": c.market_mapping_method,
                "future_aggregation_rule": c.future_aggregation_rule,
            })
    m = pd.DataFrame(rows)

    summ = []
    for (mid, mode, dim), g in m.groupby(["market_id", "mode", "legal_dimension"], sort=True):
        comp = g.groupby("state_status").state_population_share.sum().sort_values(ascending=False)
        differ = g.state_status.nunique() > 1
        num = pd.to_numeric(g.state_numeric_value, errors="coerce")
        permitting = g[num.notna()]
        low_conf = (g.evidence_confidence == "LOW").any()
        flag = ("MISSING_EVIDENCE" if (g.state_status == "MISSING_EVIDENCE").any()
                else "SINGLE_STATE" if len(g) == 1
                else "MULTI_STATE_DIFFERS" if differ
                else "MULTI_STATE_UNIFORM")
        principal = g[g.is_principal_state]
        dominant = g[g.is_dominant_state]
        summ.append({
            "market_id": mid, "cbsa_name": g.cbsa_name.iloc[0], "mode": mode, "legal_dimension": dim,
            "regulatory_feature_id": g.regulatory_feature_id.iloc[0], "n_states": len(g),
            "status_composition_by_population": "|".join(f"{s}:{v:.4f}" for s, v in comp.items()),
            "states_differ": differ,
            "principal_state": principal.state_usps.iloc[0] if len(principal) else "",
            "principal_state_status": principal.state_status.iloc[0] if len(principal) else "",
            "dominant_state": dominant.state_usps.iloc[0],
            "dominant_state_status": dominant.state_status.iloc[0],
            "most_restrictive_numeric_among_permitting_states": permitting.state_numeric_value.astype(float).min()
            if len(permitting) else "",
            "unit": permitting.unit.iloc[0] if len(permitting) else "",
            "market_mapping_method": g.market_mapping_method.iloc[0],
            "future_aggregation_rule": g.future_aggregation_rule.iloc[0],
            "qa_flag": flag + (";LOW_CONFIDENCE_EVIDENCE" if low_conf else ""),
        })
    s = pd.DataFrame(summ)

    keys = ["market_id", "mode", "legal_dimension"]
    m = m.merge(s[keys + ["qa_flag"]], on=keys, how="left", validate="many_to_one")
    assert m.qa_flag.notna().all(), "mapping row without a market summary"
    m.to_csv(OUT / "market_regulatory_mapping.csv", index=False, lineterminator="\n")
    s.to_csv(OUT / "market_regulatory_summary.csv", index=False, lineterminator="\n")

    ms = s[s.n_states > 1]
    multi = (ms.groupby(["market_id", "cbsa_name"])
             .apply(lambda g: pd.Series({
                 "n_states": int(g.n_states.iloc[0]),
                 "dimensions_mapped": len(g),
                 "dimensions_where_states_differ": int(g.states_differ.sum()),
                 "differing_dimensions": ";".join(g.loc[g.states_differ, "legal_dimension"])}),
                    include_groups=False)
             .reset_index())
    multi.to_csv(OUT / "multistate_analysis.csv", index=False, lineterminator="\n")

    # A-012 evidence: what each candidate universal rule would conclude for every multi-state market x
    # ACTIVE categorical dimension, next to the population share of the market under a favorable status.
    act = con[(con.active_candidate_flag == "TRUE") & (con.market_mapping_method == "POPULATION_SHARE_BY_STATUS")]
    comp = []
    for c in act.itertuples(index=False):
        fav = set(c.favorable_statuses.split("|"))
        sub = m[(m["mode"] == c.mode) & (m.legal_dimension == c.legal_dimension)]
        for mid, g in sub.groupby("market_id"):
            if len(g) < 2:
                continue
            g = g.sort_values("state_population_share", ascending=False)
            comp.append({
                "market_id": mid, "cbsa_name": g.cbsa_name.iloc[0], "mode": c.mode, "legal_dimension": c.legal_dimension,
                "state_statuses": "|".join(f"{s}:{st}:{p:.4f}" for s, st, p in
                                           zip(g.state_usps, g.state_status, g.state_population_share)),
                "states_differ": g.state_status.nunique() > 1,
                "C_population_share_favorable": round(float(g.loc[g.state_status.isin(fav), "state_population_share"].sum()), 4),
                "A_principal_city_state_favorable": bool(g[g.is_principal_state].state_status.isin(fav).any()),
                "B_dominant_state_favorable": bool(g.iloc[0].state_status in fav),
                "D_most_restrictive_favorable": bool(g.state_status.isin(fav).all()),
                "E_most_permissive_favorable": bool(g.state_status.isin(fav).any()),
            })
    pd.DataFrame(comp).to_csv(OUT / "a012_method_comparison.csv", index=False, lineterminator="\n")

    print(f"inventory rows {len(brg)} | mapping rows {len(m)} | summary rows {len(s)} | multi-state markets {len(multi)}")
    print("qa flags:", s.qa_flag.value_counts().to_dict())
    print(multi.to_string(index=False))
    missing = m[m.state_status == "MISSING_EVIDENCE"]
    if len(missing):
        print("MISSING EVIDENCE:", missing[["mode", "legal_dimension", "state_usps"]].drop_duplicates().to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
