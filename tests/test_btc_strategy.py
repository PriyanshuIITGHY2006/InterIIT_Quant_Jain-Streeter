"""Final BTC strategy (CTR-S: Calm-Trend Regime with calm-bear shorts): causal, bounded, and its frozen 2021-2024 results unchanged."""
import numpy as np
import pandas as pd
import pytest

from src.backtest.checks import check_backtest_truncation, check_signals_causal
from src.data.loader import load_daily_with_realised
from src.strategies.btc_strategy import SHORT_SIZE, btc_signal, ctr_long_signal, short_condition
from src.strategies.execution import btc_trading_config


@pytest.fixture(scope="module")
def btc():
    return load_daily_with_realised("BTCUSDT", end="2024-12-31")


def test_signal_is_causal(btc):
    check_signals_causal(btc_signal, btc)


def test_backtest_truncation(btc):
    check_backtest_truncation(btc_signal, btc, btc_trading_config(), cut=900)


def test_target_bounds(btc):
    target = btc_signal(btc)["target"]
    assert target.between(-SHORT_SIZE, 1.5).all() and np.isfinite(target).all()
    assert set(target[target < 0].unique()) <= {-SHORT_SIZE}


def test_short_only_when_ctr_is_flat(btc):
    """The short side never overrides a long: it acts only on days the long-only CTR holds nothing."""
    short = short_condition(btc)
    assert (ctr_long_signal(btc)["target"][short] == 0).all()
    assert (btc_signal(btc)["target"][~short] == ctr_long_signal(btc)["target"][~short]).all()


def test_frozen_results_2021_2024(btc):
    """Regression guard: the frozen strategy's 2021-2024 backtest must not change."""
    from src.backtest.evaluation import run_on_period
    from src.backtest.metrics import compute_metrics
    result, period = run_on_period(btc, btc_signal, "2021-01-01", "2024-12-31", btc_trading_config(), check=False)
    m = compute_metrics(result, period)
    assert m["Total Closed Trades"] == 31
    assert m["Short Trades"] == 13
    assert m["Total Return (%)"] == pytest.approx(388.85, abs=0.01)
    assert m["Sharpe Ratio"] == pytest.approx(1.1634, abs=1e-3)
    assert m["Max Drawdown (%)"] == pytest.approx(-29.56, abs=0.01)

