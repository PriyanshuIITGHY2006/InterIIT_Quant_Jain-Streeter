# BTCUSDT: market-state behaviour profile, 2021-01-01 to 2025-12-31

States are decided each day from indicators calibrated on the data's own history (no look-ahead). The 'mean next-7d return / volatility' columns are DESCRIPTIVE (they look forward) and are never used by the strategy.

| | share of days | average spell (days) | mean next-7d return | next-7d volatility | average exposure |
|---|---|---|---|---|---|
| Storm | 0.04 | 6.92 | 0.01 | 0.58 | 0.15 |
| Downtrend | 0.34 | 31.45 | 0.00 | 0.56 | 0.04 |
| Bear rally | 0.05 | 9.20 | -0.02 | 0.58 | 0.38 |
| Calm uptrend | 0.20 | 6.74 | 0.01 | 0.45 | 1.42 |
| Volatile uptrend | 0.09 | 6.36 | -0.00 | 0.46 | 0.54 |
| Uptrend | 0.17 | 6.65 | 0.00 | 0.51 | 0.79 |
| Fading uptrend | 0.10 | 10.00 | 0.00 | 0.53 | 0.27 |

## Transitions (row = today's state, column = tomorrow's)

| | Storm | Downtrend | Bear rally | Calm uptrend | Volatile uptrend | Uptrend | Fading uptrend |
|---|---|---|---|---|---|---|---|
| Storm | 0.86 | 0.06 | 0.00 | 0.01 | 0.04 | 0.00 | 0.04 |
| Downtrend | 0.01 | 0.97 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 |
| Bear rally | 0.00 | 0.08 | 0.89 | 0.03 | 0.00 | 0.00 | 0.00 |
| Calm uptrend | 0.00 | 0.00 | 0.00 | 0.85 | 0.04 | 0.10 | 0.01 |
| Volatile uptrend | 0.02 | 0.00 | 0.00 | 0.08 | 0.84 | 0.04 | 0.02 |
| Uptrend | 0.00 | 0.00 | 0.00 | 0.10 | 0.02 | 0.85 | 0.03 |
| Fading uptrend | 0.02 | 0.03 | 0.00 | 0.01 | 0.02 | 0.03 | 0.90 |

**Latest state (2025-12-31):** Downtrend; target exposure 0.00.
