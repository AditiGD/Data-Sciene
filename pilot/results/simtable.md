**How big are the planted effects in points?** Expected extra points from a δ shift on one receiver in a typical final ballot:

| δ (logit) | 0.5 | 1.0 | 2.0 | 3.0 | 1 SD of jury affinity (0.62) | 1 SD of televote affinity (1.52) |
|---|---|---|---|---|---|---|
| extra points | 0.69 | 1.47 | 3.24 | 5.00 | 0.87 | 2.37 |

**Ranking and recovery** (mean of 30 replicates; F = finals only, F+SF = finals + semis; best in a row in bold):

| Scenario | Metric | M0 F | M0 F+SF | M1 F | M1 F+SF | M2 F | M2 F+SF |
|---|---|---|---|---|---|---|---|
| Sparse, δ=1 (≈1.5 pts) | AUC | 0.83 | 0.90 | 0.82 | 0.88 | 0.87 | **0.92** |
| | recall@40 | 0.15 | 0.26 | 0.22 | 0.33 | 0.32 | **0.47** |
| Sparse, δ=2 (≈3.2 pts) | AUC | 0.96 | **0.99** | 0.95 | 0.98 | 0.96 | 0.99 |
| | recall@40 | 0.54 | 0.71 | 0.61 | 0.76 | 0.66 | **0.78** |
| Realistic background + δ=1 | Spearman(est, true b) | 0.60 | 0.70 | 0.68 | 0.77 | 0.74 | **0.83** |
| | top-20 overlap with true top-20 | 0.22 | 0.30 | 0.35 | 0.41 | 0.37 | **0.46** |
| | recall@40 of the planted increment | 0.13 | **0.15** | 0.11 | 0.14 | 0.11 | 0.12 |
| Realistic background + δ=2 | Spearman | 0.61 | 0.71 | 0.68 | 0.78 | 0.74 | **0.83** |
| | top-20 overlap | 0.39 | 0.50 | 0.47 | 0.55 | 0.51 | **0.59** |
| | recall@40 of the planted increment | 0.36 | **0.42** | 0.32 | 0.38 | 0.32 | 0.36 |
| Thurstone noise (misspecified) + realistic, δ=2 | Spearman | 0.62 | 0.72 | 0.69 | 0.78 | 0.73 | **0.82** |
| | top-20 overlap | 0.40 | 0.51 | 0.47 | **0.56** | 0.48 | 0.54 |
| RQ3: δ=2 in televote only, sparse | AUC of the T−J gap | 0.80 | 0.87 | 0.90 | **0.95** | 0.89 | 0.94 |
| | recall@40 of the gap | 0.17 | 0.29 | 0.36 | **0.55** | 0.36 | 0.53 |

**Inference calibration** (M2 lfsr < 0.05 against a naive per-pair t-test on M0 residuals):

| Scenario / scope | M2 lfsr: power (true b > 1) | M2 lfsr: false-sign rate | M2 90% coverage | M0 t-test p<.05: power (planted) | M0 t-test p<.05: FDP | M0 t + BH10%: power |
|---|---|---|---|---|---|---|
| Sparse δ=2, F | 0.23 | 0.008 | 0.98 | 0.75 | 0.44 | 0.08 |
| Sparse δ=2, F+SF | 0.54 | 0.011 | 0.98 | 0.90 | 0.49 | 0.52 |
| Realistic δ=1, F | 0.55 | 0.015 | 0.83 | 0.28 | 0.91 | 0.02 |
| Realistic δ=1, F+SF | **0.78** | 0.017 | 0.84 | 0.41 | 0.92 | 0.16 |
| Realistic δ=2, F+SF | 0.78 | 0.014 | 0.84 | 0.74 | 0.86 | 0.45 |

In the realistic scenario every dyad carries some bias. "FDP" there counts only planted pairs as true, so the relevant error measure for M2 is the false-sign rate.

**What the simulation shows:**

1. **Adding semi-finals helps every method in every scenario.**
   - M2 recall@40 at δ=1 rises from 0.32 to 0.47. M2 Spearman with the true affinities rises from 0.74 to 0.83.
   - Power to flag pairs with true b > 1 rises from 0.55 to 0.78.
   - For the RQ3 gap, AUC rises from 0.89 to 0.94.
   - Finals-only gives about 30–55% less power.
2. **M2 beats the proposal baseline at recovering the affinity structure** that students will publish.
   - Spearman with the truth: 0.83 vs 0.70. Top-20 overlap: 0.46–0.59 vs 0.30–0.50.
   - It also wins under misspecified (Thurstone) noise.
   - M1 sits in between, and is equal or better than M2 for the RQ3 gap, because it works on the points scale.
3. **Where the advantage disappears.** M0 is slightly better at ranking a *planted increment on top of a dense background* (recall 0.15 vs 0.12). Shrinkage pulls every pair, planted or not, toward 0 by an amount that depends on its n. M2's advantage is in estimating each pair's total affinity, which is the RQ1 estimand, not in detecting increments.
4. **lfsr flags are well calibrated for sign** (false-sign rate 0.8–1.7%, nominal 5%). Naive per-pair t-tests on M0 are not: FDP is 0.44–0.92, which supports the proposal's instinct to avoid single-pair significance on M0.
5. **Coverage.** Laplace 90% intervals are conservative in sparse settings (0.98) and under-cover in the dense realistic setting (0.83). The cause is partly that the EB variance under-estimates the true σ²_T (1.7–2.0 vs 2.32) when iterations are capped at 12. In the final analysis, run EB to convergence and use the parametric bootstrap for reported intervals.
6. **Sparse true effects with a Gaussian prior get over-shrunk.** EB σ² falls to about 0.04–0.1, which kills lfsr power for δ=1. The real data are dense (σ²_T = 2.3), so this is not the operative regime. A heavy-tailed prior (stretch) would make the model robust to either regime.
