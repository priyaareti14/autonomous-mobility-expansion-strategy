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

**Built so far (Phases 1–4):**
- **Ingestion:** reproducible Python ingestion of 25 public datasets into Snowflake RAW, with a META audit trail of checksums, idempotent reruns and source-to-RAW reconciliation.
- **dbt (Core 1.12):**
  - 25 staging views
  - 11 intermediate tables: official geography crosswalks, plus candidate station and airport relationships with no selection made
  - 14 CORE dimension, bridge and fact tables at documented grain
  - `ANALYTICS.MART_MARKET_FEATURE_BASE`: 35 markets, CBSA-native measures only
  - 336 tests, all passing

No features, scores, weights or rankings exist yet.

## Current status

| Phase | Scope | Status |
|---|---|---|
| 1 | Scope, market universe, source feasibility, repository foundation | **Complete** |
| 2 | Python environment + Snowflake warehouse foundation | **Complete** |
| 3 | Python ingestion + validation + Snowflake RAW landing | **Complete** |
| 4 | dbt sources, staging, intermediate, core, marts, tests, docs | **Complete (in review)** |
| 5 | EDA + feature audit | Not started |
| 6 | Feature/index engineering (+ clustering only if justified) | Not started |
| 7 | Mode-specific readiness models | Not started |
| 8 | Sensitivity analysis | Not started |
| 9 | Analytical output write-back + reconciliation | Not started |
| 10 | Power BI semantic model, dashboard, scenario simulator | Not started |
| 11 | Full QA | Not started |
| 12 | CI, documentation, portfolio case study | Not started |

No rankings, scores or findings exist yet.

## Documentation

- [docs/project_scope.md](docs/project_scope.md): decision contract, market universe, framework, hypotheses
- [docs/data_sources.md](docs/data_sources.md): source catalog, feature-feasibility matrix, geography mappings, regulatory evidence framework
- [docs/assumptions_and_limitations.md](docs/assumptions_and_limitations.md): assumptions and limitations register
- [docs/snowflake_foundation.md](docs/snowflake_foundation.md): warehouse, schemas, roles, authentication and cost controls
- [docs/ingestion_pipeline.md](docs/ingestion_pipeline.md): source-to-RAW ingestion, audit trail, checksums, idempotency and reconciliation (source-aligned RAW only)
- [docs/dbt_transformation_layer.md](docs/dbt_transformation_layer.md): dbt architecture, grains, DIM_MARKET, tests, lineage, deferred decisions
- [docs/dbt_reconciliation.md](docs/dbt_reconciliation.md): RAW → STAGING → INTERMEDIATE → CORE → ANALYTICS row counts and explanations
