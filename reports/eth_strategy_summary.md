# ETH/USDT Strategy: Calm-Trend Regime for ETH (CTR-ETH), summary

Short version. The full technical document, with ETH-specific reasoning and mathematics, is `reports/eth_strategy.md`.

**Status: final and frozen** (protocol v20 §26). It is the BTC strategy's market-state framework applied to ETH **with no parameter changed**. Every threshold is measured against ETH's own history, so the rules adapt to ETH automatically.

| Period | CTR-ETH | ETH buy-and-hold | Sharpe (vs B&H) | Max DD (vs B&H) |
|---|---|---|---|---|
| 2021–2024 | +274% | +357% | 0.90 (0.87) | −37.3% (−79.3%) |
| 2025 | **+54.9%** | −11.8% | 1.23 (0.20) | −25.0% (−60.0%) |
| **2021–2025** | **+482%** | +306% | **0.96** (0.75) | **−37.3%** (−79.3%) |
| **2026 to 4 Oct (unseen, run once)** | **+28.3%** | −9.5% | 1.30 (0.10) | −8.9% (−53.3%) |

## How it works (each daily close, executed at the next open)
1. **Direction:** share of 7 trend votes (ETH above its 20–200-day averages).
2. **Regime:** × 1.5 in calm ETH trends, × 0.6 when ETH is stormy, × 1 otherwise.
3. **Storm brake:** × 0.5 when ETH's sell-off risk is above 1.5× its own 1-year median.
4. **Squeeze warning:** × 0.75.
5. **Long-term gate:** × 0.5 while the 200-day trend is down.

Long only, maximum 1.5× equity, 0.15% per fill.

## Why the same rules suit ETH
- ETH's direction is as unpredictable as BTC's, its volatility is even more predictable (HAR R² 0.73), and trend-following pays in calm ETH trends in 4 of 4 years.
- **Rank-based thresholds are scale-invariant** (proof in the full document, §E2), so "stormy" means stormy *for ETH*.
- **ETH-specific designs were tested and failed:**
  - slow direction alone beats buy-and-hold nowhere;
  - the best ETH-specific design (E3) depended on early 2021 and lost 11% in 2025;
  - the old G-06 had a −57% drawdown.
- Using identical rules is the strongest guard against overfitting: nothing was tuned for ETH.

## Risk plan (ETH-specific)
- **Size:** at most 1.5× and only in calm trends.
- **Crash risk:** handled by the storm brake (hourly ETH sell-off volatility), the squeeze warning and the 200-day gate.
- **Joint risk with BTC:** ETH crashes with BTC on 82% of the worst days, so the two strategies should be sized as one risk position in crashes.
- **Stop-loss:** a trend-break exit, scaled down vote by vote. Average loss −2.4% of equity; largest −8.3%.
- **Risk–reward:** payoff ratio 23.4 : 1, profit factor 5.06, win rate 23.8%.
- **Known risks:**
  - calm-market crashes at 1.5× (worst day −18.6%, 7 Sep 2021);
  - a 828-day recovery after the 2021 top;
  - a weaker cold start than BTC (mean Sharpe 0.62 vs 0.74 over 11 windows).

## Robustness
- **No lookahead:** truncation tests, plus frozen-result regression tests.
- **Neighbouring settings:** keep at least 90% of the Sharpe.
- **Double costs:** Sharpe 0.91 (2021–25).
- **Daily candles only:** Sharpe 0.88.
- **It beat ETH in 7 of the 8 quarters where ETH fell.**
