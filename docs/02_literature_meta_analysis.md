# 02 · Systematic review and meta-analysis: voting bias in the Eurovision Song Contest (ESC)

Prepared for: "Eurovision Song Contest Voting Patterns" proposal (GF 2016–2025; RQ1 pair favouritism and region/border, RQ2 stability, RQ3 jury–televote gap). Date of search: 2026-11-18.

**How to read the tags.** `[V]` means the number or claim appeared in a search-result snippet for the cited URL (verified-snippet). `[R]` means it comes from background knowledge and was not seen in a snippet (unverified-recall). No full text could be opened, because WebFetch and DNS were blocked. All extraction therefore comes from abstracts, indexes and secondary snippets. "n.r." means the item was not reported in the accessible text. Treat every per-study detail as abstract-level only.

Companion files (in `meta_analysis/`):
- `A_effects.csv`: 31 extracted quantitative effects.
- `A_build_effects_and_meta.py`: reproducible meta-analysis and vote-count.
- `A_meta_results.json`: the outputs.
- `verify_jt_corr_from_data.py`: recomputes §5.2 from the course dataset.
- `search_log.md`: raw search log.

> **Status of evidence:** pages could not be opened, so study-level details come from abstracts and snippets. Before citing any study in the final report, open its full text and confirm the extracted numbers. Quality scores in §3 are provisional.

---

## 1. Search protocol (PRISMA-style)

**Sources.** WebSearch, standard and extended modes. US index. No database exports. No full-text access.

**Queries.** 108 queries were run. They fall into seven strands:
- (a) Anchor verification, 19 named anchors. Example: `Spierdijk Vellekoop 2009 "structure of bias in peer voting systems"`.
- (b) Recent work from 2019–2026: `Eurovision jury versus televote bias split votes 2016`, `"six ESCs" 2017 2023 differences between public and jury votes`, `Televoting Ties reciprocity CEE`, `gravity model Eurovision PPML`, `cultural diplomacy Eurovision televote jury`.
- (c) Diaspora and migration: `Eurovision televoting migration diaspora econometric`, `migrant stock elasticity`.
- (d) Networks and communities: `stochastic block model OR ERGM Eurovision`, `community detection Eurovision 2016 2022`, `L-modularity`.
- (e) GD 2026: `"Eurovision Song Contest Voting Communities"`, `"10.4230/LIPIcs.GD.2026.39"`, `"Somoji Rao" Eurovision`, `Graph Drawing Contest Report 2026`.
- (f) Method analogues: `Plackett-Luce/Bradley-Terry Eurovision`, `QAP MRQAP Eurovision`, `Zitzewitz figure skating nationalism`, `FIFA award voting bias`.
- (g) Effect-size hunting, 15 queries for coefficients, correlations and neighbour bonuses.

The full list is in `notes_A.md` and in this session's log.

**Inclusion.** All four had to hold:
- I1: an empirical or methodological analysis of ESC voting (bias, favouritism, blocs, communities, jury vs televote, determinants), or a study that uses ESC dyadic votes as a measured construct.
- I2: the study's existence was verified by a scholarly-index URL in a search result.
- I3: a journal article, proceedings paper, book chapter, working paper, preprint, or editorially reviewed magazine article (*Significance*), or a narrative review.

**Exclusion.**
- E1: purely qualitative or cultural-studies work with no vote analysis, e.g. Öberg 2025 (*Politics & Policy*, doi 10.1111/polp.70051), Welslau & Selck 2024 (cultural diplomacy, Russia and Ukraine), and the edited Eurovision volumes.
- E2: song-feature or MIR-only success prediction with no voter→receiver analysis, e.g. the ETH/RSOS "Breaking the Code" study, arXiv 2505.11555.
- E3: journalism, blogs, fan sites, podcasts and student theses. These are kept only as **grey supplementary evidence (Table G)**, are never counted as included studies, and are always labelled.
- E4: non-ESC analogues. These are listed only in §7.

**Flow.** All counts are approximate and were hand-tallied from result lists, since no export was possible.

| Stage | n |
|---|---|
| Result links returned (about 10 per query × 108 queries) | ≈1,050 |
| Unique records after de-duplication | ≈260 |
| Excluded on title/snippet: news, Wikipedia, fan pages, unrelated | ≈170 |
| Assessed on abstract/snippet | ≈90 |
| Excluded (E1 6, E2 3, unverifiable 4: e.g. a "394 songs" study whose source could not be pinned down, and arXiv 2602.05542, whose content was never found) | 13 |
| Retained as grey only (E3: theses, blogs, journalism) | ≈30 (≈20 used in Table G) |
| **Included studies** | **45** (37 primary ESC-vote studies, 5 methods/proxy studies, 1 narrative review, 2 GD-2026 items with metadata/abstract only) |

**Anchor verification.** All 19 named anchors were found, with the corrections below.
- Dekker's paper is in *Connections* 28(1) (2008); it is cited elsewhere as 2007.
- Saavedra et al.'s real title is "Identifying the underlying structure and dynamic interactions in a voting network".
- Orgaz et al. is Bello-Orgaz, Cajías & Camacho, WIMS 2011.
- Clerides & Stengos, *Ekonomia* 15(1): the page range is inconsistent across indexes (22–44 vs 1–44).
- "Budzinski & Pannicke 2017" is two separate papers: JCE 41(4) and a convergence paper (doi 10.1080/17510694.2017.1332451, journal not confirmed in snippets).
- GD 2026 paper .39 exists; only metadata was retrieved. Report .38 exists; its abstract was seen. Snippets disagree on the LIPIcs volume number (395 vs 396).

---

## 2. Evidence table (included studies)

Abbreviations:
- C = combined vote, J = jury, T = televote.
- GF = Grand Final, SF = semi-final.
- Q-base = how song quality is separated from bias.

| # | Study (venue) + URL | Data years / rounds | Unit | Vote | Bias definition / Q-base | Method | Covariates | Inference / null | Key findings (tagged) | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Yair 1995, *Social Networks* 17(2):147–161 [link](https://bibsonomy.org/bibtex/2767a40e3f9b91986e83ac0f5ce8e23d9/plaufer) | 1975–1992 [V, secondary]; 22 of 24 countries [V] | country×country | J | n.r. | network blockmodel/cluster | politics, culture | n.r. | 3 regional blocs: Mediterranean, Western, Northern [V] | jury era only; Q-base n.r. |
| 2 | Yair & Maman 1996, *Acta Sociologica* 39(3):309–325 [link](https://cris.huji.ac.il/en/publications/the-persistent-structure-of-hegemony-in-the-eurovision-song-conte/) | n.r. | blocs | J | n.r. | structural/bloc analysis | — | n.r. | 4 empirical blocs; Western bloc holds a "tertius gaudens" hegemony; Northern and Mediterranean blocs avoid each other and send surplus votes West [V] | descriptive |
| 3 | Haan, Dijkstra & Dijkstra 2005, *J Cultural Econ* 29(1):59–78 [link](https://ideas.repec.org/a/kap/jculte/v29y2005i1p59-78.html) | national finals + European finals | song | J vs T | outcomes vs non-quality factors | regression | order of appearance etc. | n.r. | Experts are less affected by non-quality factors than the public; experts are still not unbiased; later performers score higher [V] | jury/televote choice of national final is endogenous [V, critique] |
| 4 | Fenn, Suleman, Efstathiou & Johnson 2006, *Physica A* 360(2):576–598 [arXiv](https://arxiv.org/abs/physics/0505071) | 1992–2003 [V] | country×country, dynamic | C/T (regime change mid-window) | similarity of voting distributions, excluding mutual votes [V] | dynamic network, cliques | geography | vs randomised results [V] | Clustering is "more than random"; cliques are not explained by geography alone [V] | spans jury→televote switch |
| 5 | Gatherer 2006, *JASSS* 9(2) 1 [link](https://www.jasss.org/9/2/1.html) | contest history to 2005 | dyad | C | departure from simulated random voting | Monte Carlo of contest histories | — | simulation null [V] | Large geographic blocs grew from small early-1990s partnerships after the mid-1990s; blocs decided ≥2 contests; central countries have higher future win probability [V]; Balkan bloc; Greece–Cyprus [V, press] | null likely ignores song quality [inferred] |
| 6 | Saavedra, Efstathiou & Reed-Tsochas 2007, *Physica A* 377:672–688 [arXiv](https://arxiv.org/abs/physics/0605253) | 1984–2003 [V] | network | C | — | Q-analysis + SNA, dynamic connectivity [V] | — | n.r. | Clustering mostly among geographically close countries [V, secondary]; asks whether topology alone identifies the winner | Q-base n.r. |
| 7 | Dekker 2008 (cited as 2007), *Connections* 28(1):59 [TOC](https://assets.noviams.com/novi-file-uploads/insna/Connections_Archive/2008__Volume_28__Issue_1-e7f9858a.pdf) | n.r. | dyad | C | collusive and one-way biased links [V] | friendship network | language, borders [V, secondary] | n.r. | "Bridge" countries between blocs; number of borders matters regardless of song quality [V, secondary] | details n.r. |
| 8 | Ginsburgh & Noury 2008, *EJPE* 24(1):41–52 [link](https://ideas.repec.org/a/eee/poleco/v24y2008i1p41-52.html) | 1975–2003 [V, secondary] | dyad | C | quality modelled explicitly | regression incl. vote-trading test (current vs two previous years) [V] | language, culture | n.r. | Apparent vote trading is sincere voting driven by quality and linguistic/cultural proximity, not politics [V] | coefficients n.r. |
| 9 | Spierdijk & Vellekoop 2009, *Empirical Econ* 36(2):403–425 [link](https://link.springer.com/article/10.1007/s00181-008-0202-5) | 1975–2003 [V, blog] | dyad bias (DV = bias of i→j) [V] | C | bias as DV | multilevel models [V] | geography, culture, language, religion, ethnicity [V] | n.r. | Strong evidence of bias, structured very differently across countries; "hardly any" evidence of regional block voting [V]; political factors play no role [V, per Blangiardo & Baio] | early-period data |
| 10 | Gleyze 2011, *Cybergeo* [doi 10.4000/cybergeo.23451](https://doaj.org/article/265c8705248e40809b6162ec58c7dfab) | 1993–2008 [V] | {voter, performer} pair | C | deviation from a quality-only vote [V] | social vs spatial network comparison | contiguity | n.r. | "Over-votes" concern neighbouring countries [V] | French-language; details n.r. |
| 11 | Bello-Orgaz, Cajías & Camacho 2011, WIMS [dblp](https://dblp.org/rec/conf/wims/OrgazCC11) | two 5-year periods [V, secondary] | network | J era vs T era | — | clustering / community detection | — | n.r. | Stable communities evolve over periods; diaspora effect appears enhanced by televoting [V, secondary] | snippet-level only |
| 12 | Clerides & Stengos 2012, *Ekonomia* 15(1) [link](https://econpapers.repec.org/RePEc:ekn:ekonom:v:15:y:2012:i:1:p:1-44) | 25 contests, 1981–2005 [V] | dyad | C | "regardless of quality" controls | econometric (Tobit reported elsewhere, not verified) | culture, geography, economics, politics, order, language, gender, host [V] | n.r. | Clusters exchange points regardless of quality; cultural, geographic, economic and political factors significant; reciprocity yes, strategic voting no [V] | coefficients n.r. |
| 13 | Charron 2013, *Social Networks* 35(3):484–497 [link](https://www.sciencedirect.com/science/article/abs/pii/S0378873313000506) + CES paper [link](https://ces.confex.com/ces/2013/webprogram/Paper1450.html) | 1975–2012 [V] | dyad | C + televote share | **pair average points minus receiver's average points from all voters** [V, via Siganos & Tabner] | regression | impartiality (QoG), friendship networks, diaspora, televote share [V] | n.r. | Impartial institutions → "quality over friendship"; diaspora effect directly tested and strongest where more points come from televote; all 3 hypotheses strongly supported [V] | **Same baseline as the proposal** |
| 14 | García & Tanase 2013, *Adv Complex Syst* 16(8) 1350037 [arXiv](https://arxiv.org/abs/1301.2995) | 1975–2012; communities 1997–2012 [V] | dyad (FoF) | C | **Friend-or-Foe coefficient**: over/under-voting adjusted for overall song quality, max = 1 [V] | signed weighted modularity; polarisation index | — | n.r. | Stronger modularity than raw votes; 5 communities (1997–2012) [V]; jury more quality-driven, televote more geographic/cultural [V]; polarisation spike within EU 2010–11 [V] | combined votes |
| 15 | Blangiardo & Baio 2014, *J Appl Stat* 41(10):2312–2322 [arXiv](https://arxiv.org/abs/1308.6312) | GF 1998–2012 [V] | vote (ordinal category) | T era (C after 2009) | structured random effect + covariates | Bayesian hierarchical ordinal logistic [V] | cultural + spatial proximity (shared borders), World Bank migration stocks, year, host, song language, act type [V] | posterior | No negative bias; mild, systematic positive bias that is too small to decide outcomes [V]; geographic and migration effects positively associated [V] | 2009–12 mixes J+T |
| 16 | Budzinski & Pannicke 2017, *J Cultural Econ* 41(4):343–378 [link](https://ideas.repec.org/a/kap/jculte/v41y2017i4d10.1007_s10824-016-9277-6.html) | ESC 1998–2014; BSC 2005– [V] | dyad | T (1998–2008 model) | **bias = points − quality benchmark** (e.g., 12 vs 3.0) [V] | regression | culture, geography, performance [V] | n.r. | Biases of similar magnitude also appear in a homogeneous national contest; neighbour bias less frequent in BSC than ESC [V] | coefficients n.r. |
| 17 | Budzinski & Pannicke 2017, doi 10.1080/17510694.2017.1332451 [record](https://katalog.lib.cas.cz/KNAV/EdsRecord/edsair,edsair.doi...........d7462358bd94d5776876b3506ab5f98b) | 1975–2016 [V] | votes | C | concentration | concentration / homogenisation test | — | n.r. | Tests whether tastes converge (more concentration, less regional) [V]; result n.r. | result not seen |
| 18 | Antipov & Pokryshevskaya 2017, *JDM* 12(4):415–419 [link](https://ideas.repec.org/a/cup/judgdm/v12y2017i4p415-419_7.html) | ESC GF 2009–2012 + New Wave 2005–2016 [V] | song | J vs T | — | order-effect regression | running order | n.r. | Weaker order effect in ESC finals; limited jury order effect, none for public [V, secondary] | order, not dyadic bias |
| 19 | Stockemer, Blais, Kostelka & Chhim 2018, *Politics* 38(4):428–442 [link](https://repository.essex.ac.uk/23757/) | viewer survey | individual voter | T (survey) | stated preferences | survey | affinity | n.r. | 11% of vote choices strategic; 36% vote for a song that is neither their favourite nor the likely winner (neighbour/ethnic/favourite-country voting) [V] | self-report |
| 20 | Mantzaris, Rein & Hopkins 2018, *JASSS* 21(1) 1 [link](https://jasss.org/21/1/1.html) | 1957–2017 [V] | dyad over year windows | C | vs **uniform** random allocation under each year's rules [V] | resampling null; networks from significant edges | — | per-edge significance [V] | Regional collusion and biases from proximity and culture [V]; Greece–Cyprus and Nordic pairs as examples; Turkey bridges to Azerbaijan [V] | null ignores song quality; multiplicity n.r.; data on GitHub [V] |
| 21 | Mantzaris, Hopkins & Rein 2018, *J Comput Soc Sci* 1:377–390 [link](https://link.springer.com/article/10.1007/s42001-018-0020-2) | 1957–2017 | dyad | C | as #20 | preference/collusion/neglect/avoid edges [V] | — | as #20 | Preference in- and out-degree rank-correlate with total score; neglect correlates less [V] | as #20 |
| 22 | D'Angelo, Murphy & Alfò 2019, *Ann Appl Stat* 13(2):900–930 [link](https://projecteuclid.org/euclid.aoas/1560758432) | 1998–2015; 2016–17 dropped because of rule change [V] | multiplex network (edition layers) | C | latent positions | latent space model for multidimensional networks [V] | — | model-based | The latent space matters for edge probabilities, but positions only partly match geography [V] | excludes split era; R package spaceNet [V] |
| 23 | Svete & Hostnik 2020, arXiv 2002.06609 [link](https://arxiv.org/abs/2002.06609); also Svete, Hostnik & Šubelj, *Uporabna informatika* XXVIII(2) [dlib](https://dlib.si/stream/URN:NBN:SI:DOC-J5TUA77Z/340fccf8-3ee8-40b2-8120-cc0c8e0d6f49/PDF) | n.r. | dyad network | C | "significantly more points than expected" [V] | community detection, link prediction | geography | n.r. | Some correlation with geographic proximity; network + preference model barely beats betting odds [V] | |
| 24 | Siganos & Tabner 2020, *JIBS* 51(2):263–273 [link](https://ideas.repec.org/a/pal/jintbs/v51y2020i2d10.1057_s41267-019-00271-3.html) | 1999–2013 [V] | dyad affinity | C | Charron baseline [V] | regression of cross-border M&A on affinity | distance metrics | n.r. | Above-average voting predicts more cross-border M&A; Greece–Turkey affinity low despite proximity [V] | proxy use |
| 25 | Dekker 2021, MODSIM 2021 [pdf](https://mssanz.org.au/modsim2021/papers/I8/dekker2.pdf) | GF 2021 [V] | country | T | quality factor in model [V] | 5-factor simulation incl. expatriate voting [V] | diaspora populations (uneven quality) [V] | fit (abs. error, R²; values n.r.) | Expatriate voting modelled explicitly; earlier claim that it plays a large part in televoting [V] | 1 year |
| 26 | Ginsburgh & Moreno-Ternero 2023, *J Cultural Econ* 47:247–277 [link](https://link.springer.com/article/10.1007/s10824-022-09456-5) | 2021 [V] | rule | J and T | — | social choice / game theory | — | — | Recommends Shapley voting for juries and televoters; covers contrast effects and whether experts judge better [V] | normative |
| 27 | **Gustar 2023**, *Significance* 20(2):6–10 [link](https://academic.oup.com/jrssig/article/20/2/6/7095712) | 2016–2022 [V] | pairwise song comparisons | **J and T separately** | Plackett–Luce weights [V] | PL modelling | contiguity (5 countries have no voting neighbours: AUS, CYP, ISL, ISR, MLT) [V] | n.r. | **T: neighbour preferred 71% of the time, PL weight ×>2.4; J: 55%, weight ×1.22 (+22%)**; border effect "much greater" in public [V] | magazine; SEs n.r. |
| 28 | Budzinski, Gänßle & Weimar 2023, Ilmenau DP 171 [link](https://ideas.repec.org/p/zbw/tuiedp/171.html) | split era, juror-level [V] | juror × song | J (individual) | similarity → upward bias | panel regression | juror role, gender, profession, nationality/culture [V] | n.r. | Similarity raises awarded points; classical-music jurors less biased than radio/TV presenters and journalists [V] | WP; data+code public [V] |
| 29 | "Pop populism…", *Acta Politica* 58:737–760 (2023) [link](https://link.springer.com/10.1057/s41269-022-00262-7) | 21 contests 1999–2019; 767 songs; 30,822 dyads [V] | dyad | C | — | regression | ethno-traditional cues × PRR strength [V] | n.r. | Tests whether ethno-traditional cues draw more votes where PRR parties are strong [V]; result n.r. | authors not seen |
| 30 | Taylor, Keller & Fosdick 2023, arXiv 2311.18039 [link](https://arxiv.org/abs/2311.18039) | 2015 [V] | 27×27 vote matrix | C | receiver random effects [V] | restricted network regression [V] | shared border [V] | model-based | Choice of RE specification changes inference; restriction mitigates but does not remove network confounding [V] | methods demo |
| 31 | Burgoyne, Spijkervet & Baker 2023, ISMIR [pdf](https://archives.ismir.net/ismir2023/paper/000097.pdf) | 1,719 entries; juror rankings since 2016; betting odds [V] | entry | J and T | **Rasch partial-credit "cantobel"** interval-scale quality [V] | discrete choice / IRT | audio features | — | Bookmakers good but imperfect; audio foundation models predict some competitiveness [V] | dataset+code on GitHub [V] |
| 32 | Giofré 2024 [record](https://ouci.dntb.gov.ua/works/4Ejw6jql) | n.r. | dyad | C | voting bias measure | regression of bilateral portfolio holdings | cultural distance | n.r. | Bias explains portfolio investment for non-professional investors only, more for debt [V] | proxy |
| 33 | Kadoić, Žajdela Hrustek & Gligora Marković 2025, *CEJOR* 33(3) [link](https://link.springer.com/article/10.1007/s10100-025-00971-2) | 6 GFs 2017–2023 [V] | song/ranking, national and contest level | **J vs T** | — | Mann–Whitney, rank conformity | — | NHST | Jury–public ranking conformity varies by year; public-vote correlations higher than expected; snippets conflict on whether jury vs public points differ significantly [V] | page range inconsistent across indexes |
| 34 | Schoenberg, Ierapetritis, Foramitti & Schwand 2025, *Rom J Reg Sci* 19(1):1–19 [link](https://ideas.repec.org/a/rrs/journl/v19y2025i1p1-19.html) | GF 1995–2019 [V] | dyad | C | — | gravity, PPML [V] | distance, economic ties, population, migration, diplomatic ties [V] | n.r. | Proximity, economic and historical ties outweigh politics/diaspora; **diaspora observable but n.s.**; diplomatic tensions have no lasting effect [V] | combined votes |
| 35 | "The impact of cultural diplomacy on the ESC", *J Cultural Econ* 49(4) (2025) [link](https://link.springer.com/article/10.1007/s10824-025-09541-5) | n.r. | dyad | **J and T separately** | — | bilateral gravity [V] | cultural institutes, tourists, students, cultural goods [V] | n.r. | **+ effect on televote; n.s. on jury** [V] | authors not seen |
| 36 | Battiston, Magnani, Paolini & Rossi 2025, Pisa DP 2025/322 [link](https://econpapers.repec.org/RePEc:pie:dsedps:2025/322) | SF and GF [V] | voter × song | J and T | Spotify-based quality check [V] | positional (Borda) voting analysis | competitor proximity | n.r. | Strategic downgrading of close competitors of one's own entry, "particularly" by jurors; not explained by quality [V] | WP |
| 37 | Łopatecki 2025, *Textus et Studia* 11(4):135–164 [pdf](https://czasopisma.upjp2.edu.pl/textusetstudia/article/download/5755/5314/10813) | 2016–2025 (context 1956–2025) [V] | blocs | **J and T** | — | quantitative descriptive | politics, diaspora [V] | n.r. | "Perceptual polarisation" J vs T; blocs persist (e.g., Nordic); Western dominance in public vote declines in favour of South and East [V] | Polish; abstract-level |
| 38 | Brun & Boas, *Eur Polit Sci Rev* (year not confirmed; press 2026) [link](https://www.cambridge.org/core/journals/european-political-science-review/article/does-politics-drive-cultural-preferences-voting-behavior-in-the-eurovision-song-contest/2F9BE3E290F94C186DCAB57F9C39CA5A) | survey PL/ES/SE/NL before the 2025 final [V] | individual | T (survey) | measured song quality | survey regression | political, cultural attitudes [V] | NHST | Political, cultural and quality effects are significant but small; voting mostly individual taste; cultural favouritism stronger (difference n.s.) [V] | 4 countries |
| 39 | "Televoting Ties", *Pamiętnik Teatralny* 75(3) (2026) [link](https://czasopisma.ispan.pl/index.php/pt/article/view/4640) | 2000, 2003–08, **2016–2025** [V] | CEE dyads | T | — | gift-exchange / reciprocity reading | — | n.r. | Reciprocal CEE televote exchanges read as ritualised solidarity [V] | author unverified |
| 40 | Kotrotsiou, Hanias & Stavrinides 2026, Springer chapter [link](https://link.springer.com/chapter/10.1007/978-3-032-09101-7_34) | n.r. | directed weighted network | n.r. | max-points edges | community detection (cluster optimal, infomap, edge betweenness) [V] | — | n.r. | **10 stable voting communities** shaped by cultural/geopolitical ties [V] | years n.r. |
| 41 | "Generalized L-Modularity…" 2026, arXiv 2605.24450 [link](https://arxiv.org/pdf/2605.24450) | 1995–2015, 49 nodes [V] | temporal network | C (pre-2016) [V] | — | LAGO temporal modularity | — | — | Methods demonstration on ESC [V] | pre-split |
| 42 | **Somoji Rao, Baur & Krone 2026**, GD 2026, LIPIcs [doi 10.4230/LIPIcs.GD.2026.39](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.GD.2026.39) | GD-2026 dataset (J and public votes) [V, contest report] | network | J and T | n.r. | community visualisation | neighbourhood (subtitle "Does Neighborhood Predict Alliance?" [V, LinkedIn]) | n.r. | 1st place, GD 2026 Creative Topic [V, HFT profile](https://www.hft-stuttgart.com/p/melanie-baur); findings n.r. | metadata only; **closest competitor to this project (same dataset)** |
| 43 | Di Bartolomeo, Förster, Terziadis & Wulms 2026, GD Contest Report, LIPIcs 38:1–38:11 [doi 10.4230/LIPIcs.GD.2026.38](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.GD.2026.38) | GD-2026 ESC dataset; dynamic, multivariate, jury + public [V] | — | J and T | — | contest report | — | — | Creative topic: voting patterns over the years [V] | no findings |
| 44 | Felbermayr & Toubal 2010, *Eur Econ Rev* 54(2):279–293 [link](https://econpapers.repec.org/RePEc:eee:eecrev:v:54:y:2010:i:2:p:279-293) | n.r. | dyad-year | C | **quality-adjusted** score [V] | gravity with bilateral FE [V] | standard cultural proxies | — | ESC score is a time-varying, pair-specific cultural-proximity measure correlated with conventional proxies; quality adjustment raises correlations except for common language and genetic distance [V] | proxy |
| 45 | Yair 2019, *Eur J Cultural Studies* 22(5–6):1013–1029 [link](https://cris.huji.ac.il/en/publications/douze-point-eurovisions-and-euro-divisions-in-the-eurovision-song/) | review | — | — | — | narrative review | — | — | Four strands, including "Euro-Divisions" (bloc voting) and Eurovision data used as a proxy [V] | not systematic |
| 46 | Ginsburgh & Noury working paper / Clerides & Stengos CEPR DP 5732 | — | — | — | — | — | — | — | Earlier versions only; merged with #8 and #12 and not counted separately | — |

*Unique included studies = rows 1–45. Row 46 is a merge note only (earlier working-paper versions folded into #8 and #12). The Slovenian journal version of #23 is the same study.*

### Table G: grey supplementary evidence (not counted; used only for direction checks and RQ priors)

| Source | Type | Years | Claim [tag] |
|---|---|---|---|
| [Successful Software blog](https://successfulsoftware.net/tag/2025/) (from eurovisionworld tables) | blog | GF 2016–2025 | Pearson r, jury vs public, by year: .447, .656, .255, .441, .618, .467, .490, .627, .160 [V] |
| [ESC Insight 2019](https://escinsight.com/2019/03/31/eurovision-song-contest-new-voting-rules-presentation-televote-sequence/) | blog | "last three editions" | Mean Spearman jury vs televote +0.13 [V]; estimand unclear |
| [Gustar blog](https://musichistorystats.com/eurovision-love-thy-neighbour/) | blog | n.r. | Italy: 36 jury points from 5 neighbours vs 27.1 expected (A/E 1.328); public: 9 twelve-point awards to neighbours vs 3 expected; result robust to voter/border permutation; jury-only neighbour correlation n.s. [V] |
| [Parsons blog](https://medium.com/@alexparsons/measuring-the-politics-eurovision-with-data-365f92c6d20e) | blog | n.r. | +1.9 (±0.245) points to border-sharing countries; +0.39 (±0.068) per degree of separation removed [V] |
| [Boulos 2013, Duke MA](https://dukespace.lib.duke.edu/items/ed19fb6a-b074-4234-8106-53d19dfb2c0a) | thesis | 1989–2012 | Split vote had 204 bias cases, fewer than half of the televote's [V] |
| [Ruijter, EUR MSc](https://thesis.eur.nl/pub/52224/Ruijter-DHH-385582-MA-thesis-BehEc.pdf) | thesis | n.r. | Reciprocity: points received the previous year → points given, coefficient 0.082 (significant) [V] |
| [Bos, EUR MSc](https://thesis.eur.nl/pub/48682/Final_Thesis_Andre_Bos_409580.pdf) | thesis | n.r. | Expert jury cuts the influence of most external factors relative to televote [V] |
| [Megatrend](https://www.megatrend.com/en/community-detection-at-eurovision/) | blog | **2016–2019, J and T networks** | Televote driven mostly by geopolitics; 4 strong televote communities: Northern Europe; Romance-language; ex-Yugoslavia + Austro-Hungary; Eastern Europe [V] |
| [Maynooth (Kavanagh)](https://maynoothuniversity.ie/node/547122) | university blog | long-run | Bloc voting rose with televoting in the late 1990s; argues "real political voting" happens with juries more than the public [V] |
| [Groningen news 2021](https://www.rug.nl/news/2021/05/mapping-favouritism-at-the-eurovision-song-contest-does-it-impact-the-results?lang=en) | press | 1975–2019 | Caucasus and Balkans benefit most from political voting; it rarely decides the winner; Sweden is best after correction [V] |
| [Euronews 2012](https://www.euronews.com/culture/2012/05/21/eurovision-the-great-voting-conspiracy) | journalism | 1975–2003 | Greece→Cyprus mean 9.7 points; Cyprus→Greece 10.7; Turkey–Cyprus 0 points in 19 shared contests [V] |
| [Euronews/AFP 2025](https://www.euronews.com/my-europe/2025/05/16/eurovision-here-are-the-contests-strongest-geopolitical-alliances-throughout-the-years) | journalism | 9 editions | Baltic→Nordic 590 points vs 306 among Baltics; Nordic, ex-Yugoslav, ex-USSR and Baltic blocs show solidarity [V] |
| [ESC Insight 2018](https://escinsight.com/2018/05/07/consider-the-human-factor-in-the-eurovision-juries/) | blog | GF 2017 | Greece got 48 jury points, 12 from Cyprus; Cyprus got 36, 12 from Greece [V]; 2022: EBU discarded six national juries' scores [V] |
| [AOAV 2026](https://aoav.org.uk/2026/eurovisions-israel-televote-surge-in-last-two-years-raises-questions-over-political-mobilisation/), [Conversation 2026](https://theconversation.com/how-public-voting-has-turned-eurovision-from-a-song-contest-into-a-political-platform-282733) | journalism | 2016–2025 | Israel 2024: televote 323 vs jury 52; Ukraine 2022: televote 439 vs jury 192; Ireland→Lithuania televote linked to diaspora [V] |
| [europazzia](https://europazzia.com/storia/esc-2/all-songs-in-eurovision-song-contest-finals-semi-finals/winners-esc/observations/discrepancies-between-the-jury-and-televote/) | fan site | 2009–2025 | Jury and televote winners agreed in all but one year 2009–14 (2011), but in only one year 2015–25 (2017) [V] |

---

## 3. Risk-of-bias / quality appraisal

Rubric: six domains, each scored 0, 1 or 2. "?" means not assessable from the accessible text; it is excluded from the denominator. Scores come from abstract-level evidence only, so treat them as provisional.

- **Q, song-quality confound.** 0 = none or uniform-random null. 1 = crude baseline (average-points difference, FoF, benchmark). 2 = model-based quality (receiver/song effects, PL/Rasch, explicit quality term).
- **D, dyadic/network dependence.** 0 = iid tests on dyads. 1 = partial (rule-respecting resampling, multilevel, FE). 2 = explicit network model (sender/receiver random effects, latent space, QAP-type).
- **M, multiplicity for pair-level claims.** 0 = pair claims with no inference. 1 = per-pair tests against a null, no correction. 2 = FDR/joint inference, or claims only at group level.
- **S, small-sample uncertainty/shrinkage.** 0 = point estimates. 1 = SE/CI. 2 = hierarchical partial pooling.
- **V, vote-type/regime handling.** 0 = pools across rule regimes. 1 = single regime or era controls. 2 = jury and televote analysed separately.
- **R, reproducibility.** 0 = none stated. 1 = data source described. 2 = data and code public.

| Study | Q | D | M | S | V | R | Score / assessable max |
|---|---|---|---|---|---|---|---|
| Yair 1995 | ? | ? | ? | ? | 1 | ? | 1/2 |
| Haan et al. 2005 | 1 | ? | ? | ? | 2 | ? | 3/4 |
| Fenn et al. 2006 | ? | 1 | ? | ? | 0 | ? | 1/4 |
| Gatherer 2006 | 0 | 1 | 1 | ? | 1 | ? | 3/8 |
| Saavedra et al. 2007 | ? | 1 | ? | ? | 0 | 1 | 2/6 |
| Ginsburgh & Noury 2008 | 2 | ? | 2 | ? | 0 | ? | 4/6 |
| Spierdijk & Vellekoop 2009 | 1 | 1 | 2 | 2 | 0 | ? | 6/10 |
| Gleyze 2011 | 1 | ? | ? | ? | 0 | ? | 1/4 |
| Clerides & Stengos 2012 | 1 | ? | 2 | ? | 0 | ? | 3/6 |
| Charron 2013 | 1 | ? | 2 | ? | 1 | ? | 4/6 |
| García & Tanase 2013 | 1 | 1 | ? | ? | 0 | ? | 2/6 |
| Blangiardo & Baio 2014 | 2 | 2 | 2 | 2 | 1 | 1 | **10/12** |
| Budzinski & Pannicke 2017 (JCE) | 1 | ? | 2 | ? | 1 | ? | 4/6 |
| Mantzaris et al. 2018 (JASSS/JCSS) | 0 | 1 | 1 | 0 | 1 | 2 | 5/12 |
| D'Angelo et al. 2019 | 1 | 2 | 2 | ? | 1 | 2 | **8/10** |
| Svete & Hostnik 2020 | ? | 1 | ? | ? | 0 | ? | 1/4 |
| Gustar 2023 | 2 | ? | 2 | ? | 2 | ? | **6/6** |
| Budzinski et al. 2023 (WP) | ? | ? | ? | ? | 2 | 2 | 4/4 |
| Taylor et al. 2023 (methods) | 2 | 2 | 2 | 1 | 0 | ? | 7/10 |
| Burgoyne et al. 2023 | 2 | ? | 2 | ? | 2 | 2 | 8/8 |
| Kadoić et al. 2025 | 0 | 0 | 2 | ? | 2 | ? | 4/8 |
| Schoenberg et al. 2025 | ? | 1 | 2 | 1 | 0 | ? | 4/8 |
| JCE 2025 (cultural diplomacy) | ? | 1 | 2 | ? | 2 | ? | 5/6 |
| Battiston et al. 2025 (WP) | 2 | ? | 2 | ? | 2 | ? | 6/6 |
| Łopatecki 2025 | ? | ? | ? | ? | 2 | ? | 2/2 |
| Kotrotsiou et al. 2026 | 0 | 1 | ? | ? | ? | ? | 1/4 |
| Somoji Rao et al. 2026 (GD) | ? | ? | ? | ? | 2 | 2 (public GD data) | 4/4 (no findings visible) |

**Main appraisal findings.**
1. Almost no study handles quality, dyadic dependence and multiplicity together. The closest are Blangiardo & Baio and D'Angelo et al., and both predate 2016.
2. Uniform-random nulls ignore song quality and therefore overstate "collusion" between countries that both send strong songs. This affects Gatherer 2006 and Mantzaris et al. 2018.
3. Per-pair significance claims are almost never multiplicity-corrected, as far as the accessible text shows.
4. Before Gustar 2023, Kadoić 2025, Łopatecki 2025 and JCE 2025, studies pool jury, televote and 50/50 regimes, so bias is confounded with the aggregation rule.
5. Snippet-only appraisal means "?" dominates. These scores bound uncertainty; they are not verdicts.

---

## 4. Thematic synthesis

| Theme | Direction and consistency | Key evidence | Implication for the proposal |
|---|---|---|---|
| **Geography / contiguity** | Positive in 16 of 17 studies that test it; 1 partial null (D'Angelo: latent space only partly geographic). Sign test p = 3e-5 (non-independent samples, see §5) | Gleyze 2011 (over-votes go to neighbours); Gustar 2023 (T weight ×2.4, J ×1.22); Mantzaris 2018; Schoenberg 2025 (proximity dominates); Spierdijk 2009 (bias exists but not uniform block voting) | RQ1 border hypothesis is well supported. **Novelty lies in effect size by vote type and by dyad, not in existence.** 5 countries have no voting neighbours (AUS, CYP, ISL, ISR, MLT [V]), so add a "region" label as well as a border label |
| **Culture / language / religion** | Positive; often absorbs "political" effects | Ginsburgh & Noury 2008; Spierdijk 2009 (geography, culture, language, religion, ethnicity); Felbermayr & Toubal 2010; Budzinski & Pannicke 2017 (bias persists even in a homogeneous national contest); Budzinski et al. 2023 (juror–performer similarity) | A border dummy will partly proxy language/culture. Report region and border together; do not interpret them causally (the proposal already avoids this) |
| **Diaspora / migration** | Positive in 4 of 5 studies; Schoenberg 2025 n.s. | Blangiardo & Baio 2014 (migration stocks +); Charron 2013 (diaspora effect, stronger with televote); Orgaz 2011 (enhanced by televote); Dekker 2021 (expatriate parameter) | Diaspora is the leading explanation for **televote-only** pair bias. It predicts RQ3 asymmetry: televote > jury for pairs like Ireland→Lithuania [grey] |
| **Political alignment** | Split: 4 positive or moderating vs 4 null | Null: Ginsburgh & Noury; Spierdijk; Schoenberg (diplomatic tensions); Brun & Boas (small). Positive/moderating: Clerides; Charron (impartiality moderates); Boulos [grey]; Acta Politica 2023 (populism) | Avoid "political voting" language; frame as affinity |
| **Jury vs televote (RQ3)** | **Televote bias > jury bias in 7 of 7 directional studies** (1 null on a non-bias estimand). Sign test p = 0.016. Counting the Maynooth contrarian claim as opposite gives 7 of 8, p = 0.070 | Gustar 2023: neighbour PL weight ×2.4 (T) vs ×1.22 (J); 71% vs 55%. García & Tanase: jury more quality-driven. Haan 2005: experts less affected by non-quality factors. JCE 2025: cultural diplomacy affects T, not J. Boulos [grey]: split-vote bias cases fewer than half the televote's. **Exceptions**: juries are still biased (Budzinski et al. 2023), and juries engage in strategic downgrading of competitors more than the public (Battiston 2025) | Prior expectation for RQ3: affinity pairs show **larger televote than jury surplus**, with a ratio of about 2 on Gustar's weight scale. But a jury-only **strategic negative** bias may show up for rival dyads. Song-level jury–televote agreement is only moderate (pooled r = 0.48, §5), so raw-point gaps must be normalised per channel |
| **Temporal dynamics (RQ2)** | Blocs grow from about 1995 (Gatherer) and are "persistent" (Yair & Maman; Łopatecki: blocs such as the Nordic persist through 2016–2025); polarisation spikes in 2010–11 (García & Tanase); Western dominance in the public vote declines (Łopatecki); 10 "stable" communities (Kotrotsiou) | Most temporal work uses combined votes before 2016. No study found reports pair-level year-to-year stability within the split era | RQ2 is a genuine gap at the dyad level. Expect bloc-level persistence and dyad-level volatility. With n ≤ 9 per dyad, stability metrics need uncertainty |
| **Bloc / community structure** | Recurrent: **Nordic** (Mantzaris, Łopatecki, AFP, Megatrend); **ex-Yugoslav/Balkan** (Gatherer, Megatrend, Groningen); **ex-USSR / Eastern** (AFP, Megatrend); **Baltic** (AFP; strong Baltic→Nordic flow); **Iberian/Romance** (Megatrend; Mantzaris cites Andorra–Spain [V, secondary]); **Greece–Cyprus** dyad (almost every source); historic Western/Northern/Mediterranean (Yair 1995; Yair & Maman 1996) | Community counts differ by method and window: 3 (Yair), 4 (Yair & Maman; Megatrend T 2016–19), 5 (García & Tanase 1997–2012), 10 (Kotrotsiou) | Use these as **face-validity targets** for the community detection. Report community-count sensitivity to resolution and edge thresholding |
| **Methods evolution** | 1995–2007 descriptive network and blocks → 2006–2018 simulation/resampling nulls → 2008–2014 econometric and multilevel with quality controls → 2014–2019 Bayesian hierarchical and latent-space network models → 2023–2026 split-vote PL/IRT quality models, juror-level panels, gravity PPML, temporal modularity | see §7 | The proposal's leave-one-out baseline matches Charron 2013 and Siganos & Tabner 2020 (2013/2020-era practice); FoF (2013) is close. The state of the art is quality-modelled, dependence-aware, and separates J and T |

---

## 5. Quantitative meta-analysis

### 5.1 Is study-level pooling defensible? **No, for the bias effects themselves.** Reasons:
1. **Non-independent samples.** Nearly every study reuses overlapping contest years. For example, 1975–2003 appears in at least Ginsburgh & Noury, Spierdijk & Vellekoop, Charron, García & Tanase and Mantzaris. Pooled SEs would be anti-conservative.
2. **Heterogeneous estimands** for "neighbour effect":
   - PL weight multipliers and pairwise probabilities (Gustar)
   - ordinal-logit structured effects (Blangiardo & Baio)
   - PPML elasticities (Schoenberg)
   - points per border (Parsons, grey)
   - A/E ratios (Gustar blog, grey)
3. **No SE/CI is accessible** for any peer-reviewed neighbour, diaspora or jury-vs-televote estimate. Only one grey source (Parsons) gives a ± value.
4. Fewer than 3 comparable verified estimates exist in any one metric.

**Decision.** For the bias effects, a structured direction-of-effect vote count (§4 and below) replaces pooling. A formal random-effects model is fitted only where the estimand is identical across units: the **GF song-level jury–televote Pearson correlation, one estimate per contest year, 2016–2025**. That is a year-level, single-source meta-analysis, not a study-level one. Its value is as a **prior and replication target for RQ3**.

### 5.2 Random-effects model: GF jury–televote agreement, 2016–2025 (k = 9 contests)

- Data: r by year from Table G [V, grey, computed from eurovisionworld tables].
- **Verified against the course dataset** (`meta_analysis/verify_jt_corr_from_data.py`, GD fork commit `1f39f6b`). All nine per-year r values reproduce to ±0.001 from `rounds/final.json`. The finalist counts n (26, and 25 in 2022 and 2024) are confirmed from the data, so the earlier [R] tag on n is resolved. Recomputed DL: pooled r = 0.476 (0.362–0.575), PI 0.323–0.604, I² = 2.1%, year trend p = 0.72.
- Fisher z, var = 1/(n−3). REML and DerSimonian–Laird, HKSJ CI, t-based 95% prediction interval. Cross-checked against statsmodels Paule–Mandel (pooled r = 0.475).

| Model | Pooled r | 95% CI | 95% CI (HKSJ) | 95% PI | τ² (z) | Q (df = 8), p | I² |
|---|---|---|---|---|---|---|---|
| REML | **0.475** | 0.361–0.576 | 0.340–0.592 | 0.319–0.607 | 0.0012 | 8.19, 0.415 | 2.3% |
| DL | 0.475 | 0.362–0.575 | 0.340–0.592 | 0.322–0.605 | 0.0010 | 8.19, 0.415 | 2.3% |

**Sensitivity.**
- Leave-one-out pooled r ranges from 0.449 (without 2017) to 0.509 (without 2025).
- All n = 25: r = 0.476, I² = 0%.
- Dropping 2025, the lowest year (r = 0.16): r = 0.509 (0.394–0.609).
- Sub-periods: 2016–19 r = 0.462 (0.281–0.612); 2021–25 r = 0.486 (0.315–0.627).
- Meta-regression on year: slope −0.010 z/yr (SE 0.023, p = 0.67), i.e. no detectable trend.
- **Overlap sensitivity** is not applicable, because the years are disjoint. The study-level overlap problem in 5.1 is the reason bias effects were not pooled.
- Caveat: one reader comment reports that dropping two top songs moved one year's r from 0.657 to 0.255 [V, grey]. Correlations are leverage-sensitive, so **replicate with Spearman and Kendall** from the raw JSON.

**Interpretation for RQ3.** Jury and televote agree only moderately on song strength (shared variance about 23%), and the agreement is stable across the split era (no heterogeneity, no trend). So a sizeable part of any pair's jury–televote gap is generic channel disagreement, not pair bias. **Compute pair surpluses within each channel**, then difference them.

### 5.3 Direction-of-effect vote count (study level; non-independence acknowledged)

| Hypothesis | + | 0 | − | Sign test (two-sided, directional only) |
|---|---|---|---|---|
| Geographic/neighbour bias > 0 | 16 | 1 | 0 | p = 3.1e-5 |
| Televote affinity bias > jury affinity bias | 7 | 1 | 0 | p = 0.016 (0.070 if the grey Maynooth claim counts as −) |
| Diaspora/migration effect > 0 | 4 | 1 | 0 | p = 0.125 |
| Independent political-alignment effect | 4 | 4 | 0 | p = 0.125 (evenly split) |

Study-to-hypothesis classifications are listed in `A_build_effects_and_meta.py`. These p-values assume independent studies, which is false because of shared years. Read them as consistency summaries, not inference.

---

## 6. Gap analysis

### What the literature has not done, and this project could credibly contribute
1. **Dyad-level bias estimated separately for jury and televote over the full 2016–2025 split era.** What exists instead:
   - Gustar 2023 is aggregate (all neighbour pairs, 2016–22).
   - Kadoić 2025 is song/ranking-level (2017–23).
   - Łopatecki 2025 is descriptive.
   - "Televoting Ties" covers CEE televote only.
   - Megatrend covers 2016–19 and is grey.
   - GD-2026 entries are visual, with findings not public.
2. **Within-dyad jury–televote divergence (RQ3).** Taking the same i→j pair, the question is how large the T-surplus minus J-surplus is and for which pairs. This was not found in any included study.
3. **Pair-level temporal stability (RQ2) in the split era.** Examples: dyad-surplus year-to-year rank correlation, ICC across 9 contests, persistence of the top-k pair set. Existing dynamic work uses combined votes and bloc-level communities.
4. **Uncertainty-aware pair rankings.** Shrinkage (empirical-Bayes or hierarchical) of 9-observation dyad means plus FDR control over about 1,000 dyads. Prior pair claims rest on uncorrected per-edge tests (Mantzaris) or no inference at all.
5. **Quality-conditional nulls in the split era.** Permute within voter-year while respecting the 12-10-8…1 allocation, the no-self-vote rule and receiver popularity. Uniform nulls are the norm (Gatherer, Mantzaris).
6. **Jury-specific negative or strategic dyads.** Battiston 2025 suggests jurors downgrade competitors. Pair-level negative jury surpluses for close rivals have not been mapped.
7. **Rule-change robustness.** None found addresses 2023-onward changes (televote-only semi-finals, rest-of-world vote [V, grey]) or the 2026 change capping votes per payment method from 20 to 10 [V] at the dyad level.

### Prior findings to replicate as sanity checks (only those seen in sources)
- **Greece↔Cyprus mutual surplus in both channels.** Sources: Mantzaris 2018; Gatherer coverage; Euronews 9.7 and 10.7 means for 1975–2003; 2017 jury 12s both ways [grey].
- **Nordic within-bloc surplus**; **Baltic→Nordic** flow. Sources: Mantzaris; Łopatecki; AFP 590 vs 306.
- **ex-Yugoslav/Balkan** and **Eastern/ex-USSR** communities in the televote. Sources: Gatherer; Megatrend 2016–19; Groningen.
- **Iberian/Romance** grouping, including Spain–Portugal and Andorra–Spain. The Andorra pair is historic only (pre-2010), so it is irrelevant for 2016–25 [R].
- **Romania→Moldova** surplus. Seen only in a secondary snippet attributed to a 1975–2017 bias analysis; treat as a hypothesis.
- **Neighbour effect larger in televote than jury**, roughly ×2.4 vs ×1.22 on the PL scale (Gustar 2023).
- **Song-level jury–televote r ≈ 0.48** (§5.2), with 2018 and 2025 as low years.
- **Ireland→Lithuania televote surplus** (anecdotal [grey]).
- **Large T–J gaps for specific receivers**: Israel 2024 (T 323 / J 52) and Ukraine 2022 (T 439 / J 192) [grey]. These are receiver-level shocks. Run with and without them, because they will dominate receiver-mean baselines.
- Pairs involving **Turkey**, e.g. Turkey–Azerbaijan and Germany→Turkey diaspora, cannot be replicated because Turkey is absent from 2016–2025 [R].

---

## 7. Methods the literature treats as state of the art, with recommended upgrades

> **Superseded where it conflicts:** the recommendations in this table are the literature view. The adopted design is in `04_study_design_v2.md`: M2 is primary, and the leave-one-out baseline is kept as a comparability reference, not as the primary metric.

| Problem | State-of-the-art approach (citation) | Concrete use in this project |
|---|---|---|
| Separate song quality from bias | Receiver-level quality via Plackett–Luce weights (Gustar 2023); Rasch partial-credit "cantobel" (Burgoyne et al. 2023); receiver random/fixed effects (Blangiardo & Baio 2014; Taylor et al. 2023); FoF quality-adjusted coefficient (García & Tanase 2013); average-points baseline (Charron 2013; Siganos & Tabner 2020) | Keep the leave-one-out baseline as the primary metric for comparability with Charron. Add a **rank-based** surplus (rank given vs receiver's leave-one-out mean rank) and an FoF-style normalised version |
| Ordinal / censored points (top-10 only) | Bayesian hierarchical **ordinal logistic** (Blangiardo & Baio 2014); exploded logit / PL for rankings (Gustar 2023; Burgoyne's exploded-logit [blog](https://illc-aml-web.science.uva.nl/blog/2021-05-22-eurovision/how-predictable-is-eurovision/)) | At least treat points as ordinal ranks in robustness checks. Juries rank all songs, while televote is aggregated top-10, which is a mechanical source of J–T gaps (Gustar) |
| Dyadic / network dependence | Sender/receiver random-effects network regression and restricted RE (Taylor, Keller & Fosdick 2023); latent space models for multiplex networks (D'Angelo et al. 2019; R `spaceNet`); gravity PPML with FE (Schoenberg 2025; JCE 2025; Felbermayr & Toubal 2010). QAP/MRQAP was **not found** in ESC work | The group-level permutation test is reasonable. Permute **within voter-year**, preserving the point vector and excluding self-votes. Optionally add a QAP-style row/column permutation of the region matrix |
| Null models for "collusion" | Rule-respecting Monte Carlo / resampling of point allocations (Gatherer 2006; Mantzaris et al. 2018) | Use a quality-weighted null: sample each voter's ranking with probability ∝ receiver popularity, not uniformly |
| Small n per dyad, many dyads | Hierarchical partial pooling (Blangiardo & Baio 2014; Spierdijk & Vellekoop multilevel 2009) | Report shrunken dyad means with intervals. If any pair is ranked, apply BH-FDR over dyads. The current plan of no per-pair significance is consistent with the literature's weaknesses |
| Communities and their dynamics | Signed weighted modularity on bias networks (García & Tanase 2013); temporal L-modularity / LAGO (arXiv 2605.24450, 2026); infomap, edge-betweenness and optimal clustering on max-point networks (Kotrotsiou 2026); multi-algorithm comparison (Svete & Hostnik 2020) | Run community detection on the **surplus (bias) network** separately for J and T, not on raw points. Report stability across resolutions and years (e.g., ARI between years) |
| Individual-level jury bias | Juror-level panel with juror characteristics (Budzinski, Gänßle & Weimar 2023; data public) | Optional extension: individual juror rankings exist from 2016 (MIRoVision [V]; ESC Insight says from 2014 [V]) |
| Non-ESC judging-bias analogues cited in ESC work | Zitzewitz 2006, nationalism in winter-sports judging, *J Econ Manage Strategy* 15:67–99 [V, cited by Spierdijk & Vellekoop]; scoping review of national bias in sports judging ([Saarland](https://jahrbib.sulb.uni-saarland.de/bitstream/20.500.11880/40955/1/National%20bias%20in%20international%20sports%20judging%20%20a%20scoping%20review.pdf)); FIFA award voting bias (Johnson & McCarthy 2022, *PLOS ONE* 17(7) e0270546 [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9278779/)) | Use for framing ("compensating vs reinforcing" judge bias; media voters less biased than captains) |

---

## 8. BibTeX (only fields seen in snippets; missing first names/authors left out deliberately)

```bibtex
@article{yair1995,author={Yair, Gad},title={'Unite Unite Europe': The political and cultural structures of Europe as reflected in the Eurovision Song Contest},journal={Social Networks},volume={17},number={2},pages={147--161},year={1995},doi={10.1016/0378-8733(95)00253-K}}
@article{yair1996,author={Yair, G. and Maman, D.},title={The persistent structure of hegemony in the Eurovision Song Contest},journal={Acta Sociologica},volume={39},number={3},pages={309--325},year={1996}}
@article{haan2005,author={Haan, Marco and Dijkstra, Gerhard and Dijkstra, Peter},title={Expert Judgment Versus Public Opinion -- Evidence from the Eurovision Song Contest},journal={Journal of Cultural Economics},volume={29},number={1},pages={59--78},year={2005},doi={10.1007/s10824-005-6830-0}}
@article{fenn2006,author={Fenn, Daniel and Suleman, Omer and Efstathiou, Janet and Johnson, Neil F.},title={How does Europe Make Its Mind Up? Connections, cliques, and compatibility between countries in the Eurovision Song Contest},journal={Physica A},volume={360},number={2},pages={576--598},year={2006},doi={10.1016/j.physa.2005.06.051},eprint={physics/0505071}}
@article{gatherer2006,author={Gatherer, Derek},title={Comparison of Eurovision Song Contest Simulation with Actual Results Reveals Shifting Patterns of Collusive Voting Alliances},journal={Journal of Artificial Societies and Social Simulation},volume={9},number={2},pages={1},year={2006},url={https://www.jasss.org/9/2/1.html}}
@article{saavedra2007,author={Saavedra, Serguei and Efstathiou, Janet and Reed-Tsochas, Felix},title={Identifying the underlying structure and dynamic interactions in a voting network},journal={Physica A},volume={377},pages={672--688},year={2007},doi={10.1016/j.physa.2006.11.038},eprint={physics/0605253}}
@article{dekker2008,author={Dekker, Anthony},title={The Eurovision Song Contest as a 'Friendship' Network},journal={Connections},volume={28},number={1},pages={59},year={2008}}
@article{ginsburgh2008,author={Ginsburgh, Victor and Noury},title={The Eurovision Song Contest. Is voting political or cultural?},journal={European Journal of Political Economy},volume={24},number={1},pages={41--52},year={2008},doi={10.1016/j.ejpoleco.2007.05.004}}
@article{spierdijk2009,author={Spierdijk, Laura and Vellekoop, Michel},title={The structure of bias in peer voting systems: lessons from the Eurovision Song Contest},journal={Empirical Economics},volume={36},number={2},pages={403--425},year={2009},doi={10.1007/s00181-008-0202-5}}
@article{felbermayr2010,author={Felbermayr, Gabriel and Toubal, Farid},title={Cultural proximity and trade},journal={European Economic Review},volume={54},number={2},pages={279--293},year={2010}}
@article{gleyze2011,author={Gleyze, Jean-Fran{\c{c}}ois},title={L'impact du voisinage g{\'e}ographique des pays dans l'attribution des votes au Concours Eurovision de la Chanson},journal={Cybergeo},year={2011},doi={10.4000/cybergeo.23451}}
@inproceedings{belloorgaz2011,author={Bello-Orgaz, Gema and Caj{\'i}as, Ra{\'u}l and Camacho, David},title={A study on the impact of crowd-based voting schemes in the 'Eurovision' European contest},booktitle={International Conference on Web Intelligence, Mining and Semantics (WIMS 2011)},year={2011},doi={10.1145/1988688.1988718}}
@article{clerides2012,author={Clerides, Sofronis and Stengos, Thanasis},title={Love thy Neighbour, Love thy Kin: Strategy and Bias in the Eurovision Song Contest},journal={Ekonomia},volume={15},number={1},year={2012},note={pages reported as 22--44 or 1--44}}
@article{charron2013,author={Charron, Nicholas},title={Impartiality, friendship-networks and voting behavior: Evidence from voting patterns in the Eurovision Song Contest},journal={Social Networks},volume={35},number={3},pages={484--497},year={2013},doi={10.1016/j.socnet.2013.05.005}}
@article{garcia2013,author={Garc{\'i}a, David and Tanase, Dorian},title={Measuring cultural dynamics through the Eurovision Song Contest},journal={Advances in Complex Systems},volume={16},number={8},pages={1350037},year={2013},doi={10.1142/S0219525913500379},eprint={1301.2995}}
@article{blangiardo2014,author={Blangiardo, Marta and Baio, Gianluca},title={Evidence of bias in the Eurovision song contest: modelling the votes using Bayesian hierarchical models},journal={Journal of Applied Statistics},volume={41},number={10},pages={2312--2322},year={2014},doi={10.1080/02664763.2014.909792}}
@article{budzinski2017jce,author={Budzinski, Oliver and Pannicke, Julia},title={Culturally biased voting in the Eurovision Song Contest: Do national contests differ?},journal={Journal of Cultural Economics},volume={41},number={4},pages={343--378},year={2017},doi={10.1007/s10824-016-9277-6}}
@article{budzinski2017conv,author={Budzinski, Oliver and Pannicke, Julia},title={Do preferences for pop music converge across countries? -- Empirical evidence from the Eurovision Song Contest},year={2017},doi={10.1080/17510694.2017.1332451}}
@article{antipov2017,author={Antipov and Pokryshevskaya},title={Order effects in the results of song contests: Evidence from the Eurovision and the New Wave},journal={Judgment and Decision Making},volume={12},number={4},pages={415--419},year={2017}}
@article{stockemer2018,author={Stockemer, Daniel and Blais, Andr{\'e} and Kostelka, Filip and Chhim, Chris},title={Voting in the Eurovision Song Contest},journal={Politics},volume={38},number={4},pages={428--442},year={2018},doi={10.1177/0263395717737887}}
@article{mantzaris2018jasss,author={Mantzaris, Alexander V. and Rein, Samuel R. and Hopkins, Alexander D.},title={Examining collusion and voting biases between countries during the Eurovision Song Contest since 1957},journal={Journal of Artificial Societies and Social Simulation},volume={21},number={1},pages={1},year={2018},doi={10.18564/jasss.3580}}
@article{mantzaris2018jcss,author={Mantzaris, Alexander V. and Hopkins, Alexander D. and Rein, Samuel R.},title={Preference and neglect amongst countries in the Eurovision Song Contest},journal={Journal of Computational Social Science},volume={1},pages={377--390},year={2018},doi={10.1007/s42001-018-0020-2}}
@article{dangelo2019,author={D'Angelo, Silvia and Murphy, Thomas Brendan and Alf{\`o}, Marco},title={Latent space modelling of multidimensional networks with application to the exchange of votes in Eurovision Song Contest},journal={Annals of Applied Statistics},volume={13},number={2},pages={900--930},year={2019},doi={10.1214/18-AOAS1221}}
@article{yair2019,author={Yair, Gad},title={Douze point: Eurovisions and Euro-Divisions in the Eurovision Song Contest -- Review of two decades of research},journal={European Journal of Cultural Studies},volume={22},number={5-6},pages={1013--1029},year={2019}}
@misc{svete2020,author={Svete, Anej and Hostnik, Jakob},title={It is not just about the Melody: How Europe Votes for its Favorite Songs},year={2020},eprint={2002.06609},archivePrefix={arXiv},note={Slovenian version with L. {\v{S}}ubelj in Uporabna informatika XXVIII(2)}}
@article{siganos2020,author={Siganos, Antonios and Tabner, Isaac T.},title={Capturing the role of societal affinity in cross-border mergers with the Eurovision Song Contest},journal={Journal of International Business Studies},volume={51},number={2},pages={263--273},year={2020},doi={10.1057/s41267-019-00271-3}}
@inproceedings{dekker2021,author={Dekker, A. H.},title={Understanding Eurovision tele-voting through modelling},booktitle={24th International Congress on Modelling and Simulation (MODSIM 2021)},address={Sydney},year={2021}}
@article{ginsburgh2023,author={Ginsburgh, Victor and Moreno-Ternero},title={The Eurovision Song Contest: voting rules, biases and rationality},journal={Journal of Cultural Economics},volume={47},pages={247--277},year={2023},doi={10.1007/s10824-022-09456-5}}
@article{gustar2023,author={Gustar, Andrew},title={Eurovision voting: a game of two halves},journal={Significance},volume={20},number={2},pages={6--10},year={2023},doi={10.1093/jrssig/qmad022}}
@techreport{budzinski2023,author={Budzinski, Oliver and G{\"a}n{\ss}le, Sophia and Weimar, Daniel},title={Disentangling individual biases in jury voting: An empirical analysis of voting behavior in the Eurovision Song Contest},institution={TU Ilmenau},type={Ilmenau Economics Discussion Paper},number={171},year={2023}}
@article{poppopulism2023,title={Pop populism: ethno-traditionalism beyond national borders and the populist radical right},journal={Acta Politica},volume={58},pages={737--760},year={2023},doi={10.1057/s41269-022-00262-7},note={authors not verified}}
@misc{taylor2023,author={Taylor, Ian and Keller, Kayleigh P. and Fosdick, Bailey K.},title={Restricted Regression in Networks},year={2023},eprint={2311.18039},archivePrefix={arXiv}}
@inproceedings{burgoyne2023,author={Burgoyne, John Ashley and Spijkervet and Baker},title={Measuring the Eurovision Song Contest: A Living Dataset for Real-World MIR},booktitle={Proceedings of ISMIR 2023},pages={817--823},year={2023}}
@article{giofre2024,author={Giofr{\'e}, Maela},title={Foreign Portfolio Investments and Voting Bias in the European Song Contest},year={2024}}
@article{kadoic2025,author={Kado{\'i}{\'c}, Nikola and {\v{Z}}ajdela Hrustek, Nikolina and Gligora Markovi{\'c}, Maja},title={Eurovision Song Contest: Can juries assess the quality of songs objectively?},journal={Central European Journal of Operations Research},volume={33},number={3},year={2025},doi={10.1007/s10100-025-00971-2}}
@article{schoenberg2025,author={Schoenberg, Alina M. and Ierapetritis, Dimitrios G. and Foramitti, Chiara and Schwand, Christopher},title={Economic and political dependencies in cultural voting: A gravity model analysis of Eurovision},journal={Romanian Journal of Regional Science},volume={19},number={1},pages={1--19},year={2025}}
@article{jce2025culturaldiplomacy,title={The impact of cultural diplomacy on the Eurovision song contest},journal={Journal of Cultural Economics},volume={49},number={4},year={2025},doi={10.1007/s10824-025-09541-5},note={authors not verified}}
@techreport{battiston2025,author={Battiston, Pietro and Magnani, Marco and Paolini, Dimitri and Rossi, Luca},title={Country Music: Positional Voting and Strategic Behavior},institution={University of Pisa, Department of Economics and Management},type={Discussion Paper},number={2025/322},year={2025}}
@article{lopatecki2025,author={{\L}opatecki, Karol},title={O nas przez muzyk{\k{e}} -- wyniki Eurowizji w latach 2016--2025 w uj{\k{e}}ciu kwantytatywnym},journal={Textus et Studia},volume={11},number={4},pages={135--164},year={2025}}
@article{brunboas,author={Brun, Estelle and Boas, Taylor},title={Does politics drive cultural preferences? Voting behavior in the Eurovision Song Contest},journal={European Political Science Review},note={year not verified (press coverage 2026)}}
@article{televotingties2026,title={Televoting Ties: Reciprocity Among Central and Eastern European Countries in the Context of the Eurovision Song Contest},journal={Pami{\k{e}}tnik Teatralny},volume={75},number={3},year={2026},note={author not verified}}
@incollection{kotrotsiou2026,author={Kotrotsiou and Hanias and Stavrinides},title={Applying Social Network Analysis to the Eurovision Song Contest},publisher={Springer},year={2026},doi={10.1007/978-3-032-09101-7_34}}
@misc{lmodularity2026,title={Generalized L-Modularity for Community Detection Beyond Simple Temporal Networks},year={2026},eprint={2605.24450},archivePrefix={arXiv},note={authors not verified}}
@inproceedings{somojirao2026,author={Somoji Rao, Charan Kumar Kharade and Baur, Melanie and Krone, Michael},title={Eurovision Song Contest Voting Communities},booktitle={34th International Symposium on Graph Drawing and Network Visualization (GD 2026)},series={LIPIcs},year={2026},doi={10.4230/LIPIcs.GD.2026.39}}
@inproceedings{dibartolomeo2026,author={Di Bartolomeo, Sara and F{\"o}rster, Henry and Terziadis, Soeren and Wulms, Jules},title={Graph Drawing Contest Report},booktitle={34th International Symposium on Graph Drawing and Network Visualization (GD 2026)},series={LIPIcs},volume={396},pages={38:1--38:11},year={2026},doi={10.4230/LIPIcs.GD.2026.38},note={one snippet gives volume 395}}
```
