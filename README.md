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

**Built so far (Phases 1–6):**
- **Ingestion:** reproducible Python ingestion of 27 public datasets into Snowflake RAW (25 in Phase 3, plus two Phase 6 extensions: the Census Geocoder airport counties and the NOAA HOMR station-history report), with a META audit trail of checksums, idempotent reruns and source-to-RAW reconciliation.
- **dbt (Core 1.12):**
  - 27 staging views
  - 11 intermediate tables: official geography crosswalks, plus candidate station and airport relationships
  - 14 CORE dimension, bridge and fact tables at documented grain
  - `ANALYTICS.MART_MARKET_FEATURE_BASE`: 35 markets, CBSA-native measures only
  - Phase 6: 12 feature-engineering intermediate models, 3 mode feature marts and `DIM_FEATURE`
  - 519 tests, all passing (336 at the end of Phase 4)

**Phase 6.5 (in review):** an auditable evidence layer, version-controlled in `evidence/`. It holds 582 regulatory records (robotaxi, sidewalk-robot and drone law for the 31 jurisdictions of the 35 markets, plus federal drone context), each with a citation, verification status and confidence. 180 deployment records are kept separately for external validation only. A regulatory feature contract (`config/regulatory_feature_contract.csv`: 7 active candidates, no weights) and a dimension-specific multi-state mapping that resolves A-012 (`outputs/phase65/`) complete it. Analytical classification only, not legal advice.

**Phase 6:** a tested production feature layer. It covers population-weighted density, the W5 weather-station rule (preferring NOAA HOMR PLCD stations), airport activity on official county FIPS (a new Census Geocoder source, S-40), and population-weighted walkability. Three marts (`ANALYTICS.MART_ROBOTAXI_FEATURES`, `MART_SIDEWALK_DELIVERY_FEATURES`, `MART_DRONE_DELIVERY_FEATURES`) hold 10 pre-regulatory features each for the 35 markets, and `ANALYTICS.DIM_FEATURE` documents every feature. dbt build: 590 nodes, all passing. Clustering was evaluated and not adopted.

**Phase 5:** a read-only feature audit (`python scripts/run_feature_audit.py`) of 70 candidate measures. It covers missingness, variation, outliers, redundancy and market-size duplication. It also compares density, weather-station, airport and walkability mapping methods. Results are in `outputs/` and two docs, linked below. Nothing is written back to Snowflake.

No scores, weights, normalization or rankings exist yet.

## Current status

| Phase | Scope | Status |
|---|---|---|
| 1 | Scope, market universe, source feasibility, repository foundation | **Complete** |
| 2 | Python environment + Snowflake warehouse foundation | **Complete** |
| 3 | Python ingestion + validation + Snowflake RAW landing | **Complete** |
| 4 | dbt sources, staging, intermediate, core, marts, tests, docs | **Complete** |
| 5 | EDA + feature audit + mapping-method evaluation | **Complete** |
| 6 | Production feature layer (pre-regulatory mode feature sets) | **Complete** |
| 6.5 | Regulatory & deployment evidence curation | **Complete (in review)** |
| 7 | Mode-specific readiness models | Not started |
| 8 | Sensitivity analysis | Not started |
| 9 | Analytical output write-back + reconciliation | Not started |
| 10 | Power BI semantic model, dashboard, scenario simulator | Not started |
| 11 | Full QA | Not started |
| 12 | CI, documentation, portfolio case study | Not started |

No rankings, scores or market-readiness findings exist yet.

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
- [evidence/research_protocol.md](evidence/research_protocol.md): the evidence coding contract
