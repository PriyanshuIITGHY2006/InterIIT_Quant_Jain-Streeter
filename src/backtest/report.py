"""Save a backtest's tables and charts to a results folder."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.backtest.metrics import buy_and_hold, quarterly_comparison
from src.backtest.structures import BacktestResult


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def metrics_markdown(metrics: dict, title: str) -> str:
    lines = [f"# {title}", "", "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {_fmt(v)} |" for k, v in metrics.items()]
    return "\n".join(lines) + "\n"


def plot_equity(result: BacktestResult, data: pd.DataFrame, path: Path, title: str):
    bench = buy_and_hold(data, result.config)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(result.equity, label="Strategy", lw=1)
    ax1.plot(bench, label="Buy & hold", lw=1, alpha=0.7)
    ax1.set_yscale("log")
    ax1.set_ylabel("Equity (USDT, log scale)")
    ax1.set_title(title)
    ax1.legend()
    for eq, label in [(result.equity, "Strategy"), (bench, "Buy & hold")]:
        ax2.plot(100 * (eq / eq.cummax() - 1), lw=0.8, label=label)
    ax2.set_ylabel("Drawdown (%)")
    ax2.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_trades(result: BacktestResult, data: pd.DataFrame, path: Path, title: str):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(data["close"], color="grey", lw=0.6)
    t = result.trades
    if len(t):
        for side, marker, color in [("long", "^", "tab:green"), ("short", "v", "tab:red")]:
            s = t[t["side"] == side]
            ax.scatter(s["entry_time"], s["entry_price"], marker=marker, color=color, s=12, label=f"{side} entry")
        ax.scatter(t["exit_time"], t["exit_price"], marker="x", color="black", s=8, label="exit")
        ax.legend()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save_report(result: BacktestResult, data: pd.DataFrame, metrics: dict, out_dir, title: str):
    """Write metrics (CSV + Markdown), trades, fills, equity, the quarterly table and charts."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pd.Series({k: _fmt(v) for k, v in metrics.items()}, name="value").to_csv(out / "metrics.csv")
    (out / "metrics.md").write_text(metrics_markdown(metrics, title))
    result.trades.to_csv(out / "trades.csv", index=False)
    result.fills.to_csv(out / "fills.csv", index=False)
    pd.concat([result.equity, result.cash, result.position], axis=1).to_csv(out / "equity.csv")
    quarterly_comparison(result.equity, data, result.config.initial_capital).to_csv(out / "quarterly.csv")
    plot_equity(result, data, out / "equity.png", title)
    plot_trades(result, data, out / "trades.png", title)
