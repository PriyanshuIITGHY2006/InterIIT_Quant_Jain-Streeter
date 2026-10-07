"""BTC risk layers as stand-alone functions (thin wrappers over src/strategies/market_state.py).

The single source of truth for the rules is the market-state framework; these helpers expose each
layer separately for research code (e.g. notebooks/03_ml_research.ipynb, src/ml/f1_variants.py).
  regime size     1.5 on calm-trend days, 0.6 on other high-volatility days, 1.0 otherwise
  storm brake     0.5 while the downside-weighted risk forecast is > 1.5x its 1-year median
  squeeze warning 0.75 while a Bollinger-Keltner squeeze is on
  soft gate       0.5 while the slow 200-day trend is down
"""
import numpy as np
import pandas as pd

from src.strategies import market_state as ms

_P = ms.StateParams()
CALM_LEVERAGE, HIGH_VOL_SIZE, NORMAL_SIZE = _P.calm_leverage, _P.high_vol_size, 1.0
VOL_THRESHOLD, CHOP_TREND_LEVEL = _P.vol_threshold, _P.chop_trend_level
STORM_MULTIPLE, STORM_CUT, SQUEEZE_CUT = _P.storm_multiple, _P.storm_cut, _P.squeeze_cut
GATE_LOOKBACK, GATE_FLOOR = _P.gate_lookback, _P.gate_floor

vol_percentile = ms.vol_percentile


def storm_brake(data: pd.DataFrame, multiple: float = STORM_MULTIPLE) -> pd.Series:
    vol = ms.risk_forecast(data, _P.storm_forecast)
    typical = vol.rolling(365, min_periods=90).median()
    return pd.Series(np.where(vol > multiple * typical, STORM_CUT, 1.0), index=data.index)


def squeeze_warning(data: pd.DataFrame) -> pd.Series:
    from src.features import indicators as ind
    return pd.Series(np.where(ind.squeeze(data) == 1, SQUEEZE_CUT, 1.0), index=data.index)


def soft_gate(close: pd.Series, lookback: int = GATE_LOOKBACK, floor: float = GATE_FLOOR) -> pd.Series:
    return floor + (1 - floor) * ms.slow_gate(close, lookback)
