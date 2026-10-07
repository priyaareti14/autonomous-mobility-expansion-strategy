"""Phase 9 publication QA: reconcile the Power BI publication layer with the committed Phase 7/8 outputs.

Checks (read-only on Snowflake, AM_TRANSFORMER):
  1. the Phase 8 publication seeds still match outputs/phase8 (build_powerbi_seeds --check logic);
  2. every PBI_* table reconciles with the committed CSV it reports (values within the export precision,
     NULLs in the same places, no row gained or lost);
  3. dbt lineage: deployment seeds feed ONLY PBI_FCT_DEPLOYMENT_VALIDATION, and no scoring relation reads any
     Phase 8 seed;
  4. writes powerbi/data_dictionary.csv (from information_schema + dbt column docs) and
     outputs/phase9/publication_qa.csv. Deterministic: no timestamps.

Usage (repository root, .venv active, after `python scripts/run_dbt.py build`):
    python scripts/run_phase9_publication_qa.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_powerbi_seeds import DST as SEED_DIR, build as build_seeds  # noqa: E402
from src.analytics.data_access import Warehouse  # noqa: E402

P7, P8 = ROOT / "outputs" / "phase7", ROOT / "outputs" / "phase8"
OUT = ROOT / "outputs" / "phase9"
PBI_DIR = ROOT / "powerbi"
DB = "AUTONOMOUS_MOBILITY"
TOL = 1e-6
PBI_TABLES = ["PBI_DIM_MARKET", "PBI_DIM_MODE", "PBI_DIM_COMPONENT", "PBI_DIM_FEATURE", "PBI_DIM_SCENARIO",
              "PBI_DIM_REGULATORY_SCENARIO", "PBI_FCT_MARKET_BASELINE", "PBI_FCT_MARKET_COMPONENT",
              "PBI_FCT_MARKET_FEATURE_CONTRIBUTION", "PBI_FCT_MARKET_ROBUSTNESS", "PBI_FCT_BUSINESS_SCENARIO",
              "PBI_FCT_REGULATORY_UNCERTAINTY", "PBI_FCT_DEPLOYMENT_VALIDATION"]
CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))
    return bool(ok)


def reconcile(name: str, pbi: pd.DataFrame, src: pd.DataFrame, keys: list[str], cols: dict[str, str]) -> None:
    """cols: pbi column -> source column. Numeric within TOL, others exact; NULLs must coincide."""
    p, s = pbi.copy(), src.copy()
    for k in keys:
        p[k], s[k] = p[k].astype(str), s[k].astype(str)
    m = p.merge(s, on=keys, how="outer", suffixes=("_pbi", "_src"), indicator=True)
    lost = int((m._merge != "both").sum())
    bad = []
    for pc, sc in cols.items():
        a = m[pc + "_pbi"] if pc + "_pbi" in m else m[pc]
        b = m[sc + "_src"] if sc + "_src" in m else m[sc]
        is_bool = pd.api.types.is_bool_dtype(a) or pd.api.types.is_bool_dtype(b)
        if not is_bool and (pd.api.types.is_numeric_dtype(a) or pd.api.types.is_numeric_dtype(b)):
            a, b = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
            diff = (a - b).abs()
            # Phase 7 CSVs keep 10 significant digits (%.10g) and Phase 8 CSVs 6 decimals, so the tolerance is
            # the larger of 1e-6 absolute and 1e-9 relative (exact equality to Snowflake is a dbt test).
            if ((a.isna() != b.isna()) | (diff > (TOL + 1e-9 * b.abs()))).any():
                bad.append(f"{pc} (max diff {diff.max():.2e})")
        else:
            norm = lambda x: x.astype(str).str.lower().replace({"nan": "", "none": "", "<na>": ""})  # noqa: E731
            if (norm(a) != norm(b)).any():
                bad.append(pc)
    check(f"{name} reconciles with its committed source ({len(p)} rows)", lost == 0 and not bad,
          f"unmatched rows {lost}" + (f"; differing: {', '.join(bad)}" if bad else ""))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PBI_DIR.mkdir(parents=True, exist_ok=True)
    print("Seed synchronization")
    stale = [n for n, t in build_seeds().items()
             if (SEED_DIR / f"{n}.csv").read_bytes().decode("utf-8").replace("\r\n", "\n") != t]
    check("Phase 9 seeds match outputs/phase8 and config (build_powerbi_seeds --check)", not stale, f"stale: {stale}")

    tables_sql = "', '".join(PBI_TABLES)
    wh = Warehouse()
    try:
        t = {n: wh.query(f"select * from {DB}.ANALYTICS.{n}") for n in PBI_TABLES}
        cols = wh.query(f"select table_name, column_name, data_type, ordinal_position from {DB}.information_schema.columns "
                        f"where table_schema = 'ANALYTICS' and table_name in ('{tables_sql}') "
                        "order by table_name, ordinal_position")
    finally:
        wh.close()
    for v in t.values():
        if "market_id" in v:
            v["market_id"] = v["market_id"].astype(str)

    print("Reconciliation with committed Phase 7/8 outputs")
    base = pd.concat([pd.read_csv(P7 / f"{m}_baseline.csv", dtype={"market_id": str}).assign(mode=mode)
                      for m, mode in [("robotaxi", "ROBOTAXI"), ("sidewalk", "SIDEWALK_DELIVERY"), ("drone", "DRONE_DELIVERY")]])
    reconcile("PBI_FCT_MARKET_BASELINE", t["PBI_FCT_MARKET_BASELINE"], base, ["market_id", "mode"],
              {"baseline_readiness_score": "baseline_readiness_score", "baseline_rank": "baseline_rank",
               "non_regulatory_score": "non_regulatory_score", "regulatory_evidence_coverage_pct": "c4_evidence_coverage_pct",
               "regulatory_unverified_states": "c4_unverified_states"})
    reconcile("PBI_FCT_MARKET_COMPONENT", t["PBI_FCT_MARKET_COMPONENT"],
              pd.read_csv(P7 / "component_scores.csv", dtype={"market_id": str}), ["market_id", "mode", "component"],
              {"component_score": "component_score", "component_weight": "component_weight",
               "component_contribution": "component_contribution"})
    reconcile("PBI_FCT_MARKET_FEATURE_CONTRIBUTION", t["PBI_FCT_MARKET_FEATURE_CONTRIBUTION"],
              pd.read_csv(P7 / "feature_scores.csv", dtype={"market_id": str}), ["market_id", "mode", "feature_id"],
              {"raw_value": "raw_value", "transformed_value": "transformed_value", "feature_score": "feature_score",
               "feature_weight": "feature_weight", "weighted_feature_contribution": "weighted_feature_contribution"})
    rs = pd.read_csv(P8 / "robustness_summary.csv", dtype={"market_id": str})
    ws = pd.read_csv(P8 / "weight_sensitivity_summary.csv", dtype={"market_id": str})
    rob = rs.merge(ws[ws.regulatory_scenario == "BASELINE_EVIDENCE"][["mode", "market_id", "top_1_frequency",
                   "top_3_frequency", "rank_iqr", "within_2_ranks_of_baseline_frequency"]], on=["mode", "market_id"], how="left")
    reconcile("PBI_FCT_MARKET_ROBUSTNESS", t["PBI_FCT_MARKET_ROBUSTNESS"], rob, ["market_id", "mode"],
              {"mean_rank": "mean_rank", "median_rank": "median_rank", "rank_std": "rank_std", "best_rank": "best_rank",
               "worst_rank": "worst_rank", "top_1_frequency": "top_1_frequency", "top_3_frequency": "top_3_frequency",
               "top_5_frequency": "top_5_frequency", "top_10_frequency": "top_10_frequency", "rank_iqr": "rank_iqr",
               "rank_90pct_low": "rank_p05", "rank_90pct_high": "rank_p95",
               "within_2_ranks_of_baseline_frequency": "within_2_ranks_of_baseline_frequency",
               "normalization_rank_range": "normalization_rank_range", "regulatory_rank_range": "regulatory_rank_range",
               "methodology_rank_range": "methodology_rank_range", "pattern_flags": "pattern_flags"})
    reconcile("PBI_FCT_BUSINESS_SCENARIO", t["PBI_FCT_BUSINESS_SCENARIO"],
              pd.read_csv(P8 / "business_priority_scenarios.csv", dtype={"market_id": str}), ["market_id", "scenario_id"],
              {"scenario_score": "score", "scenario_rank": "rank", "rank_change_vs_baseline": "rank_change_vs_baseline"})
    reg = pd.read_csv(P8 / "regulatory_uncertainty.csv", dtype={"market_id": str})
    long = pd.concat([reg.assign(regulatory_scenario=f"REG_{s.upper()}", scenario_score=reg[f"{s}_score"],
                                 scenario_rank=reg[f"{s}_rank"]) for s in ["pessimistic", "neutral", "optimistic"]])
    reconcile("PBI_FCT_REGULATORY_UNCERTAINTY", t["PBI_FCT_REGULATORY_UNCERTAINTY"], long,
              ["market_id", "mode", "regulatory_scenario"], {"scenario_score": "scenario_score", "scenario_rank": "scenario_rank"})
    dep = pd.read_csv(P8 / "deployment_validation.csv", dtype={"market_id": str})
    reconcile("PBI_FCT_DEPLOYMENT_VALIDATION", t["PBI_FCT_DEPLOYMENT_VALIDATION"], dep, ["market_id", "mode"],
              {"deployment_present": "current_commercial_broad", "deployment_status": "deployment_cohort",
               "market_resolution_quality": "current_resolutions"})
    reconcile("PBI_DIM_SCENARIO", t["PBI_DIM_SCENARIO"], pd.read_csv(P8 / "scenario_simulator_contract.csv"),
              ["scenario_id"], {f"c{i}_weight": f"c{i}_weight" for i in range(1, 6)})

    print("Lineage (dbt manifest)")
    man = json.loads((ROOT / "dbt" / "target" / "manifest.json").read_text(encoding="utf-8"))
    nodes = {k: v for k, v in man["nodes"].items() if v["resource_type"] == "model"}
    dep_seeds = {"seed.autonomous_mobility.p8_deployment_validation", "seed.autonomous_mobility.p8_deployment_mismatch"}
    p8_seeds = {k for k in man["nodes"] if k.startswith("seed.autonomous_mobility.p8_")}
    readers = sorted(v["name"] for v in nodes.values() if dep_seeds & set(v["depends_on"]["nodes"]))
    check("deployment seeds feed only PBI_FCT_DEPLOYMENT_VALIDATION", readers == ["pbi_fct_deployment_validation"],
          ", ".join(readers))
    scoring = [v["name"] for v in nodes.values() if "/scoring/" in v["original_file_path"].replace("\\", "/")
               and p8_seeds & set(v["depends_on"]["nodes"])]
    check("no Phase 7 scoring model reads a Phase 8 seed", not scoring, ", ".join(scoring))
    nonpbi = [v["name"] for v in nodes.values() if not v["name"].startswith("pbi_") and p8_seeds & set(v["depends_on"]["nodes"])]
    check("Phase 8 seeds are read only by the publication layer", not nonpbi, ", ".join(nonpbi))
    deploy_cols = [f"{n}.{c}" for n, df in t.items() if n != "PBI_FCT_DEPLOYMENT_VALIDATION" for c in df.columns
                   if "deploy" in c.lower() or "operator" in c.lower()]
    check("no deployment field in any publication table except the validation table", not deploy_cols, ", ".join(deploy_cols))

    print("Publication invariants")
    b = t["PBI_FCT_MARKET_BASELINE"]
    check("NULL baseline scores preserved (robotaxi 6, sidewalk 4, drone 10 incomplete)",
          b.groupby("mode").baseline_readiness_score.apply(lambda s: int(s.isna().sum())).to_dict()
          == {"DRONE_DELIVERY": 10, "ROBOTAXI": 6, "SIDEWALK_DELIVERY": 4})
    c = t["PBI_FCT_MARKET_COMPONENT"]
    check("robotaxi C5 absent from the component fact",
          not ((c["mode"] == "ROBOTAXI") & (c.component == "C5_INFRASTRUCTURE_AND_MODE_FIT")).any())
    s = t["PBI_DIM_SCENARIO"]
    wsum = s[[f"c{i}_weight" for i in range(1, 6)]].fillna(0).sum(axis=1)
    check("named scenario weights sum to 1", bool((wsum - 1).abs().max() < 1e-9))

    # ---- data dictionary ---------------------------------------------------------------------------
    docs = {}
    for v in nodes.values():
        if v["name"].startswith("pbi_"):
            for cname, cdef in v.get("columns", {}).items():
                if cdef.get("description"):
                    docs[(v["name"].upper(), cname.upper())] = cdef["description"]
    rows = [dictionary_row(r.table_name, r.column_name, r.data_type, docs) for r in cols.itertuples()]
    dd = pd.DataFrame(rows)
    dd.to_csv(PBI_DIR / "data_dictionary.csv", index=False, lineterminator="\n")
    check("data dictionary covers every published column", len(dd) == sum(len(df.columns) for df in t.values()),
          f"{len(dd)} columns")
    pd.DataFrame(CHECKS).to_csv(OUT / "publication_qa.csv", index=False, lineterminator="\n")
    failed = sum(x["status"] == "FAIL" for x in CHECKS)
    print(f"\n{len(CHECKS) - failed} checks passed, {failed} failed.")
    return 1 if failed else 0


KEYS = {"MARKET_ID": "Market key (CBSA code)", "MODE": "Mode key", "COMPONENT": "Component key",
        "FEATURE_KEY": "Feature key (mode|feature_id)", "SCENARIO_ID": "Scenario key",
        "REGULATORY_SCENARIO": "Regulatory scenario key"}
PRIMARY = {"PBI_DIM_MARKET": "MARKET_ID", "PBI_DIM_MODE": "MODE", "PBI_DIM_COMPONENT": "COMPONENT",
           "PBI_DIM_FEATURE": "FEATURE_KEY", "PBI_DIM_SCENARIO": "SCENARIO_ID",
           "PBI_DIM_REGULATORY_SCENARIO": "REGULATORY_SCENARIO"}
HIDE = {"MODEL_VERSION", "IN_BASE_FLAG", "N_DRAWS", "N_RANKED_MARKETS", "NON_REGULATORY_COMPONENT_WEIGHT",
        "FEATURE_ID", "SORT_ORDER", "FIXED_TEST_WORST_RANK", "SCORE_METHOD", "TRANSFORMATION",
        "MISMATCH_CANDIDATE_EXPLANATIONS"}
W = "the 10,000 tested component-weight configurations (Phase 8)"
TEXT = {
    # baseline and decomposition
    "BASELINE_READINESS_SCORE": "Baseline readiness score (Phase 7, 0-100, within mode only; blank = not determinable from verified evidence)",
    "BASELINE_SCORE": "Phase 7 baseline readiness score (0-100, within mode; blank = incomplete regulatory evidence)",
    "BASELINE_RANK": "Phase 7 baseline rank among markets with a complete score (1 = highest); not a final recommendation",
    "BASELINE_RANK_TIED_FLAG": "TRUE if another market has the same baseline score (6 decimals)",
    "SCORE_GAP_TO_PRECEDING": "Points behind the next-higher-ranked market",
    "SCORE_COMPLETE_FLAG": "TRUE if every component, including regulation, has a verified score",
    "REGULATORY_COMPLETE_FLAG": "TRUE if every regulatory dimension rests on verified (primary, MEDIUM/HIGH) evidence",
    "NON_REGULATORY_SCORE": "Diagnostic: equal-weight mean of the non-regulatory components; available for every market, not a readiness score, not ranked",
    "REGULATORY_SCORE_VERIFIED": "C4 Regulatory & Autonomy Readiness score (0-100); blank where evidence is incomplete",
    "REGULATORY_EVIDENCE_COVERAGE_PCT": "Share of market population whose regulatory status is verified (mean across the mode's regulatory dimensions)",
    "REGULATORY_MAX_UNKNOWN_SHARE": "Largest unknown / LOW-confidence population share across the mode's regulatory dimensions",
    "REGULATORY_UNVERIFIED_STATES": "States whose evidence keeps C4 incomplete (alphabetical); blank when complete",
    "REGULATORY_INCOMPLETE_REASON": "Regulatory dimensions that are incomplete, with the evidence records responsible",
    "REGULATORY_DECOMPOSITION": "Plain-language population-share decomposition of every regulatory dimension",
    "STRONGEST_FEATURE": "Input with the highest feature score (score in brackets)",
    "WEAKEST_FEATURE": "Input with the lowest feature score (score in brackets)",
    "TOP_POSITIVE_CONTRIBUTORS": "Three inputs adding the most points to the baseline score",
    "TOP_CONSTRAINTS": "Three inputs costing the most points against a perfect score",
    # components and features
    "COMPONENT_SCORE": "Component score (0-100): equal-weight mean of the component's input scores",
    "COMPONENT_WEIGHT": "Baseline component weight (robotaxi 1/4, sidewalk and drone 1/5)",
    "COMPONENT_CONTRIBUTION": "Points the component adds to the baseline score (score x weight)",
    "COMPONENT_COMPLETE_FLAG": "TRUE if the component has a verified score",
    "FEATURE_COUNT": "Number of inputs in the component's base calculation",
    "RAW_VALUE": "Untransformed input value (unit in the feature dimension)",
    "TRANSFORMED_VALUE": "Model value after the approved transformation (e.g. LOG1P)",
    "FEATURE_SCORE": "Directionally aligned input score (0-100; percentile, or verified favorable population share for regulation)",
    "FEATURE_WEIGHT": "Weight within the component (equal)",
    "WEIGHTED_FEATURE_CONTRIBUTION": "Points the input adds to its component score",
    "CONTRIBUTION_TO_OVERALL": "Points the input adds to the baseline readiness score",
    "POINTS_BELOW_MAXIMUM": "Points the input costs against a perfect score",
    "DIRECTION": "Whether higher or lower raw values are more favorable",
    "FEATURE_LABEL": "Readable input name",
    "FEATURE_DESCRIPTION": "What the input measures",
    "KNOWN_LIMITATION": "Documented limitation of the input",
    "REGULATORY_INPUT_FLAG": "TRUE for the regulatory (C4) dimensions",
    # robustness
    "MEAN_RANK": f"Mean rank across {W}",
    "MEDIAN_RANK": f"Median rank across {W}",
    "RANK_STD": f"Standard deviation of rank across {W}",
    "BEST_RANK": f"Best rank across {W}",
    "WORST_RANK": f"Worst rank across {W}",
    "TOP_1_FREQUENCY": f"Share of {W} in which the market ranks 1st (not a probability)",
    "TOP_3_FREQUENCY": f"Share of {W} in which the market ranks in the top 3",
    "TOP_5_FREQUENCY": f"Share of {W} in which the market ranks in the top 5",
    "TOP_10_FREQUENCY": f"Share of {W} in which the market ranks in the top 10",
    "RANK_IQR": "Interquartile range of the weight-draw ranks",
    "RANK_90PCT_LOW": "5th percentile of the weight-draw ranks (better end of the 90% interval)",
    "RANK_90PCT_HIGH": "95th percentile of the weight-draw ranks (worse end of the 90% interval)",
    "RANK_INTERVAL_90": "Width of the 90% weight-draw rank interval",
    "WITHIN_2_RANKS_OF_BASELINE_FREQUENCY": "Share of weight draws within 2 ranks of the baseline rank",
    "MEAN_ABS_RANK_CHANGE_FROM_BASELINE": "Mean absolute rank change from baseline across the weight draws",
    "BUSINESS_SCENARIO_RANK_RANGE": "Rank spread across the named business-priority scenarios",
    "NORMALIZATION_RANK_RANGE": "Rank spread across percentile, raw min-max and winsorized min-max scoring",
    "METHODOLOGY_RANK_RANGE": "Rank spread across the one-at-a-time methodology tests (feature drops, airport, density, weather, wind, regulatory coding)",
    "REGULATORY_RANK_RANGE": "Rank spread across the pessimistic / neutral / optimistic regulatory bounds",
    "REGULATORY_BEST_RANK": "Best rank across the three regulatory bounds",
    "REGULATORY_WORST_RANK": "Worst rank across the three regulatory bounds",
    "REGULATORY_SCORE_RANGE": "Score spread across the three regulatory bounds (0 for complete markets)",
    "OVERALL_TESTED_BEST_RANK": "Best rank in any Phase 8 test of the complete-market universe",
    "OVERALL_TESTED_WORST_RANK": "Worst rank in any Phase 8 test of the complete-market universe",
    "CONSISTENT_TOP_PERFORMER": "Approved Phase 8 flag: top-5 in >= 80% of weight draws and top 5 in every named test",
    "WEIGHT_SENSITIVE": "Approved Phase 8 flag: 90% weight-draw rank interval >= 10 ranks",
    "NORMALIZATION_SENSITIVE": "Approved Phase 8 flag: rank range across normalizations >= 5",
    "METHODOLOGY_SENSITIVE": "Approved Phase 8 flag: rank range across methodology tests >= 5",
    "REGULATION_SENSITIVE": "Approved Phase 8 flag: own score moves across the regulatory bounds and rank range >= 5",
    "PATTERN_FLAGS": "All approved Phase 8 flags for the market, semicolon-separated",
    # scenarios
    "SCENARIO_SCORE": "Readiness score under the scenario (0-100, within mode)",
    "SCENARIO_RANK": "Rank under the scenario (1 = highest)",
    "RANK_CHANGE_VS_BASELINE": "Scenario rank minus baseline rank (negative = moves up)",
    "IS_BASELINE_SCENARIO": "TRUE for NEUTRAL (equal weights = the Phase 7 baseline)",
    "PRIORITY_COMPONENT_CODE": "Component weighted at 40% in the scenario (blank for NEUTRAL)",
    "ASSUMED_FAVORABLE_FRACTION": "Share of the unknown population counted favorable in the bound (0, 0.5, 1)",
    "REGULATORY_SCORE": "C4 under the regulatory bound (backed out from the published score)",
    "NESTED_TOP_5_FREQUENCY": "Robotaxi only: top-5 share of the 10,000 weight draws under this regulatory bound",
    "NESTED_TOP_10_FREQUENCY": "Robotaxi only: top-10 share of the 10,000 weight draws under this regulatory bound",
    "NESTED_MEAN_RANK": "Robotaxi only: mean weight-draw rank under this regulatory bound",
    "NESTED_MEDIAN_RANK": "Robotaxi only: median weight-draw rank under this regulatory bound",
    "NESTED_BEST_RANK": "Robotaxi only: best weight-draw rank under this regulatory bound",
    "NESTED_WORST_RANK": "Robotaxi only: worst weight-draw rank under this regulatory bound",
    # deployment (external validation)
    "DEPLOYMENT_PRESENT": "External validation only: a current commercial / limited-commercial service is recorded in the market (some service, not full coverage)",
    "COMMERCIAL_OR_LIMITED_COMMERCIAL_FLAG": "Same as Deployment Present (open-ended COMMERCIAL or LIMITED_COMMERCIAL record)",
    "DEPLOYMENT_PRESENT_PRIMARY_COHORT": "Deployment present, counting only WITHIN_MARKET_PARTIAL / CITY_ONLY records",
    "DEPLOYMENT_PRESENT_VERIFIED_ONLY": "Deployment present, counting only primary-verified records",
    "DEPLOYMENT_STATUS": "Deployment cohort of the market (current commercial, pilot/testing/announced, ended/paused only, other, none)",
    "ANY_DEPLOYMENT_RECORD": "TRUE if any deployment record of any status exists for the market",
    "MARKET_RESOLUTION_QUALITY": "Geographic resolution of the current records (partial, city-only, campus, multi-market)",
    "CURRENT_OPERATORS": "Operators with a current commercial record (external validation only)",
    "MISMATCH_CATEGORY": "Phase 8 mismatch class (high model / no deployment, low model / deployment, ...)",
    "MISMATCH_WEAKEST_COMPONENT": "Weakest component of a mismatched market",
    "MISMATCH_CANDIDATE_EXPLANATIONS": "Candidate (unverified) explanations for review, not findings",
    # dimensions
    "MARKET_NAME": "CBSA title (OMB July 2023)", "MARKET_SHORT_NAME": "Principal city (display label)",
    "PRINCIPAL_STATE_USPS": "State of the principal city", "STATES": "States the market spans",
    "IS_MULTI_STATE": "TRUE if the market spans more than one state",
    "POPULATION_RANK_2025": "Population rank among U.S. MSAs (PEP Vintage 2025): the fixed universe rule",
    "POPULATION_2025": "Resident population, July 2025 (PEP Vintage 2025)",
    "LATITUDE": "Population-weighted centre, latitude", "LONGITUDE": "Population-weighted centre, longitude",
    "ACTIVE_COMPONENT_COUNT": "Number of active components (robotaxi 4, others 5)",
    "HAS_C5_COMPONENT": "FALSE for robotaxi: C5 is structurally absent",
    "STATE_COUNT": "Number of states the market spans",
    "COMPONENT_CODE": "Short component code (C1-C5)", "COMPONENT_NAME": "Component display name",
    "COMPONENT_DESCRIPTION": "What the component measures", "SORT_ORDER": "Display sort order",
    "FEATURE_ID": "Contract feature id (PFxx) or regulatory feature id (RG-xx-xx)",
    "FEATURE_NAME": "Technical input name", "TRANSFORMATION": "Approved transformation applied before scoring",
    "UNIT": "Unit of the raw value", "SCORE_METHOD": "How the input is scored (percentile or verified favorable share)",
    "SOURCE_VINTAGE": "Source vintage of the input", "MODE_NAME": "Mode display name", "MODE_NOTE": "Mode note",
    "REGULATORY_SCENARIO_NAME": "Regulatory bound display name",
    "REGULATORY_SCENARIO_DESCRIPTION": "What the bound assumes about unknown evidence",
    "SCENARIO_NAME": "Scenario display name", "SCENARIO_TYPE": "NEUTRAL or the priority type",
    "DESCRIPTION": "Scenario assumption (not an estimate of business preferences)",
    "C1_WEIGHT": "C1 Demand & Market Opportunity weight", "C2_WEIGHT": "C2 Operating Environment weight",
    "C3_WEIGHT": "C3 Economic Attractiveness weight", "C4_WEIGHT": "C4 Regulatory & Autonomy Readiness weight",
    "C5_WEIGHT": "C5 Infrastructure & Mode Fit weight (always blank for robotaxi)",
    "PILOT_PRESENT": "A PILOT record exists (external validation)", "TESTING_PRESENT": "A TESTING record exists",
    "ANNOUNCED_PRESENT": "An ANNOUNCED record exists", "PAUSED_PRESENT": "A PAUSED record exists",
    "ENDED_PRESENT": "An ENDED (historical) record exists", "UNKNOWN_PRESENT": "A record of unknown status exists",
    "MODEL_VERSION": "Model version (baseline_v1)",
    "NON_REGULATORY_COMPONENT_WEIGHT": "Weight used for the diagnostic non-regulatory score",
    "IN_BASE_FLAG": "TRUE if the input enters the market's base calculation",
    "N_RANKED_MARKETS": "Markets ranked in the weight simulation (29 / 31 / 25)", "N_DRAWS": "Weight draws (10,000)",
    "MEAN_SENSITIVITY_SCORE": "Mean score across the weight draws", "SENSITIVITY_SCORE_STD": "Score standard deviation across the weight draws",
    "FIXED_TEST_WORST_RANK": "Worst rank across the named normalization, methodology and business tests",
}


def dictionary_row(table: str, col: str, dtype: str, docs: dict) -> dict:
    c = col.upper()
    if c.endswith("_FREQUENCY") or c.endswith("_SHARE") or c.endswith("_WEIGHT") or c == "ASSUMED_FAVORABLE_FRACTION":
        unit, fmt = "share (0-1)", "0.0%"
    elif "SCORE" in c and dtype in ("FLOAT", "NUMBER"):
        unit, fmt = "points (0-100)", "0.0"
    elif "RANK" in c and dtype in ("FLOAT", "NUMBER"):
        unit, fmt = "rank (1 = best)", "0"
    elif c.endswith("_PCT"):
        unit, fmt = "percent (0-100)", "0.0"
    elif c in ("LATITUDE", "LONGITUDE"):
        unit, fmt = "decimal degrees", "0.0000"
    elif c == "POPULATION_2025":
        unit, fmt = "persons", "#,0"
    elif dtype == "BOOLEAN":
        unit, fmt = "", "True/False"
    else:
        unit, fmt = "", ""
    key = "PK" if PRIMARY.get(table) == c else ("FK" if c in KEYS and table.startswith("PBI_FCT") or
                                                (c in KEYS and PRIMARY.get(table) != c) else "")
    desc = docs.get((table, c)) or TEXT.get(c) or KEYS.get(c) or c.lower().replace("_", " ").capitalize()
    hidden = key == "FK" or c in HIDE or (key == "PK" and c in ("MARKET_ID", "FEATURE_KEY"))
    return {"table": table, "column": c.lower(), "data_type": dtype, "business_name": c.replace("_", " ").title(),
            "description": desc, "unit": unit, "format": fmt, "key_flag": key,
            "visibility_recommendation": "HIDE" if hidden else "SHOW"}


if __name__ == "__main__":
    sys.exit(main())
