"""Indicators: hand-checked values and causality (no value may change when future bars are removed)."""
import numpy as np
import pandas as pd
import pytest

from src.data.loader import load_market
from src.features import indicators as ind


@pytest.fixture(scope="module")
def btc():
    return load_market("BTCUSDT", "1d", "train")


def test_efficiency_ratio_and_rsi_extremes():
    up = pd.Series(np.arange(1.0, 61.0))
    assert ind.efficiency_ratio(up, 10).iloc[-1] == pytest.approx(1.0)
    assert ind.rsi(up, 14).iloc[-1] == pytest.approx(100.0)


def test_choppiness_is_low_in_a_straight_trend():
    idx = pd.date_range("2021-01-01", periods=60, freq="1D", tz="UTC")
    c = pd.Series(np.linspace(100, 200, 60), index=idx)
    df = pd.DataFrame({"open": c.shift(1).fillna(100), "high": c + 0.5, "low": c - 0.5, "close": c})
    assert ind.choppiness(df, 14).iloc[-1] < 40


def test_realised_measures_split_variance():
    idx = pd.date_range("2021-01-01", periods=48, freq="1h", tz="UTC")
    close = pd.Series(100 * np.exp(np.cumsum(np.tile([0.01, -0.01], 24))), index=idx)
    m = ind.realised_measures(pd.DataFrame({"close": close}))
    assert np.allclose(m["rv"], m["rs_up"] + m["rs_down"])
    assert m["signed_jump"].abs().max() < 0.1


INDICATORS = {
    "atr": lambda d: ind.atr(d), "yang_zhang": lambda d: ind.yang_zhang_vol(d), "parkinson": lambda d: ind.parkinson_vol(d),
    "squeeze": lambda d: ind.squeeze(d), "adx": lambda d: ind.adx(d)["adx"], "chop": lambda d: ind.choppiness(d),
    "supertrend": lambda d: ind.supertrend(d), "rsi": lambda d: ind.rsi(d["close"]), "cmf": lambda d: ind.chaikin_money_flow(d),
    "vol_pct": lambda d: ind.rolling_percentile(ind.parkinson_vol(d)), "hurst": lambda d: ind.rolling_hurst(d["close"]),
}


@pytest.mark.parametrize("name", list(INDICATORS))
def test_indicators_are_causal(btc, name):
    fn = INDICATORS[name]
    full = fn(btc)
    for cut in [300, 700]:
        part = fn(btc.iloc[: cut + 1])
        assert np.allclose(full.iloc[: cut + 1].to_numpy(), part.to_numpy(), equal_nan=True), name


REFERENCE_INDICATORS = {
    "ema_ribbon": lambda d: ind.ema_ribbon(d["close"]), "aroon": lambda d: ind.aroon(d)["aroon_osc"],
    "heikin_ashi": lambda d: ind.heikin_ashi(d)["ha_streak"], "gauss": lambda d: ind.causal_gaussian(d["close"]),
    "kalman": lambda d: ind.kalman_trend(d["close"])["kalman_dev"], "cusum": lambda d: ind.cusum_state(d["close"]),
    "markov": lambda d: ind.markov_switching_prob(np.log(d["close"]).diff()),
    "clusters": lambda d: ind.vol_clusters(pd.DataFrame({"pv": ind.parkinson_vol(d, 14), "atr": ind.atr_pct(d)})),
}


@pytest.mark.parametrize("name", list(REFERENCE_INDICATORS))
def test_reference_indicators_are_causal(btc, name):
    fn = REFERENCE_INDICATORS[name]
    full = fn(btc)
    for cut in [400, 800]:
        part = fn(btc.iloc[: cut + 1])
        assert np.allclose(full.iloc[: cut + 1].to_numpy(), part.to_numpy(), equal_nan=True), name
