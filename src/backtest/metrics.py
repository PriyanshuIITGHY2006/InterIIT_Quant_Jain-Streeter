"""Performance metrics, the buy-and-hold benchmark and the quarterly comparison.

Definitions (see docs/backtest_engine_design.md for the reasoning):
  - Trade PnL is always NET of both fees. A winning trade has net PnL > 0.
  - Gross Profit = sum of net PnL of winning trades; Gross Loss = sum of net PnL of losing trades.
  - Net Profit = final equity - initial capital (= Gross Profit + Gross Loss).
  - Max Drawdown = largest peak-to-trough fall of the bar-by-bar marked-to-market equity.
  - Sharpe / Sortino use DAILY returns of the equity curve (last equity of each UTC day),
    annualised with sqrt(365), risk-free rate 0. Sortino's downside deviation is
    sqrt(mean(min(r, 0)^2)) over all days.
  - Buy-and-hold buys at the first tradable open after the first bar (the earliest a
    strategy could act), sells at the last close, and pays the same costs.
"""
import numpy as np
import pandas as pd

from src.backtest.engine import tradable_mask
from src.backtest.structures import BacktestConfig, BacktestResult

DAYS_PER_YEAR = 365


def buy_and_hold(data: pd.DataFrame, config: BacktestConfig) -> pd.Series:
    """Equity curve of buying at the first possible open and selling at the last close."""
    ok = tradable_mask(data)
    first = next(i for i in range(1, len(data)) if ok[i])
    price = data["open"].iloc[first]
    qty = config.initial_capital / (price * (1 + config.cost_rate))
    cash = config.initial_capital - qty * price * (1 + config.cost_rate)

    equity = pd.Series(config.initial_capital, index=data.index, dtype=float, name="buy_and_hold")
    equity.iloc[first:] = cash + qty * data["close"].iloc[first:].to_numpy()
    equity.iloc[-1] -= qty * data["close"].iloc[-1] * config.cost_rate     # exit fee
    return equity


def daily_returns(equity: pd.Series) -> pd.Series:
    return equity.resample("1D").last().pct_change().dropna()


def sharpe_ratio(equity: pd.Series) -> float:
    r = daily_returns(equity)
    return float(r.mean() / r.std() * np.sqrt(DAYS_PER_YEAR)) if r.std() > 0 else 0.0


def sortino_ratio(equity: pd.Series) -> float:
    r = daily_returns(equity)
    downside = np.sqrt(np.mean(np.minimum(r, 0) ** 2))
    return float(r.mean() / downside * np.sqrt(DAYS_PER_YEAR)) if downside > 0 else 0.0


def drawdown_stats(equity: pd.Series) -> dict:
    """Max drawdown, how long the worst drawdown took to recover, and the longest time under water."""
    peak = equity.cummax()
    dd = equity / peak - 1

    trough = dd.idxmin()
    peak_time = equity.loc[:trough].idxmax()
    recovered = equity.loc[trough:][equity.loc[trough:] >= peak.loc[trough]]
    recovery = recovered.index[0] - peak_time if len(recovered) else None   # None = never recovered

    # Longest stretch from a peak until equity is back at that peak (or the end of the data)
    longest, start = pd.Timedelta(0), None
    for k, under in enumerate((dd < 0).to_numpy()):
        if under and start is None:
            start = max(k - 1, 0)
        elif not under and start is not None:
            longest = max(longest, equity.index[k] - equity.index[start])
            start = None
    if start is not None:
        longest = max(longest, equity.index[-1] - equity.index[start])

    return {"max_drawdown_pct": 100 * dd.min(), "max_dd_recovery": recovery, "longest_underwater": longest}


def quarterly_comparison(equity: pd.Series, data: pd.DataFrame, initial_capital: float) -> pd.DataFrame:
    """Strategy return vs the asset's own return in every calendar quarter."""
    eq = equity.resample("QE").last()
    px = data["close"].resample("QE").last()
    strategy = eq / eq.shift(1).fillna(initial_capital) - 1
    asset = px / px.shift(1).fillna(data["open"].iloc[0]) - 1

    table = pd.DataFrame({"strategy %": 100 * strategy, "buy & hold %": 100 * asset})
    table["beat"] = table["strategy %"] > table["buy & hold %"]
    table.index = table.index.tz_localize(None).to_period("Q").astype(str)
    return table


def compute_metrics(result: BacktestResult, data: pd.DataFrame) -> dict:
    """The 15 metrics required by the problem statement, followed by extra context."""
    cfg = result.config
    equity, trades = result.equity, result.trades
    has_trades = len(trades) > 0
    wins = trades[trades["net_pnl"] > 0] if has_trades else trades
    losses = trades[trades["net_pnl"] <= 0] if has_trades else trades

    bench = buy_and_hold(data, cfg)
    dd = drawdown_stats(equity)
    quarters = quarterly_comparison(equity, data, cfg.initial_capital)

    bar = data.index.to_series().diff().median()
    years = (data.index[-1] - data.index[0] + bar) / pd.Timedelta(days=DAYS_PER_YEAR)
    total_return = equity.iloc[-1] / cfg.initial_capital - 1
    cagr = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1.0

    required = {
        "Gross Profit (USDT)": wins["net_pnl"].sum() if has_trades else 0.0,
        "Net Profit (USDT)": equity.iloc[-1] - cfg.initial_capital,
        "Total Closed Trades": len(trades),
        "Win Rate (%)": 100 * len(wins) / len(trades) if has_trades else 0.0,
        "Max Drawdown (%)": dd["max_drawdown_pct"],
        "Gross Loss (USDT)": losses["net_pnl"].sum() if has_trades else 0.0,
        "Average Winning Trade (USDT)": wins["net_pnl"].mean() if len(wins) else 0.0,
        "Average Losing Trade (USDT)": losses["net_pnl"].mean() if len(losses) else 0.0,
        "Buy-and-Hold Return (%)": 100 * (bench.iloc[-1] / cfg.initial_capital - 1),
        "Largest Losing Trade (USDT)": losses["net_pnl"].min() if len(losses) else 0.0,
        "Largest Winning Trade (USDT)": wins["net_pnl"].max() if len(wins) else 0.0,
        "Sharpe Ratio": sharpe_ratio(equity),
        "Sortino Ratio": sortino_ratio(equity),
        "Average Holding Duration": trades["duration"].mean() if has_trades else pd.Timedelta(0),
        "Maximum Holding Duration": trades["duration"].max() if has_trades else pd.Timedelta(0),
    }
    extra = {
        "Total Return (%)": 100 * total_return,
        "Annualised Return (%)": 100 * cagr,
        "Calmar Ratio": cagr / abs(dd["max_drawdown_pct"] / 100) if dd["max_drawdown_pct"] < 0 else 0.0,
        "Exposure (%)": 100 * (result.position != 0).mean(),
        "Long Trades": int((trades["side"] == "long").sum()) if has_trades else 0,
        "Short Trades": int((trades["side"] == "short").sum()) if has_trades else 0,
        "Total Fees (USDT)": trades["fees"].sum() if has_trades else 0.0,
        "Trading PnL before Fees (USDT)": trades["gross_pnl"].sum() if has_trades else 0.0,
        "Total Financing (USDT)": trades["financing"].sum() if has_trades and "financing" in trades else 0.0,
        "Max Drawdown Recovery Time": dd["max_dd_recovery"],
        "Longest Time Under Water": dd["longest_underwater"],
        "Quarters Beating Buy-and-Hold (%)": 100 * quarters["beat"].mean(),
        "Buy-and-Hold Max Drawdown (%)": drawdown_stats(bench)["max_drawdown_pct"],
        "Buy-and-Hold Sharpe Ratio": sharpe_ratio(bench),
        "Orders Deferred by Outages": len(result.deferred),
    }
    return {**required, **extra}
