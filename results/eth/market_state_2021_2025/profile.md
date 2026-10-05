# ETHUSDT: market-state behaviour profile, 2021-01-01 to 2025-12-31

States are decided each day from indicators calibrated on the data's own history (no look-ahead). The 'mean next-7d return / volatility' columns are DESCRIPTIVE (they look forward) and are never used by the strategy.

| | share of days | average spell (days) | mean next-7d return | next-7d volatility | average exposure |
|---|---|---|---|---|---|
| Storm | 0.07 | 11.00 | -0.00 | 0.79 | 0.10 |
| Downtrend | 0.34 | 26.74 | 0.01 | 0.70 | 0.04 |
| Bear rally | 0.07 | 11.33 | -0.01 | 0.72 | 0.40 |
| Calm uptrend | 0.15 | 10.11 | 0.02 | 0.64 | 1.38 |
| Volatile uptrend | 0.12 | 9.48 | -0.00 | 0.72 | 0.52 |
| Uptrend | 0.17 | 10.27 | 0.01 | 0.62 | 0.84 |
| Fading uptrend | 0.09 | 11.07 | -0.03 | 0.71 | 0.26 |

## Transitions (row = today's state, column = tomorrow's)

| | Storm | Downtrend | Bear rally | Calm uptrend | Volatile uptrend | Uptrend | Fading uptrend |
|---|---|---|---|---|---|---|---|
| Storm | 0.91 | 0.06 | 0.00 | 0.00 | 0.02 | 0.00 | 0.01 |
| Downtrend | 0.01 | 0.96 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 |
| Bear rally | 0.00 | 0.05 | 0.91 | 0.02 | 0.00 | 0.01 | 0.00 |
| Calm uptrend | 0.00 | 0.00 | 0.00 | 0.90 | 0.04 | 0.05 | 0.01 |
| Volatile uptrend | 0.01 | 0.00 | 0.00 | 0.03 | 0.89 | 0.05 | 0.01 |
| Uptrend | 0.00 | 0.00 | 0.00 | 0.05 | 0.02 | 0.90 | 0.02 |
| Fading uptrend | 0.00 | 0.05 | 0.00 | 0.01 | 0.01 | 0.02 | 0.91 |

**Latest state (2025-12-31):** Downtrend; target exposure 0.00.
