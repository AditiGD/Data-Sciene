"""Pandera data contract for the analysis-ready tidy vote table (tidy_votes.parquet).

Run: python3 -I 05_schema.py <OUT_DIR>      -> validates and prints PASS / failure cases
"""
import os, sys
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

ESC_CODES = ["AL", "AM", "AT", "AU", "AZ", "BA", "BE", "BG", "BY", "CH", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
             "FR", "GB", "GE", "GR", "HR", "HU", "IE", "IL", "IS", "IT", "LT", "LU", "LV", "MD", "ME", "MK", "MT",
             "NL", "NO", "PL", "PT", "RO", "RS", "RU", "SE", "SI", "SM", "UA"]
SPLIT_POINTS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
TOTAL_POINTS = sorted({a + b for a in SPLIT_POINTS for b in SPLIT_POINTS})
FLAGS = {"SUBST_JURY_2019_BY", "SUBST_JURY_2022_SIX", "SYNTH_TELEVOTE_SM", "REST_OF_WORLD", "JUROR_ERROR_2016_DK",
         "VOTER_DQ_ENTRY_2024_NL", "JUROR_CONTROVERSY_2024_NO", "JURY_6_MEMBERS_2026", "RULESET_2026"}
KEY = ["year", "round", "vote_type", "voter", "receiver"]

def flags_ok(s):
    return s.fillna("").map(lambda x: all(f in FLAGS for f in x.split("|") if f))

tidy_votes_schema = DataFrameSchema(
    {
        "year": Column(int, [Check.in_range(2016, 2026), Check.ne(2020)]),
        "round": Column(str, Check.isin(["semifinal1", "semifinal2", "final"])),
        "round_kind": Column(str, Check.isin(["semifinal", "final"])),
        "vote_type": Column(str, Check.isin(["jury", "public", "total"])),          # label as in source JSON
        "vote_kind": Column(str, Check.isin(["jury", "televote", "combined"])),     # semantic meaning
        "is_split_record": Column(bool),
        "voter": Column(str, Check.isin(ESC_CODES + ["WLD"])),
        "voter_is_country": Column(bool),
        "voter_performs_in_round": Column(bool),
        "receiver": Column(str, Check.isin(ESC_CODES)),
        "receiver_contestant_id": Column(int, Check.ge(0)),
        "receiver_place": Column(int, Check.in_range(1, 27)),
        "receiver_running": Column(int, Check.in_range(1, 27)),
        "points": Column(int, Check.isin(TOTAL_POINTS)),
        "jury_method": Column(str, Check.isin(["average_rank", "exponential_weight"]), nullable=True),
        "anomaly_flags": Column(str, Check(flags_ok, element_wise=False), nullable=True),
    },
    checks=[
        Check(lambda d: ~d.duplicated(KEY), error="duplicate primary key"),
        Check(lambda d: d.voter != d.receiver, error="self vote"),
        Check(lambda d: ~d.vote_type.isin(["jury", "public"]) | d.points.isin(SPLIT_POINTS), error="split points domain"),
        Check(lambda d: (d.vote_kind != "jury") | (d.voter != "WLD"), error="WLD has no jury"),
        Check(lambda d: (d.voter != "WLD") | (d.year >= 2023), error="WLD only from 2023"),
        Check(lambda d: (d.vote_kind != "combined") | (d.round_kind == "final") | ~d.year.isin([2023, 2024, 2025]),
              error="2023-25 semis have no combined/jury"),
        Check(lambda d: d.voter_is_country == (d.voter != "WLD"), error="voter_is_country consistent"),
    ],
    strict=True, coerce=True, unique=KEY, name="tidy_votes_v1",
)

if __name__ == "__main__":
    df = pd.read_parquet(os.path.join(sys.argv[1], "tidy_votes.parquet"))
    try:
        tidy_votes_schema.validate(df, lazy=True)
        print(f"PASS tidy_votes_v1: {len(df)} rows x {df.shape[1]} cols")
    except pa.errors.SchemaErrors as e:
        print("FAIL"); print(e.failure_cases.head(50).to_string())
        sys.exit(1)
