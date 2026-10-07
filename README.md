# Autonomous Mobility Network Expansion Strategy

**Market readiness analysis for robotaxis, sidewalk delivery robots and drone delivery across major U.S. metropolitan areas**

> **Disclaimer.** This is an independent portfolio analysis inspired by public developments in autonomous mobility. It is not affiliated with, sponsored by, or performed for Uber or any autonomous-vehicle company. It uses only public data and has no access to proprietary operator data. Nothing here represents the views, plans or strategy of any company.

---

## The business question

> Which U.S. metropolitan markets appear most attractive for autonomous mobility and delivery expansion, and how do those recommendations change under different business priorities?

The project is a transparent decision-support system. It does not declare a single "best" city. Every ranking will be traced back to observed public data. Every weight will be treated as an explicit, stress-tested assumption. Robustness under alternative priorities will be reported alongside any baseline ranking.

## Autonomous modes evaluated

| Mode | What "readiness" is meant to capture |
|---|---|
| Robotaxi | Suitability of a metro for autonomous ride-hailing |
| Sidewalk delivery robot | Suitability for short-distance, low-speed sidewalk delivery |
| Drone delivery | Suitability for small-package aerial delivery |

All three modes share one decision framework of five components, though the underlying variables may differ by mode:

1. Demand & Market Opportunity
2. Operating Environment
3. Economic Attractiveness
4. Regulatory & Autonomy Readiness
5. Infrastructure & Mode Fit

## Market universe

The top 35 U.S. Metropolitan Statistical Areas by resident population, per the U.S. Census Bureau Population Estimates Program, Vintage 2025. Markets are keyed by CBSA code. The selection rule is fixed before any scoring. See [docs/project_scope.md](docs/project_scope.md).

## Planned architecture

```
Public data sources (Census, NOAA, BTS/FAA, EPA, official regulatory sources)
  → Python ingestion + initial validation
  → Snowflake RAW
  → dbt staging → intermediate → core (dimensions / facts) → analytics marts
  → Python EDA, feature engineering, readiness scoring, sensitivity analysis
  → analytical outputs written back to Snowflake
  → Power BI semantic model + decision-support dashboard
```

This is the *planned* design. Components are listed here only as they get built and validated.

**Built so far (Phases 1–9):**
- **Ingestion:** reproducible Python ingestion of 27 public datasets into Snowflake RAW (25 in Phase 3, plus two Phase 6 extensions: the Census Geocoder airport counties and the NOAA HOMR station-history report), with a META audit trail of checksums, idempotent reruns and source-to-RAW reconciliation.
- **dbt (Core 1.12):**
  - 27 staging views
  - 11 intermediate tables: official geography crosswalks, plus candidate station and airport relationships
  - 14 CORE dimension, bridge and fact tables at documented grain
  - `ANALYTICS.MART_MARKET_FEATURE_BASE`: 35 markets, CBSA-native measures only
  - Phase 6: 12 feature-engineering intermediate models, 3 mode feature marts and `DIM_FEATURE`
  - 519 tests, all passing (336 at the end of Phase 4)

**Phase 9 (in review):** a Power BI publication layer and handoff package.
- **Star schema.** 13 compact `ANALYTICS.PBI_*` tables (6 dimensions, 7 facts) report the frozen Phase 7 baseline and the Phase 8 results through generated dbt seeds, reconciled with the committed outputs. Nothing is recalculated.
- **Handoff.** The semantic model, DAX measures (including a labelled user-defined What-If simulator), a six-page dashboard specification, a KPI dictionary, a data dictionary, a theme, a refresh workflow and a step-by-step build guide (`powerbi/`, `docs/powerbi_*.md`).
- **The dashboard itself** is built by hand in Power BI Desktop (Import, role AM_ANALYST).

**Phase 8:** sensitivity, robustness and external validation of the frozen baseline (`scripts/run_phase8_sensitivity.py`, `scripts/run_phase8_deployment_validation.py`; outputs in `outputs/phase8/`). Nothing in the baseline changed. The tests:
- **Weights:** 10,000 seeded Dirichlet component-weight draws per mode, plus named business-priority scenarios.
- **Normalization:** raw and winsorized min-max alternatives.
- **Regulation:** robotaxi pessimistic, neutral and optimistic bounds for the unresolved regulatory records, with nested weight sensitivity.
- **Methodology:** one-at-a-time alternatives (feature drops, A4 airport, block-group density, W2/W3/W4 weather, p90 wind, regulatory coding).
- **Deployment:** a deployment comparison run only after the results were frozen (checksum manifest), as an external reasonableness check, not accuracy.

Robust results so far: robotaxi San Francisco, Los Angeles and San Diego are top 5 in at least 96% of weight draws and in every named test. Most other positions are weight- or regulation-dependent ([docs/robustness_and_sensitivity.md](docs/robustness_and_sensitivity.md)).

**Phase 7:** a transparent **baseline** readiness model (`baseline_v1`) built in dbt, in three steps:
- **Feature scores.** The 30 active features are scored by average-rank percentile in their contract direction, and the 7 regulatory dimensions by verified favorable population share.
- **Weights.** Weights are equal within components and across active components: robotaxi C1–C4 at 25% each (C5 is structurally absent), sidewalk and drone C1–C5 at 20% each.
- **Baseline score.** Components combine into a 0–100 baseline readiness score with a **baseline** rank within each mode.

Markets whose regulatory evidence is incomplete or LOW confidence get no score or rank (robotaxi 6, sidewalk 4, drone 10), only a non-regulatory diagnostic. Every score reconciles exactly and is recomputed independently in Python (`scripts/run_phase7_scoring_qa.py`; outputs in `outputs/phase7/`). Scores are mode-specific. Baseline ranks are not recommendations until the Phase 8 robustness tests. dbt build: 680 nodes, all passing.

**Phase 6.5:** an auditable evidence layer, version-controlled in `evidence/`. It holds 582 regulatory records (robotaxi, sidewalk-robot and drone law for the 31 jurisdictions of the 35 markets, plus federal drone context), each with a citation, verification status and confidence. 180 deployment records are kept separately for external validation only. A regulatory feature contract (`config/regulatory_feature_contract.csv`: 7 active candidates, no weights) and a dimension-specific multi-state mapping that resolves A-012 (`outputs/phase65/`) complete it. Analytical classification only, not legal advice.

**Phase 6:** a tested production feature layer. It covers population-weighted density, the W5 weather-station rule (preferring NOAA HOMR PLCD stations), airport activity on official county FIPS (a new Census Geocoder source, S-40), and population-weighted walkability. Three marts (`ANALYTICS.MART_ROBOTAXI_FEATURES`, `MART_SIDEWALK_DELIVERY_FEATURES`, `MART_DRONE_DELIVERY_FEATURES`) hold 10 pre-regulatory features each for the 35 markets, and `ANALYTICS.DIM_FEATURE` documents every feature. dbt build: 590 nodes, all passing. Clustering was evaluated and not adopted.

**Phase 5:** a read-only feature audit (`python scripts/run_feature_audit.py`) of 70 candidate measures. It covers missingness, variation, outliers, redundancy and market-size duplication. It also compares density, weather-station, airport and walkability mapping methods. Results are in `outputs/` and two docs, linked below. Nothing is written back to Snowflake.

## Current status

| Phase | Scope | Status |
|---|---|---|
| 1 | Scope, market universe, source feasibility, repository foundation | **Complete** |
| 2 | Python environment + Snowflake warehouse foundation | **Complete** |
| 3 | Python ingestion + validation + Snowflake RAW landing | **Complete** |
| 4 | dbt sources, staging, intermediate, core, marts, tests, docs | **Complete** |
| 5 | EDA + feature audit + mapping-method evaluation | **Complete** |
| 6 | Production feature layer (pre-regulatory mode feature sets) | **Complete** |
| 6.5 | Regulatory & deployment evidence curation | **Complete** |
| 7 | Mode-specific readiness models (baseline) | **Complete** |
| 8 | Sensitivity, robustness and external validation | **Complete** |
| 9 | Decision-system publication + Power BI semantic layer | **Complete (in review)** |
| 10 | Power BI semantic model, dashboard, scenario simulator | Not started |
| 11 | Full QA | Not started |
| 12 | CI, documentation, portfolio case study | Not started |

Baseline scores and ranks exist (Phase 7), with robustness ranges (Phase 8). No final recommendation exists yet: the decision system and dashboard come in Phases 9–10.

## Documentation

- [docs/project_scope.md](docs/project_scope.md): decision contract, market universe, framework, hypotheses
- [docs/data_sources.md](docs/data_sources.md): source catalog, feature-feasibility matrix, geography mappings, regulatory evidence framework
- [docs/assumptions_and_limitations.md](docs/assumptions_and_limitations.md): assumptions and limitations register
- [docs/snowflake_foundation.md](docs/snowflake_foundation.md): warehouse, schemas, roles, authentication and cost controls
- [docs/ingestion_pipeline.md](docs/ingestion_pipeline.md): source-to-RAW ingestion, audit trail, checksums, idempotency and reconciliation (source-aligned RAW only)
- [docs/dbt_transformation_layer.md](docs/dbt_transformation_layer.md): dbt architecture, grains, DIM_MARKET, tests, lineage, deferred decisions
- [docs/dbt_reconciliation.md](docs/dbt_reconciliation.md): RAW → STAGING → INTERMEDIATE → CORE → ANALYTICS row counts and explanations
- [docs/feature_audit.md](docs/feature_audit.md): Phase 5 EDA, feature audit and KEEP/MODIFY/DEFER/DROP decisions by mode
- [docs/mapping_methodology.md](docs/mapping_methodology.md): Phase 5 comparison of density, weather-station, airport and walkability mapping methods
- [docs/production_feature_layer.md](docs/production_feature_layer.md): Phase 6 implemented methods, final mode feature sets, directions, components and marts
- [docs/feature_redundancy_resolution.md](docs/feature_redundancy_resolution.md): which signal represents each concept, and scale vs intensity
- [docs/feature_engineering_reconciliation.md](docs/feature_engineering_reconciliation.md): feature lineage and mapping counts
- [docs/regulatory_handoff.md](docs/regulatory_handoff.md): the Phase 6.5 data contract and how it was met
- [docs/regulatory_methodology.md](docs/regulatory_methodology.md): Phase 6.5 evidence methodology, findings, feature contract and A-012 multi-state mapping (not legal advice)
- [docs/regulatory_ambiguities.md](docs/regulatory_ambiguities.md): unresolved, conflicting, pending and unretrievable regulatory evidence
- [docs/deployment_validation_plan.md](docs/deployment_validation_plan.md): how deployment evidence may (and may not) be used in Phase 8
- [docs/readiness_model.md](docs/readiness_model.md): Phase 7 baseline readiness model: normalization, weights, regulatory scoring, incomplete-regulation rule, interpretation rules, Phase 8 handoff
- [docs/score_reconciliation.md](docs/score_reconciliation.md): how every Phase 7 score reconciles to its parts (dbt tests and independent recomputation)
- [docs/robustness_and_sensitivity.md](docs/robustness_and_sensitivity.md): Phase 8 weight, normalization, regulatory and methodology sensitivity; robust vs assumption-dependent findings
- [docs/deployment_validation.md](docs/deployment_validation.md): Phase 8 external reasonableness check against deployment evidence (not accuracy)
- [docs/scenario_simulator_contract.md](docs/scenario_simulator_contract.md): the What-If scenario contract and compact datasets for the future Power BI model
- [docs/powerbi_semantic_model.md](docs/powerbi_semantic_model.md): Phase 9 star schema, keys, relationships, Import vs DirectQuery
- [docs/powerbi_dashboard_spec.md](docs/powerbi_dashboard_spec.md): the six dashboard pages
- [docs/kpi_dictionary.md](docs/kpi_dictionary.md): business definition, formula, grain and limitations of every KPI
- [docs/powerbi_refresh_workflow.md](docs/powerbi_refresh_workflow.md): release and refresh steps
- [docs/executive_story.md](docs/executive_story.md): the concise portfolio story
- [powerbi/BUILD_GUIDE.md](powerbi/BUILD_GUIDE.md), [powerbi/measures.md](powerbi/measures.md), [powerbi/data_dictionary.csv](powerbi/data_dictionary.csv), [powerbi/theme.json](powerbi/theme.json): the Power BI handoff package
- [evidence/research_protocol.md](evidence/research_protocol.md): the evidence coding contract
