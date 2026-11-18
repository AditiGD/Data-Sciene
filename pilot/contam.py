import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from esc_models import *
df = pd.read_csv('long.csv'); cov = pd.read_csv('dyad_covariates.csv').set_index(['voter','receiver'])
base = df[(df.year <= 2025) & (df.voter != 'WLD') & (df.flag_substitute_jury == 0)]
des = Design(base)
r0 = m0_loo(des); rfe = m1_fit(des, lam={'J':1e-6,'T':1e-6}, iters=3000)
d = pd.DataFrame({'voter':[x[1] for x in des.dyads],'receiver':[x[2] for x in des.dyads],'vt':des.d_vtype,'M0':r0['est'],'FE':rfe['est'],'n':des.nobs_d})
d = d[d.n>0].join(cov, on=['voter','receiver'])
for k in ['bloc_exYU','bloc_exUSSR','bloc_Nordic','border']:
    g = d.groupby(k)[['M0','FE']].mean()
    print(k, g.round(2).to_dict('index'))
print('overall sd', d[['M0','FE']].std().round(2).to_dict())
# selection: pairs with no final obs, and share of obs from semis
fin = base[base['round']=='F'].groupby(['voter','receiver']).size()
allp = base.groupby(['voter','receiver']).size()
print('pairs observed only in semis', int((~allp.index.isin(fin.index)).sum()), 'of', len(allp))
# fraction of receiver-years in finals among countries that entered semis (qualification) by receiver
q = base[base['round']!='F'].drop_duplicates(['year','receiver']).groupby('receiver').qualified.agg(['mean','size'])
print('qualification rate range', q['mean'].min(), q['mean'].max(), 'n semis', q['size'].sum())
