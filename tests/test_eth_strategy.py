"""Final ETH strategy (Calm-Trend Regime for ETH): causal, bounded, identical rules to BTC, frozen results."""
import numpy as np
import pandas as pd
import pytest

from src.backtest.checks import check_backtest_truncation, check_signals_causal
from src.backtest.evaluation import run_on_period
from src.backtest.metrics import compute_metrics
from src.data.loader import load_daily_with_realised
from src.strategies.btc_strategy import btc_signal
from src.strategies.eth_strategy import eth_signal
from src.strategies.execution import trading_config


@pytest.fixture(scope="module")
def eth():
    return load_daily_with_realised("ETHUSDT", end="2024-12-31")


def test_signal_is_causal(eth):
    check_signals_causal(eth_signal, eth)


def test_backtest_truncation(eth):
    check_backtest_truncation(eth_signal, eth, trading_config(), cut=900)


def test_target_bounds(eth):
    target = eth_signal(eth)["target"]
    assert target.between(0, 1.5).all() and np.isfinite(target).all()


def test_same_rules_as_btc(eth):
    pd.testing.assert_frame_equal(eth_signal(eth), btc_signal(eth))


def test_frozen_results_2021_2024(eth):
    """Regression guard: the frozen strategy's 2021-2024 ETH backtest must not change."""
    result, period = run_on_period(eth, eth_signal, "2021-01-01", "2024-12-31", trading_config(), check=False)
    m = compute_metrics(result, period)
    assert m["Total Closed Trades"] == 18
    assert m["Total Return (%)"] == pytest.approx(274.14, abs=0.01)
    assert m["Sharpe Ratio"] == pytest.approx(0.8983, abs=1e-3)
    assert m["Max Drawdown (%)"] == pytest.approx(-37.34, abs=0.01)
