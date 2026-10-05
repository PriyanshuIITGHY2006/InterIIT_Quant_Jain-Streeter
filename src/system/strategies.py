"""The two frozen strategies, as the system runs them. Nothing here is tunable.

  btc  CTR-S    Calm-Trend Regime with calm-bear shorts (src/strategies/btc_strategy.py)
  eth  CTR-ETH  Calm-Trend Regime, long only            (src/strategies/eth_strategy.py)
Both: 0.15% fee + slippage per fill, next-open execution, max 1.5x equity, 8%/yr on borrowed USDT;
CTR-S also shorts (max 0.5x) and pays an assumed 10%/yr on borrowed BTC.
"""
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from src.backtest import BacktestConfig
from src.strategies.btc_strategy import btc_layers, btc_signal
from src.strategies.eth_strategy import eth_layers, eth_signal
from src.strategies.execution import btc_trading_config, trading_config


@dataclass(frozen=True)
class FrozenStrategy:
    key: str
    name: str
    symbol: str
    signal: Callable[[pd.DataFrame], pd.DataFrame]
    layers: Callable[[pd.DataFrame], pd.DataFrame]
    config: Callable[..., BacktestConfig]
    color: str


STRATEGIES = {
    "btc": FrozenStrategy("btc", "CTR-S (Calm-Trend Regime with calm-bear shorts)", "BTCUSDT",
                          btc_signal, btc_layers, btc_trading_config, "#F7931A"),
    "eth": FrozenStrategy("eth", "CTR-ETH (Calm-Trend Regime for ETH)", "ETHUSDT",
                          eth_signal, eth_layers, trading_config, "#627EEA"),
}


def get(key: str) -> FrozenStrategy:
    key = key.lower().replace("usdt", "").replace("/", "")
    if key not in STRATEGIES:
        raise ValueError(f"unknown asset '{key}': choose one of {sorted(STRATEGIES)}")
    return STRATEGIES[key]


def guess_asset(path: str) -> str | None:
    """'btc' or 'eth' from a file name such as BTCUSDT_1h.csv, else None."""
    name = str(path).lower()
    hits = [k for k in STRATEGIES if k in name]
    return hits[0] if len(hits) == 1 else None
