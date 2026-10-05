"""Correctness tests for the backtest engine."""
import numpy as np
import pandas as pd
import pytest

from src.backtest import (BacktestConfig, LookaheadError, buy_and_hold, check_backtest_truncation,
                          check_signals_causal, run_backtest)
from src.data.loader import load_market
from tests.helpers import make_bars, random_walk, signals

COST = 0.0015


# ---------------------------------------------------------------- timing
def test_signal_executes_at_next_open():
    data = make_bars([100, 101, 102, 103, 104, 105])
    result = run_backtest(data, signals(data, [0, 0, 0, 1, 1, 1]))
    first_fill = result.fills.iloc[0]
    assert first_fill["time"] == data.index[4]        # signal seen at bar 3's close
    assert first_fill["price"] == 104                  # filled at bar 4's open


# ---------------------------------------------------------------- costs
def test_round_trip_cost_matches_hand_calculation():
    data = make_bars([100, 100, 110, 110])
    result = run_backtest(data, signals(data, [1, 0, 0, 0]))
    trade = result.trades.iloc[0]

    qty = 10_000 / (100 * (1 + COST))
    entry_fee, exit_fee = qty * 100 * COST, qty * 110 * COST
    assert trade["qty"] == pytest.approx(qty)
    assert trade["fees"] == pytest.approx(entry_fee + exit_fee)
    assert trade["net_pnl"] == pytest.approx(qty * 10 - entry_fee - exit_fee)
    assert round(trade["net_pnl"], 2) == 967.05
    assert result.equity.iloc[-1] == pytest.approx(10_000 + trade["net_pnl"])


# ---------------------------------------------------------------- stops and targets (long)
def test_stop_fills_at_stop_price_inside_bar():
    data = make_bars(opens=[100, 100, 98, 98], highs=[100, 101, 99, 98], lows=[100, 99, 94, 98])
    result = run_backtest(data, signals(data, [1, 1, 1, 1], stop_dist=5.0))
    trade = result.trades.iloc[0]
    assert trade["exit_price"] == 95 and trade["exit_reason"] == "stop_loss"


def test_gap_through_stop_fills_at_open():
    data = make_bars(opens=[100, 100, 90, 90], highs=[100, 101, 91, 90], lows=[100, 99, 85, 90])
    result = run_backtest(data, signals(data, [1, 1, 1, 1], stop_dist=5.0))
    trade = result.trades.iloc[0]
    assert trade["exit_price"] == 90 and trade["exit_reason"] == "stop_loss"


def test_stop_assumed_before_target_in_same_bar():
    data = make_bars(opens=[100, 100, 100, 100], highs=[100, 101, 112, 100], lows=[100, 99, 94, 100])
    result = run_backtest(data, signals(data, [1, 1, 1, 1], stop_dist=5.0, tp_dist=10.0))
    assert result.trades.iloc[0]["exit_price"] == 95


def test_take_profit_fills_at_target():
    data = make_bars(opens=[100, 100, 105, 105], highs=[100, 101, 111, 105], lows=[100, 99, 104, 105])
    result = run_backtest(data, signals(data, [1, 1, 1, 1], stop_dist=5.0, tp_dist=10.0))
    trade = result.trades.iloc[0]
    assert trade["exit_price"] == 110 and trade["exit_reason"] == "take_profit"


def test_trailing_stop_does_not_use_same_bar_high():
    # Bar 1 runs to 108 then dips to 102. The trailing stop only learns about 108 after bar 1,
    # so it must NOT trigger inside bar 1; it triggers in bar 2 at 108 - 5 = 103.
    data = make_bars(opens=[100, 100, 106, 106], highs=[100, 108, 107, 106], lows=[100, 102, 102, 106])
    result = run_backtest(data, signals(data, [1, 1, 1, 1], trail_dist=5.0))
    trade = result.trades.iloc[0]
    assert trade["exit_time"] == data.index[2]
    assert trade["exit_price"] == 103 and trade["exit_reason"] == "trailing_stop"


def test_no_reentry_after_stop_until_signal_changes():
    data = make_bars(opens=[100, 100, 98, 98, 98, 98, 98], lows=[100, 99, 94, 98, 98, 98, 98])
    result = run_backtest(data, signals(data, [1, 1, 1, 1, 0, 1, 1], stop_dist=5.0))
    entries = result.fills[result.fills["reason"] == "entry"]
    assert list(entries["time"]) == [data.index[1], data.index[6]]


def test_time_exit():
    data = make_bars([100, 100, 100, 100, 100, 100])
    result = run_backtest(data, signals(data, [1] * 6), BacktestConfig(max_holding_bars=2))
    trade = result.trades.iloc[0]
    assert trade["exit_time"] == data.index[3] and trade["exit_reason"] == "time_exit"
    assert len(result.trades) == 1                      # no re-entry while the signal stays long


# ---------------------------------------------------------------- outages
def test_no_fills_on_outage_bars():
    data = make_bars([100, 100, 102, 103], filled=[False, True, False, False])
    result = run_backtest(data, signals(data, [1, 1, 1, 1]))
    assert result.fills.iloc[0]["time"] == data.index[2]
    assert result.fills.iloc[0]["price"] == 102
    assert result.deferred == [data.index[1]]


def test_stops_not_triggered_on_outage_bars():
    data = make_bars(opens=[100, 100, 100, 100], lows=[100, 99, 80, 99], filled=[False, False, True, False])
    result = run_backtest(data, signals(data, [1, 1, 1, 1], stop_dist=5.0))
    assert result.trades.iloc[0]["exit_reason"] == "end_of_data"


# ---------------------------------------------------------------- short side
def short_config():
    return BacktestConfig(allow_short=True)


def test_short_round_trip_cost():
    data = make_bars([100, 100, 90, 90])
    result = run_backtest(data, signals(data, [-1, 0, 0, 0]), short_config())
    trade = result.trades.iloc[0]
    qty = 10_000 / (100 * (1 + COST))
    expected = qty * 10 - qty * 100 * COST - qty * 90 * COST
    assert trade["side"] == "short"
    assert trade["net_pnl"] == pytest.approx(expected)
    assert result.equity.iloc[-1] == pytest.approx(10_000 + expected)


def test_short_gap_through_stop_fills_at_open():
    data = make_bars(opens=[100, 100, 110, 110], highs=[100, 101, 115, 110], lows=[100, 99, 109, 110])
    result = run_backtest(data, signals(data, [-1, -1, -1, -1], stop_dist=5.0), short_config())
    assert result.trades.iloc[0]["exit_price"] == 110


def test_short_stop_assumed_before_target():
    data = make_bars(opens=[100, 100, 100, 100], highs=[100, 101, 106, 100], lows=[100, 99, 88, 100])
    result = run_backtest(data, signals(data, [-1, -1, -1, -1], stop_dist=5.0, tp_dist=10.0), short_config())
    assert result.trades.iloc[0]["exit_price"] == 105


def test_shorts_rejected_unless_allowed():
    data = make_bars([100, 100, 100])
    with pytest.raises(ValueError):
        run_backtest(data, signals(data, [-1, 0, 0]))


# ---------------------------------------------------------------- invariants on real data
def ma_signal(data: pd.DataFrame) -> pd.DataFrame:
    """Placeholder rule used only to exercise the engine."""
    above = data["close"] > data["close"].rolling(200).mean()
    stop = 3 * (data["high"] - data["low"]).rolling(24).mean()
    return pd.DataFrame({"target": above.astype(float), "stop_dist": stop}, index=data.index)


@pytest.fixture(scope="module")
def btc_train():
    return load_market("BTCUSDT", "1h", "train")


def test_accounting_invariants(btc_train):
    result = run_backtest(btc_train, ma_signal(btc_train))
    marked = result.cash + result.position * btc_train["close"]
    assert np.allclose(result.equity, marked)
    assert result.trades["net_pnl"].sum() == pytest.approx(result.equity.iloc[-1] - 10_000)
    assert result.fills["fee"].sum() == pytest.approx(result.trades["fees"].sum())
    assert len(result.fills) == 2 * len(result.trades)


def test_truncation_gives_identical_history(btc_train):
    for cut in [5_000, 12_345, 20_000]:
        check_backtest_truncation(ma_signal, btc_train, BacktestConfig(), cut)


def test_causal_signal_passes_check(btc_train):
    check_signals_causal(ma_signal, btc_train)


def test_lookahead_signal_is_caught(btc_train):
    def cheating_signal(data):
        return (data["close"].shift(-1) > data["close"]).astype(float)    # peeks at the next close

    with pytest.raises(LookaheadError):
        check_signals_causal(cheating_signal, btc_train)


# ---------------------------------------------------------------- sanity checks
def test_always_flat_does_nothing(btc_train):
    result = run_backtest(btc_train, signals(btc_train, np.zeros(len(btc_train))))
    assert len(result.trades) == 0
    assert (result.equity == 10_000).all()


def test_always_long_equals_buy_and_hold(btc_train):
    config = BacktestConfig()
    result = run_backtest(btc_train, signals(btc_train, np.ones(len(btc_train))), config)
    assert np.allclose(result.equity, buy_and_hold(btc_train, config))


def test_random_signals_lose_about_the_costs():
    """On zero-drift prices, random trading has no edge, so it should lose exactly the costs.

    Split every trade into its price move (gross) and its fees, both as % of entry notional:
    fees must be 0.30% per round trip, and the average gross move must be zero within noise.
    """
    rng = np.random.default_rng(42)
    trades = []
    for seed in range(40):
        data = random_walk(2_000, seed)
        target = np.where(rng.random(len(data)) < 0.5, 1.0, -1.0)
        target = pd.Series(target).where(rng.random(len(data)) < 0.2).ffill().fillna(0).to_numpy()
        trades.append(run_backtest(data, signals(data, target), short_config()).trades)
    trades = pd.concat(trades)

    notional = trades["qty"] * trades["entry_price"]
    fee_pct = 100 * trades["fees"] / notional
    gross_pct = 100 * trades["gross_pnl"] / notional
    standard_error = gross_pct.std() / np.sqrt(len(gross_pct))

    assert fee_pct.mean() == pytest.approx(0.30, abs=0.002)
    assert abs(gross_pct.mean()) < 3 * standard_error


# ---------------------------------------------------------------- rebalancing
def test_resize_down_matches_hand_calculation():
    # Enter fully at 100, cut to half at 120, close the rest at 130
    data = make_bars([100, 100, 120, 130, 130])
    config = BacktestConfig(rebalance_threshold=0.1)
    result = run_backtest(data, signals(data, [1, 0.5, 0, 0, 0]), config)

    q0 = 10_000 / (100 * (1 + COST))
    fee0 = q0 * 100 * COST
    equity_at_120 = q0 * 120                                   # cash is 0 after a full entry
    q1 = 0.5 * equity_at_120 / (120 * (1 + COST))
    sold = q0 - q1
    fee1 = sold * 120 * COST
    fee2 = q1 * 130 * COST
    gross = sold * 20 + q1 * 30

    trade = result.trades.iloc[0]
    assert list(result.fills["reason"]) == ["entry", "resize", "signal"]
    assert trade["gross_pnl"] == pytest.approx(gross)
    assert trade["fees"] == pytest.approx(fee0 + fee1 + fee2)
    assert result.equity.iloc[-1] == pytest.approx(10_000 + gross - fee0 - fee1 - fee2)


def test_resize_up_updates_average_entry_and_keeps_invariants():
    data = make_bars([100, 100, 110, 120, 120, 125])
    result = run_backtest(data, signals(data, [0.5, 0.5, 1, 1, 1, 1]), BacktestConfig(rebalance_threshold=0.1))
    resize = result.fills[result.fills["reason"] == "resize"].iloc[0]
    assert resize["time"] == data.index[3] and resize["action"] == "buy"
    marked = result.cash + result.position * data["close"]
    assert np.allclose(result.equity, marked)
    assert result.trades["net_pnl"].sum() == pytest.approx(result.equity.iloc[-1] - 10_000)
    assert result.fills["fee"].sum() == pytest.approx(result.trades["fees"].sum())


def test_no_resize_without_threshold_or_for_small_changes():
    data = make_bars([100, 100, 110, 120, 120])
    target = [1, 0.95, 0.5, 0.5, 0.5]
    no_threshold = run_backtest(data, signals(data, target))
    assert "resize" not in set(no_threshold.fills["reason"])
    small_change = run_backtest(data, signals(data, [1, 0.95, 0.95, 0.95, 0.95]), BacktestConfig(rebalance_threshold=0.1))
    assert "resize" not in set(small_change.fills["reason"])


def test_reentry_after_cooldown():
    # Stopped out in bar 2; the signal stays long. With a 2-bar cool-down it re-enters at bar 5's open
    # (decision at bar 4's close, 2 bars after the stop), not before.
    data = make_bars(opens=[100, 100, 98, 98, 98, 98, 98], lows=[100, 99, 94, 98, 98, 98, 98])
    config = BacktestConfig(reentry_cooldown_bars=2)
    result = run_backtest(data, signals(data, [1] * 7, stop_dist=5.0), config)
    entries = result.fills[result.fills["reason"] == "entry"]
    assert list(entries["time"]) == [data.index[1], data.index[5]]


# ---------------------------------------------------------------- leverage and financing
def test_leveraged_round_trip_with_financing():
    data = make_bars([100, 100, 110, 110], freq="1D")
    config = BacktestConfig(max_position=1.5, borrow_rate=0.08)
    result = run_backtest(data, signals(data, [1.5, 0, 0, 0]), config)
    trade = result.trades.iloc[0]

    qty = 1.5 * 10_000 / (100 * (1 + COST))
    borrowed = qty * 100 * (1 + COST) - 10_000                   # = 5,000
    interest = borrowed * 0.08 / 365                             # held through one daily bar
    fees = qty * 100 * COST + qty * 110 * COST
    assert borrowed == pytest.approx(5_000)
    assert trade["financing"] == pytest.approx(interest)
    assert trade["net_pnl"] == pytest.approx(qty * 10 - fees - interest)
    assert result.equity.iloc[-1] == pytest.approx(10_000 + trade["net_pnl"])


def test_leverage_above_cap_is_rejected():
    data = make_bars([100, 100, 100])
    with pytest.raises(ValueError):
        run_backtest(data, signals(data, [1.5, 0, 0]))          # default max_position = 1
