"""Bar-by-bar backtest engine for one market.

Timing contract (this is what prevents look-ahead):
  1. The strategy's row for bar i may use data up to bar i's CLOSE.
  2. That decision is executed at the OPEN of the next tradable bar (i+1 or later).
     The engine applies this lag itself, so a strategy can never trade on the bar it just saw.
  3. Stops, take-profits and trailing stops are checked inside each bar using its high/low,
     pessimistically:
       - if the bar OPENS beyond the level, the fill is at the open (gap), not at the level;
       - if stop and take-profit are both touched in one bar, the stop is assumed to fill first;
       - the trailing stop only uses prices up to the PREVIOUS bar.
  4. Outage bars (is_filled or trades == 0) get no fills; orders wait for the next tradable bar.
  5. Every fill pays cost_rate on its notional (entry and exit, stops and reversals included).

Strategy input: a DataFrame with the same index as the data and columns
    target      desired position as a fraction of equity, in [-1, 1] (0 = flat)
    stop_dist   optional stop-loss distance in price units, set at entry
    tp_dist     optional take-profit distance in price units, set at entry
    trail_dist  optional trailing-stop distance in price units, set at entry
(a plain Series is treated as `target`).
The size of a position is fixed at entry; a change in |target| without a change of side is ignored.
"""
import numpy as np
import pandas as pd

from src.backtest.structures import BacktestConfig, BacktestResult, Position

LEVEL_COLUMNS = ["stop_dist", "tp_dist", "trail_dist"]


def tradable_mask(data: pd.DataFrame) -> np.ndarray:
    """True for bars where the exchange was actually trading."""
    ok = np.ones(len(data), dtype=bool)
    if "is_filled" in data:
        ok &= ~data["is_filled"].astype(bool).to_numpy()
    if "trades" in data:
        ok &= data["trades"].to_numpy() > 0
    return ok


def prepare_signals(signals, data: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    """Validate the strategy output and return it with all expected columns."""
    if isinstance(signals, pd.Series):
        signals = signals.to_frame("target")
    if "target" not in signals:
        raise ValueError("signals need a 'target' column")
    if not signals.index.equals(data.index):
        raise ValueError("signals must have exactly the same index as the data")

    sig = signals.reindex(columns=["target"] + LEVEL_COLUMNS).astype(float)
    sig["target"] = sig["target"].fillna(0.0)
    if (sig["target"].abs() > 1).any():
        raise ValueError("target must be within [-1, 1]")
    if not config.allow_short and (sig["target"] < 0).any():
        raise ValueError("negative target found but allow_short is False")
    return sig


class _Book:
    """Cash, the open position, and the logs of fills and closed trades."""

    def __init__(self, config: BacktestConfig, times: pd.DatetimeIndex):
        self.cash = config.initial_capital
        self.cost = config.cost_rate
        self.times = times
        self.pos: Position | None = None
        self.fills: list[dict] = []
        self.trades: list[dict] = []

    def open(self, i: int, side: int, fraction: float, price: float, levels: tuple):
        # The book is flat here, so equity == cash, and it is known at the moment of the fill.
        qty = fraction * self.cash / (price * (1 + self.cost))   # leaves room for the entry fee
        if qty <= 0:
            return
        fee = qty * price * self.cost
        self.cash -= side * qty * price + fee

        stop_dist, tp_dist, trail_dist = (d if d > 0 else None for d in np.nan_to_num(levels))
        self.pos = Position(
            side=side, qty=qty, entry_i=i, entry_price=price, entry_fee=fee,
            stop=price - side * stop_dist if stop_dist else None,
            take_profit=price + side * tp_dist if tp_dist else None,
            trail_dist=trail_dist,
            best_price=price, highest=price, lowest=price,
        )
        self._log_fill(i, "buy" if side == 1 else "sell", qty, price, fee, "entry")

    def close(self, i: int, price: float, reason: str):
        p = self.pos
        fee = p.qty * price * self.cost
        self.cash += p.side * p.qty * price - fee
        gross = p.side * p.qty * (price - p.entry_price)
        net = gross - p.entry_fee - fee

        if p.side == 1:
            mae, mfe = p.lowest / p.entry_price - 1, p.highest / p.entry_price - 1
        else:
            mae, mfe = 1 - p.highest / p.entry_price, 1 - p.lowest / p.entry_price

        self.trades.append({
            "entry_time": self.times[p.entry_i],
            "exit_time": self.times[i],
            "side": "long" if p.side == 1 else "short",
            "qty": p.qty,
            "entry_price": p.entry_price,
            "exit_price": price,
            "gross_pnl": gross,
            "fees": p.entry_fee + fee,
            "net_pnl": net,
            "return_pct": 100 * net / (p.qty * p.entry_price),
            "bars_held": i - p.entry_i,
            "duration": self.times[i] - self.times[p.entry_i],
            "exit_reason": reason,
            "mae_pct": 100 * mae,
            "mfe_pct": 100 * mfe,
        })
        self._log_fill(i, "sell" if p.side == 1 else "buy", p.qty, price, fee, reason)
        self.pos = None

    def _log_fill(self, i, action, qty, price, fee, reason):
        self.fills.append({"time": self.times[i], "action": action, "qty": qty,
                           "price": price, "fee": fee, "reason": reason})


def _intrabar_exit(pos: Position, o: float, h: float, l: float):
    """Return (fill price, reason) if a stop / trailing stop / take-profit triggers in this bar."""
    s = pos.side

    # Use the tighter of the fixed stop and the trailing stop
    stop, reason = pos.stop, "stop_loss"
    trail = pos.trail_level()
    if trail is not None and (stop is None or s * (trail - stop) > 0):
        stop, reason = trail, "trailing_stop"

    # Stops are checked first: if stop and target are both touched, assume the stop came first
    if stop is not None:
        if s * (o - stop) <= 0:                      # opened beyond the stop -> gap fill at the open
            return o, reason
        if (l <= stop) if s == 1 else (h >= stop):
            return stop, reason

    tp = pos.take_profit
    if tp is not None:
        if s * (o - tp) >= 0:                        # opened beyond the target -> fill at the open
            return o, "take_profit"
        if (h >= tp) if s == 1 else (l <= tp):
            return tp, "take_profit"
    return None, None


def run_backtest(data: pd.DataFrame, signals, config: BacktestConfig | None = None) -> BacktestResult:
    """Run one market's backtest. `data` needs open/high/low/close (and ideally is_filled, trades)."""
    config = config or BacktestConfig()
    sig = prepare_signals(signals, data, config)

    o, h, l, c = (data[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    target = sig["target"].to_numpy()
    levels = sig[LEVEL_COLUMNS].to_numpy()
    ok = tradable_mask(data)
    times = data.index
    n = len(data)

    book = _Book(config, times)
    equity, cash, held = np.empty(n), np.empty(n), np.zeros(n)
    deferred = []

    # The decision waiting to be executed at the next tradable open
    want_side, want_size, want_levels, want_reason = 0, 0.0, (np.nan,) * 3, "signal"
    blocked_side = 0              # side we may not re-enter until the signal changes
    peak = config.initial_capital
    halted = False

    for i in range(n):
        # 1. Execute the previous decision at this bar's open
        side_now = book.pos.side if book.pos else 0
        if i > 0 and side_now != want_side:
            if not ok[i]:
                deferred.append(times[i])
            else:
                if book.pos:
                    book.close(i, o[i], want_reason)
                if want_side != 0:
                    book.open(i, want_side, want_size, o[i], want_levels)

        # 2. Stops and targets inside this bar
        if book.pos and ok[i]:
            pos = book.pos
            pos.highest, pos.lowest = max(pos.highest, h[i]), min(pos.lowest, l[i])
            price, reason = _intrabar_exit(pos, o[i], h[i], l[i])
            if price is not None:
                book.close(i, price, reason)
                if not config.reenter_after_exit:
                    blocked_side = pos.side

        # 3. Mark to market at the close
        pos = book.pos
        held[i] = pos.side * pos.qty if pos else 0.0
        equity[i] = book.cash + held[i] * c[i]
        cash[i] = book.cash

        # 4. The trailing stop learns this bar's extreme only now, for use from the next bar on
        if pos and ok[i]:
            pos.best_price = max(pos.best_price, h[i]) if pos.side == 1 else min(pos.best_price, l[i])

        # 5. Decide what to hold from the next open, using information up to this close only
        peak = max(peak, equity[i])
        if equity[i] <= 0 or (config.max_drawdown_halt and equity[i] < peak * (1 - config.max_drawdown_halt)):
            halted = True

        t = 0.0 if halted else target[i]
        side, size = int(np.sign(t)), min(abs(t), config.max_position)
        if config.exposure_cap is not None:
            size = min(size, max(0.0, config.exposure_cap(times[i], equity[i], peak)))

        if blocked_side and side != blocked_side:
            blocked_side = 0
        if blocked_side:
            side = 0

        reason = "risk_halt" if halted else "signal"
        if pos and config.max_holding_bars and i - pos.entry_i + 1 >= config.max_holding_bars:
            side, reason = 0, "time_exit"
            if not config.reenter_after_exit:
                blocked_side = pos.side
        if size == 0:
            side = 0

        # Keep an existing position as it is; otherwise remember the new decision
        if not (pos and side == pos.side):
            want_levels = tuple(levels[i])
        want_side, want_size, want_reason = side, size, reason

    # Close whatever is still open at the last close
    if book.pos:
        book.close(n - 1, c[-1], "end_of_data")
        equity[-1] = cash[-1] = book.cash
        held[-1] = 0.0

    return BacktestResult(
        equity=pd.Series(equity, index=times, name="equity"),
        cash=pd.Series(cash, index=times, name="cash"),
        position=pd.Series(held, index=times, name="position"),
        trades=pd.DataFrame(book.trades),
        fills=pd.DataFrame(book.fills),
        deferred=deferred,
        config=config,
    )
