"""Phase 6.5: validate the curated evidence files against evidence/research_protocol.md.

Checks evidence/regulatory_evidence.csv, evidence/deployment_evidence.csv and
evidence/research_log.csv:
  * exact headers, unique IDs, ID format and mode / jurisdiction consistency;
  * every coded status is in the vocabulary of its legal dimension;
  * numeric dimensions carry a number and unit only when SPECIFIED;
  * provenance: every row has a source title, an http(s) URL, a source type and dates;
  * confidence discipline: HIGH needs a retrieved primary source; secondary-only evidence is LOW;
    absence findings are never HIGH;
  * coverage: every jurisdiction in the 35-market universe has every required dimension;
  * separation: regulatory rows never cite operator sources; deployment rows use only the
    deployment vocabulary and resolve to universe markets or say why not.

Exit code 1 on any failure. No Snowflake access; no scores, weights or rankings.

Usage (repository root, .venv active):
    python scripts/validate_evidence.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
AS_OF = "2026-10-05"

REG_COLS = ["evidence_id", "mode", "jurisdiction_type", "jurisdiction", "state_fips", "legal_dimension",
            "coded_status", "numeric_value", "unit", "effective_date", "evidence_as_of", "access_date",
            "source_title", "source_url", "source_authority", "source_type", "verification_status",
            "second_source_status", "second_source_title", "second_source_url", "confidence",
            "evidence_summary", "analyst_note"]
DEP_COLS = ["deployment_id", "operator", "mode", "reported_geography", "market_id", "market_name",
            "market_resolution", "resolution_note", "deployment_status", "service_type", "commercial_or_pilot",
            "driverless_or_supervised", "platform_partner", "announcement_date", "start_date", "end_date",
            "evidence_as_of", "source_title", "source_url", "source_type", "access_date", "verification_status",
            "notes"]
LOG_COLS = ["mode", "jurisdiction", "research_completed", "authoritative_source_checked",
            "second_source_checked", "unresolved_issue", "last_verified_date"]

STATES = {"AZ": "04", "CA": "06", "CO": "08", "DC": "11", "DE": "10", "FL": "12", "GA": "13", "IL": "17",
          "IN": "18", "KS": "20", "KY": "21", "MA": "25", "MD": "24", "MI": "26", "MN": "27", "MO": "29",
          "NC": "37", "NH": "33", "NJ": "34", "NV": "32", "NY": "36", "OH": "39", "OR": "41", "PA": "42",
          "SC": "45", "TN": "47", "TX": "48", "VA": "51", "WA": "53", "WI": "55", "WV": "54"}
MARKETS = {"12060", "12420", "12580", "14460", "16740", "16980", "17140", "17410", "18140", "19100", "19740",
           "19820", "26420", "26900", "28140", "29820", "31080", "33100", "33460", "34980", "35620", "36740",
           "37980", "38060", "38300", "38900", "40140", "40900", "41180", "41700", "41740", "41860", "42660",
           "45300", "47900"}

AUTH = ["AUTHORIZED_BY_STATUTE", "AUTHORIZED_WITH_PERMIT", "AUTHORIZED_BY_EXECUTIVE_ORDER"]
VOCAB = {
    "ROBOTAXI": {
        "RT_TESTING_AUTHORIZATION": AUTH + ["NO_SPECIFIC_STATUTE", "NOT_AUTHORIZED", "UNCLEAR"],
        "RT_DRIVERLESS_OPERATION": AUTH + ["TESTING_ONLY", "NO_SPECIFIC_STATUTE", "NOT_AUTHORIZED", "UNCLEAR"],
        "RT_COMMERCIAL_PASSENGER_SERVICE": ["AUTHORIZED_BY_STATUTE", "AUTHORIZED_WITH_PERMIT", "NO_SPECIFIC_FRAMEWORK",
                                            "NOT_AUTHORIZED", "UNCLEAR"],
        "RT_TNC_APPLICABILITY": ["AV_SPECIFIC_PROVISIONS", "TNC_LAW_APPLIES_GENERALLY", "NOT_ADDRESSED", "UNCLEAR"],
        "RT_SAFETY_DRIVER_REQUIREMENT": ["NOT_REQUIRED", "REQUIRED", "REQUIRED_FOR_TESTING_ONLY", "NOT_ADDRESSED",
                                         "UNCLEAR"],
        "RT_LOCAL_AUTHORITY": ["STATE_PREEMPTS_LOCAL", "LOCAL_MAY_REGULATE", "NOT_ADDRESSED", "UNCLEAR"],
        "RT_STATE_APPROVAL_REQUIRED": ["STATE_PERMIT_OR_APPROVAL_REQUIRED", "NOTICE_OR_SELF_CERTIFICATION",
                                       "NONE_REQUIRED", "NOT_ADDRESSED", "UNCLEAR"],
        "RT_INSURANCE_MINIMUM": ["SPECIFIED", "GENERAL_MOTOR_VEHICLE_RULES", "NOT_ADDRESSED"],
    },
    "SIDEWALK_DELIVERY": {
        "SW_PDD_LEGAL_STATUS": ["STATUTE_AUTHORIZES", "PILOT_ONLY", "NO_STATUTE", "STATUTE_PROHIBITS", "UNCLEAR"],
        "SW_SIDEWALK_AUTHORIZATION": ["AUTHORIZED", "AUTHORIZED_SUBJECT_TO_LOCAL", "NOT_AUTHORIZED", "NOT_ADDRESSED"],
        "SW_ROADWAY_AUTHORIZATION": ["AUTHORIZED", "SHOULDER_OR_EDGE_ONLY", "ONLY_IF_NO_SIDEWALK", "NOT_AUTHORIZED",
                                     "NOT_ADDRESSED"],
        "SW_MAX_WEIGHT": ["SPECIFIED", "NO_LIMIT_STATED", "NOT_ADDRESSED"],
        "SW_MAX_SPEED_SIDEWALK": ["SPECIFIED", "NO_LIMIT_STATED", "NOT_ADDRESSED"],
        "SW_MAX_SPEED_ROADWAY": ["SPECIFIED", "NOT_PERMITTED", "NO_LIMIT_STATED", "NOT_ADDRESSED"],
        "SW_OPERATOR_REQUIREMENT": ["REMOTE_OPERATOR_REQUIRED", "REMOTE_MONITORING_REQUIRED",
                                    "OPERATOR_LIABLE_NO_SUPERVISION_RULE", "NOT_ADDRESSED"],
        "SW_INSURANCE_MINIMUM": ["SPECIFIED", "NOT_ADDRESSED"],
        "SW_LOCAL_AUTHORITY": ["LOCAL_MAY_PROHIBIT", "LOCAL_MAY_REGULATE_NOT_PROHIBIT", "STATE_PREEMPTS_LOCAL",
                               "NOT_ADDRESSED"],
        "SW_REGISTRATION_OR_PERMIT": ["STATE_REQUIRED", "LOCAL_REQUIRED", "STATE_AND_LOCAL", "NONE", "NOT_ADDRESSED"],
    },
    "DRONE_DELIVERY": {
        "DR_FED_PART107": ["IN_FORCE"],
        "DR_FED_PART135_DELIVERY": ["IN_FORCE"],
        "DR_FED_BVLOS_FRAMEWORK": ["FINAL_RULE_IN_FORCE", "FINAL_RULE_NOT_YET_EFFECTIVE", "PROPOSED_RULE",
                                   "WAIVER_EXEMPTION_ONLY"],
        "DR_FED_AIRSPACE_AUTHORIZATION": ["IN_FORCE"],
        "DR_FED_REMOTE_ID": ["IN_FORCE"],
        "DR_FED_PREEMPTION_AIRSPACE": ["FEDERAL_AIRSPACE_AUTHORITY"],
        "DR_FED_DELIVERY_OPERATOR_AUTHORIZATIONS": ["IN_FORCE"],
        "DR_CRITICAL_INFRASTRUCTURE_RESTRICTION": ["STATUTE_RESTRICTS", "NO_STATUTE", "UNCLEAR"],
        "DR_STATE_PREEMPTION_OF_LOCAL": ["STATE_PREEMPTS_LOCAL", "LOCAL_MAY_REGULATE", "NOT_ADDRESSED"],
        "DR_UAS_SPECIFIC_PRIVACY_OR_TRESPASS": ["UAS_STATUTE_EXISTS", "NO_UAS_STATUTE"],
    },
}
NUMERIC_DIMS = {"RT_INSURANCE_MINIMUM": {"USD"}, "SW_MAX_WEIGHT": {"lb"}, "SW_MAX_SPEED_SIDEWALK": {"mph"},
                "SW_MAX_SPEED_ROADWAY": {"mph"}, "SW_INSURANCE_MINIMUM": {"USD"},
                "DR_CRITICAL_INFRASTRUCTURE_RESTRICTION": {"ft"}}
# Absence of a statute or provision. NO_LIMIT_STATED is NOT here: it is a positive reading of an
# existing statute that sets no limit, and can be HIGH when that statute was read in full.
ABSENCE = {"NO_SPECIFIC_STATUTE", "NO_STATUTE", "NOT_ADDRESSED", "NO_SPECIFIC_FRAMEWORK", "NO_UAS_STATUTE"}
REG_SOURCE_TYPES = {"STATE_STATUTE", "STATE_REGULATION", "STATE_AGENCY", "STATE_EXECUTIVE", "FEDERAL_STATUTE", "FEDERAL_REGULATION",
                    "FEDERAL_AGENCY", "MUNICIPAL_CODE", "REGULATOR_ORDER", "SECONDARY"}
DEP_SOURCE_TYPES = {"OPERATOR_OFFICIAL", "REGULATOR_ORDER", "STATE_AGENCY", "SECONDARY"}
VERIFICATION = {"VERIFIED_PRIMARY", "PRIMARY_CITED_NOT_RETRIEVED", "SECONDARY_ONLY"}
SECOND = {"VERIFIED_CONSISTENT", "VERIFIED_CONFLICT", "NOT_PERFORMED"}
CONF = {"HIGH", "MEDIUM", "LOW"}
DEP_STATUS = {"ANNOUNCED", "TESTING", "PILOT", "LIMITED_COMMERCIAL", "COMMERCIAL", "PAUSED", "ENDED", "UNKNOWN"}
DEP_RESOLUTION = {"WITHIN_MARKET_PARTIAL", "CITY_ONLY", "CAMPUS_OR_SITE", "MULTI_MARKET", "OUTSIDE_UNIVERSE",
                  "UNRESOLVED"}
DEP_COMMERCIAL = {"COMMERCIAL", "PILOT", "NON_COMMERCIAL_TESTING", "UNKNOWN"}
DEP_DRIVER = {"DRIVERLESS", "SAFETY_DRIVER", "MIXED", "UNKNOWN", ""}
PREFIX = {"ROBOTAXI": "RT", "SIDEWALK_DELIVERY": "SW", "DRONE_DELIVERY": "DR"}
REQUIRED_STATE_DIMS = {
    "ROBOTAXI": list(VOCAB["ROBOTAXI"]),
    "DRONE_DELIVERY": ["DR_CRITICAL_INFRASTRUCTURE_RESTRICTION", "DR_STATE_PREEMPTION_OF_LOCAL",
                       "DR_UAS_SPECIFIC_PRIVACY_OR_TRESPASS"],
}
SW_NO_STATUTE_DIMS = ["SW_PDD_LEGAL_STATUS", "SW_SIDEWALK_AUTHORIZATION", "SW_ROADWAY_AUTHORIZATION",
                      "SW_LOCAL_AUTHORITY"]
FEDERAL_DIMS = ["DR_FED_PART107", "DR_FED_PART135_DELIVERY", "DR_FED_BVLOS_FRAMEWORK",
                "DR_FED_AIRSPACE_AUTHORIZATION", "DR_FED_REMOTE_ID", "DR_FED_PREEMPTION_AIRSPACE"]
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def check_regulatory(df: pd.DataFrame, errs: list[str]) -> None:
    if list(df.columns) != REG_COLS:
        errs.append(f"regulatory header mismatch: {list(df.columns)}")
        return
    for c in ("evidence_id",):
        d = df[df[c].duplicated()][c].tolist()
        if d:
            errs.append(f"duplicate evidence_id: {d[:10]}")
    for r in df.itertuples(index=False):
        e = r.evidence_id
        def bad(msg):
            errs.append(f"{e}: {msg}")
        if r.mode not in VOCAB:
            bad(f"mode {r.mode}"); continue
        if not re.match(rf"^{PREFIX[r.mode]}-[A-Z]{{2}}(-[A-Z0-9]+)?-\d{{2,3}}$", e):
            bad("evidence_id format")
        if r.jurisdiction_type == "FEDERAL":
            if r.jurisdiction != "US" or r.state_fips:
                bad("federal row must be jurisdiction US, blank state_fips")
        elif r.jurisdiction_type == "STATE":
            if r.jurisdiction not in STATES:
                bad(f"jurisdiction {r.jurisdiction} outside the 35-market states")
            elif r.state_fips != STATES[r.jurisdiction]:
                bad(f"state_fips {r.state_fips} != {STATES[r.jurisdiction]}")
        elif r.jurisdiction_type == "LOCAL":
            if r.jurisdiction[:2] not in STATES or not re.match(r"^[A-Z]{2}-[A-Z0-9_]+$", r.jurisdiction):
                bad(f"local jurisdiction {r.jurisdiction} must look like XX-PLACE in a universe state")
        else:
            bad(f"jurisdiction_type {r.jurisdiction_type}")
        dims = VOCAB[r.mode]
        if r.legal_dimension not in dims:
            bad(f"dimension {r.legal_dimension} not in {r.mode} vocabulary"); continue
        if r.coded_status not in dims[r.legal_dimension]:
            bad(f"status {r.coded_status} not allowed for {r.legal_dimension}")
        if r.legal_dimension.startswith("DR_FED") != (r.jurisdiction_type == "FEDERAL"):
            bad("federal dimensions only on federal rows")
        if r.legal_dimension in NUMERIC_DIMS and r.coded_status in ("SPECIFIED", "STATUTE_RESTRICTS") and r.numeric_value:
            try:
                float(r.numeric_value)
            except ValueError:
                bad(f"numeric_value {r.numeric_value!r} not a number")
            if r.unit not in NUMERIC_DIMS[r.legal_dimension]:
                bad(f"unit {r.unit!r} not in {NUMERIC_DIMS[r.legal_dimension]}")
        elif r.coded_status == "SPECIFIED":
            bad("SPECIFIED requires numeric_value")
        elif r.numeric_value and r.legal_dimension not in NUMERIC_DIMS:
            bad("numeric_value on a non-numeric dimension")
        for col in ("effective_date",):
            v = getattr(r, col)
            if v and not DATE.match(v):
                bad(f"{col} {v!r} not YYYY-MM-DD")
        if r.evidence_as_of != AS_OF:
            bad(f"evidence_as_of {r.evidence_as_of}")
        if not DATE.match(r.access_date):
            bad(f"access_date {r.access_date!r}")
        if not r.source_title.strip():
            bad("missing source_title")
        if not re.match(r"^https?://", r.source_url):
            bad(f"source_url {r.source_url!r}")
        if r.source_type not in REG_SOURCE_TYPES:
            bad(f"source_type {r.source_type} (operator sources are not regulatory evidence)")
        if r.verification_status not in VERIFICATION:
            bad(f"verification_status {r.verification_status}")
        if r.second_source_status not in SECOND:
            bad(f"second_source_status {r.second_source_status}")
        if r.second_source_status != "NOT_PERFORMED" and not re.match(r"^https?://", r.second_source_url):
            bad("second source claimed without URL")
        if r.confidence not in CONF:
            bad(f"confidence {r.confidence}")
        if r.confidence == "HIGH" and (r.verification_status != "VERIFIED_PRIMARY" or r.source_type == "SECONDARY"):
            bad("HIGH confidence requires a retrieved primary source")
        if r.verification_status == "SECONDARY_ONLY" and r.confidence != "LOW":
            bad("secondary-only evidence must be LOW confidence")
        if r.coded_status in ABSENCE and r.confidence == "HIGH":
            bad("absence findings cannot be HIGH confidence")
        if not r.evidence_summary.strip():
            bad("missing evidence_summary")


def check_coverage(df: pd.DataFrame, errs: list[str]) -> None:
    st = df[df.jurisdiction_type == "STATE"]
    for mode, dims in REQUIRED_STATE_DIMS.items():
        for j in STATES:
            have = set(st[(st["mode"] == mode) & (st.jurisdiction == j)].legal_dimension)
            miss = [d for d in dims if d not in have]
            if miss:
                errs.append(f"coverage {mode} {j}: missing {miss}")
    sw = st[st["mode"] == "SIDEWALK_DELIVERY"]
    for j in STATES:
        rows = sw[sw.jurisdiction == j]
        status = rows[rows.legal_dimension == "SW_PDD_LEGAL_STATUS"].coded_status.tolist()
        if len(status) != 1:
            errs.append(f"coverage SIDEWALK {j}: expected one SW_PDD_LEGAL_STATUS row, found {len(status)}")
            continue
        need = list(VOCAB["SIDEWALK_DELIVERY"]) if status[0] in ("STATUTE_AUTHORIZES", "PILOT_ONLY") else SW_NO_STATUTE_DIMS
        miss = [d for d in need if d not in set(rows.legal_dimension)]
        if miss:
            errs.append(f"coverage SIDEWALK {j} ({status[0]}): missing {miss}")
    fed = set(df[df.jurisdiction_type == "FEDERAL"].legal_dimension)
    miss = [d for d in FEDERAL_DIMS if d not in fed]
    if miss:
        errs.append(f"coverage FEDERAL: missing {miss}")


def check_deployment(df: pd.DataFrame, errs: list[str]) -> None:
    if list(df.columns) != DEP_COLS:
        errs.append(f"deployment header mismatch: {list(df.columns)}")
        return
    d = df[df.deployment_id.duplicated()].deployment_id.tolist()
    if d:
        errs.append(f"duplicate deployment_id: {d[:10]}")
    for r in df.itertuples(index=False):
        e = r.deployment_id
        def bad(msg):
            errs.append(f"{e}: {msg}")
        if r.mode not in PREFIX or not re.match(rf"^DEP-{PREFIX.get(r.mode, 'XX')}-\d{{3}}$", e):
            bad("deployment_id / mode")
        if r.deployment_status not in DEP_STATUS:
            bad(f"deployment_status {r.deployment_status}")
        if r.market_resolution not in DEP_RESOLUTION:
            bad(f"market_resolution {r.market_resolution}")
        if r.market_id:
            if r.market_id not in MARKETS:
                bad(f"market_id {r.market_id} not in the universe")
        elif r.market_resolution not in ("OUTSIDE_UNIVERSE", "UNRESOLVED", "MULTI_MARKET"):
            bad("blank market_id needs OUTSIDE_UNIVERSE, UNRESOLVED or MULTI_MARKET")
        if r.commercial_or_pilot not in DEP_COMMERCIAL:
            bad(f"commercial_or_pilot {r.commercial_or_pilot}")
        if r.mode == "ROBOTAXI" and r.driverless_or_supervised not in DEP_DRIVER - {""}:
            bad(f"driverless_or_supervised {r.driverless_or_supervised!r}")
        for col in ("announcement_date", "start_date", "end_date"):
            v = getattr(r, col)
            if v and not DATE.match(v):
                bad(f"{col} {v!r}")
        if r.deployment_status == "ENDED" and not r.end_date and not re.search(
                r"end|clos|wind|cancel|shut|discontinu|terminat", r.notes.lower()):
            bad("ENDED without end_date or a note")
        if r.evidence_as_of != AS_OF:
            bad(f"evidence_as_of {r.evidence_as_of}")
        if not re.match(r"^https?://", r.source_url) or not r.source_title.strip():
            bad("missing source title/url")
        if r.source_type not in DEP_SOURCE_TYPES:
            bad(f"source_type {r.source_type}")
        if r.verification_status not in VERIFICATION:
            bad(f"verification_status {r.verification_status}")


def check_contract(con: pd.DataFrame, reg: pd.DataFrame, errs: list[str]) -> None:
    """config/regulatory_feature_contract.csv: every dimension and favorable status is in the protocol
    vocabulary, federal dimensions are CONTEXT_ONLY, and every active candidate has evidence for every
    universe jurisdiction (so Phase 7 can map every market). No weight, score or rank column may exist."""
    if any(k in c.lower() for c in con.columns for k in ("weight", "score", "rank")):
        errs.append("contract has a weight/score/rank column")
    pdd_absent = set(reg[(reg.legal_dimension == "SW_PDD_LEGAL_STATUS")
                         & ~reg.coded_status.isin(["STATUTE_AUTHORIZES", "PILOT_ONLY"])].jurisdiction)
    for r in con.itertuples(index=False):
        voc = VOCAB.get(r.mode, {}).get(r.legal_dimension)
        if voc is None:
            errs.append(f"contract {r.feature_id}: unknown dimension {r.legal_dimension}")
            continue
        bad = [s for s in r.favorable_statuses.split("|") if s and s not in voc]
        if bad:
            errs.append(f"contract {r.feature_id}: favorable statuses not in vocabulary {bad}")
        if r.legal_dimension.startswith("DR_FED") and r.candidate_status != "CONTEXT_ONLY":
            errs.append(f"contract {r.feature_id}: federal dimension must be CONTEXT_ONLY")
        if r.active_candidate_flag == "TRUE":
            if not r.favorable_statuses or r.direction in ("CONTEXT_DEPENDENT_OR_DEFER", "NOT_APPLICABLE"):
                errs.append(f"contract {r.feature_id}: active candidate needs favorable statuses and a direction")
            have = set(reg[(reg["mode"] == r.mode) & (reg.legal_dimension == r.legal_dimension)
                           & (reg.jurisdiction_type == "STATE")].jurisdiction)
            need = set(STATES) - (pdd_absent if r.legal_dimension == "SW_MAX_WEIGHT" else set())
            if need - have:
                errs.append(f"contract {r.feature_id}: no evidence for {sorted(need - have)}")


def main() -> int:
    errs: list[str] = []
    reg = read(EVID / "regulatory_evidence.csv")
    dep = read(EVID / "deployment_evidence.csv")
    log = read(EVID / "research_log.csv")
    con_path = ROOT / "config" / "regulatory_feature_contract.csv"
    if con_path.exists():
        con = read(con_path)
        check_contract(con, reg, errs)
        print("contract:", con.groupby(["mode", "candidate_status"]).size().to_dict())
    check_regulatory(reg, errs)
    check_coverage(reg, errs)
    check_deployment(dep, errs)
    if list(log.columns) != LOG_COLS:
        errs.append(f"research log header mismatch: {list(log.columns)}")
    else:
        for mode in ("ROBOTAXI", "SIDEWALK_DELIVERY", "DRONE_DELIVERY"):
            miss = sorted(set(STATES) - set(log[log["mode"] == mode].jurisdiction))
            if miss:
                errs.append(f"research log {mode} missing {miss}")
    print(f"regulatory rows: {len(reg)} | deployment rows: {len(dep)} | research log rows: {len(log)}")
    print("regulatory by mode:", reg["mode"].value_counts().to_dict())
    print("confidence:", reg.confidence.value_counts().to_dict())
    print("verification:", reg.verification_status.value_counts().to_dict())
    print("second source:", reg.second_source_status.value_counts().to_dict())
    print("deployment status by mode:", dep.groupby(["mode", "deployment_status"]).size().to_dict())
    if errs:
        print(f"\nFAIL: {len(errs)} problem(s)")
        for e in errs[:200]:
            print("  -", e)
        return 1
    print("\nPASS: evidence files conform to evidence/research_protocol.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
