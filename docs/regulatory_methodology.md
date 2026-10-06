# Regulatory & Deployment Evidence Methodology (Phase 6.5)

**Status:** Phase 6.5, in review · **Last updated:** 2026-10-05

> **Legal disclaimer.** This project classifies public regulatory evidence analytically, for market comparison. **It is not legal advice.** Each code reflects the cited evidence as of the frozen evidence date and may become outdated as laws and regulations change. A code is an analyst's reading of a source, recorded with its citation, confidence and caveats.

| Constant | Value |
|---|---|
| `REGULATORY_EVIDENCE_AS_OF` | **2026-10-05**. Law in force, or enacted with a known effective date, on this date |
| `DEPLOYMENT_EVIDENCE_AS_OF` | **2026-10-05**. Services publicly evidenced on this date. A separate concept and a separate file |

## 1. What this phase produced (and did not)

| Artifact | Content |
|---|---|
| `evidence/research_protocol.md` | The coding contract: source hierarchy, schemas, vocabularies, confidence rules |
| `evidence/regulatory_evidence.csv` | **582** coded records: robotaxi 248, sidewalk 232, drone 102 (95 state + 7 federal) |
| `evidence/deployment_evidence.csv` | **180** deployment records, EXTERNAL VALIDATION ONLY ([deployment_validation_plan.md](deployment_validation_plan.md)) |
| `evidence/research_log.csv` | 94 rows: per jurisdiction and mode, the research done, the authoritative source checked, any second source, unresolved issues and the date last verified |
| `config/regulatory_feature_contract.csv` | 28 legal dimensions: 7 active Phase 7 candidates, 11 deferred, 2 excluded, 8 context-only (7 federal constants plus drone privacy, classed as excluded); no weights |
| `outputs/phase65/` | Jurisdiction inventory, market × state × dimension bridge, market summaries, multi-state analysis, A-012 method comparison |
| `scripts/validate_evidence.py` | Enforces the protocol and contract integrity (PASS) |
| `scripts/build_regulatory_mapping.py` | Reproducible market mapping (A-012) |
| `dbt/tests/assert_no_deployment_evidence_in_feature_layer.sql` | Deployment-leak guard on the feature marts and DIM_FEATURE |

**Not produced:** scores, component scores, weights, normalized regulatory values, rankings, scenarios, sensitivity runs or Power BI. Deployment presence was **never** used to code a legal status.

## 2. Jurisdictions (Step 1)

From `CORE.DIM_MARKET` and `CORE.BRG_MARKET_STATE`, the 35 markets span **31 jurisdictions**:

AZ, CA, CO, DC, DE, FL, GA, IL, IN, KS, KY, MA, MD, MI, MN, MO, NC, NH, NJ, NV, NY, OH, OR, PA, SC, TN, TX, VA, WA, WI and WV.

DC is treated as a state-equivalent; it has no subordinate local governments. Federal (US) context applies to drones. The **11 multi-state markets** and their PEP 2025 population shares are in `outputs/phase65/jurisdiction_inventory.csv`. Examples:
- Washington: VA 49%, MD 39%, DC 11%, WV 1%
- Kansas City: MO 59%, KS 41%
- New York: NY 65%, NJ 35%
- Philadelphia: PA 67%, NJ 22%, DE 9%, MD 2%

No state outside the universe was researched.

## 3. How the evidence was gathered

1. **Protocol first.** Every researcher, human or agent, coded against `evidence/research_protocol.md`: one vocabulary per legal dimension, and a source-type, verification-status and confidence field on every record.
2. **Primary sources.** The source hierarchy (protocol §1) ranks:
   1. state statute
   2. regulation and agency pages
   3. executive and legislative documents
   4. federal sources
   5. municipal codes where material
   6. regulator orders
   7. operator sources, for deployment only

   NCSL, IIHS and law-firm summaries were used **only to discover** statutes, then verified on the official code. A secondary source is never the sole basis for a code when a primary source exists.
3. **Retrieval.**
   - 14 parallel research passes, one per mode and jurisdiction group.
   - Three of them were interrupted by an API session limit. Their scope was then completed by batched, cached retrieval from the official code sites (`scripts/research_fetch.py`), with downloads under `data/raw/phase65_research/` (git-ignored).
   - All PDFs and HTML were extracted to text in one pass, then read.
4. **Blocked hosts are disclosed, not hidden.** Several official hosts refuse automated access: ilga.gov (Illinois), mass.gov and malegislature.gov, nysenate.gov and dmv.ny.gov, leginfo.legislature.ca.gov, the Georgia and Tennessee code hosts, and governor.ohio.gov documents. Affected records are marked `PRIMARY_CITED_NOT_RETRIEVED` or `SECONDARY_ONLY`, with confidence capped (protocol §1). See [regulatory_ambiguities.md](regulatory_ambiguities.md) §1.

## 4. Coding conventions

1. **Absence ≠ prohibition.** No statute is coded `NO_SPECIFIC_STATUTE`, `NO_STATUTE` or `NOT_ADDRESSED`, never `NOT_AUTHORIZED`. Absence findings are never HIGH confidence. The only `NOT_AUTHORIZED` code (New York, driverless) rests on a positive statutory requirement, VTL §1226's hand-on-wheel rule, not on absence.
2. **PDD operating conditions.** Where a state has no PDD statute, the weight, speed, operator, insurance and registration dimensions are `NOT_APPLICABLE_NO_PDD_STATUTE` in the mapping (protocol §3.2). Numeric limits keep their units and their basis (with or without cargo) in the record.
3. **Drone critical-infrastructure rule (uniform).** `STATUTE_RESTRICTS` means a statute restricts **ordinary** (not intent-based) flight over a list of facilities **broader than correctional facilities**.
   - Intent-based offenses ("in furtherance of a criminal offense", "with intent to … surveil") and correctional-facility-only restrictions are coded `NO_STATUTE`, with a scope note.
   - Applying this uniformly re-coded NC, SC and TN, which had first been coded `STATUTE_RESTRICTS` on correctional-facility clauses. The re-code is recorded in each analyst note.
   - Exemptions for FAA-compliant commercial operations (TX, OR, WI, VA) are noted. They are why this dimension is deferred (§7).
4. **Sidewalk operator requirement.**
   - `REMOTE_OPERATOR_REQUIRED`: the statute requires monitoring **and** control capability (NV, NC, GA).
   - `REMOTE_MONITORING_REQUIRED`: the statute accepts monitoring **or** control.
   - `OPERATOR_LIABLE_NO_SUPERVISION_RULE`: the statute sets no supervision duty.
5. **Executive orders.** An executive order is coded as authorization only where its text was read. Illinois (EO 2018-13), Massachusetts (2016) and Ohio (EO 2018-04K) are known from NCSL only, so they are coded `NO_SPECIFIC_STATUTE` with the order described in the note (LOW).
6. **Confidence.**
   - **HIGH:** a retrieved primary source directly establishes the code.
   - **MEDIUM:** primary sources need synthesis, are partly ambiguous, are an absence finding, or were cited but not retrieved.
   - **LOW:** incomplete, conflicting, outdated, or dependent on secondary sources.

   Confidence is a quality label. **It is never converted into a number or a score.**

## 5. Evidence quality (Steps 6–7)

| | Robotaxi | Sidewalk | Drone | Total |
|---|---|---|---|---|
| Records | 248 | 232 | 102 | 582 |
| HIGH / MEDIUM / LOW | 74 / 140 / 34 | 106 / 119 / 7 | 33 / 54 / 15 | **213 / 313 / 56** |
| Primary retrieved (`VERIFIED_PRIMARY`) | 213 | 211 | 88 | **512 (88%)** |
| Primary cited, not retrievable | 6 | 21 | 7 | 34 |
| Secondary only | 29 | 0 | 7 | 36 |
| Second source checked (consistent / conflict) | 112 / 0 | 136 / 2 | 27 / 0 | **275 / 2** |

The LOW-confidence records are concentrated in hosts that blocked retrieval: MA 11, IL 8, NJ 8, OH 8, TN 7, NY 5. These counts are after Phase 6.5b (§11).

## 6. Findings by mode (state level; full detail in the evidence file)

### 6.1 Robotaxi

| Dimension | Status (jurisdictions) |
|---|---|
| Driverless operation | **Authorized by statute:** AZ CO FL GA KS KY MI NC NH NV TN TX WV · **with permit:** CA PA · **testing only:** DC · **unclear:** WA · **not authorized:** IL (licensed driver in control required, per EO 2018-13; no dedicated driverless statute) · NY (VTL §1226; Part FF testing requires a licensed person on board) · **no specific statute:** DE IN MA MD MN MO NJ OH OR SC VA WI |
| Commercial passenger service | **Statute:** AZ FL GA KS MI NH TN WV · **permit:** CA NV PA TX · **unclear:** KY · **no framework:** CO DC DE IL IN MA MD MN MO NC NJ NY OH OR SC VA WA WI |
| Local authority | **State preempts:** AZ CA CO FL IL KS KY NC NV PA TN TX WV · **unclear:** GA NY · **not addressed:** the rest |

Material conditions recorded:
- **Kansas:** a 12-month in-vehicle human driver is required for each new entity's vehicles with manual controls.
- **Michigan:** on-demand networks are limited to manufacturer SAVE fleets.
- **Pennsylvania:** PennDOT certificate of compliance plus Public Utility Commission authority.
- **Texas:** DMV authorization under SB 2807 (2025).
- **Kentucky:** $1M insurance.
- **New Hampshire:** $5M for testing.
- **New York:** the Part FF testing program lapsed on 2026-04-01. L.2026 ch.58 Part E (signed 2026-05-26) revived it until 2028-04-01 (ambiguity 4.8).

### 6.2 Sidewalk delivery robot (PDD)

| Dimension | Status |
|---|---|
| PDD statute | **Authorizes:** AZ DC FL GA IN MD MO NC NH NV OH PA TN TX VA WA WI WV (18) · **no statute:** CA CO DE IL KS KY MA MI MN NJ NY OR SC (13) |
| Local authority | **May prohibit:** NC OH PA TN VA WA WI · **may regulate, not prohibit:** AZ FL IN MD MO NH NV TX · **state preempts:** GA WV · **not addressed:** the 13 no-statute states and DC |
| Maximum weight | 80 lb (WI) · 120 (WA) · 150 (NV) · 250 (DC, temporary to 2027-04-02) · 500 (GA IN NC VA) · 550 (MD OH PA) · **no limit stated:** AZ FL MO NH TN TX WV |

Nevada's statute is limited to university campuses (scope note).

### 6.3 Drone delivery

**Federal (CONTEXT_ONLY, identical in all 35 markets):**
- Part 107 and the Part 135 delivery certificates (7 holders listed by the FAA) are in force.
- **BVLOS (proposed 14 CFR Part 108, 90 FR 38212, 2025-08-07) is `PROPOSED_RULE`:** no final rule was published as of 2026-10-05.
- Remote ID and LAANC are in force.
- Navigable airspace is a federal authority (49 U.S.C. 40103).

**State level:**

| Dimension | Status |
|---|---|
| Preemption of local UAS regulation | **State preempts:** AZ FL GA MD MI NJ OR PA TX VA WI · **local may regulate:** DE NC OH · **not addressed:** the rest |
| Critical-infrastructure restriction | **Restricts:** DE FL NV OR TX VA WI (TX, OR, WI and VA exempt FAA-compliant commercial operation) · **no statute:** the rest |
| UAS privacy or trespass | 18 jurisdictions have a UAS statute, mostly governing law-enforcement use or intentional harassment |

Florida §330.41(3)(c) also bars localities from refusing permits to drone-delivery drone ports based on location.

## 7. Federal constants and the feature contract (Steps 10–11)

`config/regulatory_feature_contract.csv` fixes which dimensions Phase 7 may consider. **No weights, no normalization.**

| Status | Dimensions |
|---|---|
| **ACTIVE_CANDIDATE (7)** | `RT_DRIVERLESS_OPERATION`, `RT_COMMERCIAL_PASSENGER_SERVICE`, `RT_LOCAL_AUTHORITY`, `SW_PDD_LEGAL_STATUS`, `SW_LOCAL_AUTHORITY`, `SW_MAX_WEIGHT`, `DR_STATE_PREEMPTION_OF_LOCAL` |
| DEFERRED_REDUNDANT / EXCLUDED_REDUNDANT | RT testing (nested in driverless); RT safety driver (near-inverse of driverless; kept as a QA flag); SW sidewalk authorization (nested) |
| DEFERRED_DIRECTION | RT TNC applicability, RT state approval, RT insurance; DR critical infrastructure (commercial exemptions make delivery impact uncertain) |
| DEFERRED_LOW_IMPACT | SW sidewalk speed (6–12 mph, rarely binding), roadway authorization and speed, operator requirement, insurance, registration |
| EXCLUDED_NOT_DELIVERY_RELEVANT | DR UAS privacy or trespass |
| **CONTEXT_ONLY (7)** | All federal drone dimensions: identical nationally, so they can never differentiate markets |

Each active candidate records:
- its `favorable_statuses` (the permissive codes);
- its `direction`, e.g. `PERMISSIVE_STATUS_MORE_FAVORABLE` or `PREEMPTION_MORE_FAVORABLE`. Absence is never in the favorable set;
- its `market_mapping_method` (§8);
- its limitations.

`RT_COMMERCIAL_PASSENGER_SERVICE` tracks `RT_DRIVERLESS_OPERATION` closely across states. Phase 7 must decide whether to combine them (e.g. as an ordinal) or keep one.

## 8. A-012: multi-state market mapping (Steps 8–9)

**Business question:** *if an operator evaluates the metropolitan market, how much of the addressable market can it lawfully serve under the relevant framework?*

**Evidence** (`outputs/phase65/a012_method_comparison.csv`): in the 11 multi-state markets, the states differ on **45 of 66** market × active-categorical-dimension pairs. Each universal rule, applied to those 45 pairs:

| Universal method | Result on the 45 differing pairs | Why it fails as a universal rule |
|---|---|---|
| A. Principal-city state | favorable in 14 | Discards minority states: Kansas City's 41% (KS, driverless authorized) and Cincinnati's 21% (KY, where CVG airport is) count as zero |
| B. Dominant-population state | favorable in 15 | The same loss. A or B misstate more than 25% of the market in 11 pairs |
| C. Population-weighted treatment | share 0.00–0.91 (median 0.21) | Directly measures the addressable share under each status: **adopted for categorical dimensions** |
| D. Most-restrictive state | favorable in **0** | A 2% fringe state (MD in Philadelphia) decides the whole market |
| E. Most-permissive state | favorable in **36** | Boston would count as driverless-authorized because of New Hampshire's 9% |

**Resolution: no single universal rule is defensible.** A-012 is resolved with a **dimension-specific mapping contract**:

| Dimension type | Mapping method | Future aggregation rule |
|---|---|---|
| Categorical legal permission or authority (RT driverless, commercial, local authority; SW PDD status, local authority; DR preemption) | `POPULATION_SHARE_BY_STATUS` | Share of market population (PEP 2025) in states whose status is in `favorable_statuses`, with the full status composition reported. **Never averages codes.** |
| Numeric operating limits (SW maximum weight; deferred insurance and speed) | `MOST_RESTRICTIVE_NUMERIC_AMONG_PERMITTING_STATES` | One fleet design must satisfy every state it serves, so the binding value is the lowest limit among the states that authorize the activity (Washington: D.C.'s 250 lb, not Maryland's 550). `NO_LIMIT_STATED` counts as unconstrained. The dominant-state value is the sensitivity |
| Federal constants | `CONTEXT_ONLY` | Not mapped |

**Boundary discontinuity.** A state line is an operational edge for robotaxi and sidewalk service: a trip into a non-authorizing state cannot be completed driverless. The mapping therefore keeps every state row and its share, and flags `MULTI_STATE_DIFFERS` where states differ (163 of 700 market × dimension summaries, 32 of them also carrying low-confidence evidence). Phase 7 can see the discontinuity rather than a blended average. For example, Cincinnati's airport (CVG) lies in Kentucky, which authorizes driverless operation, while 76% of the market lies in Ohio, which has no statute.

**Multi-state markets materially affected** (an active dimension differs across states): all 11.
- **Robotaxi:** Boston, Charlotte, Cincinnati, Kansas City, Philadelphia, Portland, Washington, New York.
- **Sidewalk:** Boston, Charlotte, Chicago, Cincinnati, Kansas City, Minneapolis, Philadelphia, Portland, St. Louis, Washington.
- **Drone preemption:** Charlotte, Cincinnati, Minneapolis, New York, Philadelphia, Portland, Washington.

**Artifacts:**
- `market_regulatory_mapping.csv`: 1,020 market × mode × dimension × state rows, with the state status, evidence ID, confidence, method, rule and QA flag.
- `market_regulatory_summary.csv`: 700 market × dimension rows.
- `multistate_analysis.csv`.

## 9. QA (Step 20)

`scripts/validate_evidence.py` **PASS**. It checks:
- every coded status is in its dimension's vocabulary, with a source title, an http(s) URL, a source type, a verification status, dates and confidence;
- HIGH confidence rests on a retrieved primary source;
- secondary-only evidence is LOW;
- absence findings are never HIGH;
- every jurisdiction has every required dimension;
- every active contract candidate has evidence for every universe jurisdiction;
- federal dimensions are CONTEXT_ONLY;
- the contract has no weight, score or rank column;
- operator sources are never regulatory evidence.

`build_regulatory_mapping.py` maps every market with **0 MISSING_EVIDENCE**, and every multi-state market has explicit treatment. The dbt leak guard proves deployment terms are absent from the feature marts and DIM_FEATURE. The no-scoring guard (`assert_no_scoring_columns`) still passes.

## 10. Updating this evidence

Re-verify in this order:
1. The LOW-confidence jurisdictions (MA, NJ, OH robotaxi and NY local authority, per the §11 checklist; TN sidewalk; CA, GA, IL, MA drone), preferably in a browser, since those hosts block automated retrieval.
2. Pending federal BVLOS: Part 108 final rule status.
3. Temporary provisions: D.C.'s PDD weight act expires 2027-04-02.
4. Annual session laws in all 31 jurisdictions.

`evidence/research_log.csv` records the last verified date and the open issue per jurisdiction and mode.

## 11. Phase 6.5b: manual verification of low-confidence robotaxi jurisdictions

**Scope.** IL, MA, NY, NJ and OH. The three active robotaxi candidates were re-verified: `RT_DRIVERLESS_OPERATION`, `RT_COMMERCIAL_PASSENGER_SERVICE` and `RT_LOCAL_AUTHORITY`. That makes 15 records. The evidence date stays 2026-10-05. Enacted, effective and access dates are recorded separately.

**Method.**
- Sources were tried in the protocol's priority order: statute, regulator, executive order, legislative history, then secondary sources (corroboration only).
- Hosts that block automated retrieval (ilga.gov, mass.gov, the Ohio governor's documents) were tried once each, not repeatedly.
- No status was upgraded without a retrieved official source.

**Outcomes** (per record: `outputs/phase65/phase65b_change_log.csv`):

| Outcome | Records |
|---|---|
| UPGRADED TO MEDIUM | RT-IL-03, RT-NY-03 |
| STATUS CORRECTED, MEDIUM | RT-IL-02 (NO_SPECIFIC_STATUTE → NOT_AUTHORIZED: licensed driver required); RT-IL-06 (NOT_ADDRESSED → STATE_PREEMPTS_LOCAL; current citation 625 ILCS 5/11-208(e-10)) |
| UNCHANGED, MEDIUM, now primary-verified | RT-NY-02 |
| UNCHANGED, LOW, **MANUAL VERIFICATION UNRESOLVED** | RT-MA-02/03/06, RT-NJ-02/03/06, RT-OH-02/03/06, RT-NY-06 |

Sources read on 2026-10-05:
- Illinois EO 2018-13 (illinois.gov), enacted and effective 2018-10-25;
- L.2017 ch.55 Part FF (nyassembly.gov PDF of S.2005-C / A.3005-C), effective 2017-04-01;
- L.2026 ch.58 Part E (nyassembly.gov bill text and actions for A.10008-C), signed and effective 2026-05-26;
- the DriveOhio policy page, which only lists EO 2018-04K and was used as context.

**Provenance fixes.** The RT-IL citations were corrected (they had pointed to the NCSL drone page) and NY "Part FFF" was corrected to Part FF.

**Phase 7 eligibility** (`outputs/phase65/phase7_regulatory_eligibility.csv`):
- Rule: a state record of an active robotaxi dimension is base-model eligible only if it is `VERIFIED_PRIMARY` with MEDIUM or HIGH confidence.
- After 6.5b: 28 of 31 states are eligible for driverless and commercial (the exceptions are MA, NJ, OH), and 27 of 31 for local authority (the exceptions are MA, NJ, OH, NY).
- Remaining LOW records are `INCLUDE_ONLY_IN_SENSITIVITY`.

The open browser checks are in `outputs/phase65/phase65b_manual_checklist.csv` and [regulatory_ambiguities.md](regulatory_ambiguities.md) §7.
