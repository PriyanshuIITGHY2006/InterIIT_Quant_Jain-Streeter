"""Load the processed candle files."""
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def load_market(symbol: str, timeframe: str = "1h", split: str = "full") -> pd.DataFrame:
    """symbol: BTCUSDT / ETHUSDT, timeframe: 1h / 4h / 1d, split: full / train / val / test."""
    path = PROCESSED_DIR / timeframe / f"{symbol}_{split}.csv"
    return pd.read_csv(path, index_col="timestamp", parse_dates=True)


def load_daily_with_realised(symbol: str, end: str | None = None) -> pd.DataFrame:
    """Daily bars plus that day's realised measures from hourly bars (rv, rs_up, rs_down, bv).

    Each day's measures use only the hours inside that day, so they are known at the day's close.
    `end` (e.g. "2024-12-31") cuts both files so nothing after it is ever loaded.
    """
    from src.features.indicators import realised_measures
    daily, hourly = load_market(symbol, "1d", "full"), load_market(symbol, "1h", "full")
    if end is not None:
        daily, hourly = daily.loc[:end], hourly.loc[:end]
    return daily.join(realised_measures(hourly)[["rv", "rs_up", "rs_down", "bv"]], how="left")


def add_daily_proxies(daily: pd.DataFrame) -> pd.DataFrame:
    """Fallback when no hourly data exists: approximate the realised measures from each daily candle.

    rv       Parkinson daily variance  ln(high/low)^2 / (4 ln 2)
    bv       = rv (a single candle cannot separate jumps)
    rs_down  rv x share of the range below the open:  ln(open/low)^2 / (ln(open/low)^2 + ln(high/open)^2)
    rs_up    rv - rs_down
    Uses only the day's own candle, so it is known at the day's close.
    """
    import numpy as np
    out = daily.copy()
    rv = np.log(out["high"] / out["low"]) ** 2 / (4 * np.log(2))
    down, up = np.log(out["open"] / out["low"]) ** 2, np.log(out["high"] / out["open"]) ** 2
    share = (down / (down + up)).where(down + up > 0, 0.5)
    out["rv"], out["bv"], out["rs_down"] = rv, rv, rv * share
    out["rs_up"] = rv - out["rs_down"]
    return out


def load_strategy_data(symbol: str, end: str | None = None) -> pd.DataFrame:
    """Daily bars with realised measures: from hourly bars when the hourly file exists, otherwise
    approximated from the daily candles (add_daily_proxies), so a strategy runs on any dataset."""
    if (PROCESSED_DIR / "1h" / f"{symbol}_full.csv").exists():
        return load_daily_with_realised(symbol, end)
    daily = load_market(symbol, "1d", "full")
    return add_daily_proxies(daily.loc[:end] if end else daily)
