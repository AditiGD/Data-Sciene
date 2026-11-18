# 04 · Study design v2.1: analysis plan (pre-registration draft)

*This replaces §2 and §4–§7 of the one-page proposal. It brings together the plan review (`01`), the literature review and meta-analysis (`02`), the data audit (`03`) and the methods pilot (`04a`). **v2.1** applies the independent red-team review (`06`; finding IDs R1–R18 are cited inline). Every decision traces back to an issue ID from `01` (C = critical, M = major, m = minor).*

**Freeze rule (R2).** This document is frozen **before any model is ported into the package, by Nov 23**, as git tag `v0.2-prereg`. The main RQ1–RQ3 runs (Dec 1–14) therefore happen *after* the freeze. Any later change goes in the change log (§13) with a date and a reason, and analyses added after the freeze are labelled *exploratory*. Milestone 2 (Dec 15–17) reports progress against the frozen plan.

---

## 0. Summary of what changes

| | v1 (proposal) | v2.1 (this design) | Why |
|---|---|---|---|
| Data scope | Grand Finals 2016–2025 | **Finals + semi-finals** 2016–2025; finals-only as a must-do sensitivity | Pairs with ≥5 observations rise from 52% to 77–80%. This **reduces**, but does not remove, the receiver-qualification selection bias (C2, R11) |
| Bias measure | points − receiver's leave-one-out mean | **M2**: top-10 rank-ordered logit (Plackett–Luce) with show-specific song quality, a year × type scale term, and **shrunken, doubly-centred dyad affinity**, fitted separately for jury and televote. **M1** (linear, points scale) is co-primary for RQ3 and robustness elsewhere. **M0** = v1 baseline, kept for comparability with Charron (2013) | It respects the 12/10/8…1 ballot structure and handles unequal n. In the pilot simulation it correlates 0.83 with true affinity, against 0.70 for M0 (C1, M2) |
| Group questions (border, language, …) | "group-level permutation test" | **Covariates inside the M2 likelihood**, with permutation refits; MRQAP per vote type as a descriptive cross-check | These contrasts stay identified despite the double-centring, and they avoid comparing jury and televote estimates that are shrunk by different amounts (M1, R1, R3, R15) |
| Anomalies | "rules change" | **Anomaly register**: 30 rows covering 26 anomaly IDs; substitute juries, the 2016 Danish reversed juror, San Marino's synthetic televote and `WLD` are excluded from pair analysis | Some "votes" are not cast by the nominal voter (C3, R12) |
| Covariates | region/border | border (curated), UN-M49 region, shared language, shared history (ex-USSR, ex-YU, Nordic), log distance, **diaspora** (UN DESA migrant stock) | Disentangles geography from language, history and migration (C4) |
| Pair rankings | top-pair bar chart | shrunken Δ ± 90% **bootstrap** interval, n, **local false sign rate** (lfsr) flag, rank interval | Winner's curse: 20% of M0's top-50 pairs have n ≤ 4 (M2, R6) |
| RQ2 "stable" | undefined | split-half reliability vs early/late drift **on a common pair set**, with a bootstrap CI of the difference; per-pair change test with a minimum detectable change | Separates real change from noise (M3, R8) |
| RQ3 "gap" | raw jury − televote points | Δ_T − Δ_J at a **fixed reference ballot design**, with a joint bootstrap; M1 points-scale gap co-primary; reliability-corrected J–T correlation | The scales differ and shrinkage differs by type (M4, R3, R4) |
| Network | communities + centrality on the bias network | positive-part Leiden at a **pre-fixed** resolution with seed consensus; **two nulls** (iid-affinity and strength-preserving); centrality redefined for a centred estimand | Negative weights, resolution choice, and whether structure is clustered rather than merely present (M5, M6, R1, R7) |
| Engineering | rerun notebook in the last week | package + one-command pipeline + tests + CI from now | M7 |

---

## 1. Research questions and expectations

- **RQ1 (affinity).** For each ordered pair *v → j* and vote type τ ∈ {jury, televote}, how much more does *v* rank *j*'s songs than *j*'s show-specific quality predicts, **relative to v's average affinity and to j's average affinity across voters** (§3)? Report it in expected points. And how strongly do **border, region, shared language, shared history and diaspora** shift affinity?
- **RQ2 (stability).** How reproducible are affinities across 2016–2025 (split-half reliability against early/late drift), and which pairs show a change larger than the minimum detectable change?
- **RQ3 (jury vs televote).** For each pair, what is the televote–jury gap G_vj in expected points at a common reference design? How strongly do the jury and televote affinity matrices agree, after correcting for their different reliabilities? Does diaspora shift televote affinity more than jury affinity?

**Directional expectations, with their provenance stated honestly (R2, R13).**

| ID | Expectation | Source | Status |
|---|---|---|---|
| H1 | Border, shared-language and shared-history pairs have higher affinity | literature: 16 of 17 studies (`02 §4`) | **seen in pilot**: the border contrast is positive |
| H2 | Televote affinity is larger than jury affinity on a scale-free comparison | literature: 7 of 7 studies; Gustar 2023 neighbour preference **71% (T) vs 55% (J)** | **seen in pilot**: replication hypothesis |
| H3 | Dyad-level reliability is higher for televote than for jury | pilot only (no split-era dyad study exists) | **pilot-derived**: replication hypothesis |
| H4 | J and T affinity matrices are positively but only moderately correlated | pilot QAP r = 0.37. The song-level J–T r = 0.48 (`02 §5.2`) is a **different estimand**, about song quality, not pair affinity | **pilot-derived**: replication hypothesis |
| H5 | Diaspora shifts televote affinity more than jury affinity | literature: Charron 2013; Blangiardo & Baio 2014; Orgaz 2011 | **not yet tested** (diaspora data not yet merged) |

Only **H5** is a genuine prediction made before seeing the data. H1–H4 are replications of patterns already seen in the exploratory pilot (§10).

**Novel contribution** (`02 §6`): dyad-level, uncertainty-aware estimates of jury and televote affinity across the whole split era, their within-pair gap at a common design, and their reproducibility.

---

## 2. Data

| Item | Decision |
|---|---|
| Source | [Graph-Drawing-Contest/eurovision-dataset](https://github.com/Graph-Drawing-Contest/eurovision-dataset), commit **`1f39f6b`** (pinned in `config/config.yaml`; raw data not vendored). The optional 2026 check uses upstream [EurovisionAPI/dataset](https://github.com/EurovisionAPI/dataset) `e56411125d4b`, pinned separately |
| Window | 2016–2025; 2020 cancelled → **9 contests, 3 shows each** |
| Canonical table | `data/processed/votes.parquet` from `esc-bias build-data` (41,350 rows incl. `combined`; jury 13,158 + televote 14,957). The `pilot/` table is the same jury + televote cells (28,115) and is not used for results (R10) |
| Vote types | `jury`; `public` → televote. For the 2023–2025 semi-finals the only score, `total`, **is televote** |
| Voters | country voters only. `WLD` (rest of world, 2023+) is excluded from dyads (S6) |
| Excluded from pair analysis (`config/anomaly_register.csv`) | 2016 final DK jury (a reversed juror distorts the whole ballot under average-rank aggregation; R12); 2019 final BY jury (substitute); 2022 SF2 and final juries of AZ, GE, ME, PL, RO, SM (substitutes); SM televote in all years (synthetic); `WLD` |
| Missing ≠ 0 | absent countries (RU 2017, 2022+; UA 2019; BY 2021+; NL as 2024 receiver; …) are missing, never zero |
| Flags | `jury_method` (2016–17 average vs 2018+ exponential); 2024 NO juror controversy (S3b); `voter_performs_in_round` |
| Open check (R12) | the identical-ballot detector cannot find pooled *televote* substitutes. Before the freeze, read the EBU scrutineer notes for each year and add a `televote_validity` flag for any substituted televote besides SM |
| Integrity | 17 automated checks run in CI and on every build; all pass or pass with a documented exception on the GD fork (`03 §2`) |
| Covariates | curated contiguity (77 land + 16 maritime pairs, `audit/reference_tables/`; verify against COW contiguity v3.2); UN-M49 region; languages; history dummies. Manual downloads: CEPII GeoDist and UN DESA International Migrant Stock 2024. **Record file name, version, download date and SHA-256** in `data/raw/README.md` (R10) |

**Coverage under the primary filter** (country voters, exclusions applied; generated from `votes.parquet`, R14):

| Scope | Vote type | Pairs observed | Median obs | Pairs ≥5 obs |
|---|---|---|---|---|
| Finals only | jury | 1,849 | 5 | 953 (51.5%) |
| Finals only | televote | 1,811 | 5 | 953 (52.6%) |
| Finals + semis | jury | 1,924 | 7 | 1,479 (76.9%) |
| Finals + semis | televote | 1,886 | 8 | 1,506 (79.9%) |

---

## 3. Estimands and models (RQ1)

Notation: voter *v*, receiver *j*, show *s* (year × round), vote type τ, eligible set *E_vsτ*, dyad covariates *x_vj*.

**M2 (primary): top-10 rank-ordered logit with crossed effects** (reference code `pilot/esc_models.py`)

```
η_vjsτ = κ_yτ · (q_jsτ + x_vj'β_τ + b_vjτ)  q: song quality per receiver × show × type (fixed)
                                             κ_yτ: year × type precision (R17), geometric mean 1 per τ;
                                             it scales the whole utility, so b and β are in
                                             common units across years (κ on q alone is unidentified)
P(ballot_vsτ) = ∏_{k=1..10} exp(η_(k)) / Σ_{j ∈ E_vsτ \ ranked so far} exp(η_j)
b_vjτ ~ N(0, σ²_τ),  σ²_τ by empirical Bayes (type-II ML, run to convergence)
```

**What b means: it is doubly centred (R1).**

- The ranking likelihood is unchanged by adding a constant to all of a voter's utilities. The receiver × show quality q absorbs anything common to all of a receiver's voters.
- So *b_vj* is affinity **relative to v's average affinity and to j's average affinity across voters**. In the pilot, row and column sums of b̂ are about 0.
- Consequences:
  - "Voter generosity" does not exist in a ranked ballot.
  - Out-strength and in-strength of b measure the **spread** of a country's affinities, not how much favouritism it gives or receives (§7).
  - A negative b means "less than this voter's and this receiver's average", not hostility.
  - **Bloc contamination (C1) is reduced, not solved.** If all of a receiver's neighbours over-rank it, part of that support goes into q.
- What remains identified: **group contrasts** (β for border, language, …) and between-pair comparisons. These covariates vary within rows and columns, so they are estimable despite the centring, which is why they sit inside the likelihood (R3, R15).
- Sensitivity S13 re-estimates q from non-bloc voters only, to bound the contamination.

**Δ in points at a fixed reference design (R4).**

- Δ_vjτ = expected points to *j* from *v* with affinity b_vjτ, minus with 0, computed on a **canonical 26-song final** in which *j* has the median quality for τ.
- The same design is used for J and T, so Δ does not depend on the receiver's actual song strength, the field size, or the J/T ballot mix.
- Δ is computed **per bootstrap draw**, not at b̂ (no Jensen gap). Combined Δ = (Δ_J + Δ_T)/2 per draw.

**M1: linear crossed model on points** with empirical-Bayes ridge shrinkage.

- It is **co-primary for RQ3**: it matches or beats M2 on the gap in simulation (R5).
- It is robustness and descriptive elsewhere.
- Port with **per-type residual variance**. Choose λ by REML or by random ballot halves, **not** by the odd/even split used for RQ2 (R16).

**M0 (descriptive reference):** the v1 leave-one-out residual and its "8+" count, for comparability with Charron (2013). It is **never ranked on its own**.

**Evidence for M2, stated precisely (R5).** In the pilot simulation (`04a §11`, 30 replicates, real design), M2 with finals + semis gives Spearman 0.83 with the true affinities against 0.70 for M0, and top-20 overlap 0.46–0.59 against 0.30–0.50. Its lfsr flags have a false-sign rate of 1–2%. The limits of that evidence:

- **Weaker results:** Laplace 90% intervals covered only **0.83–0.84** in the realistic scenario. Under Thurstone noise, M1's top-20 overlap was slightly higher (0.56 vs 0.54).
- **How the simulation favours M2:** it generated data from M2 itself with independent pair effects and no bloc structure, and capped empirical Bayes at 12 iterations.
- **The fix:** the final validation (§10) adds bloc-structured and juror-aggregation data-generating models.

---

## 4. Inference

| Question | Procedure | Settings (`config/config.yaml`) |
|---|---|---|
| Do border, region, language, history or diaspora shift affinity? (H1, H5) | **β_τ inside M2**. Null distribution from **permutation refits** (permute country labels of x, refit M2). Report one **joint geography/culture block test**, plus individual β with VIFs, because the covariates are collinear on 45 nodes (R15) | 1,000 refits (about 2 s each); seed fixed |
| Cross-check | MRQAP (Dekker DSP) on b̂, **per vote type only** (no combined logit fit) | `n_permutations: 10000` |
| Is there any affinity at all? | ballot-simulation null with b = 0 | 200 replicates |
| Single pairs | Δ and b ± 90% interval from the **parametric bootstrap (B = 200, minimum viable; R6)**; n; **lfsr < 0.05** computed from the bootstrap draws (combined lfsr from combined-Δ draws); expected false-sign count Σ lfsr | No unshrunk top lists. Laplace SDs are only a quick check: they ignore q–b covariance and σ² uncertainty |
| Reciprocity | r(b_vj, b_jv) over unordered pairs vs a transpose-preserving QAP null | |

---

## 5. RQ2: stability (R8)

| Metric | Definition |
|---|---|
| Noise ceiling | odd-year vs even-year fits, Pearson and Spearman. The halves are unequal (5 vs 4 contests), so report the Spearman–Brown value as approximate only |
| Drift | 2016–2019 vs 2021–2025, same metrics, **on the same pair set as the noise ceiling** |
| Drift test | **bootstrap CI of (ceiling − drift)**. Drift is claimed only if the CI excludes 0 |
| Format control | the drift contrast is repeated **finals-only**, because 2023 removed juries from the semis and participation changed |
| Per-pair change | early-vs-late Δb with a bootstrap interval. A pair "appears" or "disappears" only if that interval excludes 0. Report the **minimum detectable change** at the median n (the pilot suggests about 2–3 contests per window per pair, so expect low power and say so). Rolling 3-contest windows are dropped |
| Predictive check | leave-one-year-out log-likelihood gain. This shows affinity is predictive, not that it is stable |
| Stretch | random-walk dyad model σ²_ω |

All metrics are reported separately for jury and televote (H3).

---

## 6. RQ3: jury vs televote

- **Gap estimand:** G_vj = Δ_vjT − Δ_vjJ at the reference design (§3). Intervals come from a **joint bootstrap** that carries both posteriors (R3, R4).
- **Co-primary:** the M1 points-scale gap.
- **Matrix agreement:** QAP correlation of the J and T affinity matrices, plus a **reliability-corrected** version: r / √(rel_J · rel_T), with reliabilities from §5 (R3). Pilot raw r = 0.37, but jury reliability is low, so the corrected value will be higher.
- **Differential shrinkage (R3).** Jury effects are shrunk much more (σ²_J ≪ σ²_T), so raw comparisons of b̂_J and b̂_T are biased toward the televote. Claims about "which channel is more biased" rest on **β_J vs β_T from the in-likelihood covariates** and on reference-design Δ, never on counting pairs with b̂_T > b̂_J.
- **Design asymmetries:**
  - Jury data in the semis exists only for 2016–2022 → **S5 is must-do**.
  - The 2018 jury aggregation change → handled by κ_yτ in the primary model, plus S4 (drop 2016–17).
  - `WLD` has no jury → excluded.
  - Receiver shocks such as Ukraine 2022 and Israel 2024 → with/without check.

---

## 7. Network layer

1. **Graph:** a directed signed matrix W_vj of combined Δ (points).
   - The positive part W⁺ is used for structure.
   - The negative part is reported as "below this voter's and receiver's average" (R1). It is **not** labelled as rivalry unless it is more negative than under an iid-affinity null.
2. **Backbone:** an edge is kept if it is credibly positive (bootstrap lfsr < 0.05) **and** Δ ≥ 2 points. Disparity filter as a sensitivity.
3. **Communities (R7):**
   - Leiden (RB configuration, directed, weighted) on W⁺ at a **pre-fixed γ = 1.0**, with a **consensus partition** over 50 seeds.
   - A γ sweep (0.5–1.5) is reported as a sensitivity only.
   - The pilot's choice of γ = 0.75 after seeing seed ARI is withdrawn.
   - **Null 1 (iid affinity):** draw b ~ N(0, σ̂²_τ) independently, simulate ballots, refit, run Leiden. This tests *clustering beyond the amount of affinity*.
   - **Null 2 (strength-preserving):** shuffle W⁺ edge weights while keeping each node's in- and out-strength. This tests structure beyond the degree sequence.
   - **NMI against UN-M49 regions** gets a permutation p-value (permute region labels).
   - The b = 0 ballot null only shows that affinity exists. It is kept as a floor, not as the test.
4. **Centrality (R1).** Because b is centred, in- and out-strength of W⁺ measure how **concentrated** a country's positive affinities are, not how much favouritism it gives or receives. Report them as "concentration of excess points", alongside the SD of each row and column of b. PageRank is reported but not interpreted. Betweenness is not used.
5. **Face validity:** Greece↔Cyprus, ex-Yugoslav, Nordic and Baltic clusters, Romania→Moldova, Armenia↔Azerbaijan below average (`02 §6`). Failing to recover them is a pipeline bug until proven otherwise.

---

## 8. Figures

The GD Contest 2026 brief asks for a dynamic, multivariate graph (R18).

| Figure | Encodes | Notes |
|---|---|---|
| **F7 Dynamic backbone** (lead figure) | per-period backbone (2016–19 / 2021–23 / 2024–25, or per contest), node colour = consensus community, edge width = Δ, J and T as toggles or small multiples | **stable node positions** across periods; layout = stress majorisation with a fixed-weight **geographic anchoring term** (capital coordinates), so geography is kept rather than relaxed away |
| F1 Seriated affinity heatmap (voter × receiver), J and T | Δ in points, diverging palette centred on 0 | ordered by consensus community; cells with n < 3 hatched; supporting figure |
| F3 Top pairs, forest plot | shrunken Δ ± 90% bootstrap interval, n, lfsr flag | replaces the v1 bar chart |
| F4 Stability | ceiling vs drift with bootstrap CI; per-pair early/late Δ for the top 20 | RQ2 |
| F5 Jury vs televote | dumbbell of Δ_J and Δ_T per pair at the reference design + scatter with raw and reliability-corrected r | RQ3 |
| F6 Covariate effects | in-likelihood β_J and β_T ± permutation intervals | RQ1, H5 |

Every figure carries n and its uncertainty, and is built by the pipeline (`reports/figures/`).

---

## 9. Pre-specified robustness and sensitivity analyses

**Must-do: S1, S2, S3, S5, S7, S13.**

| # | Variation |
|---|---|
| S1 | M1 and M0 instead of M2 |
| S2 | Finals only (selection, R11) |
| S3 | **One definition (R12).** Primary = the register's `exclude` rows dropped. **S3a**: include all excluded ballots (DK 2016, BY 2019, 2022 substitutes, SM televote). **S3b**: primary plus dropping the `sensitivity` rows (NO 2024 jury, NL 2024 voter, 2022 substitute-jury countries' televote) |
| S4 | Drop jury 2016–17 (aggregation change; replaces the unidentifiable period interaction, R17) |
| S5 | Drop the 2023–25 televote-only semis (constant design for RQ3) |
| S6 | Include `WLD` (televote only) |
| S7 | Leave one year out (9 refits) |
| S8 | Shrinkage: EB vs cross-validated vs ×2 / ×½ |
| S9 | Thresholds: top-k ∈ {10, 20, 50}; backbone α; Leiden γ sweep |
| S10 | v1 "8+ count" and reciprocity (continuity) |
| S11 | Region definition: M49 vs literature blocs vs border only |
| S12 | M2 **without** the κ_yτ scale term (was the other way round in v2) |
| S13 | Quality q re-estimated from non-bloc voters (bounds bloc contamination, R1) |
| S14 | Round interaction: separate b for semis and finals (tests the pooling assumption, R11) |

**Reporting rule:** a headline finding is "robust" only if it keeps its sign and stays within the S1, S2 and S7 interval envelope.

---

## 10. Validation, and what counts as confirmatory

1. **Data:** reconstruct all official totals and winners (automated; passes).
2. **Method (R5):** planted-bias recovery on the **final** pipeline with three data-generating models: (a) M2 with iid b; (b) **bloc-structured** b, where communities share a common component; (c) **juror-aggregation** noise, where 5 or 7 simulated jurors are averaged or exponentially weighted. Empirical Bayes runs to convergence. Report recall, Spearman, top-20 overlap, the lfsr false-sign rate and **90% coverage**. A small version runs in CI.
3. **Face validity:** §7.5.

**Confirmatory status.** The pilot already looked at 2016–2025 and at the 2026 hold-out, so no analysis on this data is blind. H1–H4 are labelled replications of pilot patterns (§1). H5 and all robustness outcomes are not yet seen. The freeze (before porting, R2) protects against *further* forking paths; it does not make the study confirmatory. Pilot numbers in `04a` are feasibility evidence and must not be quoted as findings. A truly out-of-sample test needs the 2027 contest (May 2027), after the deadline, and can be pre-registered as future work. **Disclose the AI-assisted pilot and design in the course AI-use statement** (R9).

---

## 11. Minimum viable vs stretch (cut to fit two students; R9)

The package's model, inference and network functions are still documented stubs. `pilot/esc_models.py` is a working reference to port, with tests. **Both students should be able to explain the Plackett–Luce likelihood, empirical-Bayes shrinkage and the bootstrap orally.** Budget a reading session for this in week 1.

| Block | Minimum viable (by Jan 27) | Stretch |
|---|---|---|
| Data | `votes.parquet` + register + CI checks; covariate table with checksums | televote-validity flags beyond SM; EBU full rankings |
| RQ1 | M2 with in-likelihood covariates and permutation refits; **parametric bootstrap**; F3; M0 reference | M3 Bayesian (bivariate J/T prior); diaspora |
| RQ2 | ceiling vs drift on a common pair set with bootstrap CI, **finals-only** version | per-pair change; random-walk model |
| RQ3 | reference-design G with joint bootstrap; M1 gap; reliability-corrected r | diaspora β_T vs β_J (H5) |
| Network | W⁺ backbone; Leiden γ = 1.0 consensus; iid-affinity null; F7 | strength-preserving null; SBM |
| Robustness | S1, S2, S3, S5, S7, S13 | S4, S6, S8–S12, S14 |
| Engineering | package, tests, CI, `make all` from raw data | interactive explorer |

---

## 12. Timeline v2.1 (from Nov 18)

| Period | Milestone | Owner | Definition of done |
|---|---|---|---|
| Nov 18–23 | Adopt scaffold; CI green; review the register and the televote-validity check; download CEPII and UN DESA files with checksums; methods reading session; **freeze this document (`v0.2-prereg`)** | Tannu (data), Aditi (covariates), both (freeze) | tag pushed; `make data validate` passes |
| Nov 24–30 | Port M2 (with κ, covariates and the bootstrap) and M1 from `pilot/` into `src/esc_bias/models.py` with unit tests and a CI-size planted-bias test | Aditi (M2), Tannu (M1, bootstrap) | tests pass; the simulation reproduces `04a` within tolerance |
| Dec 1–14 | RQ1 (β, Δ, F3), RQ2 (ceiling vs drift), RQ3 (G, r); validation DGPs (b), (c) | Tannu (RQ1/2), Aditi (RQ3, validation) | tables generated by `make all` |
| **Dec 15–17** | **Milestone 2**: progress report against the frozen plan | Both | change log up to date |
| Dec 18–Jan 6 | Network (consensus, iid null, F7); must-do sensitivities (automated, so they need no supervision over the holidays) | Aditi (network), Tannu (robustness) | sensitivity table; robustness rule applied |
| Jan 7–14 | Story draft; final figures; **peer critique** | Aditi lead | every claim has a figure or table with uncertainty |
| Jan 15–27 | Apply feedback; clean-clone rerun; AI-use statement | Both | fresh clone + `make all` reproduces every number |

---

## 13. Change log

| Date | Change | Reason | Exploratory? |
|---|---|---|---|
| 2026-11-18 | v2 → v2.1: findings R1–R18 applied (see `06`) | independent red-team review | no (pre-freeze) |
| 2026-11-18 | κ_yτ moved from multiplying q only to scaling the whole utility | κ·q alone is not identified when q is free per show | no (pre-freeze) |
| | | | |

---

## Appendix: decision trace

| Issue | Resolved by |
|---|---|
| C1 baseline contaminated / wrong scale | §3 (M2, κ, double-centring stated, S13) |
| C2 finals-only and selection | §2 scope; S2, S14 ("reduces", R11) |
| C3 rule changes and substitute votes | §2 exclusions; register; televote-validity check |
| C4 region/border only | §2 covariates; §4 in-likelihood β |
| M1 permutation test undefined | §4 permutation refits + MRQAP |
| M2 winner's curse | §4 bootstrap intervals, lfsr, rank intervals |
| M3 RQ2 undefined | §5 |
| M4 RQ3 scale | §3 reference-design Δ; §6 |
| M5 community-detection traps | §7.3 (pre-fixed γ, two nulls) |
| M6 arbitrary link threshold | §7.2 backbone |
| M7 reproducibility late | `05_engineering_standards.md`; §12 |
| M8 no freeze | freeze rule before porting; §10; §13 |
| m1–m9 | §2 (counts, `WLD`, codes, provenance), §4 (reciprocity), S10 (8+), §10 (2026), `05` (four-eyes review), §7–8 (neutral wording: "affinity", "excess points") |
| Red-team R1–R18 | `06_red_team_review.md` (response table) |
