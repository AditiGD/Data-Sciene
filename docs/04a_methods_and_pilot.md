# 04a · Statistical methodology and pilot: Eurovision voting favouritism (2016–2025)

**Status:** design plus an *exploratory* pilot on the real data. Every number below comes from scripts in `pilot/` (summaries in `pilot/results/`). **The pilot numbers are feasibility evidence, not study findings.** See `04_study_design_v2.md §10` on what this means for confirmatory claims.

> **Where this document and `04_study_design_v2.md` (v2.1) differ, `04` governs.** In particular, v2.1 changes: double-centred estimand and centrality wording; in-likelihood covariates; reference-design Δ; bootstrap as minimum viable; pre-fixed γ = 1.0; and the red-team responses in `06`.
>
> Known deviation: the pilot still includes San Marino's synthetic televote. The final run excludes it, so pilot pair lists involving SM televote must not be reported.

**Data source to cite:** Graph Drawing Contest 2026 fork, https://github.com/Graph-Drawing-Contest/eurovision-dataset (commit 1f39f6b, ends 2025). Its 2016–2025 data is byte-identical to the upstream EurovisionAPI/dataset clone used in the pilot. The 2026 hold-out exists only upstream.

**Pilot runtime:** about 1 min for the real-data analysis and about 10 min for the simulation (4 cores).

---

## 0. Executive summary

| Decision | Recommendation |
|---|---|
| Estimand (RQ1) | **Dyad affinity** `b_vj`: how much higher voter *v* ranks receiver *j* than *j*'s song quality in that show predicts, relative to how *v* treats other songs. Estimate it per vote type (jury J, televote T). Report it on the model scale and as **expected extra points per show**. |
| Primary model | **M2: top-10 rank-ordered logit (Plackett–Luce)** on each ballot. Show-specific song quality is a fixed effect `q[j, year, show, type]`. Dyad effects are Gaussian random effects `b[v, j, type] ~ N(0, σ²_type)`, and σ² is estimated by empirical Bayes. The model respects the ballot exactly: 10 distinct songs ranked 12…1, no self-vote, and the eligible set changes by show. Fit by MAP in about 2 s with numpy/scipy. Uncertainty comes from Laplace SEs or a parametric bootstrap. |
| Robustness model | **M1: linear crossed model on points with an empirical-Bayes-shrunk dyad effect** (ridge). It takes 10 lines of numpy, or `lmer(points ~ 0 + show_receiver + (1|dyad))` in R. The proposal's **M0 leave-one-out residual** stays as a *descriptive* reference, not as the inferential basis. |
| Data scope | **Finals + semi-finals**, jury and televote modelled separately. Finals-only becomes a sensitivity run. Adding semis lifts median obs/pair from 5 to 7 (J) and 8 (T). |
| Inference | Group-level questions (border, region, language): **QAP / MRQAP with Dekker double semi-partialling** (node-label permutation). Pair-level questions: shrunken estimates with 90% intervals, plus **local false sign rate (lfsr)** flags. No unshrunk "top pairs". |
| RQ2 | Odd/even-year split-half reliability (noise ceiling) against early/late correlation (drift). Add year-to-year rank correlation, leave-one-year-out predictive gain, and a 2026 out-of-sample check. |
| RQ3 | Compare jury and televote on the **points scale**, not on raw logits: televote utilities are about 1.75× more spread out than jury utilities. Add a QAP correlation of the J and T affinity matrices. |
| Network | Use the signed shrunken affinity matrix. Leiden runs on the positive part with a resolution sweep and multi-seed consensus. Communities are checked against a ballot-simulation null; the pilot gives modularity 0.35 against a null of 0.13–0.14. |

---

## 1. Data facts that drive the design (verified in the pilot)

- **Ballot structure.** Every jury and televote ballot in 2016–2026 gives exactly {12,10,8,…,1} to 10 distinct songs. The other eligible songs are listed explicitly with 0 points, and there are no self-votes. In all shows, total = jury + public. This was checked in `x_inspect_ballots.py`.
- **2023–2025 semi-finals contain only `total`.** That total is the **televote** (juries were removed from the semis in 2023). Code it as T. Juries returned to the semis in 2026, and the data has J and T there.
- **Tidy table:** `long.csv`, 30,860 rows (year, round, vtype, voter, receiver, points, place, qualified, flags, rank, n_eligible). The modelling set (2016–2025, no WLD, no substitute juries) has 1,308 ballots, 981 show×receiver quality parameters and 3,854 typed dyads.
- **Rule changes and anomalies**, each with a flag in the table and a sensitivity run:
  - **2018:** jury aggregation changed from a linear average of the five jurors' ranks to an "exponential" weighting. This changes the jury scale.
  - **2019:** the Belarus jury in the final was an EBU aggregated substitute, which was itself first computed wrongly. Excluded.
  - **2022:** the AZ, GE, ME, PL, RO and SM juries were replaced by aggregates in SF2 and the final. Excluded.
  - **2023:** juries were removed from the semis, and the rest-of-world online televote (`WLD`) was introduced. WLD is not a country, so it is excluded from dyads and can be analysed separately.
  - **2024:** NL was disqualified as a performer but still voted.
  - **2026:** juries returned to the semis, juries were enlarged, the televote cap was halved, and five countries were absent (ES, IE, NL, SI, IS). This makes 2026 a different regime: use it as a hold-out, not as training data.
  - **San Marino:** per the data audit (`03`), San Marino's televote is a substitute or aggregate every year. **Exclude SM-T from the primary analysis.** The pilot below still includes SM-T, which is a known small deviation. SM is 1 of 45 voters, so the effect on group-level results should be negligible, but SM→IT-type pairs must not be reported.

---

## 2. RQ1 — estimand and model hierarchy

### 2.1 Critique of the proposal's baseline (M0)

`r_vjt = p_vjt − mean_{u≠v} p_ujt`, averaged over years.

1. **Wrong measurement scale.** Points are bounded, 76–79% zeros, ordinal and non-linear (12 vs 10 is not 2 vs 0). A residual of +5 for a top song (near the 12 ceiling) does not mean the same as +5 for a weak song.
2. **No shrinkage, so a winner's curse.** Pairs observed 2–3 times dominate the extremes. In the pilot, **20% of M0's top-50 pairs have n ≤ 4**, against 0% for M2. M0's top-15 includes BA→RS (n=2), RU→BY (n=2) and BY→RU (n=3), which M2 ranks 125th, 128th and 121st.
3. **Bloc contamination.** The leave-one-out mean for RS→ME still contains the votes of HR, BA, MK and SI. *Empirically this is small:* bloc means barely differ between M0 and an unshrunk two-way fixed-effects fit (ex-YU 4.93 vs 4.79; ex-USSR 1.56 vs 1.51; Nordic 2.52 vs 2.43). The LOO rescaling n/(n−1) roughly offsets it. So contamination is a minor issue. The scale and shrinkage problems are the major ones.
4. **No uncertainty and no handling of unequal n.** "8+ count" is a cruder version of the same thing. Spearman with M2 is only 0.52.

### 2.2 Model hierarchy

Notation: *v* is the voter, *j* the receiver, *s* a show (year × round), and τ ∈ {J, T} the vote type. *E_vs* is the set of receivers eligible on ballot (v, s, τ).

**(a) M0 (descriptive reference):** the proposal's LOO residual, kept as a descriptive heatmap layer only. A rank or percentile variant (residual of the ballot rank instead of points) fixes the scale but not shrinkage.

**(b) M1 (robustness model, linear crossed effects with empirical-Bayes shrinkage).**

```
p_vjsτ = q_jsτ + b_vjτ + ε,   b_vjτ ~ N(0, σ²_bτ),  ε ~ (0, σ²_ετ)
```

- `q_jsτ` is a fixed effect for receiver × show × type. It absorbs song quality, running order and staging.
- Given λ_τ = σ²_ε/σ²_b, the estimate is the ridge solution. Alternate `q = mean(p − b)` and `b = Σ(p − q)/(n + λ)` until converged (about 300 iterations, < 0.1 s).
- **Choosing λ by empirical Bayes:** σ²_b = Cov over dyads of the mean residuals in odd years vs even years (independent halves). σ²_ε = residual variance − σ²_b.
- Pilot values: **λ_J = 6.3 and λ_T = 1.24.** Televote dyad variance is large relative to noise.
- R equivalent: `lmer(points ~ 0 + factor(show_rec) + (1|dyad), subset=type=="T")`.

**(c) M2 (primary, top-10 rank-ordered logit / Plackett–Luce with crossed effects).**

```
η_vjsτ = q_jsτ + b_vjτ
P(ballot) = ∏_{k=1}^{10} exp(η_{v,(k)}) / Σ_{j ∈ E_vs \ {(1),…,(k−1)}} exp(η_vj)
b_vjτ ~ N(0, σ²_τ),   q has a vague N(0, 10⁴) prior for identification
```

- (k) is the song ranked k-th, worth 12, 10, 8, … points.
- **Identification:** the per-voter and per-receiver shifts are absorbed by the prior. So `b` is *double-centred*: affinity beyond the receiver's show quality and beyond the voter's average generosity.
- **Fit:** MAP with L-BFGS and an analytic gradient. σ²_τ comes from type-II maximum likelihood with a Laplace approximation (MacKay fixed point; EM gives the same answer).
- **Pilot values:** σ²_J = 0.39 and σ²_T = 2.32 on the logit scale. Leave-one-year-out CV prefers slightly stronger shrinkage (σ²_J ≈ 0.25, σ²_T ≈ 1.5), but the predictive log-likelihood differs by only about 1%. **Pre-specify EB** and report CV as a sensitivity.
- **Why this is primary:**
  - It is the likelihood of the actual data-generating object, a top-10 ranking from a varying eligible set.
  - No zero-inflation or ceiling artefacts.
  - Partial pooling handles unequal n.
  - Its parameters give expected points by simulation.
  - It is the natural ranking analogue of Blangiardo & Baio (2014)-style hierarchical models.
- **Uncertainty:**
  - Laplace diagonal posterior SD, which is instant.
  - Parametric bootstrap, the gold standard: simulate ballots from (q̂, b̂), refit, B = 200, about 7 min.
- **Points-scale translation** (`points_uplift` in `analysis_real.py`):

```
Δ_vjτ = mean over v's ballots containing j of [ E(points | q̂, b̂) − E(points | q̂, b̂ with b_vj = 0) ]
```

  computed by Monte Carlo with Gumbel noise. In a typical final, b = 0.5 / 1 / 2 / 3 logits ≈ +0.7 / +1.5 / +3.2 / +5.0 points; see the simulation section for the exact table.
- **Combined RQ1 effect:** `b_vj = (b_vjJ + b_vjT)/2`, or better the average of the two Δ's.

**(d) M3 (stretch, full Bayesian).**

- Same likelihood in Stan or PyMC (rank-ordered logit is a 20-line Stan model).
- Bivariate prior `(b_J, b_T) ~ N(0, Σ)` to borrow strength across vote types and give the J–T correlation directly.
- Optionally covariates in the prior mean, `b ~ N(x'β, σ²)`, and a heavy-tailed (Student-t or horseshoe) dyad prior.
- Gives posterior rank intervals directly.

**Further sensitivity and stretch models:**

- A year × type **scale (noise) parameter**. Pilot: within-final SD of jury quality varies from 0.97 (2016, 2018) to 2.28 (2017), so a constant logit effect does not mean constant points.
- Using the EBU's **full jury and televote rankings (ranks 11–26)** if they can be scraped. This is a large information gain, but it is not in the GD dataset.

### 2.3 Recommended primary and robustness pair

**Primary: M2. Robustness: M1. Descriptive: M0.** The three agree on the big picture (Spearman M0–M1 0.96, M1–M2 0.93, M0–M2 0.88), but disagree on the tail that students would publish: top-50 Jaccard M0–M2 is 0.43.

### 2.4 Pilot top pairs (M2, finals + semis 2016–2025, combined J+T)

| voter→receiver | n ballots | M0 | M2 b (sd) | b_J | b_T | ≈ extra pts/show | border |
|---|---|---|---|---|---|---|---|
| CY→GR | 21 | 9.14 | 4.88 (0.41) | 2.31 | 7.45 | 7.3 | 0 (language) |
| GR→CY | 23 | 8.05 | 4.25 (0.40) | 1.95 | 6.56 | 6.5 | 0 (language) |
| ME→RS | 13 | 8.47 | 3.66 (0.47) | 1.30 | 6.02 | 5.3 | 1 |
| HR→RS | 18 | 6.05 | 3.54 (0.33) | 1.18 | 5.90 | 5.3 | 1 |
| MK→AL | 12 | 7.19 | 3.53 (0.44) | 0.87 | 6.18 | 5.5 | 1 |
| RO→MD | 13 | 7.43 | 3.46 (0.46) | 1.62 | 5.30 | 5.3 | 1 |
| GE→AM | 16 | 5.67 | 3.34 (0.37) | 0.66 | 6.02 | 5.5 | 1 |
| RS→ME | 7 | 9.06 | 3.34 (0.50) | 1.03 | 5.65 | 5.2 | 1 |
| MK→RS | 16 | 7.14 | 3.32 (0.39) | 1.04 | 5.59 | 4.4 | 1 |
| LV→LT / LT→LV | 21 / 13 | 5.3 / 6.3 | 3.02 / 3.00 | | | 4.4 | 1 |

- 14 of the top 15 are contiguous or same-language pairs.
- FR→AM (n = 18, b = 2.94) is the clearest diaspora pair.
- Strongest negative pairs: AM→AZ (−2.05), AZ→AM (−1.81), GB→IT (−1.73), LT→GR (−1.71), RS→UA (−1.63).
- Files: `top15_M2.csv`, `top15_M0.csv`, `real_pair_estimates.csv`.

---

## 3. Sample size and selection (Q2)

Universe: 45 countries, 1,980 ordered pairs, WLD excluded. The data audit (`03`) gives the same numbers.

| Scope | pairs ≥1 obs | median obs (observed pairs) | IQR | % observed pairs ≥5 | % of universe ≥5 | % of universe never observed |
|---|---|---|---|---|---|---|
| Jury, final only | 1,853 | 5 | 3–7 | 52.9 | 49.5 | 6.4 |
| Televote, final only | 1,853 | 5 | 3–7 | 52.9 | 49.5 | 6.4 |
| Jury, final + semis | 1,924 | 7 | 5–9 | 77.9 | 75.7 | 2.8 |
| Jury, final + semis, no substitute juries | 1,924 | 7 | 5–9 | 76.9 | 74.7 | 2.8 |
| Televote, final + semis | 1,930 | 8 | 5–10 | 80.0 | 78.0 | 2.5 |
| J+T ballots, final only | 1,853 | 10 | 6–14 | 79.1 | 74.0 | 6.4 |
| J+T ballots, final + semis | 1,930 | 16 | 10–18 | 93.2 | 90.8 | 2.5 |
| Distinct years observed (any show) | 1,930 | 6 | 4–8 | 69.6 | 67.8 | 2.5 |

**Selection problems and how to handle them:**

1. **Receiver qualification.** 58.7% of semi entries qualify. MK reached only 1 final in 2016–25; BY, GE, LU, IE and RO reached 2. In a finals-only analysis, pairs towards weak receivers are almost unobserved, and the years observed are those where the song was good.
   - The model handles the *quality* part through `q_jsτ`, which is free per show.
   - Because the final ballot is conditionally independent of semi-final noise given (q, b), the final-ballot likelihood conditional on the finalist set stays valid. Including the semi likelihood makes the selection ignorable (MAR given observed data).
   - So: **include semis** and condition on each show's eligible set.
2. **Semi-final allocation.** Pots are drawn from voting history, which deliberately separates bloc partners. Allocation depends on *past* observed data, so it is ignorable for likelihood inference, but it makes n_vj correlated with b_vj. Report n alongside every estimate. Never rank by unshrunk means.
3. **Participation churn.** BA appears only in 2016, LU only from 2024, RU and BY until 2021 and 2019. Shrinkage handles small n honestly, so these pairs will rarely appear in top lists. State this explicitly in the report.
4. **77 pairs are observed only in semis.** These are invisible in finals-only analyses.

---

## 4. Inference that respects dyadic dependence

### 4.1 Group-level tests (RQ1 "do they share region or border")

- **Statistic:** `T = mean b̂(border pairs) − mean b̂(other pairs)` over observed dyads, using the M2 combined estimate.
- **QAP null:** permute the country labels of the covariate matrix (rows and columns together, 5,000 permutations) with `b̂` held fixed. This keeps the dependence among dyads that share a voter or receiver.
- **Multiple covariates (MRQAP, Dekker DSP):** border, same UN-M49 sub-region, shared language, ex-USSR, ex-Yugoslavia, Nordic, log distance. For each covariate, residualise it on the others, permute the residual matrix, and refit (1,000 permutations).
- **Ballot-level null (complement):** simulate ballots from the fitted quality-only model (b = 0), refit, and recompute T. This tests "any affinity structure". It is also the null used for the network modularity check.
- **Pilot results:**
  - Border: T = **1.05** logits (M2) and 2.20 points (M0), QAP p < 0.001. The QAP null SD (0.082) is **35% wider** than a naive dyad-shuffle null (0.061), so ignoring dependence overstates precision. Here the effect is large enough that both nulls reject.
  - Same M49 region: T = 0.67, QAP null SD 0.056 vs naive 0.037.
  - MRQAP on M2 b̂ (R² = 0.28):

| covariate | β (logit) | t | p (DSP) |
|---|---|---|---|
| border | 0.36 | 5.1 | 0.001 |
| same M49 region | 0.31 | 7.0 | 0.001 |
| shared language | 0.68 | 6.2 | 0.001 |
| ex-USSR | 0.60 | 8.0 | 0.001 |
| ex-Yugoslavia | 1.28 | 8.9 | 0.001 |
| Nordic | 0.94 | 6.0 | 0.001 |
| log distance | −0.07 | −3.0 | 0.010 |

  All p-values are at the floor of 1,000 permutations. Report "p < 0.001" and use 10,000 permutations in the final run.
- **Measurement error:** b̂ are shrunken estimates with unequal precision. As a sensitivity, use precision weights (1/sd²), or put the covariates in M2's prior mean (M3 stretch) with a node-bootstrap SE.

### 4.2 Pair-level statements and multiplicity

The proposal says "no significance claims for single pairs". I recommend relaxing this in a controlled way, because readers will read the top list as claims anyway.

- **Report** posterior mean ± 90% interval for every pair shown, with n.
- **Flag** a pair as "credibly favoured" if **lfsr < 0.05** (Stephens 2017). For a Gaussian posterior, lfsr = Φ(−|b̂|/sd). Report the expected number of false-sign flags, Σ lfsr over flagged pairs.
  - Pilot: 316 positive and 315 negative flags; expected false signs among the positive flags ≈ 2.6.
- **Alternative:** BH-FDR at 10% on one-sided p = 1 − Φ(b̂/sd), or on parametric-bootstrap p-values.
- **Do not** run per-pair t-tests on M0 residuals: the simulation shows raw p < 0.05 has a false-discovery proportion of 0.5–0.9.
- **Winner's curse and rank uncertainty:**
  - Show shrunken, not raw, estimates.
  - From the parametric bootstrap, report P(pair in top 20) and a 90% rank interval.
  - Caption top lists with "rank positions beyond about 10 are not distinguishable".

---

## 5. RQ2 — stability 2016–2025

**Metrics (pre-specified):**

1. **Split-half reliability.** Odd years (2017, 2019, 2021, 2023, 2025) vs even years (2016, 2018, 2022, 2024). Report the Pearson and Spearman correlation of dyad estimates across pairs observed in both halves, the Spearman–Brown corrected value, and the top-30 Jaccard. This is the **noise ceiling**.
2. **Drift contrast.** Early (2016–2019) vs late (2021–2025), using the same metric. If early/late correlation is clearly below odd/even, relationships changed. If they are similar, the year-to-year differences are mostly noise.
3. **ICC of dyad effects:** σ²_b / (σ²_b + σ²_ε/n̄) from M1. Equivalently, the reliability of the pair mean.
4. **Year-to-year rank correlation** of single-year affinity estimates (M2 fitted per year with the EB prior), plotted as a correlation-vs-lag curve.
5. **Leave-one-year-out predictive gain:** log-likelihood per ballot of the held-out year using b̂ from the other years, against b = 0, with q re-estimated on the held-out year. Positive and flat over years means stable affinities.
6. **"Appear/disappear", made robust to noise.**
   - Fit a rolling 3-contest window, or the time-varying stretch model below.
   - A pair **appears** if lfsr < 0.05 (positive) in a window after being non-flagged in all earlier windows, *and* the change Δb between windows has lfsr < 0.05.
   - Otherwise call it "within noise". This avoids reading threshold-crossing noise as change.
7. **Stretch, random-walk dyad model:** `b_vjτ,t = b_vjτ,t−1 + ω`, `ω ~ N(0, σ²_ω)`. Report σ²_ω, with the 2020 gap counted as one step. If σ²_ω ≈ 0, affinities are stable.

**Pilot results** (combined J+T, fixed EB variances):

| split | method | pairs | Pearson | Spearman | Spearman–Brown | top-30 Jaccard |
|---|---|---|---|---|---|---|
| odd/even (F+SF) | M0 | 1,814 | 0.568 | 0.411 | 0.724 | 0.33 |
| odd/even (F+SF) | M1 | 1,814 | 0.666 | 0.497 | 0.799 | 0.40 |
| odd/even (F+SF) | **M2** | 1,814 | **0.673** | **0.522** | **0.805** | **0.50** |
| early/late (F+SF) | M0 | 1,593 | 0.538 | 0.375 | 0.700 | 0.33 |
| early/late (F+SF) | M1 | 1,593 | 0.629 | 0.440 | 0.772 | 0.30 |
| early/late (F+SF) | M2 | 1,593 | 0.624 | 0.470 | 0.769 | 0.40 |
| odd/even (finals only) | M0 | 1,571 | 0.512 | 0.363 | 0.677 | 0.30 |
| odd/even (finals only) | M2 | 1,571 | 0.608 | 0.462 | 0.756 | 0.43 |

- **By vote type** (M2, odd/even): televote r = 0.70, **jury r = 0.21**. M0: T 0.70, J 0.28. Jury affinities are weakly reproducible. Most of the stable favouritism is in the televote.
- **Early vs late is only slightly below odd vs even** (0.62 vs 0.67 for M2). So affinities are largely stable, with modest drift. The early/late split also mixes in composition change: RU and BY left, and juries were removed from the semis in 2023.
- **LOYO predictive gain (M2):** +1.46 to +2.33 nats per ballot in every year (2016 2.12, 2017 1.58, 2018 2.33, 2019 1.91, 2021 1.46, 2022 1.46, 2023 2.03, 2024 1.87, 2025 1.89).
- **2026 out-of-sample** (affinities from 2016–25 only, 2026 quality re-fitted):
  - Televote: +2.17 nats per ballot; 12-point recipient correctly predicted in 57% of ballots, against 33% without affinities.
  - Jury: +0.10 nats per ballot; 20% vs 16%.
  - Correlation of the 2016–25 estimate with the 2026 LOO residual: M0 0.39, M1 0.41, M2 0.39. On this crude points-scale check the three are equivalent.

---

## 6. RQ3 — jury vs televote gap

**The scale trap.** On the Plackett–Luce scale, televote rankings are less noisy: they aggregate thousands of voters. The average within-show SD of quality is 2.62 for T against 1.50 for J. A raw logit gap `b_T − b_J` therefore overstates televote favouritism. In the pilot, the top-20 pairs all have b_T > b_J, with a mean logit gap of 4.4.

**Estimand:** for each pair and type, the expected-points uplift Δ_vjτ defined in 2.2(c). The gap is `G_vj = Δ_vjT − Δ_vjJ`, in points, on the same 0–12 scale for both types.

- **Uncertainty:** parametric bootstrap, re-simulating J and T ballots jointly.
- **Scale-free alternative:** standardise the effect by the show's quality spread, `b/sd(q_sτ)`.
- **Cheap version:** M1 dyad effects are already on the points scale. Pilot SD of dyad effects in points: **J 0.79, T 1.66**. Scale-free ratio sd(b)/sd(q): J 0.28, T 0.52 (M2) or 0.35, 0.64 (M1). Televote favouritism is still about 2× jury favouritism after putting both on the same footing.

**Matrix-level comparison:** the QAP correlation of the J and T affinity matrices is **r = 0.37, p < 0.001** (2,000 node permutations). Jury and televote favour the same pairs, but only moderately. Pairs with the largest logit gap: GE→AM, MK→AL, SI→RS, IE→LT, CY→GR, SI→HR, GB→LT, CH→AL, IT→RO, CH→RS. Most of these are diaspora-driven (`rq3_top_gaps.csv`).

**Rule changes for jury-scale comparability (pre-specified sensitivity):**

1. Split 2016–17 from 2018–25 because of the jury aggregation change. Fit the J effects with a period interaction.
2. Exclude the substitute juries (2019 BY, 2022 ×6). Already done in the primary analysis.
3. Exclude the SM televote.
4. Jury data in the semis exists only 2016–2022. Run a sensitivity restricted to finals, where both types exist every year.
5. Exclude WLD. It has a televote ballot but no jury, so it can never form a gap.
6. Keep 2026 (juries back in semis, 7-member panels, changed televote cap) out of training.

---

## 7. Network layer

1. **Build:** a directed, signed, weighted matrix W_vj = combined shrunken affinity (M2, or Δ in points), with the diagonal and unobserved cells set to zero. Plot positive and negative affinities as separate layers. Use the positive part W⁺ for modularity, PageRank and strength. Analyse the negative part separately: the "rivalry" layer, e.g. AM↔AZ.
2. **Backbone, replacing the "strongest links" cut:**
   - Primary rule: keep edges that are **credibly positive** (lfsr < 0.05) *and* have Δ ≥ 2 points.
   - Alternative: the disparity filter (Serrano et al. 2009) on W⁺ at α = 0.05.
   - Report how the edge count varies with α.
3. **Communities:**
   - Leiden (`leidenalg.RBConfigurationVertexPartition`, directed, weighted) with a resolution sweep γ ∈ {0.5, 0.75, 1, 1.25, 1.5} and 50 seeds per γ.
   - Stability: mean pairwise ARI across seeds, plus a consensus (co-assignment) matrix.
   - Stretch: a directed weighted **SBM** with MDL model selection in graph-tool, which needs conda.
   - **Validation:** compare modularity with the ballot-simulation null (simulate b = 0 ballots, refit M2, run Leiden). Compare partitions with M49 regions (NMI).
   - **Pilot:**

| γ | communities | modularity | seed ARI | NMI vs M49 |
|---|---|---|---|---|
| 0.5 | 2 | 0.257 | 0.37 | 0.42 |
| 0.75 | 3 | 0.345 | **0.96** | 0.43 |
| 1.0 | 4 | 0.348 | 0.62 | 0.57 |
| 1.25 | 5 | 0.344 | 0.88 | 0.58 |
| 1.5 | 8 | 0.314 | 0.78 | 0.64 |

   - Null modularity at γ = 1 (10 replicates): mean **0.134**, max 0.143. The community structure is real.
   - γ = 1 communities:
     - ex-YU + AL + CZ + HU
     - ex-USSR / Caucasus + Greece / Cyprus + Mediterranean (IT, MT, SM) + RO, MD, BG
     - Western (AT, BE, CH, DE, ES, FR, IL, LU, NL, PT)
     - Nordic + Baltic + GB / IE / AU + PL
   - Partitions are seed-unstable at γ = 1, so present γ = 0.75 or the consensus partition.
4. **Centrality, with interpretation:**
   - In-strength of W⁺: "receives favouritism beyond song quality". Pilot top: RS 21.7, AM 18.1, LT 17.5, GR 16.8, AL 16.7, UA 15.7.
   - Out-strength: "gives favouritism". Pilot top: ME 18.3, MK 17.2, FR 16.7, AM 15.8, DK 15.4, GB 15.1.
   - PageRank on W⁺: favoured by countries that are themselves favoured. Mention it, but do not over-interpret.
   - Betweenness on a weight-as-distance graph has no behavioural meaning here. Skip it.
   - Reciprocity, which the proposal asks for: the weighted reciprocity of W⁺ and the correlation r(b_vj, b_jv) across unordered pairs, tested with QAP (transpose-preserving node permutations).

---

## 8. Covariates and confounders (kept descriptive)

| Covariate | Source | Priority |
|---|---|---|
| Land contiguity | CEPII GeoDist `contig`; pilot hand-coded in `covariates.py` | high (RQ1) |
| Capital distance (log) | CEPII GeoDist | high |
| Shared official or ethnologue language | CEPII `comlang_off` / `comlang_ethno` | high |
| Diaspora: migrant stock of j-born people living in v, as a share of v's population | UN DESA International Migrant Stock 2020/2024 | high for the **televote** (RQ3) |
| Shared history: ex-USSR, ex-YU, ex-Czechoslovakia; Nordic | hand-coded | medium |
| Same UN M49 sub-region (reproducible "region") | UN M49 | primary region definition. Bloc lists from the literature (Gatherer 2006; Fenn et al. 2006) are a sensitivity only, because they are partly derived from voting itself, which is circular |

**How to include them:** MRQAP on b̂ (MVP), or covariates in M2's prior mean (stretch). Interpret as "the share of favouritism *aligned with* geography, language or diaspora". No causal claims. Diaspora is the main candidate explanation for televote–jury gaps.

---

## 9. Pre-specified robustness and sensitivity analyses

| # | Variation | Purpose |
|---|---|---|
| S1 | M1 (points scale) and M0 instead of M2 | model dependence of top lists and group tests |
| S2 | Finals only | selection and semi-final pooling assumption |
| S3 | Exclude substitute juries (default) / also exclude SM televote / include both | data anomalies |
| S4 | Split jury 2016–17 vs 2018–25 | 2018 aggregation change |
| S5 | Exclude 2023–25 semis (televote-only shows) | constant design for RQ3 |
| S6 | Include WLD as a voter (televote only) | rest-of-world |
| S7 | Leave-one-year-out (9 refits): rank stability of the top 20 and of the border effect | single-year leverage, e.g. 2022 without Russia |
| S8 | Shrinkage strength: EB vs LOYO-CV (σ²_J ≈ 0.25, σ²_T ≈ 1.5) vs ×2 / ×½ | prior sensitivity |
| S9 | Top-list size k ∈ {10, 20, 50}; backbone α ∈ {0.01, 0.05, 0.1}; Leiden γ sweep | arbitrary thresholds |
| S10 | Proposal's "8+ count" and reciprocity | comparability with the original plan |
| S11 | Region definition: M49 vs literature blocs vs border-only | definitional |
| S12 | Year × type scale (noise) parameter in M2 | heteroskedastic juries |

---

## 10. Validation and sanity checks

1. **Data:**
   - Reconstruct the official totals for every show. The audit (`03`) did this.
   - Every ballot is {12, 10, 8, …, 1} with no self-votes. Verified.
   - total = J + T. Verified.
2. **Planted-bias recovery** (Section 11): run it on the final pipeline, not only this pilot.
3. **Known patterns that must replicate:**
   - GR↔CY, ex-YU mutual support, RO→MD, Nordic and Baltic clusters, AM↔AZ negative.
   - Diaspora televote pairs such as FR→AM, IT→RO, CH→AL.
   - All of these appear in the pilot output.
4. **Out-of-sample:** 2026 hold-out log-likelihood and top-1 hit rate, with jury and televote separately (Section 5).
5. **Calibration:** coverage of the 90% intervals in the simulation, and an lfsr false-sign rate below 5%.
6. **Reproducibility:** re-run from the raw JSON with one command. Fix seeds. Record package versions.

---

## 11. Planted-bias recovery simulation (pilot)

**Design (`sim.py`):**

- **Real design:** real voters, real eligible sets and real qualification outcomes, 2016–2025, finals + semis, with no WLD and no substitute juries.
- **Quality:** q̂ from the M2 fit on the real data.
- **Ballots:** top-10 orderings from η = q̂ + b_true with Gumbel noise (Plackett–Luce). One scenario uses Gaussian (Thurstone) noise to check misspecification.
- **Planting:** each replicate plants δ on K = 40 random ordered pairs, both vote types, out of 1,930 observed pairs.
- **Scenarios:**
  - **Sparse:** no other bias.
  - **Realistic background:** all dyads get b ~ N(0, σ̂²_τ), with σ̂²_J = 0.39 and σ̂²_T = 2.32, plus the planted δ.
  - **RQ3:** δ = 2 planted in the televote only.
- **Analysis:** each simulated data set is analysed finals-only and finals + semis, with M0, M1 and M2. The EB variance is re-estimated each replicate.
- **Replicates:** 30 per scenario (180 jobs, 581 s on 4 cores). Results: `sim_summary.csv`, `sim_se.csv`, `sim_raw.csv`. The Monte-Carlo SE of the means is about 0.01–0.03.
- **Metrics:**
  - AUC of planted vs other pairs.
  - Recall@40: share of planted pairs in the method's top 40.
  - Spearman correlation with the true combined b.
  - Overlap of the estimated top-20 with the true top-20.
  - For inference: power and false-discovery or false-sign proportion of M2 lfsr < 0.05 and of a naive per-pair t-test on M0 residuals (raw p < 0.05, and BH 10%).
  - 90% interval coverage.

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


---

## 12. Minimum viable vs stretch (two students, deadline late January)

| Block | Minimum viable (must deliver) | Stretch |
|---|---|---|
| Data | `long.csv` built from GD-fork JSON; flags; finals + semis; J/T split; WLD, substitute-jury and SM-T exclusions | scrape EBU full rankings (ranks 11–26) |
| RQ1 | M2 (supplied code: `esc_models.py`, about 200 lines) + M1 + M0 heatmap; top-20 with intervals, n and lfsr; border/region/language MRQAP | Bayesian M3 in Stan/PyMC with bivariate J/T prior and covariates in the prior |
| Uncertainty | Laplace SDs; lfsr flags | parametric bootstrap (B = 200) for rank intervals, P(top-20) and Δ-points intervals |
| RQ2 | odd/even vs early/late reliability; LOYO predictive gain; rolling 3-contest windows with lfsr-based appear/disappear | random-walk dyad model; 2026 hold-out |
| RQ3 | Δ-points gap per pair (or M1 points-scale gap) + QAP correlation J vs T; 2018-split sensitivity | diaspora covariate (UN DESA) explaining T − J gaps |
| Network | W⁺ from M2; lfsr backbone; Leiden γ sweep + seed ARI; null modularity (10 simulated nulls); in/out strength | disparity filter; consensus clustering; directed SBM (graph-tool) |
| Robustness | S1, S2, S3, S7, S8 | the rest of Section 9 |
| Validation | planted-bias recovery on the final pipeline (R = 30); known-pattern check | Thurstone misspecification; coverage study |

**Suggested schedule change:**

- **Nov 17–30:** M0 + M1 + M2 working on `long.csv`.
- **Dec 1–14:** RQ1 and RQ2 tables, simulation check.
- **Dec 18–Jan 6:** network + MRQAP + RQ3 Δ-points.
- **January:** robustness and write-up.

The modelling is not the bottleneck: M2 fits in about 2 s.

---

## 13. Caveats of this pilot

- The pilot keeps the SM televote, which the audit (`03`) says is synthetic. The final run must drop it.
- Border, language and capital data are hand-coded (`covariates.py`). They must be replaced by CEPII GeoDist.
- Laplace SDs ignore uncertainty in q and posterior correlations. The parametric bootstrap is the check.
- The simulation keeps the real finalist sets fixed. It does not re-simulate qualification.
- EB iterations were capped at 12 in the simulation for runtime, which slightly under-estimates σ² when the background is dense (see the realistic rows).
- The QAP and MRQAP use b̂ as if measured without error.

**References (methods):**

- Plackett (1975); Luce (1959).
- Blangiardo & Baio (2014), *J. Applied Statistics* (Bayesian ESC voting).
- Krackhardt (1988) QAP; Dekker, Krackhardt & Snijders (2007) MRQAP-DSP.
- Stephens (2017) lfsr / ashr.
- Traag, Waltman & van Eck (2019) Leiden.
- Serrano, Boguñá & Vespignani (2009) disparity filter.
- Peixoto (2014) SBM / MDL.
- Gatherer (2006); Fenn et al. (2006) on ESC blocs.
- Spierdijk & Vellekoop (2009) on geography and culture in ESC voting.
- Ginsburgh & Noury (2008) on cultural voting.
- Rule changes: EBU / eurovisionworld (2018 jury aggregation change; 2019 Belarus jury replaced; 2022 six juries replaced; 2026 juries return to the semis).
