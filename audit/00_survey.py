"""Structural survey of the EurovisionAPI dataset, 2016-2026 (read-only).
Run: python3 -I 00_survey.py <DATA_ROOT>/data
"""
import json, os, sys, collections

ROOT = sys.argv[1]
SEN = os.path.join(ROOT, "senior")

for y in range(2014, 2027):
    yd = os.path.join(SEN, str(y))
    if not os.path.isdir(yd):
        print(y, "MISSING"); continue
    contest = json.load(open(os.path.join(yd, "contest.json"), encoding="utf-8"))
    rounds = sorted(os.listdir(os.path.join(yd, "rounds")))
    cdirs = sorted(os.listdir(os.path.join(yd, "contestants")))
    print(f"== {y} host={contest.get('country')} intended={contest.get('intendedCountry')} city={contest.get('city')} rounds={rounds} n_contestant_dirs={len(cdirs)}")
    print("   contest keys:", sorted(contest.keys()))
    for r in rounds:
        rd = json.load(open(os.path.join(yd, "rounds", r), encoding="utf-8"))
        perfs = rd.get("performances")
        keys = sorted(rd.keys())
        if perfs is None:
            print(f"   {r}: keys={keys} performances=None disq={rd.get('disqualifieds')}")
            continue
        snames = collections.Counter()
        pkeys = collections.Counter()
        for p in perfs:
            pkeys.update(p.keys())
            for s in p.get("scores") or []:
                snames[s.get("name")] += 1
        print(f"   {r}: keys={keys} n_perf={len(perfs)} perf_keys={dict(pkeys)} score_names={dict(snames)} disq={rd.get('disqualifieds')} date={rd.get('date')}")
