"""Run the final BTC/USDT strategy and write every deliverable to results/btc/.

Periods
  2021-2024   development data (the strategy was designed and selected here)
  2025        the last year of the competition data
  2021-2025   the required 5-year backtest
For each period: all metrics, trade history, fills, equity, quarterly table, equity/drawdown and trade charts.
Plus: a yearly table, a 2x-cost stress test, a risk analysis (payoff ratio, expectancy, adverse excursion)
and a chart of every decision layer. Summary: results/btc/summary.md.

Run from the project root:  .venv/bin/python -m scripts.run_btc_strategy
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.backtest.evaluation import log_experiment, run_on_period, yearly_breakdown
from src.backtest.metrics import compute_metrics
from src.backtest.report import markdown_table, save_report
from src.data.loader import load_daily_with_realised
from src.strategies.btc_strategy import btc_layers, btc_signal
from src.strategies.execution import trading_config

OUT = Path("results/btc")
PERIODS = {"2021-2024": ("2021-01-01", "2024-12-31"), "2025": ("2025-01-01", "2025-12-31"),
           "2021-2025": ("2021-01-01", "2025-12-31")}
REQUIRED = ["Gross Profit (USDT)", "Net Profit (USDT)", "Total Closed Trades", "Win Rate (%)", "Max Drawdown (%)",
            "Gross Loss (USDT)", "Average Winning Trade (USDT)", "Average Losing Trade (USDT)", "Buy-and-Hold Return (%)",
            "Largest Losing Trade (USDT)", "Largest Winning Trade (USDT)", "Sharpe Ratio", "Sortino Ratio",
            "Average Holding Duration", "Maximum Holding Duration"]
EXTRA = ["Total Return (%)", "Annualised Return (%)", "Calmar Ratio", "Quarters Beating Buy-and-Hold (%)",
         "Max Drawdown Recovery Time", "Longest Time Under Water", "Exposure (%)", "Total Fees (USDT)",
         "Total Financing (USDT)", "Buy-and-Hold Sharpe Ratio", "Buy-and-Hold Max Drawdown (%)"]


def fmt(v):
    return f"{v:,.2f}" if isinstance(v, float) else str(v)


def risk_analysis(result) -> dict:
    """Risk / reward measured on account equity.

    Positions are resized while open, so the engine's per-trade entry price is an average cost and
    per-trade price returns are not meaningful here; each trade's PnL is measured as a percentage of the
    equity at its entry instead, plus loss statistics of the daily equity curve.
    """
    trades = result.trades
    equity = result.equity
    start_equity = equity.shift(1).fillna(result.config.initial_capital).reindex(trades.entry_time).to_numpy()
    r = 100 * trades.net_pnl.to_numpy() / start_equity
    wins, losses = r[r > 0], r[r <= 0]
    daily = equity.resample("1D").last().pct_change().dropna()
    return {
        "Average win (% of equity)": wins.mean() if len(wins) else 0.0,
        "Average loss (% of equity)": losses.mean() if len(losses) else 0.0,
        "Largest loss (% of equity)": r.min(),
        "Largest win (% of equity)": r.max(),
        "Payoff ratio (avg win / avg loss)": wins.mean() / -losses.mean() if len(wins) and len(losses) else float("nan"),
        "Profit factor (gross wins / gross losses)": (trades.net_pnl[trades.net_pnl > 0].sum()
                                                      / -trades.net_pnl[trades.net_pnl <= 0].sum()),
        "Expectancy per trade (% of equity)": r.mean(),
        "Worst day (%)": 100 * daily.min(),
        "Worst 7 days (%)": 100 * ((1 + daily).rolling(7).apply(lambda x: x.prod()) - 1).min(),
        "Worst 30 days (%)": 100 * ((1 + daily).rolling(30).apply(lambda x: x.prod()) - 1).min(),
        "Daily 95% VaR (%)": 100 * daily.quantile(0.05),
        "Daily 95% CVaR (%)": 100 * daily[daily <= daily.quantile(0.05)].mean(),
        "Exit reasons": ", ".join(f"{k} {v}" for k, v in trades.exit_reason.value_counts().items()),
    }


def plot_layers(data: pd.DataFrame, signals: pd.DataFrame, path: Path, title: str):
    layers = btc_layers(data)
    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1, 1.4]})
    axes[0].plot(data["close"], color="#F7931A", lw=1)
    axes[0].set_yscale("log")
    axes[0].set_title(title)
    axes[0].set_ylabel("BTC (log)")
    axes[1].plot(layers["trend"], lw=0.9)
    axes[1].set_ylabel("trend votes")
    axes[2].plot(layers["regime"], lw=0.9, color="tab:green", label="regime size")
    axes[2].plot(layers["gate"], lw=0.9, color="tab:purple", label="soft gate")
    axes[2].plot(layers["storm_brake"] * layers["squeeze"], lw=0.9, color="tab:red", label="storm x squeeze")
    axes[2].legend(loc="upper left", fontsize=8, ncol=3)
    axes[3].fill_between(signals.index, signals["target"], step="post", alpha=0.6)
    axes[3].set_ylabel("target exposure")
    axes[3].set_ylim(0, 1.6)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    data = load_daily_with_realised("BTCUSDT")
    lines = ["# BTC/USDT strategy: Calm-Trend Regime (CTR), results", "",
             "Logic and risk plan: `reports/btc_strategy.md`. 10,000 USDT start, 0.15% per fill, max 1.5x equity, "
             "8%/yr on borrowed USDT.", ""]
    table, risk = {}, {}
    for label, (start, end) in PERIODS.items():
        result, period = run_on_period(data, btc_signal, start, end, trading_config())
        metrics = compute_metrics(result, period)
        log_experiment("btc_final", "BTCUSDT", {"strategy": "calm_trend_regime"}, start, end, result.config, metrics)
        save_report(result, period, metrics, OUT / label, title=f"BTC Calm-Trend Regime, {label}")
        stressed, _ = run_on_period(data, btc_signal, start, end, trading_config(0.003), check=False)
        table[label] = {k: metrics[k] for k in REQUIRED + EXTRA} | {"Sharpe at 2x costs": compute_metrics(stressed, period)["Sharpe Ratio"]}
        risk[label] = risk_analysis(result)
        yearly = yearly_breakdown(result, period)
        yearly.to_csv(OUT / label / "yearly.csv")
        plot_layers(period, btc_signal(data.loc[:end]).loc[start:end], OUT / label / "layers.png",
                    f"BTC Calm-Trend Regime: decision layers, {label}")
        if label == "2021-2025":
            lines += ["## By year (2021-2025)", "", markdown_table(yearly.round(2)), ""]
    metrics_table = pd.DataFrame(table).map(fmt)
    lines = lines[:4] + ["## Required metrics (and extras)", "", markdown_table(metrics_table), "",
                         "## Risk / reward of the closed trades", "", markdown_table(pd.DataFrame(risk).map(fmt)), ""] + lines[4:]
    lines += ["Charts per period: `equity.png` (equity and drawdown vs buy-and-hold), `trades.png`, `layers.png`. "
              "Trade history: `trades.csv`; quarterly: `quarterly.csv`."]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print(metrics_table.to_string())
    print(pd.DataFrame(risk).map(fmt).to_string())


if __name__ == "__main__":
    main()
