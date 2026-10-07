# Robustness & Sensitivity (Phase 8)

**Status:** Phase 8 deliverable (in review) · **Input snapshot:** `bc2023b` (Phase 7) · **Baseline:** `baseline_v1` (model inputs `55b1cb4`) · **Random seed:** `20261007` · **Evidence as of:** 2026-10-05

## 1. Purpose and the three kinds of result

Phase 8 asks whether the Phase 7 **baseline** ranks survive reasonable changes to the analytical assumptions. Every result in this document is one of three kinds:

| Kind | Meaning |
|---|---|
| **BASELINE RESULT** | The frozen Phase 7 rank under equal weights, percentile normalization and the approved mappings |
| **ROBUST RESULT** | A position that holds across the tested weight space, normalizations and methodology alternatives |
| **SENSITIVITY-DEPENDENT RESULT** | A position that moves materially under at least one tested assumption. The assumption is named |

**The baseline is immutable.**
- `scripts/run_phase8_sensitivity.py` first recomputes every Phase 7 feature score, component score, readiness score and rank from the warehouse, and stops unless they match exactly.
- Every alternative changes **one assumption at a time**, except the nested robotaxi weight-by-regulation analysis (§5), which is a deliberate two-factor test.
- No weight, feature, normalization or mapping was changed because of a result.

Outputs are in `outputs/phase8/`, with figures in `outputs/phase8/figures/`. `model_metadata.json` records the seed, the methods and a checksum manifest.

## 2. Named business-priority scenarios (`business_priority_scenarios.csv`)

| Scenario | Robotaxi (C1–C4) | Sidewalk and drone (C1–C5) |
|---|---|---|
| NEUTRAL | 25 / 25 / 25 / 25 (baseline) | 20 each (baseline) |
| DEMAND, OPERATING_ENVIRONMENT, ECONOMIC, REGULATORY priority | priority 40%, others 20% each | priority 40%, others 15% each |
| INFRASTRUCTURE priority | **not defined** (no robotaxi C5) | C5 40%, others 15% |

These are **scenario assumptions**, not estimates of any company's preferences. The weights are the machine-readable What-If contract (`scenario_simulator_contract.csv`; [scenario_simulator_contract.md](scenario_simulator_contract.md)).

**Rank 1 under each scenario:**
- **Robotaxi:** San Francisco under every scenario. Los Angeles and San Diego fill ranks 2–3 everywhere.
- **Sidewalk:** San Francisco under every scenario except REGULATORY_PRIORITY. There the top three become Dallas, Miami and Austin, which are statute states.
- **Drone:** Pittsburgh (NEUTRAL, REGULATORY), Portland (DEMAND, ECONOMIC, OPERATING_ENVIRONMENT) or Detroit (INFRASTRUCTURE).

**Largest scenario rank ranges:**

| Mode | Market | Rank range |
|---|---|---|
| Sidewalk | Miami | 2–22 |
| Sidewalk | Phoenix | 4–23 |
| Sidewalk | New York | 6–24 |
| Drone | New York | 7–25 |
| Robotaxi | Seattle | 12–24 |
| Robotaxi | Chicago | 8–19 |

## 3. Random component-weight sensitivity (`weight_sensitivity_summary.csv`)

**Design:**
- **Draws:** **10,000 draws per mode** from Dirichlet(α = 1) over the active components: 4 for robotaxi, 5 for sidewalk and drone. Within-component feature weights stay equal.
- **Generator:** `numpy.random.default_rng(20261007)`, with draws taken in the order robotaxi, sidewalk, drone.
- **Common random numbers:** the robotaxi draws are reused for the three regulatory scenarios.
- **Ranking:** markets are ranked by standard competition rank among markets with a complete score, with ties at 6 decimals.
- **Storage:** only aggregates are stored; the draw matrix is reproducible from the seed.

**Interpretation.** Dirichlet(1) is uniform over the weight simplex. It is a **mathematical stress test across possible component priorities**, not a probability distribution of executive preferences. Frequencies are "frequency across tested weight configurations", never a probability of being the best market.

**Metrics** for every market × mode:
- mean, median, standard deviation, best and worst rank;
- 5th, 25th, 75th and 95th rank percentiles (`inverted_cdf`), and the 90% interval and IQR;
- top-1, top-3, top-5 and top-10 frequency;
- mean and standard deviation of the score;
- mean absolute change from the baseline rank, and the frequency within ±2 ranks of baseline.

### 3.1 Baseline top 10 by mode

**Robotaxi** (29 ranked markets)

| Base | Market | Mean | Median | SD | Best–Worst | 90% interval | Top-5 | Top-10 |
|---|---|---|---|---|---|---|---|---|
| 1 | San Francisco | 1.06 | 1 | 0.24 | 1–2 | 1–2 | 100% | 100% |
| 2 | Los Angeles | 2.33 | 2 | 0.48 | 2–4 | 2–3 | 100% | 100% |
| 3 | San Diego | 2.88 | 3 | 1.18 | 1–13 | 1–5 | 96% | 100% |
| 4 | Denver | 7.95 | 5 | 4.78 | 3–19 | 4–17 | 51% | 71% |
| 5 | Miami | 7.46 | 6 | 3.93 | 3–25 | 3–15 | 44% | 81% |
| 6 | Sacramento | 8.23 | 7 | 4.14 | 4–20 | 4–17 | 37% | 72% |
| 7 | Phoenix | 8.70 | 8 | 3.99 | 4–21 | 4–17 | 27% | 74% |
| 8 | Tampa | 10.67 | 10 | 3.77 | 5–19 | 6–18 | 3% | 53% |
| 9 | Orlando | 11.64 | 12 | 3.22 | 5–22 | 7–17 | 1% | 39% |
| 10 | Austin | 11.71 | 11 | 3.35 | 5–20 | 7–18 | 0.2% | 41% |

**Sidewalk delivery** (31 ranked markets)

| Base | Market | Mean | Median | SD | Best–Worst | 90% interval | Top-5 | Top-10 |
|---|---|---|---|---|---|---|---|---|
| 1 | San Francisco | 4.23 | 1 | 5.89 | 1–25 | 1–19 | 79% | 85% |
| 2 | Los Angeles | 6.26 | 3 | 6.47 | 1–27 | 1–21 | 67% | 79% |
| 3 | Seattle | 6.13 | 5 | 4.13 | 1–20 | 2–15 | 54% | 84% |
| 4 | Las Vegas | 7.73 | 7 | 3.80 | 1–20 | 3–14 | 35% | 75% |
| 5 | San Diego | 9.44 | 7 | 7.15 | 1–29 | 2–24 | 41% | 65% |
| 6 | Washington | 8.67 | 9 | 2.88 | 2–19 | 4–13 | 16% | 71% |
| 7 | Boston | 10.62 | 10 | 4.81 | 1–26 | 4–19 | 19% | 51% |
| 8 | Portland | 10.98 | 9 | 6.38 | 2–27 | 4–23 | 22% | 60% |
| 9 | Dallas | 10.27 | 12 | 5.52 | 1–22 | 2–18 | 27% | 44% |
| 10 | Miami | 11.21 | 10 | 8.37 | 1–31 | 1–26 | 33% | 52% |

**Drone delivery** (25 ranked markets)

| Base | Market | Mean | Median | SD | Best–Worst | 90% interval | Top-5 | Top-10 |
|---|---|---|---|---|---|---|---|---|
| 1 | Pittsburgh | 4.24 | 3 | 3.06 | 1–18 | 1–10 | 72% | 96% |
| 2 | Portland | 4.07 | 3 | 3.26 | 1–14 | 1–11 | 73% | 94% |
| 3 | Detroit | 5.64 | 4 | 4.71 | 1–21 | 1–14 | 55% | 79% |
| 4 | Dallas | 5.60 | 5 | 2.75 | 1–18 | 2–10 | 57% | 96% |
| 5 | Austin | 7.86 | 7 | 4.17 | 1–23 | 2–16 | 31% | 76% |
| 6 | Houston | 7.84 | 7 | 2.91 | 2–16 | 4–13 | 23% | 76% |
| 7 | Washington | 9.32 | 8 | 5.72 | 1–23 | 2–21 | 32% | 61% |
| 8 | Phoenix | 9.35 | 9 | 5.54 | 1–22 | 1–18 | 30% | 58% |
| 9 | San Antonio | 11.49 | 11 | 5.43 | 2–25 | 4–22 | 14% | 47% |
| 10 | Seattle | 10.69 | 12 | 6.87 | 1–25 | 1–22 | 31% | 47% |

**Most stable ranks** (lowest rank SD):
- **Robotaxi:** Indianapolis (last in every draw), San Francisco, Los Angeles, San Diego.
- **Sidewalk:** Charlotte, Columbus, Detroit and Cleveland, all near the bottom.
- **Drone:** Columbus, Dallas, Houston, Pittsburgh, Portland.

**Most unstable ranks:**

| Mode | Market | Rank SD | Best–worst |
|---|---|---|---|
| Robotaxi | Washington | 7.4 | 2–27 |
| Robotaxi | Seattle | 7.3 | 4–26 |
| Robotaxi | Portland | 6.8 | 6–28 |
| Robotaxi | Chicago | 6.0 | 2–22 |
| Sidewalk | Miami | 8.4 | 1–31 |
| Sidewalk | New York | 8.2 | 1–31 |
| Sidewalk | Tampa | 7.3 | 2–30 |
| Drone | Seattle | 6.9 | 1–25 |
| Drone | New York | 6.6 | 1–25 |
| Drone | Denver | 6.0 | 2–25 |

These markets are strong on some components and weak on others, so their rank depends on which component is emphasised.

## 4. Alternative normalization (`normalization_sensitivity.csv`, `normalization_comparison.csv`)

The alternatives apply to the 30 contract features, using the already-approved transformed values:

| Method | Formula |
|---|---|
| A: BASELINE_PERCENTILE | Average-rank percentile (Phase 7) |
| B: RAW_MINMAX | 100 × (x − min) / (max − min) |
| C: WINSORIZED_MINMAX | Clip to the 5th and 95th cross-sectional percentiles (numpy `linear`), then min-max on the clipped range |

For every method, LOWER_IS_MORE_FAVORABLE uses 100 − score. A constant feature would score 50; no active feature is constant.

**C4 is held at the baseline.** Verified favorable shares are already bounded operational quantities, and the weight limit includes an unbounded NO_LIMIT_STATED category.

Comparisons are of ranks within each mode, never of scores across systems.

| Mode | Method | Spearman ρ | Kendall τ-b | Top-5 overlap | Top-10 overlap | Max rank move | Markets moving ≥ 5 |
|---|---|---|---|---|---|---|---|
| Robotaxi | Raw min-max | 0.962 | 0.852 | 4 / 5 | 8 / 10 | 6 | 2 (Chicago 14→20, Las Vegas 12→7) |
| Robotaxi | Winsorized | 0.965 | 0.862 | 5 / 5 | 8 / 10 | 5 | 1 (Tampa 8→13) |
| Sidewalk | Raw min-max | 0.973 | 0.884 | 4 / 5 | 9 / 10 | 6 | 2 (San Diego 5→11, Austin 13→8) |
| Sidewalk | Winsorized | 0.989 | 0.940 | 4 / 5 | 9 / 10 | 3 | 0 |
| Drone | Raw min-max | 0.974 | 0.878 | 5 / 5 | 10 / 10 | 5 | 1 (Philadelphia 12→17) |
| Drone | Winsorized | 0.966 | 0.865 | 5 / 5 | 10 / 10 | 5 | 1 (Philadelphia 12→17) |

**Reading:** percentile and magnitude-sensitive scoring agree closely (ρ ≥ 0.96 everywhere). Normalization is a **minor** source of rank uncertainty compared with component weights.

## 5. Robotaxi regulatory uncertainty (`regulatory_uncertainty.csv`)

**The records.** The 10 LOW-confidence robotaxi records stay sensitivity-only and are never treated as known:
- Massachusetts, New Jersey and Ohio: driverless, commercial and local authority;
- New York: local authority.

**The bounds.** Each is applied to the unknown population share of every dimension, without overwriting any evidence:

```
scenario_favorable_share = verified_favorable_share + unknown_share × assumed_favorable_fraction
PESSIMISTIC = 0    NEUTRAL = 0.5    OPTIMISTIC = 1
```

These are analytical bounds. They do not claim the law is favorable or unfavorable. All 35 markets are ranked under equal weights. Complete-C4 markets keep their baseline scores exactly (tested), but they can shift a few ranks because six more markets enter the ranking.

| Market (C4 incomplete) | Pessimistic | Neutral | Optimistic | Rank range | Score range |
|---|---|---|---|---|---|
| Boston | 20 | 8 | 4 | **16** | 51.1–73.8 |
| New York | 18 | 14 | 7 | **11** | 51.7–65.9 |
| Cleveland | 33 | 31 | 25 | 8 | 21.3–46.3 |
| Columbus | 34 | 34 | 28 | 6 | 19.0–44.0 |
| Philadelphia | 16 | 15 | 14 | 2 | 54.7–60.2 |
| Cincinnati | 32 | 33 | 30 | 3 | 22.5–41.5 |

**Boston and New York are explicitly regulation-dependent.** Boston ranges from 20th (pessimistic) to 4th (optimistic). Under the optimistic bound, Boston enters the top 5 in 69% of weight draws, with New York at 33%.

The Ohio markets stay in the lower group under every bound.

**Nested weight sensitivity.** Each regulatory scenario was run against the same 10,000 robotaxi draws. The three scenarios are **not averaged**, because that would assign arbitrary probabilities to unresolved law. Top-5 frequency under each:

| Scenario | Top-5 frequency, leading markets |
|---|---|
| Pessimistic | San Francisco 100%, Los Angeles 99.7%, San Diego 94.8%, Denver 48.7%, Miami 41.1% |
| Neutral | San Francisco 100%, Los Angeles 99.7%, San Diego 93.4%, Denver 44.0%, Sacramento 35.6%, Miami 35.3%, New York 27.7% |
| Optimistic | San Francisco 100%, Los Angeles 99.7%, San Diego 91.7%, Boston 69.4%, New York 32.6%, Denver 30.0% |

**Extension** (beyond the brief; it uses the same bounds). Sidewalk and drone markets with incomplete C4 get the same three bounds, so that no market is left without a regulatory range.
- **Sidewalk weight limit:** in an incomplete market the limit uses verified states only, scored at the baseline score of the same limit value. The baseline domain is unchanged.
- **Drone** (incomplete C4 because of DR-CA/GA/IL/MA/TN-02), rank under the three bounds:

| Market | Pessimistic | Neutral | Optimistic |
|---|---|---|---|
| Sacramento | 9 | 1 | 1 |
| San Francisco | 11 | 5 | 2 |
| San Diego | 13 | 7 | 3 |
| Los Angeles | 14 | 9 | 4 |
| Atlanta | 18 | 11 | 5 |
| Riverside | 24 | 14 | 7 |

- **Sidewalk:** Nashville ranges 31 / 28 / 22. Chicago, Cincinnati and Indianapolis stay low under every bound.

## 6. One-at-a-time methodology sensitivity (`methodology_sensitivity.csv`, `methodology_comparison.csv`)

| Test | Mode(s) | Spearman ρ vs baseline | Largest movements |
|---|---|---|---|
| **DROP_INCOME**: PF05 out of C1 (4 features at ¼) | Robotaxi | 0.988 | Sacramento 6→9; none ≥ 5 |
| **DROP_WAGE**: PF09 out of C3 (PF06 alone) | Robotaxi | 0.937 | 5 markets ≥ 5: Sacramento 6→12, Atlanta 15→9, Pittsburgh 21→15, Charlotte 24→18, San Antonio 17→23 |
| **DROP_DENSITY**: PF02 out of C1 | Sidewalk | 0.994 | Atlanta 26→23; none ≥ 5 |
| DROP_WALKABILITY | Sidewalk | **not run** | PF15 is sidewalk C5's only feature; dropping it removes a component, which would change component weights, not feature weights |
| DROP_COMMERCIAL_DIMENSION (A-056) | Robotaxi | 0.990 | Charlotte 24→19 |
| **AIRPORT_A4**: PF04 from the 80 km radius diagnostic (PX03), LOG1P | Robotaxi | 1.000 | Austin and Dallas swap 10/11; top 5 unchanged |
| **DENSITY_D3**: PF02 from population-weighted block-group density (PX02), LOG1P | Robotaxi, sidewalk | 1.000 / 0.999 | ≤ 1 rank |
| **WEATHER W2 / W3 / W4**: Phase 5 station methods for PF11, PF12 (and PF13 for W3) | All | 0.989–0.999 | ≤ 4 ranks (e.g. Las Vegas 12→8 and Tampa 8→12 robotaxi W4; Riverside 13→9 robotaxi W3) |
| **WIND_P90**: PF14 from the p90 of hourly-mean wind normals (PX04) | Drone | 0.991 | Denver 15→12, Orlando 11→14 |
| ABSENCE_HALF_CREDIT (A-043/A-055) | All | 0.886–0.948 | **8 drone, 8 robotaxi, 6 sidewalk markets move ≥ 5**: Washington robotaxi 18→9, Denver sidewalk 11→4, Seattle drone 10→5 |
| ELIGIBILITY_CONFIDENCE_ONLY (A-051) | All | 1.000 | Only Atlanta (drone) changes completeness: it becomes scored and **ranks 1st** (67.6), because Georgia's MEDIUM, not-retrieved preemption record is then accepted. Every other market moves ≤ 1 rank |
| NEVADA_UNADJUSTED (A-046) | Sidewalk | 0.999 | Las Vegas 4→3 |

**Notes on these tests:**
- **Wind.** The p90 is a climatological statistic of hourly-mean normals. It is **not an observed extreme-wind metric**.
- **Weather.** Phase 5 W3 publishes no snowfall for 6 markets, which keep their baseline snowfall in that test (disclosed in `qa_checks_sensitivity.csv`).
- **A-041 not evaluated.** The current-class PLCD variant would change only Los Angeles' station, and no alternative station values were ever computed for it. Building a new station selection would mean inventing a method, so it was not done.

**Reading:**
- **Mapping and data alternatives barely matter.** Airport, density, weather and wind all give ρ ≥ 0.99.
- **Three choices do matter:**
  - the robotaxi **wage** feature (drop-wage);
  - the treatment of **statutory absence** (A-055), which moves a third of the markets by five ranks or more;
  - component **weights**.

## 7. Robustness summary (`robustness_summary.csv`)

**Contents.** One row per market × mode:
- the baseline rank and score, and the Dirichlet statistics;
- the rank range across the named business scenarios, normalizations, methodology tests and regulatory bounds;
- the tested best and worst rank.

There is no composite robustness score. Regulatory ranks are kept separate from the others because they rank 35 markets, while the other tests rank only complete markets.

**Pattern flags.** Thresholds are recorded in `model_metadata.json`, and a market can carry several flags.

| Flag | Rule |
|---|---|
| CONSISTENT_TOP_PERFORMER | Top-5 frequency ≥ 80%, and rank ≤ 5 under every named normalization, methodology and business test |
| WEIGHT_SENSITIVE | 90% Dirichlet rank interval ≥ 10 ranks |
| NORMALIZATION_SENSITIVE | Rank range across normalizations ≥ 5 |
| METHODOLOGY_SENSITIVE | Rank range across the one-at-a-time methodology tests ≥ 5 |
| REGULATION_SENSITIVE | The market's **own** score moves across the regulatory bounds, and its rank range ≥ 5. Complete markets displaced only by newly ranked markets are not flagged |

CONSISTENT_MIDFIELD and CONSISTENT_LOWER_RANK are **deferred**: any band boundary would be arbitrary, and the continuous metrics are published instead.

**Flag counts:**

| Mode | CONSISTENT_TOP_PERFORMER | WEIGHT_SENSITIVE | METHODOLOGY_SENSITIVE | NORMALIZATION_SENSITIVE | REGULATION_SENSITIVE |
|---|---|---|---|---|---|
| Robotaxi | 3 (San Francisco, Los Angeles, San Diego) | 22 | 15 | 4 | Boston, New York, Cleveland, Columbus |
| Sidewalk | 0 (San Francisco's top-5 frequency is 79%) | 26 | 8 | 2 | Nashville |
| Drone | 0 | 21 | 10 | 1 | 9 unscored markets: Atlanta, Boston, Chicago, Los Angeles, Nashville, Riverside, Sacramento, San Diego, San Francisco |

## 8. Decision-relevant findings

**Robust findings:**
- **Robotaxi: San Francisco, Los Angeles and San Diego.** They are top 5 in 96–100% of weight draws. They are ranked 1–3 under every business scenario, normalization, methodology test and all three regulatory bounds, and stay top 5 in 92–100% of draws in each nested regulatory simulation. This is the strongest and most stable result in the project.
- **Drone: Pittsburgh, Portland and Dallas.** They are top 10 in 94–96% of draws. Dallas has the lowest rank SD of any leading market (2.75).
- **Normalization and the data-mapping alternatives** (airport, density, weather, wind) do not materially change any mode's ranking (ρ ≥ 0.96).

**Assumption-dependent findings:**
- **Robotaxi, ranks 4–10** (Denver, Miami, Sacramento, Phoenix, Tampa, Orlando, Austin). They are strong in the baseline but WEIGHT_SENSITIVE, with 90% intervals spanning 10–13 ranks. Their order should not be read as meaningful.
- **Robotaxi Boston and New York** depend on unresolved regulation. They are near the top under optimistic law and mid-pack under pessimistic law.
- **Sidewalk is weight-dependent throughout.**
  - Even San Francisco ranges from rank 1 to 25 across draws.
  - Under REGULATORY_PRIORITY, the leaders become the statute states: Dallas, Miami and Austin.
  - California's top positions rely on demand, wage and walkability, and are offset by having no PDD statute.
- **Drone C4 dominates (A-054),** and 10 markets, including Los Angeles, San Francisco and Sacramento, are unscored. Under the optimistic bound Sacramento would rank 1st, so the drone baseline top 10 is conditional on California's unresolved preemption evidence.
- **The statutory-absence treatment (A-055)** is the single most influential coding choice tested. Giving absence half credit moves 22 market × mode positions by five ranks or more.

**Strong only under one narrow assumption:**
- Boston (robotaxi), rank 4, only under the optimistic regulatory bound.
- Sacramento (drone), rank 1 only if California's unretrieved preemption evidence is favorable.
- Atlanta (drone), unscored in the baseline, ranks 1st only under the confidence-only eligibility reading (A-051), which accepts Georgia's MEDIUM but unretrieved preemption record.
- Las Vegas (robotaxi), 12→7, only under raw min-max.
- Denver (sidewalk), 11→4, only with absence half credit.

## 9. Reproducibility

- **Determinism:**
  - one seed (`20261007`); inputs rounded to 9 decimals on read;
  - every read ordered by grain, and every export sorted with a stable sort at fixed 6-decimal precision (−0 normalized to 0);
  - no timestamps or repository HEAD in any artifact; `git_input_commit` = `bc2023b`.
- **Verified:** two complete runs of both Phase 8 scripts produced **32 of 32 files byte-identical**, including the figures.

## 10. Limitations

See A-059 to A-066 in [assumptions_and_limitations.md](assumptions_and_limitations.md).

- **Dirichlet(1)** treats every weight configuration as equally plausible, which no real business does.
- **Ranking universe.** Ranks are within the complete-market universe (29 / 31 / 25) unless stated.
- **Regulatory bounds** are bounds, not forecasts.
- **Feature drops** are only possible where a component keeps at least one feature.
- **No sensitivity covers** municipal ordinances, operator economics or the CBSA-versus-service-area mismatch (A-002, A-047).
