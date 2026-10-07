# Power BI Build Guide (manual, Power BI Desktop)

Build the dashboard by hand from the validated Snowflake publication layer. Do the steps in order and tick each one off. The design is specified in [docs/powerbi_dashboard_spec.md](../docs/powerbi_dashboard_spec.md), the model in [docs/powerbi_semantic_model.md](../docs/powerbi_semantic_model.md), the DAX in [measures.md](measures.md), and the theme in [theme.json](theme.json).

## 0. Before you start

- [ ] **Warehouse is current.** The refresh workflow has passed ([docs/powerbi_refresh_workflow.md](../docs/powerbi_refresh_workflow.md)): `dbt build` all PASS, and `python scripts/run_phase9_publication_qa.py` reports 0 failures.
- [ ] **Software.** Power BI Desktop, current release.
- [ ] **Account.** A Snowflake login allowed to use role **AM_ANALYST**, which reads CORE and ANALYTICS only. Never put credentials in the repository or in a file next to the PBIX.

## 1. Connect to Snowflake (Import)

1. **Get data → Snowflake.**
   - **Server:** your account host, `<account_identifier>.snowflakecomputing.com` (the value of `SNOWFLAKE_ACCOUNT`; do not paste it into any committed file).
   - **Warehouse:** `AM_EXPANSION_WH`.
   - **Advanced options → Role:** `AM_ANALYST`.
   - **Data connectivity mode:** **Import**. Import is the recommended mode ([semantic model §4](../docs/powerbi_semantic_model.md)).
2. **Authenticate** with the method your Snowflake account permits for that user.
3. **Navigator:** open `AUTONOMOUS_MOBILITY → ANALYTICS` and select exactly these 13 tables:
   - dimensions: `PBI_DIM_MARKET`, `PBI_DIM_MODE`, `PBI_DIM_COMPONENT`, `PBI_DIM_FEATURE`, `PBI_DIM_SCENARIO`, `PBI_DIM_REGULATORY_SCENARIO`;
   - facts: `PBI_FCT_MARKET_BASELINE`, `PBI_FCT_MARKET_COMPONENT`, `PBI_FCT_MARKET_FEATURE_CONTRIBUTION`, `PBI_FCT_MARKET_ROBUSTNESS`, `PBI_FCT_BUSINESS_SCENARIO`, `PBI_FCT_REGULATORY_UNCERTAINTY`, `PBI_FCT_DEPLOYMENT_VALIDATION`.

   Do **not** import any other ANALYTICS table.
4. **Load.** The import is about 3,000 rows.

## 2. Rename tables and columns

1. **Rename tables** to the Power BI names:

| Snowflake table | Power BI name |
|---|---|
| `PBI_DIM_MARKET` | Market |
| `PBI_DIM_MODE` | Mode |
| `PBI_DIM_COMPONENT` | Component |
| `PBI_DIM_FEATURE` | Feature |
| `PBI_DIM_SCENARIO` | Scenario |
| `PBI_DIM_REGULATORY_SCENARIO` | Regulatory Scenario |
| `PBI_FCT_MARKET_BASELINE` | Baseline |
| `PBI_FCT_MARKET_COMPONENT` | Component Scores |
| `PBI_FCT_MARKET_FEATURE_CONTRIBUTION` | Feature Contribution |
| `PBI_FCT_MARKET_ROBUSTNESS` | Robustness |
| `PBI_FCT_BUSINESS_SCENARIO` | Business Scenario |
| `PBI_FCT_REGULATORY_UNCERTAINTY` | Regulatory Uncertainty |
| `PBI_FCT_DEPLOYMENT_VALIDATION` | Deployment Validation |

2. **Lower-case the column names** in Power Query: *Transform → Format → lowercase* on the header, or rename. Snowflake returns them upper-case, and the DAX in `measures.md` uses lower-case names.
3. **Check data types:**
   - `market_id` = Text;
   - scores, ranks and frequencies = Decimal number;
   - flags = True/False;
   - `latitude` / `longitude` = Decimal number, with Data category Latitude / Longitude.

## 3. Relationships

1. **Remove auto-detected relationships.** *Model view → Manage relationships → delete everything Power BI auto-detected.*
2. **Create the 19 relationships** in [semantic model §3](../docs/powerbi_semantic_model.md#3-relationships-all-single-direction-dimension--fact). All are **one-to-many, single direction, dimension → fact, active**.
3. **Two deliberate omissions** (they would create ambiguous paths):
   - Business Scenario and Feature Contribution get **no** direct relationship to Mode;
   - Feature Contribution gets **no** direct relationship to Component.
4. **Confirm** that no relationship is bidirectional and that there are no fact-to-fact relationships.

## 4. Hide, format, sort

1. **Hide columns.** Open `data_dictionary.csv` and hide every column marked `HIDE` (39), including every fact-side key.
2. **Formats** (the dictionary's `format` column):
   - scores `0.0`;
   - ranks `0`;
   - frequencies and shares as **Percentage**, 1 decimal place;
   - population `#,0`.
3. **Default summarization** = *Don't summarize* on every numeric fact column.
4. **Sort by column:**
   - Mode[mode_name] by Mode[sort_order];
   - Component[component_name] by Component[sort_order];
   - Scenario[scenario_name] by Scenario[sort_order];
   - Regulatory Scenario[regulatory_scenario_name] by its `sort_order`.

## 5. Measures and What-If parameters

1. **Measures table.** *Home → Enter data* → name it **Measures**, with one column; load it, then hide the column.
2. **What-If parameters.** *Modeling → New parameter → Numeric range*, five times: **W C1 … W C5**, each with minimum 0, maximum 100, increment 5 and default 20. Tick *Add slicer to this page* only on the Scenario Simulator page.
3. **Create every measure** in [measures.md](measures.md) §1–§6, in order. The guards in §1 must exist first.
4. **Set measure formats:**
   - percent: Top 5 / Top 10 Frequency, Regulatory Coverage %, Share Of Markets Scored, Normalized Weights;
   - `0.0`: the score measures;
   - `0`: the rank measures.

## 6. Theme

*View → Themes → Browse for themes →* `powerbi/theme.json`. It sets:
- page background `#F7F9FC`, with white cards and `#E5E7EB` borders;
- text `#1F2937`;
- blue `#2F6B9A`, teal `#16A085` and amber `#D97706`;
- no shadows.

**Fixed component colours.** Set these in each visual's data colours so that a component always has the same colour:

| C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|
| `#2F6B9A` | `#16A085` | `#D97706` | `#6B7280` | `#7FA8C9` |

**Avoid:** 3D visuals, rainbow palettes, gauges and heavy shadows.

## 7. Pages (in this order)

Build each page as specified in the dashboard spec. The summary:

| # | Page | Slicers | Key visuals |
|---|---|---|---|
| 1 | Executive Overview | Mode (single) | 4 KPI cards; bubble map (lat/long; size `Top 5 Frequency`; colour `Selected Baseline Rank`); top-10 table; two insight text boxes |
| 2 | Robotaxi | Market (single); page filter Mode = ROBOTAXI | Ranking table; rank 90% interval bars; regulatory dumbbell (Boston 4–20); C1–C4 component bars; feature contribution waterfall; regulatory text card |
| 3 | Autonomous Delivery | Mode (SIDEWALK or DRONE, single); Market | Ranking table; top-5 frequency bar; C2 and C5 feature visuals; regulatory range; deployment strip (titled as external validation) |
| 4 | Market Comparison | Mode (single); Market (multi, 2–4) | Component profile; rank statistics table; strengths/constraints table; regulatory evidence; deployment presence |
| 5 | Scenario Simulator | Mode; Scenario[scenario_name]; W C1–W C5 sliders | Named-scenario ranking; dynamic ranking with banner **"SCENARIO RESULT — NOT BASELINE"**; normalized-weight bar |
| 6 | Methodology / Data Quality | Mode | Text panel; `Share Of Markets Scored` by mode; unverified-states table |

**Slicers.** Mode slicers are *single select* and *required*: the measures return blank on a multi-mode selection by design. Sync the Mode slicer across pages 1, 4, 5 and 6.

**Interactions.** *Format → Edit interactions:* set the rank-range and dumbbell visuals so they do not filter other visuals, and leave the map and tables cross-filtering.

**Tooltip page.** Create it with *Page information → Allow use as tooltip*; size *Tooltip*. Show Baseline Rank, Top-5 Frequency, Rank Range, Regulatory Rank Low–High and Deployment Status. Assign it to the map and the ranking tables.

**Drill-through.** On page 4, add `Market[market_short_name]` as a drill-through field, so that right-clicking a market on pages 1–3 opens the comparison.

## 8. Final QA (do not publish until all pass)

- [ ] [measures.md](measures.md) §7: all six checks pass.
- [ ] **Robotaxi.** San Francisco, Los Angeles and San Diego rank 1–3, with Top-5 Frequency of 100%, 100% and about 96%. Boston shows "Not ranked" and a regulatory range of 4–20.
- [ ] **No zeros for missing scores.** No visual shows a zero where a score is missing: 6 robotaxi, 4 sidewalk and 10 drone markets are blank or "Not ranked".
- [ ] **No combined score.** No visual combines modes or shows a "best city overall".
- [ ] **Deployment framing.** Deployment visuals are titled as external validation and never sit inside a score visual.
- [ ] **What-If baseline match.** Every What-If visual shows the "NOT BASELINE" banner, and equal sliders reproduce the baseline.
- [ ] **Credentials and repository.** Save the PBIX **outside** the repository, or in `powerbi/` only after deciding to version it; Import-mode PBIX files contain data. Check that no credentials are embedded: the data source should hold no saved password if you share the file.
