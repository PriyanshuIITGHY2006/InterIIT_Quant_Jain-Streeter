"""Run the final ETH/USDT strategy (Calm-Trend Regime for ETH) and write every deliverable to results/eth/.

Same periods and outputs as scripts/run_btc_strategy.py: 2021-2024, 2025, 2021-2025 (the required 5-year
backtest); all metrics, trade history, fills, equity, quarterly and yearly tables, 2x-cost stress, risk analysis,
equity/drawdown, trade and decision-layer charts. Summary: results/eth/summary.md.

Run from the project root:  .venv/bin/python -m scripts.run_eth_strategy
"""
from pathlib import Path

from scripts.run_btc_strategy import run_final
from src.strategies.eth_strategy import eth_layers, eth_signal

OUT = Path("results/eth")


def main():
    run_final("ETHUSDT", eth_signal, eth_layers, OUT, "Calm-Trend Regime (CTR-ETH)", "reports/eth_strategy.md", "ETH", "#627EEA")


if __name__ == "__main__":
    main()
