"""Load and clean any OHLC candle file into the frame the strategies expect.

Accepted input (CSV):
  * Binance kline exports, with or without a header (open_time in ms / µs / s, or as text);
  * any table with a time column (timestamp / open_time / date / datetime / time) and open, high, low, close
    (volume, quote_volume, trades and taker columns are used when present).
Bars may be hourly or finer (aggregated to 1h) or daily. Timestamps are bar OPEN times in UTC.

Cleaning follows the rules of src/data/preprocess.py (the competition data pipeline):
  1. sort, drop duplicate timestamps;
  2. repair OHLC so high/low bound open/close; reject non-positive prices;
  3. complete time grid; missing bars become flat candles at the previous close with zero volume,
     flagged is_filled (forward fill only, never interpolation); bars with trades == 0 are outages too;
  4. daily bars built from hourly ones with label="left", closed="left".
The strategy frame is daily bars plus that day's realised measures: from the hourly bars when they exist,
otherwise approximated from the daily candle (src.data.loader.add_daily_proxies).
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loader import add_daily_proxies
from src.features.indicators import realised_measures

PRICE_COLS = ["open", "high", "low", "close"]
VOLUME_COLS = ["volume", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote"]
BINANCE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades",
                   "taker_buy_base", "taker_buy_quote", "ignore"]
TIME_COLUMNS = ["timestamp", "open_time", "datetime", "date", "time"]


@dataclass
class Dataset:
    """A cleaned market dataset."""
    symbol: str
    source: str
    frequency: str                       # "1h" or "1d" (after aggregation)
    hourly: pd.DataFrame | None          # cleaned hourly bars, if the input was intraday
    daily: pd.DataFrame                  # cleaned daily bars
    strategy_frame: pd.DataFrame         # daily bars + realised measures (input to the strategies)
    quality: dict = field(default_factory=dict)


def _parse_time(col: pd.Series) -> pd.DatetimeIndex:
    if pd.api.types.is_numeric_dtype(col):
        v = col.astype("int64")
        unit = "us" if v.abs().max() > 1e14 else "ms" if v.abs().max() > 1e11 else "s"
        return pd.DatetimeIndex(pd.to_datetime(v, unit=unit, utc=True)).as_unit("us")
    return pd.DatetimeIndex(pd.to_datetime(col, utc=True)).as_unit("us")


def read_candles(path: str | Path) -> pd.DataFrame:
    """Read a candle CSV into a UTC-indexed frame with lower-case OHLC(V) columns."""
    path = Path(path)
    raw = pd.read_csv(path)
    if pd.to_numeric(pd.Series([raw.columns[0]]), errors="coerce").notna().all():   # header-less Binance kline dump
        raw = pd.read_csv(path, header=None)
        raw.columns = BINANCE_COLUMNS[: raw.shape[1]] + [f"extra_{i}" for i in range(max(0, raw.shape[1] - 12))]
    raw.columns = [str(c).strip().lower().replace(" ", "_") for c in raw.columns]
    time_col = next((c for c in TIME_COLUMNS if c in raw.columns), None)
    if time_col is None:
        raise ValueError(f"{path}: no time column (expected one of timestamp / open_time / date / datetime / time)")
    missing = [c for c in PRICE_COLS if c not in raw.columns]
    if missing:
        raise ValueError(f"{path}: missing price columns {missing}")
    df = raw.set_index(_parse_time(raw[time_col])).rename_axis("timestamp")
    keep = PRICE_COLS + [c for c in VOLUME_COLS if c in df.columns]
    return df[keep].apply(pd.to_numeric, errors="coerce").sort_index()


def infer_frequency(index: pd.DatetimeIndex) -> pd.Timedelta:
    if len(index) < 3:
        raise ValueError("need at least 3 bars")
    return index.to_series().diff().median()


def clean(df: pd.DataFrame, freq: str) -> tuple[pd.DataFrame, dict]:
    """Steps 1-3 above on bars of frequency `freq` ("1h" or "1D"). Returns the clean frame and a quality report."""
    q = {"rows_in": int(len(df))}
    dupes = df.index.duplicated(keep="first")
    df = df[~dupes].dropna(subset=["close"])
    q["duplicates_removed"] = int(dupes.sum())
    if (df[PRICE_COLS] <= 0).any().any():
        raise ValueError("non-positive prices found")
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    q["ohlc_rows_repaired"] = int(bad.sum())
    df = df.copy()
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    grid = pd.date_range(df.index[0], df.index[-1], freq=freq, name="timestamp")
    off_grid = (~df.index.isin(grid)).sum()
    if off_grid:
        raise ValueError(f"{off_grid} bars are not on the {freq} grid starting {df.index[0]}")
    df = df.reindex(grid)
    missing = df["close"].isna()
    df["close"] = df["close"].ffill()
    for col in ["open", "high", "low"]:
        df[col] = df[col].fillna(df["close"])
    vols = [c for c in VOLUME_COLS if c in df.columns]
    df[vols] = df[vols].fillna(0.0)
    empty = (~missing & (df["trades"] == 0)) if "trades" in df else pd.Series(False, index=df.index)
    df["is_filled"] = missing | empty
    df["return"] = df["close"].pct_change()
    df["log_return"] = np.log(df["close"]).diff()
    q.update({"bars": int(len(df)), "missing_bars_filled": int(missing.sum()), "empty_outage_bars": int(empty.sum()),
              "start": str(df.index[0]), "end": str(df.index[-1])})
    return df, q


def to_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Daily bars from clean hourly bars (label and close on the left: a day is usable at 00:00 UTC next day)."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "is_filled": "sum"}
    agg.update({c: "sum" for c in VOLUME_COLS if c in hourly.columns})
    out = hourly.resample("1D", label="left", closed="left").agg(agg).rename(columns={"is_filled": "filled_hours"})
    if "trades" not in out:                     # no trade counts: a day is an outage only if every hour was missing
        hours = hourly["close"].resample("1D", label="left", closed="left").size()
        out["is_filled"] = out["filled_hours"] >= hours
    out["return"] = out["close"].pct_change()
    out["log_return"] = np.log(out["close"]).diff()
    return out


def load_dataset(path: str | Path, symbol: str) -> Dataset:
    """Read, clean and prepare a candle file for analysis and the strategies."""
    df = read_candles(path)
    step = infer_frequency(df.index)
    if step <= pd.Timedelta(hours=1):
        if step < pd.Timedelta(hours=1):
            agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
            agg.update({c: "sum" for c in VOLUME_COLS if c in df.columns})
            df = df.resample("1h", label="left", closed="left").agg(agg).dropna(subset=["close"])
        hourly, q = clean(df, "1h")
        last_day = hourly.index[-1].floor("1D")
        q["incomplete_last_day_dropped"] = bool(hourly.index[-1] < last_day + pd.Timedelta(hours=23))
        if q["incomplete_last_day_dropped"]:      # a day is only known once its last hour has closed
            hourly = hourly.loc[: last_day - pd.Timedelta(hours=1)]
        daily = to_daily(hourly)
        frame = daily.join(realised_measures(hourly)[["rv", "rs_up", "rs_down", "bv"]], how="left")
        frequency, q["realised_measures"] = "1h", "from hourly bars"
    elif step == pd.Timedelta(days=1):
        daily, q = clean(df, "1D")
        hourly, frame, frequency = None, add_daily_proxies(daily), "1d"
        q["realised_measures"] = "approximated from daily candles (no intraday data)"
    else:
        raise ValueError(f"unsupported bar length {step}: use hourly (or finer) or daily candles")
    q["input_bar"] = "1d" if step == pd.Timedelta(days=1) else f"{int(step.total_seconds() // 60)}min" if step < pd.Timedelta(hours=1) else "1h"
    q["days"] = int(len(daily))
    return Dataset(symbol=symbol, source=str(path), frequency=frequency, hourly=hourly, daily=daily,
                   strategy_frame=frame, quality=q)
