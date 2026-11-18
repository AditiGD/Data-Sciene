"""Annotate tidy votes with study semantics + anomaly flags; compute coverage & participation.

Run: python3 -I 03_annotate_coverage.py <OUT_DIR>

Outputs (OUT_DIR):
  tidy_votes.parquet / tidy_votes.csv   analysis-ready long table (contract in C_data_audit.md section 6)
  participation_matrix.csv              country x year: F=final performer, S=semi-only performer, V=voted only (n/a here), '' absent
  coverage_pairs.csv                    per (voter, receiver, scope, vote_kind): n_obs, n_years, n_8plus, mean_points
  coverage_summary.csv                  pairs with >=k observations by scope x vote_kind
  anomaly_flag_counts.csv               rows affected per flag
"""
import os, sys
import pandas as pd

OUT = sys.argv[1]
v = pd.read_parquet(os.path.join(OUT, "tidy_votes_raw.parquet"))
perf = pd.read_csv(os.path.join(OUT, "performances.csv"))

TELE_ONLY_SEMI_YEARS = {2023, 2024, 2025}
v["round_kind"] = v["round"].map(lambda r: "final" if r == "final" else "semifinal")
# vote_kind: semantic source of the points, independent of the source label
def kind(r):
    if r.vote_type == "jury":
        return "jury"
    if r.vote_type == "public":
        return "televote"
    if r.round_kind == "semifinal" and r.year in TELE_ONLY_SEMI_YEARS:
        return "televote"  # 2023-2025 semis: 'total' == televote (no jury component)
    return "combined"
v["vote_kind"] = v.apply(kind, axis=1)
# is_primary_record: one record per ballot (avoids double counting 'total' when the split exists;
# in tele-only semis the 'total' row IS the televote record)
v["is_split_record"] = v.vote_type.isin(["jury", "public"]) | (v.vote_kind == "televote")
v["voter_is_country"] = v.voter != "WLD"

# receiver place/running
v = v.merge(perf[["year", "round", "contestant_id", "place", "running"]].rename(
    columns={"contestant_id": "receiver_contestant_id", "place": "receiver_place", "running": "receiver_running"}),
    on=["year", "round", "receiver_contestant_id"], how="left")
# voter performs in this round?
perf_set = set(zip(perf.year, perf["round"], perf.country))
v["voter_performs_in_round"] = [(y, r, c) in perf_set for y, r, c in zip(v.year, v["round"], v.voter)]

# ---- anomaly flags (documented in C_data_audit.md section 3) ----
F = pd.Series("", index=v.index)
def flag(mask, name):
    global F
    F = F.where(~mask, F + ("|" if True else "") + name)
m = lambda **kw: pd.Series(True, index=v.index).__and__(
    pd.concat([(v[k].isin(val) if isinstance(val, (list, set, tuple)) else v[k].eq(val)) for k, val in kw.items()], axis=1).all(axis=1))
jt = ["jury", "total"]  # jury-substitute also propagates into 'total'
flag(m(year=2019, round="final", voter="BY", vote_type=jt), "SUBST_JURY_2019_BY")
flag(m(year=2022, round=["semifinal2", "final"], voter=["AZ", "GE", "ME", "PL", "RO", "SM"], vote_type=jt), "SUBST_JURY_2022_SIX")
flag(m(voter="SM", vote_type=["public", "total"]) & (v.vote_kind != "jury"), "SYNTH_TELEVOTE_SM")
flag(m(voter="WLD"), "REST_OF_WORLD")
flag(m(year=2016, round="final", voter="DK", vote_type=jt), "JUROR_ERROR_2016_DK")
flag(m(year=2024, round="final", voter="NL"), "VOTER_DQ_ENTRY_2024_NL")
flag(m(year=2024, round="final", voter="NO", vote_type=jt), "JUROR_CONTROVERSY_2024_NO")
flag(m(year=2026, voter=["CZ", "CY", "MT", "LU"], vote_type=jt), "JURY_6_MEMBERS_2026")
flag(m(year=2026), "RULESET_2026")  # juries back in semis, 7-member juries, televote cap 10
v["anomaly_flags"] = F.str.strip("|")

v["jury_method"] = v.year.map(lambda y: "average_rank" if y < 2018 else "exponential_weight")
v.loc[v.vote_kind.isin(["televote"]), "jury_method"] = None

cols = ["year", "round", "round_kind", "vote_type", "vote_kind", "is_split_record", "voter", "voter_is_country",
        "voter_performs_in_round", "receiver", "receiver_contestant_id", "receiver_place", "receiver_running",
        "points", "jury_method", "anomaly_flags"]
v = v[cols].sort_values(["year", "round", "vote_type", "voter", "receiver"]).reset_index(drop=True)
v.to_parquet(os.path.join(OUT, "tidy_votes.parquet"), index=False)
v.to_csv(os.path.join(OUT, "tidy_votes.csv"), index=False)

fl = v.anomaly_flags.str.split("|").explode()
fl = fl[fl != ""]
fc = fl.groupby(fl).size().rename("rows").reset_index().rename(columns={"anomaly_flags": "flag"})
# Also count distinct ballots affected
bal = v.assign(flag=v.anomaly_flags.str.split("|")).explode("flag")
bal = bal[bal.flag.notna() & (bal.flag != "")]
fc = fc.merge(bal.groupby("flag").apply(lambda g: g[["year", "round", "vote_type", "voter"]].drop_duplicates().shape[0],
                                         include_groups=False).rename("ballots").reset_index(), on="flag")
fc.to_csv(os.path.join(OUT, "anomaly_flag_counts.csv"), index=False)
print(fc.to_string(index=False))

# ---- participation matrix ----
years = sorted(set(perf.year))
allc = sorted(set(perf.country) | set(v.voter[v.voter_is_country]))
fin = set(zip(perf.year[perf["round"] == "final"], perf.country[perf["round"] == "final"]))
semi = set(zip(perf.year[perf["round"] != "final"], perf.country[perf["round"] != "final"]))
voted = set(zip(v.year, v.voter))
rows = []
for c in allc:
    r = {"country": c}
    for y in years:
        r[str(y)] = "F" if (y, c) in fin else ("S" if (y, c) in semi else ("V" if (y, c) in voted else ""))
    r["n_years_participating"] = sum(1 for y in years if r[str(y)])
    r["n_finals"] = sum(1 for y in years if r[str(y)] == "F")
    rows.append(r)
pm = pd.DataFrame(rows)
pm.to_csv(os.path.join(OUT, "participation_matrix.csv"), index=False)

# ---- coverage ----
base = v[v.voter_is_country & v.is_split_record & (v.year <= 2025)]
scopes = {"A_finals_2016_2025": base[base.round_kind == "final"],
          "B_finals_plus_semis_2016_2025": base}
cov = []
for sname, d in scopes.items():
    for vk, dd in d.groupby("vote_kind"):
        g = dd.groupby(["voter", "receiver"])
        t = pd.DataFrame({"n_obs": g.size(), "n_years": g.year.nunique(), "n_8plus": g.points.apply(lambda s: (s >= 8).sum()),
                          "mean_points": g.points.mean().round(3)}).reset_index()
        t["scope"] = sname; t["vote_kind"] = vk
        cov.append(t)
cov = pd.concat(cov)
cov.to_csv(os.path.join(OUT, "coverage_pairs.csv"), index=False)
summ = []
for (s, vk), g in cov.groupby(["scope", "vote_kind"]):
    summ.append({"scope": s, "vote_kind": vk, "n_rows": int(g.n_obs.sum()), "n_pairs": len(g),
                 "n_obs_min": int(g.n_obs.min()), "n_obs_median": float(g.n_obs.median()), "n_obs_max": int(g.n_obs.max()),
                 "pairs_ge3": int((g.n_obs >= 3).sum()), "pairs_ge5": int((g.n_obs >= 5).sum()),
                 "pairs_ge7": int((g.n_obs >= 7).sum()), "pairs_eq9": int((g.n_obs == 9).sum())})
summ = pd.DataFrame(summ)
summ.to_csv(os.path.join(OUT, "coverage_summary.csv"), index=False)
print(summ.to_string(index=False))
# distribution table for scope A
a = cov[(cov.scope == "A_finals_2016_2025") & (cov.vote_kind == "jury")]
print("scope A jury n_obs distribution:", a.n_obs.value_counts().sort_index().to_dict())
b = cov[(cov.scope == "B_finals_plus_semis_2016_2025") & (cov.vote_kind == "televote")]
print("scope B televote n_obs distribution:", b.n_obs.value_counts().sort_index().to_dict())
print(pm.to_string(index=False))
