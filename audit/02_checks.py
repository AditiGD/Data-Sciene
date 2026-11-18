"""Executable integrity checks on the tidy Eurovision tables (2016-2026).

Run: python3 -I 02_checks.py <DATA_DIR> <OUT_DIR> [--strict]

Each check yields (id, description, n_offending, offenders DataFrame). Offenders are written to
OUT_DIR/checks/<id>.csv and a summary to OUT_DIR/checks/summary.csv.
Known, documented deviations are listed in KNOWN_EXCEPTIONS; with --strict the script raises
AssertionError if any check has offenders that are NOT covered by a known exception.
"""
import json, os, sys
from collections import Counter
import pandas as pd

DATA, OUT = sys.argv[1], sys.argv[2]
STRICT = "--strict" in sys.argv
CK = os.path.join(OUT, "checks"); os.makedirs(CK, exist_ok=True)
countries = json.load(open(os.path.join(DATA, "countries.json"), encoding="utf-8"))
v = pd.read_parquet(os.path.join(OUT, "tidy_votes_raw.parquet"))
perf = pd.read_csv(os.path.join(OUT, "performances.csv"))
rounds = pd.read_csv(os.path.join(OUT, "rounds.csv"))
BALLOT = Counter([12, 10, 8, 7, 6, 5, 4, 3, 2, 1])
TELE_ONLY_SEMIS = {(2023, "semifinal1"), (2023, "semifinal2"), (2024, "semifinal1"), (2024, "semifinal2"),
                   (2025, "semifinal1"), (2025, "semifinal2")}

# Known deviations (documented in C_data_audit.md); keys are check ids -> predicate on offender rows
KNOWN_EXCEPTIONS = {
    "C07_codes_in_countries_json": lambda df: df["code"].eq("WLD").all(),
    # 2024: NL (contestant 36) qualified from SF2 (2nd) but was disqualified before the final; slot 5 of the
    # final running order stays empty. Listed in semifinal2.json 'disqualifieds': [36].
    "C05c_running_order_permutation": lambda df: (df.year.eq(2024) & df["round"].eq("final")).all() and len(df) == 1,
    "C11_qualification_consistent": lambda df: (df.year.eq(2024) & df.semi_qualifiers_missing_from_final.eq("NL")).all(),
}

results = []
def record(cid, desc, off):
    off = off if isinstance(off, pd.DataFrame) else pd.DataFrame(off)
    off.to_csv(os.path.join(CK, f"{cid}.csv"), index=False)
    known = bool(len(off)) and cid in KNOWN_EXCEPTIONS and bool(KNOWN_EXCEPTIONS[cid](off))
    status = "PASS" if len(off) == 0 else ("PASS_WITH_KNOWN_EXCEPTION" if known else "FAIL")
    results.append({"check": cid, "description": desc, "n_offending": len(off), "status": status})
    print(f"[{status}] {cid}: {desc} -> {len(off)} offending")

# C01 ballot multiset: jury/public always; total only in televote-only semis
b = v[(v.vote_type.isin(["jury", "public"])) |
      (v.vote_type.eq("total") & v.apply(lambda r: (r.year, r["round"]) in TELE_ONLY_SEMIS, axis=1))]
rows = []
for k, g in b.groupby(["year", "round", "vote_type", "voter"]):
    c = Counter(g.points[g.points > 0].tolist())
    if c != BALLOT:
        rows.append(dict(zip(["year", "round", "vote_type", "voter"], k), awarded=sorted(c.elements(), reverse=True)))
record("C01_ballot_multiset", "each (year,round,vote_type,voter) ballot awards exactly {12,10,8..1}", rows)

# C02 no self votes
record("C02_no_self_votes", "voter != receiver", v[v.voter == v.receiver])

# C03 jury + public == total per voter->receiver (where all three exist); WLD has no jury -> public == total
w = v.pivot_table(index=["year", "round", "voter", "receiver"], columns="vote_type", values="points", aggfunc="first").reset_index()
both = w.dropna(subset=["jury", "public", "total"])
off3 = both[both.jury + both.public != both.total]
wld = w[w.jury.isna() & w.public.notna() & w.total.notna()]
off3b = wld[wld.public != wld.total]
record("C03_jury_plus_public_eq_total", "jury+public == total per voter->receiver (and public==total where no jury exists, e.g. WLD)", pd.concat([off3, off3b]))
# C03b: where a total exists but no split exists, it must be a televote-only semi
nosplit = w[w.jury.isna() & w.public.isna()]
bad = nosplit[~nosplit.apply(lambda r: (r.year, r["round"]) in TELE_ONLY_SEMIS, axis=1)]
record("C03b_total_only_rows_are_tele_semis", "rows with only 'total' (no split) occur only in 2023-2025 semis", bad)

# C04 per-receiver points sum equals the 'points' field
rows = []
sums = v.groupby(["year", "round", "receiver_contestant_id", "vote_type"]).points.sum().reset_index()
for _, r in sums.iterrows():
    p = perf[(perf.year == r.year) & (perf["round"] == r["round"]) & (perf.contestant_id == r.receiver_contestant_id)]
    field = p[f"points_{r.vote_type}"].iloc[0]
    if field != r.points:
        rows.append({**r.to_dict(), "points_field": field})
record("C04_votes_sum_eq_points_field", "sum of votes dict == Score.points for every performance and score name", rows)

# C05a points_total == points_jury + points_public at performance level
pp = perf.dropna(subset=["points_jury", "points_public"])
record("C05a_perf_total_eq_jury_plus_public", "performance points_total == points_jury + points_public",
       pp[pp.points_total != pp.points_jury + pp.points_public])

# C05b places: permutation 1..n, and ordered by points_total desc (ties allowed only if equal points)
rows = []
for (y, rn), g in perf.groupby(["year", "round"]):
    n = len(g)
    if sorted(g.place.tolist()) != list(range(1, n + 1)):
        rows.append({"year": y, "round": rn, "issue": "place not a permutation of 1..n", "places": sorted(g.place.tolist())})
    gs = g.sort_values("place")
    pts = gs.points_total.tolist()
    for i in range(1, n):
        if pts[i] > pts[i - 1]:
            rows.append({"year": y, "round": rn, "issue": "points increase with worse place",
                         "place": int(gs.place.iloc[i]), "country": gs.country.iloc[i], "points": pts[i], "prev_points": pts[i - 1]})
    for i in range(1, n):
        if pts[i] == pts[i - 1]:
            rows.append({"year": y, "round": rn, "issue": "INFO tie on points_total (tie-break applied)",
                         "place": int(gs.place.iloc[i]), "country": gs.country.iloc[i], "points": pts[i],
                         "tied_with": gs.country.iloc[i - 1]})
off5 = pd.DataFrame(rows)
record("C05b_places_consistent", "places are 1..n and monotone in points_total (ties reported as INFO)",
       off5[~off5.issue.str.startswith("INFO")] if len(off5) else off5)
if len(off5):
    off5[off5.issue.str.startswith("INFO")].to_csv(os.path.join(CK, "C05b_INFO_ties.csv"), index=False)

# C05c running order: permutation 1..n
rows = []
for (y, rn), g in perf.groupby(["year", "round"]):
    if sorted(g.running.tolist()) != list(range(1, len(g) + 1)):
        rows.append({"year": y, "round": rn, "running": sorted(g.running.tolist())})
record("C05c_running_order_permutation", "running order is a permutation of 1..n", rows)

# C06 duplicate keys
k = ["year", "round", "vote_type", "voter", "receiver"]
record("C06_no_duplicate_keys", "unique (year,round,vote_type,voter,receiver)", v[v.duplicated(k, keep=False)])
pk = ["year", "round", "contestant_id"]
record("C06b_no_duplicate_performances", "unique (year,round,contestant_id) and (year,round,country)",
       pd.concat([perf[perf.duplicated(pk, keep=False)], perf[perf.duplicated(["year", "round", "country"], keep=False)]]))

# C07 every code exists in countries.json
codes = pd.concat([v[["year", "round", "voter"]].rename(columns={"voter": "code"}).assign(role="voter"),
                   v[["year", "round", "receiver"]].rename(columns={"receiver": "code"}).assign(role="receiver")])
miss = codes[~codes.code.isin(countries.keys())].drop_duplicates()
record("C07_codes_in_countries_json", "every voter/receiver code exists in countries.json", miss)

# C08 dense grid: every voter appears for every receiver (except itself) within (year,round,vote_type)
rows = []
for (y, rn, t), g in v.groupby(["year", "round", "vote_type"]):
    voters = set(g.voter); recs = set(g.receiver)
    have = set(zip(g.voter, g.receiver))
    for vo in voters:
        for re_ in recs:
            if vo != re_ and (vo, re_) not in have:
                rows.append({"year": y, "round": rn, "vote_type": t, "voter": vo, "receiver": re_})
record("C08_dense_grid", "every voter listed (possibly with 0) for every non-self receiver", rows)

# C09 points domain
dom_split = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12}
dom_total = {a + b for a in dom_split for b in dom_split}
o1 = v[v.vote_type.isin(["jury", "public"]) & ~v.points.isin(dom_split)]
o2 = v[v.vote_type.eq("total") & ~v.points.isin(dom_total)]
record("C09_points_domain", "jury/public in {0..8,10,12}; total in pairwise sums", pd.concat([o1, o2]))

# C10 each country votes in exactly one semi per year (WLD excepted: both semis), and voter sets are
# identical across vote types within a round (except WLD absent from jury)
rows = []
semi = v[v["round"].str.startswith("semi") & (v.voter != "WLD")]
cnt = semi.groupby(["year", "voter"])["round"].nunique()
for (y, vo), n in cnt.items():
    if n != 1:
        rows.append({"year": y, "voter": vo, "issue": f"votes in {n} semis"})
for (y, rn), g in v.groupby(["year", "round"]):
    sets = {t: set(gg.voter) for t, gg in g.groupby("vote_type")}
    if "jury" in sets:
        if sets["public"] - sets["jury"] - {"WLD"} or sets["jury"] - sets["public"]:
            rows.append({"year": y, "round": rn, "issue": "jury/public voter sets differ beyond WLD",
                         "public_only": sorted(sets["public"] - sets["jury"]), "jury_only": sorted(sets["jury"] - sets["public"])})
record("C10_voter_assignment", "each country votes in exactly one semi; jury/public voter sets equal (bar WLD)", rows)

# C11 finalists = top-10 of each semi + auto-qualifiers; final voters = all participating countries
rows = []
for y, g in perf.groupby("year"):
    fin = set(g[g["round"] == "final"].country)
    q = set(g[(g["round"].str.startswith("semi")) & (g.place <= 10)].country)
    semi_perf = set(g[g["round"].str.startswith("semi")].country)
    auto = fin - semi_perf
    nonq_in_final = fin & (semi_perf - q)
    q_not_in_final = q - fin
    rows.append({"year": y, "n_final": len(fin), "auto_qualifiers": " ".join(sorted(auto)),
                 "semi_qualifiers_missing_from_final": " ".join(sorted(q_not_in_final)),
                 "non_qualifiers_in_final": " ".join(sorted(nonq_in_final))})
c11 = pd.DataFrame(rows)
c11.to_csv(os.path.join(CK, "C11_INFO_qualification.csv"), index=False)
record("C11_qualification_consistent", "no non-qualifier in final; every top-10 semi entry is in the final",
       c11[(c11.semi_qualifiers_missing_from_final != "") | (c11.non_qualifiers_in_final != "")])

# C12 final voter set == all countries that performed in any round that year (plus WLD from 2023)
rows = []
for y, g in perf.groupby("year"):
    participants = set(g.country)
    fv = set(v[(v.year == y) & (v["round"] == "final") & (v.vote_type == "total")].voter) - {"WLD"}
    sv = set(v[(v.year == y) & (v["round"].str.startswith("semi")) & (v.vote_type == "total")].voter) - {"WLD"}
    rows.append({"year": y, "n_participants": len(participants), "n_final_voters_excl_WLD": len(fv),
                 "final_voters_not_performing": " ".join(sorted(fv - participants)),
                 "participants_not_voting_in_final": " ".join(sorted(participants - fv)),
                 "semi_voters_not_final_voters": " ".join(sorted(sv - fv)),
                 "final_voters_not_semi_voters": " ".join(sorted(fv - sv))})
c12 = pd.DataFrame(rows)
c12.to_csv(os.path.join(CK, "C12_INFO_final_voters.csv"), index=False)
record("C12_final_voters_eq_participants", "final voters == participating countries (DQ'd entries documented)",
       c12[(c12.final_voters_not_performing != "") | (c12.participants_not_voting_in_final != "")])

# C13 contestantId -> country join
record("C13_contestant_join", "every performance contestantId resolves to a contestant country", perf[perf.country.isna()])

summary = pd.DataFrame(results)
summary.to_csv(os.path.join(CK, "summary.csv"), index=False)
if STRICT:
    bad = summary[summary.status == "FAIL"]
    assert bad.empty, f"Failing checks: {bad.check.tolist()}"
