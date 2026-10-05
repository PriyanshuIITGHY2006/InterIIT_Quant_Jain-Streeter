"""Market-state behaviour profile of any dataset (protocol v10 §16).

Classifies every day into a named state (Storm, Downtrend, Bear rally, Calm uptrend, Volatile uptrend,
Uptrend, Fading uptrend) with the indicators of src/strategies/market_state.py, and reports how the
data behaves: share of time per state, average spell length, state transitions, what followed each
state (descriptive, looks ahead), and the strategy's average exposure per state.

Run from the project root:
  .venv/bin/python -m scripts.market_state_report BTCUSDT [START] [END]
Writes results/<coin>/market_state_<START>_<END>/ (profile.md, states.png, daily_states.csv).
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.backtest.report import markdown_table
from src.data.loader import load_strategy_data
from src.strategies.market_state import STATE_ORDER, behaviour_profile

COLORS = {"Storm": "#d62728", "Downtrend": "#8c564b", "Bear rally": "#e377c2", "Calm uptrend": "#2ca02c",
          "Volatile uptrend": "#ff7f0e", "Uptrend": "#98df8a", "Fading uptrend": "#bcbd22"}


def main(symbol: str = "BTCUSDT", start: str = "2021-01-01", end: str = "2024-12-31"):
    data = load_strategy_data(symbol, end=end)
    prof = behaviour_profile(data)
    states = prof["states"].loc[start:end]
    out = Path("results") / symbol[:3].lower() / f"market_state_{start[:4]}_{end[:4]}"
    out.mkdir(parents=True, exist_ok=True)
    window = data.loc[start:end]
    summary = window_summary(prof, data, start, end)

    fig, ax = plt.subplots(figsize=(13, 5))
    for state in STATE_ORDER:
        mask = states == state
        ax.scatter(window.index[mask], window["close"][mask], s=5, color=COLORS[state], label=state)
    ax.set_yscale("log")
    ax.set_title(f"{symbol}: market state each day ({start} to {end})")
    ax.legend(markerscale=3, fontsize=8, ncol=4, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "states.png", dpi=120)
    plt.close(fig)

    prof["indicators"].loc[start:end].assign(state=states, target=prof["target"].loc[start:end]).to_csv(out / "daily_states.csv")
    import pandas as pd
    trans = pd.crosstab(states.shift(), states, normalize="index").reindex(index=summary.index, columns=summary.index).fillna(0)
    lines = [f"# {symbol}: market-state behaviour profile, {start} to {end}", "",
             "States are decided each day from indicators calibrated on the data's own history (no look-ahead). "
             "The 'mean next-7d return / volatility' columns are DESCRIPTIVE (they look forward) and are never used by the strategy.", "",
             markdown_table(summary.round(3)), "", "## Transitions (row = today's state, column = tomorrow's)", "",
             markdown_table(trans.round(2)), "",
             f"**Latest state ({states.index[-1].date()}):** {states.iloc[-1]}; target exposure {prof['target'].loc[:end].iloc[-1]:.2f}."]
    (out / "profile.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def window_summary(prof: dict, data, start: str, end: str, horizon: int = 7):
    """Per-state statistics for days in [start, end]. Indicators use all history before `start` (causal);
    the forward return/volatility columns are descriptive and look ahead within the loaded data."""
    import numpy as np
    import pandas as pd
    s = prof["states"].loc[start:end]
    log_ret = np.log(data["close"]).diff()
    fwd_ret = log_ret[::-1].rolling(horizon).sum()[::-1].shift(-1).loc[start:end]
    fwd_vol = (log_ret[::-1].rolling(horizon).std()[::-1].shift(-1) * np.sqrt(365)).loc[start:end]
    spells = (s != s.shift()).cumsum()
    durations = s.groupby(spells).agg(["first", "size"]).groupby("first")["size"].mean()
    return pd.DataFrame({"share of days": s.value_counts(normalize=True), "average spell (days)": durations,
                         f"mean next-{horizon}d return": fwd_ret.groupby(s).mean(),
                         f"next-{horizon}d volatility": fwd_vol.groupby(s).mean(),
                         "average exposure": prof["target"].loc[start:end].groupby(s).mean()}).reindex(
        [x for x in STATE_ORDER if x in set(s)])


if __name__ == "__main__":
    main(*sys.argv[1:])
