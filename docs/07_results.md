# 07 · Results (first full run of the v2.1 pipeline)

*Produced by `make results` (`esc-bias analyze && esc-bias figures`) on the GD-fork data (commit `1f39f6b`), following `04_study_design_v2.md` v2.1 as written on 2026-11-18. The run takes about 8.5 min on 4 cores. All numbers below are read from `reports/results/` (`summary.json` and the CSVs), and figures are in `reports/figures/`.*

**Status:** this is a first, unreviewed run. Before quoting any number, rerun `make results` from a clean clone and check it (definition of done in `04 §12`). Every deviation from the spec is logged in `summary.json → deviations` and listed in §7. **Tag this commit as the freeze (`v0.2-prereg`) before changing any analysis choice.** Anything changed after that is exploratory (`04 §13`).

**Reading guide.** "Affinity" means *total* affinity a = x'β + b. It is measured relative to the voter's own average and the receiver's average (`04 §3`). Δ is the expected excess points on a fixed reference ballot, a 26-song final with the receiver at median quality. Intervals are 90% parametric-bootstrap intervals (B = 200). lfsr is the local false sign rate.

**Sample.** 591 jury and 698 televote ballots from country voters. That covers 1,924 jury and 1,886 televote ordered pairs among 45 countries, finals and semi-finals 2016–2025, with the anomaly-register exclusions applied.

---

## 1. Headline findings

1. **Affinity is real, structured, and much larger in the televote than in the jury.**
   - The pair-affinity variance is 0.27 for the jury and 1.46 for the televote, both on the logit scale with covariates in the model.
   - In excess points on the reference ballot, Greece→Cyprus is +4.1 for the jury and +10.4 for the televote. The Nordic within-bloc mean is +1.8 for the jury and +5.6 for the televote.
   - This replicates H2.
2. **Shared history explains more than borders do.** The joint geography/culture block test gives p = 0.005 for both vote types.
   - The ex-Yugoslav effect is the largest for both, about +1.1 excess points for the jury and about +9.8 for the televote. The televote figure is near the 12-point ceiling (see §6).
   - Nordic and ex-USSR follow.
   - **Once these are in the model, a land border adds nothing for juries** (−0.02 points, p = 0.91) and little for the televote (+0.38, p = 0.085).
   - H1 is therefore only *partly* supported: "neighbours" stand in for shared history and language.
3. **Pair affinities are very reproducible in the televote and moderately so in the jury, with small but detectable drift.**
   - Odd vs even years: Pearson r = 0.86 for the televote and 0.49 for the jury (H3 replicated).
   - Early (2016–19) vs late (2021–25) is slightly lower. The ceiling-minus-drift gap has a CI that excludes 0 for the televote, [0.030, 0.063]. For the jury it does not ([−0.009, 0.072]), except in the finals-only contrast.
4. **Jury and televote favour the same pairs more than raw numbers suggest.** The QAP correlation of the two affinity matrices is r = 0.62 (p < 0.001), and 0.80 after correcting for the jury's lower reliability (H4).
5. **Four communities, well beyond both null models**, matching the bloc literature (§5).

---

## 2. RQ1: which pairs, and what aligns with affinity

**Top pairs** (combined Δ, pairs with ≥5 ballots only; Figure F3 `fig03_top_pairs_forest.png`):

| Pair | n | Δ (points) | 90% interval |
|---|---|---|---|
| RS→ME | 7 | 8.05 | 7.13–8.89 |
| ME→RS | 13 | 7.83 | 6.89–8.79 |
| CY→GR | 21 | 7.70 | 6.85–8.50 |
| RS→MK | 8 | 7.61 | 6.67–8.43 |
| HR→RS | 18 | 7.43 | 6.43–8.41 |
| ME→AL | 8 | 7.40 | 6.52–8.35 |
| RO→MD | 13 | 7.31 | 6.18–8.24 |
| MK→RS | 16 | 7.27 | 6.28–8.34 |
| GR→CY | 23 | 7.26 | 6.44–7.93 |
| LV→LT | 21 | 7.20 | 6.41–8.05 |

- The intervals of the top ~20 pairs overlap heavily, so **rank positions within the top band are not distinguishable**.
- 606 combined pairs have lfsr < 0.05, with about 6.3 expected false signs among them.
- Pairs with n < 5 are excluded from ranked lists (e.g., BA→RS, n = 2). Their high Δ comes mostly from the ex-Yugoslav covariate, not from their own votes.

**What aligns with affinity** (in-likelihood β in excess points, 90% interval, permutation p from 200 refits; F6 `fig06_covariate_effects.png`):

| Covariate | Jury Δ | p | Televote Δ | p |
|---|---|---|---|---|
| ex-Yugoslavia | +1.05 (0.36, 1.89) | 0.015 | +9.81 (8.91, 10.45)* | 0.005 |
| Nordic | +0.96 (0.41, 1.63) | 0.055 | +2.42 (1.43, 3.65) | 0.010 |
| ex-USSR | +0.49 (0.17, 0.85) | 0.040 | +0.72 (0.35, 1.21) | 0.055 |
| shared language | +0.15 (−0.04, 0.34) | 0.249 | +0.46 (0.27, 0.69) | 0.005 |
| same UN-M49 region | +0.21 (0.05, 0.36) | 0.065 | +0.33 (0.17, 0.51) | 0.015 |
| land border | −0.02 (−0.22, 0.23) | 0.905 | +0.38 (0.13, 0.71) | 0.085 |
| maritime border | −0.26 (−0.54, 0.05) | 0.318 | +0.43 (0.03, 0.99) | 0.234 |
| log distance (per unit) | −0.42 | 0.005 | −0.44 | 0.005 |

\* Near the 12-point ceiling of the reference ballot, so it is better read as "ex-Yugoslav televotes almost always put each other at the top" than as a precise size.

- The p-values have a floor of 0.005, because there were 200 refits.
- The covariates are collinear (VIFs in `rq1_vif.csv`), so read the block test as primary and individual coefficients as indicative.
- The MRQAP cross-check on b̂ is in `rq1_mrqap.csv`.

---

## 3. RQ2: stability (F4 `fig04_stability.png`)

| Vote type | Split | Pearson | Spearman | Pairs | Ceiling − drift, 95% CI |
|---|---|---|---|---|---|
| jury | odd/even (ceiling) | 0.49 | 0.42 | 1,521 | — |
| jury | early/late | 0.46 | 0.40 | 1,521 | −0.009 to 0.072 |
| jury | early/late, finals only | 0.67 | 0.64 | 1,365 | 0.022 to 0.092 |
| televote | odd/even (ceiling) | 0.86 | 0.72 | 1,535 | — |
| televote | early/late | 0.81 | 0.67 | 1,535 | 0.030 to 0.063 |
| televote | early/late, finals only | 0.84 | 0.71 | 1,357 | 0.021 to 0.053 |

- **Reading:** the pattern of who-favours-whom is largely stable across the era. There is a small, statistically detectable shift in the televote. The early/late split also coincides with format changes (televote-only semis from 2023) and participation changes (RU and BY left), so the drift is not attributed to changing relationships alone.
- **Per-pair change:** the minimum detectable change is about **4.3 excess points**. Only 94 pairs have an early-vs-late interval that excludes 0, *fewer* than the 156 expected by chance at 10%. So **no individual pair can be said to have "appeared" or "disappeared"**. The visible changes in F7 are descriptive.

---

## 4. RQ3: jury vs televote (F5 `fig05_jury_vs_televote.png`)

- **Matrix level:** r = 0.62 (QAP p < 0.001); reliability-corrected r = 0.80 (reliabilities 0.66 for jury, 0.92 for televote). The M1 points-scale cross-check gives a lower raw r = 0.39.
- **Pair level** (pairs with ≥5 jury and ≥5 televote ballots):
  - The median gap Δ_T − Δ_J is +0.18 points, and 59% of gaps are positive.
  - **Largest televote surpluses:** CH→RS, SI→RS, IE→LT, ME→SI, GB→LT, CH→AL, MK→HR, GE→AM, each about +9 points with intervals entirely above +7. Most involve voters with large diaspora communities from the receiving country (Swiss/Serbian, Irish/Lithuanian, UK/Lithuanian, Swiss/Albanian). That matches H5, but **diaspora has not been tested yet** (UN DESA data still to be merged).
  - **Largest jury surpluses:** FI→SE (−3.9; jury Δ +5.0 vs televote +1.0), GR→MD, AM→MD, ME→AM.

---

## 5. Network (F7 `fig07_dynamic_backbone.png`, F1 `fig01_affinity_heatmap.png`)

- **Communities** (Leiden on the positive combined Δ, γ = 1.0 pre-fixed, consensus over 50 seeds, mean seed ARI 0.83):
  1. **Balkan/Mediterranean:** AL BA BG CY GR HR HU IT ME MK MT RS SI SM
  2. **Nordic/Baltic/Anglo:** AU DK EE FI GB IE IS LT LV NO PL SE
  3. **Western:** AT BE CH DE ES FR IL LU NL PT
  4. **ex-USSR/Caucasus + RO/MD/CZ:** AM AZ BY CZ GE MD RO RU UA
- **Against the nulls:** modularity is 0.321. The iid-affinity null gives 0.149 ± 0.010 (max 0.175, p = 0.048, the floor for 20 replicates). The strength-preserving null gives 0.148 ± 0.008 (p = 0.0099). So the **clustering** is beyond both the amount of affinity and the degree sequence.
- **Fit to geography:** NMI with UN-M49 sub-regions is 0.65 (permutation p < 0.001).
- **Backbone:** 209 credible edges (lfsr < 0.05 and Δ ≥ 2).
- **Face validity:** all pre-registered patterns are recovered (`face_validity.csv`). GR↔CY, ex-YU pairs, RO→MD and LV↔LT are strongly positive. AM↔AZ is below average (−0.7 to −0.8 points, interval excluding 0).

---

## 6. Robustness (must-do sensitivities, `sensitivity.csv`)

| Run | Jury | Televote | Verdict |
|---|---|---|---|
| S1 M1 vs M2 (Spearman of pair estimates / top-20 overlap) | 0.75 / 0.60 | 0.79 / 0.45 | ordering agrees broadly; the top-20 list is model-dependent |
| S1 M0 vs M2 | 0.74 / 0.40 | 0.78 / 0.60 | as above |
| S2 finals only | 0.89 / 0.50 | 0.93 / 0.80 | robust; border β unchanged in sign |
| S3a include excluded ballots | 0.997 / 0.95 | 1.00 / 1.00 | exclusions do not drive results |
| S5 drop 2023–25 semis | (no jury there) | 0.985 / 1.00 | robust |
| S7 leave one year out (border β range; min top-20 overlap) | −0.04 to 0.04; 0.65 | 0.36 to 0.52; 0.90 | robust |
| S13 quality from non-bloc voters | 0.996 / 0.95 | 0.995 / 1.00 | bloc contamination of q is small |

By the reporting rule (`04 §9`), the headline findings in §1 are **robust**. The exact membership of a top-20 list is **not**, because it depends on the model (S1). Report top lists as "examples within a credible top band", not as rankings.

**Ceiling effect.** For the strongest televote pairs, Δ approaches the 12-point maximum of the reference ballot, and their intervals become very narrow (e.g. ME→RS televote 11.09–11.15). This is a property of the points scale, not extra certainty. Compare strong pairs on the logit scale (`b`, `b_lo`, `b_hi` in the dyad CSVs).

---

## 7. Deviations from the spec (from `summary.json`)

- Permutation refits: 200 per vote type (spec 1,000), with warm starts and σ² fixed at the EB value. p-values have a floor of 0.005.
- MRQAP / QAP / NMI: 2,000 permutations (config 10,000).
- iid-affinity network null: 20 replicates (p floor 0.048).
- Bootstrap mode "prior": b is redrawn from N(0, σ̂²), which gives 0.8–0.9 coverage in tests vs about 0.6 when simulating from b̂. β intervals are β̂ ± 1.645 bootstrap SD.
- RQ2 per-pair change and the per-period backbone use Laplace SEs (no bootstrap).
- S13 is implemented as quality from a fit without bloc cells, then one refit with σ² fixed.
- κ (year × type precision) is estimated on the Laplace marginal likelihood. Range: jury 0.59–1.61, televote 0.83–1.19.

To remove the first three before the final report, raise `n_perm` and the replicate counts in `config/config.yaml` and rerun. The expected runtime is about 30–40 min.

---

## 8. Not done yet

- **Diaspora (H5):** download UN DESA International Migrant Stock 2024, add the bilateral share to `covariates.py`, rerun.
- **CEPII GeoDist:** replace the curated distance and language data, recording checksums.
- **Televote-validity check:** read the EBU notes for televote substitutes besides SM (`04 §2`).
- **Validation simulation with bloc-structured and juror-aggregation data-generating models** (`04 §10`).
- **Interpretation and narrative** for the report. The numbers above are the evidence base, not the story.
