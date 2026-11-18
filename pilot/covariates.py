"""Hand-coded dyad covariates for the pilot (to be replaced/verified by the students:
CEPII GeoDist for contiguity/distance/language, UN DESA migrant stock for diaspora).
Borders = land borders between ESC participants (Kosovo-related borders not counted; Gibraltar not counted)."""
import itertools, math
import numpy as np, pandas as pd
BORDERS = {
 'AL': ['ME', 'MK', 'GR'], 'AM': ['GE', 'AZ'], 'AT': ['DE', 'CZ', 'HU', 'SI', 'IT', 'CH'],
 'AZ': ['GE', 'AM', 'RU'], 'BY': ['RU', 'UA', 'PL', 'LT', 'LV'], 'BE': ['NL', 'DE', 'LU', 'FR'],
 'BA': ['HR', 'RS', 'ME'], 'BG': ['RO', 'RS', 'MK', 'GR'], 'HR': ['SI', 'HU', 'RS', 'BA', 'ME'],
 'CZ': ['DE', 'PL', 'AT'], 'DK': ['DE'], 'EE': ['LV', 'RU'], 'FI': ['SE', 'NO', 'RU'],
 'FR': ['BE', 'LU', 'DE', 'CH', 'IT', 'ES'], 'GE': ['RU', 'AZ', 'AM'],
 'DE': ['DK', 'PL', 'CZ', 'AT', 'CH', 'FR', 'LU', 'BE', 'NL'], 'GR': ['AL', 'MK', 'BG'],
 'HU': ['AT', 'UA', 'RO', 'RS', 'HR', 'SI'], 'IE': ['GB'], 'IT': ['FR', 'CH', 'AT', 'SI', 'SM'],
 'LV': ['EE', 'LT', 'BY', 'RU'], 'LT': ['LV', 'BY', 'PL', 'RU'], 'LU': ['BE', 'DE', 'FR'],
 'MK': ['RS', 'BG', 'GR', 'AL'], 'MD': ['RO', 'UA'], 'ME': ['HR', 'BA', 'RS', 'AL'], 'NL': ['DE', 'BE'],
 'NO': ['SE', 'FI', 'RU'], 'PL': ['DE', 'CZ', 'UA', 'BY', 'LT', 'RU'], 'PT': ['ES'],
 'RO': ['UA', 'MD', 'HU', 'RS', 'BG'], 'RU': ['NO', 'FI', 'EE', 'LV', 'LT', 'PL', 'BY', 'UA', 'GE', 'AZ'],
 'SM': ['IT'], 'RS': ['HU', 'RO', 'BG', 'MK', 'HR', 'BA', 'ME'], 'SI': ['IT', 'AT', 'HU', 'HR'],
 'ES': ['FR', 'PT'], 'SE': ['NO', 'FI'], 'CH': ['DE', 'FR', 'IT', 'AT'],
 'UA': ['RU', 'BY', 'PL', 'HU', 'RO', 'MD'], 'GB': ['IE']}
# UN M49 sub-regions (reproducible default region scheme)
M49 = {}
for c in 'DK EE FI IS IE LV LT NO SE GB'.split(): M49[c] = 'Northern Europe'
for c in 'AT BE FR DE LU NL CH'.split(): M49[c] = 'Western Europe'
for c in 'AL BA HR GR IT MT ME MK PT SM RS SI ES'.split(): M49[c] = 'Southern Europe'
for c in 'BY BG CZ HU PL MD RO RU UA'.split(): M49[c] = 'Eastern Europe'
for c in 'AM AZ CY GE IL'.split(): M49[c] = 'Western Asia'
M49['AU'] = 'Oceania'
BLOCS = {'exUSSR': 'AM AZ BY EE GE LV LT MD RU UA', 'exYU': 'BA HR MK ME RS SI', 'Nordic': 'DK FI IS NO SE',
         'Baltic': 'EE LV LT'}
# shared official/majority language groups (coarse)
LANG = [('GR', 'CY'), ('DE', 'AT'), ('DE', 'CH'), ('AT', 'CH'), ('FR', 'BE'), ('FR', 'CH'), ('FR', 'LU'), ('BE', 'LU'),
        ('NL', 'BE'), ('RO', 'MD'), ('RS', 'ME'), ('RS', 'BA'), ('RS', 'HR'), ('HR', 'BA'), ('HR', 'ME'), ('BA', 'ME'),
        ('GB', 'IE'), ('GB', 'AU'), ('IE', 'AU'), ('GB', 'MT'), ('IT', 'SM'), ('IT', 'CH'), ('SE', 'FI'),
        ('RU', 'BY'), ('DE', 'LU'), ('SE', 'NO'), ('SE', 'DK'), ('NO', 'DK')]  # last three: mutually intelligible
CAP = {'AL': (41.33, 19.82), 'AM': (40.18, 44.51), 'AT': (48.21, 16.37), 'AU': (-35.28, 149.13), 'AZ': (40.41, 49.87),
       'BA': (43.86, 18.41), 'BE': (50.85, 4.35), 'BG': (42.70, 23.32), 'BY': (53.90, 27.57), 'CH': (46.95, 7.45),
       'CY': (35.17, 33.36), 'CZ': (50.08, 14.44), 'DE': (52.52, 13.40), 'DK': (55.68, 12.57), 'EE': (59.44, 24.75),
       'ES': (40.42, -3.70), 'FI': (60.17, 24.94), 'FR': (48.86, 2.35), 'GB': (51.51, -0.13), 'GE': (41.72, 44.79),
       'GR': (37.98, 23.73), 'HR': (45.81, 15.98), 'HU': (47.50, 19.04), 'IE': (53.35, -6.26), 'IL': (31.77, 35.22),
       'IS': (64.15, -21.94), 'IT': (41.90, 12.50), 'LT': (54.69, 25.28), 'LU': (49.61, 6.13), 'LV': (56.95, 24.11),
       'MD': (47.01, 28.86), 'ME': (42.44, 19.26), 'MK': (41.99, 21.43), 'MT': (35.90, 14.51), 'NL': (52.37, 4.90),
       'NO': (59.91, 10.75), 'PL': (52.23, 21.01), 'PT': (38.72, -9.14), 'RO': (44.43, 26.10), 'RS': (44.79, 20.45),
       'RU': (55.76, 37.62), 'SE': (59.33, 18.07), 'SI': (46.06, 14.51), 'SM': (43.94, 12.45), 'UA': (50.45, 30.52)}
def hav(a, b):
    (la1, lo1), (la2, lo2) = CAP[a], CAP[b]
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
def dyad_covariates(countries):
    for a, nb in BORDERS.items():  # symmetry check
        for b in nb:
            assert a in BORDERS.get(b, []), (a, b)
    lang = {frozenset(p) for p in LANG}
    rows = []
    for a, b in itertools.permutations(countries, 2):
        r = dict(voter=a, receiver=b, border=int(b in BORDERS.get(a, [])), same_m49=int(M49[a] == M49[b]),
                 shared_lang=int(frozenset((a, b)) in lang), dist_km=hav(a, b))
        for k, v in BLOCS.items():
            s = v.split(); r['bloc_' + k] = int(a in s and b in s)
        rows.append(r)
    d = pd.DataFrame(rows); d['log_dist'] = np.log(d.dist_km)
    return d
if __name__ == '__main__':
    C = sorted(CAP)
    d = dyad_covariates(C)
    d.to_csv('dyad_covariates.csv', index=False)
    print(d[['border', 'same_m49', 'shared_lang', 'bloc_exUSSR', 'bloc_exYU', 'bloc_Nordic']].mean().round(3).to_dict(), len(d))
