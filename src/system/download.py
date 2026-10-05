"""Download hourly candles from Binance's public market-data API (no account or key needed).

Writes a CSV in Binance kline format (timestamp = bar open time, UTC) that `ctr run` reads directly.
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://data-api.binance.vision/api/v3/klines"
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades",
           "taker_buy_base", "taker_buy_quote"]
HOUR_MS = 3_600_000


def download(symbol: str, start: str, end: str, interval: str = "1h", log=print) -> pd.DataFrame:
    """All `interval` klines whose open time is in [start, end] (UTC)."""
    t0 = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    t_end = pd.Timestamp(end, tz="UTC")
    if t_end == t_end.normalize():                 # a plain date means "through the end of that day"
        t_end += pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    t1 = int(t_end.timestamp() * 1000)
    rows, cursor = [], t0
    while cursor <= t1:
        url = f"{URL}?symbol={symbol}&interval={interval}&startTime={cursor}&endTime={t1}&limit=1000"
        for attempt in range(5):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    batch = json.loads(r.read())
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
        if not batch:
            break
        rows += batch
        cursor = batch[-1][0] + 1
        log(f"  {symbol}: {len(rows):,} bars, up to {pd.Timestamp(batch[-1][0], unit='ms')}")
        time.sleep(0.2)
    if not rows:
        raise ValueError(f"no {symbol} data between {start} and {end}")
    df = pd.DataFrame([r[:11] for r in rows], columns=COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    df = df.drop_duplicates("timestamp")
    return df[df["close_time"] < pd.Timestamp.now(tz="UTC").tz_localize(None)]   # only bars that have closed


def download_to(symbol: str, start: str, end: str, out_dir: str | Path, log=print) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = download(symbol, start, end, log=log)
    path = out_dir / f"{symbol}_1h_{pd.Timestamp(start):%Y%m%d}_{pd.Timestamp(end):%Y%m%d}.csv"
    df.to_csv(path, index=False)
    return path
