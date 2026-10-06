# Regulatory Ambiguity Register (Phase 6.5)

**Evidence as of:** 2026-10-05 · Not legal advice ([regulatory_methodology.md](regulatory_methodology.md)).

This register lists everything that is uncertain, rather than presenting uncertain law as certain. Each item names the affected evidence IDs in `evidence/regulatory_evidence.csv`. The **impact** column says whether an item touches an ACTIVE Phase 7 candidate (`config/regulatory_feature_contract.csv`).

## 1. Sources that could not be retrieved (verification gaps)

| # | Jurisdiction / topic | Issue | Evidence | Impact |
|---|---|---|---|---|
| 1.1 | **Illinois** (all modes) | ilga.gov still refuses connections. **Phase 6.5b:** EO 2018-13 was read on illinois.gov. It states that Illinois law allows AVs only "with a licensed driver in control of the driving task". It also states that the Vehicle Code "gives the State sole authority to govern automated vehicles' operation", citing that provision under its 2018 number, (e-5). The current citation is 625 ILCS 5/11-208(e-10). **Changes:** driverless was **corrected** from NO_SPECIFIC_STATUTE to NOT_AUTHORIZED (MEDIUM), because a licensed driver is required and so there is no current driverless authorization; Illinois still has no dedicated enacted driverless framework. Commercial was upgraded to MEDIUM. Local authority was **corrected** from NOT_ADDRESSED to STATE_PREEMPTS_LOCAL (MEDIUM). **Still open:** the statute text itself, and whether any 2025–2026 bill (e.g. HB 2974, SB 3392) was enacted. Pending bills are not treated as law | RT-IL-02/03/06 (MEDIUM); RT-IL-01/04/05/07/08, DR-IL-* (LOW) | **Active:** Chicago (92%), St. Louis (24%) |
| 1.2 | **Massachusetts** | mass.gov and malegislature.gov still return 403. EO 572 (2016), any successor order and the MassDOT/RMV testing process remain unread. Testing is not read as commercial authorization. **MANUAL VERIFICATION UNRESOLVED** | RT-MA-*, DR-MA-* (LOW) | **Active:** Boston (91%) |
| 1.3 | **New York** | **Phase 6.5b:** the 2017 Part FF text (L.2017 ch.55, the Assembly PDF) and L.2026 ch.58 Part E were both read. Part FF is the AV testing program, previously mis-cited as "Part FFF". Part E moves the program's expiry from 2026-04-01 to 2028-04-01. Driverless (NOT_AUTHORIZED) and commercial (NO_SPECIFIC_FRAMEWORK) are now primary-verified at MEDIUM. Still open: the NYC DOT permit program, so local authority stays UNCLEAR (LOW) | RT-NY-02/03 (MEDIUM); RT-NY-06 (LOW) | **Active:** New York (65%) |
| 1.4 | **New Jersey** | No official full-text statute search was retrievable. Absence rests on NCSL, and pending AV bills were introduced only. The codes are **absence** (NO_SPECIFIC_STATUTE / NO_SPECIFIC_FRAMEWORK / NOT_ADDRESSED), not prohibition. Nothing found supports NOT_AUTHORIZED. **MANUAL VERIFICATION UNRESOLVED** | RT-NJ-* (LOW) | **Active:** New York (35%), Philadelphia (22%) |
| 1.5 | **Ohio** | No AV statute was found. The official DriveOhio policy page (read 2026-10-05) lists EO 2018-04K as the order that "authorized autonomous vehicle testing in Ohio", and EO 2019-26D as re-establishing DriveOhio. The EO text was not retrievable, so whether it allows testing with no one on board is unknown. Testing is not read as driverless or commercial authorization. **MANUAL VERIFICATION UNRESOLVED** | RT-OH-* (LOW) | **Active:** Cincinnati (76%); Cleveland and Columbus (single-state) |
| 1.6 | **Tennessee** sidewalk | The official code host (LexisNexis) was blocked; text read via FindLaw (current to 2024-01-02) | SW-TN-04..10 (LOW) | **Active:** SW_MAX_WEIGHT (TN = no limit stated), Nashville |
| 1.7 | **California** drone | leginfo blocked; Civ. Code §1708.8 cited, not retrieved | DR-CA-* | DR preemption (CA = not addressed, LOW) |
| 1.8 | **Georgia** | Code text from Release 84 (2022) via a public copy, so 2023–2026 amendments are not ruled out. Drone preemption (O.C.G.A. §6-1-4) cited, not retrieved | RT-GA-*, SW-GA-*, DR-GA-* | **Active:** Atlanta (all modes) |
| 1.9 | **Kentucky** robotaxi | Coded from the veto-overridden HB 7 bill text; codified KRS and 2025–2026 amendments not retrieved | RT-KY-* (MEDIUM) | **Active:** Cincinnati (21%) |
| 1.10 | **Pennsylvania** insurance, **West Virginia** insurance | Operative text of 75 Pa.C.S. §8508(f) and W. Va. Code §17H-1-10 could not be isolated from the retrieved pages | RT-PA-08, RT-WV-08 | Deferred dimension only |

## 2. Unclear statutory interpretation

| # | Issue | Evidence | Impact |
|---|---|---|---|
| 2.1 | **Georgia** robotaxi: §40-8-11's "any commercial use … notwithstanding" clause may displace TNC rules and restrain local ordinances, but it does not name local governments. Coded UNCLEAR (TNC, local authority) | RT-GA-04, RT-GA-06 | **Active:** RT local authority, Atlanta |
| 2.2 | **Kentucky** robotaxi: HB 7 amends the KRS 281 motor-carrier and TNC definitions without an explicit for-hire AV passenger provision in the text read. Coded UNCLEAR | RT-KY-03, RT-KY-04 | **Active:** RT commercial, Cincinnati |
| 2.3 | **Washington** robotaxi: RCW 46.92.010 is a self-certification testing program silent on occupant requirements; EO 17-02 not retrieved. Coded UNCLEAR | RT-WA-02 | **Active:** Seattle, Portland (21%) |
| 2.4 | **Tennessee** robotaxi TNC: whether TNC permit and driver rules reach driverless fleets is unclear | RT-TN-04 | Deferred |
| 2.5 | **Maryland**: the safety-driver position rests on an MVA guidance process with no stated legal basis | RT-MD-05 | Deferred |
| 2.6 | **Michigan**: on-demand AV networks are expressly tied to manufacturer SAVE fleets. Whether a non-manufacturer operator may run for-hire service outside SAVE is not stated | RT-MI-03 | **Active:** RT commercial, Detroit |
| 2.7 | **Indiana** PDD: localities may adopt "restrictions"; whether that extends to an outright ban is not stated | SW-IN-09 (LOW) | **Active:** SW local authority |
| 2.8 | **Arizona and Texas** PDD local authority: local rules must not be "inconsistent" with the statute; whether a citywide ban would be inconsistent is untested | SW-AZ-09, SW-TX-09 | **Active:** SW local authority |
| 2.9 | **Washington** PDD local authority: no preemption clause, and compliance with local right-of-way rules is required. Coded LOCAL_MAY_PROHIBIT by inference | SW-WA-09 | **Active** |
| 2.10 | **Nevada** PDD: the statute authorizes operation only at state university campuses and adjacent sidewalks, so it is far narrower than the STATUTE_AUTHORIZES code suggests | SW-NV-01 | **Active:** SW PDD status, Las Vegas. Phase 7 should treat Nevada as near-equivalent to "no general authorization" or apply a scope adjustment |

## 3. Conflicting sources

| # | Issue | Evidence |
|---|---|---|
| 3.1 | **Arizona** PDD weight: a 2026 secondary summary still reports the superseded 2018 limits (100 lb, 10 mph). The current A.R.S. text (SB 1305, 2020) states no weight limit. The primary source was followed | SW-AZ-04 |
| 3.2 | **Nevada** PDD: the secondary summary omits Nevada entirely; the official NRS text shows the narrow campus statute | SW-NV-01 |
| 3.3 | **Georgia** PDD speed: a news article reported 20 mph on sidewalks, contradicting the enacted text (4 mph, raised to 7 mph by HB 986, effective 2026-07-01). The enacted text was followed | SW-GA-05 |

## 4. Pending, temporary or date-sensitive law

| # | Issue | Evidence |
|---|---|---|
| 4.1 | **Federal BVLOS (Part 108)**: proposed 2025-08-07; no final rule by 2026-10-05, though the Unified Agenda targeted July 2026 and secondary reports say OIRA received a final rule 2026-07-10. **Recheck before Phase 7** (context only) | DR-US-04, DR-US-05 |
| 4.2 | **D.C.** PDD weight cap of 250 lb is from a temporary act expiring 2027-04-02; the permanent text is under 90 lb | SW-DC-04 |
| 4.3 | **Texas** robotaxi: SB 2807 is effective 2025-09-01 and DMV rules 2026-02-27; compliance is due the later of 2026-05-28 or 90 days after the Public Safety Commission's rule, a date not verified | RT-TX-* |
| 4.4 | **Kansas** robotaxi: the 12-month in-vehicle driver phase-in applies to each new entity; the tandem-axle limit expired 2025-07-01 | RT-KS-05 |
| 4.5 | **Kentucky** robotaxi: the >62,000 lb human-driver requirement lapsed 2026-07-31 | RT-KY-02 |
| 4.6 | **Ohio** drone: HB 251 police-warrant provisions take effect 2026-10-06, one day after the evidence date | DR-OH-* |
| 4.7 | **Wisconsin** drone critical-infrastructure act (2026) effective date derived from the default publication rule | DR-WI-01 |
| 4.8 | **New York AV testing-program lapse.** Part FF §1 expired 2026-04-01. L.2026 ch.58 Part E (A.10008-C / S.9008-C) was signed 2026-05-26, "effective immediately", and amends the expiry to 2028-04-01 without stating retroactivity. Between 2026-04-01 and 2026-05-26 no testing authority existed. As of 2026-10-05 the program is in force. The NY driverless and commercial codes do not depend on this: Part FF never allowed operation without a licensed person in the vehicle | RT-NY-01..08 |

## 5. Local-versus-state authority

- **No municipal ordinances were coded.** A state's `NOT_ADDRESSED` or `LOCAL_MAY_*` status means local rules can matter, but the ordinances of the 35 principal cities were not surveyed. Examples: San Francisco PDD permits, Chicago and NYC AV or PDD permit programs, D.C. DDOT PDD permits.
- **Drone local exposure** concerns land use (takeoff, landing, drone ports) only; navigable airspace is federal (49 U.S.C. 40103).
- **Delaware** expressly lets counties and municipalities adopt stricter UAS rules (11 Del. C. §1334(d)).

## 6. Coding judgments that Phase 7 should know

1. **Absence findings.** 13 robotaxi and 13 PDD jurisdictions are coded as absence, which is neither favorable nor prohibitive. Phase 7 must treat absence as its own ordinal level, not as zero or as prohibition.
2. **Critical-infrastructure rule.** NC, SC and TN were re-coded from `STATUTE_RESTRICTS` to `NO_STATUTE` under the uniform intent-based / correctional-only rule.
3. **Executive-order states** (IL, MA, OH, and the WA EO, which was not retrieved) are coded as having no specific statute. Illinois EO 2018-13 has now been read. It creates a voluntary registration program for testing with a licensed driver, not an authorization of driverless operation. It also states that current law requires a licensed driver in control, so RT-IL-02 is coded NOT_AUTHORIZED. That is the same basis as New York, where a human must be in control. If the MA and OH orders were read, some testing codes might rise to `AUTHORIZED_BY_EXECUTIVE_ORDER`, which is not in the favorable set for driverless operation.
4. **New York `NOT_AUTHORIZED`** rests on VTL §1226 (hand on the steering mechanism) together with the Part FF exception, which was retrieved in Phase 6.5b. That exception requires a licensed natural person present in the vehicle. VTL §1226 itself remains cited, not retrieved.
5. **Phase 6.5b citation fixes.** All RT-IL rows previously cited the NCSL *drone* page because of a staging-script key collision. They now cite EO 2018-13 (RT-IL-02/03/06) or the NCSL AV page (the rest). The statuses of RT-IL-01/04/05/07/08 were not re-reviewed. The NY rows' "Part FFF" citation was corrected to Part FF. The Part FF text also bears on RT-NY-01/05/07/08 (DMV approval, a licensed person present, $5M financial security), but those rows were outside the 6.5b scope and keep their codes.

## 7. Manual-browser checklist (Phase 6.5b, open)

Records still marked **MANUAL VERIFICATION UNRESOLVED** are listed in `outputs/phase65/phase65b_manual_checklist.csv`, with the exact official URL and the fact to verify for each. The per-record before/after detail is in `outputs/phase65/phase65b_change_log.csv`.

| Jurisdiction | Dimension(s) | Current code (confidence) | Fact to verify |
|---|---|---|---|
| IL | Local authority | STATE_PREEMPTS_LOCAL (MEDIUM) | Text and Public Act of 625 ILCS 5/11-208(e-10) (numbered (e-5) in EO 2018-13) |
| IL | Driverless, commercial | NOT_AUTHORIZED / NO_SPECIFIC_FRAMEWORK (MEDIUM) | Whether HB 2974 or SB 3392 (104th GA) was enacted by 2026-10-05 |
| MA | Driverless, commercial, local | Absence (LOW) | EO 572 and any successor (e.g. EO 603); MassDOT/RMV testing terms; whether municipal MOUs are required |
| NJ | Driverless, commercial, local | Absence (LOW) | No enacted AV statute in N.J.S.A. Title 39; any NJ MVC testing process |
| OH | Driverless, commercial, local | Absence (LOW) | EO 2018-04K text: driverless testing? still in force? No AV provision in the ORC |
| NY | Local authority | UNCLEAR (LOW) | NYC DOT AV testing permit and its legal basis |
