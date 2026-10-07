"""Data analysis of any (unseen) dataset: the checks from our research, run unchanged.

Everything here is DESCRIPTIVE: it summarises the loaded data and is never fed to the strategies.
  1. Return statistics, overall and per calendar year (volatility, Sharpe, drawdown, skew, kurtosis, extremes)
  2. Tails: Hill tail index of daily returns
  3. Direction: lag-1 autocorrelation and variance ratios (is the market trending or mean-reverting?)
  4. Volatility: persistence of log volatility (1 / 7 / 30-day autocorrelation) and the downside share
     of realised variance (the "bad volatility" asymmetry the storm brake is built on)
  5. Market states: the 7 named states of src/strategies/market_state.py, their shares, spells,
     transitions and what followed them
Charts: overview.png (price, drawdown, 30-day volatility), returns.png (distribution vs normal),
states.png (price coloured by market state).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as st

from src.strategies.market_state import STATE_ORDER, behaviour_profile

DAYS = 365
STATE_COLORS = {"Storm": "#d62728", "Downtrend": "#8c564b", "Bear rally": "#e377c2", "Calm uptrend": "#2ca02c",
                "Volatile uptrend": "#ff7f0e", "Uptrend": "#98df8a", "Fading uptrend": "#bcbd22"}


def return_stats(close: pd.Series) -> pd.DataFrame:
    r = close.pct_change().dropna()
    rows = {"all": r} | {str(y): r[r.index.year == y] for y in sorted(set(r.index.year))}
    out = {}
    for label, x in rows.items():
        if len(x) < 20:
            continue
        px = (1 + x).cumprod()
        out[label] = {
            "days": len(x),
            "return %": 100 * (px.iloc[-1] - 1),
            "ann. volatility %": 100 * x.std() * np.sqrt(DAYS),
            "Sharpe": x.mean() / x.std() * np.sqrt(DAYS) if x.std() > 0 else np.nan,
            "max drawdown %": 100 * (px / px.cummax() - 1).min(),
            "skew": x.skew(),
            "excess kurtosis": x.kurt(),
            "best day %": 100 * x.max(),
            "worst day %": 100 * x.min(),
        }
    return pd.DataFrame(out).T


def hill_alpha(r: pd.Series, tail: float = 0.05) -> float:
    """Hill estimator of the tail index of |r| using the largest `tail` share of observations."""
    a = np.sort(np.abs(r.dropna().to_numpy()))[::-1]
    k = max(int(len(a) * tail), 5)
    if len(a) <= k:
        return np.nan
    return 1 / np.mean(np.log(a[:k] / a[k]))


def variance_ratio(r: pd.Series, q: int) -> float:
    r = r.dropna()
    if len(r) < 3 * q:
        return np.nan
    return r.rolling(q).sum().var() / (q * r.var())


def structure(frame: pd.DataFrame) -> dict:
    r = np.log(frame["close"]).diff().dropna()
    log_vol = np.log(frame["rv"].where(frame["rv"] > 0)).dropna()
    return {
        "tail index (Hill, 5% tail)": hill_alpha(r),
        "Jarque-Bera p-value": st.jarque_bera(r).pvalue,
        "lag-1 autocorrelation of returns": r.autocorr(1),
        "variance ratio, 5 days": variance_ratio(r, 5),
        "variance ratio, 20 days": variance_ratio(r, 20),
        "log-volatility autocorrelation, 1 day": log_vol.autocorr(1),
        "log-volatility autocorrelation, 7 days": log_vol.autocorr(7),
        "log-volatility autocorrelation, 30 days": log_vol.autocorr(30),
        "downside share of realised variance": frame["rs_down"].sum() / frame["rv"].sum(),
    }


def interpret(s: dict) -> list[str]:
    """Plain-language reading of the structure checks, using the thresholds from our research."""
    out = []
    a = s["tail index (Hill, 5% tail)"]
    out.append(f"Tails: alpha = {a:.1f}. " + ("Heavy tails (alpha < 4): rely on ranks and percentiles, not z-scores."
                                              if a < 4 else "Moderate tails."))
    vr = s["variance ratio, 20 days"]
    out.append(f"Direction: VR(20) = {vr:.2f}. " + ("Trending over weeks." if vr > 1.1 else
                                                    "Mean-reverting over weeks." if vr < 0.9 else
                                                    "Close to a random walk: direction is hard to predict."))
    p = s["log-volatility autocorrelation, 30 days"]
    out.append(f"Volatility: 30-day autocorrelation of log volatility = {p:.2f}. "
               + ("Volatility is persistent and forecastable, which the regime layers rely on." if p > 0.2
                  else "Volatility is weakly persistent: the regime layers will switch more often."))
    d = s["downside share of realised variance"]
    out.append(f"Asymmetry: {100 * d:.0f}% of realised variance came from down moves.")
    return out


def state_profile(full: pd.DataFrame, start, end, target: pd.Series, horizon: int = 7):
    """States are classified on all history up to each day (causal); statistics cover [start, end].
    The next-7-day columns look ahead and are descriptive only."""
    states = behaviour_profile(full)["states"].loc[start:end]
    log_ret = np.log(full["close"]).diff()
    fwd_ret = log_ret[::-1].rolling(horizon).sum()[::-1].shift(-1).loc[start:end]
    fwd_vol = (log_ret[::-1].rolling(horizon).std()[::-1].shift(-1) * np.sqrt(DAYS)).loc[start:end]
    spells = (states != states.shift()).cumsum()
    order = [x for x in STATE_ORDER if x in set(states)]
    summary = pd.DataFrame({
        "share of days": states.value_counts(normalize=True),
        "average spell (days)": states.groupby(spells).agg(["first", "size"]).groupby("first")["size"].mean(),
        f"mean next-{horizon}d return": fwd_ret.groupby(states).mean(),
        f"next-{horizon}d volatility": fwd_vol.groupby(states).mean(),
        "strategy position (avg)": target.loc[start:end].groupby(states).mean(),
    }).reindex(order)
    transitions = pd.crosstab(states.shift(), states, normalize="index").reindex(index=order, columns=order).fillna(0)
    return summary, transitions, states


def charts(frame: pd.DataFrame, states: pd.Series, out: Path, title: str, color: str):
    close = frame["close"]
    r = close.pct_change()
    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1]})
    axes[0].plot(close, color=color, lw=1)
    axes[0].set_yscale("log")
    axes[0].set_title(f"{title}: price (log)")
    axes[1].fill_between(close.index, 100 * (close / close.cummax() - 1), color="tab:red", alpha=0.4)
    axes[1].set_ylabel("drawdown %")
    axes[2].plot(100 * r.rolling(30).std() * np.sqrt(DAYS), color="tab:purple", lw=1)
    axes[2].set_ylabel("30d vol %")
    fig.tight_layout()
    fig.savefig(out / "overview.png", dpi=120)
    plt.close(fig)

    x = r.dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(100 * x, bins=120, density=True, alpha=0.6, color=color, label="daily returns")
    grid = np.linspace(100 * x.min(), 100 * x.max(), 400)
    ax.plot(grid, st.norm.pdf(grid, 100 * x.mean(), 100 * x.std()), color="black", lw=1, label="normal, same mean and std")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-4)
    ax.set_xlabel("daily return %")
    ax.set_title(f"{title}: return distribution (log density) vs normal")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "returns.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 5))
    for state in STATE_ORDER:
        mask = states == state
        if mask.any():
            ax.scatter(close.index[mask], close[mask], s=5, color=STATE_COLORS[state], label=state)
    ax.set_yscale("log")
    ax.set_title(f"{title}: market state each day")
    ax.legend(markerscale=3, fontsize=8, ncol=4, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "states.png", dpi=120)
    plt.close(fig)


def analyse(full: pd.DataFrame, start, end, target: pd.Series, out: Path, title: str, color: str) -> dict:
    """Describe [start, end] of `full` (earlier rows only warm up the state indicators); write tables and charts."""
    out.mkdir(parents=True, exist_ok=True)
    frame = full.loc[start:end]
    ret = return_stats(frame["close"])
    struct = structure(frame)
    summary, transitions, states = state_profile(full, start, end, target)
    ret.to_csv(out / "return_stats.csv")
    pd.Series(struct, name="value").to_csv(out / "structure.csv")
    summary.to_csv(out / "market_states.csv")
    transitions.to_csv(out / "state_transitions.csv")
    states.to_frame("state").to_csv(out / "daily_states.csv")
    charts(frame, states, out, title, color)
    return {"returns": ret, "structure": struct, "reading": interpret(struct), "states": summary,
            "transitions": transitions, "latest_state": states.iloc[-1]}
