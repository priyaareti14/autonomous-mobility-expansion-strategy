# Evidence Research Protocol (Phase 6.5)

This protocol governs every regulatory and deployment evidence record in `evidence/`. It is the coding contract: records that do not follow it are rejected at QA (`scripts/validate_evidence.py`).

- `REGULATORY_EVIDENCE_AS_OF = 2026-10-05`
- `DEPLOYMENT_EVIDENCE_AS_OF = 2026-10-05`

These are the same date but separate concepts. Legal status is coded as in force, or enacted with a known effective date, on that date. Deployment status is coded as publicly evidenced on that date.

This is analytical classification of public evidence for market comparison. **It is not legal advice.**

## 1. Source hierarchy

Use the highest available level. `source_type` must name the level actually used.

| Rank | `source_type` | Examples |
|---|---|---|
| 1 | `STATE_STATUTE` | Official state code or legislature site (session law or codified section) |
| 2 | `STATE_REGULATION` / `STATE_AGENCY` | Administrative code; DMV / DOT / PUC program page or rule |
| 3 | `STATE_EXECUTIVE` | Governor's executive order; official legislative bill page (enrolled text) |
| 4 | `FEDERAL_STATUTE` / `FEDERAL_REGULATION` / `FEDERAL_AGENCY` | U.S. Code (e.g. 49 U.S.C. 40103), eCFR, Federal Register, FAA, NHTSA |
| 5 | `MUNICIPAL_CODE` | Official city code or transportation authority, only where local authority materially matters |
| 6 | `REGULATOR_ORDER` | Permit or order databases (e.g. CPUC decisions, CA DMV permit lists) |
| 7 | `OPERATOR_OFFICIAL` | Operator newsroom or service page. **Deployment evidence only** |
| — | `SECONDARY` | NCSL, IIHS, law-firm or academic reviews. Discovery and cross-checking only. Never the sole basis of a code when a primary source exists |

**Rules:**
- **Fetch before coding.** `source_url` must be a page actually opened, and `evidence_summary` must paraphrase what it says. If an official site blocks automated access (common for Texas, Georgia and some code hosts), try the legislature's own site, the official PDF, or the enrolled bill. If only the citation can be identified, set `verification_status = PRIMARY_CITED_NOT_RETRIEVED`; confidence then cannot be HIGH.
- **Paraphrase concisely** and cite the section, e.g. "Tex. Transp. Code §545.453". Do not paste long statutory text; a quoted phrase of 25 words or fewer is allowed.
- **Absence is not prohibition.** If no statute addresses a dimension, code `NO_SPECIFIC_STATUTE` or `NOT_ADDRESSED` (per the vocabulary), never `NOT_AUTHORIZED`. Record how absence was checked in `analyst_note` (e.g. "official code search for 'autonomous', 'automated driving system'; NCSL database cross-check").
- **Currentness.** Prefer the current codified text. Check for amendments or repeal after any summary's date. Record `effective_date` as YYYY-MM-DD where known; if only the year is known, use YYYY-01-01 and say so in the note.

## 2. Regulatory record schema (`evidence/regulatory_evidence.csv`)

One row per **jurisdiction × legal_dimension** (plus extra rows only where one dimension genuinely needs two sources).

| Column | Rule |
|---|---|
| `evidence_id` | `RT-<USPS>-<NN>`, `SW-<USPS>-<NN>`, `DR-<USPS>-<NN>`, `DR-US-<NN>` |
| `mode` | `ROBOTAXI` / `SIDEWALK_DELIVERY` / `DRONE_DELIVERY` |
| `jurisdiction_type` | `STATE` (DC counts as STATE-equivalent) / `FEDERAL` / `LOCAL` |
| `jurisdiction` | USPS code, or `US` |
| `state_fips` | 2-digit, blank for US |
| `legal_dimension` | From §3 |
| `coded_status` | From the dimension's vocabulary in §3 (exact spelling) |
| `numeric_value`, `unit` | Only for numeric dimensions (lb, mph, USD, ft); else blank |
| `effective_date` | YYYY-MM-DD or blank if unknown |
| `evidence_as_of` | 2026-10-05 |
| `access_date` | Date the source was opened (2026-10-05) |
| `source_title` | e.g. "Fla. Stat. §316.85 Autonomous vehicles; operation" |
| `source_url` | Primary URL actually used |
| `source_authority` | e.g. "Florida Legislature (Online Sunshine)" |
| `source_type` | From §1 |
| `verification_status` | `VERIFIED_PRIMARY` (primary text read and confirms the code) / `PRIMARY_CITED_NOT_RETRIEVED` / `SECONDARY_ONLY` |
| `second_source_status` | `VERIFIED_CONSISTENT` / `VERIFIED_CONFLICT` / `NOT_PERFORMED` |
| `second_source_title`, `second_source_url` | If checked |
| `confidence` | `HIGH`: primary source directly establishes the code. `MEDIUM`: primary exists but needs synthesis or is partly ambiguous; also every absence finding. `LOW`: incomplete, conflicting, outdated or secondary-dependent |
| `evidence_summary` | 1–3 sentence paraphrase with section cite |
| `analyst_note` | Interpretation, ambiguity, how absence was checked, pending bills |

## 3. Legal dimensions and coded vocabularies

### 3.1 Robotaxi (state level)

| `legal_dimension` | Vocabulary | Meaning |
|---|---|---|
| `RT_TESTING_AUTHORIZATION` | `AUTHORIZED_BY_STATUTE`, `AUTHORIZED_WITH_PERMIT`, `AUTHORIZED_BY_EXECUTIVE_ORDER`, `NO_SPECIFIC_STATUTE`, `NOT_AUTHORIZED`, `UNCLEAR` | May AVs be tested on public roads? |
| `RT_DRIVERLESS_OPERATION` | `AUTHORIZED_BY_STATUTE`, `AUTHORIZED_WITH_PERMIT`, `AUTHORIZED_BY_EXECUTIVE_ORDER`, `TESTING_ONLY`, `NO_SPECIFIC_STATUTE`, `NOT_AUTHORIZED`, `UNCLEAR` | May a vehicle operate with **no human driver on board**? |
| `RT_COMMERCIAL_PASSENGER_SERVICE` | `AUTHORIZED_BY_STATUTE`, `AUTHORIZED_WITH_PERMIT`, `NO_SPECIFIC_FRAMEWORK`, `NOT_AUTHORIZED`, `UNCLEAR` | May driverless AVs carry paying passengers? |
| `RT_TNC_APPLICABILITY` | `AV_SPECIFIC_PROVISIONS`, `TNC_LAW_APPLIES_GENERALLY`, `NOT_ADDRESSED`, `UNCLEAR` | Does TNC / for-hire law address AV fleets? |
| `RT_SAFETY_DRIVER_REQUIREMENT` | `NOT_REQUIRED`, `REQUIRED`, `REQUIRED_FOR_TESTING_ONLY`, `NOT_ADDRESSED`, `UNCLEAR` | Is a human safety driver legally required? |
| `RT_LOCAL_AUTHORITY` | `STATE_PREEMPTS_LOCAL`, `LOCAL_MAY_REGULATE`, `NOT_ADDRESSED`, `UNCLEAR` | Can cities restrict AV operation or AV for-hire service? |
| `RT_STATE_APPROVAL_REQUIRED` | `STATE_PERMIT_OR_APPROVAL_REQUIRED`, `NOTICE_OR_SELF_CERTIFICATION`, `NONE_REQUIRED`, `NOT_ADDRESSED`, `UNCLEAR` | What state approval precedes driverless deployment? |
| `RT_INSURANCE_MINIMUM` | `SPECIFIED` (numeric_value USD per incident or aggregate, see note), `GENERAL_MOTOR_VEHICLE_RULES`, `NOT_ADDRESSED` | AV-specific minimum liability coverage |

### 3.2 Sidewalk delivery robot / personal delivery device (state level)

| `legal_dimension` | Vocabulary |
|---|---|
| `SW_PDD_LEGAL_STATUS` | `STATUTE_AUTHORIZES`, `PILOT_ONLY`, `NO_STATUTE`, `STATUTE_PROHIBITS`, `UNCLEAR` |
| `SW_SIDEWALK_AUTHORIZATION` | `AUTHORIZED`, `AUTHORIZED_SUBJECT_TO_LOCAL`, `NOT_AUTHORIZED`, `NOT_ADDRESSED` |
| `SW_ROADWAY_AUTHORIZATION` | `AUTHORIZED`, `SHOULDER_OR_EDGE_ONLY`, `ONLY_IF_NO_SIDEWALK`, `NOT_AUTHORIZED`, `NOT_ADDRESSED` |
| `SW_MAX_WEIGHT` | `SPECIFIED` (numeric_value lb; note whether cargo is excluded), `NO_LIMIT_STATED`, `NOT_ADDRESSED` |
| `SW_MAX_SPEED_SIDEWALK` | `SPECIFIED` (numeric_value mph), `NO_LIMIT_STATED`, `NOT_ADDRESSED` |
| `SW_MAX_SPEED_ROADWAY` | `SPECIFIED` (numeric_value mph), `NOT_PERMITTED`, `NO_LIMIT_STATED`, `NOT_ADDRESSED` |
| `SW_OPERATOR_REQUIREMENT` | `REMOTE_OPERATOR_REQUIRED`, `REMOTE_MONITORING_REQUIRED`, `OPERATOR_LIABLE_NO_SUPERVISION_RULE`, `NOT_ADDRESSED` |
| `SW_INSURANCE_MINIMUM` | `SPECIFIED` (numeric_value USD), `NOT_ADDRESSED` |
| `SW_LOCAL_AUTHORITY` | `LOCAL_MAY_PROHIBIT`, `LOCAL_MAY_REGULATE_NOT_PROHIBIT`, `STATE_PREEMPTS_LOCAL`, `NOT_ADDRESSED` |
| `SW_REGISTRATION_OR_PERMIT` | `STATE_REQUIRED`, `LOCAL_REQUIRED`, `STATE_AND_LOCAL`, `NONE`, `NOT_ADDRESSED` |

If a state has **no PDD statute**, record `SW_PDD_LEGAL_STATUS = NO_STATUTE`, plus one row each for sidewalk, roadway and local authority coded `NOT_ADDRESSED`, with notes on general pedestrian/vehicle law. The numeric dimensions are omitted.

### 3.3 Drone delivery

**Federal (`jurisdiction = US`; all CONTEXT_ONLY because they are identical in every market):**

| `legal_dimension` | Vocabulary |
|---|---|
| `DR_FED_PART107` | `IN_FORCE` |
| `DR_FED_PART135_DELIVERY` | `IN_FORCE` |
| `DR_FED_BVLOS_FRAMEWORK` | `FINAL_RULE_IN_FORCE`, `FINAL_RULE_NOT_YET_EFFECTIVE`, `PROPOSED_RULE`, `WAIVER_EXEMPTION_ONLY` |
| `DR_FED_AIRSPACE_AUTHORIZATION` | `IN_FORCE` (LAANC / Part 107 controlled-airspace authorization) |
| `DR_FED_REMOTE_ID` | `IN_FORCE` |
| `DR_FED_PREEMPTION_AIRSPACE` | `FEDERAL_AIRSPACE_AUTHORITY` (FAA authority over navigable airspace; state/local roles limited to land use, police powers, etc.) |

**State level:**

| `legal_dimension` | Vocabulary |
|---|---|
| `DR_CRITICAL_INFRASTRUCTURE_RESTRICTION` | `STATUTE_RESTRICTS` (numeric_value = altitude ft if stated), `NO_STATUTE`, `UNCLEAR` |
| `DR_STATE_PREEMPTION_OF_LOCAL` | `STATE_PREEMPTS_LOCAL`, `LOCAL_MAY_REGULATE`, `NOT_ADDRESSED` |
| `DR_UAS_SPECIFIC_PRIVACY_OR_TRESPASS` | `UAS_STATUTE_EXISTS`, `NO_UAS_STATUTE` (context; rarely affects delivery) |

## 4. Deployment record schema (`evidence/deployment_evidence.csv`)

**EXTERNAL VALIDATION ONLY.** These records never enter features, weights or regulatory codes.

| Column | Rule |
|---|---|
| `deployment_id` | `DEP-<MODE>-<NNN>` (RT, SW, DR) |
| `operator` | Company |
| `mode` | `ROBOTAXI` / `SIDEWALK_DELIVERY` / `DRONE_DELIVERY` |
| `reported_geography` | As the source states it (e.g. "Phoenix metro", "parts of Austin") |
| `market_id` | 5-digit CBSA of the 35-market universe if resolvable, else blank |
| `market_name` | CBSA title, or blank |
| `market_resolution` | `WITHIN_MARKET_PARTIAL` (service area inside part of the CBSA), `CITY_ONLY`, `CAMPUS_OR_SITE`, `MULTI_MARKET`, `OUTSIDE_UNIVERSE`, `UNRESOLVED` |
| `resolution_note` | Why that market; what share or area is plausibly covered |
| `deployment_status` | `ANNOUNCED`, `TESTING`, `PILOT`, `LIMITED_COMMERCIAL`, `COMMERCIAL`, `PAUSED`, `ENDED`, `UNKNOWN` |
| `service_type` | e.g. `RIDE_HAIL`, `FOOD_DELIVERY`, `RETAIL_DELIVERY`, `HEALTHCARE_DELIVERY`, `CAMPUS_DELIVERY` |
| `commercial_or_pilot` | `COMMERCIAL` / `PILOT` / `NON_COMMERCIAL_TESTING` / `UNKNOWN` |
| `driverless_or_supervised` | Robotaxi: `DRIVERLESS`, `SAFETY_DRIVER`, `MIXED`, `UNKNOWN`; else blank |
| `platform_partner` | e.g. Uber, Lyft, DoorDash, Walmart; blank if none |
| `announcement_date`, `start_date`, `end_date` | YYYY-MM-DD where known |
| `evidence_as_of` | 2026-10-05 |
| `source_title`, `source_url`, `source_type` | `OPERATOR_OFFICIAL`, `REGULATOR_ORDER`, `STATE_AGENCY` or `SECONDARY` |
| `access_date` | 2026-10-05 |
| `verification_status` | `VERIFIED_PRIMARY` / `SECONDARY_ONLY` / `PRIMARY_CITED_NOT_RETRIEVED` |
| `notes` | Anything that limits interpretation |

**Status discipline:**
- An announcement is `ANNOUNCED`, not `COMMERCIAL`.
- A historical service that has stopped is `ENDED`, kept as its own row, never merged into an active one.
- Use the most recent dated evidence on or before 2026-10-05.
- One row per operator × market × service phase.
