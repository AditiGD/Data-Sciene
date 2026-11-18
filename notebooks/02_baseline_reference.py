# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 02 · Reference baseline (proposal metric)
#
# `excess = points - mean points the receiver got from the other voters`, per year,
# round and vote type. This is the **reference** metric from the proposal, not the
# primary estimator: it is biased toward zero for cohesive blocs (plan review C1), and
# raw rankings of dyads suffer from the winner's curse (M2). Always read `n_obs`.
#
# Wording: "excess points" / "dyadic affinity", not "favouritism" (plan review m7).

# %%
import pandas as pd

from esc_bias.baseline import add_baseline, pair_summary
from esc_bias.config import load_config

cfg = load_config()
votes = pd.read_parquet(cfg.processed_dir / "votes.parquet")
primary = votes[~votes["exclude"]]  # register-driven filter (WLD, SM televote, substitutes)

# %%
scored = add_baseline(primary[primary["vote_type"].isin(["jury", "televote"])])
pairs = pair_summary(scored, "excess")
pairs.head()

# %% [markdown]
# ## Dyads with the largest mean excess (minimum 8 observations), per vote type

# %%
MIN_OBS = 8
(
    pairs[pairs["n_obs"] >= MIN_OBS]
    .sort_values("mean", ascending=False)
    .groupby("vote_type")
    .head(10)
    .round(2)
)
