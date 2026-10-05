"""Execution settings for the final strategies (evaluation protocol v6 §12; short side v29 §35)."""
from src.backtest import BacktestConfig

LEVERAGE = 1.5          # maximum position, x equity (fixed, never tuned)
BORROW_RATE = 0.08      # yearly interest on borrowed USDT, charged daily
REBALANCE_BAND = 0.25   # resize an open position only when the target moves more than this
REENTRY_COOLDOWN = 5    # days
SHORT_BORROW_RATE = 0.10  # yearly fee for borrowing coins to short (assumed margin rate; charged daily)


def trading_config(cost_rate: float = 0.0015, allow_short: bool = False) -> BacktestConfig:
    return BacktestConfig(cost_rate=cost_rate, rebalance_threshold=REBALANCE_BAND, reentry_cooldown_bars=REENTRY_COOLDOWN,
                          max_position=LEVERAGE, borrow_rate=BORROW_RATE, allow_short=allow_short,
                          short_borrow_rate=SHORT_BORROW_RATE)


def btc_trading_config(cost_rate: float = 0.0015) -> BacktestConfig:
    """BTC runs CTR-S, which shorts; ETH stays long only."""
    return trading_config(cost_rate, allow_short=True)
