# Project Scope: Decision Contract

**Status:** Phase 1 draft for review · **Last updated:** 2026-09-29

> **Independent-analysis disclaimer.** This is an independent portfolio analysis inspired by public developments in autonomous mobility. It is not affiliated with, sponsored by, or performed for Uber or any autonomous-vehicle company. It uses only public data. It does not represent the views, plans or strategy of any company.

This document is the contract that later analysis has to follow. When a later phase wants to deviate from it, the change must be recorded here, with the reason, before that work begins.

---

## 1. Business objective

Build a transparent, reproducible decision-support system that lets an expansion strategist compare major U.S. metropolitan markets for three autonomous-service modes. It should also show how those comparisons change when business priorities change. The system supports a resource-allocation decision about which markets deserve deeper diligence first. It does not claim objective truth about which market is "best."

## 2. Core business question

> Which U.S. metropolitan markets appear most attractive for autonomous mobility and delivery expansion, and how do those recommendations change under different business priorities?

Sub-questions:
- For each mode, which markets look strong on each of the five components, and why (in terms of observed metrics)?
- Which markets keep a high ranking across many plausible weighting schemes (robust), and which depend on one priority (fragile)?
- Do markets with current public deployments show characteristics that the framework independently rates as favorable? This is a reasonableness check only.

## 3. Unit of analysis

One **U.S. Metropolitan Statistical Area (MSA)**, as delineated by the U.S. Office of Management and Budget (OMB) and published by the U.S. Census Bureau.

The MSA was chosen as the market for four reasons:
- It approximates a commuting-based labor and consumer market, which suits service-area expansion decisions.
- Census, BLS and BEA publish natively at this geography.
- Its county-based composition gives a clean crosswalk for county-level sources.
- It avoids ad-hoc city-limit definitions.

Known weakness: an MSA includes low-density outlying counties. The metro-wide averages can therefore misrepresent the urban core where early deployments would actually happen (see §13, assumption A-008 and `data_sources.md` §6).

## 4. Canonical geography key

| Item | Value |
|---|---|
| Key name | `market_id` |
| Definition | 5-digit Census CBSA code, stored as a string with leading zeros preserved |
| Delineation | The delineation used by the pinned PEP vintage (OMB Bulletin No. 23-01, July 2023; see `data_sources.md` §S-01) |
| Join rule | Every source must resolve to `market_id` through a documented crosswalk or aggregation rule. Free-text city or metro names are never the primary join key. Names are labels only. |

## 5. Market-selection rule

| Field | Value |
|---|---|
| **Market universe** | Top 35 U.S. Metropolitan Statistical Areas by resident population |
| **Source** | U.S. Census Bureau, Population Estimates Program (PEP): *Metropolitan and Micropolitan Statistical Area Population Totals: 2020–2025* |
| **File** | `cbsa-est2025-alldata.csv` |
| **Official URL** | https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/metro/totals/cbsa-est2025-alldata.csv |
| **Vintage** | **Vintage 2025** (July 1, 2025 estimates). File server `Last-Modified`: 2026-03-26 |
| **Population field** | `POPESTIMATE2025` |
| **Geography** | Metropolitan Statistical Area (`LSAD = "Metropolitan Statistical Area"`) |
| **Identifier** | CBSA code (`CBSA` column) |
| **Accessed** | 2026-09-29 |
| **File checksum (SHA-256)** | `BF6FAD83753456413D047D1ACEBEB434BD067EBA9D6D0BE62B3F737AD1301852` |
| **Selection** | Keep rows where `LSAD = "Metropolitan Statistical Area"`, which drops Micropolitan Statistical Areas, Metropolitan Divisions and county rows. Sort by `POPESTIMATE2025` descending and keep ranks 1–35. |
| **Coverage note** | The file covers the 50 states + DC. Puerto Rico metros are published separately (`prc-cbsa-est2025.csv`) and are out of scope. |
| **Frozen** | Yes. This vintage and list stay fixed for the whole project, even after Census publishes Vintage 2026. |

Checks performed on the file at access (2026-09-29):
- 2,806 total rows. 387 are Metropolitan Statistical Areas, 538 Micropolitan Statistical Areas, 37 Metropolitan Divisions, and 1,844 county rows.
- Of the 387 MSA rows, none has a duplicate CBSA code and none has a Metropolitan Division code.

**Selection rules that were deliberately not used:**
- No markets are added or removed because of current autonomous deployments.
- No hand-picking.
- No substitution of ACS population.

**Boundary note, recorded for transparency:** #36 is San Jose-Sunnyvale-Santa Clara, CA (41940), with 1,984,473 residents. It falls outside the universe. #35 Cleveland has 2,165,775, a gap of about 181,000 people. San Jose is a known autonomous-vehicle market, and excluding it is a direct result of the pre-committed rule. It is recorded as assumption A-001 and must not be reversed to improve validation results.

## 6. Final market list (35)

Source: PEP Vintage 2025, `POPESTIMATE2025`, accessed 2026-09-29.

| Rank | market_id (CBSA) | CBSA name | Population (July 1, 2025 est.) |
|---:|---|---|---:|
| 1 | 35620 | New York-Newark-Jersey City, NY-NJ | 20,112,448 |
| 2 | 31080 | Los Angeles-Long Beach-Anaheim, CA | 12,844,441 |
| 3 | 16980 | Chicago-Naperville-Elgin, IL-IN | 9,434,123 |
| 4 | 19100 | Dallas-Fort Worth-Arlington, TX | 8,477,157 |
| 5 | 26420 | Houston-Pasadena-The Woodlands, TX | 7,904,627 |
| 6 | 12060 | Atlanta-Sandy Springs-Roswell, GA | 6,482,182 |
| 7 | 47900 | Washington-Arlington-Alexandria, DC-VA-MD-WV | 6,465,724 |
| 8 | 33100 | Miami-Fort Lauderdale-West Palm Beach, FL | 6,391,072 |
| 9 | 37980 | Philadelphia-Camden-Wilmington, PA-NJ-DE-MD | 6,329,118 |
| 10 | 38060 | Phoenix-Mesa-Chandler, AZ | 5,228,938 |
| 11 | 14460 | Boston-Cambridge-Newton, MA-NH | 5,034,221 |
| 12 | 40140 | Riverside-San Bernardino-Ontario, CA | 4,769,007 |
| 13 | 41860 | San Francisco-Oakland-Fremont, CA | 4,630,041 |
| 14 | 19820 | Detroit-Warren-Dearborn, MI | 4,390,913 |
| 15 | 42660 | Seattle-Tacoma-Bellevue, WA | 4,161,883 |
| 16 | 33460 | Minneapolis-St. Paul-Bloomington, MN-WI | 3,790,295 |
| 17 | 45300 | Tampa-St. Petersburg-Clearwater, FL | 3,418,895 |
| 18 | 41740 | San Diego-Chula Vista-Carlsbad, CA | 3,282,248 |
| 19 | 19740 | Denver-Aurora-Centennial, CO | 3,092,037 |
| 20 | 36740 | Orlando-Kissimmee-Sanford, FL | 2,957,672 |
| 21 | 16740 | Charlotte-Concord-Gastonia, NC-SC | 2,938,830 |
| 22 | 12580 | Baltimore-Columbia-Towson, MD | 2,857,781 |
| 23 | 41180 | St. Louis, MO-IL | 2,814,421 |
| 24 | 41700 | San Antonio-New Braunfels, TX | 2,813,140 |
| 25 | 12420 | Austin-Round Rock-San Marcos, TX | 2,620,945 |
| 26 | 38900 | Portland-Vancouver-Hillsboro, OR-WA | 2,542,282 |
| 27 | 40900 | Sacramento-Roseville-Folsom, CA | 2,477,274 |
| 28 | 38300 | Pittsburgh, PA | 2,421,992 |
| 29 | 29820 | Las Vegas-Henderson-North Las Vegas, NV | 2,407,226 |
| 30 | 17140 | Cincinnati, OH-KY-IN | 2,312,858 |
| 31 | 28140 | Kansas City, MO-KS | 2,270,682 |
| 32 | 18140 | Columbus, OH | 2,242,028 |
| 33 | 26900 | Indianapolis-Carmel-Greenwood, IN | 2,205,695 |
| 34 | 34980 | Nashville-Davidson--Murfreesboro--Franklin, TN | 2,197,416 |
| 35 | 17410 | Cleveland, OH | 2,165,775 |

**Multi-state markets:** 11 of the 35 span more than one state. The state shares below are observed from the PEP county rows:

| Market | State shares of population |
|---|---|
| New York 35620 | NY 64.6% · NJ 35.4% |
| Chicago 16980 | IL 92.3% · IN 7.7% |
| Washington 47900 | VA 49.3% · MD 39.0% · DC 10.7% · WV 1.0% |
| Philadelphia 37980 | PA 67.0% · NJ 22.1% · DE 9.3% · MD 1.7% |
| Boston 14460 | MA 90.9% · NH 9.1% |
| Minneapolis 33460 | MN 96.3% · WI 3.7% |
| Charlotte 16740 | NC 84.5% · SC 15.5% |
| St. Louis 41180 | MO 76.1% · IL 23.9% |
| Portland 38900 | OR 78.6% · WA 21.4% |
| Cincinnati 17140 | OH 76.0% · KY 20.5% · IN 3.5% |
| Kansas City 28140 | MO 58.7% · KS 41.3% |

This matters for state-level regulatory evidence (see `data_sources.md` §5 and assumption A-012).

**Jurisdictions in scope:** 30 states plus DC. The 35 markets contain 319 county-equivalents with these state FIPS codes: 04, 06, 08, 10, 11, 12, 13, 17, 18, 20, 21, 24, 25, 26, 27, 29, 32, 33, 34, 36, 37, 39, 41, 42, 45, 47, 48, 51, 53, 54, 55.

**Connecticut correction:** An earlier Phase 1 working note listed Connecticut among the in-scope jurisdictions. That was wrong. Under the July 2023 delineation, New York-Newark-Jersey City (35620) contains only New York and New Jersey counties: 22 county rows (12 NJ, 10 NY) in 4 Metropolitan Divisions (29484, 35004, 35084, 35614). The former Fairfield County area belongs to Bridgeport-Stamford-Danbury, CT (14860), which is outside the universe. **No Connecticut planning region is part of any of the 35 markets**, so the 2022 change from Connecticut counties to planning regions doesn't affect this project.

### 6.1 Market-universe validation evidence (2026-09-29)

| Check | Result |
|---|---|
| Source is the official Census PEP file | `www2.census.gov/.../2020-2025/metro/totals/cbsa-est2025-alldata.csv`, HTTP 200 |
| Vintage | 2025 (`POPESTIMATE2025`); file Last-Modified 2026-03-26 |
| File integrity | SHA-256 `BF6FAD83753456413D047D1ACEBEB434BD067EBA9D6D0BE62B3F737AD1301852` |
| Filter | `LSAD = "Metropolitan Statistical Area"` → 387 rows (micropolitan areas, divisions and county rows excluded) |
| Duplicate CBSA codes among MSAs | 0 |
| Sort / retain | `POPESTIMATE2025` descending → exactly 35 retained |
| County reconciliation | The 319 county rows of the 35 markets sum exactly to each MSA total (0 mismatches) |
| Independent re-derivation | The research pass reproduced the same 35 codes in the same order |

The downloaded file was kept in a temporary working directory outside the repository and is **not** committed. Phase 3 ingestion will re-download it and check the SHA-256.

### 6.2 Unresolved delineation issues (carried to Phase 3)

1. **PEP delineation is inferred, not stated.** The file matches the July 2023 delineation (OMB Bulletin 23-01) exactly: 387/538 counts, 2023 titles, and Connecticut planning regions. No Census page found states it in words. Phase 3 will compare the 35 markets' county composition against `list1_2023.xlsx`.
2. **ACS 2020–2024 and CBP 2023 delineation** are inferred to be July 2023 but not stated. Phase 3 will check that every `market_id` and name matches (assumption A-005).
3. **EPA SLD's embedded `CBSA` field uses a pre-2023 delineation.** It must not be used. The SLD will be re-assigned through county FIPS (assumption A-006).
4. **BEA RPP metro delineation and availability** are unknown (optional source S-11).

## 7. Autonomous modes

| Mode | Service definition used in this project |
|---|---|
| **Robotaxi** | On-demand passenger transport in automated vehicles, with or without a safety driver, provided to the public |
| **Sidewalk delivery robot** | Low-speed ground robots carrying goods on sidewalks and crosswalks, typically called "personal delivery devices" in state law |
| **Drone delivery** | Small uncrewed aircraft delivering packages to consumers under FAA rules |

## 8. Canonical decision framework (five components)

All three modes use the same five top-level components. Each mode may use different underlying variables. **No weights are defined in Phase 1.**

| # | Component | Question it answers |
|---|---|---|
| 1 | **Demand & Market Opportunity** | Is there enough addressable demand for this service here? |
| 2 | **Operating Environment** | How hard are the physical and climate operating conditions? |
| 3 | **Economic Attractiveness** | Can the service be economically attractive here (willingness to pay, cost of the human alternative, commercial activity)? |
| 4 | **Regulatory & Autonomy Readiness** | Does the legal and permitting environment allow this mode to operate, and at what stage? |
| 5 | **Infrastructure & Mode Fit** | Does the built environment physically suit this mode? |

## 9. Candidate drivers by mode: HYPOTHESES ONLY

> **All entries below are HYPOTHESES.** None is a confirmed feature, and none carries a weight or an assumed direction of effect beyond the stated rationale. A candidate becomes a feature only after (a) a defensible source is verified (`data_sources.md` feature-feasibility matrix) and (b) Phase 5 EDA has checked its distribution, missing data and redundancy.

### 9.1 Robotaxi (hypotheses)
| Component | Candidate drivers (hypotheses) |
|---|---|
| Demand & Market Opportunity | Population; population-weighted density; commuting volume and mode mix; airport passenger activity |
| Operating Environment | Precipitation days; snowfall and snow-cover days; freezing days; extreme-heat days |
| Economic Attractiveness | Median household income; wage level of human drivers (labor-cost proxy); commercial activity |
| Regulatory & Autonomy Readiness | State statute authorizing driverless operation; state testing/deployment permit framework; local preemption; passenger-carrier rules (see the evidence framework in `data_sources.md` §5) |
| Infrastructure & Mode Fit | Airport connectivity; urban-form proxies (intersection density); household vehicle availability / car dependence |

### 9.2 Sidewalk delivery robot (hypotheses)
| Component | Candidate drivers (hypotheses) |
|---|---|
| Demand & Market Opportunity | Population-weighted density; restaurant and food-service establishment density; retail/grocery density |
| Operating Environment | Precipitation days; snowfall and snow-cover days; freezing days; extreme-heat days |
| Economic Attractiveness | Median household income; courier/food-service wage level; business activity |
| Regulatory & Autonomy Readiness | State personal delivery device (PDD) statute; weight and speed limits; local authority to prohibit or regulate |
| Infrastructure & Mode Fit | Walkability / built-environment indices; street-intersection density; short-distance commercial density |

### 9.3 Drone delivery (hypotheses)
| Component | Candidate drivers (hypotheses) |
|---|---|
| Demand & Market Opportunity | Households; household/population opportunity in lower-density areas; commercial/retail activity |
| Operating Environment | Precipitation days; wind (only if a defensible source exists); temperature extremes |
| Economic Attractiveness | Median household income; courier wage level; retail activity |
| Regulatory & Autonomy Readiness | FAA framework (Part 107 / Part 135 / BVLOS rulemaking status), which applies federally and uniformly; state/local restrictions where relevant |
| Infrastructure & Mode Fit | Suburban-structure proxies (single-family detached housing share); density; share of area within controlled airspace near airports (only if defensibly quantifiable) |

## 10. Time-period and vintage strategy

- **Cross-sectional design.** Each source contributes one pinned vintage. The analysis compares markets at a point in time. It does not forecast.
- **Pin, don't chase.** Each source's vintage is recorded in `data_sources.md` and frozen once Phase 3 ingestion begins. Newer releases are not mixed in mid-project.
- **Vintage kept explicitly.** Every future fact table will carry `source_vintage` / `observation_period` columns (and `effective_date` for regulatory evidence). There will be no `DIM_DATE` unless a real time-series need emerges.
- **Mixed vintages are expected and documented.** Examples: PEP 2025 population, ACS 5-year pooled survey periods, climate normals for 1991–2020, the latest calendar-year enplanements, and regulatory status as of an access date. See assumption A-003.
- **Climate uses 30-year normals** rather than a single year, so that one anomalous year doesn't drive operating-environment rankings.
- **Regulatory and deployment evidence** is point-in-time, recorded with `effective_date`, `evidence_date` and `accessed_date`.

## 11. Evidence taxonomy

Every field, metric or statement in this project must carry one of these labels:

| Label | Meaning | Example |
|---|---|---|
| **OBSERVED** | Value published by an authoritative source, loaded without alteration apart from typing and renaming | ACS median household income for a CBSA |
| **DERIVED** | Computed by us from observed values with a documented formula | Population-weighted density; restaurants per 10,000 residents |
| **ASSUMPTION** | A modeling choice about the world that cannot be directly verified | "The primary airport's weather station represents the metro's climate" |
| **SCORING CHOICE** | A decision-model design choice: normalization method, weights, aggregation | Min-max vs. percentile scaling; baseline weights (Phase 7) |
| **QUALITATIVE CLASSIFICATION** | A categorical coding of documentary evidence, with citation and date | "State statute expressly authorizes driverless operation: yes/no" |
| **EXTERNAL VALIDATION EVIDENCE** | Information used only to sanity-check outputs, never as input | An operator's official service-area page |

## 12. Major intended deliverables

1. A reproducible Python ingestion pipeline from public sources into Snowflake RAW, with load metadata and row-count audit.
2. A layered Snowflake warehouse (RAW → STAGING → CORE → ANALYTICS) with documented grain.
3. A dbt project with sources, staging/intermediate/core/mart models, generic and business-rule tests, and documentation/lineage.
4. `MART_MARKET_FEATURES`: one row per market (35 rows).
5. EDA and feature-audit notebook, with a log of inclusion and exclusion decisions.
6. Mode-specific readiness models with exposed component scores and documented weights (Phase 7).
7. A sensitivity analysis across many weighting scenarios: Top-5 rate, mean/median rank, rank SD, best/worst rank.
8. Analytical outputs written back to Snowflake, with reconciliation evidence.
9. A Power BI semantic model and decision-support dashboard with a What-If scenario simulator and a methodology page.
10. Methodology, data dictionary, source catalog and assumptions register.
11. Lightweight CI and a portfolio case study.

## 13. Known limitations (summary)

The full register is in [assumptions_and_limitations.md](assumptions_and_limitations.md). The main ones:
- Public data can't observe proprietary economics, fleet costs, partnerships, safety performance or company strategy.
- MSA-wide averages blur the differences between urban core and periphery.
- Regulatory evidence is qualitative, changes frequently, and multi-state metros complicate state-to-market mapping.
- Sources come from different vintages.
- Current deployments reflect company strategy and history, not only market fit. They are therefore used only as a reasonableness check.
- A top-35-by-population universe excludes smaller markets where some modes (notably drones) actually operate.
- Readiness scores (future) will be decision models built on explicit assumptions, not objective truth.

## 14. Change log

| Date | Change | Reason |
|---|---|---|
| 2026-09-29 | Initial scope contract | Phase 1 |
