# Documentation guide

The documentation follows the project's build phases, from scope to the Power BI layer. Use this page to find the right document for your purpose. Back to the [project README](../README.md).

## Start here

| If you want… | Read |
|---|---|
| The story in five minutes | [executive_story.md](executive_story.md) |
| The question, market universe and framework | [project_scope.md](project_scope.md) |
| How readiness is scored | [readiness_model.md](readiness_model.md) |
| How robust the rankings are | [robustness_and_sensitivity.md](robustness_and_sensitivity.md) |
| Every assumption and limitation | [assumptions_and_limitations.md](assumptions_and_limitations.md) |

## 1. Scope and data sources

| Document | Contents |
|---|---|
| [project_scope.md](project_scope.md) | Business question, the fixed 35-market universe, the five-component framework, hypotheses, phase plan |
| [data_sources.md](data_sources.md) | Source catalogue (S-01 to S-41), feature-feasibility matrix, geography mappings, regulatory evidence framework. It includes planned sources that were later not used; the README's data-source table lists the sources actually used |
| [assumptions_and_limitations.md](assumptions_and_limitations.md) | Register of 70 assumptions, scoring choices and limitations, each with its rationale, impact and status |

## 2. Data engineering (Snowflake, ingestion, dbt)

| Document | Contents |
|---|---|
| [snowflake_foundation.md](snowflake_foundation.md) | Warehouse, schemas, least-privilege roles, key-pair authentication, cost controls |
| [ingestion_pipeline.md](ingestion_pipeline.md) | Source-to-RAW ingestion, audit trail, checksums, idempotent reruns, reconciliation |
| [dbt_transformation_layer.md](dbt_transformation_layer.md) | dbt architecture, model grains, the market dimension, tests, lineage |
| [dbt_reconciliation.md](dbt_reconciliation.md) | Row counts from RAW to ANALYTICS, with explanations |

## 3. Feature engineering

| Document | Contents |
|---|---|
| [feature_audit.md](feature_audit.md) | Exploratory audit of 70 candidate measures; KEEP / MODIFY / DEFER / DROP decisions by mode |
| [mapping_methodology.md](mapping_methodology.md) | Comparison of the density, weather-station, airport and walkability mapping methods |
| [production_feature_layer.md](production_feature_layer.md) | The implemented methods and final feature set for each mode, with directions and components |
| [feature_redundancy_resolution.md](feature_redundancy_resolution.md) | Which signal represents each concept; scale vs. intensity |
| [feature_engineering_reconciliation.md](feature_engineering_reconciliation.md) | Feature lineage and mapping counts |

## 4. Regulatory and deployment evidence

| Document | Contents |
|---|---|
| [regulatory_handoff.md](regulatory_handoff.md) | The data contract the regulatory evidence had to meet |
| [regulatory_methodology.md](regulatory_methodology.md) | How the 582 legal records were coded, findings by mode, the multi-state mapping (not legal advice) |
| [regulatory_ambiguities.md](regulatory_ambiguities.md) | Unresolved, conflicting, pending or unretrievable evidence, and the manual-verification checklist |
| [../evidence/research_protocol.md](../evidence/research_protocol.md) | The evidence coding contract (vocabularies, verification and confidence rules) |
| [deployment_validation_plan.md](deployment_validation_plan.md) | How deployment evidence may, and may not, be used |

## 5. Readiness model (baseline)

| Document | Contents |
|---|---|
| [readiness_model.md](readiness_model.md) | Normalization, weights, regulatory scoring, the incomplete-regulation rule, interpretation rules |
| [score_reconciliation.md](score_reconciliation.md) | How every score reconciles to its parts; reproducibility checks |

## 6. Robustness and validation

| Document | Contents |
|---|---|
| [robustness_and_sensitivity.md](robustness_and_sensitivity.md) | 10,000 weight scenarios per mode, business scenarios, normalization, regulatory bounds, methodology tests; robust vs. assumption-dependent findings |
| [deployment_validation.md](deployment_validation.md) | External reasonableness check against real deployments (not accuracy) |
| [scenario_simulator_contract.md](scenario_simulator_contract.md) | The named-scenario contract used by the dashboard's simulator |

## 7. Power BI

| Document | Contents |
|---|---|
| [powerbi_semantic_model.md](powerbi_semantic_model.md) | Star schema, keys, relationships, Import vs. DirectQuery |
| [powerbi_dashboard_spec.md](powerbi_dashboard_spec.md) | Specification of the six dashboard pages |
| [kpi_dictionary.md](kpi_dictionary.md) | Definition, formula, grain and limitations of every KPI |
| [powerbi_refresh_workflow.md](powerbi_refresh_workflow.md) | Step-by-step refresh and release workflow |
| [../powerbi/BUILD_GUIDE.md](../powerbi/BUILD_GUIDE.md) | Manual build guide for the dashboard |
| [../powerbi/measures.md](../powerbi/measures.md) | DAX measures |
| [../powerbi/data_dictionary.csv](../powerbi/data_dictionary.csv) | Every published column, with business name, unit, format and visibility |
| [../powerbi/theme.json](../powerbi/theme.json) | Report theme |

## Where the results live

| Folder | Contents |
|---|---|
| `outputs/` (root files and `figures/`) | Feature audit and mapping-method diagnostics |
| `outputs/phase6/` | Production feature QA and correlations |
| `outputs/phase65/` | Regulatory market mapping |
| `outputs/phase7/` | Baseline scores, components, feature contributions, reconciliation, diagnostics |
| `outputs/phase8/` | Robustness, scenarios, regulatory uncertainty, methodology tests, deployment validation |
| `outputs/phase9/` | Power BI publication QA |
