# dbt project: `autonomous_mobility`

Transforms the Phase 3 RAW tables into STAGING → INTERMEDIATE → CORE → ANALYTICS in Snowflake. The full design is in [../docs/dbt_transformation_layer.md](../docs/dbt_transformation_layer.md) and the row-count trail is in [../docs/dbt_reconciliation.md](../docs/dbt_reconciliation.md).

```
models/
  staging/       _sources.yml (RAW + META), _staging.yml, census/ labor/ weather/ airports/ built_environment/
  intermediate/  official crosswalks, market universe, ACS join, candidate station/airport relationships
  core/          dim_market, dim_weather_station, dim_airport, brg_*, fct_*
  marts/         mart_market_feature_base
seeds/           frozen_market_universe.csv  (approved 35 markets, generated from docs/project_scope.md)
tests/           singular business-rule and reconciliation tests
macros/          generate_schema_name (use the existing schemas), cleaning, staging helpers, generic tests
```

## Setup
1. Copy `profiles.example.yml` to `profiles.yml`. The copy is git-ignored and holds only `env_var()` references.
2. Make sure the repository `.env` defines the `SNOWFLAKE_*` variables (see `.env.example`).
3. From the repository root, run:
   ```
   python scripts/run_dbt.py debug
   python scripts/run_dbt.py build
   ```

dbt connects as the service user with the **AM_TRANSFORMER** role (key-pair authentication). It writes only to the existing schemas and never creates any.
