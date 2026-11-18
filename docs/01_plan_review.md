# 01 · Review of the current plan (Project Proposal v1)

*Scope: the one-page `Project_Proposal.pdf` (Tannu Malik, Aditi Deshpande). This document is the "analyse the current plan" step. It (a) records what is already strong, (b) lists every issue found, ranked by severity, each with a concrete fix and a pointer to where the fix lives in the upgraded design, and (c) closes with a meta-review scorecard of the plan as a research design.*

Companion documents: [`02_literature_meta_analysis.md`](02_literature_meta_analysis.md) · [`03_data_audit.md`](03_data_audit.md) · [`04_study_design_v2.md`](04_study_design_v2.md) · [`05_engineering_standards.md`](05_engineering_standards.md) · [`06_red_team_review.md`](06_red_team_review.md)

---

## 1. One-paragraph verdict

The proposal asks a sharp, well-scoped question, picks the right time window (the split jury/televote era), is honest about its limits ("descriptive; no causal claims"), and already contains the single most important idea in this literature: **separate favouritism from song quality with a per-year popularity baseline.** What keeps it from being state of the art is not ambition but **measurement and inference**. The baseline it proposes is biased *against* finding bloc effects. The sample is throttled to the finals only, so each pair has at most 9 observations. Several 2016–2025 rule changes that make some votes non-comparable are not identified. The only covariate is region/border, which leaves out diaspora, the best-documented driver of televote bias. And "permutation test", "stable" and "gap" are named but not defined. All of these can be fixed inside the existing timeline and team. None of them requires changing the research questions.

---

## 2. Strengths to keep

| # | Strength | Why it matters |
|---|---|---|
| S1 | **Graph framing**: directed, weighted, dynamic network; countries = nodes, votes = edges | Matches the GD Contest 2026 brief ("dynamic and multivariate graph") and the network literature (Fenn et al. 2006; Dekker 2007; Mantzaris et al. 2018). |
| S2 | **Popularity baseline** to separate bias from song quality | It is the core identification idea. Most naive "who votes for whom" analyses lack it. |
| S3 | **2016–2025 window** with separate jury and televote | It is the only period where the two channels can be compared at the dyad level, which is the study's chance at novelty (RQ3). |
| S4 | **Descriptive framing; no single-pair significance claims** | Correct epistemic stance given ≤9 observations per pair. |
| S5 | **Group-level permutation test** for within-region vs other pairs | Right instinct: test hypotheses at the level where power exists. It needs to be specified (see M1). |
| S6 | **Validation against official results**; documenting every transformation | It is the start of a data contract. We make it automatic (see M7). |
| S7 | **Three RQs, risk table, weekly timeline, named owners** | It is already better organised than most student proposals. |

---

## 3. Issues, ranked by severity

Severity: **Critical** means it can invalidate a headline finding. **Major** means it weakens validity or credibility noticeably. **Minor** means a polish, clarity or robustness issue.

### Critical

**C1 · The leave-one-out-mean baseline is contaminated by the very bias it is meant to measure.**
*Plan:* "points given minus the receiver's average points from all other voters that year."
*Problem:* If a bloc (say, five neighbours) all over-vote receiver R, R's leave-one-out mean is inflated by the other four bloc members. So each bloc member's measured bias is **shrunk toward zero**. The more cohesive the bloc, the larger the underestimate, which biases RQ1 against its own hypothesis. Second, Eurovision ballots are **constrained rankings**: each voter gives exactly 12, 10, 8, 7…1 to ten distinct songs, 0 to the rest, and never to itself. Points are bounded, ordinal, non-linear (12 vs 10 is a different gap from 2 vs 1) and zero-inflated (about 60% zeros). A mean difference on that scale is a poor estimator, and its variance depends on the receiver's quality. Third, jury and televote prefer different songs, so **one combined baseline mixes two different quality signals.**
*Fix:* Estimate **song quality and dyad bias jointly**, per vote type: a crossed-effects model with receiver × year × vote-type quality and voter × receiver dyad effects with partial pooling. Add a **rank-aware robustness model** (rank-ordered logit / Plackett–Luce, or rank-percentile residuals). Keep the proposal's baseline as a transparent reference. → `04_study_design_v2.md §3`

**C2 · Finals-only data discards most of the available information and adds selection bias.**
*Plan:* Grand Final 2016–2025 → "each pair appears at most 9 times."
*Problem:* A pair is observed only in years when the receiver qualified. So for most pairs n ≪ 9, and **strong songs are over-represented**, because bias is only measured conditional on qualification. The semi-finals carry the **same jury/televote split** in 2016–2022 and televote in 2023–2025. They add a large number of extra dyad observations at no cost, because they are in the same dataset (`rounds/semifinal1.json`, `semifinal2.json`).
*Fix:* Primary analysis on **finals + semi-finals** with a round effect. Finals-only becomes a pre-specified sensitivity analysis. Report observations per pair explicitly (pilot numbers in `04 §2`).

**C3 · Rule changes and substitute votes are not identified, so some "votes" are not genuine dyadic preferences.**
*Plan:* "Comparability: rules and participants change (e.g. a country absent from 2022)."
*Problem:* The window contains votes that were **not cast by the nominal voter's own jury or public**. Examples: juries replaced by aggregated substitute results, juries dismissed, televotes replaced by jury results for small countries, the 2023 change to televote-only semi-finals, and the new "Rest of the World" (`WLD`) televote voter. Changes to how jury rankings are aggregated also alter the jury points scale across years. Treating these records as real voter → receiver preferences plants artificial "bias" or erases real bias for specific pairs.
*Fix:* Produce an **anomaly register** (year, round, vote type, voter, handling = keep / flag / exclude / sensitivity), generated from the audit, and a `is_substitute` flag in the tidy table. → `03_data_audit.md`, `04 §6`

**C4 · Region/border is the only covariate, so RQ1 and RQ3 cannot be interpreted.**
*Plan:* "Enrichment: a region/border label per country."
*Problem:* Geography is collinear with the mechanisms the literature actually separates: **diaspora / migrant stock** (the strongest documented driver of televote bias), **shared language**, and **shared political history** (ex-USSR, ex-Yugoslavia, Nordic). Without them, "neighbours favour each other" is uninformative, and the jury–televote gap (RQ3) has no explanatory handle, because diaspora acts on the public, not on juries.
*Fix:* A **dyad covariate table**: contiguity (curated, sourced), distance, common official/spoken language, historical bloc, and log bilateral migrant stock (UN DESA) where obtainable. Use it descriptively in MRQAP / dyad-level regressions of estimated bias, never causally. → `04 §5`, `03 §5`

### Major

**M1 · The "group-level permutation test" is not defined, and naive permutation ignores dyadic dependence.** Dyads that share a voter or a receiver are not independent. Shuffling pair labels under independence makes p-values too small. *Fix:* **QAP / MRQAP** (permute country labels of the covariate matrix, keeping the bias matrix's row and column structure). In addition, use a **ballot-constrained null**: simulate ballots from the fitted quality-only model, which preserves the 12/10/8…1 structure. Use fixed seeds and report the number of permutations. → `04 §4`

**M2 · "Top pairs" bar charts with ≤9 noisy observations will mostly show noise (winner's curse).** The pairs with the most extreme raw averages are disproportionately the ones with few observations. "No significance claims" is honest, but a ranked bar chart *is* an implicit claim. *Fix:* **Empirical-Bayes or hierarchical shrinkage** of dyad effects, intervals on every ranked estimate, rank uncertainty (e.g., the probability that a pair is in the top 20), and a minimum-observations rule. → `04 §3–4`, `06`

**M3 · RQ2 ("stable… or appear and disappear") has no operational definition.** With so few observations per year, most apparent appearing and disappearing is sampling noise. *Fix:* Measure **reliability first** (odd- vs even-year split-half correlation of dyad bias, ICC, year-to-year rank correlation). Then define *persistence* against a null, i.e., the expected flip rate if the true bias were constant. Optionally add a time-varying dyad effect. → `04 §5`

**M4 · RQ3 compares raw points, but juries and televoters have different song-quality baselines and scales.** A pair can show a large raw jury–televote gap simply because the jury and the public rated the *song* differently. That is quality, not bias. *Fix:* Define the estimand as the **difference between dyad-bias estimates** from the same model fitted per vote type, with uncertainty. Add a QAP correlation between the jury and televote bias matrices. Handle the 2023+ televote-only semi-finals explicitly, because that asymmetry is easy to miss. → `04 §6`

**M5 · Community detection on a "bias network" has unaddressed technical traps.** The bias network has **negative weights**, which most modularity and Leiden implementations cannot take. Modularity is positive even on random graphs. Results are sensitive to the resolution parameter and to the random seed. *Fix:* Use positive-part or signed variants, run a resolution sweep, build a consensus over many seeds, compare against a **null (configuration model or ballot-permutation)**, and optionally fit a weighted directed SBM for comparison. → `04 §7`

**M6 · "Show only the strongest links" is an arbitrary threshold.** *Fix:* Use statistically grounded **backbone extraction** (disparity filter, or edges whose shrunken bias interval excludes 0). Order the heatmap by community or hierarchical clustering (seriation). Use small multiples or a timeline for the dynamic aspect, and dumbbell or slope charts for RQ3. → `04 §8`

**M7 · Reproducibility is scheduled for the last week, and the workflow is notebook-first.** "Rerun notebook from raw data" in Jan 15–27 means problems surface when there is no time left to fix them. *Fix:* From day 1: a pinned environment, a `src/` package plus thin notebooks, a one-command pipeline (`make all`), data-validation tests, CI on every push, a pinned data commit hash, and fixed seeds. → `05_engineering_standards.md`

**M8 · The analysis plan is not frozen before results are seen (garden of forking paths).** Robustness checks and the permutation test are scheduled *after* the progress report. Baseline, thresholds (8+), community-detection settings and exclusion rules are all researcher degrees of freedom. *Fix:* Freeze `04_study_design_v2.md` as a lightweight **pre-registration** at Milestone 2 (Dec 15–17). Anything decided later is labelled exploratory. → `04 §10`

### Minor

| # | Issue | Fix |
|---|---|---|
| m1 | "About 25 finalists / roughly 40 voters": the data shows 26 finalists, and voters vary from 37 to 42 by year and vote type. From 2023 there are 38 televote voters (including `WLD`, which is not a country) and 37 juries. | State exact counts from the data and handle `WLD` explicitly (exclude from dyads; sensitivity). |
| m2 | The reciprocity metric is unspecified. | Use the correlation of the bias matrix B with Bᵀ, against a QAP null, plus a mutual-top-k count. |
| m3 | The "8+ points" threshold is arbitrary. | Use a rank-based "top-3 of ballot" equivalent with sensitivity at top-1 and top-5. |
| m4 | Data provenance: the source is an **unofficial** scraped dataset. The course version is the GD 2026 fork. | Pin the fork URL and commit hash, record the licence, and validate totals and winners against official results automatically. |
| m5 | 2026 results are already in the upstream dataset. | Optionally use 2026 as an **out-of-sample check**: do 2016–2025 dyad biases predict 2026 points beyond quality? Use it only if the course allows. |
| m6 | No second-person check is built into roles. | Use pull requests with review by the other teammate ("four-eyes") on all analysis code. |
| m7 | Wording such as "friendly" and "favouritism" can read as accusations of collusion. | Use neutral language ("excess points", "dyadic affinity") and say explicitly that patterns can reflect shared taste, language or diaspora, not coordination. |
| m8 | Country-code edge cases: the North Macedonia name change, Australia (no European region), and auto-qualifiers who vote in a semi-final they don't perform in. | Handle them in the data contract. |
| m9 | The audience is fans, but the outputs are static. | Stretch goal: a small interactive explorer (e.g., pair lookup), built from the same pipeline outputs. |

---

## 4. Meta-review scorecard

The scorecard rates the plan as a research design on standard validity dimensions. Scale: 1 = absent, 3 = adequate for a course project, 5 = publication or industry grade. "v2 target" is what the upgraded design in `04` aims for.

| Dimension | What is assessed | v1 | v2 target | Main lever |
|---|---|:-:|:-:|---|
| Question clarity | RQs specific, answerable, scoped | **4** | 5 | Operational definitions for "stable" and "gap" (M3, M4) |
| Construct validity | Does "bias" measure what it claims? | **2** | 4 | Joint quality + dyad model per vote type (C1) |
| Internal validity | Confounding, selection, data artefacts | **2** | 4 | Semi-finals, anomaly register, covariates (C2–C4) |
| Statistical conclusion validity | Inference, dependence, multiplicity, power | **2** | 4 | QAP, shrinkage, reliability, simulation-based power (M1–M3) |
| External validity | Generalisation beyond the sample | **3** | 3–4 | Optional 2026 hold-out (m5); scope statements |
| Reproducibility | Can a stranger rerun it from raw data? | **2** | 5 | Pipeline, lockfile, CI, pinned data (M7) |
| Transparency / pre-specification | Decisions fixed before results | **2** | 4 | Pre-registration at Milestone 2 (M8) |
| Novelty vs literature | Adds to prior ESC research | **3** | 4 | Dyad-level jury–televote divergence with uncertainty (see `02`) |
| Communication | Fit to audience, honest uncertainty | **3** | 5 | Backbone network, seriated heatmap, intervals on every ranking (M2, M6) |
| Feasibility | Deliverable by two students by Jan 27 | **4** | 4 | Minimum-viable vs stretch split in `04 §11` |
| **Mean** | | **2.7** | **4.3** | |

**Reading the scorecard:** the plan is strongest where proposals are usually weak (clarity, feasibility, honesty) and weakest where validity is decided (measurement and inference). That is good news: the fixes are methodological, not a change of topic.

---

## 5. Things the team should confirm (cannot be settled from the PDF)

1. ~~Which exact repository and commit is the "pre-approved GD 2026 dataset"?~~ **Resolved:** [`Graph-Drawing-Contest/eurovision-dataset`](https://github.com/Graph-Drawing-Contest/eurovision-dataset), commit `1f39f6b238b9` (2025-12-23), covering 1956–2025. Its `countries.json` and all 2016–2025 senior `rounds/` and `contestant.json` files are **byte-identical** to upstream [`EurovisionAPI/dataset`](https://github.com/EurovisionAPI/dataset) (commit `e56411125d4b`). The upstream also has 2026, which is usable only as an optional hold-out.
2. Whether the course **allows semi-final data** (it is in the same dataset) and a **2026 hold-out** check.
3. Whether the course wants a fixed tool stack (plain Jupyter) or allows a `src/` package plus CI. The engineering standards are written so that either works.
