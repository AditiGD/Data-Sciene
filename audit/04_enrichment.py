"""Offline enrichment covariates for all ESC participants 2016-2026 (no network needed).

Run: python3 -I 04_enrichment.py <OUT_DIR>
Sources (all bundled in PyPI packages, no download):
  - country_converter 1.3.2: UN M49 sub-region (UNregion), continent, EU-27 membership (current)
  - geonamescache 3.0.2: GeoNames countryInfo (CC BY 4.0): land 'neighbours', 'languages', capital; cities (lat/lon)
  - Hand-curated (documented below): historical blocs, maritime neighbours, Serbo-Croatian language cluster
Outputs: country_attributes.csv, contiguity_curated.csv, dyads_offline.csv
"""
import math, os, sys
import pandas as pd
import country_converter as coco
import geonamescache

OUT = sys.argv[1]
pm = pd.read_csv(os.path.join(OUT, "participation_matrix.csv"))
P = sorted(pm.country)
gc = geonamescache.GeonamesCache()
G = gc.get_countries()
cc = coco.CountryConverter().data.set_index("ISO3")  # NB: coco stores GB ISO2 as regex "^GB$|^UK$"; key on ISO3

# ---- historical / cultural blocs (well-established memberships; cite Wikipedia/state histories in report) ----
BLOCS = {
    "ex_ussr": {"AM", "AZ", "BY", "EE", "GE", "LV", "LT", "MD", "RU", "UA"},
    "ex_yugoslavia": {"BA", "HR", "ME", "MK", "RS", "SI"},
    "nordic": {"DK", "FI", "IS", "NO", "SE"},              # Nordic Council members
    "baltic": {"EE", "LV", "LT"},
    "ex_warsaw_pact_non_ussr": {"PL", "CZ", "HU", "RO", "BG", "AL"},  # AL left 1968; DDR/CS now DE/CZ+SK
    "big5": {"DE", "ES", "FR", "GB", "IT"},
}
# ---- maritime neighbours (curated; class follows COW Direct Contiguity v3.2 thresholds in statute miles) ----
# Only pairs separated by <=150 miles of water and NOT sharing a land border; approx distances from standard maps,
# to be verified against COW contdir v3.2 (https://correlatesofwar.org/data-sets/direct-contiguity/).
MARITIME = [
    ("DK", "SE", "sea_le12mi", "Oresund strait ~4 km; fixed link (Oresund Bridge)"),
    ("FR", "GB", "sea_le24mi", "Strait of Dover ~33 km; Channel Tunnel"),
    ("EE", "FI", "sea_le150mi", "Gulf of Finland ~60-80 km (Tallinn-Helsinki)"),
    ("AL", "IT", "sea_le150mi", "Strait of Otranto ~72 km"),
    ("GR", "IT", "sea_le150mi", "Ionian Sea; Othonoi-Salento ~75 km"),
    ("IT", "MT", "sea_le150mi", "Malta channel ~93 km (Sicily-Malta)"),
    ("HR", "IT", "sea_le150mi", "Adriatic; Palagruza-Gargano ~50-60 km"),
    ("IT", "ME", "sea_le150mi", "Adriatic ~190 km (Bari-Bar)"),
    ("DK", "NO", "sea_le150mi", "Skagerrak ~130-140 km"),
    ("DK", "PL", "sea_le150mi", "Bornholm-Polish coast ~90-100 km"),
    ("DE", "SE", "sea_le150mi", "Baltic; Rugen-Skane ~90-100 km"),
    ("PL", "SE", "sea_le150mi", "Baltic ~165 km (Ystad-Swinoujscie)"),
    ("EE", "SE", "sea_le150mi", "Baltic; Gotland/Faro-Saaremaa ~150 km"),
    ("LV", "SE", "sea_le150mi", "Baltic; Gotland-Courland ~150 km"),
    ("BE", "GB", "sea_le150mi", "North Sea ~110-120 km (Dover-Ostend)"),
    ("GB", "NL", "sea_le150mi", "North Sea ~180 km (Harwich-Hook of Holland)"),
]
LAND_NOTES = {("AL", "RS"): "DISPUTED: border exists only via Kosovo (XK); GeoNames counts it, sovereignty-neutral coding should set land_border=False or flag",
              ("AZ", "RU"): "Dagestan border", ("LT", "RU"): "via Kaliningrad exclave", ("PL", "RU"): "via Kaliningrad exclave",
              ("NO", "RU"): "short Arctic border", ("IT", "SM"): "enclave", ("GB", "IE"): "Northern Ireland land border"}
SH = {"sr", "hr", "bs", "sh", "cnr"}  # Serbo-Croatian cluster (mutually intelligible standards)

def langs(c):
    raw = [x for x in G[c]["languages"].split(",") if x]
    base = [x.split("-")[0] for x in raw]
    return ["sh" if b in SH else b for b in base]

def capital_coords(c):
    cap = G[c]["capital"]
    best = None
    for city in gc.get_cities().values():
        if city["countrycode"] == c and city["name"] == cap:
            if best is None or city["population"] > best["population"]:
                best = city
    return (best["latitude"], best["longitude"]) if best else (None, None)

rows = []
for c in P:
    lat, lon = capital_coords(c)
    i3 = G[c]["iso3"]
    r = {"code": c, "iso3": i3, "name": cc.loc[i3, "name_short"], "un_m49_subregion": cc.loc[i3, "UNregion"],
         "continent": cc.loc[i3, "continent"], "eu27_current": cc.loc[i3, "EU27"] == "EU27",
         "geonames_languages": G[c]["languages"], "primary_language": langs(c)[0], "capital": G[c]["capital"],
         "capital_lat": lat, "capital_lon": lon, "population_geonames": G[c]["population"],
         "land_neighbours_all": G[c]["neighbours"],
         "land_neighbours_esc": ",".join(sorted(n for n in G[c]["neighbours"].split(",") if n in P))}
    for b, s in BLOCS.items():
        r[b] = c in s
    rows.append(r)
ca = pd.DataFrame(rows)
ca.to_csv(os.path.join(OUT, "country_attributes.csv"), index=False)

# ---- curated contiguity (undirected, a<b) ----
cont = []
for c in P:
    for n in G[c]["neighbours"].split(","):
        if n in P and c < n:
            symmetric = c in G[n]["neighbours"].split(",")
            cont.append({"a": c, "b": n, "contig_type": "land",
                         "source": "GeoNames countryInfo 'neighbours' via geonamescache 3.0.2 (CC BY 4.0)",
                         "note": LAND_NOTES.get((c, n), "") if symmetric else "ASYMMETRIC in GeoNames - check"})
land = {(r["a"], r["b"]) for r in cont}
for a, b, t, note in MARITIME:
    a, b = sorted((a, b))
    assert (a, b) not in land, (a, b)
    cont.append({"a": a, "b": b, "contig_type": t,
                 "source": "Curated; class per COW Direct Contiguity v3.2 thresholds (verify against contdir v3.2)",
                 "note": note})
ct = pd.DataFrame(cont).sort_values(["contig_type", "a", "b"])
ct.to_csv(os.path.join(OUT, "contiguity_curated.csv"), index=False)

# ---- dyads (ordered voter->receiver) ----
def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))
cai = ca.set_index("code")
ctype = {(r.a, r.b): r.contig_type for r in ct.itertuples()}
dy = []
for a in P:
    for b in P:
        if a == b:
            continue
        k = tuple(sorted((a, b)))
        la, lb = set(langs(a)), set(langs(b))
        d = {"voter": a, "receiver": b, "contig_type": ctype.get(k, "none"),
             "land_border": ctype.get(k) == "land", "any_neighbour": k in ctype,
             "capital_dist_km": round(hav((cai.loc[a, "capital_lat"], cai.loc[a, "capital_lon"]),
                                          (cai.loc[b, "capital_lat"], cai.loc[b, "capital_lon"])), 1),
             "shared_primary_language": langs(a)[0] == langs(b)[0],
             "shared_any_listed_language": bool(la & lb),
             "same_un_subregion": cai.loc[a, "un_m49_subregion"] == cai.loc[b, "un_m49_subregion"]}
        for bl in BLOCS:
            d[f"both_{bl}"] = bool(cai.loc[a, bl] and cai.loc[b, bl])
        dy.append(d)
dy = pd.DataFrame(dy)
dy["same_bloc_any"] = dy[[f"both_{b}" for b in ["ex_ussr", "ex_yugoslavia", "nordic"]]].any(axis=1)
dy.to_csv(os.path.join(OUT, "dyads_offline.csv"), index=False)
print(ca[["code", "un_m49_subregion", "primary_language", "land_neighbours_esc"]].to_string(index=False))
print(ct.contig_type.value_counts().to_dict(), "asymmetric:", (ct.note.str.startswith("ASYM")).sum())
print("dyads", dy.shape, dy[["land_border", "any_neighbour", "shared_primary_language", "shared_any_listed_language", "same_un_subregion", "same_bloc_any"]].sum().to_dict())
