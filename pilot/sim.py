"""Planted-bias recovery simulation on the real ESC 2016-2025 design (real voters, real eligible sets).
DGP: top-10 ballots from eta = q_hat (fitted M2 quality, real data) + b_true; Gumbel (PL) or Gaussian (Thurstone) noise.
Compares M0 (proposal LOO baseline), M1 (linear ridge/EB), M2 (PL ridge/EB) for finals-only vs finals+semis."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, time
import numpy as np, pandas as pd
from multiprocessing import Pool
from scipy.stats import norm, t as tdist, spearmanr
from sklearn.metrics import roc_auc_score
from statsmodels.stats.multitest import multipletests
from esc_models import *

R = int(os.environ.get('NREP', 50))
K = 40
df = pd.read_csv('long.csv')
base = df[(df.year <= 2025) & (df.voter != 'WLD') & (df.flag_substitute_jury == 0)]
DES = Design(base)
DY = DES.dyads
FIT = m2_fit(DES)
Q, S2 = FIT['q'], FIT['s2']
PAIRS = sorted({(d[1], d[2]) for d, n in zip(DY, DES.nobs_d) if n > 0})
PIDX = {p: i for i, p in enumerate(PAIRS)}
d_pair = np.array([PIDX.get((d[1], d[2]), -1) for d in DY])
fin_pairs = {(d[1], d[2]) for d, n in zip(DY, Design(base[base['round'] == 'F'], dyads=DY).nobs_d) if n > 0}


def pair_vec(des, e, fill=0.0):
    s = pd.DataFrame({'p': d_pair, 'e': np.where(des.nobs_d > 0, e, np.nan)})
    v = s.groupby('p').e.mean().reindex(range(len(PAIRS)))
    return v.fillna(fill).values, v.isna().values


def m0_pooled_t(des, r0):
    rr = pd.DataFrame({'p': d_pair[des.rd], 'r': r0['resid']})
    g = rr.groupby('p').r.agg(['mean', 'std', 'size']).reindex(range(len(PAIRS)))
    t = g['mean'] / (g['std'] / np.sqrt(g['size']))
    p = 1 - tdist.cdf(t.values, df=np.maximum(g['size'].fillna(1).values - 1, 1))
    bad = ((g['size'] < 2) | g['std'].isna() | (g['std'] == 0)).values
    p[bad] = 1.0
    return np.nan_to_num(p, nan=1.0)


def one_rep(args):
    cfg, rep = args
    rng = np.random.default_rng(1000 * sum(map(ord, cfg['name'])) + rep)
    b = np.zeros(DES.nd)
    if cfg['background']:
        for vt in ('J', 'T'):
            m = DES.d_vtype == vt
            b[m] = rng.normal(scale=np.sqrt(S2[vt]), size=m.sum())
    planted = rng.choice(len(PAIRS), K, replace=False)
    pl_mask = np.isin(d_pair, planted)
    if cfg['types'] == 'both':
        b[pl_mask] += cfg['delta']
    else:
        b[pl_mask & (DES.d_vtype == 'T')] += cfg['delta']
    pts = simulate_points(DES, Q, b, rng, noise=cfg['noise'])
    sim = DES.df.copy(); sim['points'] = pts[sim.bal.values, sim.col.values]
    sim = sim[['year', 'round', 'vtype', 'voter', 'receiver', 'points']]
    truth = np.zeros(len(PAIRS)); truth[planted] = 1
    true_comb, _ = pair_vec(DES, b)
    out = []
    for scope in ('F', 'F+SF'):
        sub = sim[sim['round'] == 'F'] if scope == 'F' else sim
        des = Design(sub, dyads=DY)
        r0 = m0_loo(des); r1 = m1_fit(des); r2 = m2_fit(des, em_iters=12, tol=0.02)  # EB variance re-estimated each replicate
        ests = {'M0': r0['est'], 'M1': r1['est'], 'M2': r2['est']}
        if cfg['types'] == 'Tonly':  # RQ3 gap: T minus J per pair
            res = dict(cfg=cfg['name'], rep=rep, scope=scope)
            for m, e in ests.items():
                dfm = pd.DataFrame({'p': d_pair, 'vt': DES.d_vtype, 'e': np.where(des.nobs_d > 0, e, np.nan)})
                w = dfm.pivot_table(index='p', columns='vt', values='e').reindex(range(len(PAIRS)))
                gap = (w['T'] - w['J'])
                ok = gap.notna().values
                res[f'{m}_gapAUC'] = roc_auc_score(truth[ok], gap.values[ok]) if truth[ok].sum() > 0 else np.nan
                res[f'{m}_gap_recall@K'] = float(truth[np.argsort(-gap.fillna(-1e9).values)[:K]].sum() / K)
            res['n_pairs_with_gap'] = int(ok.sum())
            out.append(res); continue
        res = dict(cfg=cfg['name'], rep=rep, scope=scope)
        for m, e in ests.items():
            v, miss = pair_vec(des, e, fill=0.0)
            order = np.argsort(-v)
            res[f'{m}_AUC'] = roc_auc_score(truth, v)
            res[f'{m}_recall@K'] = truth[order[:K]].sum() / K
            fp = np.array([PAIRS[i] in fin_pairs for i in range(len(PAIRS))])
            res[f'{m}_recall@K_finalobs'] = truth[order[:K]][fp[order[:K]]].sum() / max(truth[fp].sum(), 1)
            res[f'{m}_spearman_true'] = spearmanr(v, true_comb).statistic
            tt = np.argsort(-true_comb)[:20]
            res[f'{m}_top20_overlap'] = len(set(order[:20]) & set(tt)) / 20
        # inference: M2 lfsr / BH on posterior z ; M0 naive t-test + BH
        v2, _ = pair_vec(des, r2['est'])
        sdd = pd.DataFrame({'p': d_pair, 'vt': DES.d_vtype, 'sd': np.where(des.nobs_d > 0, r2['sd'], np.nan)})
        sw = sdd.pivot_table(index='p', columns='vt', values='sd').reindex(range(len(PAIRS)))
        sdc = (0.5 * np.sqrt(sw['J'] ** 2 + sw['T'] ** 2)).fillna(sw['T'] if 'T' in sw else np.nan).fillna(1e3).values
        z = v2 / sdc
        lfsr = norm.cdf(-np.abs(z))
        flag = (lfsr < 0.05) & (v2 > 0)
        res['M2_lfsr_power'] = flag[truth == 1].mean(); res['M2_lfsr_FDP'] = (flag & (truth == 0)).sum() / max(flag.sum(), 1)
        res['M2_lfsr_nflag'] = int(flag.sum())
        strong = true_comb > 1.0
        res['M2_lfsr_false_sign_rate'] = (flag & (true_comb <= 0)).sum() / max(flag.sum(), 1)
        res['M2_lfsr_power_true_gt1'] = flag[strong].mean() if strong.any() else np.nan
        pz = 1 - norm.cdf(z)
        rej = multipletests(pz, alpha=0.10, method='fdr_bh')[0]
        res['M2_BH_power'] = rej[truth == 1].mean(); res['M2_BH_FDP'] = (rej & (truth == 0)).sum() / max(rej.sum(), 1)
        lo, hi = v2 - 1.645 * sdc, v2 + 1.645 * sdc
        obs = sdc < 1e3
        res['M2_cover90'] = float(((true_comb >= lo) & (true_comb <= hi))[obs].mean())
        p0 = m0_pooled_t(des, r0)
        rej0 = multipletests(p0, alpha=0.10, method='fdr_bh')[0]
        res['M0t_BH_power'] = rej0[truth == 1].mean(); res['M0t_BH_FDP'] = (rej0 & (truth == 0)).sum() / max(rej0.sum(), 1)
        rawp = p0 < 0.05
        res['M0t_raw05_false_sign_rate'] = (rawp & (true_comb <= 0)).sum() / max(rawp.sum(), 1)
        res['M0t_raw05_power_true_gt1'] = rawp[strong].mean() if strong.any() else np.nan
        res['M0t_BH_false_sign_rate'] = (rej0 & (true_comb <= 0)).sum() / max(rej0.sum(), 1)
        res['M0t_raw05_power'] = rawp[truth == 1].mean(); res['M0t_raw05_FDP'] = (rawp & (truth == 0)).sum() / max(rawp.sum(), 1)
        res['s2_J'] = r2['s2']['J']; res['s2_T'] = r2['s2']['T']
        out.append(res)
    return out


def points_equiv(deltas, n_cells=400, nsim=3000, seed=1):
    """Average expected-points uplift in Grand Final ballots from adding delta to one receiver's utility."""
    rng = np.random.default_rng(seed)
    fb = np.nonzero(DES.bal_round == 'F')[0]
    res = {d: [] for d in deltas}
    for _ in range(n_cells):
        bi = rng.choice(fb); cols = np.nonzero(DES.mask[bi])[0]; pos = rng.integers(len(cols))
        eta = Q[DES.qidx[bi, cols]]
        g = rng.gumbel(size=(nsim, len(cols)))
        def ep(e):
            rk = (-(e[None, :] + g)).argsort(1).argsort(1)[:, pos]
            return np.where(rk < 10, RANK2PTS[np.minimum(rk, 9)], 0).mean()
        base_ = ep(eta)
        for d in deltas:
            e2 = eta.copy(); e2[pos] += d; res[d].append(ep(e2) - base_)
    return {str(d): round(float(np.mean(v)), 2) for d, v in res.items()}


if __name__ == '__main__':
    T0 = time.time()
    cfgs = [dict(name='S1_sparse_d1.0', background=False, delta=1.0, types='both', noise='gumbel'),
            dict(name='S1_sparse_d2.0', background=False, delta=2.0, types='both', noise='gumbel'),
            dict(name='S2_realbg_d1.0', background=True, delta=1.0, types='both', noise='gumbel'),
            dict(name='S2_realbg_d2.0', background=True, delta=2.0, types='both', noise='gumbel'),
            dict(name='S3_thurstone_realbg_d2.0', background=True, delta=2.0, types='both', noise='normal'),
            dict(name='S4_RQ3_Tonly_sparse_d2.0', background=False, delta=2.0, types='Tonly', noise='gumbel')]
    jobs = [(c, r) for c in cfgs for r in range(R)]
    with Pool(4) as pool:
        allres = [x for lst in pool.map(one_rep, jobs, chunksize=2) for x in lst]
    res = pd.DataFrame(allres)
    res.to_csv('sim_raw.csv', index=False)
    summ = res.groupby(['cfg', 'scope']).mean(numeric_only=True).drop(columns='rep')
    se = res.groupby(['cfg', 'scope']).sem(numeric_only=True).drop(columns='rep')
    summ.round(3).to_csv('sim_summary.csv'); se.round(3).to_csv('sim_se.csv')
    pd.set_option('display.width', 250)
    print(summ.round(3).T.to_string())
    pe = points_equiv([0.5, 1.0, 2.0, 3.0, float(np.sqrt(S2['J'])), float(np.sqrt(S2['T']))], n_cells=300, nsim=2000)
    print('points-equivalent (final ballots):', pe, 'S2', S2)
    json.dump(dict(points_equiv=pe, S2=S2, R=R, K=K, n_pairs=len(PAIRS), runtime=round(time.time() - T0, 1)),
              open('sim_meta.json', 'w'), indent=1)
    print('runtime', round(time.time() - T0, 1))
