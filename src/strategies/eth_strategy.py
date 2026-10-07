"""ETH/USDT strategy: Calm-Trend Regime for ETH (CTR-ETH). Final and frozen (protocol v20 §26).

The same market-state framework as the BTC strategy (src/strategies/market_state.py), with the same default
parameters. Nothing is tuned for ETH: every threshold is measured against ETH's OWN history (its volatility
percentile within its trailing year, its efficiency ratio against its own median, its sell-off risk
against its own 1-year median), so the rules adapt to ETH's higher volatility and sharper cycles.
Full documentation: reports/eth_strategy.md.

Each day at the close (executed at the next day's open, 0.15% per fill):
  1. Direction   share of 7 banded trend votes (20/30/50/75/100/150/200-day averages)
  2. Regime      x 1.5 on calm-trend days, x 0.6 on other high-volatility days, x 1.0 otherwise
  3. Storm brake x 0.5 while the downside-weighted risk forecast is > 1.5x its 1-year median
  4. Squeeze     x 0.75 while a Bollinger-Keltner squeeze is on
  5. Soft gate   x 0.5 while the slow 200-day trend is down
Target exposure = 1 x 2 x 3 x 4 (capped at 1.5) x 5, long only, maximum 1.5x equity.
"""
import pandas as pd

from src.strategies.market_state import StateParams, layers, market_indicators, target_exposure

ETH_PARAMS = StateParams()          # identical to BTC: no ETH-specific tuning (frozen)


def eth_layers(data: pd.DataFrame) -> pd.DataFrame:
    """Every sizing layer, one column each (for analysis and charts)."""
    return layers(market_indicators(data, ETH_PARAMS), ETH_PARAMS)


def eth_signal(data: pd.DataFrame) -> pd.DataFrame:
    """Signal function: daily ETH data -> DataFrame with the target exposure (fraction of equity)."""
    return target_exposure(data, ETH_PARAMS).to_frame("target")
