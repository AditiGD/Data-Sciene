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
# # 01 · Data overview
#
# What is in the tidy vote table: coverage per year, round and vote type, the share
# of explicit zeros, and which rows the anomaly register flags.
#
# **Prerequisite:** `make data` (writes `data/processed/votes.parquet`).
# This notebook only *reads* pipeline outputs; all logic lives in `src/esc_bias/`.

# %%
import json

import matplotlib.pyplot as plt
import pandas as pd

from esc_bias.config import load_config
from esc_bias.viz import VOTE_TYPE_COLORS, save_figure, set_style

cfg = load_config()
set_style()
votes = pd.read_parquet(cfg.processed_dir / "votes.parquet")
meta = json.loads((cfg.processed_dir / "metadata.json").read_text())
print("raw data commit:", meta["raw_git_commit"], "| rows:", len(votes))

# %% [markdown]
# ## Coverage: voters per year, round and vote type

# %%
coverage = votes.pivot_table(
    index=["year", "round"], columns="vote_type", values="voter", aggfunc="nunique"
)
coverage

# %% [markdown]
# ## Share of zero points per vote type (why explicit zeros matter)

# %%
votes.groupby("vote_type")["points"].apply(lambda s: (s == 0).mean()).round(3)

# %% [markdown]
# ## Anomaly register: flagged rows

# %%
votes[votes["is_flagged"]].groupby(["anomaly_ids", "vote_type"]).size()

# %% [markdown]
# ## Figure: number of voters per final, by vote type

# %%
finals = coverage.xs("final", level="round")
fig, ax = plt.subplots(figsize=(7, 3.5))
for vote_type in ("jury", "televote"):
    ax.plot(
        finals.index,
        finals[vote_type],
        marker="o",
        color=VOTE_TYPE_COLORS[vote_type],
        label=vote_type,
    )
ax.set(xlabel="Year", ylabel="Voters in the final", title="Voters per Grand Final")
ax.legend()
save_figure(fig, "fig01_voters_per_final", cfg.figures_dir)
