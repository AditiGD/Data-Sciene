# 03 · Data audit: Eurovision voting data 2016–2026 (for the voter→receiver favouritism study)

Audit date 2026-11-18. All numbers below come from the scripts in `audit/` (rerun with `bash audit/run_all.sh <DATA_DIR>`).

## 0. Executive summary

| Item | Finding |
|---|---|
| Official course source | **GD 2026 fork: https://github.com/Graph-Drawing-Contest/eurovision-dataset**, commit `1f39f6b238b94f2806694a08607998258ed8a41e` (2025-12-23), ends at 2025. A byte-level comparison shows `countries.json` and every 2016–2025 senior `rounds/` and `contestant.json` file match upstream. Running the full pipeline on the fork clone gives an 2016–2025 tidy table is **identical** (41,350 rows). |
| Audited clone | Upstream `EurovisionAPI/dataset` @ `e56411125d4b` (2026-10-26, one squashed commit, so there is no history to diff). It also has **2026**. |
| Shape | 11 editions (2016–2026). 2020 was cancelled (`performances: null`). 30 rounds with data, 592 performances, **45,495** raw vote rows (41,350 for 2016–2025). The votes dicts are **dense**: every voter is listed for every non-self receiver, zeros included. |
| Integrity | **17 executable checks: 14 PASS, 3 PASS_WITH_KNOWN_EXCEPTION, 0 FAIL.** The exceptions are `WLD` missing from `countries.json` (12 voter-round records) and the 2024 NL disqualification (1 running-order gap, 1 qualifier missing from the final). Every ballot is exactly {12,10,8..1}, jury+public=total in every cell, vote sums = `points` in every case, and places are monotone in points. |
| Spot-checks vs web | Winners and winning totals for all 10 editions match (UA 534, PT 758, IL 529, NL 498, IT 524, UA 631, SE 583, CH 591, AT 436, BG 516), plus 12 further detail checks (§2.3). |
| Main comparability threats | Jury aggregation changed in 2018. Some voters are substitute/synthetic (2019 BY jury, 2022 six juries, SM televote every year). `WLD` exists from 2023. Semis were televote-only 2023–25, and the source label `total` hides this. 2026 is a new ruleset. Participation churns every year. |
| Coverage (finals 2016–25) | 1,853 ordered pairs observed per vote type, median 5 observations, max 9. **980 pairs have ≥5 observations.** Adding semis gives 1,499 (jury) and 1,544 (televote) pairs with ≥5. |
| Enrichment | Offline (PyPI): UN M49 sub-regions (`country_converter`), GeoNames land neighbours and languages and capitals (`geonamescache`), with a curated contiguity CSV built here. CEPII GeoDist/Language, COW contiguity, UN DESA migrant stock and religion data need a **manual download** on a normal machine; there are no PyPI bundles. |

## 1. Schema & profiling

### 1.1 Source schema as found (vs README)

| Path | Fields used | Notes / deviations from README |
|---|---|---|
| `data/countries.json` | code → name (54 entries) | Has historical/junior codes `CS`, `YU`, `GB-WLS`, `KZ`, `AD`, `MC`, `MA`, `SK`, `TR`, `LU`. **No `WLD`**, though `WLD` appears as a voter from 2023. Names are current names applied retroactively (`MK` = "North Macedonia" also for 2016–18; `CZ` = "Czechia" also for 2016–22). |
| `senior/<Y>/contest.json` | `country` (host), `intendedCountry` | `intendedCountry = UA` in 2023 (GB hosted for Ukraine). |
| `senior/<Y>/contestants/<NN>_<cc>/contestant.json` | `id`, `country` | 434 contestants 2016–26. Dir suffix = country in 100%. `id` unique within year. 2020 has 41 contestants but no rounds data. |
| `senior/<Y>/rounds/{semifinal1,semifinal2,final}.json` | `performances[] → contestantId, running, place, scores[]`; `disqualifieds` | The README says score names are `total`, `tele`, `jury`. **The data uses `public`, not `tele`.** In **2023–2025 semis only `total` exists**, and it is televote (+WLD), not jury+televote. `disqualifieds = [36]` (NL) sits in **2024 semifinal2.json**, not in final.json. |
| `Score.votes` | `{voterCode: points}` | Dense (zeros listed), self excluded. `total` cell = jury cell + public cell (e.g. 20 = 12+8). |

### 1.2 Per year/round profile (`audit/reference_tables/profile_year_round.csv`)

`voters_not_performing` lists the auto-qualifiers voting in their assigned semi, plus finalists' voters who did not qualify (final rows). No nulls in `place` or `running` in any round with data.

|   year | round      |   n_performers | score_names       |   n_voters_total |   n_voters_jury |   n_voters_public | WLD   | voters_not_performing                              |   null_place |   null_running |
|-------:|:-----------|---------------:|:------------------|-----------------:|----------------:|------------------:|:------|:---------------------------------------------------|-------------:|---------------:|
|   2016 | semifinal1 |             18 | jury,public,total |               21 |              21 |                21 | False | ES FR SE                                           |            0 |              0 |
|   2016 | semifinal2 |             18 | jury,public,total |               21 |              21 |                21 | False | DE GB IT                                           |            0 |              0 |
|   2016 | final      |             26 | jury,public,total |               42 |              42 |                42 | False | AL BA BY CH DK EE FI GR IE IS MD ME MK NO SI SM    |            0 |              0 |
|   2017 | semifinal1 |             18 | jury,public,total |               21 |              21 |                21 | False | ES GB IT                                           |            0 |              0 |
|   2017 | semifinal2 |             18 | jury,public,total |               21 |              21 |                21 | False | DE FR UA                                           |            0 |              0 |
|   2017 | final      |             26 | jury,public,total |               42 |              42 |                42 | False | AL CH CZ EE FI GE IE IS LT LV ME MK MT RS SI SM    |            0 |              0 |
|   2018 | semifinal1 |             19 | jury,public,total |               22 |              22 |                22 | False | ES GB PT                                           |            0 |              0 |
|   2018 | semifinal2 |             18 | jury,public,total |               21 |              21 |                21 | False | DE FR IT                                           |            0 |              0 |
|   2018 | final      |             26 | jury,public,total |               43 |              43 |                43 | False | AM AZ BE BY CH GE GR HR IS LV ME MK MT PL RO RU SM |            0 |              0 |
|   2019 | semifinal1 |             17 | jury,public,total |               20 |              20 |                20 | False | ES FR IL                                           |            0 |              0 |
|   2019 | semifinal2 |             18 | jury,public,total |               21 |              21 |                21 | False | DE GB IT                                           |            0 |              0 |
|   2019 | final      |             26 | jury,public,total |               41 |              41 |                41 | False | AM AT BE FI GE HR HU IE LT LV MD ME PL PT RO       |            0 |              0 |
|   2021 | semifinal1 |             16 | jury,public,total |               19 |              19 |                19 | False | DE IT NL                                           |            0 |              0 |
|   2021 | semifinal2 |             17 | jury,public,total |               20 |              20 |                20 | False | ES FR GB                                           |            0 |              0 |
|   2021 | final      |             26 | jury,public,total |               39 |              39 |                39 | False | AT AU CZ DK EE GE HR IE LV MK PL RO SI             |            0 |              0 |
|   2022 | semifinal1 |             17 | jury,public,total |               19 |              19 |                19 | False | FR IT                                              |            0 |              0 |
|   2022 | semifinal2 |             18 | jury,public,total |               21 |              21 |                21 | False | DE ES GB                                           |            0 |              0 |
|   2022 | final      |             25 | jury,public,total |               40 |              40 |                40 | False | AL AT BG CY DK GE HR IE IL LV ME MK MT SI SM       |            0 |              0 |
|   2023 | semifinal1 |             15 | total             |               19 |               0 |                 0 | True  | DE FR IT                                           |            0 |              0 |
|   2023 | semifinal2 |             16 | total             |               20 |               0 |                 0 | True  | ES GB UA                                           |            0 |              0 |
|   2023 | final      |             26 | jury,public,total |               38 |              37 |                38 | True  | AZ DK GE GR IE IS LV MT NL RO SM                   |            0 |              0 |
|   2024 | semifinal1 |             15 | total             |               19 |               0 |                 0 | True  | DE GB SE                                           |            0 |              0 |
|   2024 | semifinal2 |             16 | total             |               20 |               0 |                 0 | True  | ES FR IT                                           |            0 |              0 |
|   2024 | final      |             25 | jury,public,total |               38 |              37 |                38 | True  | AL AU AZ BE CZ DK IS MD MT NL PL SM                |            0 |              0 |
|   2025 | semifinal1 |             15 | total             |               19 |               0 |                 0 | True  | CH ES IT                                           |            0 |              0 |
|   2025 | semifinal2 |             16 | total             |               20 |               0 |                 0 | True  | DE FR GB                                           |            0 |              0 |
|   2025 | final      |             26 | jury,public,total |               38 |              37 |                38 | True  | AU AZ BE CY CZ GE HR IE ME RS SI                   |            0 |              0 |
|   2026 | semifinal1 |             15 | jury,public,total |               18 |              17 |                18 | True  | DE IT                                              |            0 |              0 |
|   2026 | semifinal2 |             15 | jury,public,total |               19 |              18 |                19 | True  | AT FR GB                                           |            0 |              0 |
|   2026 | final      |             25 | jury,public,total |               36 |              35 |                36 | True  | AM AZ CH EE GE LU LV ME PT SM                      |            0 |              0 |


Final voter list changes (excluding WLD): 2016→17 +PT +RO −BA −RU; 2017→18 +RU; 2018→19 −BG −UA; 2019→21 +BG +UA −AM −BY −HU −ME; 2021→22 +AM +ME −RU; 2022→23 −BG −ME −MK (+WLD); 2023→24 +LU −RO; 2024→25 +ME −MD; 2025→26 +BG +MD +RO −ES −IE −IS −NL −SI.

### 1.3 Join and null summary

| Check | Result |
|---|---|
| contestantId → country join | 592/592 (100%) |
| Null `performances` | 2020 × 3 rounds only |
| Null running/place/scores/votes | 0 |
| Non-integer points | 0 |
| Unexpected score names | 0 |
| Ties on total points (place decided by tie-break rule) | 16 (INFO, `checks/C05b_INFO_ties.csv`), e.g. 2023 SF2 RO=SM=0, RO placed 15th by running order (matches web) |

## 2. Integrity checks (`02_checks.py`, `--strict` exits non-zero on any un-documented failure)

### 2.1 Results (upstream 2016–2026; identical outcome on GD fork 2016–2025)

| ID | Assertion | Offending | Status |
|---|---|---|---|
| C01 | each (year,round,vote_type,voter) ballot = multiset {12,10,8,7,6,5,4,3,2,1} (jury, public; `total` in tele-only semis) | 0 | PASS |
| C02 | no self-votes | 0 | PASS |
| C03 | jury+public == total per voter→receiver; public==total where no jury (WLD) | 0 | PASS |
| C03b | `total`-only cells occur only in 2023–25 semis | 0 | PASS |
| C04 | Σ votes == `Score.points` for every performance × score name | 0 | PASS |
| C05a | performance points_total == points_jury + points_public | 0 | PASS |
| C05b | place ∈ 1..n, monotone non-increasing in points_total | 0 | PASS |
| C05c | running order is a permutation of 1..n | 1 (2024 final, slot 5 empty = NL) | KNOWN EXCEPTION |
| C06/C06b | unique (year,round,vote_type,voter,receiver); unique performance keys | 0 | PASS |
| C07 | every voter/receiver code ∈ countries.json | 12 (`WLD` × 2023–26 × 3 rounds) | KNOWN EXCEPTION |
| C08 | dense grid: every voter listed for every non-self receiver | 0 | PASS |
| C09 | points domain: split ∈ {0..8,10,12}; total ∈ pairwise sums | 0 | PASS |
| C10 | each country votes in exactly one semi; jury/public voter sets equal (bar WLD) | 0 | PASS |
| C11 | finalists = semi top-10 + auto-qualifiers; no non-qualifier in final | 1 (2024: NL qualified 2nd in SF2, absent from final) | KNOWN EXCEPTION |
| C12 | final voters == all participating countries that year | 0 (NL 2024 still votes) | PASS |
| C13 | contestant join | 0 | PASS |
| Schema | pandera `tidy_votes_v1` (§6.3) on analysis table | 0 | PASS |

Auto-qualifiers found (C11 INFO) match the rules: Big Five + host. 2017 includes UA (host), 2019 IL, 2021 NL, 2022 only the Big Five because IT was host, 2023 UA (winner, hosted by GB), 2025 CH, and 2026 AT + DE FR GB IT (ES withdrew).

### 2.2 Data-driven anomaly detector

Identical ballots across different voters in the same show are a signature of EBU substitute aggregates. The **only** hits in 2016–2026 are in 2022:

| Year | Round | Type | Identical ballots |
|---|---|---|---|
| 2022 | final | jury | AZ = GE; PL = RO |
| 2022 | semifinal2 | jury | PL = RO; GE = SM |

No voter has jury ballot == public ballot in any show, so there are no "jury copied into televote" substitutions.

### 2.3 Spot-checks against published results (all match)

| Fact (data) | Web source |
|---|---|
| Winners/totals 2016 UA 534, 2017 PT 758 (382 J / 376 T), 2018 IL 529, 2019 NL 498, 2021 IT 524, 2022 UA 631 | https://en.wikipedia.org/wiki/List_of_Eurovision_Song_Contest_winners ; https://www.guinnessworldrecords.com/world-records/84627-most-points-scored-at-eurovision |
| 2016: UA 534 (J 211/T 323), AU won jury (320), RU won televote (361) | https://eurovisionworld.com/esc/russia-won-televoting-australia-won-jury-ukraine-won-eurovision-2016 |
| 2019 **corrected** scoreboard: GB 11 pts (26th), SE 5th, DE 25th, BY jury 12→MT, 0→IL | https://ebu.ch/news/2019/05/ebu-issues-statement-on-eurovision-song-contest-grand-final-jury-result ; https://eurovisionworld.com/esc/eurovision-song-contest-2019-grand-final-corrected-result |
| 2021 GB 0 points; IT 524 | (winners list above) |
| 2022 UA 631 = J 192 + T 439; GB 466 (jury 283) | https://escxtra.com/2022/05/15/eurovision-2022-split-voting-results/ |
| 2023 SE 583 = J 340 + T 243 | https://www.rte.ie/entertainment/2023/0513/1383481-swedens-loreen-wins-eurovision-for-second-time |
| 2023 SF2 RO 0 (15th), SM 0 (16th) | https://www.eurofansradio.com/latest-news/eurovision-2023-semi-final-one-two-overall-results-revealed |
| 2024 CH 591, jury 365, 22 jury 12-pointers (list matches exactly, incl. NL) | https://escbeat.com/2024/05/13/eurovision-2024-results-statistical-analysis/amp/ |
| 2024 NL 2nd in SF2 (182) then disqualified | https://www.dutchnews.nl/2024/05/disqualified-dutch-eurovision-entry-was-second-in-semi-final/ |
| 2025 AT 436 = J 258 + T 178; IL T 297 / J 60; ES & BE televote 12→IL, jury 0 | https://www.timesofisrael.com/eurovision-organizers-dismiss-claims-of-voter-fraud-after-israel-tops-televote/ |
| 2025 SM last in final with 27 | https://en.wikipedia.org/wiki/Tutta_l%27Italia |
| 2026 BG 516, IL 343, RO 296, AU 287, IT 281, FI 279 | https://www.sortiraparis.com/en/what-to-see-in-paris/concerts-music-festival/articles/275471-eurovision-2026-bulgaria-wins-the-contest-france-finishes-11th-the-full-rankings ; https://www.irishtimes.com/world/europe/2026/05/17/eurovision-2026-bulgaria-pip-israel-at-the-post-to-win-in-vienna/ |
| 2026 MD jury → RO 3, UA 0 (controversy) | https://escxtra.com/2026/05/19/crisis-in-moldova-tv-director-general-resigns-eurovision/ |

## 3. Rule changes and anomalies 2016–2026: impact and handling

Handling legend: **KEEP** (no action), **FLAG** (flag column, keep in main analysis), **SENS** (main analysis keeps it, sensitivity run drops it), **EXCL** (exclude from pair analysis).

| # | Year | Event (verified) | Records affected in data | Flag in `tidy_votes` | Handling |
|---|---|---|---|---|---|
| 1 | 2016 | **Split jury/televote presentation introduced.** Each country gives two ballots of 58 points; total = sum. Sources: https://eurovisionworld.com/esc/voting-systems-in-eurovision-history , https://escinsight.com/2016/05/15/ukraine-russia-australia-parsing-results-years-top-three | All 2016+ shows have `jury` and `public` | — | KEEP. Defines the start of the study window. |
| 2 | 2016 | **Danish juror (Hilda Heick) ranked in reverse.** The official result stood. https://tvtonight.com.au/2016/05/oops-danish-eurovision-juror-admits-voting-error-for-ukraine.html ; https://eurovisionary.com/danish-jury-votes-published | 2016 final, voter DK, jury (+total): 1 ballot, 26 cells. Data: DK jury UA 12, AU 10, GE 0 | `JUROR_ERROR_2016_DK` | SENS |
| 3 | 2016 | **Romania expelled** (TVR debts). https://eurovision.tv/story/tvr-romania-no-longer-entitled-to-take-part-in-eurovision-2016 | RO absent 2016 (structural missing) | — | KEEP (missing ≠ 0) |
| 4 | 2017 | **Russia withdrew** (host UA barred Samoylova). https://eurovisionworld.com/esc/russia-withdraws-from-eurovision-2017 ; https://wiwibloggs.com/2017/04/13/russias-channel-one-will-not-broadcast-eurovision-as-ebu-unable-to-confirm-julia-samoylovas-participation/ | RU absent as voter and receiver 2017 | — | KEEP (missing) |
| 5 | 2018 | **Jury aggregation changed:** 5 jurors' ranks are combined with an undisclosed **exponential weight model** instead of the plain average rank (2016–17). https://eurovisionworld.com/esc/eurovision-2018-ebu-changes-the-calculation-of-jury-voting ; https://escxtra.com/2018/04/28/the-jury-voting-change-explained/ | All jury ballots 2018+ (structural break) | `jury_method` column | SENS: jury analyses with and without 2016–17, or a year fixed effect |
| 6 | 2019 | **Belarus jury dismissed** (jurors revealed SF1 rankings). The EBU used a substitute aggregate in the final, published it **reversed**, and corrected it on 22 May. **Data holds the corrected values.** https://ebu.ch/news/2019/05/ebu-issues-statement-on-eurovision-song-contest-grand-final-jury-result | 2019 final, voter BY, jury (+total): 1 ballot | `SUBST_JURY_2019_BY` | EXCL from pair/jury analysis (not a Belarusian jury); keep in receiver totals |
| 7 | 2019 | **Ukraine withdrew** (MARUV contract dispute). https://eurovisionworld.com/esc/ukraine-withdraws-from-eurovision-2019 | UA absent 2019 | — | KEEP (missing) |
| 8 | 2019 | **FYR Macedonia → North Macedonia** (Prespa). Code `MK` is unchanged in the data. https://eurovisionary.com/by-country/fyr-macedonia ; https://ipfs.ssi.eecc.de/ipns/en.wikipedia-on-ipfs.org/wiki/North_Macedonia_in_the_Eurovision_Song_Contest | None (codes stable); display names are retroactive | — | KEEP. Join on code, never on name. |
| 9 | 2020 | **Contest cancelled** (COVID-19, 18 Mar 2020). https://www.rollingstone.com/music/music-news/eurovision-2020-coronavirus-cancellation-969046/ | 3 round files with `performances: null`; 41 contestant dirs | — | EXCL year (9 contests) |
| 10 | 2021 | **Belarus disqualified** (two songs rejected). https://en.wikipedia.org/wiki/Belarus_in_the_Eurovision_Song_Contest_2021 | BY absent 2021–26 | — | KEEP (missing) |
| 11 | 2022 | **Russia excluded** (25 Feb 2022). https://eurovisionworld.com/esc/ebu-kicks-russia-out-of-eurovision-2022 | RU absent 2022+; final has 25 entries | — | KEEP (missing) |
| 12 | 2022 | **Six juries removed for irregular SF2 patterns: AZ, GE, ME, PL, RO, SM.** Replaced by substitute aggregates in **SF2 and final**. https://eurovisionworld.com/esc/eurovision-2022-votes-from-six-national-juries-removed ; https://escxtra.com/2022/05/19/ebu-reveals-eurovision-2022-irregular-voting-patterns/ | 2022 SF2 + final, those 6 voters, jury (+total): 12 jury ballots, 498 cells. Identical-ballot signature confirmed (§2.2) | `SUBST_JURY_2022_SIX` | EXCL from pair-level jury analysis; SENS for televote/total |
| 13 | 2016–26 | **San Marino has no real televote.** It shares Italy's phone network and is below the threshold, so the EBU substitutes a composite from an undisclosed group of countries. https://en.wikipedia.org/wiki/San_Marino_in_the_Eurovision_Song_Contest ; https://escinsight.com/2016/12/05/san-marino-televote-eurovision-2016/ (2023+ method not confirmed) | Voter SM, `public` (+`total`), all years: 37 ballots, 780 cells | `SYNTH_TELEVOTE_SM` | EXCL SM as televote voter in pair analysis (SM as receiver OK). In 2022 SF2/final **both** SM ballots are synthetic. |
| 14 | 2023 | **Rest-of-World online televote** (one extra voter set, `WLD`, in semis and final). https://www.ebu.ch/news/2022/11/voting-changes-announced-for-eurovision-song-contest-2023 | `WLD` voter, public/total, 2023–26: 18 ballots, 357 cells. Not in countries.json | `REST_OF_WORLD`, `voter_is_country=False` | EXCL from pairs. Baselines should use country voters only (or document inclusion). |
| 15 | 2023–25 | **Semis decided by televote only** (backup juries used only on televote failure; no activation found). https://wiwibloggs.com/2022/11/22/eurovision-2023-voting-change-removes-juries-from-semi-finals/273929/ | 2023–25 semis: only `total`, which semantically = televote | `vote_kind='televote'` | Use `vote_kind`, not `vote_type`. No semi jury data 2023–25. |
| 16 | 2023 | **UK hosted on behalf of Ukraine.** UA auto-qualified, GB as Big Five. Data: `intendedCountry=UA`. https://www.ebu.ch/news/2022/11/voting-changes-announced-for-eurovision-song-contest-2023 | No vote anomaly | — | KEEP. Note "host" ≠ venue in 2023. |
| 17 | 2023 | **Czech Republic → "Czechia"** branding. Code `CZ` unchanged. https://escxtra.com/2023/02/11/ebu-confirms-czechia-name-change-for-eurovision/ | None | — | KEEP |
| 18 | 2023 | BG, ME, MK withdrew; ME returned 2025; MK has not returned (data-verified; reasons not web-verified) | Missing | — | KEEP |
| 19 | 2024 | **Netherlands (Joost Klein) disqualified** after SF2 (placed 2nd, 182). It **retained its vote**: Dutch jury gave CH 12. https://eurovisionworld.com/esc/joost-klein-from-the-netherlands-disqualified-from-eurovision-2024 ; https://www.hartvannederland.nl/entertainment/songfestival/artikelen/dit-is-de-winnaar-van-het-eurovisie-songfestival | NL absent as receiver in final (running slot 5 empty). NL jury + televote present as voter | `VOTER_DQ_ENTRY_2024_NL` | KEEP NL as voter (SENS). NL-as-receiver 2024 final = missing, **not 0**. |
| 20 | 2024 | **Norwegian juror controversy** (said he withheld points from IL). The EBU accepted NRK's notarised result; NO jury gave IL 8. https://www.algemeiner.com/2024/05/13/eurovision-organizers-disappointed-jury-member-improperly-withheld-points-israel-due-gaza-war/ | 2024 final, NO jury (+total) | `JUROR_CONTROVERSY_2024_NO` | KEEP/FLAG |
| 21 | 2024–25 | **Israel televote disputes** (ES, BE, FI, IS broadcasters asked for audits). The EBU found no irregularity and used **no substitutes**. https://www.timesofisrael.com/eurovision-organizers-dismiss-claims-of-voter-fraud-after-israel-tops-televote/ | None (valid data) | — | KEEP. Discuss in RQ3 interpretation (televote campaigns, diaspora). |
| 22 | 2024–25 | RO absent 2024–25 and MD absent 2025 (data) | Missing | — | KEEP |
| 23 | 2026 | **Ruleset change:** juries back in semis (~50/50), juries grow from 5 to 7 incl. 18–25-year-olds, televote cap drops from 20 to 10 votes per payment method. https://www.eurovision.com/newsroom/release/ebu-announces-changes-to-voting-rules-for-2026/ ; https://wiwibloggs.com/2025/11/21/voting-changes-announced-for-eurovision-2026-including-juries-back-in-the-semi-finals-and-halving-televotes-allowed/285815 | All 2026 rows (216 ballots) | `RULESET_2026` | EXCL (outside window; GD fork ends 2025). Use only as out-of-sample check. |
| 24 | 2026 | **Boycott by ES, NL, IE, SI, IS** over Israel's participation. BG, MD, RO returned; 35 countries. Only 4 Big-Five auto-qualifiers. https://www.npr.org/2025/12/05/nx-s1-5634466/eurovision-contest-israel ; https://www.thepinknews.com/2026/05/12/eurovision-song-contest-2026-boycott-countries/ | 2026 participation | `RULESET_2026` | as #23 |
| 25 | 2026 | Four juries (CZ, CY, MT, LU) had 6 instead of 7 members; valid per EBU. https://eurovoix.com/2026/06/16/eurovision-2026-ebu-explains-six-member-juries-at-this-years-contest/ | 2026 jury ballots of those 4 (16 ballots incl. total) | `JURY_6_MEMBERS_2026` | FLAG |
| 26 | 2016+ | **Australia:** non-EBU-area participant by invitation. Since 2016 it must qualify and votes only in its own semi + final. https://en.wikipedia.org/wiki/Australia_in_the_Eurovision_Song_Contest | AU as voter/receiver every year | — | KEEP. Region = "Australia and New Zealand"; no neighbours. Exclude from border tests or code as its own region. |
| 27 | all | **Big Five + host vote in an assigned semi without performing.** Each country votes in exactly one semi (C10). | 2–3 non-performing voters per semi (§1.2) | `voter_performs_in_round` | KEEP. Semi observations exist only for receivers in the voter's semi. |

Also note for the study design: proposal scope A (finals only) observes a pair **only if the receiver qualified**, and qualification itself depends on neighbour support in the semi. This is a selection effect; a robustness run should use scope B (finals + semis).

## 4. Coverage for the study (`(generated by audit/run_all.sh) out/coverage_pairs.csv`, `audit/reference_tables/coverage_summary.csv`)

Country voters only (WLD excluded), split records only, 2016–2025 (9 contests).

| Scope | Vote kind | Rows | Ordered pairs observed (of 1,980 = 45×44) | median n | max n | pairs ≥3 | **pairs ≥5** | pairs ≥7 | pairs = 9 |
|---|---|---|---|---|---|---|---|---|---|
| (a) Finals only | jury | 8,999 | 1,853 | 5 | 9 | 1,466 | **980** | 475 | 186 |
| (a) Finals only | televote | 8,999 | 1,853 | 5 | 9 | 1,466 | **980** | 475 | 186 |
| (b) Finals + semis | jury (semis only 2016–22) | 13,158 | 1,924 | 7 | 13 | 1,754 | **1,499** | 1,112 | 368 |
| (b) Finals + semis | televote | 14,787 | 1,930 | 8 | 16 | 1,800 | **1,544** | 1,253 | 344 |

Distribution, scope (a) jury, n_obs → #pairs: 1:118, 2:269, 3:207, 4:279, 5:240, 6:265, 7:170, 8:119, 9:186. Of the scope-(a) cells, 147 jury cells are 2022 substitutes, 25 are the BY 2019 substitute, 229 televote cells are SM synthetic, and 77 are WLD (already excluded above). The flagged share is about 2–3%.

### Participation matrix (F = finalist, S = semi only, blank = absent; `audit/reference_tables/participation_matrix.csv`)

| country   | 2016   | 2017   | 2018   | 2019   | 2021   | 2022   | 2023   | 2024   | 2025   | 2026   |   n_years_participating |   n_finals |
|:----------|:-------|:-------|:-------|:-------|:-------|:-------|:-------|:-------|:-------|:-------|------------------------:|-----------:|
| AL        | S      | S      | F      | F      | F      | S      | F      | S      | F      | F      |                      10 |          6 |
| AM        | F      | F      | S      | S      |        | F      | F      | F      | F      | S      |                       9 |          6 |
| AT        | F      | F      | F      | S      | S      | S      | F      | F      | F      | F      |                      10 |          7 |
| AU        | F      | F      | F      | F      | S      | F      | F      | S      | S      | F      |                      10 |          7 |
| AZ        | F      | F      | S      | F      | F      | F      | S      | S      | S      | S      |                      10 |          5 |
| BA        | S      |        |        |        |        |        |        |        |        |        |                       1 |          0 |
| BE        | F      | F      | S      | S      | F      | F      | F      | S      | S      | F      |                      10 |          6 |
| BG        | F      | F      | F      |        | F      | S      |        |        |        | F      |                       6 |          5 |
| BY        | S      | F      | S      | F      |        |        |        |        |        |        |                       4 |          2 |
| CH        | S      | S      | S      | F      | F      | F      | F      | F      | F      | S      |                      10 |          6 |
| CY        | F      | F      | F      | F      | F      | S      | F      | F      | S      | F      |                      10 |          8 |
| CZ        | F      | S      | F      | F      | S      | F      | F      | S      | S      | F      |                      10 |          6 |
| DE        | F      | F      | F      | F      | F      | F      | F      | F      | F      | F      |                      10 |         10 |
| DK        | S      | F      | F      | F      | S      | S      | S      | S      | F      | F      |                      10 |          5 |
| EE        | S      | S      | F      | F      | S      | F      | F      | F      | F      | S      |                      10 |          6 |
| ES        | F      | F      | F      | F      | F      | F      | F      | F      | F      |        |                       9 |          9 |
| FI        | S      | S      | F      | S      | F      | F      | F      | F      | F      | F      |                      10 |          7 |
| FR        | F      | F      | F      | F      | F      | F      | F      | F      | F      | F      |                      10 |         10 |
| GB        | F      | F      | F      | F      | F      | F      | F      | F      | F      | F      |                      10 |         10 |
| GE        | F      | S      | S      | S      | S      | S      | S      | F      | S      | S      |                      10 |          2 |
| GR        | S      | F      | S      | F      | F      | F      | S      | F      | F      | F      |                      10 |          7 |
| HR        | F      | F      | S      | S      | S      | S      | F      | F      | S      | F      |                      10 |          5 |
| HU        | F      | F      | F      | S      |        |        |        |        |        |        |                       4 |          3 |
| IE        | S      | S      | F      | S      | S      | S      | S      | F      | S      |        |                       9 |          2 |
| IL        | F      | F      | F      | F      | F      | S      | F      | F      | F      | F      |                      10 |          9 |
| IS        | S      | S      | S      | F      | F      | F      | S      | S      | F      |        |                       9 |          4 |
| IT        | F      | F      | F      | F      | F      | F      | F      | F      | F      | F      |                      10 |         10 |
| LT        | F      | S      | F      | S      | F      | F      | F      | F      | F      | F      |                      10 |          8 |
| LU        |        |        |        |        |        |        |        | F      | F      | S      |                       3 |          2 |
| LV        | F      | S      | S      | S      | S      | S      | S      | F      | F      | S      |                      10 |          3 |
| MD        | S      | F      | F      | S      | F      | F      | F      | S      |        | F      |                       9 |          6 |
| ME        | S      | S      | S      | S      |        | S      |        |        | S      | S      |                       7 |          0 |
| MK        | S      | S      | S      | F      | S      | S      |        |        |        |        |                       6 |          1 |
| MT        | F      | S      | S      | F      | F      | S      | S      | S      | F      | F      |                      10 |          5 |
| NL        | F      | F      | F      | F      | F      | F      | S      | S      | F      |        |                       9 |          7 |
| NO        | S      | F      | F      | F      | F      | F      | F      | F      | F      | F      |                      10 |          9 |
| PL        | F      | F      | S      | S      | S      | F      | F      | S      | F      | F      |                      10 |          6 |
| PT        |        | F      | F      | S      | F      | F      | F      | F      | F      | S      |                       9 |          7 |
| RO        |        | F      | S      | S      | S      | F      | S      |        |        | F      |                       7 |          3 |
| RS        | F      | S      | F      | F      | F      | F      | F      | F      | S      | F      |                      10 |          8 |
| RU        | F      |        | S      | F      | F      |        |        |        |        |        |                       4 |          3 |
| SE        | F      | F      | F      | F      | F      | F      | F      | F      | F      | F      |                      10 |         10 |
| SI        | S      | S      | F      | F      | S      | S      | F      | F      | S      |        |                       9 |          4 |
| SM        | S      | S      | S      | F      | F      | S      | S      | S      | F      | S      |                      10 |          3 |
| UA        | F      | F      | F      |        | F      | F      | F      | F      | F      | F      |                       9 |          9 |


## 5. Enrichment plan

### 5.1 Source feasibility

| Covariate | Source (citable) | Obtainable here? | Notes |
|---|---|---|---|
| Region (UN M49 sub-region, continent) | UN M49 via `country_converter` 1.3.2 (PyPI, bundled) | **Yes, offline** (done: `country_attributes.csv`) | Gotcha: coco stores GB ISO2 as regex `^GB$|^UK$`, so key on ISO3. M49 puts CY, IL, GE, AM, AZ in "Western Asia" and AU in "Australia and New Zealand". |
| Land neighbours, languages, capital, population | GeoNames countryInfo (CC BY 4.0) via `geonamescache` 3.0.2 (PyPI, bundled) | **Yes, offline** (done) | AL–RS is counted via Kosovo, so it is flagged DISPUTED. |
| Contiguity incl. sea (≤12/24/150/400 mi) | COW Direct Contiguity v3.2 (Stinnett et al. 2002), https://correlatesofwar.org/data-sets/direct-contiguity/ ; R: `peacesciencer::cow_contdir` | Manual download only (no PyPI). Covers to 2016; borders are unchanged since. | Authority for verifying the curated maritime list. |
| Distance, contiguity, common official/ethnic language, colonial ties | CEPII GeoDist `dist_cepii` (Mayer & Zignago 2011, WP 2011-25), http://www.cepii.fr/CEPII/en/bdd_modele/download.asp?id=6 ; CRAN `cepiigeodist` (CC0) ships the same tables | Manual download (cepii.fr not reachable from here; no PyPI). Via R: `cepiigeodist::dist_cepii` → CSV | Note: SRB/MNE/MKD coding in GeoDist predates splits, so check ME and RS rows (Serbia-and-Montenegro era). |
| Linguistic proximity (common spoken/native, LP1/LP2) | CEPII Language (Melitz & Toubal 2014, JIE 92(2)), https://www.cepii.fr/CEPII/en/bdd_modele/presentation.asp?id=19 | Manual download | Better than a binary common language. |
| Diaspora (bilateral migrant stock) | UN DESA International Migrant Stock 2024 (POP/DB/MIG/Stock/Rev.2024), https://www.un.org/development/desa/pd/content/international-migrant-stock ; viewer: https://www.migrationpolicy.org/data-tool/immigrant-emigrant-populations-origin-destination | Manual download (xlsx origin×destination, 1990–2024) | Use stock of receiver-born residents in voter country / voter population. The strongest televote covariate in the literature. |
| Religion | World Religion Project, National dataset 1945–2010 (Maoz & Henderson 2013), https://correlatesofwar.org/?p=316 ; ARDA mirror | Manual download; ends 2010 | Use 2010 dominant-denomination shares (Orthodox/Catholic/Protestant/Muslim/Jewish). |
| EU sub-regions | EuroVoc 911/912/913/914 (Northern/Southern/Western/Central & Eastern Europe), https://en.wikipedia.org/wiki/EuroVoc | Lists on op.europa.eu; small and hand-codable | Alternative to M49. Caucasus is separate in EuroVoc. |
| Historical blocs | Hand-curated in `04_enrichment.py`: ex-USSR, ex-Yugoslavia, Nordic Council, Baltic, ex-Warsaw-Pact (non-USSR), Big Five | Done | Memberships are standard historical facts. |
| Natural Earth polygons | `geodatasets` wheel is 22 KB, so there is **no bundled data** (downloads on demand, blocked here). `geopandas` ≥1.0 no longer bundles naturalearth_lowres. | Not offline | Not needed, because contiguity comes from GeoNames + COW. |

### 5.2 Artifacts produced (offline)

| File | Content |
|---|---|
| `audit/reference_tables/country_attributes.csv` | 45 participants: ISO3, name, M49 sub-region, continent, EU27 (current), GeoNames languages, primary language, capital + lat/lon, land neighbours (all / ESC-only), bloc dummies |
| `audit/reference_tables/contiguity_curated.csv` | **Undirected curated contiguity, 93 pairs: 77 land** (GeoNames, symmetric-checked, with notes for Kaliningrad, enclave SM–IT, NI border, Dagestan, **AL–RS disputed**) **+ 16 maritime** (1 ≤12 mi DK–SE; 1 ≤24 mi FR–GB; 14 ≤150 mi: EE–FI, AL–IT, GR–IT, IT–MT, HR–IT, IT–ME, DK–NO, DK–PL, DE–SE, PL–SE, EE–SE, LV–SE, BE–GB, GB–NL). Each row has a source and an approximate distance note. Maritime classes are a curation on COW thresholds; **verify against COW contdir v3.2**. |
| `(generated by audit/run_all.sh) out/dyads_offline.csv` | 1,980 ordered dyads: contig_type, land_border, any_neighbour, capital great-circle km, shared primary / any listed language (Serbo-Croatian cluster merged), same M49 sub-region, both-in-bloc dummies, same_bloc_any |

Counts (ordered dyads): land_border 154, any_neighbour 186, shared primary language 32, same M49 sub-region 380, same bloc 140. Caveats: there are no land neighbours for AU, IS, MT, CY, IL. For GR–CY (shared language, >150 mi of sea) and similar pairs, rely on language/diaspora covariates, not borders.

**Recommendation:** use `same_un_subregion` + `land_border` (primary RQ1 test). Run `any_neighbour`, `same_bloc_any` and `shared_primary_language` as secondary labels. Add UN DESA diaspora as the key confounder for televote if time allows.

## 6. Data dictionary and data contract

### 6.1 `tidy_votes.parquet` (primary analysis table; grain = one source vote cell)

Primary key: (year, round, vote_type, voter, receiver).

| Column | Type | Allowed values | Null | Meaning | Source / derivation |
|---|---|---|---|---|---|
| year | int | 2016–2026, ≠2020 | no | contest year | directory name |
| round | str | semifinal1, semifinal2, final | no | show | round filename |
| round_kind | str | semifinal, final | no | coarse show type | derived |
| vote_type | str | jury, public, total | no | **label in source** `Score.name` | JSON |
| vote_kind | str | jury, televote, combined | no | **semantic** source of points (2023–25 semis `total` → televote) | derived (§3 #15) |
| is_split_record | bool | | no | True for jury/televote cells (use these for analysis; `combined` rows duplicate them in finals) | derived |
| voter | str | 45 ISO-2 codes + `WLD` | no | awarding country (WLD = rest of world) | `votes` key |
| voter_is_country | bool | | no | False for WLD | derived |
| voter_performs_in_round | bool | | no | voter has an entry in this show | derived |
| receiver | str | 45 ISO-2 codes | no | receiving country | contestant.json `country` via `contestantId` |
| receiver_contestant_id | int | ≥0 | no | contestant id (unique within year) | `contestantId` |
| receiver_place | int | 1–26 | no | final place of receiver in that show | `place` |
| receiver_running | int | 1–26 | no | running order | `running` |
| points | int | split: {0..8,10,12}; combined: pairwise sums | no | points awarded (zeros explicit) | `votes` value |
| jury_method | str | average_rank (2016–17), exponential_weight (2018+) | yes (televote) | jury aggregation regime | §3 #5 |
| anomaly_flags | str | `|`-joined subset of 9 flags (§3) | empty | data-quality flags | §3 |

Flag vocabulary: `SUBST_JURY_2019_BY`, `SUBST_JURY_2022_SIX`, `SYNTH_TELEVOTE_SM`, `REST_OF_WORLD`, `JUROR_ERROR_2016_DK`, `VOTER_DQ_ENTRY_2024_NL`, `JUROR_CONTROVERSY_2024_NO`, `JURY_6_MEMBERS_2026`, `RULESET_2026`. Row and ballot counts are in `audit/reference_tables/anomaly_flag_counts.csv`.

**Recommended analysis filter (RQ1–3):** `year<=2025 & is_split_record & voter_is_country & round_kind=='final'`. For jury, additionally drop `SUBST_JURY_*`; for televote, drop `SYNTH_TELEVOTE_SM`. Sensitivity runs: keep them; drop `JUROR_ERROR_2016_DK` and `VOTER_DQ_ENTRY_2024_NL`; jury 2018+ only; scope (b) with semis.

**Baseline note:** "receiver's average from all other voters that year" should be computed over the same filtered voter set (WLD and substitutes excluded) and per vote kind. Rows are dense, so zeros are included correctly. Do not treat absent receivers (non-qualifiers, 2024 NL) as zeros.

### 6.2 Auxiliary tables

| Table | Grain / key | Key columns |
|---|---|---|
| `performances.csv` | (year, round, contestant_id) | country, running, place, points_total/jury/public, nvoters_* |
| `contestants.csv` | (year, contestant_id) | country, dir, artist, song, host, intended_host |
| `rounds.csv` | (year, round) | date, time, n_performances (null 2020), disqualifieds (JSON) |
| `participation_matrix.csv` | country | per-year F/S/blank |
| `country_attributes.csv` | code | see §5.2 |
| `contiguity_curated.csv` | (a, b) a<b | contig_type ∈ land, sea_le12mi, sea_le24mi, sea_le150mi; source; note |
| `dyads_offline.csv` | (voter, receiver) | see §5.2 |

### 6.3 Pandera schema (executable: `05_schema.py`, passes on upstream and on the GD fork)

```python
"""Pandera data contract for the analysis-ready tidy vote table (tidy_votes.parquet).

Run: python3 -I 05_schema.py <OUT_DIR>      -> validates and prints PASS / failure cases
"""

import os, sys
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

ESC_CODES = [
    "AL",
    "AM",
    "AT",
    "AU",
    "AZ",
    "BA",
    "BE",
    "BG",
    "BY",
    "CH",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GE",
    "GR",
    "HR",
    "HU",
    "IE",
    "IL",
    "IS",
    "IT",
    "LT",
    "LU",
    "LV",
    "MD",
    "ME",
    "MK",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "RU",
    "SE",
    "SI",
    "SM",
    "UA",
]
SPLIT_POINTS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
TOTAL_POINTS = sorted({a + b for a in SPLIT_POINTS for b in SPLIT_POINTS})
FLAGS = {
    "SUBST_JURY_2019_BY",
    "SUBST_JURY_2022_SIX",
    "SYNTH_TELEVOTE_SM",
    "REST_OF_WORLD",
    "JUROR_ERROR_2016_DK",
    "VOTER_DQ_ENTRY_2024_NL",
    "JUROR_CONTROVERSY_2024_NO",
    "JURY_6_MEMBERS_2026",
    "RULESET_2026",
}
KEY = ["year", "round", "vote_type", "voter", "receiver"]


def flags_ok(s):
    return s.fillna("").map(lambda x: all(f in FLAGS for f in x.split("|") if f))


tidy_votes_schema = DataFrameSchema(
    {
        "year": Column(int, [Check.in_range(2016, 2026), Check.ne(2020)]),
        "round": Column(str, Check.isin(["semifinal1", "semifinal2", "final"])),
        "round_kind": Column(str, Check.isin(["semifinal", "final"])),
        "vote_type": Column(
            str, Check.isin(["jury", "public", "total"])
        ),  # label as in source JSON
        "vote_kind": Column(str, Check.isin(["jury", "televote", "combined"])),  # semantic meaning
        "is_split_record": Column(bool),
        "voter": Column(str, Check.isin(ESC_CODES + ["WLD"])),
        "voter_is_country": Column(bool),
        "voter_performs_in_round": Column(bool),
        "receiver": Column(str, Check.isin(ESC_CODES)),
        "receiver_contestant_id": Column(int, Check.ge(0)),
        "receiver_place": Column(int, Check.in_range(1, 27)),
        "receiver_running": Column(int, Check.in_range(1, 27)),
        "points": Column(int, Check.isin(TOTAL_POINTS)),
        "jury_method": Column(
            str, Check.isin(["average_rank", "exponential_weight"]), nullable=True
        ),
        "anomaly_flags": Column(str, Check(flags_ok, element_wise=False), nullable=True),
    },
    checks=[
        Check(lambda d: ~d.duplicated(KEY), error="duplicate primary key"),
        Check(lambda d: d.voter != d.receiver, error="self vote"),
        Check(
            lambda d: ~d.vote_type.isin(["jury", "public"]) | d.points.isin(SPLIT_POINTS),
            error="split points domain",
        ),
        Check(lambda d: (d.vote_kind != "jury") | (d.voter != "WLD"), error="WLD has no jury"),
        Check(lambda d: (d.voter != "WLD") | (d.year >= 2023), error="WLD only from 2023"),
        Check(
            lambda d: (
                (d.vote_kind != "combined")
                | (d.round_kind == "final")
                | ~d.year.isin([2023, 2024, 2025])
            ),
            error="2023-25 semis have no combined/jury",
        ),
        Check(
            lambda d: d.voter_is_country == (d.voter != "WLD"), error="voter_is_country consistent"
        ),
    ],
    strict=True,
    coerce=True,
    unique=KEY,
    name="tidy_votes_v1",
)

if __name__ == "__main__":
    df = pd.read_parquet(os.path.join(sys.argv[1], "tidy_votes.parquet"))
    try:
        tidy_votes_schema.validate(df, lazy=True)
        print(f"PASS tidy_votes_v1: {len(df)} rows x {df.shape[1]} cols")
    except pa.errors.SchemaErrors as e:
        print("FAIL")
        print(e.failure_cases.head(50).to_string())
        sys.exit(1)
```

### 6.4 Contract rules (in addition to the schema)

1. Upstream source pinned to the GD fork commit `1f39f6b`. Any re-download must reproduce `02_checks.py --strict` with 0 FAIL and the same row count (41,350 for 2016–2025).
2. Joins on ISO-2 codes only. Display names come from `countries.json`, which uses modern names retroactively.
3. `WLD` must never enter country-level pair statistics.
4. New anomalies must be added to `FLAGS` in the schema and to `KNOWN_EXCEPTIONS` in the checks, with a citation.

## 7. Files

| Path | Purpose |
|---|---|
| `audit/run_all.sh` | full pipeline (auto-detects years; works on upstream and fork) |
| `audit/00_survey.py` | raw structure survey |
| `audit/01_build_tidy.py` | JSON → raw tidy + performances/contestants/rounds |
| `audit/02_checks.py` | 17 integrity assertions (`--strict`) → `(generated by audit/run_all.sh) out/checks/*.csv`, `summary.csv` |
| `audit/03_annotate_coverage.py` | semantics + flags → `tidy_votes.parquet/csv`; coverage; participation |
| `audit/04_enrichment.py` | offline covariates, curated contiguity, dyads |
| `audit/05_schema.py` | pandera contract |
| `audit/06_profile.py` | per-round profile |
| `audit/ (upstream run, not committed)` | outputs from upstream (2016–2026) |
| `audit/reference_tables/` | same outputs from the GD fork (2016–2025) |

Unresolved / not verified: San Marino's televote method for 2023+ (online vote possible?); whether any 2023–25 semi backup jury was ever activated (none found); reasons for the 2021 AM and 2023 BG/ME/MK absences (data-verified only).

## 8. Additional sources consulted (WebSearch)

- GD 2026 creative topic (fork described, "updated on Jan 21, 2026"): https://mozart.diei.unipg.it/gdcontest/2026/creative/
- EBU 2023 voting changes: https://www.ebu.ch/news/2022/11/voting-changes-announced-for-eurovision-song-contest-2023
- 2026 jury/televote changes: https://www.eurovision.com/newsroom/release/ebu-announces-changes-to-voting-rules-for-2026/ ; https://www.rte.ie/entertainment/2025/1121/1545121-eurovision-unveils-major-voting-rules-changes-for-2026
- Belarus 2021: https://eurovisionworld.com/esc/belarus-disqualified-from-eurovision-song-contest-2021
- San Marino 2025 criticism: https://escxtra.com/2025/06/12/smrtv-director-general-releases-statement-on-eurovision-2025-voting/
- San Marino online-vote possibility (2023 rules): https://eurovoix.com/2022/11/22/san-marino-voting-changes-eurovision-2023/
- Australia rules: https://en.wikipedia.org/wiki/Australia_in_the_Eurovision_Song_Contest
- CEPII GeoDist docs (CRAN mirror): https://cran.r-project.org/web/packages/cepiigeodist/refman/cepiigeodist.html
- COW contiguity in R: https://search.r-project.org/CRAN/refmans/peacesciencer/html/cow_contdir.html
- World Religion Data: https://correlatesofwar.org/?p=316
