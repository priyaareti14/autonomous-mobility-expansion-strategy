# Regulatory Handoff: Data Contract for Phase 6.5

**Status:** Phase 6 deliverable; **satisfied by Phase 6.5** (see §6) · **Last updated:** 2026-10-05

## 1. Purpose and boundaries

Component **C4 Regulatory & Autonomy Readiness** is empty in every mode mart. This document fixes the exact data Phase 6.5 (Regulatory & Deployment Evidence Curation) must deliver before C4 can be designed.

It builds on:
- the evidence framework in [data_sources.md](data_sources.md) §7 (sources S-28 to S-33)
- the curation checklist in [feature_audit.md](feature_audit.md) §13
- the sequencing decision in [project_scope.md](project_scope.md) §14

**Rules carried forward:**
- Phase 6 populates **nothing** and scores **nothing**. No regulatory value, ordinal level or proxy exists in the warehouse.
- Regulatory evidence becomes a scored input only after its framework and measurement rules are finalized (Phase 7 design).
- **Deployment evidence (S-35 to S-39) is EXTERNAL VALIDATION only.** It must never fill a C4 field, select a feature or set a weight (A-015).
- Every record needs a primary-source citation, an effective date, an access date and a verification status (A-011). Discovery aids such as NCSL summaries are not citations.

## 2. Common record structure (every mode)

**Grain:** one record per **jurisdiction × mode × legal_dimension**, as of a stated date.

| Field | Type | Required | Definition |
|---|---|---|---|
| `evidence_id` | string | yes | Stable identifier |
| `mode` | enum | yes | ROBOTAXI / SIDEWALK_DELIVERY / DRONE_DELIVERY |
| `jurisdiction_level` | enum | yes | FEDERAL / STATE / LOCAL |
| `jurisdiction_code` | string | yes | `US`, a state USPS code, or a local FIPS / place code |
| `legal_dimension` | enum | yes | One of the mode dimensions in §3 |
| `status_value` | enum or number | yes | The dimension's coded value (vocabularies in §3). `UNKNOWN` is allowed and must be explicit, never blank |
| `status_unit` | string | for numeric | e.g. `lb`, `mph` |
| `legal_instrument` | string | yes | Statute, regulation, order or ordinance identifier (e.g. bill number and chapter) |
| `citation` | string | yes | Primary-source reference |
| `source_url` | string | yes | Official URL of the primary source |
| `effective_date` | date | yes | Date the provision took effect. A future date is allowed and flagged |
| `sunset_or_expiry_date` | date | no | If the provision lapses |
| `evidence_date` | date | yes | Date of the document relied on |
| `accessed_date` | date | yes | Date the source was read |
| `verification_status` | enum | yes | VERIFIED_PRIMARY / VERIFIED_SECONDARY / UNVERIFIED |
| `evidence_confidence` | enum | yes | HIGH / MEDIUM / LOW, with a rationale |
| `confidence_rationale` | string | yes | Why that confidence |
| `notes` | string | no | Ambiguities, pending litigation, amendments |

## 3. Mode-specific legal dimensions

### 3.1 Robotaxi

| `legal_dimension` | Values (vocabulary) | Notes |
|---|---|---|
| `TESTING_AUTHORIZATION` | NOT_ADDRESSED / PERMITTED_WITH_SAFETY_DRIVER / PERMITTED_DRIVERLESS / PROHIBITED | |
| `DRIVERLESS_DEPLOYMENT_AUTHORIZATION` | NOT_ADDRESSED / AUTHORIZED / AUTHORIZED_WITH_PERMIT / PROHIBITED | No human operator on board |
| `COMMERCIAL_PASSENGER_FRAMEWORK` | NONE / AV_SPECIFIC_PERMIT / GENERAL_FRAMEWORK / PROHIBITED | Fare-charging service authorization and the agency responsible |
| `TNC_APPLICABILITY` | APPLIES / EXEMPT / AV_SPECIFIC_RULES / NOT_ADDRESSED | Whether TNC statutes cover AV fleets |
| `STATE_PREEMPTION_LOCAL_AUTHORITY` | STATE_PREEMPTS / SHARED / LOCAL_AUTHORITY / NOT_ADDRESSED | Can cities restrict or permit AV operation? |
| `INSURANCE_REQUIREMENT` | number (USD) or NOT_ADDRESSED | Minimum liability |
| `REPORTING_REQUIREMENT` | NONE / CRASH_REPORTING / OPERATIONAL_REPORTING | State-level, in addition to NHTSA SGO (federal context) |

### 3.2 Sidewalk delivery robot (personal delivery device, PDD)

| `legal_dimension` | Values (vocabulary) | Notes |
|---|---|---|
| `PDD_STATUTE_STATUS` | NO_STATUTE / STATUTE_AUTHORIZES / STATUTE_RESTRICTS / PILOT_ONLY | |
| `WEIGHT_LIMIT` | number (lb) or NO_LIMIT_STATED | Unladen and/or loaded, as defined |
| `SPEED_LIMIT_SIDEWALK` | number (mph) | |
| `SPEED_LIMIT_ROADWAY` | number (mph) or NOT_PERMITTED | |
| `OPERATING_AREA_AUTHORIZATION` | SIDEWALK / SIDEWALK_AND_CROSSWALK / ROAD_SHOULDER / ROADWAY | Where a PDD may operate |
| `OPERATOR_REQUIREMENT` | NONE / REMOTE_MONITORING / REMOTE_OPERATOR_REQUIRED | Human supervision |
| `INSURANCE_REQUIREMENT` | number (USD) or NOT_ADDRESSED | |
| `LOCAL_AUTHORITY` | STATE_PREEMPTS / LOCAL_MAY_REGULATE / LOCAL_MAY_PROHIBIT | |
| `REGISTRATION_OR_PERMIT` | NONE / STATE / LOCAL / BOTH | |

### 3.3 Drone delivery

| `legal_dimension` | Values (vocabulary) | Notes |
|---|---|---|
| `FEDERAL_OPERATING_FRAMEWORK` | Text status of Part 107 / Part 135 / BVLOS rulemaking | **Federal and uniform**: one `US` record, context only (A-022), not differentiating |
| `STATE_CRITICAL_INFRASTRUCTURE_RESTRICTION` | NONE / RESTRICTION_EXISTS | Overflight restrictions near designated facilities |
| `STATE_LOCAL_PREEMPTION` | STATE_PREEMPTS_LOCAL / LOCAL_MAY_REGULATE / NOT_ADDRESSED | Only where legally relevant: airspace is federal, while land use, takeoff and landing are local |
| `STATE_DRONE_PRIVACY_TRESPASS` | NONE / LAW_EXISTS | If it affects delivery operations |
| `LOCAL_TAKEOFF_LANDING_RESTRICTION` | NONE / RESTRICTION_EXISTS / UNKNOWN | Only where a local record exists |

The drone airspace candidates F49 (UAS Facility Map share) and F50 (national-security UAS restrictions) are C5 PROXY candidates in data_sources.md §3. They are not ingested, not part of C4, and not regulatory evidence.

## 4. Market mapping requirement (A-012; resolved in Phase 6.5, see §6)

- 11 of the 35 markets span more than one state.
- `CORE.BRG_MARKET_STATE` is **preserved unchanged** (market × state with observed PEP 2025 population shares) and is the input for any mapping.
- Phase 6 does **not** choose the method.

**Phase 6.5 must evaluate and document** at least these options:
- dominant state
- population-weighted state shares
- most-restrictive state
- most-permissive state
- principal-city state

Each option needs a sensitivity comparison. Examples of balanced markets are Washington (VA 49% / MD 39% / DC 11%), Kansas City (MO 59% / KS 41%), New York (NY 65% / NJ 35%) and Philadelphia (PA 67% / NJ 22% / DE 9%).

## 5. Acceptance criteria for Phase 6.5 output

1. **Coverage:** every state appearing in `BRG_MARKET_STATE`, plus `US`, has a record for every dimension in §3 for each mode. `UNKNOWN` is explicit; there are no blanks.
2. **Evidence:** every record has a primary-source citation, `effective_date`, `accessed_date`, `verification_status` and `evidence_confidence`.
3. **No proxies:** no regulatory field is derived from deployments, company announcements or unrelated socioeconomic variables.
4. **Landing:** records land through the existing architecture: registry, RAW, META audit, checksum, dbt source, staging, tests, lineage. No manual table edits.
5. **Mapping:** the A-012 state → market method is documented with its sensitivity before any C4 feature is created.
6. **Measurement rules:** how coded values become an ordinal C4 measure is defined and approved in Phase 7. Until then, the mode marts keep no C4 column, which `assert_mode_marts_match_feature_contract` enforces.

## 6. Phase 6.5 outcome (2026-10-05)

Evidence was curated in `evidence/regulatory_evidence.csv` (582 records). The methodology is in [regulatory_methodology.md](regulatory_methodology.md) and open issues are in [regulatory_ambiguities.md](regulatory_ambiguities.md).

**Refinements to this contract:**
- **Field names.** The record schema follows `evidence/research_protocol.md` §2, which carries this contract's §2 fields under the protocol's names: `coded_status`, `source_type`, `second_source_status`, `confidence`.
- **Robotaxi vocabularies** gained `AUTHORIZED_BY_EXECUTIVE_ORDER`, `NO_SPECIFIC_STATUTE` and `NO_SPECIFIC_FRAMEWORK`, so that absence is never coded as prohibition.
- **Sidewalk** speed was split into sidewalk and roadway limits.
- **Drone** dimensions were reduced to three state dimensions plus seven federal CONTEXT_ONLY dimensions; `LOCAL_TAKEOFF_LANDING_RESTRICTION` was folded into `DR_STATE_PREEMPTION_OF_LOCAL`.

**Acceptance criteria (§5):**

| # | Criterion | Result |
|---|---|---|
| 1 | Coverage: every state in `BRG_MARKET_STATE` plus US, with explicit codes and no blanks | **Met**: 31 jurisdictions plus US; `validate_evidence.py` coverage check PASS |
| 2 | Evidence fields on every record | **Met**: citation, URL, effective date (where known), access date, verification status and confidence on all 582. 75 records are not primary-retrieved, and say so |
| 3 | No proxies (no deployment- or socioeconomic-derived codes) | **Met**: operator sources are rejected as regulatory evidence; deployment evidence is in a separate file |
| 4 | Landing through registry / RAW / META / dbt | **Deferred to Phase 7 preparation**, as permitted by the Phase 6.5 brief (Step 19). The evidence is version-controlled and validated; Snowflake landing waits for the Phase 7 measurement rules. **Phase 7:** landed as deterministic dbt seeds generated from `evidence/` (`scripts/build_regulatory_seed.py`), not through RAW (A-057; [readiness_model.md](readiness_model.md) §3) |
| 5 | A-012 method documented with sensitivity | **Met**: dimension-specific contract (`POPULATION_SHARE_BY_STATUS`; `MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES`; `CONTEXT_ONLY`) with the method comparison in `outputs/phase65/a012_method_comparison.csv` |
| 6 | Ordinal measurement rules only in Phase 7; no C4 column in the marts | **Met**: `config/regulatory_feature_contract.csv` lists candidates and favorable statuses only; `assert_mode_marts_match_feature_contract` still passes |
