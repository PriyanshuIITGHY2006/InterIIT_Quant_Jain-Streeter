"""Look-ahead detection.

A strategy is a function `signal_fn(data) -> signals`. If any of its outputs up to time T
change when the data AFTER T is removed, the strategy is using future information.
"""
import numpy as np
import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.structures import BacktestConfig


class LookaheadError(AssertionError):
    pass


def _as_frame(signals) -> pd.DataFrame:
    return signals.to_frame("target") if isinstance(signals, pd.Series) else signals


def _first_difference(a: pd.DataFrame, b: pd.DataFrame):
    same = np.isclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True).all(axis=1)
    return a.index[~same][0] if (~same).any() else None


def check_signals_causal(signal_fn, data: pd.DataFrame, n_cuts: int = 6, warmup: int = 300) -> None:
    """Recompute the signals on truncated data at several cut points; they must not change."""
    full = _as_frame(signal_fn(data))
    for cut in np.linspace(warmup, len(data) - 1, n_cuts).astype(int):
        partial = _as_frame(signal_fn(data.iloc[: cut + 1]))
        diff = _first_difference(full.iloc[: cut + 1], partial)
        if diff is not None:
            raise LookaheadError(f"signal at {diff} changes when data after {data.index[cut]} is removed")


def check_backtest_truncation(signal_fn, data: pd.DataFrame, config: BacktestConfig, cut: int) -> None:
    """Backtest on data[:cut] and on all data; every trade and equity value before the cut must match.

    The truncated run force-closes its last position at the cut, so that final trade and the
    last equity value are excluded from the comparison.
    """
    short_data = data.iloc[: cut + 1]
    full = run_backtest(data, signal_fn(data), config)
    part = run_backtest(short_data, signal_fn(short_data), config)

    part_trades = part.trades[part.trades["exit_reason"] != "end_of_data"] if len(part.trades) else part.trades
    full_trades = full.trades.iloc[: len(part_trades)]
    if len(part_trades) and not part_trades.reset_index(drop=True).equals(full_trades.reset_index(drop=True)):
        raise LookaheadError("trades before the cut differ between the truncated and the full run")
    if not np.allclose(part.equity.iloc[:-1], full.equity.iloc[:cut]):
        raise LookaheadError("equity before the cut differs between the truncated and the full run")


def backtest(data: pd.DataFrame, signal_fn, config: BacktestConfig | None = None, check: bool = True):
    """Recommended entry point: verify the strategy is causal, then run it."""
    if check:
        check_signals_causal(signal_fn, data)
    return run_backtest(data, signal_fn(data), config)
