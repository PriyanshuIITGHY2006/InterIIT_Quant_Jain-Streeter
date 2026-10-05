"""The strategy and data-analysis system (src/system/): input handling, causality, and exact reproduction."""
import json

import numpy as np
import pandas as pd
import pytest

from src.data.loader import load_daily_with_realised
from src.system.ingest import load_dataset, read_candles
from src.system.pipeline import run
from src.system.strategies import get, guess_asset

RAW_BTC = "data/raw/BTCUSDT_1h.csv"


def _hourly_csv(path, hours=24 * 40, drop=(), header=True, start="2024-01-01"):
    idx = pd.date_range(start, periods=hours, freq="1h", tz="UTC")
    rng = np.random.default_rng(0)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, hours)))
    df = pd.DataFrame({"timestamp": idx, "open": np.r_[100, close[:-1]], "high": close * 1.01, "low": close * 0.99,
                       "close": close, "volume": 1.0, "trades": 10})
    df = df.drop(index=list(drop))
    if header:
        df.to_csv(path, index=False)
    else:  # Binance kline dump: no header, open time in ms, 12 columns
        ms = (df["timestamp"].astype("int64") // 1000).astype("int64")
        pd.DataFrame({0: ms, 1: df.open, 2: df.high, 3: df.low, 4: df.close, 5: df.volume, 6: ms + 3_599_999,
                      7: df.volume * df.close, 8: df.trades, 9: 0.5, 10: 50.0, 11: 0}).to_csv(path, index=False, header=False)
    return df


def test_ingest_matches_competition_pipeline():
    """The system's cleaning reproduces data/processed exactly on the competition file."""
    frame = load_dataset(RAW_BTC, "BTCUSDT").strategy_frame
    ref = load_daily_with_realised("BTCUSDT")
    cols = ["open", "high", "low", "close", "trades", "filled_hours", "rv", "rs_up", "rs_down", "bv"]
    pd.testing.assert_frame_equal(frame[cols], ref[cols], check_freq=False)


def test_run_reproduces_the_frozen_btc_backtest(tmp_path):
    """Raw competition candles -> system -> the published 2021-2025 BTC result."""
    res = run(RAW_BTC, "btc", "2021-01-01", "2025-12-31", tmp_path, verify=False, log=lambda *_: None)
    m = res["metrics"]
    assert m["Total Return (%)"] == pytest.approx(368.40, abs=0.01)
    assert m["Total Closed Trades"] == 36 and m["Short Trades"] == 15
    for f in ["report.md", "manifest.json", "signal_today.json", "daily_signals.csv", "backtest/trades.csv",
              "backtest/equity.png", "analysis/market_states.csv", "analysis/states.png"]:
        assert (tmp_path / f).exists(), f
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["period"] == ["2021-01-01", "2025-12-31"]


def test_binance_headerless_and_generic_formats_agree(tmp_path):
    _hourly_csv(tmp_path / "a.csv")
    _hourly_csv(tmp_path / "b.csv", header=False)
    a, b = read_candles(tmp_path / "a.csv"), read_candles(tmp_path / "b.csv")
    pd.testing.assert_frame_equal(a[["open", "high", "low", "close"]], b[["open", "high", "low", "close"]], check_freq=False)


def test_gaps_are_filled_forward_and_flagged(tmp_path):
    _hourly_csv(tmp_path / "g.csv", drop=(100, 101, 102))
    ds = load_dataset(tmp_path / "g.csv", "BTCUSDT")
    assert ds.quality["missing_bars_filled"] == 3
    h = ds.hourly
    assert h["is_filled"].sum() == 3
    assert (h["close"].iloc[100:103] == h["close"].iloc[99]).all()      # previous close, never interpolated
    assert (h["volume"].iloc[100:103] == 0).all()


def test_incomplete_last_day_is_dropped(tmp_path):
    """A day is only known once its last hour has closed; a partial final day must not drive a decision."""
    _hourly_csv(tmp_path / "p.csv", hours=24 * 40 + 5)
    ds = load_dataset(tmp_path / "p.csv", "BTCUSDT")
    assert ds.quality["incomplete_last_day_dropped"]
    assert ds.daily.index[-1] == pd.Timestamp("2024-02-09", tz="UTC")


def test_daily_input_uses_candle_proxies(tmp_path):
    d = pd.read_csv("data/raw/BTCUSDT_1d.csv").rename(columns={"timestamp": "Date"})
    d = d[["Date", "open", "high", "low", "close", "volume"]].rename(columns=str.capitalize)
    d.to_csv(tmp_path / "btc_daily.csv", index=False)
    ds = load_dataset(tmp_path / "btc_daily.csv", "BTCUSDT")
    assert ds.frequency == "1d" and ds.hourly is None
    assert {"rv", "rs_down", "bv"} <= set(ds.strategy_frame.columns)


def test_strategy_registry_is_frozen():
    assert get("BTCUSDT").config().allow_short and not get("eth").config().allow_short
    assert guess_asset("data/ETHUSDT_1h.csv") == "eth" and guess_asset("prices.csv") is None
    with pytest.raises(ValueError):
        get("sol")
