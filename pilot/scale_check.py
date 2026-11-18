import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from esc_models import *
df = pd.read_csv('long.csv')
base = df[(df.year <= 2025) & (df.voter != 'WLD') & (df.flag_substitute_jury == 0)]
des = Design(base); r2 = m2_fit(des); r1 = m1_fit(des)
qk = des.df.drop_duplicates('qk').sort_values('qk')
qk['q'] = r2['q'][qk.qk.values]; qk['q1'] = r1['q'][qk.qk.values]
s = qk.groupby(['year', 'round', 'vtype']).agg(sd_q=('q', 'std'), sd_q_points=('q1', 'std')).reset_index()
print(s.groupby('vtype')[['sd_q', 'sd_q_points']].mean().round(3))
print(s[s['round']=='F'].pivot(index='year', columns='vtype', values='sd_q').round(2).T.to_string())
# M1 points-scale gap and bias sd
for vt in ['J','T']:
    m = (des.d_vtype == vt) & (des.nobs_d > 0)
    print(vt, 'M1 sd(b) points', r1['est'][m].std().round(3), 'M2 sd(b) logit', r2['est'][m].std().round(3),
          'ratio sd(b)/mean sd(q) M2', (r2['est'][m].std() / s[s.vtype==vt].sd_q.mean()).round(3),
          'M1', (r1['est'][m].std() / s[s.vtype==vt].sd_q_points.mean()).round(3))
# jury semis vs final scale (2016-22)
print(s.groupby(['vtype','round']).sd_q.mean().round(2))
