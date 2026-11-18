"""Build tidy long table of ESC ballots 2016-2026.
Usage: python3 -I build_long.py <dataset_root> <out_csv>
Rows: one per (year, round, vote_type, voter, receiver) for every eligible pair listed in the data
(the data list 0-point entries explicitly, so eligibility = presence in votes dict)."""
import json, os, sys
import pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
ROUNDS = {'final.json': 'F', 'semifinal1.json': 'SF1', 'semifinal2.json': 'SF2'}
rows = []
for y in range(2016, 2027):
    base = os.path.join(D, 'data', 'senior', str(y))
    if not os.path.isdir(base):  # GD fork ends at 2025; 2026 exists only upstream
        continue
    cmap = {}
    cdir = os.path.join(base, 'contestants')
    for c in os.listdir(cdir):
        j = json.load(open(os.path.join(cdir, c, 'contestant.json')))
        cmap[j['id']] = j['country']
    final_set = set()
    rf = json.load(open(os.path.join(base, 'rounds', 'final.json')))
    for p in rf['performances'] or []:
        final_set.add(cmap[p['contestantId']])
    for fn, rd in ROUNDS.items():
        r = json.load(open(os.path.join(base, 'rounds', fn)))
        perfs = r['performances'] or []
        types = {s['name'] for p in perfs for s in p['scores']}
        for p in perfs:
            rc = cmap[p['contestantId']]
            for s in p['scores']:
                nm = s['name']
                if nm == 'total' and 'jury' in types:
                    continue  # total = jury + public; keep components only
                vt = {'jury': 'J', 'public': 'T', 'total': 'T'}[nm]  # total-only rounds (2023-25 semis) are televote-only
                for v, pts in (s.get('votes') or {}).items():
                    rows.append(dict(year=y, round=rd, vtype=vt, voter=v, receiver=rc, points=int(pts),
                                     place=p.get('place'), running=p.get('running'),
                                     qualified=int(rc in final_set) if rd != 'F' else 1))
df = pd.DataFrame(rows)
# flags
df['flag_substitute_jury'] = 0
sub = [(2019, 'F', 'BY'), (2022, 'SF2', 'AZ'), (2022, 'SF2', 'GE'), (2022, 'SF2', 'ME'), (2022, 'SF2', 'PL'),
       (2022, 'SF2', 'RO'), (2022, 'SF2', 'SM'), (2022, 'F', 'AZ'), (2022, 'F', 'GE'), (2022, 'F', 'ME'),
       (2022, 'F', 'PL'), (2022, 'F', 'RO'), (2022, 'F', 'SM')]
for (y, rd, v) in sub:
    m = (df.year == y) & (df['round'] == rd) & (df.voter == v) & (df.vtype == 'J')
    df.loc[m, 'flag_substitute_jury'] = 1
df['flag_wld'] = (df.voter == 'WLD').astype(int)
df['flag_semi_tele_only'] = ((df.year.between(2023, 2025)) & (df['round'] != 'F')).astype(int)
# within-ballot rank among top 10 (1 = 12 points); 0-point -> NaN
order = {12: 1, 10: 2, 8: 3, 7: 4, 6: 5, 5: 6, 4: 7, 3: 8, 2: 9, 1: 10}
df['rank'] = df.points.map(order)
df['n_eligible'] = df.groupby(['year', 'round', 'vtype', 'voter']).receiver.transform('size')
df.to_csv(OUT, index=False)
print(df.shape)
print(df.groupby(['year', 'round', 'vtype']).agg(n=('points', 'size'), voters=('voter', 'nunique'),
      receivers=('receiver', 'nunique')).unstack('vtype').to_string())
