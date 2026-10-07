"""Metric formulas checked on tiny hand-made examples."""
import numpy as np
import pandas as pd
import pytest

from src.backtest import BacktestConfig, BacktestResult, compute_metrics, quarterly_comparison
from src.backtest.metrics import drawdown_stats
from tests.helpers import make_bars


@pytest.fixture
def example():
    """Four trades on a 5-day market with a hand-written equity curve."""
    data = make_bars(opens=[100, 100, 110, 120, 130], closes=[100, 110, 120, 130, 130], freq="1D")
    equity = pd.Series([10_000, 10_100, 10_050, 10_250, 10_225], index=data.index, dtype=float)
    hours = pd.to_timedelta([1, 3, 2, 6], unit="h")
    trades = pd.DataFrame({
        "net_pnl": [100.0, -50.0, 200.0, -25.0],
        "fees": [3.0, 3.0, 3.0, 3.0],
        "gross_pnl": [103.0, -47.0, 203.0, -22.0],             # net PnL + fees
        "side": ["long", "long", "short", "long"],
        "duration": hours,
    })
    position = pd.Series([0, 1, 1, 0, 0], index=data.index, dtype=float)
    result = BacktestResult(equity, equity, position, trades, pd.DataFrame(), [], BacktestConfig())
    return result, data, compute_metrics(result, data)


def test_trade_metrics(example):
    _, _, m = example
    assert m["Gross Profit (USDT)"] == 300
    assert m["Gross Loss (USDT)"] == -75
    assert m["Net Profit (USDT)"] == 225                      # = gross profit + gross loss
    assert m["Total Closed Trades"] == 4
    assert m["Win Rate (%)"] == 50
    assert m["Average Winning Trade (USDT)"] == 150
    assert m["Average Losing Trade (USDT)"] == -37.5
    assert m["Largest Winning Trade (USDT)"] == 200
    assert m["Largest Losing Trade (USDT)"] == -50
    assert m["Average Holding Duration"] == pd.Timedelta(hours=3)
    assert m["Maximum Holding Duration"] == pd.Timedelta(hours=6)
    assert m["Long Trades"] == 3 and m["Short Trades"] == 1
    assert m["Total Fees (USDT)"] == 12
    assert m["Trading PnL before Fees (USDT)"] == 237           # = net profit + fees
    assert m["Exposure (%)"] == 40


def test_max_drawdown(example):
    _, _, m = example
    assert m["Max Drawdown (%)"] == pytest.approx(100 * (10_050 / 10_100 - 1))


def test_sharpe_and_sortino(example):
    _, _, m = example
    r = np.array([10_100 / 10_000, 10_050 / 10_100, 10_250 / 10_050, 10_225 / 10_250]) - 1
    sharpe = r.mean() / r.std(ddof=1) * np.sqrt(365)
    sortino = r.mean() / np.sqrt(np.mean(np.minimum(r, 0) ** 2)) * np.sqrt(365)
    assert m["Sharpe Ratio"] == pytest.approx(sharpe)
    assert m["Sortino Ratio"] == pytest.approx(sortino)


def test_buy_and_hold_return(example):
    _, _, m = example
    # Buy at the second bar's open (100), sell at the last close (130), 0.15% each way
    expected = 130 * (1 - 0.0015) / (100 * (1 + 0.0015)) - 1
    assert m["Buy-and-Hold Return (%)"] == pytest.approx(100 * expected)


def test_drawdown_recovery_and_time_under_water():
    index = pd.date_range("2021-01-01", periods=6, freq="1h", tz="UTC")
    equity = pd.Series([100, 120, 90, 110, 125, 124], index=index, dtype=float)
    dd = drawdown_stats(equity)
    assert dd["max_drawdown_pct"] == pytest.approx(-25)
    assert dd["max_dd_recovery"] == pd.Timedelta(hours=3)       # peak at 01:00, back above it at 04:00
    assert dd["longest_underwater"] == pd.Timedelta(hours=3)


def test_quarterly_comparison():
    index = pd.to_datetime(["2021-03-31", "2021-06-30"]).tz_localize("UTC")
    data = pd.DataFrame({"open": [100.0, 100.0], "close": [100.0, 150.0]}, index=index)
    equity = pd.Series([11_000.0, 12_100.0], index=index)
    table = quarterly_comparison(equity, data, 10_000)
    assert list(table["strategy %"].round(6)) == [10.0, 10.0]
    assert list(table["buy & hold %"].round(6)) == [0.0, 50.0]
    assert list(table["beat"]) == [True, False]


def test_deflated_sharpe_penalises_many_trials():
    from src.backtest.evaluation import deflated_sharpe
    rng = np.random.default_rng(0)
    returns = pd.Series(rng.normal(0.001, 0.02, 1000))          # annual Sharpe ~ 0.95
    few = deflated_sharpe(returns, pd.Series(rng.normal(0, 0.3, 5)))
    many = deflated_sharpe(returns, pd.Series(rng.normal(0, 0.3, 2000)))
    assert 0 <= many["deflated Sharpe (probability true Sharpe > 0)"] < few["deflated Sharpe (probability true Sharpe > 0)"] <= 1
