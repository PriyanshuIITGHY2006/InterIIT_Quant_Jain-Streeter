"""BTC/USDT strategy: Calm-Trend Regime (CTR). Final and frozen (research ID F1; protocol v8 §14, kept in v10 §16).
Built on the market-state framework. Full documentation: reports/btc_strategy.md.

Idea (from our research, reports/indicator_analysis_report.md): BTC's direction is hard to predict,
but WHEN trend-following pays is not. It paid in calm, orderly trends in every year 2021-2024 and paid
nothing in violent markets; sell-off volatility persists, squeezes precede volatility expansions.
So: a simple trend signal decides WHETHER to be long; the market state decides HOW MUCH.

Each day at the close (executed at the next day's open, 0.15% per fill), src/strategies/market_state.py
answers five questions and sizes the position:
  1. Direction   share of 7 banded trend votes: close above its 20/30/50/75/100/150/200-day average
  2. Regime      x 1.5 on calm-trend days, x 0.6 on other high-volatility days, x 1.0 otherwise
  3. Storm brake x 0.5 while BTC's downside-weighted volatility forecast is > 1.5x its 1-year median
  4. Squeeze     x 0.75 while a Bollinger-Keltner squeeze is on
  5. Soft gate   x 0.5 while the slow 200-day trend is down (bear-market rallies at half size)
Target exposure = 1 x 2 x 3 x 4 (capped at 1.5) x 5, long only, maximum 1.5x equity.
Every threshold is relative to the dataset's own history, so the rules apply unchanged to new data.
Data: daily bars plus realised measures (src.data.loader.load_strategy_data: hourly if available,
otherwise daily-candle proxies).
"""
import pandas as pd

from src.strategies.market_state import StateParams, layers, market_indicators, target_exposure

BTC_PARAMS = StateParams()          # CTR uses the framework defaults (frozen)


def btc_layers(data: pd.DataFrame) -> pd.DataFrame:
    """Every sizing layer, one column each (for analysis and charts)."""
    return layers(market_indicators(data, BTC_PARAMS), BTC_PARAMS)


def btc_signal(data: pd.DataFrame) -> pd.DataFrame:
    """Signal function: daily data -> DataFrame with the target exposure (fraction of equity)."""
    return target_exposure(data, BTC_PARAMS).to_frame("target")
