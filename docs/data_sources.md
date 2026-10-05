# Data Sources, Feature Feasibility, and Geography Mapping

**Status:** Phase 1 research artifact · **Research/access date for all entries:** 2026-09-29 unless stated otherwise

This document catalogs every candidate source considered in Phase 1. For each source it assesses whether the source can support the decision framework defined in [project_scope.md](project_scope.md). No data has been ingested yet. No features, weights or scores have been finalized.

**Verification convention**

| Mark | Meaning |
|---|---|
| **V** | Verified against the official page or file cited |
| **I** | Inferred from official file contents, but not stated in words by the publisher |
| **U** | Unverified. Must be confirmed before or during Phase 3 ingestion |

**Verdicts:**
- **GO** means usable as intended.
- **PROXY** means usable only as an imperfect stand-in, or only after a documented condition is met.
- **DROP** means not used. The reason is recorded.

**Usage categories:**
- **OBSERVED FEATURE**: an input to features.
- **CROSSWALK**: used for geography or keys only.
- **QUALITATIVE EVIDENCE**: regulatory evidence, coded without a numeric score.
- **EXTERNAL VALIDATION**: used only to check the reasonableness of outputs, never as an input.

**Access notes from Phase 1:**
- The Census Data API now rejects data requests without a key (V: a live request returned "Missing Key"). Metadata endpoints still work without one.
- Several FAA, NHTSA and Federal Register pages block automated fetching (HTTP 403). Facts from those pages are marked V only where the page or file was actually read, whether by a browser-agent request or the live ArcGIS service.
- Spot-checks from this machine on 2026-09-29 returned HTTP 200 for:
  - list1_2023.xlsx
  - cbp23msa.zip
  - the NOAA normals station CSV
  - the SLD v3 zip
  - the 2024 Gazetteer tracts file
  - the UA–county relationship file
  - the ACS variable metadata
- Two spot-checks failed. The BLS OEWS zip returned 403 because BLS blocks automated agents; the research pass verified it earlier with a HEAD request. The FAA NASR zip returned 503, a temporary server outage; the research pass verified it earlier. Both are re-checked in Phase 3.

---

## Contents
1. [Master source index](#1-master-source-index)
2. [Detailed source records](#2-detailed-source-records)
3. [Feature-feasibility matrix](#3-feature-feasibility-matrix)
4. [Source-to-feature mapping](#4-source-to-feature-mapping)
5. [Geography-mapping table](#5-geography-mapping-table)
6. [Population-density options](#6-population-density-options)
7. [Regulatory evidence framework](#7-regulatory-evidence-framework)
8. [Deployment evidence framework](#8-deployment-evidence-framework)
9. [Vintage alignment](#9-vintage-alignment)
10. [Candidate features without a defensible source](#10-candidate-features-without-a-defensible-source)
11. [Phase 3 retrieval findings](#11-phase-3-retrieval-findings-2026-10-0405)

---

## 1. Master source index

| ID | Source | Provider | Usage category | Verdict |
|---|---|---|---|---|
| S-01 | PEP Vintage 2025 CBSA population totals | U.S. Census Bureau | CROSSWALK + OBSERVED FEATURE | **GO** |
| S-02 | CBSA delineation file, July 2023 (list1_2023) | U.S. Census Bureau / OMB | CROSSWALK | **GO** |
| S-03 | ACS 5-year 2020–2024, MSA level (Detailed + Subject tables) | U.S. Census Bureau | OBSERVED FEATURE | **GO** |
| S-04 | ACS 5-year 2020–2024, tract level | U.S. Census Bureau | OBSERVED FEATURE (density input) | **GO** |
| S-05 | Census Gazetteer files, 2024 (CBSA, county, tract, UA) | U.S. Census Bureau | CROSSWALK (land area) | **GO** |
| S-06 | 2020 Census Urban Areas + UA-to-county relationship file | U.S. Census Bureau | CROSSWALK / OBSERVED FEATURE | **PROXY** |
| S-07 | TIGER/Line shapefiles (CBSA, tract), 2024 | U.S. Census Bureau | CROSSWALK (spatial overlays) | **GO** |
| S-08 | County Business Patterns 2023 | U.S. Census Bureau | OBSERVED FEATURE | **GO** |
| S-09 | BLS OEWS, May 2025, metropolitan areas | U.S. Bureau of Labor Statistics | OBSERVED FEATURE | **GO** |
| S-10 | BLS QCEW, 2025 annual averages | U.S. Bureau of Labor Statistics | OBSERVED FEATURE (backup) | **PROXY** |
| S-11 | BEA Regional Price Parities, 2024 | U.S. Bureau of Economic Analysis | OBSERVED FEATURE (optional) | **PROXY** |
| S-12 | NOAA U.S. Climate Normals 1991–2020, annual/seasonal | NOAA NCEI | OBSERVED FEATURE | **GO** |
| S-13 | NOAA U.S. Climate Normals 1991–2020, hourly (wind) | NOAA NCEI | OBSERVED FEATURE | **GO** |
| S-14 | NOAA Local Climatological Data v2 | NOAA NCEI | OBSERVED FEATURE | **PROXY** |
| S-15 | NOAA Storm Events Database | NOAA NCEI | OBSERVED FEATURE | **DROP** |
| S-16 | NOAA GHCN-Daily | NOAA NCEI | OBSERVED FEATURE | **DROP** |
| S-17 | FAA CY2025 Passenger Boarding (Enplanement) Data | FAA | OBSERVED FEATURE | **GO** |
| S-18 | BTS T-100 Segment (All Carriers) | USDOT BTS | OBSERVED FEATURE | **PROXY** |
| S-19 | FAA NASR 28-Day Subscription, APT data | FAA | CROSSWALK | **GO** |
| S-20 | BTS Aviation Support Tables: Master Coordinate | USDOT BTS | CROSSWALK | **DROP** |
| S-21 | EPA Smart Location Database v3.0 | U.S. EPA | OBSERVED FEATURE | **GO** |
| S-22 | EPA National Walkability Index | U.S. EPA | OBSERVED FEATURE | **GO** |
| S-23 | FAA UAS Facility Maps (UASFM) | FAA | OBSERVED FEATURE | **PROXY** |
| S-24 | FAA National Security UAS Flight Restrictions / Prohibited Areas | FAA | OBSERVED FEATURE | **PROXY** |
| S-25 | FAA Class Airspace | FAA | CROSSWALK / OBSERVED FEATURE | **PROXY** |
| S-26 | FAA Part 107 Waivers Issued | FAA | — | **DROP** |
| S-27 | FAA-Recognized Identification Areas (FRIAs) | FAA | — | **DROP** |
| S-28 | State statutes (official legislature code sites) | State legislatures | QUALITATIVE EVIDENCE | **GO** |
| S-29 | State agency AV/PDD program pages (DMV / DOT / PUC) | State agencies | QUALITATIVE EVIDENCE | **GO** |
| S-30 | Federal AV/UAS framework (Federal Register, eCFR, NHTSA, FAA) | USDOT / NHTSA / FAA | QUALITATIVE EVIDENCE (national context) | **GO** |
| S-31 | NCSL Autonomous Vehicles Legislation Database | NCSL (non-governmental) | QUALITATIVE EVIDENCE (discovery only) | **PROXY** |
| S-32 | NCSL Unmanned Aircraft State Law Landscape | NCSL (non-governmental) | QUALITATIVE EVIDENCE (discovery only) | **PROXY** |
| S-33 | IIHS "Highly automated vehicle laws" table | IIHS (non-governmental) | QUALITATIVE EVIDENCE (cross-check only) | **PROXY** |
| S-34 | BTS "Automated Vehicle Legislation by State" (2019) | USDOT BTS | — | **DROP** |
| S-35 | CA DMV AV permit holders lists | California DMV | EXTERNAL VALIDATION | **GO** |
| S-36 | CPUC AV programs + quarterly reporting | California PUC | EXTERNAL VALIDATION | **GO** |
| S-37 | FAA drone-delivery environmental reviews (NEPA) | FAA | EXTERNAL VALIDATION | **GO** |
| S-38 | Operator official service-area pages and newsrooms | Operators (see §2) | EXTERNAL VALIDATION | **GO** (per-operator verdicts in the record) |
| S-39 | Partner/platform announcements (e.g., ride-hail platform newsrooms, investor releases) | Platforms | EXTERNAL VALIDATION | **PROXY** |

Counts: 39 sources: 21 GO · 12 PROXY · 6 DROP. S-38 also carries per-operator sub-verdicts.

---

## 2. Detailed source records

Each record has the same fields. The research/access date is 2026-09-29 for all records unless stated otherwise. "Crosswalk" means the steps needed to reach `market_id` (the CBSA code).

### A. Census Bureau and federal statistical sources

#### S-01: PEP Vintage 2025 CBSA population totals
| Field | Value |
|---|---|
| Provider | U.S. Census Bureau, Population Estimates Program |
| Official URL | https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/metro/totals/cbsa-est2025-alldata.csv (V). Landing page: https://www.census.gov/data/tables/time-series/demo/popest/2020s-total-metro-and-micro-statistical-areas.html |
| Dataset | Metropolitan and Micropolitan Statistical Area Population Totals: 2020–2025 |
| Release date | March 2026 (press release 2026-03-26). File `Last-Modified` is 2026-03-26 (V) |
| Pinned vintage | **Vintage 2025**, `POPESTIMATE2025` (July 1, 2025). SHA-256 `BF6FAD83753456413D047D1ACEBEB434BD067EBA9D6D0BE62B3F737AD1301852` |
| Update frequency | Annual. Vintage 2026 is expected around March 2027 (U). Not adopted: the vintage is frozen |
| Access method | CSV download, no credentials |
| Native geography / grain | CBSA, Metropolitan Division and county rows, marked by `LSAD`. One row per geography |
| Useful fields | `CBSA`, `MDIV`, `STCOU`, `NAME`, `LSAD`, `ESTIMATESBASE2020`, `POPESTIMATE2020`–`POPESTIMATE2025`, components of change (V) |
| Aggregation | None. Filter `LSAD = "Metropolitan Statistical Area"` |
| Crosswalk | Native CBSA. The county rows (`STCOU`) also give the county→CBSA membership for the pinned delineation |
| Delineation | Matches the OMB July 2023 delineation (Bulletin 23-01) exactly. There are 387 MSAs and 538 micropolitan areas, 2023-style titles, and Connecticut planning regions (I). No census.gov page found states this in words (U) |
| License / terms | U.S. Government work. The Census API catalog lists CC0 for Census datasets (V for the ACS catalog entry) |
| Limitations | These are estimates, not counts. The file excludes Puerto Rico, which is published separately |
| Phase 1 checks | 2,806 rows. 387 MSAs with no duplicate CBSA. The 319 counties in the top 35 sum exactly to their MSA totals (0 mismatches) |
| Verdict | **GO** |

#### S-02: CBSA delineation file, July 2023
| Field | Value |
|---|---|
| Provider | U.S. Census Bureau, from OMB Bulletin No. 23-01 |
| Official URL | https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx (V, HTTP 200, Last-Modified 2023-08-04). About page: https://www.census.gov/programs-surveys/metro-micro/about/delineation-files.html |
| Dataset | List 1. Core Based Statistical Areas (CBSAs), Metropolitan Divisions, and Combined Statistical Areas (CSAs), July 2023 |
| Release date | July 2023 delineation. File modified 2023-08-04 |
| Pinned vintage | July 2023. This is the current delineation; no newer one has been published (V) |
| Update frequency | Irregular OMB bulletins |
| Access method | XLSX download. The header is on row 3. No credentials |
| Native geography / grain | One row per county (or county-equivalent) × CBSA |
| Useful fields | `CBSA Code`, `Metropolitan Division Code`, `CSA Code`, `CBSA Title`, `Metropolitan/Micropolitan Statistical Area`, `County/County Equivalent`, `State Name`, `FIPS State Code`, `FIPS County Code`, `Central/Outlying County` (V) |
| Aggregation | None |
| Crosswalk | This file *is* the county→CBSA crosswalk |
| License / terms | U.S. Government work |
| Limitations | Connecticut uses 9 planning regions (09110–09190) instead of the 8 legacy counties, since the 2022 change (V). **None of the 35 markets contains a Connecticut county-equivalent** (V, from S-01). Sources keyed to legacy CT counties or pre-2023 delineations need re-mapping (see §5) |
| Usage category | CROSSWALK |
| Verdict | **GO** |

#### S-03: ACS 5-year 2020–2024, MSA level
| Field | Value |
|---|---|
| Provider | U.S. Census Bureau, American Community Survey |
| Official URL | https://api.census.gov/data/2024/acs/acs5 (Detailed) and https://api.census.gov/data/2024/acs/acs5/subject (Subject) (V). Release notes: https://www.census.gov/programs-surveys/acs/news/updates/2026.html |
| Dataset | ACS 5-Year Estimates, 2020–2024 (`ACSDT5Y2024`, `ACSST5Y2024`) |
| Release date | 2026-01-29, delayed from the usual December (V) |
| Pinned vintage | **2020–2024 5-year.** The 2021–2025 5-year had not been released on 2026-09-29 (`/data/2025/acs/acs5` returns 404, V). The 2025 ACS 1-year release date is "being determined" under a new disclosure-avoidance order (V, notice dated 2026-08-06) |
| Update frequency | Annual (currently delayed) |
| Access method | Census Data API. **An API key is required** (V). data.census.gov and the Summary File are alternatives |
| Native geography / grain | `metropolitan statistical area/micropolitan statistical area` (summary level 310). One row per CBSA per variable, with a margin of error (`_M`) |
| Useful fields (V) | Detailed tables:<br>• `B01003_001E` population<br>• `B11001_001E` households<br>• `B19013_001E` median household income (2024 inflation-adjusted dollars)<br>• `B08301_001E` workers 16+ total<br>• `_003E` drove alone<br>• `_010E` public transportation<br>• `_016E` **taxi or ride-hailing**<br>• `_018E` bicycle<br>• `_019E` walked<br>• `_021E` worked from home<br>• `B08201_001E`–`_006E` households by vehicles available (0/1/2/3/4+)<br>• `B25044_003E` / `_010E` zero-vehicle owner / renter households<br>• `B25046_001E` aggregate vehicles<br>• `B08013_001E` aggregate travel time<br>• `B08303_001E` travel-time universe<br>• `B25024_001E`–`_011E` units in structure (`_002E` 1-unit detached)<br>• `B25003_001E` / `_002E` tenure / owner-occupied<br><br>Subject table:<br>• `S0801_C01_046E` mean travel time to work (workers who did not work from home) |
| Aggregation | None at MSA level |
| Crosswalk | Native CBSA. 2023 ACS products use OMB Bulletin 23-01 (V). That the 2024 products do too is inferred from the 2024-01-01 geography reference date (I). **To confirm in Phase 3:** query CBSA codes and check that they match S-01 |
| License / terms | CC0 per the Census API catalog (V) |
| Limitations | Pooled 5-year estimates with sampling error. The 2020–2024 window includes pandemic years, which inflate work-from-home and distort commute measures. The small taxi/ride-hailing counts have relatively large MOEs. `B08303` universe metadata was blank in `groups.json`; the S0801 label implies non-WFH workers (U) |
| Usage category | OBSERVED FEATURE |
| Verdict | **GO** |

#### S-04: ACS 5-year 2020–2024, tract level
| Field | Value |
|---|---|
| Provider / URL | Same as S-03. Geography `tract` (summary level 140), which requires `state` and allows the `county:*` wildcard (V) |
| Dataset / vintage | ACS 5-year 2020–2024 (2020-census tract geography) |
| Access method | API, one call per state (31 state FIPS). Key required |
| Native geography / grain | Census tract. One row per tract |
| Useful fields | `B01003_001E` (for density); optionally `B25024_*` and `B11001_001E` |
| Scale | **38,579 tracts** across the 319 counties of the 35 markets, including 65 with zero land area (computed from official files during research). NY 35620 has the most (4,928); Nashville has the fewest (434) |
| Aggregation | Tract → county (`GEOID[0:5]`) → CBSA (S-02). Population-weighted statistics are computed in Phase 4/6 |
| Crosswalk | Tracts nest in counties and counties nest in CBSAs, so the assignment is exact |
| License / terms | CC0 (V) |
| Limitations | Tract population MOEs are large relative to small tracts. Zero-land-area tracts must be excluded, and each exclusion documented |
| Usage category | OBSERVED FEATURE (input to derived density) |
| Verdict | **GO** |

#### S-05: Census Gazetteer files, 2024
| Field | Value |
|---|---|
| Provider | U.S. Census Bureau, Geography Division |
| Official URL | https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/ (V). Examples: `2024_Gaz_tracts_national.zip` (HTTP 200, Last-Modified 2024-08-30), `2024_Gaz_cbsa_national.zip`, `2024_Gaz_counties_national.zip`, `2024_Gaz_ua_national.zip` |
| Release date | 2024-08-30 (tracts file). 2025 and 2026 Gazetteers also exist |
| Pinned vintage | **2024**, to match the ACS 2024 geography |
| Update frequency | Annual |
| Access method | Zipped TXT, no credentials |
| Native geography / grain | One row per geography (CBSA: 935 rows; tracts: 85,396 rows) |
| Useful fields (V) | CBSA: `GEOID`, `NAME`, `CBSA_TYPE`, `ALAND`, `ALAND_SQMI`, `AWATER_SQMI`, `INTPTLAT`, `INTPTLONG`. Tracts: `USPS`, `GEOID`, `ALAND`, `ALAND_SQMI`, `INTPTLAT`, `INTPTLONG` |
| Aggregation / crosswalk | Tract GEOID → county → CBSA via S-02 |
| License / terms | U.S. Government work |
| Limitations | Land area only; population must come from S-03 or S-04 |
| Usage category | CROSSWALK |
| Verdict | **GO** |

#### S-06: 2020 Census Urban Areas and the UA-to-county relationship file
| Field | Value |
|---|---|
| Provider | U.S. Census Bureau |
| Official URL | Criteria: https://www.census.gov/programs-surveys/geography/guidance/geo-areas/urban-rural.html (V). Relationship file: https://www2.census.gov/geo/docs/maps-data/data/rel2020/ua/tab20_ua20_county20_natl.txt (V, HTTP 200, Last-Modified 2023-02-10) |
| Dataset | 2020 Census Urban Areas; UA20–County20 relationship file |
| Pinned vintage | 2020 Census urban areas. Criteria: final Federal Register notice 2022-03-24 (V); ≥2,000 housing units or ≥5,000 people. The urbanized-area / urban-cluster split is gone |
| Update frequency | Decennial |
| Access method | Pipe-delimited TXT. ACS also publishes data at `urban area` geography (400) |
| Native geography / grain | One row per UA × county part |
| Useful fields (V) | `GEOID_UA_20`, `NAMELSAD_UA_20`, `AREALAND_UA_20`, `GEOID_COUNTY_20`, `AREALAND_PART`, `AREAWATER_PART` |
| Aggregation | Principal UA(s) → county parts → CBSA |
| Crosswalk | **No official UA→CBSA file exists** (V). The relationship file gives land area per county part, **not population** |
| License / terms | U.S. Government work |
| Limitations | UAs cross CBSA boundaries. Choosing the "principal" UA is a judgment call. The file uses 2020 counties (legacy CT counties, which do not affect the 35 markets) |
| Usage category | CROSSWALK / OBSERVED FEATURE (urban-core density option) |
| Verdict | **PROXY** |

#### S-07: TIGER/Line shapefiles, 2024
| Field | Value |
|---|---|
| Provider | U.S. Census Bureau |
| Official URL | https://www2.census.gov/geo/tiger/TIGER2024/ (`CBSA/`, `TRACT/`); 2025 folders also exist (V, from research) |
| Pinned vintage | 2024, to match S-05 and S-03 |
| Access method | Zipped shapefiles, no credentials |
| Native geography / grain | Polygon per geography |
| Useful fields | `GEOID`, `NAME`, geometry |
| Use | Only for point-in-polygon (airports, weather stations) and area overlays (UASFM). Land areas come from S-05 |
| License / terms | U.S. Government work |
| Limitations | Adds a geospatial dependency in Python (to be decided in Phase 2/3). That the 2024 CBSA shapes follow the July 2023 delineation is inferred, not confirmed (U) |
| Usage category | CROSSWALK |
| Verdict | **GO** |

#### S-08: County Business Patterns 2023
| Field | Value |
|---|---|
| Provider | U.S. Census Bureau |
| Official URL | API: https://api.census.gov/data/2023/cbp (key required). Flat file: https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23msa.zip (V, HTTP 200, Last-Modified 2025-06-26). Status page: https://www.census.gov/programs-surveys/cbp/data.html |
| Dataset | County Business Patterns 2023, metro-area file |
| Release date | 2025-06-26 (V) |
| Pinned vintage | **2023.** CBP 2024 has "no planned release date" because of the order prohibiting noise infusion (V, page revised 2026-09-16) |
| Update frequency | Annual (currently suspended) |
| Access method | Flat file (no key) or API (key) |
| Native geography / grain | CBSA × NAICS × legal form of organization |
| Useful fields (V) | API: `ESTAB`, `EMP`, `PAYANN`, `NAICS2017`, `EMPSZES`. Flat file: `msa`, `naics`, `est`, `emp`, `emp_nf`, `ap`<br>NAICS codes:<br>• `44-45` Retail trade<br>• `445` Food and beverage retailers<br>• `722` Food services and drinking places<br>• `7225` Restaurants and other eating places<br>• `492` / `4921` Couriers |
| Check value | CBSA 35620, 2023: 52,247 establishments in NAICS 722 (V, research pass) |
| Aggregation | None |
| Crosswalk | Native CBSA. The 2023 file holds 925 CBSAs (387 metro + 538 micro), consistent with July 2023 (I). API metadata shows a 2022-01-01 reference date, so confirm the codes against S-01 in Phase 3 (U) |
| License / terms | U.S. Government work |
| Limitations | Noise infusion (flags G/H/J). Some cells withheld. Excludes the self-employed and most government. Establishments are not the same as delivery demand. NAICS 2017 basis (V) |
| Usage category | OBSERVED FEATURE |
| Verdict | **GO** |

#### S-09: BLS Occupational Employment and Wage Statistics, May 2025
| Field | Value |
|---|---|
| Provider | U.S. Bureau of Labor Statistics |
| Official URL | https://www.bls.gov/oes/. Metro file: https://www.bls.gov/oes/special-requests/oesm25ma.zip. Area definitions: https://www.bls.gov/oes/2025/may/oessrcma.htm (V, research pass). **Phase 3 correction:** the 403 seen in Phase 1 came from a browser-style User-Agent. The ingestion pipeline's descriptive User-Agent downloaded the file successfully on 2026-10-04 (see §11) |
| Dataset | OEWS May 2025, metropolitan and nonmetropolitan area estimates |
| Release date | 2026-05-15 (V) |
| Pinned vintage | **May 2025** |
| Update frequency | Annual |
| Access method | Zipped XLSX, no credentials |
| Native geography / grain | MSA × occupation (SOC) |
| Useful fields | Occupation codes (V):<br>• 53-3053 Shuttle drivers and chauffeurs<br>• 53-3054 Taxi drivers<br>• 53-3033 Light truck drivers<br>• 53-3031 Driver/sales workers<br>• 43-5021 Couriers and messengers<br>• 35-3023 Fast food and counter workers<br><br>Wage column names (e.g., mean/median hourly wage) must be confirmed on first download (U) |
| Aggregation | None |
| Crosswalk | Native. "The May 2025 OEWS estimates use the metropolitan area definitions in OMB Bulletin 23-01" (V), so codes match S-01 |
| License / terms | Public domain (V, https://www.bls.gov/opub/copyright-information.htm) |
| Limitations | A 3-year pooled panel (Nov 2022–May 2025). **Excludes the self-employed**, so gig ride-hail and delivery drivers are largely missing. Small occupations may be suppressed. Whether Metropolitan Divisions are published is unknown (U) |
| Usage category | OBSERVED FEATURE (labor-cost proxy) |
| Verdict | **GO** |

#### S-10: BLS QCEW, 2025 annual averages
| Field | Value |
|---|---|
| Provider | U.S. Bureau of Labor Statistics |
| Official URL | https://www.bls.gov/cew/. MSA crosswalk: https://www.bls.gov/cew/classifications/areas/county-msa-csa-crosswalk.htm (V) |
| Pinned vintage | 2025 annual averages (V: released; latest quarter Q1 2026; next release 2026-12-02) |
| Access method | CSV / data files, no credentials |
| Native geography / grain | County and MSA (`C` + 4-digit codes, e.g., `C3562`) × NAICS × ownership |
| Useful fields | Industry employment, establishments, average weekly wage (e.g., NAICS 7225, 492) |
| Crosswalk | "NAICS-based data from 2024 forward use the July 2023 CBSA delineations" (V). Pre-2024 data use the 2013 delineation |
| License / terms | Public domain (V) |
| Limitations | Gives industry wages, not occupation wages. Overlaps with S-08 and S-09 |
| Usage category | OBSERVED FEATURE (backup only) |
| Verdict | **PROXY.** Use only if OEWS suppression leaves gaps |

#### S-11: BEA Regional Price Parities, 2024
| Field | Value |
|---|---|
| Provider | U.S. Bureau of Economic Analysis |
| Official URL | https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area (V) |
| Release date | 2026-02-19 (2024 data); next release 2026-12-10 (V) |
| Pinned vintage | 2024, if MSA coverage is confirmed |
| Access method | Interactive tables / API (the BEA API key requirement is U) |
| Native geography / grain | State and (possibly) MSA |
| Useful fields | RPP all-items index |
| Crosswalk | Unknown delineation (U) |
| License / terms | U.S. Government work |
| Limitations | **BEA announced it has discontinued publishing statistics for metropolitan statistical areas, while stating RPPs "will continue to be published by state and local areas"** (V). Whether 2024 MSA RPPs exist is **ambiguous** (U) |
| Usage category | OBSERVED FEATURE (optional cost-of-living adjustment to income) |
| Verdict | **PROXY.** Adopt only after confirming a 2024 MSA table with 2023-delineation codes. Otherwise DROP |

### B. Weather and climate (NOAA NCEI)

#### S-12: U.S. Climate Normals 1991–2020, annual/seasonal
| Field | Value |
|---|---|
| Provider | NOAA National Centers for Environmental Information |
| Official URL | https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals. Data: https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/ (V; station file `access/USW00094846.csv` returned HTTP 200) |
| Dataset | U.S. Annual/Seasonal Climate Normals (1991–2020), DOI 10.25921/4ek7-fk11 (V) |
| Release date | Published 2021-05-04; revised 2023-05-15 (V) |
| Pinned vintage | **1991–2020, v1.0.1** (archive `..._c20230404.tar.gz`) (V) |
| Update frequency | Static 30-year normal |
| Access method | Per-station CSV, archive tarball, or NCEI Access Data Service API. **No credentials** (V) |
| Native geography / grain | Weather station (point). One row of 30-year statistics per station |
| Useful fields (V) | • `ANN-PRCP-NORMAL`<br>• `ANN-PRCP-AVGNDS-GE001HI`, `-GE010HI`, `-GE050HI`, `-GE100HI` (days with precipitation ≥ 0.01/0.10/0.50/1.00 in)<br>• `ANN-SNOW-NORMAL`<br>• `ANN-SNOW-AVGNDS-GE010TI` (days with snowfall ≥ 1.0 in)<br>• `ANN-SNWD-AVGNDS-GE001WI` (days with snow depth ≥ 1 in)<br>• `ANN-TMAX-AVGNDS-GRTH090` (days with Tmax ≥ 90 °F)<br>• `ANN-TMIN-AVGNDS-LSTH032` (days with Tmin ≤ 32 °F)<br>• `ANN-TAVG-NORMAL`<br>• station metadata: `STATION`, `LATITUDE`, `LONGITUDE`, `ELEVATION`, `NAME`<br>• completeness flags: `comp_flag_*`, `years_*` |
| Aggregation | Station → CBSA per the station-mapping rule (§5; to be decided in Phase 3) |
| Crosswalk | Point-in-polygon against the S-07 CBSA shapes, or an explicit designated-station list |
| License / terms | NOAA/NCEI no-warranty statement (V). The public-domain open-data policy was not read directly (U) |
| Limitations | A station represents a point, not a metro. **Snow normals are absent at some stations** (e.g., Los Angeles Intl USW00023174 and Phoenix Sky Harbor USW00023183, V), so "missing" must be distinguished from "zero". Completeness flags vary |
| Usage category | OBSERVED FEATURE |
| Verdict | **GO** |

#### S-13: U.S. Climate Normals 1991–2020, hourly (wind)
| Field | Value |
|---|---|
| Provider / URL | NOAA NCEI. https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/ (V) |
| Pinned vintage | 1991–2020 |
| Access method | Per-station CSV, no credentials |
| Native geography / grain | Station × hour of year (8,760 rows). About 467 stations, mostly first-order airports (V) |
| Useful fields (V) | `HLY-WIND-AVGSPD`, `HLY-WIND-PCTCLM`, `HLY-WIND-VCTDIR`, `HLY-WIND-VCTSPD`, `HLY-WIND-1STDIR/1STPCT/2NDDIR/2NDPCT` |
| Aggregation | Hours → annual mean wind speed per station → CBSA |
| Crosswalk | Same station rule as S-12. Coverage is limited to first-order stations |
| License / terms | As S-12 |
| Limitations | Mean wind is a coarse proxy for the gust and turbulence limits that matter to drone operations. Wind is the only field used from this product |
| Usage category | OBSERVED FEATURE |
| Verdict | **GO** (source). The drone wind *feature* built from it is a PROXY (§3) |

#### S-14: Local Climatological Data v2
| Field | Value |
|---|---|
| Provider / URL | NOAA NCEI. https://www.ncei.noaa.gov/products/land-based-station/local-climatological-data. Files: `https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access/{YEAR}/LCD_{STATION}_{YEAR}.csv` (V) |
| Pinned vintage | Would be a self-built multi-year window (e.g., 2016–2025). Not pinned |
| Access method | CSV per station-year, no credentials |
| Native geography / grain | Station × hour/day/month |
| Useful fields (V) | `HourlyWindSpeed`, `HourlyWindGustSpeed`, `DailyPeakWindSpeed`, `DailySnowDepth`, `MonthlyNumberDaysWithThunderstorms`, `MonthlyNumberDaysWithHeavyFog`, `HourlyVisibility` |
| License / terms | Not stated on the page (U) |
| Limitations | LCD v1 is deprecated (source ISD discontinued in August 2025) (V). v2 units are presumed metric (U). Any statistic would be computed by us and need its own methodology |
| Usage category | OBSERVED FEATURE |
| Verdict | **PROXY.** Optional, only for drone gust frequency if Phase 5 shows mean wind is insufficient |

#### S-15: NOAA Storm Events Database
| Field | Value |
|---|---|
| Provider / URL | NOAA NCEI. https://www.ncei.noaa.gov/stormevents/. Bulk: https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/ (V) |
| Vintage | Yearly files reissued with creation dates (e.g., `d2025_c20260819`) (V) |
| Native geography / grain | Event × county or forecast zone |
| Useful fields (V) | `EVENT_TYPE`, `STATE_FIPS`, `CZ_TYPE`, `CZ_FIPS`, `BEGIN_DATE_TIME`, `DAMAGE_PROPERTY`, `MAGNITUDE`, `BEGIN_LAT`, `BEGIN_LON` |
| Access method / credentials / license | CSV.gz, no credentials, U.S. Government work |
| Limitations | Reporting-driven: dense metros report more events, so counts correlate with population. Zone-coded events do not map cleanly to counties |
| Usage category | OBSERVED FEATURE |
| Verdict | **DROP.** Reporting bias makes it indefensible as a cross-market feature |

#### S-16: GHCN-Daily
| Field | Value |
|---|---|
| Provider / URL | NOAA NCEI. https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily (V) |
| Vintage / frequency | Rebuilt weekly |
| Native geography / grain | Station × day. `TMAX`, `TMIN`, `PRCP`, `SNOW`, `SNWD` (V) |
| Access / credentials / license | HTTPS, none, U.S. Government work |
| Limitations | The normals (S-12) are already derived from it. Recomputing adds work without adding defensible value for a cross-section |
| Usage category | OBSERVED FEATURE |
| Verdict | **DROP.** Revisit only as a documented backfill if a market's snow normal is missing and no in-CBSA fallback station exists |

### C. Aviation

#### S-17: FAA CY2025 Passenger Boarding (Enplanement) Data
| Field | Value |
|---|---|
| Provider | Federal Aviation Administration, Office of Airports |
| Official URL | https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger (V, via browser-agent request) |
| Dataset | `arp-cy2025-commercial-service-enplanements.xlsx` (also all-enplanements and all-cargo) (V) |
| Release date | Updated 2026-09-24 (V) |
| Pinned vintage | **CY2025.** Whether it is labeled final is ambiguous. The discrepancy deadline (2026-08-14) has passed and the file was updated afterward (U) |
| Update frequency | Annual. Preliminary CY2026 is expected June 2027 (V) |
| Access method | XLSX download, no credentials |
| Native geography / grain | Airport × calendar year |
| Useful fields (V) | `Rank`, `RO`, `ST`, `Locid`, `City`, `Airport Name`, `S/L`, `Hub`, `CY 25 Enplanements`, `CY 24 Enplanements`, `% Change` |
| Aggregation | Sum over the commercial-service airports assigned to a CBSA |
| Crosswalk | `Locid` → S-19 coordinates → CBSA polygon (S-07). **No county field in the file** |
| License / terms | U.S. Government work |
| Limitations | Connecting hubs inflate enplanements relative to local demand. Totals rows must be excluded. Strongly correlated with population |
| Usage category | OBSERVED FEATURE |
| Verdict | **GO** |

#### S-18: BTS T-100 Segment (All Carriers)
| Field | Value |
|---|---|
| Provider / URL | USDOT BTS. https://www.transtats.bts.gov/ (download page for T-100 Segment). Release info: https://transtats.bts.gov/releaseinfo.asp (V) |
| Vintage | Latest data 06/2026, released 2026-09-14 (V). Would pin calendar 2025 |
| Access method | Manual field-selection download. **No official API or bulk endpoint found** (U that none exists). No credentials |
| Native geography / grain | Carrier × origin × destination × month |
| Useful fields | Web UI names `Passengers`, `DepPerformed`, `Seats`, `Origin`, `OriginAirportID`, `OriginCityMarketID` (V). CSV header names (U) |
| Crosswalk | Airport → CBSA as for S-17. The DOT "City Market ID" is **not** a CBSA equivalent |
| License / terms | U.S. Government work |
| Limitations | Segment passengers count through-passengers twice. A manual download is hard to reproduce. Duplicates S-17 for passenger volume |
| Usage category | OBSERVED FEATURE |
| Verdict | **PROXY.** Not planned for the MVP. Use only if a departures/connectivity feature is needed beyond S-17 |

#### S-19: FAA NASR 28-Day Subscription, APT data
| Field | Value |
|---|---|
| Provider / URL | FAA Aeronautical Information Services. https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/. File: https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip (V, research pass; the spot-check from this machine returned 503, a temporary outage) |
| Pinned vintage | Edition effective **2026-09-03** (V) |
| Update frequency | 28-day cycle |
| Access method | Zipped CSV (`APT_BASE.csv`), no credentials |
| Native geography / grain | Airport (point) |
| Useful fields (V) | `ARPT_ID`, `ICAO_ID`, `ARPT_NAME`, `CITY`, `STATE_CODE`, `COUNTY_NAME`, `COUNTY_ASSOC_STATE`, `LAT_DECIMAL`, `LONG_DECIMAL`, `SITE_TYPE_CODE`, `FACILITY_USE_CODE`, `ARPT_STATUS`, `EFF_DATE` |
| Crosswalk | Coordinates → CBSA polygon. **County is a name, not a FIPS code**, with pitfalls: "DADE" for Miami-Dade, "ST LOUIS" being ambiguous between city and county, and `CITY` being unreliable. Point-in-polygon is preferred |
| License / terms | U.S. Government work |
| Limitations | The edition changes every 28 days; pin one edition |
| Usage category | CROSSWALK |
| Verdict | **GO** |

#### S-20: BTS Master Coordinate table
| Field | Value |
|---|---|
| Provider / URL | USDOT BTS TranStats aviation support tables (V) |
| Fields (V) | `AirportID`, `Airport`, `AirportStateFips`, `CityMarketID`, `Latitude`, `Longitude`, `AirportIsLatest` |
| Native geography / grain | Airport × validity period. No county field |
| Access / license | Manual download, no credentials, U.S. Government work |
| Limitations | Only needed to join T-100 IDs. S-19 already provides the coordinates |
| Usage category | CROSSWALK |
| Verdict | **DROP.** Re-open only if S-18 is adopted |

### D. Built environment (EPA)

#### S-21: EPA Smart Location Database v3.0
| Field | Value |
|---|---|
| Provider | U.S. EPA Smart Growth Program |
| Official URL | https://www.epa.gov/smartgrowth/smart-location-mapping (V). Zip: https://edg.epa.gov/EPADataCommons/public/OA/SLD/SmartLocationDatabaseV3.zip (V, HTTP 200, Last-Modified 2021-06-08, about 553 MB). Service: https://geodata.epa.gov/arcgis/rest/services/OA/SmartLocationDatabase/MapServer (V) |
| Dataset | Smart Location Database, Version 3.0 |
| Release date | June 2021 (technical documentation "Updated June 2021") (V) |
| Pinned vintage | **v3.0.** This is the latest version. Inputs (V): ACS 2014–2018; LEHD LODES 2017; HERE NAVSTREETS 2018 Q4; GTFS feeds collected Jul–Sep 2020 |
| Update frequency | Irregular (v2 2014, v3 2021) |
| Access method | Geodatabase zip, or REST service (paged). No credentials |
| Native geography / grain | Census block group, 2019 TIGER boundaries (2010-census-based). Carries `GEOID10` and `GEOID20` (V; the GEOID20 alias is ambiguous) |
| Useful fields (V) | `GEOID10`, `STATEFP`, `COUNTYFP`, `TotPop`, `HH`, `Ac_Land`, `D1B` (gross population density), `D1C` (gross employment density), `D2A_EPHHM` (employment/household entropy), `D3B` (street intersection density), `D4A` (distance to transit stop), `NatWalkInd` |
| Aggregation | Block group → county (`STATEFP` + `COUNTYFP`) → CBSA (S-02). Population-weighted means using `TotPop` |
| Crosswalk | **Do not use the embedded `CBSA` field.** It follows a pre-2023 delineation. Re-assign by county FIPS (V: Dutchess County NY maps to pre-2023 code 39100 in the SLD) |
| License / terms | "A free resource available to the public" (V). No explicit license. Presumed U.S. Government work (U) |
| Limitations | Inputs date from 2017–2020 and predate the 2020 block groups. Transit coverage is limited to agencies that publish GTFS. Weights come from 2018 ACS population |
| Usage category | OBSERVED FEATURE |
| Verdict | **GO**, with the vintage caveat recorded |

#### S-22: EPA National Walkability Index
| Field | Value |
|---|---|
| Provider / URL | U.S. EPA. https://edg.epa.gov/EPADataCommons/public/OA/WalkabilityIndex.zip (V). Methodology: https://www.epa.gov/sites/default/files/2021-06/documents/national_walkability_index_methodology_and_user_guide_june2021.pdf (V) |
| Release date / vintage | June 2021. Same inputs as S-21 (it is the `NatWalkInd` field) |
| Method (V) | NWI = w/3 + x/3 + y/6 + z/6. The terms are the 1–20 quantile ranks of intersection density (D3B), transit proximity (D4A), employment mix (D2B_E8MIXA) and employment–household mix (D2A_EPHHM). Scale 1–20 |
| Native geography / grain | Block group |
| Aggregation / crosswalk | Population-weighted mean over block groups by county → CBSA (S-02) |
| Access / credentials / license | Zip or service, none, as S-21 |
| Limitations | A relative national rank with no absolute units. Block groups without transit appear to receive the lowest transit rank (I, from field alias). Sidewalk presence is not measured directly |
| Usage category | OBSERVED FEATURE |
| Verdict | **GO** (as a relative index) |

### E. Drone airspace (FAA)

#### S-23: FAA UAS Facility Maps
| Field | Value |
|---|---|
| Provider | FAA |
| Official URL | https://www.faa.gov/uas/commercial_operators/uas_facility_maps (V). FAQ: .../uas_facility_maps/faq (V). Service: https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/arcgis/rest/services/FAA_UAS_FacilityMap_Data/FeatureServer/0 (V) |
| Dataset | `FAA_UAS_FacilityMap_Data` (UAS Data Delivery System) |
| Release / vintage | Live service. On 2026-09-29 all 380,860 cells had `MAP_EFF` 9/3/2026 (V). Pin the 2026-09-03 chart cycle |
| Update frequency | 56-day aeronautical cycle (V) |
| Access method | ArcGIS REST (2,000-record pages), CSV/shapefile export. No credentials |
| Native geography / grain | Grid cell, 30″ × 30″ (about 0.25 sq mi) (V). Covers Class B/C/D/E surface areas |
| Useful fields (V) | `CEILING` (ft AGL; 0–400), `LATITUDE`, `LONGITUDE`, `APT1_FAAID`, `AIRSPACE_1`, `MAP_EFF` |
| Aggregation | Intersect cells with CBSA polygons (S-07) in an equal-area projection. Share of land area in any cell, and share at `CEILING = 0` |
| License / terms | Custom liability disclaimer; no reuse restriction noted (V) |
| Limitations | **Controlled airspace is not prohibition.** Operators obtain authorization (LAANC/DroneZone), and Part 135 operators work under exemptions. The maps are FAA "job aids" and "DO NOT authorize operations" (V). TFRs (stadiums, VIP movements) are not included |
| Usage category | OBSERVED FEATURE |
| Verdict | **PROXY.** Describes an airport-proximity airspace constraint, not whether drones can operate |

#### S-24: FAA National Security UAS Flight Restrictions / Prohibited Areas
| Field | Value |
|---|---|
| Provider / URL | FAA UAS Data Delivery System / ADDS open data (V: both services exist, updated 2026-09-28) |
| Pinned vintage | The chart cycle in effect at ingestion |
| Access method | ArcGIS services, no credentials |
| Native geography / grain | Polygon per restricted area |
| Useful fields | **Schema not verified** (U) |
| Aggregation | Share of CBSA land area inside restrictions |
| License / terms | U (presumed as S-25) |
| Limitations | Schema unverified. Small areas contribute little metro-level variation |
| Usage category | OBSERVED FEATURE |
| Verdict | **PROXY.** An optional add-on to S-23 once the schema is confirmed |

#### S-25: FAA Class Airspace
| Field | Value |
|---|---|
| Provider / URL | FAA ADDS. https://adds-faa.opendata.arcgis.com/datasets/faa::class-airspace. Service: https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/arcgis/rest/services/Class_Airspace/FeatureServer (V) |
| Vintage | Effective period 2026-09-03 to 2026-10-29 (V). 8-week cycle |
| Native geography / grain | Airspace polygon, with floor and ceiling |
| Useful fields (V) | `IDENT`, `NAME`, `CLASS`, `LOCAL_TYPE`, `UPPER_VAL`, `LOWER_VAL`, `CITY`, `STATE` |
| Access / credentials / license | ArcGIS, none, "for public use" (V) |
| Limitations | At the surface level it largely duplicates S-23 |
| Usage category | CROSSWALK / OBSERVED FEATURE |
| Verdict | **PROXY.** A cross-check for S-23 only |

#### S-26: FAA Part 107 Waivers Issued
| Field | Value |
|---|---|
| Provider / URL | FAA. https://www.faa.gov/uas/commercial_operators/part_107_waivers/waivers_issued (V) |
| Grain / fields (V) | Waiver. `Date of Issuance`, `Expiration Date`, `Company Name`, `Waivered Regulation`, PDF link |
| Vintage / access / license | Live HTML table, no download. U.S. Government work |
| Limitations | **No location field.** Holders are often nationwide. Some issuance dates are in the future (ambiguous) |
| Usage category | — |
| Verdict | **DROP.** Cannot be mapped to CBSA |

#### S-27: FAA-Recognized Identification Areas
| Field | Value |
|---|---|
| Provider / URL | FAA UDDS, `FAA_Recognized_Identification_Areas` (V) |
| Grain | Point/polygon site |
| Limitations | Hobby flying sites; not relevant to delivery |
| Verdict | **DROP** |

### F. Regulatory evidence (see §7 for the framework)

#### S-28: State statutes on official legislature sites
| Field | Value |
|---|---|
| Provider | State legislatures (31 jurisdictions: 30 states + DC) |
| Official URLs (sample, V) | • CA Veh. Code §38750: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=38750<br>• AZ ARS 28-9702: https://www.azleg.gov/ars/28/09702.htm<br>• FL §316.85: https://www.flsenate.gov/Laws/Statutes/2025/316.85<br>• FL §316.2071 (PDD): https://www.flsenate.gov/Laws/Statutes/2025/316.2071<br>• FL §330.41 (drones/critical infrastructure): https://www.flsenate.gov/Laws/Statutes/2025/330.41<br>• VA §46.2-908.1:1 (PDD): https://law.lis.virginia.gov/vacode/title46.2/chapter8/section46.2-908.1:1/<br>• PA Act 106 of 2020 (PDD; 75 Pa.C.S. §§8511–8522): https://www.legis.state.pa.us/WU01/LI/LI/US/HTM/2020/0/0106..HTM<br>• NC G.S. 20-175.15: https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_20/GS_20-175.15.html |
| Access gaps (V) | Georgia's official code (O.C.G.A. §40-8-11) has no stable official deep link; secondary hosting only. Texas statute pages returned only the site shell to automated fetches, so the text must be captured manually |
| Vintage | Point-in-time. Each record carries `effective_date`, `evidence_date` and `accessed_date` |
| Access method | Manual evidence capture into a curated CSV (schema in §7.4) |
| Native geography / grain | State × statute section |
| License / terms | Public law. Site terms vary |
| Limitations | Laws change often (e.g., CA SB 480 effective 2026-01-01; TX SB 2807 effective 2025-09-01). "Silent" is not the same as "prohibited". Interpretation is required |
| Usage category | QUALITATIVE EVIDENCE |
| Verdict | **GO** |

#### S-29: State agency AV/PDD program pages
| Field | Value |
|---|---|
| Provider | State DMVs, DOTs and PUCs |
| Official URLs (sample, V) | • CA DMV AV program: https://www.dmv.ca.gov/portal/vehicle-industry-services/autonomous-vehicles/<br>• CPUC AV programs: https://www.cpuc.ca.gov/regulatory-services/licensing/transportation-licensing-and-analysis-branch/autonomous-vehicle-programs<br>• TxDMV AV program: https://www.txdmv.gov/AVprogram (SB 2807 effective 2025-09-01; rules effective 2026-02-27) |
| Access method | Manual evidence capture |
| Native geography / grain | State × program |
| Limitations | A program's existence is not proof of permits issued, and permits are not proof of service. **Permit-holder lists are deployment evidence** (S-35/S-36, EXTERNAL VALIDATION), not regulatory inputs |
| Usage category | QUALITATIVE EVIDENCE |
| Verdict | **GO** |

#### S-30: Federal AV/UAS framework
| Field | Value |
|---|---|
| Provider | NHTSA, FAA, Federal Register, eCFR |
| Official URLs | • BVLOS NPRM "Normalizing Unmanned Aircraft Systems Beyond Visual Line of Sight Operations", 90 FR 38212, 2025-08-07, Docket FAA-2025-1908: https://www.federalregister.gov/documents/2025/08/07/2025-14992/normalizing-unmanned-aircraft-systems-beyond-visual-line-of-sight-operations (V). **No final rule found as of 2026-09-29** (V, Federal Register API search)<br>• 14 CFR Part 107 and §107.205 (eCFR, V)<br>• FAA Package Delivery by Drone (Part 135): https://www.faa.gov/uas/advanced_operations/package_delivery_drone (URL V; page returned 403)<br>• FAA State and Local Regulation of UAS: https://www.faa.gov/uas/state-and-local-regulation-unmanned-aircraft-systems (URL V)<br>• NHTSA Standing General Order 2021-01 crash reporting: https://www.nhtsa.gov/laws-regulations/standing-general-order-crash-reporting (URL V; page returned 403)<br>• FAA Section 2209 NPRM (fixed-site facility restrictions), 2026-05-06, Docket FAA-2026-4558 (URL V)<br>• NHTSA "AV Framework Updates and Request for Comments on Interim Guidance", FR Doc. 2026-15483, 2026-07-31 (URL V; contents U) |
| Native geography / grain | Federal (identical across all markets) |
| Limitations | No variation across markets, so it cannot differentiate them. It is context only |
| Usage category | QUALITATIVE EVIDENCE (national context) |
| Verdict | **GO** (context row, not a differentiating feature) |

#### S-31: NCSL Autonomous Vehicles Legislation Database
| Field | Value |
|---|---|
| Provider / URL | National Conference of State Legislatures. https://www.ncsl.org/transportation/autonomous-vehicles-legislation-database (V) |
| Vintage | Last updated 2026-09-15. Covers 2017–present, 50 states + DC, monthly updates (V) |
| Grain | Bill |
| Limitations | Non-governmental secondary index |
| Usage category | QUALITATIVE EVIDENCE, **discovery only, never cited as final evidence** |
| Verdict | **PROXY** |

#### S-32: NCSL Unmanned Aircraft State Law Landscape
| Field | Value |
|---|---|
| Provider / URL | NCSL. https://www.ncsl.org/transportation/current-unmanned-aircraft-state-law-landscape (V) |
| Vintage | Updated 2023-03-27; covers laws 2013–2021 (V). Stale |
| Usage category / verdict | QUALITATIVE EVIDENCE, discovery only. **PROXY** |

#### S-33: IIHS highly automated vehicle laws table
| Field | Value |
|---|---|
| Provider / URL | Insurance Institute for Highway Safety. https://www.iihs.org/research-areas/advanced-driver-assistance/highly-automated-vehicle-laws (V) |
| Vintage | "September 2026" (V) |
| Fields | State, type of operation authorized (testing/deployment), licensed-driver exceptions, liability coverage |
| Limitations | Non-governmental, with a disclaimer |
| Usage category / verdict | QUALITATIVE EVIDENCE, cross-check only. **PROXY** |

#### S-34: BTS "Automated Vehicle Legislation by State" (2019)
| Field | Value |
|---|---|
| Provider / URL | USDOT BTS. https://www.bts.gov/geography/geospatial-portal/automated-vehicle-legislation-state-2019 (URL V) |
| Limitations | Stale (2019) |
| Verdict | **DROP** |

### G. Deployment evidence: EXTERNAL VALIDATION only (see §8)

> These sources are **never** used for market selection, feature engineering or scoring.

#### S-35: CA DMV AV permit holders
| Field | Value |
|---|---|
| Provider / URL | California DMV. https://www.dmv.ca.gov/portal/vehicle-industry-services/autonomous-vehicles/autonomous-vehicle-testing-permit-holders/ (V) |
| Vintage | Testing-with-driver list "as of September 17, 2026". Driverless-testing table updated 2026-04-03. Deployment table updated 2025-11-21 (V) |
| Grain / fields | Permit holder × permit type; manufacturer, approved locations, time of day, ODD (V) |
| Limitations | California only. Approved areas sometimes appear only as maps. A permit is not the same as service |
| Usage category / verdict | EXTERNAL VALIDATION. **GO** |

#### S-36: CPUC AV programs and quarterly reporting
| Field | Value |
|---|---|
| Provider / URL | California PUC. Program page as S-29; quarterly reporting sub-page (V; latest Q2 2026) |
| Grain / fields | Operator × quarter; VMT, deadhead miles, occupancy, incidents (V) |
| Limitations | California only. Some fields are redacted under confidentiality claims |
| Usage category / verdict | EXTERNAL VALIDATION. **GO** |

#### S-37: FAA drone-delivery environmental reviews (NEPA)
| Field | Value |
|---|---|
| Provider / URL | FAA. https://www.faa.gov/uas/advanced_operations/nepa_and_drones (V; last updated 2026-09-24) |
| Grain / fields | Operator × metro/site × review stage (draft/final) × signing date. About 34 sign-off dates, Nov 2021–Sep 2026 (V, partial parse) |
| Limitations | A review is not active service. The page must be read manually to capture titles fully. **This records operator-specific activity, so it is deployment evidence, not regulatory framework evidence** |
| Usage category / verdict | EXTERNAL VALIDATION. **GO** |

#### S-38: Operator official service-area pages and newsrooms
| Operator | Official URL | What it states | Dated? | Sub-verdict |
|---|---|---|---|---|
| Waymo | https://waymo.com/ | Cities served plus "Coming soon" | Undated | **GO** (needs manual recount of each city's status) |
| Zoox | https://zoox.com/where-to-ride | City list; status wording not captured | Undated | **PROXY** |
| Tesla | https://www.tesla.com/support/robotaxi | Blocked (403). Shareholder-update PDF not fetched | — | **PROXY** (pending manual capture) |
| May Mobility | https://maymobility.com/locations/ | Locations, price/"Free", hours | Undated | **GO** |
| Motional | https://motional.com/news/motional-robotaxis-now-available-uber-las-vegas | Las Vegas, "supervised service phase" | 2026-03-13 | **GO** |
| Avride | https://www.avride.ai/ | No locations | — | **DROP** (use the dated partner release under S-39) |
| Starship | https://www.starship.xyz/press/starship-technologies-doubles-down-on-grocery/ | Winding down U.S. campus operations | 2026-06-04 | **GO** |
| Serve Robotics | https://investors.serverobotics.com/news-releases/ | Metro launches (from search snippets; page timed out) | Dated releases | **PROXY** |
| Coco | https://www.cocodelivery.com/ | No U.S. city list found | — | **PROXY** |
| Kiwibot | kiwibot.com (redirects to robot.com) | No named locations | — | **DROP** |
| Wing | https://wing.com/get-delivery ; https://wing.com/news/ | "Now serving" / "Coming soon" metros; dated news | Partly | **GO** |
| Amazon Prime Air | https://www.aboutamazon.com/news/transportation/amazon-prime-air-drone-delivery-expansion | Current sites plus "launching soon" | Aug 2026 (exact day U) | **GO** |
| Zipline | https://www.zipline.com/newsroom/ | Service areas and planned metros | Dated | **GO** (fact sheet page is misdated, so use newsroom items) |
| Flytrex | https://help.flytrex.com/ | Delivery radius only; towns unverified | 2023-10-31 | **PROXY** |
| DroneUp | https://www.droneup.com/ | Unverified locations | — | **PROXY** |
| Manna | https://www.manna.aero/blog/manna-announces-major-us-expansion | Tulsa, OK operation | 2026-07-08 | **GO** |

Common fields for S-38:
- **Provider:** the operator.
- **Access:** manual capture with an archive URL.
- **Grain:** operator × location × status.
- **License:** operator website terms (not redistributed; only facts and URLs recorded).
- **Limitations:** marketing claims, undated or overwritten pages, survivorship.
- **Usage category:** EXTERNAL VALIDATION.
- **Class verdict:** **GO**.

#### S-39: Partner/platform announcements
| Field | Value |
|---|---|
| Provider / URL | Platform newsrooms and investor releases, e.g., https://www.uber.com/us/en/newsroom/avride-on-uber/ (2025-12-03, V) and https://investors.uber.com/news-events/news/ |
| Limitations | Announcements often describe future plans, not operations. They must be coded `announced` unless the page states that service is live. This project is independent of any platform named |
| Usage category / verdict | EXTERNAL VALIDATION. **PROXY** |

---

## 3. Feature-feasibility matrix

> **Every row is a hypothesis.** No weights are assigned, and no direction-of-effect is fixed beyond the stated rationale. Phase 5 EDA decides inclusion and records any redundancy.
>
> **Abbreviations:**
> - Modes: **RT** robotaxi · **SW** sidewalk robot · **DR** drone · **All** all three
> - Components: **C1** Demand & Market Opportunity · **C2** Operating Environment · **C3** Economic Attractiveness · **C4** Regulatory & Autonomy Readiness · **C5** Infrastructure & Mode Fit
> - Evidence types: **Obs** observed · **Der** derived · **Qual** qualitative

| # | Mode | Component | Candidate feature | Business rationale | Source | Raw field(s) | Native geo | Target geo | Aggregation / crosswalk | Vintage | Type | Verdict | Known limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F01 | All | C1 | Resident population | Size of the addressable market | S-01 | `POPESTIMATE2025` | CBSA | CBSA | None | V2025 | Obs | **GO** | Correlates with most size-driven features (redundancy risk) |
| F02 | DR, SW | C1 | Households | Delivery demand is household-based | S-03 | `B11001_001E` | CBSA | CBSA | None | ACS 2020–24 | Obs | **GO** | Near-duplicate of population |
| F03 | RT, SW | C1 | Population-weighted density | Density of trips and orders where people actually live | S-04 + S-05 | `B01003_001E`; `ALAND_SQMI` | Tract | CBSA | Tract → county → CBSA; formula decided in Phase 6 (§6) | ACS 2020–24; Gaz 2024 | Der | **GO** | 38,579 tracts; tract MOEs; formula not yet chosen |
| F04 | All | C1 | Raw MSA density | Simple density benchmark | S-01 + S-05 | `POPESTIMATE2025`; `ALAND_SQMI` | CBSA | CBSA | None | V2025; Gaz 2024 | Der | **PROXY** | Distorted by large low-density outlying counties (§6); benchmark only |
| F05 | RT | C1 | Commuting workers (volume) | Scale of recurring trip demand | S-03 | `B08301_001E` | CBSA | CBSA | None | ACS 2020–24 | Obs | **GO** | Pandemic-era work-from-home inflation |
| F06 | RT | C1 | Taxi/ride-hailing commute share | Existing paid ride-hail behavior | S-03 | `B08301_016E` / `B08301_001E` | CBSA | CBSA | Ratio | ACS 2020–24 | Der | **GO** | Small counts, relatively large MOE; commute trips only |
| F07 | RT | C1 | Public-transit commute share | Car-light travel culture (could complement or substitute) | S-03 | `B08301_010E` / `_001E` | CBSA | CBSA | Ratio | ACS 2020–24 | Der | **PROXY** | Direction of effect is ambiguous; dominated by a few metros |
| F08 | RT | C1 | Mean commute time | Trip length and congestion signal | S-03 | `S0801_C01_046E` | CBSA | CBSA | None | ACS 2020–24 | Obs | **PROXY** | Ambiguous interpretation (demand vs. congestion) |
| F09 | RT | C1 | Airport enplanements per capita | Airport ride demand | S-17 + S-19 + S-07 + S-01 | `CY 25 Enplanements`; `LAT_DECIMAL`/`LONG_DECIMAL` | Airport | CBSA | Point-in-polygon; sum; ÷ population | CY2025 | Der | **GO** | Connecting-hub inflation; airports just outside a CBSA (§5) |
| F10 | SW, DR | C1 | Restaurant / food-service establishment density | On-demand food delivery opportunity | S-08 (+ S-01/S-05 denominators) | `est` for NAICS `722` / `7225` | CBSA | CBSA | ÷ population or ÷ land area (choice in Phase 6) | CBP 2023 | Der | **GO** | Establishments ≠ order volume; noise infusion |
| F11 | SW, DR | C1 | Retail and grocery establishment density | Retail and grocery delivery opportunity | S-08 | `est` for `44-45`, `445` | CBSA | CBSA | As F10 | CBP 2023 | Der | **GO** | As F10; correlated with F10 |
| F12 | SW | C1 | Short-distance delivery opportunity | Roadmap dimension: many origins and destinations close together | S-08 + S-04/S-05 | Derived from F03 and F10 | CBSA | CBSA | Combination of existing features (defined in Phase 6) | Mixed | Der | **PROXY** | No direct measure of trip distance; composite of other features |
| F13 | All | C2 | Days with precipitation ≥ 0.10 in | Wet-weather sensor and operating disruption | S-12 | `ANN-PRCP-AVGNDS-GE010HI` | Station | CBSA | Station rule (§5) | 1991–2020 | Obs | **GO** | Single-station representativeness |
| F14 | All | C2 | Annual precipitation | Overall wetness | S-12 | `ANN-PRCP-NORMAL` | Station | CBSA | Station rule | 1991–2020 | Obs | **GO** | Likely redundant with F13 |
| F15 | All | C2 | Annual snowfall | Snow disruption, especially for sidewalk robots | S-12 | `ANN-SNOW-NORMAL` | Station | CBSA | Station rule + missing-snow rule | 1991–2020 | Obs | **GO** | Missing at some stations (e.g., LAX, PHX); missing ≠ zero |
| F16 | SW, RT | C2 | Days with snow depth ≥ 1 in | Persistent snow cover blocks sidewalks and hides lane markings | S-12 | `ANN-SNWD-AVGNDS-GE001WI` | Station | CBSA | As F15 | 1991–2020 | Obs | **GO** | As F15 |
| F17 | All | C2 | Days with Tmin ≤ 32 °F | Freeze/ice exposure; battery performance | S-12 | `ANN-TMIN-AVGNDS-LSTH032` | Station | CBSA | Station rule | 1991–2020 | Obs | **GO** | Correlated with snow features |
| F18 | All | C2 | Days with Tmax ≥ 90 °F | Heat stress on batteries and sensors | S-12 | `ANN-TMAX-AVGNDS-GRTH090` | Station | CBSA | Station rule | 1991–2020 | Obs | **GO** | Airport stations may run warmer or cooler than the core |
| F19 | DR | C2 | Mean annual wind speed | Drone flight suitability | S-13 | `HLY-WIND-AVGSPD` | Station | CBSA | Hourly → annual mean; station rule | 1991–2020 | Der | **PROXY** | Mean wind is a coarse stand-in for gust limits; first-order stations only |
| F20 | DR | C2 | Gust / high-wind frequency | Drone operating-limit exceedance | S-14 | `HourlyWindGustSpeed` | Station | CBSA | Self-computed multi-year statistic | Not pinned | Der | **PROXY** | Only if F19 proves insufficient; our own methodology |
| F21 | All | C2 | Severe-weather event frequency | Extreme-event disruption | S-15 | `EVENT_TYPE` counts | County/zone | CBSA | County → CBSA | — | Der | **DROP** | Reporting bias correlated with population |
| F22 | RT | C2 | Road operating complexity | Harder driving environments slow AV deployment | S-21 | `D3B` (intersection density) | Block group | CBSA | Population-weighted mean by county → CBSA | SLD v3 (2017–2020 inputs) | Der | **PROXY** | Intersection density is an indirect, direction-ambiguous proxy. No national source for road geometry, construction or traffic complexity |
| F23 | All | C3 | Median household income | Willingness and ability to pay for premium services | S-03 | `B19013_001E` | CBSA | CBSA | None | ACS 2020–24 | Obs | **GO** | Not adjusted for cost of living (see F24) |
| F24 | All | C3 | Cost-of-living-adjusted income | Real purchasing power | S-03 + S-11 | `B19013_001E`; RPP | CBSA | CBSA | Income ÷ (RPP/100) | 2024 | Der | **PROXY** | BEA MSA RPP availability unconfirmed |
| F25 | RT | C3 | Taxi/chauffeur wage level | Cost of the human-driven alternative (labor-cost proxy) | S-09 | SOC 53-3053, 53-3054 wage columns | CBSA | CBSA | None | OEWS May 2025 | Obs | **GO** | Excludes the self-employed (gig drivers); possible suppression |
| F26 | SW, DR | C3 | Courier / delivery wage level | Cost of human delivery labor | S-09 | SOC 43-5021, 53-3033 (35-3023 optional) | CBSA | CBSA | None | OEWS May 2025 | Obs | **GO** | As F25 |
| F27 | All | C3 | Commercial activity (total establishments / annual payroll) | Size of the business customer base | S-08 | `est`, `ap` for all sectors | CBSA | CBSA | None / per capita | CBP 2023 | Obs/Der | **GO** | Size redundancy with F01 |
| F28 | RT | C4 | Statute expressly authorizes driverless operation | Legal permission to remove the safety driver | S-28 | Evidence record RT-a | State | CBSA | State → CBSA mapping (§5, §7.5) | Evidence date | Qual | **GO** | "Silent" ≠ "prohibited"; multi-state markets |
| F29 | RT | C4 | State AV testing permit/notice framework | Pathway to begin operating | S-28/S-29 | RT-b | State | CBSA | As F28 | Evidence date | Qual | **GO** | May exist in regulation only |
| F30 | RT | C4 | State driverless deployment/commercial authorization framework | Pathway to paid service | S-28/S-29 | RT-c | State | CBSA | As F28 | Evidence date | Qual | **GO** | A framework's existence is not the same as permits issued |
| F31 | RT | C4 | State preemption of local AV regulation | Reduces local-patchwork risk | S-28 | RT-d | State | CBSA | As F28 | Evidence date | Qual | **GO** | Implied preemption requires legal judgment |
| F32 | RT | C4 | TNC/for-hire rules applicable to AVs | Commercial passenger-service compliance | S-28/S-29 | RT-e | State (some municipal) | CBSA | As F28 | Evidence date | Qual | **PROXY** | Hard to locate comprehensively |
| F33 | RT | C4 | AV insurance minimum | Cost and complexity of entry | S-28 | RT-g | State | CBSA | As F28 | Evidence date | Qual | **PROXY** | Amounts vary by vehicle and service type |
| F34 | SW | C4 | State PDD statute exists | Legal status of sidewalk robots | S-28 | PDD-a | State | CBSA | As F28 | Evidence date | Qual | **GO** | Naming varies across states |
| F35 | SW | C4 | PDD weight and speed limits | Operating envelope | S-28 | PDD-b, PDD-c | State | CBSA | As F28 | Evidence date | Qual | **GO** | Limits are sometimes in separate definition sections |
| F36 | SW | C4 | Local authority to prohibit/regulate PDDs | Local-ban risk | S-28 | PDD-d | State (+ municipal) | CBSA | As F28 | Evidence date | Qual | **GO** (state text) / **PROXY** (ordinances) | Local ordinances cannot be enumerated completely |
| F37 | SW | C4 | PDD operator/monitoring, insurance, state authorization | Compliance burden | S-28/S-29 | PDD-e, PDD-f, PDD-g | State | CBSA | As F28 | Evidence date | Qual | **GO** | Phased requirements (e.g., PA) |
| F38 | DR | C4 | State critical-infrastructure overflight law | Flight-restriction risk | S-28 | DR-f | State | CBSA | As F28 | Evidence date | Qual | **GO** | Most include exemptions for FAA-authorized commercial operations |
| F39 | DR | C4 | State preemption of local drone rules | Local-patchwork risk | S-28 | DR-g | State (+ municipal) | CBSA | As F28 | Evidence date | Qual | **GO** (state) / **PROXY** (local) | Local take-off/landing rules are hard to enumerate |
| F40 | DR, RT | C4 | Federal framework (Part 107/135, BVLOS NPRM, NHTSA SGO / AV Framework) | Overall feasibility context | S-30 | DR-a–e, RT-f | Federal | — | None (identical for all markets) | Evidence date | Qual | **DROP** (as a differentiating feature) | Constant across markets; kept as documented context |
| F41 | SW, RT | C5 | Population-weighted National Walkability Index | Pedestrian-friendly built environment | S-22 | `NatWalkInd`, `TotPop` | Block group | CBSA | Population-weighted mean by county → CBSA | SLD v3 | Der | **GO** | Relative rank; 2017–2020 inputs; not a sidewalk inventory |
| F42 | SW | C5 | Street intersection density | Short, connected pedestrian routes | S-21 | `D3B` | Block group | CBSA | As F41 | SLD v3 | Der | **GO** | Is one input of F41 (redundancy) |
| F43 | RT | C5 | Transit accessibility | Mobility environment and multimodal complement | S-21 | `D4A` | Block group | CBSA | As F41 | SLD v3 (GTFS 2020) | Der | **PROXY** | Only GTFS-publishing agencies; 2020 service levels |
| F44 | RT | C5 | Zero-vehicle household share / vehicles per household | Car dependence vs. demand for car-free mobility | S-03 | `B08201_002E` / `_001E`; `B25046_001E` / `B11001_001E` | CBSA | CBSA | Ratio | ACS 2020–24 | Der | **GO** | Direction of effect ambiguous; dominated by NYC |
| F45 | RT | C5 | Airport connectivity (count / hub size of commercial airports in CBSA) | Airport-trip infrastructure | S-17 + S-19 | `Hub`, `S/L` | Airport | CBSA | Point-in-polygon; count by hub type | CY2025 | Der | **PROXY** | Redundant with F09 |
| F46 | DR | C5 | Single-family detached housing share | Yard/driveway drop-off feasibility | S-03 | `B25024_002E` / `B25024_001E` | CBSA | CBSA | Ratio | ACS 2020–24 | Der | **PROXY** | Does not capture lot size, tree cover or setbacks |
| F47 | DR | C5 | Owner-occupied housing share | Suburban household structure | S-03 | `B25003_002E` / `B25003_001E` | CBSA | CBSA | Ratio | ACS 2020–24 | Der | **PROXY** | Weak, indirect proxy; correlated with F46 |
| F48 | DR | C5 | Share of population in low-density tracts | Suburban service-area fit | S-04 + S-05 | `B01003_001E`; `ALAND_SQMI` | Tract | CBSA | Density threshold (to be defined) → share | ACS 2020–24; Gaz 2024 | Der | **PROXY** | The threshold is a scoring choice to be justified in Phase 6 |
| F49 | DR | C5 | Share of CBSA land within UAS Facility Map grid / at ceiling 0 | Airspace constraint near airports | S-23 + S-07 | `CEILING`, cell geometry | Grid cell | CBSA | Polygon intersection, equal-area | 2026-09-03 cycle | Der | **PROXY** | Controlled airspace is not prohibition; TFRs excluded |
| F50 | DR | C5 | Share of land in national-security UAS restrictions / prohibited areas | Hard airspace constraint | S-24 + S-07 | Unverified | Polygon | CBSA | Polygon intersection | Cycle at ingestion | Der | **PROXY** | Schema unverified; little metro-level variation expected |
| F51 | RT, SW | C5 | Urban-core density (principal urban area) | Density of the deployable core | S-06 + S-03 (UA geography) + S-05 | UA population; `ALAND_SQMI` | Urban area | CBSA | Principal UA → CBSA (judgment) | 2020 UA; ACS 2020–24 | Der | **PROXY** | UAs cross CBSAs; no population split published |
| F52 | RT, DR | C4/C5 | Existing autonomous / drone ecosystem (current deployments) | Listed in the roadmap as a dimension | S-35–S-39 | — | Operator × location | CBSA | — | — | Qual | **DROP** (as a feature) | **Excluded by the approved rule: deployment evidence is external validation only.** Using it would make the validation circular |
| F53 | SW | C5 | Sidewalk presence/quality inventory | Direct sidewalk suitability | — | — | — | — | — | — | — | **DROP** | No national, consistent public source identified; F41/F42 are the proxies |
| F54 | DR | C5 | Low-obstacle structure (tree canopy, building heights) | Drone approach/landing clearance | — | — | — | — | — | — | — | **DROP** (for now) | No source researched or verified in Phase 1. A candidate for later research if Phase 5 shows a gap |
| F55 | All | C3 | Delivery/trip demand volume (actual orders or rides) | Direct demand measure | — | — | — | — | — | — | — | **DROP** | Proprietary; not publicly observable |

---

## 4. Source-to-feature mapping

| Source | Verdict | Feeds features | Role |
|---|---|---|---|
| S-01 PEP V2025 | GO | F01, F04, F09 (denominator), F10/F11 (denominator) | Market universe, population |
| S-02 Delineation 2023 | GO | All non-native-CBSA features | County → CBSA crosswalk |
| S-03 ACS MSA | GO | F02, F05, F06, F07, F08, F23, F24, F44, F46, F47, F51 | Demographics, commuting, housing |
| S-04 ACS tract | GO | F03, F48 | Density inputs |
| S-05 Gazetteer 2024 | GO | F03, F04, F48, F51 | Land area |
| S-06 Urban areas | PROXY | F51 | Urban-core definition |
| S-07 TIGER 2024 | GO | F09, F45, F49, F50; station mapping | Spatial overlays |
| S-08 CBP 2023 | GO | F10, F11, F12, F27 | Commercial activity |
| S-09 OEWS May 2025 | GO | F25, F26 | Labor cost |
| S-10 QCEW 2025 | PROXY | Backup for F25/F26/F27 | — |
| S-11 BEA RPP | PROXY | F24 | Cost-of-living adjustment |
| S-12 Normals annual | GO | F13–F18 | Climate |
| S-13 Normals hourly | GO | F19 | Wind |
| S-14 LCD v2 | PROXY | F20 | Gusts (optional) |
| S-15 Storm Events | DROP | (F21, dropped) | — |
| S-16 GHCN-Daily | DROP | — (backfill only) | — |
| S-17 FAA enplanements | GO | F09, F45 | Airport demand |
| S-18 BTS T-100 | PROXY | Optional connectivity | — |
| S-19 FAA NASR APT | GO | F09, F45 | Airport coordinates |
| S-20 BTS Master Coordinate | DROP | — | — |
| S-21 EPA SLD v3 | GO | F22, F42, F43 | Built environment |
| S-22 EPA NWI | GO | F41 | Walkability |
| S-23 FAA UASFM | PROXY | F49 | Airspace constraint |
| S-24 FAA security restrictions | PROXY | F50 | Airspace constraint |
| S-25 FAA Class Airspace | PROXY | Cross-check for F49 | — |
| S-26 Part 107 waivers | DROP | — | — |
| S-27 FRIAs | DROP | — | — |
| S-28 State statutes | GO | F28–F39 | Regulatory evidence |
| S-29 State agency programs | GO | F29, F30, F32, F37 | Regulatory evidence |
| S-30 Federal framework | GO | F40 (context only) | National context |
| S-31/S-32/S-33 NCSL, IIHS | PROXY | Discovery/cross-check for F28–F39 | Never cited as final evidence |
| S-34 BTS 2019 map | DROP | — | — |
| S-35–S-39 Deployment evidence | GO/PROXY | **None**, by design | External validation only (§8) |

---

## 5. Geography-mapping table

The canonical target for every mapping is the **CBSA code (July 2023 delineation) = `market_id`**.

| Source geography → CBSA | Used by | Mapping method | Aggregation rule | Unresolved ambiguity | Distortion risk |
|---|---|---|---|---|---|
| **CBSA (native)** | S-01, S-03, S-08, S-09 | Direct join on 5-digit code | None | ACS 2024 and CBP 2023 use the July 2023 delineation, which is inferred rather than stated. **Phase 3 must check that all 35 codes are present and match S-01 names** | Low |
| **County → CBSA** | S-01 (county rows), S-10, S-21/S-22 (via county FIPS), S-06 | Join `state FIPS + county FIPS` to S-02 list1_2023 | Sum counts; population-weighted means for rates/indices | None for the 35 markets (no CT planning regions involved). Sources keyed to legacy CT counties or pre-2023 CBSA codes (e.g., the SLD's own `CBSA` field) must be re-mapped by county FIPS, never by their own CBSA field | Low |
| **Tract → CBSA** | S-04, S-05 | `GEOID[0:5]` (county FIPS) → S-02 | Population-weighted statistics (§6); exclude zero-land-area tracts and document them | ACS 2024 uses 2020 tracts; Gazetteer 2024 must use the same tract vintage (checked in Phase 3) | Low (exact nesting) |
| **Block group → CBSA** | S-21, S-22 | `STATEFP + COUNTYFP` → S-02 | Population-weighted mean using SLD `TotPop` (2018) | SLD block groups are 2010-census-based (2019 TIGER), not 2020. County codes unchanged for the 35 markets' counties is **to be verified in Phase 3** | Low–medium (2018 population weights) |
| **Airport → CBSA** | S-17, S-19 | NASR coordinates → point-in-polygon on TIGER 2024 CBSA shapes (preferred over NASR county *names*) | Sum enplanements of FAA commercial-service airports physically inside the CBSA | **Unresolved:** airports just outside a CBSA that serve it, e.g. BWI (Baltimore CBSA) for DC, ONT (Riverside CBSA) for LA, MHT/PVD (outside the Boston CBSA), SJC (San Jose CBSA, outside the universe) for the Bay Area. A separate "large/medium hub within X miles" sensitivity variable is proposed; X is undecided. Connecting-hub inflation (ATL, DFW, CLT, DEN, ORD) | **Medium–high** |
| **Weather station → CBSA** | S-12, S-13, (S-14) | **Undecided (Phase 3).** Options: (1) designated primary first-order airport station per CBSA; (2) mean of all normals stations inside the CBSA polygon; (3) population-weighted nearest qualifying station | Station value used as the metro value (option 1), or a mean/weighted mean (options 2–3) | Which station represents large or climatically varied CBSAs (e.g., Riverside–San Bernardino's desert and valley; Denver's plains and foothills). Missing-snow rule: fall back to the nearest in-CBSA station with a complete flag, or mark NA with a flag. Station IDs and completeness flags must be recorded per market per element | **Medium–high** |
| **Urban area → CBSA** | S-06 | Principal UA(s) → UA-county relationship file → S-02 | UA population (ACS UA geography) ÷ UA land area | No official UA→CBSA file. UAs cross CBSA lines (e.g., multi-CBSA urban areas). The relationship file has land area only, not population. Choosing the "principal" UA is a judgment call | **High** (hence PROXY) |
| **State regulation → CBSA** | S-28, S-29 | **Undecided (Phase 7).** Options: (1) principal-city state; (2) population-weighted state share; (3) carry all states and flag divergence; (4) principal-city state + divergence flag | Qualitative values are not averaged. For option 2, shares come from S-01 county rows | **11 of the 35 markets span more than one state** (state population shares from S-01 county rows):<br>• New York 35620: NY 64.6% / NJ 35.4%<br>• Chicago 16980: IL 92.3% / IN 7.7%<br>• Washington 47900: VA 49.3% / MD 39.0% / DC 10.7% / WV 1.0%<br>• Philadelphia 37980: PA 67.0% / NJ 22.1% / DE 9.3% / MD 1.7%<br>• Boston 14460: MA 90.9% / NH 9.1%<br>• Minneapolis 33460: MN 96.3% / WI 3.7%<br>• Charlotte 16740: NC 84.5% / SC 15.5%<br>• St. Louis 41180: MO 76.1% / IL 23.9%<br>• Portland 38900: OR 78.6% / WA 21.4%<br>• Cincinnati 17140: OH 76.0% / KY 20.5% / IN 3.5%<br>• Kansas City 28140: MO 58.7% / KS 41.3%<br><br>Municipal ordinances vary within a state | **High** where states diverge (Washington, Kansas City, Philadelphia and New York are the most balanced) |
| **Airspace geography → CBSA** | S-23, S-24, S-25 | Polygon intersection with TIGER 2024 CBSA shapes in an equal-area projection | Share of CBSA land area covered (optionally by ceiling class) | CBSA polygons include large rural areas, which dilutes the share of land near airports. It is unclear whether to intersect with the CBSA or with its urban core. TFRs are not represented | Medium |
| **Operator location text → CBSA** (external validation only) | S-35–S-39 | Manual: stated place → Census place/county FIPS → S-02; record `mapping_method` and `mapping_confidence` | None (evidence list, not a feature) | "Bay Area"-style regions span several CBSAs. Small service areas cover a tiny share of a CBSA. Map-only permit areas. Suburbs listed on their own | Medium (validation only) |

---

## 6. Population-density options

**The problem:** CBSAs are built from whole counties. Metros whose counties contain large rural or desert areas show artificially low land-area density, even when their urban cores are dense. Examples are Riverside–San Bernardino (2 counties) and Phoenix (2 counties, including very large Maricopa and Pinal). Robotaxi and sidewalk-robot service areas depend on the density where people actually live and travel, not on density over the county footprint. **No final formula is chosen in Phase 1.**

| Option | Definition | Source feasibility | Computational implications | Strengths | Limitations |
|---|---|---|---|---|---|
| **Raw MSA density** | CBSA population ÷ CBSA land area | GO (S-01 + S-05) | Trivial: 35 divisions | Transparent, reproducible | Strongly distorted by county size; mis-ranks sprawling-county metros. Benchmark only (F04 = PROXY) |
| **Population-weighted density (tract)** | Σ(pop_t × density_t) ÷ Σ pop_t over tracts, where density_t = pop_t ÷ land_t. This is the density experienced by the average resident | GO (S-04 tract population + S-05 tract land area + S-02). Same method as Census special report C2010SR-01 (V). **No current official 2020-based metro product exists** (V, not exhaustive), so we compute it ourselves | 38,579 tracts; 31 state-level API calls; simple joins, no GIS needed. Exclude 65 zero-land tracts and document them | Robust to empty peripheral land; standard in the literature | Sensitive to tract size; tract MOEs; uses ACS rather than PEP population (vintage mismatch with F01) |
| **Population-weighted density (block group)** | Same formula over block groups | ACS 5-year supports block groups (S-03 geography list, V), or the SLD `D1B` (S-21) | More rows (roughly 3× tracts); higher MOEs; the SLD route uses 2018 population on 2010-based block groups | Finer resolution | Larger sampling error; the SLD vintage mismatch; marginal benefit over tracts for a 35-metro comparison |
| **Urban-core density** | Principal 2020 urban area population ÷ its land area | PROXY (S-06 + ACS UA geography + S-05 UA land area) | Small: 35 UAs, plus a judgment table for principal UA selection | Directly measures the deployable core | UAs cross CBSAs; no official UA→CBSA split; the principal-UA choice is subjective |
| **Tract-level aggregation (alternative summaries)** | e.g., share of population living in tracts above a density threshold; median tract density | GO (same inputs as tract PWD) | Same as tract PWD | Produces the "low-density share" for drones (F48) and a high-density share for sidewalk robots | Thresholds are scoring choices that need justification (Phase 6) |

**Phase 1 position:**
- Tract-level population-weighted density is the most feasible defensible option.
- Raw MSA density is kept only as a benchmark.
- Urban-core density is a sensitivity option.
- The final choice is made in Phase 6, after the Phase 5 EDA compares the options.

---

## 7. Regulatory evidence framework

**Principles:**
- There is **no numeric regulatory score in Phase 1.**
- Every regulatory value is a sourced, dated, qualitative classification.
- NCSL (S-31, S-32) and IIHS (S-33) are used **for discovery and cross-checking only**. Final evidence traces to statutes, legislature sites, DMV/DOT/PUC pages, FAA or other official government sources.
- **Regulatory framework evidence is kept separate from deployment evidence.** Whether a permit *program* exists is regulatory evidence. *Who holds* permits and *where* they operate is deployment evidence (EXTERNAL VALIDATION, §8).

### 7.1 Robotaxi concepts

| ID | Exact concept | Authoritative source | Geography | Effective-date capture | Value type | Interpretation limitation | Feasibility |
|---|---|---|---|---|---|---|---|
| RT-a | A state statute expressly permits an ADS-equipped vehicle to operate without a human driver in the vehicle | State statute (official code site) | State | Enactment/amendment history note on the code page | Binary (Y / N / Unclear) + conditions (qualitative) | "Silent" ≠ "prohibited"; statutory wording varies | **GO** |
| RT-b | A state permit, registration or notice program exists for AV **testing** | Statute, regulation, DMV/DOT program page | State | Program or rule effective date | Categorical (none / notice / permit) | May exist only in regulation or executive order | **GO** |
| RT-c | A state authorization program exists for **driverless deployment / commercial passenger service** (single- or dual-agency) | Statute; DMV and/or PUC program page (e.g., CA DMV + CPUC; TxDMV under SB 2807) | State | Program or rule effective date (e.g., TX SB 2807 effective 2025-09-01; TX rules effective 2026-02-27, V) | Categorical (none / single-agency / dual-agency) | A program's existence does not mean permits were issued | **GO** |
| RT-d | The state expressly preempts local regulation, taxes or fees on AVs | State statute (e.g., FL §316.85, V) | State | Enactment date | Binary + carve-outs (qualitative, e.g., airport fees) | Implied preemption requires legal judgment | **GO** |
| RT-e | TNC/for-hire passenger-carrier rules expressly apply to, or exempt, AVs | Statute; PUC rules | State (some municipal/airport) | Enactment/rule date | Categorical | Often buried in TNC chapters; hard to locate comprehensively | **PROXY** |
| RT-f | Federal layer: NHTSA SGO crash reporting; AV Framework; FMVSS exemptions | NHTSA / Federal Register (S-30) | Federal | Order/notice dates (Third Amended SGO issued 2025-04-24, effective 2025-06-16; URL V) | Qualitative | Identical across markets, so context only | **GO (context; not a differentiator)** |
| RT-g | A minimum insurance/liability amount is specified for AV operation | State statute | State | Enactment date | Categorical (dollar band) | Amounts vary by vehicle and service type | **PROXY** |

### 7.2 Sidewalk delivery robot (PDD) concepts

| ID | Exact concept | Authoritative source | Geography | Effective-date capture | Value type | Interpretation limitation | Feasibility |
|---|---|---|---|---|---|---|---|
| PDD-a | A state statute defines and authorizes personal delivery devices (or "mobile carriers") | State statute (e.g., VA §46.2-908.1:1; FL §316.2071; PA 75 Pa.C.S. §§8511–8522; V) | State | Enactment history (e.g., VA 2017; PA Act 106 of 2020) | Binary | Terminology varies | **GO** |
| PDD-b | Maximum device weight (with or without cargo) | State statute (often a definitions section) | State | Enactment date | Categorical (lb band / not stated) | Limit may sit in a separate definitions section (e.g., FL; U) | **GO** |
| PDD-c | Maximum speed on sidewalks/crosswalks and on roadways | State statute (e.g., VA 10 mph sidewalk; PA 12 mph pedestrian areas / 25 mph roads; V) | State | Enactment date | Categorical (mph) | Separate caps for different surfaces | **GO** |
| PDD-d | The state grants, limits or preempts local authority to prohibit or regulate PDDs | State statute (+ municipal code) | State + municipal | Enactment date | Categorical (preempted / limited / broad / silent) | Enumerating ordinances is infeasible, so only state text is coded | **GO (state) / PROXY (local)** |
| PDD-e | Operator or remote-monitoring requirement | State statute | State | Enactment date | Categorical (line-of-sight / remote / either) | Phased regimes (PA Phase 1/2) | **GO** |
| PDD-f | Minimum insurance | State statute (e.g., VA and FL $100,000; V) | State | Enactment date | Categorical ($) | — | **GO** |
| PDD-g | State authorization or registration of the operating entity | Statute; DOT page (e.g., PennDOT authorization, V) | State | Program date | Binary | Few states have this | **GO** |

### 7.3 Drone delivery concepts

| ID | Exact concept | Authoritative source | Geography | Effective-date capture | Value type | Interpretation limitation | Feasibility |
|---|---|---|---|---|---|---|---|
| DR-a | FAA exclusive authority over airspace and aviation safety | FAA fact sheet / policy (S-30) | Federal | Document date (2023) | Qualitative | Policy statement, not binding law; courts define the edges | **GO (context)** |
| DR-b | Part 107 small UAS operating rules | 14 CFR Part 107 (eCFR) | Federal | eCFR amendment dates | Qualitative | Identical across markets | **GO (context)** |
| DR-c | Part 135 air-carrier certification for drone package delivery | 14 CFR Part 135; FAA program page | Federal (operator-level) | Certification dates (operator-specific) | Qualitative | National operator certification, not market-specific. **Operator lists are deployment evidence** | **PROXY (context)** |
| DR-d | Status of the BVLOS rule (proposed Part 108) | Federal Register (NPRM 2025-08-07, 90 FR 38212, V) | Federal | NPRM / final / effective dates | Categorical (NPRM / final / effective): **NPRM as of 2026-09-29** (V) | Identical across markets | **GO (status tracking)** |
| DR-e | Federal critical-infrastructure UAS restrictions (Section 2209) | Federal Register (NPRM 2026-05-06, URL V) | Federal (site-specific) | NPRM / final dates | Categorical | Proposed only | **GO (status)** |
| DR-f | A state statute restricts drone operation over critical infrastructure | State statute (e.g., FL §330.41, V) | State | Enactment/amendment dates (FL amended 2025) | Binary + exemptions (qualitative) | Most exempt FAA-authorized commercial operations | **GO** |
| DR-g | The state preempts local drone regulation, or local take-off/landing control exists | State statute (+ municipal code) | State + municipal | Enactment date | Categorical | Local rules are hard to enumerate | **GO (state) / PROXY (local)** |

### 7.4 Evidence record schema (curated CSV, loaded to RAW in the dedicated evidence-curation step before Phase 7; see `project_scope.md` §14)

Grain: **one row per jurisdiction × mode × concept × evidence item.**

| Field | Description |
|---|---|
| `record_id` | e.g., `FL-RT-d-001` |
| `jurisdiction_type` | federal / state / county / municipal / airport_authority |
| `jurisdiction_code` | USPS code + state FIPS; Census place GEOID for municipalities |
| `jurisdiction_name` | Text |
| `mode` | robotaxi / sidewalk_robot / drone |
| `concept_id` | e.g., `RT-a`, `PDD-c`, `DR-f` |
| `value` | e.g., `Y`, `N`, `Unclear`, `10 mph`, `550 lb` |
| `value_type` | binary / categorical / qualitative |
| `value_detail` | Conditions, carve-outs |
| `legal_citation` | e.g., `Fla. Stat. §316.85(3)` |
| `enacting_instrument` | Session law / bill / chapter |
| `source_url` | Primary official URL |
| `source_type` | statute / regulation / agency_program_page / federal_rule / federal_order / federal_policy |
| `source_authority` | primary_official / primary_unofficial_host (e.g., when no official deep link exists) |
| `discovered_via` | NCSL / IIHS / direct |
| `effective_date` | ISO date (blank + note if unknown) |
| `evidence_date` | Date the source states it was updated or amended |
| `accessed_date` | ISO date |
| `archive_url` | Web archive capture |
| `verification_status` | VERIFIED / UNVERIFIED |
| `reviewer_confidence` | high / medium / low (qualitative; **not** a score) |
| `notes` | Interpretation reasoning |

### 7.5 Open framework decisions (not decided in Phase 1)

1. The state → CBSA mapping rule for multi-state markets (§5).
2. Whether and how to translate categorical evidence into any ordinal component in Phase 7. If an ordinal taxonomy is created, each level needs an explicit definition, dated evidence and source links, and it must be sensitivity-tested.
3. How often evidence is re-verified. Examples of recent changes: TX SB 2807 (2025), CA SB 480 (effective 2026-01-01), BVLOS final rule pending.
4. Manual capture procedure for sources that block automated fetching (Texas statutes, Georgia code, NHTSA, FAA pages).

---

## 8. Deployment evidence framework

**Usage category: EXTERNAL VALIDATION only.** Deployment evidence is **never** used for market selection, feature engineering or readiness scoring (including feature F52). In Phase 9/11 it answers one question: *do markets with current deployments show characteristics the framework independently rates as favorable?* Mismatches get documented as carefully as matches.

### 8.1 Acceptable sources
- Operator/company official pages, newsrooms and press releases (S-38).
- Official government sources: permit holder lists, PUC reporting, FAA environmental reviews (S-35, S-36, S-37).
- Platform/partner announcements, coded `announced` unless the page states live service (S-39).
- News articles, Wikipedia and blogs are **not** evidence. They may only point to an official source.

### 8.2 Status categories

| Category | Definition |
|---|---|
| `announced` | Planned / "coming soon" / partnership with no public rides or deliveries yet |
| `testing_with_safety_driver` | No public riders; human safety driver aboard |
| `driverless_testing` | No human aboard; no public or paying riders |
| `public_service_limited` | Open to the public with restrictions (free, waitlist, pilot, small area, or human aboard) |
| `public_service_commercial` | Open to the public, paid, in a defined area |
| `ended` | Paused, wound down or listed as a previous deployment |

When wording is ambiguous, code to the more conservative category and explain in `notes`.

### 8.3 Evidence record schema (curated CSV)

Grain: **one row per operator × location × status statement × source.**

`evidence_id, operator, mode, location_as_stated, location_type (city/metro/neighborhood/county/campus/site/map_only), state, place_fips, county_fips, cbsa_code, mapping_method, mapping_confidence, status_category, status_as_stated, safety_operator_onboard (Y/N/unknown), fare_charged (Y/N/unknown), source_url, source_type (operator_site/operator_press/partner_press/investor_filing/gov_permit/gov_data), source_date, source_date_basis (page_stated/dateline/undated), accessed_date, archive_url, verification (VERIFIED/UNVERIFIED), usage_category (= EXTERNAL_VALIDATION), notes`

### 8.4 Location → CBSA mapping
Stated place → Census place / county FIPS → S-02. `mapping_method` is one of place_to_county / county_direct / principal_city / campus_to_county, with a `mapping_confidence`. Automated fuzzy matching on city names is not allowed without manual review. Known ambiguities are listed in §5.

### 8.5 Phase 1 feasibility sample
The research pass confirmed at summary level that the official sources in S-35–S-39 carry mappable location statements. Examples:
- A CA DMV deployment-permit table updated 2025-11-21.
- Dated operator releases for Las Vegas (2026-03-13) and Houston-area drone delivery (2026-01-15).
- A dated sidewalk-robot campus wind-down (2026-06-04).

**No deployment records are curated or stored in Phase 1.** Collection, manual verification of exact wording, and archive capture happen in the dedicated evidence-curation step before Phase 7 (`project_scope.md` §14; this replaces the original Phase 3 timing). The evidence is used only in the validation phases.

### 8.6 Limitations
- Marketing language: "serving" can mean a tiny area, a waitlist or limited hours.
- Undated or misdated pages.
- Pages overwritten without archive.
- Survivorship: ended programs disappear.
- Announcements are not operations.
- Permits are not service.
- Company strategy is unobserved; absence is not evidence of unsuitability.
- Most states publish no permit-holder lists.

---

## 9. Vintage alignment

| Source | Pinned vintage / period | Reference point |
|---|---|---|
| S-01 PEP | Vintage 2025 | July 1, 2025 |
| S-02 Delineation | July 2023 | — |
| S-03/S-04 ACS | 2020–2024 5-year | Pooled 2020–2024 |
| S-05 Gazetteer | 2024 | Jan 1, 2024 geography |
| S-07 TIGER | 2024 | Jan 1, 2024 geography |
| S-08 CBP | 2023 | Mid-March 2023 employment week; calendar-2023 payroll |
| S-09 OEWS | May 2025 | Panels Nov 2022–May 2025 |
| S-11 BEA RPP (optional) | 2024 | Calendar 2024 |
| S-12/S-13 Normals | 1991–2020 | 30-year climatology |
| S-17 FAA enplanements | CY2025 | Calendar 2025 |
| S-19 NASR | Edition 2026-09-03 | — |
| S-21/S-22 EPA SLD/NWI | v3.0 (June 2021) | Inputs 2017–2020 (ACS 2014–2018, LODES 2017, streets 2018, GTFS 2020) |
| S-23 UASFM | Cycle 2026-09-03 | — |
| S-28/S-29/S-30 Regulatory | Point-in-time | Evidence and access dates per record |

**Mismatches that could affect comparability:**
1. **EPA SLD/NWI (2017–2020 inputs, 2010-based block groups)** vs. the 2025 population and 2023 delineation. Built-environment change since 2018 is not captured. This matters most in fast-growing Sunbelt metros.
2. **ACS 2020–2024 includes pandemic years.** Work-from-home and commute measures reflect a transitional period. They are not comparable with pre-2020 behavior.
3. **CBP 2023 vs. PEP 2025.** Establishment densities per 2025 resident mix years. CBP 2024 is not coming soon (suspended).
4. **Population denominators:** PEP 2025 (market size) vs. ACS 2020–2024 (tract density) vs. SLD 2018 (block-group weights). Each derived metric must name its denominator.
5. **Climate normals (1991–2020)** are a deliberate long-run baseline and are not synchronous with other sources. Recent warming trends are not reflected.
6. **Regulatory evidence** is dated to 2026. The underlying economic and demographic data describe 2020–2025.
7. **Delineation inference.** ACS 2024 and CBP 2023 are inferred, but not yet confirmed, to use the July 2023 delineation. BEA RPP delineation is unknown.

---

## 10. Candidate features without a defensible source

| Candidate (from roadmap or hypotheses) | Status | Reason |
|---|---|---|
| Existing autonomous / drone ecosystem as a scoring input (F52) | **Excluded by rule** | Deployment evidence is validation only; using it would make validation circular |
| Sidewalk presence/quality (F53) | **No source** | No consistent national public sidewalk inventory identified |
| Low-obstacle structure for drones: tree canopy, building heights (F54) | **Not researched / no verified source** | Would require a new source family, evaluated only if Phase 5 shows a gap |
| Actual ride/delivery demand volumes (F55) | **No public source** | Proprietary |
| Road geometry, construction, traffic complexity | **Proxy only** (F22) | Only indirect built-environment proxies are available |
| Wind gust operating-limit exceedance | **Proxy only** (F19/F20) | Normals give mean wind; gust statistics would be self-computed |
| Local ordinances (PDD bans, drone take-off/landing, curb rules) | **Proxy only** | Cannot be enumerated comprehensively; state text is coded instead |
| Controlled-airspace constraint as a true operating restriction | **Proxy only** (F49) | Controlled airspace ≠ prohibition; authorizations, waivers and TFRs are not captured |
| Fleet economics, partnerships, safety performance | **No public source** | Proprietary; acknowledged as a limitation |

---

## 11. Phase 3 retrieval findings (2026-10-04/05)

Facts established by actually retrieving the sources. They correct or complete the Phase 1 research above. No analytical decision is changed. Full pipeline detail is in [ingestion_pipeline.md](ingestion_pipeline.md).

| Source | Finding | Effect |
|---|---|---|
| S-01 PEP | Re-downloaded file has the same SHA-256 as Phase 1 (`BF6FAD83…1852`). The frozen top 35 (code, name, population, rank) matches §6 of the scope document exactly | Market universe confirmed unchanged |
| S-02 Delineation | 1,915 county rows. The sheet also has 2 title rows above the header, plus 1 blank row and 2 source-note rows below the data. The 3 trailing non-data rows are recorded as rejected with reasons | None |
| S-03 ACS (CBSA) | Every table returns 935 CBSAs (387 metro + 538 micro), and all 35 frozen market codes are present. This is consistent with the July 2023 delineation | A-005 evidence (see register) |
| S-04 ACS (tract) | 85,382 tracts across 52 state-level geographies (50 states + DC + Puerto Rico), all landed without filtering | Includes Puerto Rico tracts (not in any market) |
| S-03 / S-04 Census API | **Row order is not guaranteed.** An identical S-04 response came back reordered on 2026-10-05: same records, same values, different order. API snapshots are now sorted by GEO_ID before hashing | Checksums are content-based; see `ingestion_pipeline.md` §6.1 |
| S-05 Gazetteer | The last field of every line is padded with trailing spaces. Leading/trailing whitespace is trimmed from names and values (recorded as WARN). Positive longitudes are written with a leading `+` (e.g. Aleutians West `+179.621188`) | Technical normalization only |
| S-08 CBP | 576,818 rows (CBSA × NAICS); all 35 frozen markets present | None |
| S-09 OEWS | **Accessible** (see the S-09 correction above). The zip holds `MSA_M2025_dl.xlsx` (landed: 150,023 rows, 393 metropolitan areas including Puerto Rico), `BOS_M2025_dl.xlsx` (nonmetropolitan areas, not landed) and `file_descriptions.xlsx`. Wage cells use BLS markers `*` (not available, 11,005 cells across the two median columns) and `#` (top-coded, 416). **There is no 53-3054 Taxi Drivers row for New York (35620)**. A metadata sheet `UpdateTime` reads `09MAR2021`, which appears to be a stale BLS template value. **Phase 4:** 53-3054 Taxi Drivers is published for only 11 of 393 metros (7 of the 35 markets). 53-3053 Shuttle Drivers and Chauffeurs and 43-5021 Couriers cover all 35 markets | Labor-cost feature F25 must handle missing occupations per market (Phase 5; A-026) |
| S-12 Normals annual | 15,616 station files with **2,140 distinct column names**; each station publishes a different element set. Landed as one row per station with the full record in a VARIANT column | Element extraction happens in dbt |
| S-13 Normals hourly | 467 stations × 8,760 hours = 4,090,920 rows. Wind elements are `HLY-WIND-*` plus a `DATE` column (`MM-DDTHH:00:00`). **Phase 4 correction:** the archive's flag columns use the same `meas_flag_*` / `comp_flag_*` / `years_*` prefixes as the annual product. The `*_ATTRIBUTES` naming stated earlier came from NCEI's documentation *sample* file, not the archive. `-9999` marks 6,746 missing station-hours. 427 of the 467 hourly stations also have annual normals; 40 are hourly-only. Projected to 38 of 113 source columns (identifiers + wind) | Documented column projection |
| S-17 FAA enplanements | 516 airport rows. The sheet also contains **6 summary rows**: hub-group subtotals Large 30, Medium 35, Small 79 and Nonhub 258 (= 402 primary airports), plus 114 nonprimary and the 402 total. They are rejected with reasons, and the subtotals reconcile exactly to the 516 airports loaded | None |
| S-19 NASR | **`SITE_NO` is not unique**: `23747.31` is shared by airport 9XS4 and heliport 16XA (Denison, TX). `ARPT_ID` is unique across all 19,411 rows and is the natural key; the repeat is kept and flagged | Key choice corrected |
| S-21 EPA SLD | The REST service returned transient HTTP 502 errors mid-paging in the first full run. Pages now retry with longer backoff | Operational only |
| S-21 EPA SLD (Phase 4) | `D4A = -99999` (EPA's no-transit-data code) on 125,941 of 220,134 block groups. 2,581 Connecticut block groups carry legacy county codes with no 2023 county, so they map to no CBSA (no project market is in CT). In the 35 markets, 1,919 block groups have an SLD CBSA that differs from the 2023 delineation | Mapping via 2023 county FIPS confirmed (A-006) |
| S-04 / S-05 tracts (Phase 4) | 14 Suffolk County, NY (36103) tracts are in Gazetteer 2024 but not in ACS 2020–2024 (A-029). Every other tract matches 1:1 (85,382 joined) | Density inputs for the New York market are incomplete |
