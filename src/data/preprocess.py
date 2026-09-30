"""Clean raw Binance candles and save analysis-ready files to data/processed/.

Run from the project root:
    .venv/bin/python -m src.data.preprocess

Steps
  1. Load, set types, sort, drop duplicate timestamps
  2. Validate OHLC (high/low must bound open/close, prices > 0)
  3. Reindex to a complete hourly grid; fill missing hours with flat candles
     (O=H=L=C = previous close, volume = 0) and flag them with is_filled
  4. Check BTC and ETH share the same timestamps
  5. Add simple and log returns; build 4h and 1d candles from the hourly data
  6. Split into train / validation / test and save
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
START, END = "2021-01-01 00:00", "2025-12-31 23:00"
SPLITS = {
    "train": ("2021-01-01", "2023-12-31"),
    "val": ("2024-01-01", "2024-12-31"),
    "test": ("2025-01-01", "2025-12-31"),
}
PRICE_COLS = ["open", "high", "low", "close"]
VOLUME_COLS = ["volume", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote"]


def load_raw(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / f"{symbol}_1h.csv", parse_dates=["timestamp"])
    df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    df = df.drop(columns=["close_time"]).set_index("timestamp")
    df = df.astype(float).sort_index()

    n_dupes = df.index.duplicated().sum()
    df = df[~df.index.duplicated(keep="first")]
    print(f"  duplicates removed: {n_dupes}")
    return df


def validate_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if (df[PRICE_COLS] <= 0).any().any():
        raise ValueError("non-positive prices found")

    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    print(f"  invalid OHLC rows fixed: {bad.sum()}")
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    return df


def fill_gaps(df: pd.DataFrame) -> pd.DataFrame:
    grid = pd.date_range(START, END, freq="1h", tz="UTC", name="timestamp")
    df = df.reindex(grid)
    df["is_filled"] = df["close"].isna()

    # Flat candle at the last traded price; the exchange was down, so nothing traded
    df["close"] = df["close"].ffill()
    for col in ["open", "high", "low"]:
        df[col] = df[col].fillna(df["close"])
    df[VOLUME_COLS] = df[VOLUME_COLS].fillna(0.0)

    print(f"  missing hours filled: {df['is_filled'].sum()}  (total rows: {len(df)})")
    return df


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    df["return"] = df["close"].pct_change()
    df["log_return"] = np.log(df["close"]).diff()
    return df


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "is_filled": "sum"}
    agg.update({col: "sum" for col in VOLUME_COLS})
    out = df.resample(rule, label="left", closed="left").agg(agg)
    out = out.rename(columns={"is_filled": "filled_hours"})
    return add_returns(out)


def save(df: pd.DataFrame, symbol: str, timeframe: str):
    out_dir = PROCESSED_DIR / timeframe
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / f"{symbol}_full.csv")
    for name, (start, end) in SPLITS.items():
        df.loc[start:end].to_csv(out_dir / f"{symbol}_{name}.csv")


def main():
    hourly = {}
    for symbol in SYMBOLS:
        print(symbol)
        df = load_raw(symbol)
        df = validate_ohlc(df)
        df = fill_gaps(df)
        hourly[symbol] = add_returns(df)

    btc, eth = (hourly[s].index for s in SYMBOLS)
    if not btc.equals(eth):
        raise ValueError("BTC and ETH timestamps do not match")
    print("BTC/ETH timestamps aligned")

    for symbol, df in hourly.items():
        save(df, symbol, "1h")
        save(resample(df, "4h"), symbol, "4h")
        save(resample(df, "1D"), symbol, "1d")
    print(f"saved to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
