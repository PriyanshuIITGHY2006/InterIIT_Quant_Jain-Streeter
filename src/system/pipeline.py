"""One run of the system on a dataset: clean -> analyse -> verify causality -> backtest -> report.

Output folder (default runs/<asset>_<input name>_<UTC time>/):
  report.md            the run report: data quality, analysis, strategy results, the next decision
  manifest.json        inputs, file hash, period, versions, git commit (for exact reproduction)
  data_quality.json    cleaning report
  signal_today.json    the position the strategy wants from the next daily open
  daily_signals.csv    every day's target position and decision layers
  analysis/            return statistics, structure tests, market states, charts
  backtest/            all metrics, trades, fills, equity, quarterly and yearly tables, charts
"""
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest.checks import check_signals_causal
from src.backtest.evaluation import run_on_period, yearly_breakdown
from src.backtest.metrics import compute_metrics
from src.backtest.report import markdown_table, save_report
from src.system import analysis
from src.system.ingest import load_dataset
from src.system.strategies import FrozenStrategy, get

ROOT = Path(__file__).resolve().parents[2]
WARMUP_DAYS = 200
REQUIRED = ["Gross Profit (USDT)", "Net Profit (USDT)", "Total Closed Trades", "Win Rate (%)", "Max Drawdown (%)",
            "Gross Loss (USDT)", "Average Winning Trade (USDT)", "Average Losing Trade (USDT)", "Buy-and-Hold Return (%)",
            "Largest Losing Trade (USDT)", "Largest Winning Trade (USDT)", "Sharpe Ratio", "Sortino Ratio",
            "Average Holding Duration", "Maximum Holding Duration"]
EXTRA = ["Total Return (%)", "Annualised Return (%)", "Calmar Ratio", "Quarters Beating Buy-and-Hold (%)",
         "Long Trades", "Short Trades", "Exposure (%)", "Total Fees (USDT)", "Total Financing (USDT)",
         "Buy-and-Hold Sharpe Ratio", "Buy-and-Hold Max Drawdown (%)", "Longest Time Under Water"]


def _fmt(v):
    if isinstance(v, (float, np.floating)):
        return f"{v:,.2f}"
    if isinstance(v, pd.Timedelta):
        return f"{v.days} d {v.components.hours} h" if v.components.hours else f"{v.days} d"
    return str(v)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5, check=True).stdout.strip() or None
    except Exception:
        return None


def _versions() -> dict:
    import matplotlib
    import scipy
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "scipy": scipy.__version__, "matplotlib": matplotlib.__version__}


def next_decision(strategy: FrozenStrategy, frame: pd.DataFrame, signals: pd.DataFrame, states: pd.Series) -> dict:
    """The decision made at the last available daily close, to be executed at the next open."""
    last = frame.index[-1]
    layers = strategy.layers(frame).iloc[-1]
    target = float(signals["target"].iloc[-1])
    side = "LONG" if target > 0 else "SHORT" if target < 0 else "FLAT"
    return {"decided_at_close_of": str(last.date()), "execute_at": str((last + pd.Timedelta(days=1)).date()) + " 00:00 UTC open",
            "target_position_x_equity": round(target, 4), "side": side, "market_state": str(states.iloc[-1]),
            "layers": {k: round(float(v), 4) for k, v in layers.items()}}


def run(data_path: str | Path, asset: str, start: str | None = None, end: str | None = None,
        out: str | Path | None = None, verify: bool = True, log=print) -> dict:
    strategy = get(asset)
    data_path = Path(data_path)
    log(f"loading {data_path}")
    ds = load_dataset(data_path, strategy.symbol)
    frame = ds.strategy_frame
    start = pd.Timestamp(start or frame.index[0]).strftime("%Y-%m-%d")
    end = pd.Timestamp(end or frame.index[-1]).strftime("%Y-%m-%d")
    frame = frame.loc[:end]
    if len(frame.loc[start:end]) < 30:
        raise ValueError(f"the period {start} -> {end} has fewer than 30 days of data")
    history = len(frame.loc[:start]) - 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(out) if out else ROOT / "runs" / f"{strategy.key}_{data_path.stem}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    notes = []
    if history < WARMUP_DAYS:
        notes.append(f"Cold start: only {history} days of history before {start}. Indicators warm up adaptively, "
                     f"but the first months use short windows. Load at least {WARMUP_DAYS} earlier days for a full warm-up.")

    if verify:
        log("verifying causality (signals recomputed on truncated data must not change)")
        check_signals_causal(strategy.signal, frame)

    log(f"backtesting {strategy.name} on {start} -> {end}")
    result, period = run_on_period(frame, strategy.signal, start, end, strategy.config(), check=False)
    metrics = compute_metrics(result, period)
    stressed, _ = run_on_period(frame, strategy.signal, start, end, strategy.config(0.003), check=False)
    metrics["Sharpe at 2x costs"] = compute_metrics(stressed, period)["Sharpe Ratio"]
    title = f"{strategy.symbol[:3]} {strategy.name.split(' (')[0]}, {start} to {end}"
    save_report(result, period, metrics, out / "backtest", title=title)
    yearly = yearly_breakdown(result, period)
    yearly.to_csv(out / "backtest" / "yearly.csv")

    from scripts.run_btc_strategy import plot_layers, risk_analysis
    signals = strategy.signal(frame)
    plot_layers(period, signals.loc[start:end], out / "backtest" / "layers.png", f"{title}: decision layers",
                strategy.layers, strategy.symbol[:3], strategy.color)
    risk = risk_analysis(result) if len(result.trades) else {}
    strategy.layers(frame).assign(target=signals["target"]).loc[start:end].to_csv(out / "daily_signals.csv")

    log("analysing the data")
    an = analysis.analyse(frame, start, end, signals["target"], out / "analysis", strategy.symbol, strategy.color)
    states = pd.read_csv(out / "analysis" / "daily_states.csv", index_col=0, parse_dates=True)["state"]
    decision = next_decision(strategy, frame, signals, states)

    (out / "data_quality.json").write_text(json.dumps(ds.quality, indent=2))
    (out / "signal_today.json").write_text(json.dumps(decision, indent=2))
    manifest = {"system": "ctr", "strategy": strategy.name, "asset": strategy.symbol, "input": str(data_path),
                "input_sha256": _sha256(data_path), "period": [start, end], "history_days_before_start": history,
                "causality_verified": verify, "created_utc": stamp, "git_commit": _git_commit(), "versions": _versions(),
                "costs": {"fee_and_slippage_per_fill": result.config.cost_rate, "max_position": result.config.max_position,
                          "usdt_borrow_rate": result.config.borrow_rate, "coin_borrow_rate": result.config.short_borrow_rate,
                          "shorts_allowed": result.config.allow_short}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    table = pd.DataFrame({"value": {k: _fmt(metrics[k]) for k in REQUIRED + EXTRA + ["Sharpe at 2x costs"]}})
    q = ds.quality
    lines = [f"# {strategy.symbol}: {strategy.name}", "",
             f"Run `{out.name}` · input `{data_path.name}` (sha256 {manifest['input_sha256'][:12]}…) · period **{start} → {end}** "
             f"· {history} days of warm-up history · causality check: {'passed' if verify else 'skipped'}", ""]
    lines += [f"> {n}" for n in notes] + ([""] if notes else [])
    lines += ["## Next decision", "",
              f"At the close of **{decision['decided_at_close_of']}** the strategy wants **{decision['side']} "
              f"{abs(decision['target_position_x_equity']):.2f}× equity** from the next open "
              f"(market state: {decision['market_state']}).", "",
              "## Data quality", "",
              f"- {q['rows_in']:,} input rows ({q['input_bar']} bars), {q['bars']:,} after completing the time grid, {q['days']:,} days",
              f"- duplicates removed: {q['duplicates_removed']}; OHLC rows repaired: {q['ohlc_rows_repaired']}",
              f"- missing bars filled forward (no trading on them): {q['missing_bars_filled']}; empty outage bars: {q['empty_outage_bars']}",
              f"- realised measures: {q['realised_measures']}", "",
              "## Strategy results (0.15% per fill, next-open execution)", "", markdown_table(table), "",
              "### By year", "", markdown_table(yearly.round(2)), ""]
    if risk:
        lines += ["### Risk and reward of the closed trades", "",
                  markdown_table(pd.DataFrame({"value": {k: _fmt(v) for k, v in risk.items()}})), ""]
    lines += ["![equity](backtest/equity.png)", "", "![layers](backtest/layers.png)", "",
              "## Data analysis (descriptive)", "", *[f"- {x}" for x in an["reading"]], "",
              "### Return statistics", "", markdown_table(an["returns"].round(2)), "",
              "### Structure tests", "", markdown_table(pd.DataFrame({"value": an["structure"]}).round(3)), "",
              "### Market states", "", "States use only past data; the next-7-day columns look ahead and are descriptive.", "",
              markdown_table(an["states"].round(3)), "",
              "![overview](analysis/overview.png)", "", "![states](analysis/states.png)", "", "![returns](analysis/returns.png)", ""]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return {"out": out, "metrics": metrics, "decision": decision, "quality": q, "notes": notes,
            "reading": an["reading"], "start": start, "end": end, "strategy": strategy}
