"""Small hand-made markets for tests."""
import numpy as np
import pandas as pd


def make_bars(opens, highs=None, lows=None, closes=None, filled=None, freq="1h") -> pd.DataFrame:
    """Build an OHLC frame. Missing highs/lows/closes default to flat bars at the open."""
    opens = np.asarray(opens, dtype=float)
    closes = opens if closes is None else np.asarray(closes, dtype=float)
    highs = np.maximum(opens, closes) if highs is None else np.asarray(highs, dtype=float)
    lows = np.minimum(opens, closes) if lows is None else np.asarray(lows, dtype=float)
    index = pd.date_range("2021-01-01", periods=len(opens), freq=freq, tz="UTC", name="timestamp")
    filled = np.zeros(len(opens), dtype=bool) if filled is None else np.asarray(filled, dtype=bool)
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": closes,
        "trades": np.where(filled, 0, 100), "is_filled": filled,
    }, index=index)


def signals(data: pd.DataFrame, target, **levels) -> pd.DataFrame:
    """Signals frame with a target per bar plus optional constant level columns."""
    out = pd.DataFrame({"target": np.asarray(target, dtype=float)}, index=data.index)
    for name, value in levels.items():
        out[name] = value
    return out


def random_walk(n: int, seed: int, vol: float = 0.01, start: float = 100.0) -> pd.DataFrame:
    """Zero-drift random-walk prices with a little intrabar range."""
    rng = np.random.default_rng(seed)
    closes = start * np.exp(np.cumsum(rng.normal(-vol ** 2 / 2, vol, n)))
    opens = np.concatenate([[start], closes[:-1]])
    wiggle = np.abs(rng.normal(0, vol / 2, n))
    highs = np.maximum(opens, closes) * (1 + wiggle)
    lows = np.minimum(opens, closes) * (1 - wiggle)
    return make_bars(opens, highs, lows, closes)
