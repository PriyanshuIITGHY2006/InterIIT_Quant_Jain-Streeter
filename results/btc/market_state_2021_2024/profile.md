# BTCUSDT: market-state behaviour profile, 2021-01-01 to 2024-12-31

States are decided each day from indicators calibrated on the data's own history (no look-ahead). The 'mean next-7d return / volatility' columns are DESCRIPTIVE (they look forward) and are never used by the strategy.

| | share of days | average spell (days) | mean next-7d return | next-7d volatility | average exposure |
|---|---|---|---|---|---|
| Storm | 0.06 | 8.00 | 0.01 | 0.58 | 0.16 |
| Downtrend | 0.36 | 29.39 | 0.00 | 0.58 | 0.04 |
| Bear rally | 0.06 | 9.20 | -0.02 | 0.58 | 0.38 |
| Calm uptrend | 0.20 | 6.22 | 0.02 | 0.48 | 1.42 |
| Volatile uptrend | 0.10 | 5.79 | 0.00 | 0.48 | 0.54 |
| Uptrend | 0.16 | 5.87 | -0.00 | 0.57 | 0.79 |
| Fading uptrend | 0.07 | 8.15 | 0.01 | 0.59 | 0.30 |

## Transitions (row = today's state, column = tomorrow's)

| | Storm | Downtrend | Bear rally | Calm uptrend | Volatile uptrend | Uptrend | Fading uptrend |
|---|---|---|---|---|---|---|---|
| Storm | 0.88 | 0.05 | 0.00 | 0.01 | 0.04 | 0.00 | 0.02 |
| Downtrend | 0.01 | 0.97 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 |
| Bear rally | 0.00 | 0.08 | 0.89 | 0.03 | 0.00 | 0.00 | 0.00 |
| Calm uptrend | 0.00 | 0.00 | 0.00 | 0.84 | 0.05 | 0.10 | 0.01 |
| Volatile uptrend | 0.02 | 0.00 | 0.00 | 0.09 | 0.83 | 0.04 | 0.01 |
| Uptrend | 0.00 | 0.00 | 0.00 | 0.12 | 0.02 | 0.83 | 0.03 |
| Fading uptrend | 0.02 | 0.04 | 0.00 | 0.00 | 0.03 | 0.04 | 0.88 |

**Latest state (2024-12-31):** Volatile uptrend; target exposure 0.34.
