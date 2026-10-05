"""Final BTC strategy (Calm-Trend Regime): causal, bounded, and its frozen 2021-2024 results unchanged."""
import numpy as np
import pandas as pd
import pytest

from src.backtest.checks import check_backtest_truncation, check_signals_causal
from src.data.loader import load_daily_with_realised
from src.strategies.btc_strategy import btc_signal
from src.strategies.execution import trading_config


@pytest.fixture(scope="module")
def btc():
    return load_daily_with_realised("BTCUSDT", end="2024-12-31")


def test_signal_is_causal(btc):
    check_signals_causal(btc_signal, btc)


def test_backtest_truncation(btc):
    check_backtest_truncation(btc_signal, btc, trading_config(), cut=900)


def test_target_bounds(btc):
    target = btc_signal(btc)["target"]
    assert target.between(0, 1.5).all() and np.isfinite(target).all()


def test_frozen_results_2021_2024(btc):
    """Regression guard: the frozen strategy's 2021-2024 backtest must not change."""
    from src.backtest.evaluation import run_on_period
    from src.backtest.metrics import compute_metrics
    result, period = run_on_period(btc, btc_signal, "2021-01-01", "2024-12-31", trading_config(), check=False)
    m = compute_metrics(result, period)
    assert m["Total Closed Trades"] == 18
    assert m["Total Return (%)"] == pytest.approx(373.15, abs=0.01)
    assert m["Sharpe Ratio"] == pytest.approx(1.1588, abs=1e-3)
    assert m["Max Drawdown (%)"] == pytest.approx(-37.53, abs=0.01)

