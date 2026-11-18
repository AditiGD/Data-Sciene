"""Per-(year, round) profile table. Run: python3 -I 06_profile.py <OUT_DIR>"""
import os, sys
import pandas as pd
OUT = sys.argv[1]
v = pd.read_parquet(os.path.join(OUT, "tidy_votes.parquet"))
perf = pd.read_csv(os.path.join(OUT, "performances.csv"))
rows = []
prev = None
for (y, r), g in v.groupby(["year", "round"], sort=False):
    p = perf[(perf.year == y) & (perf["round"] == r)]
    vs = {t: set(gg.voter) for t, gg in g.groupby("vote_type")}
    nonperf = sorted(set(g.voter) - set(p.country) - {"WLD"})
    rows.append({"year": y, "round": r, "n_performers": len(p), "score_names": ",".join(sorted(vs)),
                 "n_voters_total": len(vs.get("total", [])), "n_voters_jury": len(vs.get("jury", [])),
                 "n_voters_public": len(vs.get("public", [])), "WLD": "WLD" in vs.get("total", set()),
                 "voters_not_performing": " ".join(nonperf), "null_place": int(p.place.isna().sum()),
                 "null_running": int(p.running.isna().sum())})
pr = pd.DataFrame(rows)
pr["round"] = pd.Categorical(pr["round"], ["semifinal1", "semifinal2", "final"])
pr = pr.sort_values(["year", "round"])
pr.to_csv(os.path.join(OUT, "profile_year_round.csv"), index=False)
print(pr.to_markdown(index=False) if hasattr(pr, "to_markdown") else pr.to_string(index=False))
# final voter list changes year to year
fv = v[(v["round"] == "final") & (v.vote_type == "total")].groupby("year").voter.apply(set)
ys = list(fv.index)
for a, b in zip(ys, ys[1:]):
    print(f"{a}->{b}: joined {sorted(fv[b]-fv[a])} left {sorted(fv[a]-fv[b])}")
