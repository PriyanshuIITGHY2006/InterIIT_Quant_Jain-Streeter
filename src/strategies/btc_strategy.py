"""BTC/USDT strategy: Calm-Trend Regime with calm-bear shorts (CTR-S). Final and frozen (protocol v29 §35).
CTR (research ID F1; protocol v8 §14, kept in v10 §16) plus a disciplined short side (research ID X3; §34).
Built on the market-state framework. Full documentation: reports/btc_strategy.md.

Idea (from our research, reports/indicator_analysis_report.md): BTC's direction is hard to predict,
but WHEN trend-following pays is not. It paid in calm, orderly trends in every year 2021-2024 and paid
nothing in violent markets; sell-off volatility persists, squeezes precede volatility expansions.
So: a simple trend signal decides WHETHER to be long; the market state decides HOW MUCH.
The same logic, mirrored, decides when to be short: only in a calm, fully confirmed bear market.

Each day at the close (executed at the next day's open, 0.15% per fill), src/strategies/market_state.py
answers five questions and sizes the long position:
  1. Direction   share of 7 banded trend votes: close above its 20/30/50/75/100/150/200-day average
  2. Regime      x 1.5 on calm-trend days, x 0.6 on other high-volatility days, x 1.0 otherwise
  3. Storm brake x 0.5 while BTC's downside-weighted volatility forecast is > 1.5x its 1-year median
  4. Squeeze     x 0.75 while a Bollinger-Keltner squeeze is on
  5. Soft gate   x 0.5 while the slow 200-day trend is down (bear-market rallies at half size)
Long target = 1 x 2 x 3 x 4 (capped at 1.5) x 5, maximum 1.5x equity.

Short side: -0.5x equity only while ALL of these hold, covered as soon as any fails:
  a. the long target is 0                 (CTR is flat)
  b. the 200-day gate is down             (slow trend down)
  c. all 7 trend votes are down           (every horizon agrees)
  d. volatility percentile <= 0.5         (calm, orderly decline, not a panic: squeezes are violent)
  e. drawdown from the 365-day high > -60% (not after a capitulation, where rebounds are sharpest)
Borrowing the coins costs an assumed 10%/yr, charged daily in the backtest.
Every threshold is relative to the dataset's own history, so the rules apply unchanged to new data.
Data: daily bars plus realised measures (src.data.loader.load_strategy_data: hourly if available,
otherwise daily-candle proxies).
"""
import pandas as pd

from src.features.indicators import drawdown_from_high
from src.strategies.market_state import StateParams, layers, market_indicators, target_exposure

BTC_PARAMS = StateParams()          # CTR uses the framework defaults (frozen)
SHORT_SIZE = 0.5                    # short exposure, x equity
SHORT_MAX_VOL_PERCENTILE = 0.5      # short only in the calmer half of the past year's volatility
CAPITULATION_DRAWDOWN = -0.60       # no new or held short once BTC is more than 60% below its 365-day high
CAPITULATION_LOOKBACK = 365         # days


def short_condition(data: pd.DataFrame, mi: pd.DataFrame | None = None) -> pd.Series:
    """True on days when CTR-S holds the short (all five conditions a-e)."""
    mi = market_indicators(data, BTC_PARAMS) if mi is None else mi
    long = target_exposure(data, BTC_PARAMS)
    return ((long <= 0) & (mi["gate"] == 0) & (mi["trend_votes"] <= 1e-9)
            & (mi["vol_percentile"] <= SHORT_MAX_VOL_PERCENTILE)
            & (drawdown_from_high(data["close"], CAPITULATION_LOOKBACK) > CAPITULATION_DRAWDOWN))


def btc_layers(data: pd.DataFrame) -> pd.DataFrame:
    """Every sizing layer, one column each, plus the short condition (for analysis and charts)."""
    mi = market_indicators(data, BTC_PARAMS)
    return layers(mi, BTC_PARAMS).assign(short=short_condition(data, mi).astype(float))


def ctr_long_signal(data: pd.DataFrame) -> pd.DataFrame:
    """The long-only CTR (the previous BTC final), kept for comparisons."""
    return target_exposure(data, BTC_PARAMS).to_frame("target")


def btc_signal(data: pd.DataFrame) -> pd.DataFrame:
    """Signal function: daily data -> DataFrame with the target exposure (fraction of equity, < 0 = short)."""
    long = target_exposure(data, BTC_PARAMS)
    return long.where(~short_condition(data), -SHORT_SIZE).to_frame("target")
