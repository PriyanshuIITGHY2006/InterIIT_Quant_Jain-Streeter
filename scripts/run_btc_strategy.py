"""Run the final BTC/USDT strategy (CTR-S: Calm-Trend Regime with calm-bear shorts) and write every deliverable to results/btc/.

Periods
  2021-2024   development data (the strategy was designed and selected here)
  2025        the last year of the competition data
  2021-2025   the required 5-year backtest
For each period: all metrics, trade history, fills, equity, quarterly table, equity/drawdown and trade charts.
Plus: a yearly table, a 2x-cost stress test, a risk analysis (payoff ratio, expectancy, adverse excursion)
a chart of every decision layer, and a by-year comparison with the long-only CTR. Summary: results/btc/summary.md.

Run from the project root:  .venv/bin/python -m scripts.run_btc_strategy
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.backtest.evaluation import log_experiment, run_on_period, yearly_breakdown
from src.backtest.metrics import buy_and_hold, compute_metrics
from src.backtest.report import markdown_table, save_report
from src.data.loader import load_daily_with_realised
from src.strategies.btc_strategy import btc_layers, btc_signal, ctr_long_signal
from src.strategies.execution import btc_trading_config, trading_config

OUT = Path("results/btc")
PERIODS = {"2021-2024": ("2021-01-01", "2024-12-31"), "2025": ("2025-01-01", "2025-12-31"),
           "2021-2025": ("2021-01-01", "2025-12-31")}
REQUIRED = ["Gross Profit (USDT)", "Net Profit (USDT)", "Total Closed Trades", "Win Rate (%)", "Max Drawdown (%)",
            "Gross Loss (USDT)", "Average Winning Trade (USDT)", "Average Losing Trade (USDT)", "Buy-and-Hold Return (%)",
            "Largest Losing Trade (USDT)", "Largest Winning Trade (USDT)", "Sharpe Ratio", "Sortino Ratio",
            "Average Holding Duration", "Maximum Holding Duration"]
EXTRA = ["Total Return (%)", "Annualised Return (%)", "Calmar Ratio", "Quarters Beating Buy-and-Hold (%)", "Long Trades", "Short Trades",
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


def plot_layers(data: pd.DataFrame, signals: pd.DataFrame, path: Path, title: str, layers_fn=btc_layers,
                asset: str = "BTC", color: str = "#F7931A"):
    layers = layers_fn(data)
    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1, 1.4]})
    axes[0].plot(data["close"], color=color, lw=1)
    axes[0].set_yscale("log")
    axes[0].set_title(title)
    axes[0].set_ylabel(f"{asset} (log)")
    axes[1].plot(layers["trend"], lw=0.9)
    axes[1].set_ylabel("trend votes")
    axes[2].plot(layers["regime"], lw=0.9, color="tab:green", label="regime size")
    axes[2].plot(layers["gate"], lw=0.9, color="tab:purple", label="soft gate")
    axes[2].plot(layers["storm_brake"] * layers["squeeze"], lw=0.9, color="tab:red", label="storm x squeeze")
    axes[2].legend(loc="upper left", fontsize=8, ncol=3)
    t = signals["target"]
    axes[3].fill_between(t.index, t.clip(lower=0), step="post", alpha=0.6, label="long")
    if (t < 0).any():
        axes[3].fill_between(t.index, t.clip(upper=0), step="post", alpha=0.6, color="tab:red", label="short")
        axes[3].legend(loc="upper left", fontsize=8, ncol=2)
    axes[3].set_ylabel("target exposure")
    axes[3].set_ylim(min(0.0, t.min()) - 0.1, 1.6)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def run_final(symbol: str, signal_fn, layers_fn, out: Path, name: str, doc: str, asset: str, color: str,
              config_fn=trading_config, strategy_id: str = "calm_trend_regime", extra_lines=None):
    """Run a final strategy on every period and write all deliverables to `out`.

    `config_fn(cost_rate)` builds the execution settings; `extra_lines(data)` may add a section to the summary.
    """
    data = load_daily_with_realised(symbol)
    lines = [f"# {symbol[:3]}/USDT strategy: {name}, results", "",
             f"Logic and risk plan: `{doc}`. 10,000 USDT start, 0.15% per fill, max 1.5x equity, 8%/yr on borrowed USDT"
             + (", 10%/yr on borrowed coins (shorts)." if config_fn().allow_short else "."), ""]
    table, risk = {}, {}
    for label, (start, end) in PERIODS.items():
        result, period = run_on_period(data, signal_fn, start, end, config_fn())
        metrics = compute_metrics(result, period)
        log_experiment(f"{asset.lower()}_final", symbol, {"strategy": strategy_id}, start, end, result.config, metrics)
        save_report(result, period, metrics, out / label, title=f"{asset} {name}, {label}")
        stressed, _ = run_on_period(data, signal_fn, start, end, config_fn(0.003), check=False)
        table[label] = {k: metrics[k] for k in REQUIRED + EXTRA} | {"Sharpe at 2x costs": compute_metrics(stressed, period)["Sharpe Ratio"]}
        risk[label] = risk_analysis(result)
        yearly = yearly_breakdown(result, period)
        yearly.to_csv(out / label / "yearly.csv")
        plot_layers(period, signal_fn(data.loc[:end]).loc[start:end], out / label / "layers.png",
                    f"{asset} {name}: decision layers, {label}", layers_fn, asset, color)
        if label == "2021-2025":
            lines += ["## By year (2021-2025)", "", markdown_table(yearly.round(2)), ""]
    metrics_table = pd.DataFrame(table).map(fmt)
    lines = lines[:4] + ["## Required metrics (and extras)", "", markdown_table(metrics_table), "",
                         "## Risk / reward of the closed trades", "", markdown_table(pd.DataFrame(risk).map(fmt)), ""] + lines[4:]
    if extra_lines is not None:
        lines += extra_lines(data)
    lines += ["Charts per period: `equity.png` (equity and drawdown vs buy-and-hold), `trades.png`, `layers.png`. "
              "Trade history: `trades.csv`; quarterly: `quarterly.csv`."]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print(metrics_table.to_string())
    print(pd.DataFrame(risk).map(fmt).to_string())


def compare_with_ctr(data: pd.DataFrame) -> list[str]:
    """By-year returns (one continuous 2021-2025 run) of CTR-S vs the long-only CTR vs buy-and-hold, plus a chart."""
    start, end = PERIODS["2021-2025"]
    rows, curves = {}, {}
    for name, fn, cfg in [("CTR-S (final)", btc_signal, btc_trading_config()), ("CTR (long only)", ctr_long_signal, trading_config())]:
        result, period = run_on_period(data, fn, start, end, cfg, check=False)
        y = yearly_breakdown(result, period)
        rows[name + " return %"] = y["strategy return %"]
        rows[name + " max DD %"] = y["strategy max DD %"]
        curves[name] = result.equity
    rows["BTC return %"] = y["asset return %"]
    table = pd.DataFrame(rows)
    table.index = table.index.astype(int)
    fig, ax = plt.subplots(figsize=(12, 5))
    for (name, eq), col in zip(curves.items(), ["tab:green", "tab:blue"]):
        ax.plot(eq, label=name, color=col, lw=1.2)
    ax.plot(buy_and_hold(period, trading_config()), label="Buy & hold", color="#F7931A", lw=1)
    ax.set_yscale("log")
    ax.set_title("BTC 2021-2025: CTR-S vs the long-only CTR vs buy-and-hold")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "ctr_s_vs_ctr.png", dpi=120)
    plt.close(fig)
    return ["## CTR-S vs the long-only CTR, return by year (%)", "", markdown_table(table.round(2)), "",
            "Chart: `ctr_s_vs_ctr.png`.", ""]


def main():
    run_final("BTCUSDT", btc_signal, btc_layers, OUT, "Calm-Trend Regime with calm-bear shorts (CTR-S)",
              "reports/btc_strategy.md", "BTC", "#F7931A", config_fn=btc_trading_config,
              strategy_id="calm_trend_regime_short", extra_lines=compare_with_ctr)


if __name__ == "__main__":
    main()
