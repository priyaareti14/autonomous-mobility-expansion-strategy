# Power BI Refresh Workflow (Phase 9)

The dashboard is a **release artifact**: it is refreshed when a new analytical release is committed, not on a schedule. Run every command from the repository root with the `.venv` active. Stop at the first failure.

| Step | When | Command | Pass condition |
|---|---|---|---|
| 1. Ingestion | Only if a source vintage changes (a deliberate, documented decision; A-004) | `python scripts/run_ingestion.py --all`, then `python scripts/validate_raw_landing.py` | 0 FAIL |
| 2. dbt warehouse | Always | `python scripts/run_dbt.py build --threads 2` | All nodes PASS |
| 3. Phase 7 analytics | When model inputs (features, evidence, contracts) change | `python scripts/build_regulatory_seed.py --check` (regenerate without `--check` if evidence changed), then `python scripts/run_dbt.py build --threads 2`, then `python scripts/run_phase7_scoring_qa.py` | 40/40, outputs/phase7 reproducible |
| 4. Phase 8 analytics | When Phase 7 results change | `python scripts/run_phase8_sensitivity.py`, then `python scripts/run_phase8_deployment_validation.py` | 40/40 and 5/5; outputs/phase8 reproducible |
| 5. Publication seeds | When Phase 8 outputs change | `python scripts/build_powerbi_seeds.py`, then `python scripts/build_powerbi_seeds.py --check` | "phase8 seeds match outputs/phase8" |
| 6. Publication layer | Always after 3–5 | `python scripts/run_dbt.py build --threads 2`, then `python scripts/run_phase9_publication_qa.py` | All dbt nodes PASS; publication QA 0 failures |
| 7. Power BI | After 6 | Power BI Desktop → **Refresh** (Import) → run the measure QA in [powerbi/measures.md](../powerbi/measures.md) §7 → republish | QA matches the committed outputs |

**Rules:**
- **Never edit a seed by hand.** Every generated seed is checked against its source (`--check`) and reconciled in the publication QA.
- **Never refresh Power BI against an unvalidated warehouse.** Steps 2–6 must pass first.
- **Re-check the narrative.** If Phase 7/8 results change, re-check the dashboard's headline text (e.g. "SF / LA / SD remain the stable leading group") against `docs/robustness_and_sensitivity.md` §8 before republishing.
- **Credentials.** Credentials stay in `.env` and the Power BI data-source settings, never in the repository. Power BI uses the read-only role **AM_ANALYST**.
- **Cost.** Each dbt build uses warehouse credits. Refreshing in Import mode reads about 3,000 rows (A-058: the resource-monitor assignment is still to be verified by AM_ADMIN).
