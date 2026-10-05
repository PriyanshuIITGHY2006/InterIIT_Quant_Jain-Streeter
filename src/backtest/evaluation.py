"""Helpers for evaluating strategies the same way every time (see docs/evaluation_protocol.md)."""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest.checks import check_signals_causal
from src.backtest.engine import run_backtest
from src.backtest.structures import BacktestConfig, BacktestResult

EXPERIMENT_LOG = Path(__file__).resolve().parents[2] / "results" / "experiment_log.csv"


def run_on_period(full_data: pd.DataFrame, signal_fn, start: str, end: str,
                  config: BacktestConfig, check: bool = True) -> tuple[BacktestResult, pd.DataFrame]:
    """Backtest `signal_fn` on [start, end].

    Signals are computed on all history up to `end` (earlier data only warms up indicators;
    nothing after `end` is ever passed in), then the period is sliced out and run.
    """
    history = full_data.loc[:end]
    if check:
        check_signals_causal(signal_fn, history)
    signals = signal_fn(history).loc[start:end]
    data = history.loc[start:end]
    return run_backtest(data, signals, config), data


def _max_drawdown(returns: pd.Series) -> float:
    wealth = np.concatenate([[1.0], (1 + returns).cumprod().to_numpy()])
    return 100 * (wealth / np.maximum.accumulate(wealth) - 1).min()


def yearly_breakdown(result: BacktestResult, data: pd.DataFrame) -> pd.DataFrame:
    """Return, max drawdown and Sharpe of the strategy and of the asset for each calendar year (daily data)."""
    eq = result.equity.resample("1D").last()
    strategy = eq / eq.shift(1).fillna(result.config.initial_capital) - 1
    px = data["close"].resample("1D").last()
    asset = px / px.shift(1).fillna(data["open"].iloc[0]) - 1

    rows = {}
    for year in sorted(set(strategy.index.year)):
        s, a = strategy[strategy.index.year == year], asset[asset.index.year == year]
        rows[year] = {
            "strategy return %": 100 * ((1 + s).prod() - 1),
            "strategy max DD %": _max_drawdown(s),
            "strategy Sharpe": s.mean() / s.std() * np.sqrt(365) if s.std() > 0 else 0.0,
            "asset return %": 100 * ((1 + a).prod() - 1),
            "asset max DD %": _max_drawdown(a),
            "asset Sharpe": a.mean() / a.std() * np.sqrt(365) if a.std() > 0 else 0.0,
        }
    return pd.DataFrame(rows).T


def log_experiment(name: str, asset: str, params: dict, start: str, end: str,
                   config: BacktestConfig, metrics: dict, path: Path | None = None):
    """Append one run to the experiment log (default: module-level EXPERIMENT_LOG).
    Every run is recorded; nothing is ever removed."""
    path = path or EXPERIMENT_LOG
    row = {
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": name,
        "asset": asset,
        "params": json.dumps(params, sort_keys=True),
        "start": start,
        "end": end,
        "cost_rate": config.cost_rate,
        "sharpe": metrics["Sharpe Ratio"],
        "max_drawdown_pct": metrics["Max Drawdown (%)"],
        "total_return_pct": metrics["Total Return (%)"],
        "cagr_pct": metrics["Annualised Return (%)"],
        "calmar": metrics["Calmar Ratio"],
        "quarters_beating_bh_pct": metrics["Quarters Beating Buy-and-Hold (%)"],
        "trades": metrics["Total Closed Trades"],
        "fees": metrics["Total Fees (USDT)"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(path, mode="a", header=not path.exists(), index=False)


def summary_row(metrics: dict) -> dict:
    """The scorecard columns from the evaluation protocol."""
    keys = ["Total Return (%)", "Annualised Return (%)", "Sharpe Ratio", "Sortino Ratio", "Max Drawdown (%)",
            "Calmar Ratio", "Quarters Beating Buy-and-Hold (%)", "Longest Time Under Water",
            "Total Closed Trades", "Total Fees (USDT)", "Exposure (%)"]
    return {k: metrics[k] for k in keys}


def deflated_sharpe(daily_returns: pd.Series, trial_sharpes_annual: pd.Series, periods_per_year: int = 365) -> dict:
    """Deflated Sharpe ratio (Bailey & Lopez de Prado, 2014).

    Probability that the strategy's true Sharpe is above zero after accounting for having picked the
    best of N trials (N = len(trial_sharpes_annual)), the track-record length, skewness and kurtosis.
    """
    from scipy.stats import kurtosis, norm, skew

    r = daily_returns.dropna()
    t = len(r)
    sr = r.mean() / r.std()                                                 # per-period Sharpe
    trials = trial_sharpes_annual.dropna() / np.sqrt(periods_per_year)      # per-period trial Sharpes
    n, euler = len(trials), 0.5772156649
    sr0 = np.sqrt(trials.var()) * ((1 - euler) * norm.ppf(1 - 1 / n) + euler * norm.ppf(1 - 1 / (n * np.e)))
    g3, g4 = skew(r), kurtosis(r, fisher=False)
    z = (sr - sr0) * np.sqrt(t - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return {"trials": n, "annual Sharpe": sr * np.sqrt(periods_per_year),
            "expected max Sharpe of luck (annual)": sr0 * np.sqrt(periods_per_year),
            "deflated Sharpe (probability true Sharpe > 0)": float(norm.cdf(z))}
