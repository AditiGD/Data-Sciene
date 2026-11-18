"""Build A_effects.csv (all extracted quantitative effects, verified from search snippets)
and run (i) a random-effects meta-analysis where pooling is defensible and
(ii) direction-of-effect vote counting where it is not.

Every number below was seen in a WebSearch snippet ([verified-snippet]) unless tagged
[unverified-recall]. n for Grand-Final finalists per year is [unverified-recall].
"""
import csv, math, json, os
import numpy as np
from scipy import stats, optimize

OUT = os.path.dirname(os.path.abspath(__file__))

rows = []
def add(study, effect_name, estimate, se_or_ci, unit, n, data_years, vote_type, source_tag, url):
    rows.append(dict(study=study, effect_name=effect_name, estimate=estimate, se_or_ci=se_or_ci,
                     unit=unit, n=n, data_years=data_years, vote_type=vote_type,
                     source_tag=source_tag, url=url))

G = "https://academic.oup.com/jrssig/article/20/2/6/7095712"
# --- Neighbour / contiguity effects (NOT poolable: different estimands, no SEs) ---
add("Gustar 2023 (Significance 20(2):6-10)", "neighbour_pairwise_preference_probability", 0.71, "not reported in accessible text",
    "P(neighbour song ranked above non-neighbour song)", "not reported in accessible text", "2016-2022", "televote", "[verified-snippet]", G)
add("Gustar 2023 (Significance 20(2):6-10)", "neighbour_PlackettLuce_weight_multiplier", 2.4, "reported as 'over 2.4' (lower bound)",
    "multiplicative PL weight", "not reported in accessible text", "2016-2022", "televote", "[verified-snippet]", G)
add("Gustar 2023 (Significance 20(2):6-10)", "neighbour_pairwise_preference_probability", 0.55, "not reported in accessible text",
    "P(neighbour song ranked above non-neighbour song), jurors bordering X but not Y", "not reported in accessible text", "2016-2022", "jury", "[verified-snippet]", G)
add("Gustar 2023 (Significance 20(2):6-10)", "neighbour_PlackettLuce_weight_multiplier", 1.22, "not reported in accessible text",
    "multiplicative PL weight (22% increase)", "not reported in accessible text", "2016-2022", "jury", "[verified-snippet]", G)
add("Gustar (blog, musichistorystats) 'Love thy neighbour'", "neighbour_points_actual_over_expected_Italy", 1.328, "not reported",
    "A/E ratio = 36/27.1 jury points from Italy's 5 neighbours", "5 voting countries", "not reported in accessible text", "jury",
    "[verified-snippet] grey", "https://musichistorystats.com/eurovision-love-thy-neighbour/")
add("Gustar (blog, musichistorystats) 'Love thy neighbour'", "neighbour_12pt_awards_actual_over_expected", 3.0, "not reported",
    "ratio: 9 observed 12-pt awards to neighbours vs 3 expected", "not reported", "not reported in accessible text", "televote",
    "[verified-snippet] grey", "https://musichistorystats.com/eurovision-love-thy-neighbour/")
P = "https://medium.com/@alexparsons/measuring-the-politics-eurovision-with-data-365f92c6d20e"
add("Parsons (blog) 'Measuring the politics of Eurovision with data'", "shared_border_extra_points", 1.9, "+/-0.245 (as reported; SE or CI not stated)",
    "points per dyad-contest", "all votes cast (n not reported)", "not reported in accessible text", "combined/unspecified", "[verified-snippet] grey", P)
add("Parsons (blog) 'Measuring the politics of Eurovision with data'", "points_per_degree_of_separation_removed", 0.39, "+/-0.068 (as reported)",
    "points per dyad-contest per border step", "not reported", "not reported in accessible text", "combined/unspecified", "[verified-snippet] grey", P)
# --- Descriptive dyad / bloc magnitudes ---
add("Euronews/AFP 2025 (nine editions)", "Baltic_to_Nordic_points_vs_Baltic_to_Baltic", 590/306, "not applicable (raw totals 590 vs 306)",
    "ratio of raw point totals (no quality baseline)", "nine editions", "not reported in accessible text", "combined/unspecified", "[verified-snippet] grey",
    "https://www.euronews.com/my-europe/2025/05/16/eurovision-here-are-the-contests-strongest-geopolitical-alliances-throughout-the-years")
add("Euronews 2012", "Greece_to_Cyprus_mean_points", 9.7, "not applicable", "mean points per contest", "not reported", "1975-2003", "combined (jury era + televote era)",
    "[verified-snippet] grey", "https://www.euronews.com/culture/2012/05/21/eurovision-the-great-voting-conspiracy")
add("Euronews 2012", "Cyprus_to_Greece_mean_points", 10.7, "not applicable", "mean points per contest", "not reported", "1975-2003", "combined (jury era + televote era)",
    "[verified-snippet] grey", "https://www.euronews.com/culture/2012/05/21/eurovision-the-great-voting-conspiracy")
add("ESC Insight 2018 (Human factor in juries)", "Greece_jury_points_from_Cyprus_share", 12/48, "not applicable", "share of Greece's jury points (12 of 48)", "1 final", "2017",
    "jury", "[verified-snippet] grey", "https://escinsight.com/2018/05/07/consider-the-human-factor-in-the-eurovision-juries/")
add("ESC Insight 2018 (Human factor in juries)", "Cyprus_jury_points_from_Greece_share", 12/36, "not applicable", "share of Cyprus's jury points (12 of 36)", "1 final", "2017",
    "jury", "[verified-snippet] grey", "https://escinsight.com/2018/05/07/consider-the-human-factor-in-the-eurovision-juries/")
# --- Reciprocity / strategic ---
add("Ruijter (EUR MSc thesis, Behavioural Economics)", "reciprocity_points_received_prev_year_on_points_given", 0.082, "reported as statistically significant; SE not in snippet",
    "regression coefficient (points)", "not reported", "not reported in accessible text", "not reported", "[verified-snippet] grey",
    "https://thesis.eur.nl/pub/52224/Ruijter-DHH-385582-MA-thesis-BehEc.pdf")
add("Stockemer, Blais, Kostelka & Chhim 2018 (Politics 38(4))", "share_strategic_votes", 0.11, "not reported", "share of viewer vote choices", "survey (n not in snippet)",
    "survey (year not in snippet)", "televote (survey of viewers)", "[verified-snippet]", "https://repository.essex.ac.uk/23757/")
add("Stockemer, Blais, Kostelka & Chhim 2018 (Politics 38(4))", "share_voting_neither_favourite_nor_likely_winner", 0.36, "not reported", "share of participants",
    "survey (n not in snippet)", "survey (year not in snippet)", "televote (survey of viewers)", "[verified-snippet]", "https://repository.essex.ac.uk/23757/")
# --- Jury vs televote ---
add("Boulos 2013 (Duke MA project)", "count_bias_cases_split_vote", 204, "not applicable", "number of detected bias cases; televote count > 2x (reported as 'less than half')",
    "not reported", "1989-2012 (split-vote subset years not in snippet)", "jury+televote split vs televote", "[verified-snippet] grey",
    "https://dukespace.lib.duke.edu/items/ed19fb6a-b074-4234-8106-53d19dfb2c0a")
SS = "https://successfulsoftware.net/tag/2025/"
GF_N = {2016: 26, 2017: 26, 2018: 26, 2019: 26, 2021: 26, 2022: 25, 2023: 26, 2024: 25, 2025: 26}  # [unverified-recall]
GF_R = {2016: 0.447, 2017: 0.656, 2018: 0.255, 2019: 0.441, 2021: 0.618, 2022: 0.467, 2023: 0.490, 2024: 0.627, 2025: 0.160}  # [verified-snippet]
for y, r in GF_R.items():
    add("Successful Software blog (from eurovisionworld.com tables)", "GF_song_level_jury_vs_televote_pearson_r", r, "not reported (derived: Fisher z SE=1/sqrt(n-3))",
        "Pearson r between songs' jury and televote totals", f"{GF_N[y]} finalists [unverified-recall]", str(y), "jury vs televote", "[verified-snippet] grey (r); n [unverified-recall]", SS)
add("ESC Insight 2019", "avg_spearman_jury_vs_televote_last_three_editions", 0.13, "not reported", "Spearman rho (estimand not fully clear from snippet)",
    "not reported", "three editions before 2019 (presumably 2016-2018)", "jury vs televote", "[verified-snippet] grey; estimand ambiguous",
    "https://escinsight.com/2019/03/31/eurovision-song-contest-new-voting-rules-presentation-televote-sequence/")
# --- Counts / structure ---
add("Kotrotsiou, Hanias & Stavrinides 2026 (Springer chapter)", "number_stable_voting_communities", 10, "not applicable", "communities", "not reported", "not reported in accessible text",
    "not reported", "[verified-snippet]", "https://link.springer.com/chapter/10.1007/978-3-032-09101-7_34")
add("Garcia & Tanase 2013 (ACS 16(8))", "number_communities_max_signed_modularity", 5, "not applicable", "communities (FoF network)", "not reported", "1997-2012",
    "combined", "[verified-snippet]", "https://arxiv.org/abs/1301.2995")
add("Yair 1995 (Social Networks 17(2))", "number_regional_blocs", 3, "not applicable", "blocs (Mediterranean, Western, Northern)", "22 of 24 countries", "1975-1992", "jury",
    "[verified-snippet] (via secondary snippet)", "https://bibsonomy.org/bibtex/2767a40e3f9b91986e83ac0f5ce8e23d9/plaufer")
add("Yair & Maman 1996 (Acta Sociologica 39(3))", "number_empirical_blocs", 4, "not applicable", "blocs", "not reported", "not reported in accessible text", "jury",
    "[verified-snippet]", "https://cris.huji.ac.il/en/publications/the-persistent-structure-of-hegemony-in-the-eurovision-song-conte/")

with open(os.path.join(OUT, "A_effects.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# ------------------------------------------------------------------
# (i) Random-effects meta-analysis: GF song-level jury-televote agreement, 2016-2025
# ------------------------------------------------------------------
def re_meta(y, v, method="REML"):
    y, v = np.asarray(y, float), np.asarray(v, float)
    k = len(y); w = 1 / v
    mu_fe = np.sum(w * y) / np.sum(w)
    Q = np.sum(w * (y - mu_fe) ** 2)
    C = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    tau2_dl = max(0.0, (Q - (k - 1)) / C)
    if method == "DL":
        tau2 = tau2_dl
    else:  # REML via 1-D optimisation of restricted log-likelihood
        def nll(t2):
            wi = 1 / (v + t2); mu = np.sum(wi * y) / np.sum(wi)
            return 0.5 * (np.sum(np.log(v + t2)) + np.log(np.sum(wi)) + np.sum(wi * (y - mu) ** 2))
        res = optimize.minimize_scalar(nll, bounds=(0, 10), method="bounded")
        tau2 = max(0.0, res.x)
    wi = 1 / (v + tau2)
    mu = np.sum(wi * y) / np.sum(wi); se = math.sqrt(1 / np.sum(wi))
    I2 = max(0.0, (Q - (k - 1)) / Q) if Q > 0 else 0.0
    # Hartung-Knapp-Sidik-Jonkman adjusted CI
    q_hk = np.sum(wi * (y - mu) ** 2) / (k - 1)
    se_hk = math.sqrt(max(q_hk, 1e-12) / np.sum(wi))
    tcrit = stats.t.ppf(0.975, k - 1)
    pi_t = stats.t.ppf(0.975, k - 2)
    pi = (mu - pi_t * math.sqrt(tau2 + se ** 2), mu + pi_t * math.sqrt(tau2 + se ** 2))
    return dict(k=k, mu=mu, se=se, ci=(mu - 1.96 * se, mu + 1.96 * se), ci_hksj=(mu - tcrit * se_hk, mu + tcrit * se_hk),
                tau2=tau2, Q=Q, Q_p=1 - stats.chi2.cdf(Q, k - 1), I2=I2, pi=pi, mu_fe=mu_fe)

z = lambda r: np.arctanh(r); iz = lambda x: float(np.tanh(x))
def summarize(res):
    return {"k": res["k"], "pooled_r": round(iz(res["mu"]), 3),
            "CI95_r": [round(iz(res["ci"][0]), 3), round(iz(res["ci"][1]), 3)],
            "CI95_r_HKSJ": [round(iz(res["ci_hksj"][0]), 3), round(iz(res["ci_hksj"][1]), 3)],
            "PI95_r": [round(iz(res["pi"][0]), 3), round(iz(res["pi"][1]), 3)],
            "tau2_z": round(res["tau2"], 4), "tau_z": round(math.sqrt(res["tau2"]), 3), "Q": round(res["Q"], 2),
            "Q_p": round(res["Q_p"], 4), "I2_pct": round(100 * res["I2"], 1), "FE_pooled_r": round(iz(res["mu_fe"]), 3)}

years = sorted(GF_R)
yz = np.array([z(GF_R[t]) for t in years]); vz = np.array([1 / (GF_N[t] - 3) for t in years])
out = {"primary_REML": summarize(re_meta(yz, vz, "REML")), "primary_DL": summarize(re_meta(yz, vz, "DL"))}
# leave-one-out
loo = {}
for i, t in enumerate(years):
    m = np.ones(len(years), bool); m[i] = False
    loo[str(t)] = summarize(re_meta(yz[m], vz[m], "REML"))["pooled_r"]
out["leave_one_out_REML_pooled_r"] = loo
# sensitivity: n=25 for all years; drop 2025 (lowest, newest rules); 2016-2019 vs 2021-2025 sub-periods
vz25 = np.array([1 / 22] * len(years))
out["sens_n25_REML"] = summarize(re_meta(yz, vz25, "REML"))
m = np.array([t != 2025 for t in years]); out["sens_drop2025_REML"] = summarize(re_meta(yz[m], vz[m], "REML"))
m1 = np.array([t <= 2019 for t in years]); out["sub_2016_2019_REML"] = summarize(re_meta(yz[m1], vz[m1], "REML"))
out["sub_2021_2025_REML"] = summarize(re_meta(yz[~m1], vz[~m1], "REML"))
# meta-regression on year (RE weights from primary REML tau2): temporal drift relevant to RQ2
tau2 = re_meta(yz, vz, "REML")["tau2"]; wv = 1 / (vz + tau2)
X = np.column_stack([np.ones(len(years)), np.array(years) - 2020])
W = np.diag(wv); beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ yz); cov = np.linalg.inv(X.T @ W @ X)
out["metareg_year_slope_z_per_year"] = {"slope": round(float(beta[1]), 4), "se": round(float(math.sqrt(cov[1, 1])), 4),
                                         "p": round(float(2 * (1 - stats.norm.cdf(abs(beta[1] / math.sqrt(cov[1, 1]))))), 3)}
# cross-check with statsmodels if available
try:
    from statsmodels.stats.meta_analysis import combine_effects
    cr = combine_effects(yz, vz, method_re="iterated")  # Paule-Mandel
    sm = cr.summary_frame()
    out["statsmodels_PM_check_pooled_r"] = round(iz(float(sm.loc["random effect", "eff"])), 3)
except Exception as e:  # pragma: no cover
    out["statsmodels_PM_check_pooled_r"] = f"unavailable: {e}"

# ------------------------------------------------------------------
# (ii) Direction-of-effect vote counting (study-level; classification documented in report)
# +1 = effect present in hypothesised direction, 0 = null / n.s., -1 = opposite
# ------------------------------------------------------------------
votecount = {
  "geography_or_neighbour_positive": {
    "+1": ["Yair1995", "Fenn2006", "Gatherer2006", "Spierdijk2009", "Ginsburgh2008", "Clerides2012", "Charron2013", "Blangiardo2014",
            "BudzinskiPannicke2017JCE", "Mantzaris2018", "Gleyze2011", "Svete2020", "Schoenberg2025", "Gustar2023", "Kotrotsiou2026", "SiganosTabner2020"],
    "0": ["DAngelo2019 (latent space only partially geographic)"], "-1": []},
  "televote_bias_greater_than_jury_bias": {
    "+1": ["Haan2005 (experts less affected by non-quality factors)", "GarciaTanase2013", "Gustar2023 (2.4x vs 1.22x)",
            "Boulos2013 (split vote <half televote bias cases)", "JCE2025 cultural diplomacy (+ televote, n.s. jury)",
            "Charron2013 (diaspora effect expected strongest with more televote; supported)", "Orgaz2011 (diaspora enhanced by televoting)"],
    "0": ["Kadoic2025 (no sig. jury-public difference in points; not a bias estimand)"],
    "-1": []},
  "diaspora_or_migration_positive": {
    "+1": ["Blangiardo2014", "Charron2013", "Orgaz2011", "Dekker2021"], "0": ["Schoenberg2025 (observable, n.s.)"], "-1": []},
  "political_alignment_independent_effect": {
    "+1": ["Clerides2012 (political factors significant)", "Boulos2013", "Charron2013 (impartiality moderates)", "PopPopulism2023 (PRR moderates)"],
    "0": ["Ginsburgh2008", "Spierdijk2009 (political no role per Blangiardo summary)", "Schoenberg2025 (diplomatic tensions no lasting impact)",
          "BrunBoas (survey: small effects)"], "-1": []},
}
vc_out = {}
for k_, d in votecount.items():
    pos, nul, neg = len(d["+1"]), len(d["0"]), len(d["-1"])
    # sign test among studies with a directional (non-null) result
    nd = pos + neg
    p_sign = stats.binomtest(pos, nd, 0.5).pvalue if nd > 0 else float("nan")
    vc_out[k_] = {"positive": pos, "null": nul, "negative": neg, "sign_test_p_two_sided": float(f"{p_sign:.3g}"),
                  "prop_positive_of_all": round(pos / (pos + nul + neg), 2)}
# sensitivity: count grey contrarian claims as opposite direction
pos=len(votecount["televote_bias_greater_than_jury_bias"]["+1"]); neg=1  # Maynooth/Kavanagh: "real political voting" with juries (grey)
vc_out["televote_gt_jury_SENS_with_Maynooth_as_negative"]={"positive":pos,"negative":neg,
   "sign_test_p_two_sided": float(f"{stats.binomtest(pos,pos+neg,0.5).pvalue:.3g}")}
vc_out["note_strategic_competitor_downgrading"]="Battiston et al. 2025: strategic downgrading of close competitors present in both jury and televote, 'particularly' jury -> opposite direction for THIS bias type (not affinity); not counted above"
out["vote_count"] = vc_out
with open(os.path.join(OUT, "A_meta_results.json"), "w") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
print("rows in A_effects.csv:", len(rows))
