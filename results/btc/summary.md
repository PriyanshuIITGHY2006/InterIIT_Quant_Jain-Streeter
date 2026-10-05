# BTC/USDT strategy: Calm-Trend Regime (CTR), results

Logic and risk plan: `reports/btc_strategy.md`. 10,000 USDT start, 0.15% per fill, max 1.5x equity, 8%/yr on borrowed USDT.

## Required metrics (and extras)

| | 2021-2024 | 2025 | 2021-2025 |
|---|---|---|---|
| Gross Profit (USDT) | 43,685.77 | 295.46 | 42,639.75 |
| Net Profit (USDT) | 37,315.25 | -413.51 | 35,812.22 |
| Total Closed Trades | 18 | 4 | 21 |
| Win Rate (%) | 27.78 | 25.00 | 28.57 |
| Max Drawdown (%) | -37.53 | -19.93 | -37.53 |
| Gross Loss (USDT) | -6,370.53 | -708.97 | -6,827.53 |
| Average Winning Trade (USDT) | 8,737.15 | 295.46 | 7,106.63 |
| Average Losing Trade (USDT) | -490.04 | -236.32 | -455.17 |
| Buy-and-Hold Return (%) | 218.07 | -7.62 | 197.92 |
| Largest Losing Trade (USDT) | -3,739.80 | -613.34 | -3,739.80 |
| Largest Winning Trade (USDT) | 18,768.61 | 295.46 | 18,768.61 |
| Sharpe Ratio | 1.16 | -0.02 | 0.98 |
| Sortino Ratio | 1.94 | -0.02 | 1.61 |
| Average Holding Duration | 60 days 17:20:00 | 72 days 00:00:00 | 65 days 20:34:17.142857 |
| Maximum Holding Duration | 290 days 00:00:00 | 196 days 00:00:00 | 290 days 00:00:00 |
| Total Return (%) | 373.15 | -4.14 | 358.12 |
| Annualised Return (%) | 47.45 | -4.14 | 35.56 |
| Calmar Ratio | 1.26 | -0.21 | 0.95 |
| Quarters Beating Buy-and-Hold (%) | 56.25 | 50.00 | 55.00 |
| Max Drawdown Recovery Time | 723 days 00:00:00 | None | 723 days 00:00:00 |
| Longest Time Under Water | 723 days 00:00:00 | 223 days 00:00:00 | 723 days 00:00:00 |
| Exposure (%) | 74.81 | 78.90 | 75.74 |
| Total Fees (USDT) | 2,721.89 | 250.48 | 3,834.28 |
| Total Financing (USDT) | 583.26 | 73.06 | 932.43 |
| Buy-and-Hold Sharpe Ratio | 0.78 | 0.02 | 0.67 |
| Buy-and-Hold Max Drawdown (%) | -76.63 | -32.02 | -76.63 |
| Sharpe at 2x costs | 1.09 | -0.10 | 0.91 |

## Risk / reward of the closed trades

| | 2021-2024 | 2025 | 2021-2025 |
|---|---|---|---|
| Average win (% of equity) | 48.38 | 3.17 | 39.55 |
| Average loss (% of equity) | -2.24 | -2.38 | -2.01 |
| Largest loss (% of equity) | -10.58 | -6.13 | -10.58 |
| Largest win (% of equity) | 113.28 | 3.17 | 113.28 |
| Payoff ratio (avg win / avg loss) | 21.62 | 1.33 | 19.70 |
| Profit factor (gross wins / gross losses) | 6.86 | 0.42 | 6.25 |
| Expectancy per trade (% of equity) | 11.82 | -0.99 | 9.87 |
| Worst day (%) | -15.70 | -10.84 | -15.70 |
| Worst 7 days (%) | -23.75 | -14.14 | -23.75 |
| Worst 30 days (%) | -22.11 | -15.26 | -22.11 |
| Daily 95% VaR (%) | -2.79 | -1.98 | -2.50 |
| Daily 95% CVaR (%) | -4.68 | -3.49 | -4.47 |
| Exit reasons | signal 17, end_of_data 1 | signal 4 | signal 21 |

## By year (2021-2025)

| | strategy return % | strategy max DD % | strategy Sharpe | asset return % | asset max DD % | asset Sharpe |
|---|---|---|---|---|---|---|
| 2021 | 49.94 | -25.51 | 1.00 | 59.79 | -53.14 | 0.98 |
| 2022 | -16.10 | -16.58 | -2.33 | -64.21 | -66.93 | -1.29 |
| 2023 | 84.42 | -20.53 | 1.69 | 155.61 | -20.00 | 2.35 |
| 2024 | 104.13 | -27.97 | 1.96 | 121.31 | -26.15 | 1.76 |
| 2025 | -3.26 | -19.93 | 0.02 | -6.33 | -32.02 | 0.05 |

Charts per period: `equity.png` (equity and drawdown vs buy-and-hold), `trades.png`, `layers.png`. Trade history: `trades.csv`; quarterly: `quarterly.csv`.
