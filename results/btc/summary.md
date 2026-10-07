# BTC/USDT strategy: Calm-Trend Regime with calm-bear shorts (CTR-S), results

Logic and risk plan: `reports/btc_strategy.md`. 10,000 USDT start, 0.15% per fill, max 1.5x equity, 8%/yr on borrowed USDT, 10%/yr on borrowed coins (shorts).

## Required metrics (and extras)

| | 2021-2024 | 2025 | 2021-2025 |
|---|---|---|---|
| Gross Profit (USDT) | 49,053.33 | 293.59 | 47,963.39 |
| Net Profit (USDT) | 38,885.35 | -513.35 | 36,839.51 |
| Total Closed Trades | 31 | 6 | 36 |
| Win Rate (%) | 35.48 | 16.67 | 33.33 |
| Max Drawdown (%) | -29.56 | -20.56 | -29.56 |
| Gross Loss (USDT) | -10,167.98 | -806.94 | -11,123.88 |
| Average Winning Trade (USDT) | 4,459.39 | 293.59 | 3,996.95 |
| Average Losing Trade (USDT) | -508.40 | -161.39 | -463.49 |
| Buy-and-Hold Return (%) | 218.07 | -7.62 | 197.92 |
| Largest Losing Trade (USDT) | -3,950.76 | -613.34 | -3,950.76 |
| Largest Winning Trade (USDT) | 19,827.38 | 293.59 | 19,827.38 |
| Sharpe Ratio | 1.16 | -0.05 | 0.98 |
| Sortino Ratio | 1.93 | -0.07 | 1.60 |
| Average Holding Duration | 38 days 21:40:38.709677 | 48 days 08:00:00 | 41 days 14:40:00 |
| Maximum Holding Duration | 290 days 00:00:00 | 196 days 00:00:00 | 290 days 00:00:00 |
| Total Return (%) | 388.85 | -5.13 | 368.40 |
| Annualised Return (%) | 48.65 | -5.13 | 36.16 |
| Calmar Ratio | 1.65 | -0.25 | 1.22 |
| Quarters Beating Buy-and-Hold (%) | 56.25 | 50.00 | 55.00 |
| Long Trades | 18 | 4 | 21 |
| Short Trades | 13 | 2 | 15 |
| Max Drawdown Recovery Time | 252 days 00:00:00 | None | 252 days 00:00:00 |
| Longest Time Under Water | 496 days 00:00:00 | 223 days 00:00:00 | 496 days 00:00:00 |
| Exposure (%) | 82.55 | 79.45 | 82.04 |
| Total Fees (USDT) | 3,129.24 | 277.56 | 4,412.24 |
| Total Financing (USDT) | 816.35 | 76.52 | 1,194.16 |
| Buy-and-Hold Sharpe Ratio | 0.78 | 0.02 | 0.67 |
| Buy-and-Hold Max Drawdown (%) | -76.63 | -32.02 | -76.63 |
| Sharpe at 2x costs | 1.08 | -0.15 | 0.90 |

## Risk / reward of the closed trades

| | 2021-2024 | 2025 | 2021-2025 |
|---|---|---|---|
| Average win (% of equity) | 24.37 | 3.17 | 21.96 |
| Average loss (% of equity) | -2.53 | -1.64 | -2.19 |
| Largest loss (% of equity) | -10.58 | -6.13 | -10.58 |
| Largest win (% of equity) | 113.19 | 3.17 | 113.19 |
| Payoff ratio (avg win / avg loss) | 9.63 | 1.94 | 10.01 |
| Profit factor (gross wins / gross losses) | 4.82 | 0.36 | 4.31 |
| Expectancy per trade (% of equity) | 7.02 | -0.84 | 5.86 |
| Worst day (%) | -15.70 | -10.84 | -15.70 |
| Worst 7 days (%) | -23.75 | -14.14 | -23.75 |
| Worst 30 days (%) | -22.11 | -15.26 | -22.11 |
| Daily 95% VaR (%) | -2.92 | -1.98 | -2.59 |
| Daily 95% CVaR (%) | -4.77 | -3.49 | -4.55 |
| Exit reasons | signal 30, end_of_data 1 | signal 5, end_of_data 1 | signal 35, end_of_data 1 |

## By year (2021-2025)

| | strategy return % | strategy max DD % | strategy Sharpe | asset return % | asset max DD % | asset Sharpe |
|---|---|---|---|---|---|---|
| 2021 | 37.12 | -27.45 | 0.83 | 59.79 | -53.14 | 0.98 |
| 2022 | -1.12 | -12.71 | -0.00 | -64.21 | -66.93 | -1.29 |
| 2023 | 80.76 | -20.53 | 1.64 | 155.61 | -20.00 | 2.35 |
| 2024 | 99.64 | -29.56 | 1.90 | 121.31 | -26.15 | 1.76 |
| 2025 | -4.27 | -20.56 | -0.02 | -6.33 | -32.02 | 0.05 |

## CTR-S vs the long-only CTR, return by year (%)

| | CTR-S (final) return % | CTR-S (final) max DD % | CTR (long only) return % | CTR (long only) max DD % | BTC return % |
|---|---|---|---|---|---|
| 2021 | 37.12 | -27.45 | 49.94 | -25.51 | 59.79 |
| 2022 | -1.12 | -12.71 | -16.10 | -16.58 | -64.21 |
| 2023 | 80.76 | -20.53 | 84.42 | -20.53 | 155.61 |
| 2024 | 99.64 | -29.56 | 104.13 | -27.97 | 121.31 |
| 2025 | -4.27 | -20.56 | -3.26 | -19.93 | -6.33 |

Chart: `ctr_s_vs_ctr.png`.

Charts per period: `equity.png` (equity and drawdown vs buy-and-hold), `trades.png`, `layers.png`. Trade history: `trades.csv`; quarterly: `quarterly.csv`.
