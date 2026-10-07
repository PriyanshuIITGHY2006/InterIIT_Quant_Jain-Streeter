# ETH/USDT strategy: Calm-Trend Regime (CTR-ETH), results

Logic and risk plan: `reports/eth_strategy.md`. 10,000 USDT start, 0.15% per fill, max 1.5x equity, 8%/yr on borrowed USDT.

## Required metrics (and extras)

| | 2021-2024 | 2025 | 2021-2025 |
|---|---|---|---|
| Gross Profit (USDT) | 36,994.95 | 6,570.38 | 60,041.03 |
| Net Profit (USDT) | 27,413.69 | 5,487.85 | 48,168.68 |
| Total Closed Trades | 18 | 4 | 21 |
| Win Rate (%) | 27.78 | 25.00 | 23.81 |
| Max Drawdown (%) | -37.34 | -24.97 | -37.34 |
| Gross Loss (USDT) | -9,581.26 | -1,082.54 | -11,872.35 |
| Average Winning Trade (USDT) | 7,398.99 | 6,570.38 | 12,008.21 |
| Average Losing Trade (USDT) | -737.02 | -360.85 | -742.02 |
| Buy-and-Hold Return (%) | 356.54 | -11.83 | 306.46 |
| Largest Losing Trade (USDT) | -3,360.95 | -925.39 | -3,360.95 |
| Largest Winning Trade (USDT) | 16,511.50 | 6,570.38 | 24,676.80 |
| Sharpe Ratio | 0.90 | 1.23 | 0.96 |
| Sortino Ratio | 1.43 | 2.03 | 1.53 |
| Average Holding Duration | 60 days 21:20:00 | 63 days 00:00:00 | 64 days 06:51:25.714285 |
| Maximum Holding Duration | 258 days 00:00:00 | 205 days 00:00:00 | 258 days 00:00:00 |
| Total Return (%) | 274.14 | 54.88 | 481.69 |
| Annualised Return (%) | 39.05 | 54.88 | 42.19 |
| Calmar Ratio | 1.05 | 2.20 | 1.13 |
| Quarters Beating Buy-and-Hold (%) | 43.75 | 75.00 | 50.00 |
| Long Trades | 18 | 4 | 21 |
| Short Trades | 0 | 0 | 0 |
| Max Drawdown Recovery Time | 828 days 00:00:00 | None | 828 days 00:00:00 |
| Longest Time Under Water | 828 days 00:00:00 | 185 days 00:00:00 | 828 days 00:00:00 |
| Exposure (%) | 75.02 | 69.04 | 73.93 |
| Total Fees (USDT) | 2,486.51 | 206.59 | 3,223.37 |
| Total Financing (USDT) | 566.69 | 49.68 | 753.28 |
| Buy-and-Hold Sharpe Ratio | 0.87 | 0.20 | 0.75 |
| Buy-and-Hold Max Drawdown (%) | -79.30 | -60.04 | -79.30 |
| Sharpe at 2x costs | 0.85 | 1.19 | 0.91 |

## Risk / reward of the closed trades

| | 2021-2024 | 2025 | 2021-2025 |
|---|---|---|---|
| Average win (% of equity) | 42.32 | 73.06 | 56.02 |
| Average loss (% of equity) | -2.47 | -3.55 | -2.39 |
| Largest loss (% of equity) | -8.33 | -9.25 | -8.33 |
| Largest win (% of equity) | 69.28 | 73.06 | 73.06 |
| Payoff ratio (avg win / avg loss) | 17.13 | 20.61 | 23.43 |
| Profit factor (gross wins / gross losses) | 3.86 | 6.07 | 5.06 |
| Expectancy per trade (% of equity) | 9.97 | 15.61 | 11.52 |
| Worst day (%) | -18.57 | -12.32 | -18.57 |
| Worst 7 days (%) | -25.70 | -18.40 | -25.70 |
| Worst 30 days (%) | -31.94 | -21.53 | -31.94 |
| Daily 95% VaR (%) | -3.63 | -2.53 | -3.48 |
| Daily 95% CVaR (%) | -6.09 | -5.08 | -5.91 |
| Exit reasons | signal 17, end_of_data 1 | signal 4 | signal 21 |

## By year (2021-2025)

| | strategy return % | strategy max DD % | strategy Sharpe | asset return % | asset max DD % | asset Sharpe |
|---|---|---|---|---|---|---|
| 2021 | 174.98 | -37.24 | 1.64 | 399.20 | -57.20 | 2.03 |
| 2022 | -20.16 | -22.45 | -1.34 | -67.46 | -74.01 | -0.86 |
| 2023 | 39.99 | -26.21 | 0.96 | 90.77 | -27.33 | 1.61 |
| 2024 | 21.79 | -33.61 | 0.72 | 46.27 | -45.26 | 0.90 |
| 2025 | 55.39 | -24.97 | 1.23 | -10.97 | -60.04 | 0.21 |

Charts per period: `equity.png` (equity and drawdown vs buy-and-hold), `trades.png`, `layers.png`. Trade history: `trades.csv`; quarterly: `quarterly.csv`.
