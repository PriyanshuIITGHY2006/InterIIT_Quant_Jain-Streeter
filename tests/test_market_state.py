"""Market-state framework: causal with every option, daily fallback works, profile is consistent."""
import numpy as np
import pandas as pd
import pytest

from src.backtest.checks import check_signals_causal
from src.data.loader import add_daily_proxies, load_daily_with_realised, load_market
from src.strategies.market_state import StateParams, behaviour_profile, target_exposure


@pytest.fixture(scope="module")
def btc():
    return load_daily_with_realised("BTCUSDT", end="2024-12-31")


@pytest.mark.parametrize("params", [StateParams(calm_smoothing=5), StateParams(agreement_votes=7),
                                    StateParams(storm_forecast="downside")])
def test_options_are_causal(btc, params):
    check_signals_causal(lambda d: target_exposure(d, params).to_frame("target"), btc)


def test_daily_fallback_runs_and_is_bounded():
    daily = add_daily_proxies(load_market("BTCUSDT", "1d", "full").loc[:"2024-12-31"])
    target = target_exposure(daily)
    assert target.between(0, 1.5).all() and np.isfinite(target).all()


def test_profile_shares_sum_to_one(btc):
    prof = behaviour_profile(btc)
    assert abs(prof["summary"]["share of days"].sum() - 1) < 1e-9
