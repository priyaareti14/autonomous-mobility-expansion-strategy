# Executive Story

*Autonomous Mobility Expansion Strategy: an independent portfolio analysis using public data only. Not affiliated with any operator.*

**1. Expansion decisions need more than market size.**
Where to launch a robotaxi, sidewalk-robot or drone service depends on more than how big the market is: demand intensity, weather, labor economics, the built environment and, above all, state law. A population ranking alone would put New York first for everything.

**2. A trusted multi-source warehouse.**
27 public datasets (Census, BLS, NOAA, FAA, EPA) are ingested into Snowflake with checksums and audit trails. They are transformed by a tested dbt pipeline (789 nodes, all passing) into one consistent view of the 35 largest U.S. metros.

**3. Mode-specific models.**
Each mode has its own 10 approved features, chosen in an audit for relevance, redundancy and data quality. Robotaxi has no infrastructure component, because no defensible measure exists, and the model says so instead of inventing one.

**4. Regulation as evidence, not anecdote.**
582 state and federal legal records were coded with citations and confidence levels. Only verified evidence enters the score. Where state law could not be verified (for example Massachusetts robotaxi, or California drone preemption), the market is left **unranked** rather than scored as zero.

**5. Transparent readiness scores.**
Percentile-scored features are combined with equal weights into mode-specific readiness scores. Every score decomposes exactly into the features behind it.

**6. Stress-tested, not asserted.**
Each mode's ranking was re-run under 10,000 random component-weight configurations, two alternative normalizations, 13 one-at-a-time methodology changes, and pessimistic, neutral and optimistic bounds for unresolved law.

**7. Robust opportunities and uncertainty-sensitive markets.**

| Finding | Detail |
|---|---|
| **Robust** | **Robotaxi: San Francisco, Los Angeles and San Diego.** Top 5 in at least 96% of weight configurations and in every named test |
| **Robust** | **Drone: Pittsburgh, Portland and Dallas.** Top 10 in 94–96% of configurations |
| **Depends on assumptions** | Most other positions: robotaxi ranks 4–10, all of sidewalk, and Boston and New York robotaxi, which range from 4th to 20th depending on how unresolved Massachusetts law is treated |

**8. Checked against the real world only after the model was frozen.**
Current commercial deployments, as of October 2026, sit higher in the model. For robotaxi, the median baseline rank is 9 for markets with a commercial service and 22.5 for those without, and all five robotaxi top-5 markets have a commercial service. That is a reasonableness check, not proof of accuracy. Deployments also reflect operator footprint, partnerships and strategy, and the model was never tuned to them.

**What it does not claim:**
- no causal effects;
- no "best city overall": modes are never combined;
- no final recommendation without the robustness context shown alongside every rank.
