"""Trend building blocks (in-house, causal: the value on bar t uses data up to bar t's close)."""
import numpy as np
import pandas as pd

MIN_WARMUP = 10     # adaptive warm-up: an average needs at least this many bars


def sma(close: pd.Series, n: int, adaptive: bool = False) -> pd.Series:
    """n-bar simple moving average. With adaptive=True it uses all bars so far until it has n of them
    (at least MIN_WARMUP), so a strategy can act from the start of any dataset."""
    return close.rolling(n, min_periods=min(n, MIN_WARMUP) if adaptive else n).mean()


def daily_vol(close: pd.Series, span: int = 60) -> pd.Series:
    """EWMA standard deviation of daily log returns (a fraction per day)."""
    log_ret = np.log(close).diff()
    return np.sqrt((log_ret ** 2).ewm(span=span, min_periods=20).mean())


def ma_state_with_band(close: pd.Series, n: int, band: pd.Series, adaptive: bool = False) -> pd.Series:
    """1/0 trend state with hysteresis: switches to 1 only above average x (1 + band), back to 0 only
    below average x (1 - band); in between it keeps its previous state (fewer whipsaws)."""
    average = sma(close, n, adaptive).to_numpy()
    c, b = close.to_numpy(), band.to_numpy()
    state = np.zeros(len(c))
    current = 0.0
    for t in range(len(c)):
        if not np.isnan(average[t]) and not np.isnan(b[t]):
            if c[t] > average[t] * (1 + b[t]):
                current = 1.0
            elif c[t] < average[t] * (1 - b[t]):
                current = 0.0
        state[t] = current
    return pd.Series(state, index=close.index)
