"""Real-data pilot: M0 vs M1 vs M2 on ESC 2016-2025, stability, 2026 hold-out, RQ3, QAP/MRQAP, Leiden."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, time
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
from esc_models import *

T0 = time.time()
rng = np.random.default_rng(2026)
df = pd.read_csv('long.csv')
cov = pd.read_csv('dyad_covariates.csv')
base = df[(df.year <= 2025) & (df.voter != 'WLD') & (df.flag_substitute_jury == 0)]
DY = sorted(set(zip(base.vtype, base.voter, base.receiver)) | set(zip(df.vtype, df.voter, df.receiver)) - {d for d in set(zip(df.vtype, df.voter, df.receiver)) if d[1] == 'WLD'})
out = {}


def fit_all(sub, s2=None, lam=None):
    des = Design(sub, dyads=DY)
    r0 = m0_loo(des); r1 = m1_fit(des, lam=lam); r2 = m2_fit(des, s2=s2)
    res = {}
    for name, r in [('M0', r0), ('M1', r1), ('M2', r2)]:
        e = r['est'].copy()
        if name != 'M0':
            e[des.nobs_d == 0] = np.nan
        res[name] = e
    return des, res, r0, r1, r2


def comb(des, e):
    s = pd.DataFrame({'voter': [d[1] for d in des.dyads], 'receiver': [d[2] for d in des.dyads], 'e': e})
    return s.groupby(['voter', 'receiver']).e.mean()  # nan-skipping mean over J/T


# ------------------------------------------------------------------ full fit
des, res, r0, r1, r2 = fit_all(base)
S2 = r2['s2']
LAM = r1['lam']
out['s2_M2'] = {k: round(v, 3) for k, v in S2.items()}
out['lambda_M1'] = {k: round(float(v), 3) for k, v in r1['lam'].items()}
print('M2 prior var', S2, 'M1 lambda', r1['lam'])
C = {m: comb(des, res[m]) for m in res}
nobs = pd.Series(des.nobs_d, index=pd.MultiIndex.from_tuples([(d[1], d[2]) for d in des.dyads])).groupby(level=[0, 1]).sum()
tab = pd.DataFrame(C); tab['n'] = nobs.reindex(tab.index)
tab = tab[tab.n > 0]
# M2 posterior sd for combined = 0.5*sqrt(sdJ^2+sdT^2) (independent), J-only pairs -> sdJ
sd = pd.DataFrame({'voter': [d[1] for d in des.dyads], 'receiver': [d[2] for d in des.dyads], 'vt': des.d_vtype,
                   'sd': r2['sd'], 'n': des.nobs_d, 'b': r2['est']})
sdw = sd[sd.n > 0].pivot_table(index=['voter', 'receiver'], columns='vt', values='sd')
bw = sd[sd.n > 0].pivot_table(index=['voter', 'receiver'], columns='vt', values='b')
tab['M2_sd'] = (0.5 * np.sqrt(sdw['J'] ** 2 + sdw['T'] ** 2)).reindex(tab.index).fillna(sdw['T'].reindex(tab.index))
tab['M2_J'] = bw['J'].reindex(tab.index); tab['M2_T'] = bw['T'].reindex(tab.index)
tab['M2_sdJ'] = sdw['J'].reindex(tab.index); tab['M2_sdT'] = sdw['T'].reindex(tab.index)
from scipy.stats import norm
tab['M2_lfsr'] = norm.cdf(-np.abs(tab.M2 / tab.M2_sd))
tab['M2_p_pos'] = norm.cdf(tab.M2 / tab.M2_sd)
# 8+ count (proposal) over J+T ballots
d8 = pd.DataFrame({'voter': [d[1] for d in des.dyads], 'receiver': [d[2] for d in des.dyads], 'n8': r0['n8']}).groupby(['voter', 'receiver']).n8.sum()
tab['n8plus'] = d8.reindex(tab.index)
tab = tab.join(cov.set_index(['voter', 'receiver']))
tab.to_csv('real_pair_estimates.csv')
out['n_pairs'] = int(len(tab))
out['spearman_methods'] = {f'{a}-{b}': round(spearmanr(tab[a], tab[b]).statistic, 3) for a, b in [('M0', 'M1'), ('M0', 'M2'), ('M1', 'M2')]}
def jacc(a, b, k):
    A = set(a.nlargest(k).index); B = set(b.nlargest(k).index); return round(len(A & B) / len(A | B), 3)
out['top50_jaccard'] = {f'{a}-{b}': jacc(tab[a], tab[b], 50) for a, b in [('M0', 'M1'), ('M0', 'M2'), ('M1', 'M2')]}
# small-n representation in top lists
for m in ['M0', 'M1', 'M2']:
    tt = tab.nlargest(50, m)
    out[f'top50_{m}_median_n'] = float(tt.n.median()); out[f'top50_{m}_share_n_le4'] = round(float((tt.n <= 4).mean()), 3)
out['median_n_all'] = float(tab.n.median())
# n flagged by lfsr<0.05 ; positive
out['M2_flag_lfsr05_pos'] = int(((tab.M2_lfsr < 0.05) & (tab.M2 > 0)).sum())
out['M2_flag_lfsr05_neg'] = int(((tab.M2_lfsr < 0.05) & (tab.M2 < 0)).sum())
out['M2_expected_false_signs_among_pos_flags'] = round(float(tab.loc[(tab.M2_lfsr < 0.05) & (tab.M2 > 0), 'M2_lfsr'].sum()), 2)
# naive t-test BH on M0
from statsmodels.stats.multitest import multipletests
t0 = pd.Series(r0['t'], index=pd.MultiIndex.from_tuples([(d[1], d[2], d[0]) for d in des.dyads]))

# ------------------------------------------------------------------ points-equivalent of M2 top pairs
def points_uplift(v, j, nsim=2000):
    """Expected points v->j over v's observed ballots containing j: with fitted b vs b_vj set to 0."""
    ups = []
    for bi in np.nonzero(des.bal_voter == v)[0]:
        cols = np.nonzero(des.mask[bi])[0]
        dj = [c for c in cols if des.dyads[des.didx[bi, c]][2] == j]
        if not dj: continue
        cj = dj[0]
        eta = r2['q'][des.qidx[bi, cols]] + r2['est'][des.didx[bi, cols]]
        pos = list(cols).index(cj)
        res_ = []
        for e in (eta, np.where(np.arange(len(cols)) == pos, eta - r2['est'][des.didx[bi, cj]], eta)):
            u = e[None, :] + rng.gumbel(size=(nsim, len(cols)))
            rk = (-u).argsort(1).argsort(1)[:, pos]
            res_.append(np.where(rk < 10, RANK2PTS[np.minimum(rk, 9)], 0).mean())
        ups.append(res_[0] - res_[1])
    return float(np.mean(ups)) if ups else np.nan

top = tab.nlargest(15, 'M2').copy()
top['pts_uplift'] = [points_uplift(v, j) for v, j in top.index]
cols = ['n', 'n8plus', 'M0', 'M1', 'M2', 'M2_sd', 'M2_J', 'M2_T', 'pts_uplift', 'border', 'same_m49', 'shared_lang']
print(top[cols].round(2).to_string())
top[cols].round(3).to_csv('top15_M2.csv')
top0 = tab.nlargest(15, 'M0')
print(top0[cols[:8] + ['border']].round(2).to_string())
top0[['n', 'n8plus', 'M0', 'M1', 'M2', 'M2_sd', 'border']].round(3).to_csv('top15_M0.csv')
print('rank in M2 of M0 top-15:', [int((tab.M2 > tab.loc[i, 'M2']).sum()) + 1 for i in top0.index])
out['M2_rank_of_M0_top15'] = [int((tab.M2 > tab.loc[i, 'M2']).sum()) + 1 for i in top0.index]

# ------------------------------------------------------------------ stability: odd/even and early/late
def half_corr(sel_a, sel_b, label):
    da, ra, *_ = fit_all(base[sel_a(base)], s2=S2, lam=LAM)
    db, rb, *_ = fit_all(base[sel_b(base)], s2=S2, lam=LAM)
    o = {}
    for m in ['M0', 'M1', 'M2']:
        a = comb(da, ra[m]); b = comb(db, rb[m])
        j = pd.concat([a, b], axis=1).dropna()
        r = pearsonr(j.iloc[:, 0], j.iloc[:, 1]).statistic
        o[m] = dict(n_pairs=len(j), pearson=round(r, 3), spearman=round(spearmanr(j.iloc[:, 0], j.iloc[:, 1]).statistic, 3),
                    spearman_brown=round(2 * r / (1 + r), 3), top30_jacc=jacc(j.iloc[:, 0], j.iloc[:, 1], 30))
    # per vote type for M2
    for vt in ['J', 'T']:
        m = (da.d_vtype == vt) & (da.nobs_d > 0) & (db.nobs_d > 0)
        o[f'M2_{vt}'] = round(pearsonr(ra['M2'][m], rb['M2'][m]).statistic, 3)
        o[f'M0_{vt}'] = round(pearsonr(ra['M0'][m], rb['M0'][m]).statistic, 3)
    out[f'split_{label}'] = o
    print(label, o)

half_corr(lambda d: d.year % 2 == 1, lambda d: d.year % 2 == 0, 'odd_even')
half_corr(lambda d: d.year <= 2019, lambda d: d.year >= 2021, 'early_late')
# finals-only vs finals+semis agreement and finals-only split-half
fo = base[base['round'] == 'F']
half_corr(lambda d: (d.year % 2 == 1) & (d['round'] == 'F'), lambda d: (d.year % 2 == 0) & (d['round'] == 'F'), 'odd_even_finals_only')

# leave-one-year-out predictive gain (M2) and year-to-year correlations
years = sorted(base.year.unique())
loyo = {}
for y in years:
    tr = Design(base[base.year != y], dyads=DY); te = Design(base[base.year == y], dyads=DY)
    f = m2_fit(tr, s2=S2)
    _, ll = pl_fit_q_given_b(te, f['est']); _, ll0 = pl_fit_q_given_b(te, np.zeros(te.nd))
    loyo[int(y)] = round((ll - ll0) / te.B, 3)
out['M2_LOYO_dLL_per_ballot'] = loyo
print('LOYO', loyo)

# ------------------------------------------------------------------ 2026 hold-out
h = df[(df.year == 2026) & (df.voter != 'WLD')]
te = Design(h, dyads=DY)
ho = {}
for vt in ['J', 'T', 'all']:
    hh = h if vt == 'all' else h[h.vtype == vt]
    t_ = Design(hh, dyads=DY)
    _, ll = pl_fit_q_given_b(t_, r2['est']); _, ll0 = pl_fit_q_given_b(t_, np.zeros(t_.nd))
    # top-1 hit: does argmax of fitted eta equal the 12-point receiver
    qh, _ = pl_fit_q_given_b(t_, r2['est']); q0, _ = pl_fit_q_given_b(t_, np.zeros(t_.nd))
    hit = {}
    for nm, qq, bb in [('with_b', qh, r2['est']), ('no_b', q0, np.zeros(t_.nd))]:
        eta = np.where(t_.mask, qq[t_.qidx] + bb[t_.didx], -np.inf)
        hit[nm] = round(float((eta.argmax(1) == t_.order[:, 0]).mean()), 3)
    ho[vt] = dict(ballots=int(t_.B), dLL_per_ballot=round((ll - ll0) / t_.B, 3), top1_hit=hit)
# M0/M1 predictive: correlation of 2016-25 pair estimate with 2026 LOO residual
r0h = m0_loo(te)
for m in ['M0', 'M1', 'M2']:
    e = res[m]
    ok = (te.nobs_d > 0) & ~np.isnan(e)
    ho[f'corr_{m}_vs_2026_residual'] = round(pearsonr(e[ok], r0h['est'][ok]).statistic, 3)
out['holdout_2026'] = ho
print('holdout', ho)

# ------------------------------------------------------------------ RQ3: jury vs televote
countries = sorted(set(base.voter))
idx = {c: i for i, c in enumerate(countries)}
def mat(series):
    A = np.full((len(countries), len(countries)), np.nan)
    for (v, j), x in series.items():
        if v in idx and j in idx: A[idx[v], idx[j]] = x
    return A
J = mat(tab.M2_J.dropna()); Tm = mat(tab.M2_T.dropna())
def qap_corr(A, B, nperm=2000):
    ok = ~np.isnan(A) & ~np.isnan(B)
    r = np.corrcoef(A[ok], B[ok])[0, 1]
    n = A.shape[0]; cnt = 0
    for _ in range(nperm):
        p = rng.permutation(n); Bp = B[np.ix_(p, p)]; o = ~np.isnan(A) & ~np.isnan(Bp)
        cnt += np.corrcoef(A[o], Bp[o])[0, 1] >= r
    return round(r, 3), (cnt + 1) / (nperm + 1)
out['RQ3_corr_J_T_M2_QAP'] = qap_corr(J, Tm)
tab['gap_TJ'] = tab.M2_T - tab.M2_J
tab['gap_sd'] = np.sqrt(tab.M2_sdT ** 2 + tab.M2_sdJ ** 2)
g = tab.dropna(subset=['gap_TJ'])
out['RQ3_gap_lfsr05_count'] = int((norm.cdf(-np.abs(g.gap_TJ / g.gap_sd)) < 0.05).sum())
top_pairs = tab.nlargest(20, 'M2')
out['RQ3_top20_mean_gap_TJ'] = round(float(top_pairs.gap_TJ.mean()), 3)
out['RQ3_top20_share_T_gt_J'] = round(float((top_pairs.gap_TJ > 0).mean()), 3)
print('RQ3', out['RQ3_corr_J_T_M2_QAP'], out['RQ3_gap_lfsr05_count'])
gcols = ['n', 'M2_J', 'M2_sdJ', 'M2_T', 'M2_sdT', 'gap_TJ', 'gap_sd']
g.reindex(g.gap_TJ.abs().sort_values(ascending=False).index)[gcols].head(10).round(2).to_csv('rq3_top_gaps.csv')

# ------------------------------------------------------------------ group-level: border vs other
Y = mat(tab.M2.dropna()); Y0 = mat(tab.M0.dropna())
covm = {k: mat(cov.set_index(['voter', 'receiver'])[k]) for k in ['border', 'same_m49', 'shared_lang', 'bloc_exUSSR', 'bloc_exYU', 'bloc_Nordic', 'log_dist']}
def diff_stat(Y, X):
    ok = ~np.isnan(Y) & ~np.isnan(X)
    return Y[ok][X[ok] == 1].mean() - Y[ok][X[ok] == 0].mean()
def qap_diff(Y, X, nperm=5000):
    obs = diff_stat(Y, X); n = Y.shape[0]
    null_qap = np.array([diff_stat(Y, X[np.ix_(p, p)]) for p in (rng.permutation(n) for _ in range(nperm))])
    # naive: permute dyad labels ignoring node structure
    ok = ~np.isnan(Y) & ~np.isnan(X); y = Y[ok]; x = X[ok]
    null_naive = np.array([y[rng.permutation(len(x))][x == 1].mean() - y[x == 0].mean() for _ in range(nperm)])
    return dict(diff=round(obs, 3), p_qap=round(((null_qap >= obs).sum() + 1) / (nperm + 1), 4),
                p_naive=round(((null_naive >= obs).sum() + 1) / (nperm + 1), 4),
                sd_null_qap=round(null_qap.std(), 3), sd_null_naive=round(null_naive.std(), 3))
out['border_test_M2'] = qap_diff(Y, covm['border'])
out['border_test_M0'] = qap_diff(Y0, covm['border'])
out['same_m49_test_M2'] = qap_diff(Y, covm['same_m49'])
print('border', out['border_test_M2'], out['border_test_M0'])

def mrqap(Y, Xs, nperm=1000):
    names = list(Xs); n = Y.shape[0]
    off = ~np.eye(n, dtype=bool)
    ok = ~np.isnan(Y) & off
    for k in names: ok &= ~np.isnan(Xs[k])
    X = np.column_stack([np.ones(ok.sum())] + [Xs[k][ok] for k in names]); y = Y[ok]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    def tstat(X, y, col):
        b, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ b
        s2 = r @ r / (len(y) - X.shape[1]); V = s2 * np.linalg.inv(X.T @ X)
        return b[col] / np.sqrt(V[col, col])
    resd = {}
    full_off = off.copy()
    for k in Xs: full_off &= ~np.isnan(Xs[k])
    for ci, k in enumerate(names):
        others = [o for o in names if o != k]
        Xo = np.column_stack([np.ones(full_off.sum())] + [Xs[o][full_off] for o in others])
        bk, *_ = np.linalg.lstsq(Xo, Xs[k][full_off], rcond=None)
        E = np.full((n, n), np.nan); E[full_off] = Xs[k][full_off] - Xo @ bk
        t_obs = tstat(X, y, ci + 1)
        cnt = 0
        for _ in range(nperm):
            p = rng.permutation(n); Ep = E[np.ix_(p, p)]
            o2 = ok & ~np.isnan(Ep)
            Xp = np.column_stack([np.ones(o2.sum())] + [Xs[o][o2] for o in others] + [Ep[o2]])
            cnt += abs(tstat(Xp, Y[o2], Xp.shape[1] - 1)) >= abs(t_obs)
        resd[k] = dict(beta=round(beta[ci + 1], 3), t=round(t_obs, 2), p_dsp=round((cnt + 1) / (nperm + 1), 4))
    return resd, round(1 - ((y - X @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum(), 3)
mr, r2_ = mrqap(Y, covm)
out['MRQAP_M2'] = mr; out['MRQAP_M2_R2'] = r2_
print('MRQAP', mr, r2_)

# ------------------------------------------------------------------ network: Leiden on positive bias
import igraph as ig, leidenalg as la
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
def leiden_runs(Ymat, gammas=(0.5, 0.75, 1.0, 1.25, 1.5), seeds=50):
    W = np.where(np.isnan(Ymat), 0, np.maximum(Ymat, 0)); np.fill_diagonal(W, 0)
    g = ig.Graph.Weighted_Adjacency(W.tolist(), mode='directed', attr='weight', loops=False)
    resg = {}
    for gm in gammas:
        parts = []; Qs = []
        for s in range(seeds):
            p = la.find_partition(g, la.RBConfigurationVertexPartition, weights='weight', resolution_parameter=gm, seed=s)
            parts.append(np.array(p.membership)); Qs.append(p.quality())
        P = np.array(parts)
        # stability: mean pairwise ARI across seeds
        aris = [adjusted_rand_score(P[a], P[b]) for a in range(10) for b in range(a + 1, 10)]
        best = P[int(np.argmax(Qs))]
        mod = g.modularity(best.tolist(), weights='weight', directed=True)
        resg[gm] = dict(k=int(best.max() + 1), modularity=round(mod, 3), seed_ARI=round(float(np.mean(aris)), 3), best=best)
    return resg
lr = leiden_runs(Y)
m49 = [pd.Series(dict(zip(cov.voter, cov.voter))).index for _ in [0]]
from covariates import M49
lab = np.array([M49[c] for c in countries])
for gm, r in lr.items():
    r['NMI_vs_M49'] = round(normalized_mutual_info_score(lab, r['best']), 3)
# null: simulate ballots with b=0 (quality only), refit M2, run Leiden at gamma=1
nullmods = []
for rep in range(10):
    pts = simulate_points(des, r2['q'], np.zeros(des.nd), rng)
    dsim = des.with_points(pts)
    f = m2_fit(dsim, s2=S2)
    Yn = mat(comb(dsim, np.where(des.nobs_d > 0, f['est'], np.nan)).dropna())
    nullmods.append(leiden_runs(Yn, gammas=(1.0,), seeds=10)[1.0]['modularity'])
out['leiden'] = {str(k): {kk: vv for kk, vv in v.items() if kk != 'best'} for k, v in lr.items()}
out['leiden_null_modularity_gamma1'] = dict(mean=round(float(np.mean(nullmods)), 3), max=round(float(np.max(nullmods)), 3))
comm = {c: int(m) for c, m in zip(countries, lr[1.0]['best'])}
groups = {}
for c, m in comm.items(): groups.setdefault(m, []).append(c)
out['leiden_gamma1_communities'] = list(groups.values())
print('leiden', out['leiden'], out['leiden_null_modularity_gamma1'], groups)
# centrality: in/out strength of positive bias, PageRank
W = np.where(np.isnan(Y), 0, np.maximum(Y, 0)); np.fill_diagonal(W, 0)
g = ig.Graph.Weighted_Adjacency(W.tolist(), mode='directed', attr='weight', loops=False)
pr = g.pagerank(weights='weight')
cent = pd.DataFrame({'in_strength_pos': W.sum(0), 'out_strength_pos': W.sum(1), 'pagerank': pr}, index=countries)
cent.round(3).sort_values('in_strength_pos', ascending=False).to_csv('centrality_M2.csv')
out['top_in_strength'] = cent.in_strength_pos.nlargest(6).round(2).to_dict()
out['top_out_strength'] = cent.out_strength_pos.nlargest(6).round(2).to_dict()
out['runtime_s'] = round(time.time() - T0, 1)
json.dump(out, open('real_results.json', 'w'), indent=1, default=str)
print('done', out['runtime_s'])
