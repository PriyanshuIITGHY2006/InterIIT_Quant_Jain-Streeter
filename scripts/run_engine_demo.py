"""Demonstrate the backtest engine on the train split.

The signal below is a PLACEHOLDER to exercise the engine end to end (entries, stops, costs,
metrics, charts). It is not a strategy and its results mean nothing.

Run from the project root:
    .venv/bin/python -m scripts.run_engine_demo
"""
import pandas as pd

from src.backtest import BacktestConfig, backtest, compute_metrics, save_report
from src.data.loader import load_market


def placeholder_signal(data: pd.DataFrame) -> pd.DataFrame:
    """Long when the close is above its 200-bar trailing mean; stop at 3x the 24-bar average range."""
    above = data["close"] > data["close"].rolling(200).mean()
    stop = 3 * (data["high"] - data["low"]).rolling(24).mean()
    return pd.DataFrame({"target": above.astype(float), "stop_dist": stop}, index=data.index)


def main():
    config = BacktestConfig()
    for symbol, folder in [("BTCUSDT", "btc"), ("ETHUSDT", "eth")]:
        data = load_market(symbol, "1h", "train")
        result = backtest(data, placeholder_signal, config)          # checks for look-ahead first
        metrics = compute_metrics(result, data)
        save_report(result, data, metrics, f"results/{folder}/engine_demo",
                    f"{symbol} engine demo (placeholder signal, train 2021-2023)")
        print(f"{symbol}: {metrics['Total Closed Trades']} trades, "
              f"net {metrics['Net Profit (USDT)']:,.0f} USDT, fees {metrics['Total Fees (USDT)']:,.0f} USDT, "
              f"max DD {metrics['Max Drawdown (%)']:.1f}%, buy & hold {metrics['Buy-and-Hold Return (%)']:.1f}%")


if __name__ == "__main__":
    main()
