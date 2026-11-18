"""Models for dyadic favouritism in ESC ballots.

M0  proposal baseline: points minus receiver's leave-one-out mean (same year/round/vote type), averaged per pair.
M1  linear crossed model: points = q[receiver,year,round,type] + b[voter,receiver,type] + e, ridge (Gaussian prior) on b,
    variance ratio by empirical Bayes (split-half moment estimator of var(b)).
M2  top-10 rank-ordered logit (Plackett-Luce) with eta = q[receiver,year,round,type] + b[voter,receiver,type],
    Gaussian prior b ~ N(0, s2[type]) with s2 by EM/empirical Bayes (Laplace), MAP via L-BFGS, Laplace diagonal SEs.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

PTS2RANK = {12: 1, 10: 2, 8: 3, 7: 4, 6: 5, 5: 6, 4: 7, 3: 8, 2: 9, 1: 10}
RANK2PTS = np.array([12, 10, 8, 7, 6, 5, 4, 3, 2, 1])


class Design:
    """Index the long table. dkey/qkey are fixed universes so that estimates from different
    subsets are aligned (pass `dyads`, a list of (vtype, voter, receiver))."""

    def __init__(self, df, dyads=None):
        df = df.copy()
        df['bal'] = df.groupby(['year', 'round', 'vtype', 'voter'], sort=True).ngroup()
        df['qk'] = df.groupby(['year', 'round', 'vtype', 'receiver'], sort=True).ngroup()
        if dyads is None:
            dyads = sorted(set(zip(df.vtype, df.voter, df.receiver)))
        self.dyads = list(dyads)
        dmap = {d: i for i, d in enumerate(self.dyads)}
        df['dk'] = [dmap[t] for t in zip(df.vtype, df.voter, df.receiver)]
        df = df.sort_values(['bal', 'receiver']).reset_index(drop=True)
        df['col'] = df.groupby('bal').cumcount()
        self.df = df
        self.B = df.bal.max() + 1
        self.M = df.col.max() + 1
        self.nq = df.qk.max() + 1
        self.nd = len(self.dyads)
        B, M = self.B, self.M
        self.qidx = np.zeros((B, M), int)
        self.didx = np.zeros((B, M), int)
        self.mask = np.zeros((B, M), bool)
        self.pts = np.zeros((B, M), int)
        self.qidx[df.bal, df.col] = df.qk
        self.didx[df.bal, df.col] = df.dk
        self.mask[df.bal, df.col] = True
        self.pts[df.bal, df.col] = df.points
        # order[b, k] = column holding rank k+1
        self.order = np.zeros((B, 10), int)
        top = df[df.points > 0]
        rk = top.points.map(PTS2RANK).values - 1
        self.order[top.bal.values, rk] = top.col.values
        assert (np.bincount(top.bal.values, minlength=B) == 10).all(), 'every ballot must have 10 ranked entries'
        bal_info = df.drop_duplicates('bal').sort_values('bal')
        self.bal_vtype = bal_info.vtype.values
        self.bal_year = bal_info.year.values
        self.bal_round = bal_info['round'].values
        self.bal_voter = bal_info.voter.values
        self.d_vtype = np.array([d[0] for d in self.dyads])
        self.nobs_d = np.bincount(df.dk, minlength=self.nd)
        # row-level arrays for linear models
        self.y = df.points.values.astype(float)
        self.rq = df.qk.values
        self.rd = df.dk.values
        self.rbal = df.bal.values

    def with_points(self, pts):
        """Return a shallow copy of the design with simulated points matrix (B x M)."""
        import copy
        d = copy.copy(self)
        d.pts = pts
        order = np.zeros((self.B, 10), int)
        for k, p in enumerate(RANK2PTS):
            r, c = np.nonzero((pts == p) & self.mask)
            order[r, k] = c
        d.order = order
        d.y = pts[self.df.bal.values, self.df.col.values].astype(float)
        return d


# ---------------------------------------------------------------- M0: proposal baseline
def m0_loo(des):
    """Per-row residual: points - mean of points to the same receiver from all other voters in that ballot set."""
    y = des.y
    s = np.bincount(des.rq, y, minlength=des.nq)
    n = np.bincount(des.rq, minlength=des.nq)
    loo = (s[des.rq] - y) / np.maximum(n[des.rq] - 1, 1)
    r = y - loo
    cnt = np.bincount(des.rd, minlength=des.nd)
    est = np.bincount(des.rd, r, minlength=des.nd) / np.maximum(cnt, 1)
    est[cnt == 0] = np.nan
    # naive per-pair t statistic (what a student would do): mean / (sd/sqrt(n))
    ss = np.bincount(des.rd, r ** 2, minlength=des.nd)
    var = (ss - cnt * np.nan_to_num(est) ** 2) / np.maximum(cnt - 1, 1)
    t = est / np.sqrt(np.maximum(var, 1e-9) / np.maximum(cnt, 1))
    t[cnt < 2] = np.nan
    hi = np.bincount(des.rd, (y >= 8).astype(float), minlength=des.nd)  # count of 8+ points
    return dict(est=est, t=t, n=cnt, n8=hi, resid=r)


# ---------------------------------------------------------------- M1: linear ridge crossed model
def m1_fit(des, lam=None, iters=300, tol=1e-8):
    y, rq, rd = des.y, des.rq, des.rd
    nq_cnt = np.bincount(rq, minlength=des.nq)
    nd_cnt = np.bincount(rd, minlength=des.nd)
    if lam is None:
        lam = m1_eb_lambda(des)
    lam_d = np.array([lam[v] for v in des.d_vtype]) if isinstance(lam, dict) else np.full(des.nd, lam)
    b = np.zeros(des.nd)
    for it in range(iters):
        q = np.bincount(rq, y - b[rd], minlength=des.nq) / np.maximum(nq_cnt, 1)
        bn = np.bincount(rd, y - q[rq], minlength=des.nd) / (nd_cnt + lam_d)
        if np.max(np.abs(bn - b)) < tol:
            b = bn
            break
        b = bn
    resid = y - q[rq] - b[rd]
    s2e = resid.var()
    se = np.sqrt(s2e / (nd_cnt + lam_d))
    return dict(est=b, q=q, se=se, lam=lam, n=nd_cnt)


def m1_eb_lambda(des):
    """Empirical-Bayes variance ratio per vote type: var(b) = cov of dyad mean residuals in odd vs even years
    (independent halves), var(e) = residual variance - var(b)."""
    y, rq, rd = des.y, des.rq, des.rd
    q = np.bincount(rq, y, minlength=des.nq) / np.maximum(np.bincount(rq, minlength=des.nq), 1)
    r = y - q[rq]
    yr = des.df.year.values
    out = {}
    for vt in np.unique(des.d_vtype):
        sel_d = des.d_vtype[rd] == vt
        means = []
        for half in (yr % 2 == 1, yr % 2 == 0):
            m = sel_d & half
            c = np.bincount(rd[m], minlength=des.nd)
            s = np.bincount(rd[m], r[m], minlength=des.nd)
            means.append((s / np.maximum(c, 1), c))
        ok = (means[0][1] > 0) & (means[1][1] > 0)
        s2b = max(np.cov(means[0][0][ok], means[1][0][ok])[0, 1], 1e-3)
        s2e = max(r[sel_d].var() - s2b, 1e-3)
        out[vt] = s2e / s2b
    return out


# ---------------------------------------------------------------- M2: Plackett-Luce top-10 with dyad effects
def pl_nll_grad(theta, des, prec_d, prec_q=1e-4, fixed_b=None, want_info=False):
    nq = des.nq
    q = theta[:nq]
    b = theta[nq:] if fixed_b is None else fixed_b
    eta = q[des.qidx] + b[des.didx]
    avail = des.mask.copy()
    rows = np.arange(des.B)
    nll = 0.0
    g_eta = np.zeros_like(eta)
    info = np.zeros_like(eta) if want_info else None
    for k in range(10):
        e = np.where(avail, eta, -np.inf)
        m = e.max(1)
        w = np.exp(e - m[:, None])
        Z = w.sum(1)
        p = w / Z[:, None]
        c = des.order[:, k]
        nll -= (eta[rows, c] - m - np.log(Z)).sum()
        g_eta += p
        g_eta[rows, c] -= 1.0
        if want_info:
            info += p * (1 - p)
        avail[rows, c] = False
    mk = des.mask
    gq = np.bincount(des.qidx[mk], g_eta[mk], minlength=nq) + prec_q * q
    nll += 0.5 * prec_q * (q ** 2).sum()
    if fixed_b is None:
        gb = np.bincount(des.didx[mk], g_eta[mk], minlength=des.nd) + prec_d * b
        nll += 0.5 * (prec_d * b ** 2).sum()
        g = np.concatenate([gq, gb])
    else:
        g = gq
    if want_info:
        return nll, g, np.bincount(des.didx[mk], info[mk], minlength=des.nd)
    return nll, g


def m2_fit(des, s2=None, em_iters=30, init=None, maxiter=2000, verbose=False, update='mackay', tol=0.01):
    """MAP fit. s2: dict vtype->prior variance of b, or None to estimate by EM (Laplace diag approx)."""
    vts = np.unique(des.d_vtype)
    est_s2 = s2 is None
    if est_s2:
        s2 = {v: 0.5 for v in vts}
    theta = np.zeros(des.nq + des.nd) if init is None else init.copy()
    n_em = em_iters if est_s2 else 1
    for it in range(n_em):
        prec_d = np.array([1.0 / s2[v] for v in des.d_vtype])
        res = minimize(pl_nll_grad, theta, args=(des, prec_d), jac=True, method='L-BFGS-B',
                       options=dict(maxiter=maxiter, gtol=1e-6))
        theta = res.x
        b = theta[des.nq:]
        _, _, info = pl_nll_grad(theta, des, prec_d, want_info=True)
        pvar = 1.0 / (info + prec_d)
        if est_s2:
            new = {}
            for v in vts:
                m = (des.d_vtype == v) & (des.nobs_d > 0)
                if update == 'em':
                    new[v] = float(np.mean(b[m] ** 2 + pvar[m]))
                else:  # MacKay fixed point: s2 = sum b^2 / sum(1 - pvar/s2)
                    gam = np.sum(1 - pvar[m] / s2[v])
                    new[v] = float(np.sum(b[m] ** 2) / max(gam, 1.0))
            if verbose:
                print('EM', it, {k: round(x, 4) for k, x in new.items()}, res.nit, res.fun)
            if max(abs(new[v] - s2[v]) / s2[v] for v in vts) < tol:
                s2 = new
                break
            s2 = new
    prec_d = np.array([1.0 / s2[v] for v in des.d_vtype])
    _, _, info = pl_nll_grad(theta, des, prec_d, want_info=True)
    sd = 1.0 / np.sqrt(info + prec_d)
    return dict(est=theta[des.nq:], q=theta[:des.nq], sd=sd, s2=s2, theta=theta, nll=res.fun, n=des.nobs_d)


def pl_loglik(des, q, b):
    """Log-likelihood of observed top-10 orderings (no penalty)."""
    nll, _ = pl_nll_grad(np.concatenate([q, b]), des, np.zeros(des.nd), prec_q=0.0)
    return -nll


def pl_fit_q_given_b(des, b, prec_q=1e-4):
    res = minimize(pl_nll_grad, np.zeros(des.nq), args=(des, None, prec_q, b), jac=True, method='L-BFGS-B',
                   options=dict(maxiter=2000, gtol=1e-6))
    return res.x, -res.fun


# ---------------------------------------------------------------- simulation of ballots
def simulate_points(des, q, b, rng, noise='gumbel'):
    eta = q[des.qidx] + b[des.didx]
    if noise == 'gumbel':
        u = eta + rng.gumbel(size=eta.shape)
    else:  # Thurstone, sd matched to Gumbel
        u = eta + rng.normal(scale=np.pi / np.sqrt(6), size=eta.shape)
    u[~des.mask] = -np.inf
    top = np.argsort(-u, axis=1)[:, :10]
    pts = np.zeros_like(des.pts)
    rows = np.arange(des.B)[:, None]
    pts[rows, top] = RANK2PTS[None, :]
    pts[~des.mask] = 0
    return pts


def combine_types(des, est, w=None):
    """Average J and T estimates per (voter, receiver); returns Series indexed by (voter, receiver)."""
    s = pd.DataFrame({'vtype': des.d_vtype, 'voter': [d[1] for d in des.dyads],
                      'receiver': [d[2] for d in des.dyads], 'est': est})
    return s.groupby(['voter', 'receiver']).est.mean()
