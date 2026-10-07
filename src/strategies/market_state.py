"""Market-state framework (evaluation protocol v10 §16).

Every day, at the close, the indicators answer five questions about the market. Each answer is
calibrated against the dataset's OWN history (trailing/expanding percentiles and medians), so the same
rules work on any new dataset from a cold start:

  1. Direction    is price above its moving averages?           7 banded trend votes (0..1)
  2. Big picture  is the slow (200-day) trend up?                banded 200-day gate (1 / 0)
  3. Weather      is the market calm or stormy for this asset?   volatility percentile vs the past year
  4. Quality      is the move orderly or choppy?                 efficiency ratio vs its history, Choppiness
  5. Danger       is sell-off risk unusually high? compressed?   storm brake, Bollinger-Keltner squeeze

The answers give (a) a NAMED STATE for analysis and reporting, and (b) the position size:
  target = trend votes x regime size x storm brake x squeeze  (capped at 1.5)  x soft gate
where regime size is 1.5 on calm-trend days, 0.6 on stormy days, 1.0 otherwise.

`StateParams()` with its defaults is the final BTC strategy, Calm-Trend Regime (CTR, research ID F1);
the options are the pre-registered refinements H1-H3 of protocol §16, tested and not adopted.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.features import indicators as ind
from src.features.trend import daily_vol, ma_state_with_band, sma

DAYS = 365
TREND_LOOKBACKS = (20, 30, 50, 75, 100, 150, 200)
STATE_ORDER = ["Storm", "Downtrend", "Bear rally", "Calm uptrend", "Volatile uptrend", "Uptrend", "Fading uptrend"]


@dataclass
class StateParams:
    vol_threshold: float = 0.5          # volatility percentile above which a day is "stormy"
    high_vol_size: float = 0.6          # size on stormy days
    calm_leverage: float = 1.5          # size on calm-trend days (maximum exposure)
    chop_trend_level: float = 38.2      # Choppiness below this = clean trend
    storm_multiple: float = 1.5         # brake when the risk forecast exceeds this x its 1-year median
    storm_cut: float = 0.5
    storm_forecast: str = "smooth_downside"   # CTR: 0.5 x bipower + downside semivariance; H3: "downside"
    squeeze_cut: float = 0.75
    gate_lookback: int = 200
    gate_floor: float = 0.5
    calm_smoothing: int | None = None   # H1: calm-trend = majority of the last N days' condition
    agreement_votes: int | None = None  # H2: calm-trend also when >= this many trend votes are up (gate up, not stormy)


# ---------------------------------------------------------------- the five questions
def trend_votes(close: pd.Series) -> pd.Series:
    band = daily_vol(close)
    votes = [ma_state_with_band(close, n, band, adaptive=True) for n in TREND_LOOKBACKS]
    return pd.concat(votes, axis=1).mean(axis=1)


def slow_gate(close: pd.Series, lookback: int = 200) -> pd.Series:
    state = ma_state_with_band(close, lookback, daily_vol(close), adaptive=True)
    return state.where(sma(close, lookback, adaptive=True).notna()).fillna(0.0)


def vol_percentile(data: pd.DataFrame) -> pd.Series:
    return ind.rolling_percentile(ind.parkinson_vol(data, 14), window=365, min_periods=30)


def risk_forecast(data: pd.DataFrame, kind: str = "smooth_downside", span: int = 30) -> pd.Series:
    """Annualised sell-off-risk forecast from hourly realised measures (or their daily proxies)."""
    proxy = 0.5 * data["bv"] + data["rs_down"] if kind == "smooth_downside" else 2 * data["rs_down"]
    return np.sqrt(DAYS * proxy.ewm(span=span, min_periods=10).mean())


def market_indicators(data: pd.DataFrame, p: StateParams = StateParams()) -> pd.DataFrame:
    """Every indicator the framework uses, one column each (all known at the day's close)."""
    close = data["close"]
    votes = trend_votes(close)
    gate = slow_gate(close, p.gate_lookback)
    pct = vol_percentile(data)
    stormy = pct > p.vol_threshold
    er = ind.efficiency_ratio(close, 30)
    efficient = er > er.expanding(min_periods=90).median()
    chop = ind.choppiness(data, 14)
    calm_cond = ((pct <= p.vol_threshold) & efficient) | (chop < p.chop_trend_level)
    if p.agreement_votes is not None:
        calm_cond |= (votes >= p.agreement_votes / len(TREND_LOOKBACKS) - 1e-9) & (gate == 1) & ~stormy
    if p.calm_smoothing is not None:
        calm_cond = calm_cond.astype(float).rolling(p.calm_smoothing, min_periods=1).mean() > 0.5
    forecast = risk_forecast(data, p.storm_forecast)
    storm = forecast > p.storm_multiple * forecast.rolling(365, min_periods=90).median()
    return pd.DataFrame({"trend_votes": votes, "gate": gate, "vol_percentile": pct, "stormy": stormy,
                         "efficiency": er, "efficient": efficient, "choppiness": chop, "calm_trend": calm_cond,
                         "risk_forecast": forecast, "storm": storm, "squeeze": ind.squeeze(data) == 1},
                        index=data.index)


# ---------------------------------------------------------------- decisions
def layers(mi: pd.DataFrame, p: StateParams = StateParams()) -> pd.DataFrame:
    """Each sizing layer as a multiplier."""
    regime = np.select([mi["calm_trend"], mi["stormy"]], [p.calm_leverage, p.high_vol_size], 1.0)
    return pd.DataFrame({"trend": mi["trend_votes"], "regime": regime,
                         "storm_brake": np.where(mi["storm"], p.storm_cut, 1.0),
                         "squeeze": np.where(mi["squeeze"], p.squeeze_cut, 1.0),
                         "gate": p.gate_floor + (1 - p.gate_floor) * mi["gate"]}, index=mi.index)


def target_exposure(data: pd.DataFrame, p: StateParams = StateParams()) -> pd.Series:
    lay = layers(market_indicators(data, p), p)
    sized = (lay["trend"] * lay["regime"] * lay["storm_brake"] * lay["squeeze"]).clip(0, p.calm_leverage)
    return sized * lay["gate"]


def classify(mi: pd.DataFrame) -> pd.Series:
    """Named market state for each day (descriptive; priority order = STATE_ORDER)."""
    up = mi["trend_votes"] >= 0.5
    gate_up = mi["gate"] == 1
    label = np.select(
        [mi["storm"], ~gate_up & ~up, ~gate_up & up, gate_up & up & mi["calm_trend"], gate_up & up & mi["stormy"],
         gate_up & up, gate_up & ~up],
        STATE_ORDER, "Undefined")
    return pd.Series(label, index=mi.index, name="state")


# ---------------------------------------------------------------- behaviour profile of any dataset
def behaviour_profile(data: pd.DataFrame, p: StateParams = StateParams(), horizon: int = 7) -> dict:
    """How this dataset behaves, state by state.

    shares/durations/transitions describe the market; forward return and volatility per state are
    DESCRIPTIVE statistics (they look ahead and are never used by the strategy).
    """
    mi = market_indicators(data, p)
    states = classify(mi)
    target = target_exposure(data, p)
    log_ret = np.log(data["close"]).diff()
    fwd_ret = log_ret[::-1].rolling(horizon).sum()[::-1].shift(-1)
    fwd_vol = log_ret[::-1].rolling(horizon).std()[::-1].shift(-1) * np.sqrt(DAYS)
    spells = (states != states.shift()).cumsum()
    durations = states.groupby(spells).agg(["first", "size"]).groupby("first")["size"].mean()
    summary = pd.DataFrame({
        "share of days": states.value_counts(normalize=True),
        "average spell (days)": durations,
        f"mean next-{horizon}d return": fwd_ret.groupby(states).mean(),
        f"next-{horizon}d volatility": fwd_vol.groupby(states).mean(),
        "average exposure": target.groupby(states).mean(),
    }).reindex([s for s in STATE_ORDER if s in set(states)])
    transitions = pd.crosstab(states.shift(), states, normalize="index").reindex(index=summary.index, columns=summary.index)
    return {"indicators": mi, "states": states, "target": target, "summary": summary, "transitions": transitions}
