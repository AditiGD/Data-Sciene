"""Build tidy tables from the EurovisionAPI dataset (senior, 2016-2026). Read-only on the data dir.

Run: python3 -I 01_build_tidy.py <DATA_DIR> <OUT_DIR>

Outputs (OUT_DIR):
  tidy_votes.parquet / .csv  one row per (year, round, vote_type, voter, receiver) as present in the source
                             votes dicts (zeros kept if the source lists them).
  performances.csv           one row per (year, round, contestant) with running/place/points per score name
  contestants.csv            one row per (year, contestant_id) with country, artist, song, dir name
  rounds.csv                 one row per (year, round) with date, n_performances, disqualifieds
  load_log.json              raw-structure anomalies found while loading (null fields, missing keys, etc.)
"""
import json, os, sys
import pandas as pd

DATA, OUT = sys.argv[1], sys.argv[2]
SEN = os.path.join(DATA, "senior")
YEARS = [y for y in range(2016, 2027) if os.path.isdir(os.path.join(SEN, str(y)))]  # fork ends 2025
ROUND_ORDER = {"semifinal1": 1, "semifinal2": 2, "final": 3}
log = {"null_performances": [], "missing_score_fields": [], "contestant_dir_mismatch": [],
       "unknown_contestant_id": [], "non_int_points": [], "score_name_unexpected": []}

countries = json.load(open(os.path.join(DATA, "countries.json"), encoding="utf-8"))

vote_rows, perf_rows, cont_rows, round_rows = [], [], [], []
for y in YEARS:
    yd = os.path.join(SEN, str(y))
    contest = json.load(open(os.path.join(yd, "contest.json"), encoding="utf-8"))
    id2c = {}
    for d in sorted(os.listdir(os.path.join(yd, "contestants"))):
        cj = json.load(open(os.path.join(yd, "contestants", d, "contestant.json"), encoding="utf-8"))
        order, cc = d.split("_", 1)
        if cj.get("country", "").lower() != cc.lower():
            log["contestant_dir_mismatch"].append({"year": y, "dir": d, "country": cj.get("country")})
        if cj["id"] in id2c:
            log["contestant_dir_mismatch"].append({"year": y, "dir": d, "dup_id": cj["id"]})
        id2c[cj["id"]] = cj["country"]
        cont_rows.append({"year": y, "contestant_id": cj["id"], "country": cj["country"],
                          "dir": d, "dir_order": int(order), "artist": cj.get("artist"),
                          "song": cj.get("song"), "host": contest.get("country"),
                          "intended_host": contest.get("intendedCountry")})
    for rf in sorted(os.listdir(os.path.join(yd, "rounds"))):
        rname = rf[:-5]
        rd = json.load(open(os.path.join(yd, "rounds", rf), encoding="utf-8"))
        perfs = rd.get("performances")
        round_rows.append({"year": y, "round": rname, "date": rd.get("date"), "time": rd.get("time"),
                           "n_performances": None if perfs is None else len(perfs),
                           "disqualifieds": json.dumps(rd.get("disqualifieds")),
                           "host": contest.get("country"), "intended_host": contest.get("intendedCountry")})
        if perfs is None:
            log["null_performances"].append({"year": y, "round": rname})
            continue
        for p in perfs:
            cid = p.get("contestantId")
            rc = id2c.get(cid)
            if rc is None:
                log["unknown_contestant_id"].append({"year": y, "round": rname, "contestantId": cid})
            pr = {"year": y, "round": rname, "contestant_id": cid, "country": rc,
                  "running": p.get("running"), "place": p.get("place")}
            for k in ("contestantId", "running", "place", "scores"):
                if p.get(k) is None:
                    log["missing_score_fields"].append({"year": y, "round": rname, "contestantId": cid, "field": k})
            for s in p.get("scores") or []:
                nm = s.get("name")
                if nm not in ("total", "jury", "public"):
                    log["score_name_unexpected"].append({"year": y, "round": rname, "name": nm})
                pr[f"points_{nm}"] = s.get("points")
                pr[f"nvoters_{nm}"] = None if s.get("votes") is None else len(s["votes"])
                if s.get("votes") is None:
                    log["missing_score_fields"].append({"year": y, "round": rname, "contestantId": cid, "field": f"{nm}.votes"})
                    continue
                for voter, pts in s["votes"].items():
                    if not isinstance(pts, int) or isinstance(pts, bool):
                        log["non_int_points"].append({"year": y, "round": rname, "type": nm, "voter": voter, "pts": repr(pts)})
                    vote_rows.append({"year": y, "round": rname, "vote_type": nm, "voter": voter,
                                      "receiver": rc, "receiver_contestant_id": cid, "points": pts})
            perf_rows.append(pr)

votes = pd.DataFrame(vote_rows)
votes["round_order"] = votes["round"].map(ROUND_ORDER)
votes = votes.sort_values(["year", "round_order", "vote_type", "voter", "receiver"]).reset_index(drop=True)
perf = pd.DataFrame(perf_rows)
cont = pd.DataFrame(cont_rows)
rounds = pd.DataFrame(round_rows)
os.makedirs(OUT, exist_ok=True)
votes.drop(columns="round_order").to_csv(os.path.join(OUT, "tidy_votes_raw.csv"), index=False)
votes.drop(columns="round_order").to_parquet(os.path.join(OUT, "tidy_votes_raw.parquet"), index=False)
perf.to_csv(os.path.join(OUT, "performances.csv"), index=False)
cont.to_csv(os.path.join(OUT, "contestants.csv"), index=False)
rounds.to_csv(os.path.join(OUT, "rounds.csv"), index=False)
json.dump(log, open(os.path.join(OUT, "load_log.json"), "w"), indent=1)
print("votes", votes.shape, "perf", perf.shape, "contestants", cont.shape, "rounds", rounds.shape)
print({k: len(v) for k, v in log.items()})
