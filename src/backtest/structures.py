"""Plain data containers used by the backtest engine."""
from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class BacktestConfig:
    """Settings for one backtest run.

    initial_capital     starting equity in USDT
    cost_rate           fee + slippage charged on the notional of EVERY fill (0.0015 = 0.15%)
    allow_short         if False, negative targets raise an error
    max_position        cap on |target| (fraction of equity; 1.0 = fully invested, >1 = leverage)
    borrow_rate         yearly interest on borrowed cash (negative cash when leveraged long), charged every bar
    max_holding_bars    close a position after this many bars (None = no limit)
    rebalance_threshold if set, an open position is resized to the new |target| whenever the
                        target differs from the current exposure by more than this (e.g. 0.1);
                        if None, a position keeps the size it was opened with
    reenter_after_exit  if False, after a stop / take-profit / trailing / time exit the engine
                        waits for the signal to change side before entering the same side again
    reentry_cooldown_bars  if set (and reenter_after_exit is False), that wait also ends after this
                        many bars, even if the signal never changed side
    max_drawdown_halt   stop trading for good once equity falls this far below its peak (e.g. 0.3)
    exposure_cap        optional hook f(time, equity, peak_equity) -> max fraction for NEW positions,
                        evaluated at the decision bar's close (a global risk-management hook)
    """
    initial_capital: float = 10_000.0
    cost_rate: float = 0.0015
    allow_short: bool = False
    max_position: float = 1.0
    borrow_rate: float = 0.0
    max_holding_bars: int | None = None
    rebalance_threshold: float | None = None
    reenter_after_exit: bool = False
    reentry_cooldown_bars: int | None = None
    max_drawdown_halt: float | None = None
    exposure_cap: Callable[[pd.Timestamp, float, float], float] | None = None


@dataclass
class Position:
    """The currently open position."""
    side: int                  # +1 long, -1 short
    qty: float                 # units of the base asset currently held (always > 0)
    entry_i: int               # bar index of the first entry fill
    entry_price: float         # average entry price of the units still held
    fees_paid: float           # all fees paid so far in this trade
    realized: float            # gross PnL already realised by partial reductions
    financing: float           # interest paid on borrowed cash while this position was open
    max_qty: float             # largest size held during the trade
    stop: float | None         # fixed stop-loss price
    take_profit: float | None  # fixed take-profit price
    trail_dist: float | None   # trailing-stop distance in price units
    best_price: float          # best price seen so far (for the trailing stop), up to the previous bar
    highest: float             # highest high while held (for MAE / MFE)
    lowest: float              # lowest low while held

    def trail_level(self) -> float | None:
        if self.trail_dist is None:
            return None
        return self.best_price - self.side * self.trail_dist


@dataclass
class BacktestResult:
    """Everything a backtest produces."""
    equity: pd.Series          # marked to market at every bar close
    cash: pd.Series
    position: pd.Series        # signed quantity held at every bar close
    trades: pd.DataFrame       # one row per closed trade
    fills: pd.DataFrame        # one row per fill (every buy / sell)
    deferred: list             # bars where an order had to wait because the bar was an outage
    config: BacktestConfig
