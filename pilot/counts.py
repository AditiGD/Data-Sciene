import pandas as pd, numpy as np, sys
df = pd.read_csv('long.csv')
df = df[(df.year <= 2025) & (df.voter != 'WLD')]
countries = sorted(set(df.voter) | set(df.receiver))
univ = [(a, b) for a in sorted(set(df.voter)) for b in sorted(set(df.receiver)) if a != b]
print('countries', len(countries), 'voters', df.voter.nunique(), 'receivers', df.receiver.nunique(), 'universe ordered pairs', len(univ))
def summ(sub, label):
    c = sub.groupby(['voter', 'receiver']).size()
    full = c.reindex(pd.MultiIndex.from_tuples(univ, names=['voter','receiver']), fill_value=0)
    pos = c
    out = dict(scope=label, pairs_ge1=len(pos), median_obs_ge1=np.median(pos), mean_obs=round(pos.mean(),2),
               pct_ge5_of_observed=round(100*(pos >= 5).mean(),1), pct_ge5_universe=round(100*(full >= 5).mean(),1),
               pct_ge8_universe=round(100*(full >= 8).mean(),1), max=pos.max(), q25=np.percentile(pos,25), q75=np.percentile(pos,75),
               pct_zero_universe=round(100*(full == 0).mean(),1), total_rows=len(sub))
    return out
res = []
for vt in ['J', 'T']:
    s = df[df.vtype == vt]
    res.append(summ(s[s['round'] == 'F'], f'{vt} final only'))
    res.append(summ(s, f'{vt} final+semis'))
    if vt == 'J':
        res.append(summ(s[s.flag_substitute_jury == 0], 'J final+semis excl. substitute juries'))
# combined J+T ballots (each type = separate obs)
res.append(summ(df[df['round'] == 'F'], 'J+T final only (ballots)'))
res.append(summ(df, 'J+T final+semis (ballots)'))
# year-level (pair observed in a year in any round, either type)
yr = df.drop_duplicates(['year', 'voter', 'receiver'])
res.append(summ(yr, 'distinct years observed (any round/type)'))
yrF = df[df['round']=='F'].drop_duplicates(['year', 'voter', 'receiver'])
res.append(summ(yrF, 'distinct years observed (final)'))
out = pd.DataFrame(res)
print(out.to_string(index=False))
out.to_csv('counts_summary.csv', index=False)
# distribution table for final-only J and F+SF T
for lab, s in [('J_final', df[(df.vtype=='J')&(df['round']=='F')]), ('T_final+semi', df[df.vtype=='T']), ('T_final', df[(df.vtype=='T')&(df['round']=='F')])]:
    c = s.groupby(['voter','receiver']).size().reindex(pd.MultiIndex.from_tuples(univ), fill_value=0)
    print(lab, 'distribution of obs (universe):', c.value_counts().sort_index().to_dict())
# selection: receivers' share of finals reached
q = df[(df['round']!='F')].drop_duplicates(['year','receiver'])[['year','receiver','qualified']]
print('semi-final qualification rate overall', q.qualified.mean().round(3))
fin = df[df['round']=='F'].drop_duplicates(['year','receiver']).groupby('receiver').size()
print('number of finals per receiver (2016-2025, 9 contests):'); print(fin.sort_values().to_string())
