# BTC/USDT Strategy: Calm-Trend Regime (CTR), full technical document

Part I describes the strategy, its risk plan and results. **Part II gives the mathematical foundations:** the statistical properties of BTC returns, why each family of directional indicators fails, why the volatility-based components work, and the multiple-testing correction. A short version is `reports/btc_strategy_summary.md`.

# Part I: The strategy

**Status: final and frozen.** Selected under evaluation protocol v8 §14 (research ID *F1*) and kept unchanged after the refinement round (v10 §16). Not changed since; every later experiment is in `tries/` and was compared against it.

| | |
|---|---|
| **Market** | BTC/USDT, Binance spot, daily decisions (hourly data for the risk measures) |
| **Style** | Long-only trend following with regime-based position sizing |
| **Capital and costs** | 10,000 USDT; 0.15% fee + slippage on every fill; maximum position 1.5× equity; borrowed USDT charged 8% a year |
| **Code** | `src/strategies/btc_strategy.py` (strategy), `src/strategies/market_state.py` (market-state framework), `src/risk/btc_risk.py` (risk layers as stand-alone functions), `src/strategies/execution.py` (execution settings) |
| **Run** | `.venv/bin/python -m scripts.run_btc_strategy` → `results/btc/` (all metrics, equity, trades, charts) |
| **Behaviour profile** | `.venv/bin/python -m scripts.market_state_report BTCUSDT 2021-01-01 2025-12-31` → `results/btc/market_state_2021_2025/` |
| **Tests** | `tests/test_btc_strategy.py`, `tests/test_market_state.py` (no lookahead, bounded targets, frozen results) |

## Results at a glance

| Period | CTR return | BTC buy-and-hold | CTR Sharpe | B&H Sharpe | CTR max DD | B&H max DD |
|---|---|---|---|---|---|---|
| 2021–2024 (development) | **+373%** | +218% | **1.16** | 0.78 | **−37.5%** | −76.6% |
| 2025 | **−4.1%** | −7.6% | −0.02 | 0.02 | **−19.9%** | −32.0% |
| **2021–2025 (required 5-year backtest)** | **+358%** | +198% | **0.98** | 0.67 | **−37.5%** | −76.6% |
| **2026-01-01 → 10-04 (unseen data, strategy frozen before download)** | **+13.5%** | −2.9% | **0.86** | 0.14 | **−11.2%** | −39.5% |

Over 2021–2025 it beat buy-and-hold in 55% of quarters, and in 8 of the 9 quarters where BTC fell.

---

## 1. Why this strategy: what the data told us

Every rule comes from our own research (`notebooks/01_data_research.ipynb`, `notebooks/02_indicator_analysis.ipynb`, `notebooks/03_ml_research.ipynb`). Four facts about BTC drive the design:

1. **Direction is hard to predict, but the size of moves is not.**
   - No indicator predicted next week's direction consistently (RSI, MACD-style stretch measures, Supertrend, ADX, Heikin-Ashi, Kalman, CUSUM; machine-learning models scored AUC 0.40–0.51).
   - Volatility is forecastable out of sample (R² 0.30–0.73, every year).
2. **Trend-following pays only in calm, orderly trends.** Splitting days by volatility and trend efficiency, a 30-day momentum bet earned money in calm trends in **4 of 4 years** and roughly nothing in high-volatility regimes. Choppiness < 38.2 (a clean trend) also paid in 4 of 4 years.
3. **BTC's sell-off volatility lingers; rally volatility and one-off jumps fade.** Downside semivariance carries about 2× the forecasting weight of upside semivariance. Smooth (bipower) volatility persists while the jump part does not.
4. **The worst damage is in long bear markets.** Buy-and-hold fell −77% in 2022 and stayed under water for about 780 days. Being out of most of a bear market matters more than catching every rally.

So the strategy splits the job in two: **a simple, robust trend signal decides *whether* to be long; the market's regime decides *how much*.**

## 2. The rules

Evaluated at each daily close; orders fill at the **next day's open**.

| Step | Rule | Values |
|---|---|---|
| 1. Direction | Share of 7 trend votes: is the close above its 20, 30, 50, 75, 100, 150 and 200-day average? Each vote has a hysteresis band of 1 × daily volatility, so it doesn't flip on noise. | 0 to 1 |
| 2. Regime | **Calm trend** = volatility percentile ≤ 0.5 *and* 30-day efficiency ratio above its own expanding median, *or* Choppiness(14) < 38.2. **Stormy** = volatility percentile > 0.5. | × 1.5 calm trend, × 0.6 stormy, × 1.0 otherwise |
| 3. Storm brake | Sell-off risk forecast = √(365 · EWMA₃₀(0.5 · bipower variation + downside semivariance)), from hourly data. Brake when it exceeds 1.5 × its 1-year median. | × 0.5 |
| 4. Squeeze | Bollinger Bands (20, 2) inside the Keltner Channel (20, 1.5 ATR) | × 0.75 |
| 5. Long-term gate | Banded 200-day trend state is down | × 0.5 |

**Target exposure** = steps 1 × 2 × 3 × 4, capped at 1.5, then × step 5.

**Execution:**
- An open position is resized only when the target moves by more than 0.25 (this limits churn and costs).
- The strategy waits 5 days before re-entering after an exit.
- No orders are placed on exchange-outage bars.

**Parameters:** all are round or conventional values fixed before testing (the 20–200-day averages, the 0.5 median split, Choppiness 38.2, 1.5× leverage, the 30-day EWMA). None was optimised; neighbouring values were checked instead (§7).

![decision layers](../results/btc/2021-2025/layers.png)

## 3. The market-state framework: how CTR reads any dataset

The rules are organised as a framework that first **names what the market is doing**, then acts (`src/strategies/market_state.py`).
- Every threshold is relative to the dataset's own history: the volatility percentile within the trailing year, the efficiency ratio against its expanding median, the risk forecast against its 1-year median.
- Averages warm up adaptively, using all available bars until the full window exists.
- So the same code works unchanged on new or hidden data from a cold start, and with daily candles only (§7).

| State (priority order) | Definition | 2021–25 share | Average spell | CTR exposure |
|---|---|---|---|---|
| Storm | sell-off risk forecast > 1.5 × its 1-year median | 4% | 7 days | 0.15 |
| Downtrend | 200-day gate down, fewer than half the trend votes | 34% | 31 days | 0.04 |
| Bear rally | 200-day gate down, at least half the votes up | 5% | 9 days | 0.38 |
| **Calm uptrend** | gate up, votes up, calm and orderly | 20% | 7 days | **1.42** |
| Volatile uptrend | gate up, votes up, stormy | 9% | 6 days | 0.54 |
| Uptrend | gate up, votes up, neither | 17% | 7 days | 0.79 |
| Fading uptrend | gate up, fewer than half the votes | 10% | 10 days | 0.27 |

- **States are persistent:** a state stays the same the next day 83–97% of the time.
- **Calm uptrends were followed by the best weeks at the lowest volatility.** This is descriptive (it looks ahead) and is never used by the rules, but it is exactly where CTR is largest.

![market states](../results/btc/market_state_2021_2025/states.png)

## 4. Why each component is there, and what was rejected

| Component | Evidence for it | What happens without it |
|---|---|---|
| 7 averaged trend votes | A single lookback is fragile: 30-day momentum gave Sharpe 1.08, but its 20- and 45-day neighbours gave 0.77 and 0.68 (stage 13). The vote share changes little across lookbacks. | Whipsaw trades: 50 trades under 30 days lost 7,900 USDT in the single-lookback baseline |
| Calm-trend leverage 1.5× | Trend payoff is positive in calm trends in 4/4 years. The 18.5% of days at more than 1× earned most of the return. | Long-term votes alone: Sharpe 0.96, +252% (stage 14) |
| Stormy size 0.6× | Momentum payoff ≈ 0 or negative in high-volatility regimes | Entries in stormy markets lost 3,700 USDT net (stage 13 trade analysis) |
| Downside-weighted storm brake | Sell-off volatility persists about 2× more (notebook 02 §3) | A brake on all volatility would also fire in rallies |
| Squeeze warning | Volatility rises about 10–14% after a squeeze, direction random (notebook 02 §4) | Removed in a test, Sharpe fell from 1.13 to 1.04 (stage 10b, B6 vs B7) |
| 200-day soft gate | 2022 bear-market rallies were the main loss of the ungated design (−51% max drawdown, stage 11) | The gate cut 2022's loss from −34% to −16% |

**Tested and rejected, all pre-registered in `docs/evaluation_protocol.md` and recorded in `tries/`:**

| Idea | Result | Stage |
|---|---|---|
| Fixed trailing stop at 3 × ATR | Fired 37 times; Sharpe 1.16 → 0.71, return +373% → +125% | 11 (F2) |
| No leverage after a 15% drawdown | Lower Sharpe (1.05), same max drawdown | 11 (F3) |
| Smoother calm-trend label; downside-only brake | Sharpe +0.01 / +0.02, within noise; failed the cold-start gate | 12 (H1, H3) |
| Leverage on full trend agreement | Worse (Sharpe 1.13, deeper drawdown) | 12 (H2) |
| No leverage when far above the 200-day average, or on volume surges | Dropped *before* testing: those leveraged days earned *more* | 12 |
| Short-term dip trades in an uptrend (rule and ML) | Lost money after costs: −8.2% (rule), −16.5% (ML) vs B&H +102.5%, 2022–24 | 15 |
| ML / RL leverage control (quantile gradient boosting, HMM, contextual bandit) | ML forecasts no better than the simple HAR model; no skill beyond a placebo | 16 |
| ML direction prediction, triple-barrier filter, Q-learning agents | AUC ≤ 0.51; a Q-learning agent lost about 79% | ML research, notebook 03 |
| Previous final K-01 | Sharpe 1.156 (tie), +289%, max DD −33%, exactly 50% of quarters beating B&H | 8 / 11 |

## 5. Risk management plan (BTC-specific)

### 5.1 How position size is controlled
- **At most 1.5× equity, and only in calm trends.** On stormy days at most 0.6×; in a slow downtrend at most 0.3–0.75×.
- **Sell-off volatility cuts size faster than rally volatility** (the downside-weighted storm brake). This is a BTC-specific choice from the semivariance research.
- **The squeeze warning** shrinks size before an expected volatility expansion.
- **The soft gate** halves everything while the 200-day trend is down.

### 5.2 Stop-loss rules
- **The exit is a trend-break stop.** The position is scaled down vote by vote as price falls through the 20–200-day averages, and closed when all votes are down.
- **Measured effect, 2021–2025 (21 trades):**
  - average loss −2.0% of equity;
  - largest loss −10.6% (July 2024 entry, closed in the 5 August 2024 crash);
  - only 1 trade lost more than 6% of equity.
- **Why there is no fixed price stop:** it was tested and destroyed returns (§4). On daily BTC a price stop mostly sells dips that recover, because jumps fade.
- **Gap risk** is modelled: fills happen at the next open, and stops fill through gaps.

### 5.3 Risk–reward (measured on equity)
| | 2021–2024 | 2021–2025 |
|---|---|---|
| Win rate | 27.8% | 28.6% |
| Average win / average loss (% of equity) | +48.4% / −2.2% | +39.6% / −2.0% |
| **Payoff ratio (reward : risk)** | **21.6 : 1** | **19.7 : 1** |
| Profit factor | 6.86 | 6.25 |
| Break-even win rate at this payoff | 4.4% | 4.8% |

This is the classic trend-following profile: many small losses cut quickly, and a few large wins that run for months (the longest lasted 290 days).

### 5.4 Known risks
- **Shocks from calm markets** hit while the strategy holds 1.5×. The worst days were −15.7% (7 Sep 2021) and −10.8% (10 Oct 2025). The worst 7 days: −23.8%. Daily 95% VaR −2.5%, CVaR −4.5%.
- **Slow recovery after a top:** the deepest drawdown (−37.5%, Nov 2021 → Dec 2022) took 723 days to recover.
- **Late entries after long downtrends:** it lags strong bull quarters (2021 Q1 +52% vs +103%; 2026 Q3 +15.7% vs +42.6%).

## 6. Results in detail (2021–2025, the required backtest)

**Required metrics:**

| Metric | Value | | Metric | Value |
|---|---|---|---|---|
| Gross Profit | 42,639.75 USDT | | Buy-and-Hold Return | +197.92% |
| Net Profit | 35,812.22 USDT | | Largest Losing Trade | −3,739.80 USDT |
| Total Closed Trades | 21 | | Largest Winning Trade | 18,768.61 USDT |
| Win Rate | 28.57% | | Sharpe Ratio | 0.98 |
| Max Drawdown | −37.53% | | Sortino Ratio | 1.61 |
| Gross Loss | −6,827.53 USDT | | Average Holding Duration | 65.9 days |
| Average Winning Trade | 7,106.63 USDT | | Maximum Holding Duration | 290 days |
| Average Losing Trade | −455.17 USDT | | | |

Extras: total return +358.1%, annualised +35.6%, Calmar 0.95, exposure 76%, fees 3,834 USDT, financing 932 USDT. Per-period tables, trade history, fills, equity and quarterly files are in `results/btc/<period>/`.

| Year | CTR | BTC | CTR max DD | BTC max DD |
|---|---|---|---|---|
| 2021 | +49.9% | +59.8% | −25.5% | −53.1% |
| 2022 | −16.1% | −64.2% | −16.6% | −66.9% |
| 2023 | +84.4% | +155.6% | −20.5% | −20.0% |
| 2024 | +104.1% | +121.3% | −28.0% | −26.2% |
| 2025 | −3.3% | −6.3% | −19.9% | −32.0% |

![equity](../results/btc/2021-2025/equity.png)

**The edge is defence plus leverage in calm trends:**
- it lost 16% in 2022 against −64%;
- it kept most of the bull years;
- it ended about 1.5× buy-and-hold's final equity with half the drawdown.

## 7. Robustness
- **No lookahead:**
  - signals are identical when future data is removed (truncation tests);
  - the backtest matches when cut at any point;
  - a regression test locks the frozen 2021–2024 results (18 trades, +373.15%, Sharpe 1.159).
- **Neighbouring settings** (2021–24) keep at least 96% of the Sharpe: high-vol size 0.5 / 0.7, volatility threshold 0.4 / 0.6, storm brake 1.25 / 1.75, gate floor 0.3 / 0.7, gate lookback 150 / 250.
- **Double costs** (0.30% per fill): Sharpe 1.09 on 2021–24 (B&H 0.78).
- **Cold start** (started with *no history* in each quarter 2021Q2–2023Q4, run to end-2024):
  - mean Sharpe 1.56;
  - max drawdown between −27% and −37%;
  - beat buy-and-hold's Sharpe in 8 of 11 windows (the misses are pure bull-market windows starting at the 2022 bottom).
- **Daily candles only:** with hourly measures approximated from daily OHLC, 2021–24 Sharpe is 1.17 (vs 1.16). The strategy does not need hourly data.
- **New data (2026, run once, protocol §21):**

  | 2026 quarter | CTR | BTC |
  |---|---|---|
  | Q1 | −3.2% | −22.1% |
  | Q2 | −1.6% | −14.2% |
  | Q3 | +15.7% | +42.6% |

  Year to 4 Oct: +13.5% vs −2.9%, max DD −11.2% vs −39.5%. Same pattern as every earlier year: small losses in falls, partial upside in rallies. Results in `tries/results/stage17_test_2026/`.

## 8. Why we trust it, and its limits
- **Many trials:** about 1,000 BTC backtests have been logged in this project, so some out-performance could be luck. The main defences are consistency (every year positive or better than BTC), stable neighbours, the cold-start runs and the 2026 result on genuinely new data.
- **One-sample caveat:** the 2026 result is one 9-month sample with 4 trades.
- **Design limits:** it is long-only (no gain from falls), it lags early rallies, and calm-market crashes hit at 1.5×.

## 9. How it was developed (honest history)
1. **Stages 1–9:** baselines, trend ensembles, regime gate, chop filter, leading to K-01, frozen in protocol v6.
   - 2024 failed as a validation year for the earlier designs and was then treated as training data (v4).
   - 2025 was used once, as K-01's test (−17.5% vs −7.6%).
2. **Indicator research (notebook 02, 25+ indicators):** risk and regime indicators are reliable; direction indicators are not.
3. **Stages 10–10b:** first regime-sizing designs (B7: Sharpe 1.13, +375%, but max DD −51%).
   - 2025 had been used to test earlier candidate strategies before CTR was selected; the unseen-data test of CTR is 2026 (§7).
4. **Stage 11:** the 2022 bear rallies were diagnosed as B7's weakness, and K-01's soft gate was added. That design is **CTR (F1)**.
   - It tied K-01 on Sharpe (1.1588 vs 1.1556); the protocol gate had quoted a rounded 1.16.
   - The team chose CTR (protocol v8a) for +373% vs +289% and 56% vs 50% of quarters beating buy-and-hold, and accepted a deeper drawdown.
5. **Stage 12:** the market-state framework; refinements H1–H4 did not pass the cold-start gate, so CTR was unchanged.
6. **Stages 13–17:** reliable-indicator baseline, long-term direction study, short-term layer, ML risk engine. None beat CTR. Then the one-time 2026 test.

All of it is documented in `docs/evaluation_protocol.md` (every rule written before its run), `docs/project_history.md`, and `tries/README.md`.

---

# Part II: Mathematical foundations

Every number below was measured on our data (2021–2024 unless stated), in `notebooks/01–03`, `reports/indicator_analysis_report.md` and the experiment reports. The derivations are standard results; references are listed at the end.

## M1. Notation, information sets and causality

- Let $P_t$ be the BTC close of day $t$ and $r_t = \ln P_t - \ln P_{t-1}$ the log return.
- Let $\mathcal{F}_t = \sigma(P_s, H_s, L_s, V_s, \ldots : s \le t)$ be the **filtration** generated by everything observable up to the close of day $t$.
- A strategy is a position process $w_t$ that must be **$\mathcal{F}_t$-adapted** (measurable with respect to $\mathcal{F}_t$). It is executed at the next open, so the portfolio return is

$$
R^{\text{strat}}_{t+1} = w_t \, r^{\text{open}}_{t+1} - c\,|w_t - w_{t-1}| - b\,(w_t - 1)^+, \qquad c = 0.0015 ,
$$

where $b$ is the daily borrowing rate on leverage above 1. Adaptedness is exactly the "no lookahead" property. The truncation test checks it empirically: for any cut-off $T$, the signal computed on $\mathcal{F}_T$ alone must equal the signal computed on the full sample up to $T$.

## M2. The statistical nature of BTC returns

Write the return as a location–scale process

$$
r_{t+1} = \mu_t + \sigma_t\, \varepsilon_{t+1}, \qquad \mathbb{E}[\varepsilon_{t+1}\mid\mathcal{F}_t]=0,\ \mathrm{Var}(\varepsilon_{t+1}\mid\mathcal{F}_t)=1 .
$$

Three stylised facts, all measured on our data, determine what can and cannot be traded.

**(a) Heavy tails.**
- Hourly excess kurtosis is 15.7 (BTC).
- The Hill estimator of the tail index, $\hat\alpha = \big(\tfrac1k\sum_{i=1}^{k}\ln X_{(i)} - \ln X_{(k)}\big)^{-1}$, gives $\hat\alpha \approx 2.7$–$3.7$ for hourly returns, and a fitted Student-$t$ for daily returns has $\nu \approx 2.5$ degrees of freedom.
- Since $\mathbb{E}|r|^p < \infty$ only for $p < \alpha$, the **fourth moment is not finite**, so any statistic built on kurtosis or on squared errors of extreme moves is unstable.

**(b) Volatility clustering with long memory.**
- The autocorrelation of $\ln RV_t$ is 0.63 at lag 1 and still 0.26 at lag 90.
- $\sigma_t$ is therefore highly predictable.

**(c) Approximate martingale-difference behaviour of the mean.** The **variance ratio**

$$
VR(q) = \frac{\mathrm{Var}\!\big(\sum_{i=1}^{q} r_{t+i}\big)}{q\,\mathrm{Var}(r_t)} = 1 + 2\sum_{k=1}^{q-1}\Big(1-\frac{k}{q}\Big)\rho_k
$$

is a weighted sum of autocorrelations $\rho_k$. With the heteroskedasticity-robust Lo–MacKinlay statistic, our daily estimates are $VR(2)=0.97$, $VR(5)=1.00$, $VR(10)=1.01$ and $VR(20)=1.02$, all with $|z|<1$.

Hence $\rho_k \approx 0$, and to first order

$$
\mathbb{E}[r_{t+1}\mid\mathcal{F}_t] \approx \mu \quad (\text{a constant}) .
$$

**The central consequence.** The conditional **second** moment is predictable; the conditional **first** moment is (almost) not. Every successful component of CTR uses $\sigma_t$; every failed indicator tried to predict $\mu_t$.

## M3. Why directional indicators fail

### M3.1 The information coefficient and the cost hurdle
- Let $s_t$ be any $\mathcal{F}_t$-measurable signal and $IC = \mathrm{corr}(s_t, r_{t+1:t+h})$ its information coefficient.
- If $(s, r)$ is approximately jointly Gaussian with $\mathbb{E}[r]=0$, the expected return of the sign bet $w_t = \mathrm{sign}(s_t)$ is

$$
\mathbb{E}[\mathrm{sign}(s)\,r] = \mathbb{E}\big[\mathrm{sign}(s)\,\mathbb{E}[r\mid s]\big] = \rho\,\frac{\sigma_r}{\sigma_s}\,\mathbb{E}|s| = \rho\,\sigma_r\sqrt{2/\pi}.
$$

**Our strongest short-horizon effect** (the 4-hour return predicting the next 4 hours) has $\rho \approx -0.07$ ($t=-11$, same sign in every year).
- With $\sigma_{4h} = 0.665/\sqrt{2190} \approx 1.42\%$, the gross edge per bet is about **7.9 bps**, against **30 bps** of round-trip costs. The measured extreme-decile spread (13–15 bps) confirms the order of magnitude.
- The effect is real in the statistical sense and unprofitable in the economic sense.

The **fundamental law of active management** gives the same verdict at portfolio level: $IR \approx IC\sqrt{BR}$.
- For a weekly signal, the breadth is $BR \approx 52$ independent bets a year.
- $|IC| \le 0.05$ then gives $IR \le 0.36$ *before* costs, and turnover costs remove most of it.

### M3.2 Non-stationarity: an IC that changes sign
Treat each year's IC as a draw $IC_y = \bar{\kappa} + u_y$ with $u_y \sim (0, \tau^2)$.
- For RSI, stochastic RSI, %B, z-score, ADX, DI spread, Supertrend, EMA ribbon, Aroon, Heikin-Ashi, Kalman slope and CUSUM, the yearly ICs change sign between years (e.g. Supertrend $+0.11, -0.11, -0.04, -0.12$).
- So $\tau \gg |\bar\kappa|$: the random-effect variance dominates the mean, and a signal fitted in one regime is a coin flip in the next.
- The same instability shows up in the weekly variance ratio by year: $VR(168h) = 0.83$ (2021, mean-reverting), $1.05$ (2022), $1.34$ (2023, trending). No fixed directional rule can be right in all three.

### M3.3 Oscillators: RSI, stochastic RSI, Bollinger %B, z-scores
- RSI is a bounded monotone transform of a ratio of Wilder averages:

$$
RSI_t = 100 - \frac{100}{1 + RS_t},\qquad RS_t = \frac{\mathrm{EWMA}_{1/n}(r^+)_t}{\mathrm{EWMA}_{1/n}(r^-)_t}.
$$

- It is $\mathcal{F}_t$-measurable. Under the martingale-difference property, $\mathbb{E}[r_{t+1}\mid RSI_t] = \mathbb{E}[\,\mathbb{E}[r_{t+1}\mid\mathcal{F}_t]\mid RSI_t] \approx \mu$, independent of the RSI level.
- "Overbought/oversold" trading presumes **negative serial dependence**, $\rho_k < 0$, at the oscillator's horizon. With $VR \approx 1$ there is none on average.
- In trending regimes ($VR > 1$) the sign even reverses, which is exactly what we measured: RSI > 70 was followed by *gains* in the 2023–24 bull years and losses in 2022.

### M3.4 ADX: a sign-invariant statistic
$DX_t = 100\,\frac{|DI^+_t - DI^-_t|}{DI^+_t + DI^-_t}$, and ADX is its Wilder average.
- **No direction by construction.** Under the reflection of the price path (up-moves ↔ down-moves), $DI^+ \leftrightarrow DI^-$ and $DX$ is unchanged. ADX is an **even function of direction**, so it cannot carry directional information.
- **Built-in lag.** Wilder smoothing is an EWMA with $\alpha = 1/14$, whose mean lag is $(1-\alpha)/\alpha = 13$ bars. ADX applies it twice (to the DIs, then to DX), so its effective delay is about 26 bars. It reports trend magnitude **after** the move, which matches its positive link with *past* volatility and zero link with future trend profit.

### M3.5 Moving-average crossovers, Supertrend, EMA ribbon: linear filters with delay
An $n$-day SMA is a finite impulse response filter with symmetric weights. Its **group delay** is

$$
\tau_g = \frac{n-1}{2}\ \text{days} \qquad (99.5 \text{ days for the 200-day average}).
$$

To leading order, a linear trend rule holds $w_t = \sum_{k\ge0} a_k\, r_{t-k}$, so its expected P&L is a **weighted sum of autocovariances**:

$$
\mathbb{E}[w_t\, r_{t+1}] = \sum_{k\ge0} a_k\, \gamma(k+1).
$$

This is the standard decomposition of trend-following returns.
- With $\gamma(k) \approx 0$ the expected P&L is about zero, while every sign change of $w$ costs $2c$.
- Fast filters change sign more often: the single 30-day rule made 59 trades in 2021–24, while the 100–250-day vote share made 9.
- That is why the fast rule lost 7,900 USDT on trades shorter than 30 days, and why slow filters only pay through **rare, persistent** autocorrelation episodes (the multi-month 2023–24 trends).

### M3.6 Heikin-Ashi candles: an exponential filter in disguise
- With $HA^c_t = (O_t+H_t+L_t+C_t)/4$ and $HA^o_t = \tfrac12(HA^o_{t-1}+HA^c_{t-1})$, unrolling the recursion gives

$$
HA^o_t = \sum_{j\ge1} 2^{-j}\, HA^c_{t-j},
$$

an EWMA with $\alpha = 1/2$ of the *lagged* typical price.
- The candle colour $\mathrm{sign}(HA^c_t - HA^o_t)$ is therefore the sign of a very short momentum filter, so it inherits M3.5's zero expected P&L. It is causal (allowed) but uninformative.

### M3.7 The Kalman filter: an EWMA by another name
For the local-level model $x_t = \ell_t + \epsilon_t$ ($\mathrm{Var}=R$), $\ell_t = \ell_{t-1} + \eta_t$ ($\mathrm{Var}=Q$):
- The prior variance converges to the solution of the **algebraic Riccati equation**

$$
P = \frac{Q + \sqrt{Q^2 + 4QR}}{2}, \qquad K = \frac{P}{P+R}.
$$

- The filtered level is then $\hat\ell_t = \hat\ell_{t-1} + K(x_t - \hat\ell_{t-1})$, an EWMA with $\alpha = K$.
- For our $Q/R = 0.01$: $K = 0.0951$, an EWMA span of $2/K - 1 \approx 20$ days.
- The "optimal state estimate" is a 20-day exponential moving average, and its slope carries no more directional information than any other trend filter.

### M3.8 CUSUM change detection: optimality assumptions violated
Page's CUSUM, $S^+_t = \max(0, S^+_{t-1} + d_t - k)$, is optimal (Lorden; Moustakides) for detecting a shift between **known** densities of **i.i.d.** observations. Both conditions fail here:
- **Not i.i.d.:** $d_t = \ln P_t - \hat\ell_t$ is an EWMA residual, autocorrelated with coefficient about $1-K \approx 0.9$.
- **No meaningful shift to detect:** the mean shift is negligible relative to $\sigma$ (M2c).

The average run lengths therefore have no guaranteed meaning, and the bull/bear labels flip sign in predictive value year to year (ICs $+0.14, -0.11, +0.03, -0.08$).

### M3.9 The Hurst exponent: small-sample bias, not market memory
The rescaled-range estimator regresses $\ln \mathbb{E}[R/S]_n$ on $\ln n$. For **independent** data the expected value is not $c\,n^{1/2}$ but (Anis–Lloyd)

$$
\mathbb{E}[R/S]_n = \frac{n-\tfrac12}{n}\,\frac{\Gamma\!\big(\tfrac{n-1}{2}\big)}{\sqrt{\pi}\,\Gamma\!\big(\tfrac{n}{2}\big)} \sum_{i=1}^{n-1}\sqrt{\frac{n-i}{i}} .
$$

- Over window sizes 8–64 (those used in our 128-day estimator), this implies a slope of **0.617 for pure noise**.
- Our measured $\hat H = 0.589$ on BTC is statistically indistinguishable from the $0.594$ obtained on **randomly shuffled** BTC returns.
- The apparent "persistence" is estimator bias, so the "trade when H > 0.5" filter is a constant.

### M3.10 Markov switching and the HMM: classifiers of variance, not of mean
The forward (filtered) recursion is

$$
\alpha_t(j) \propto f_j(y_t)\sum_i \alpha_{t-1}(i)\,\Pi_{ij},
$$

and the one-step predictive mean is

$$
\mathbb{E}[r_{t+1}\mid\mathcal{F}_t] = \sum_j \Big(\sum_i \alpha_t(i)\Pi_{ij}\Big)\mu_j .
$$

- **The states differ in variance, not in mean.** Our fitted states have $\mu_j \approx 0.000$ and $0.001$ per day, but log-volatility levels corresponding to about 26% and 66% annualised.
- So the predictive mean is about zero whatever the filtered probabilities are. The model is an excellent **volatility** classifier (next-week vol 0.59 vs 0.47 across its states) and contains no first-moment information.
- Persistence $\Pi_{11}=0.83$, $\Pi_{22}=0.90$ (expected durations $1/(1-\Pi_{ii}) \approx 6$ and 10 days) matches the persistence of our market states.

### M3.11 PCA + K-means under heavy tails: degenerate clusters
Lloyd's algorithm minimises $\sum_i \lVert x_i - c_{k(i)}\rVert^2$.
- With power-law features ($\alpha \approx 3$), the second moment is dominated by a handful of extreme observations, so new centroids are placed to absorb the tails.
- The bulk of the distribution collapses into one cluster: 90.5% (BTC) and 93.5% (ETH) of days.
- The clustering partitions *outliers versus everything else* and does not discover regimes.

### M3.12 Short-term trading: the break-even hit rate
- A trade with symmetric take-profit and stop at $\pm k\sigma$ and round-trip cost $c$ has expected value

$$
\mathbb{E}[\text{PnL}] = p\,k\sigma - (1-p)\,k\sigma - c = (2p-1)k\sigma - c \quad\Rightarrow\quad p^* = \frac12 + \frac{c}{2k\sigma}.
$$

- With $k=1$, daily $\sigma \approx 3\%$ and $c = 0.30\%$, the break-even hit rate is $p^* = 0.55$.
- Our dip trades hit the target first in 24 of 49 decided cases ($\hat p = 0.49$), so they **must** lose, and they did (−8.2% out of sample).
- The ML filter would have needed to lift $p$ by 6 points, which requires an AUC far above the 0.535 achieved.

### M3.13 Machine learning: effective sample size and the Bayes-error floor
- Labels over $h$-day horizons overlap, so the **effective number of independent observations** is $n_{\text{eff}} \approx T/h$. Two years of daily data with $h=7$ gives $n_{\text{eff}} \approx 100$.
- The Hanley–McNeil standard error of an AUC near 0.5 is then

$$
SE(\widehat{AUC}) = \sqrt{\frac{A(1-A) + (n_1-1)(Q_1-A^2) + (n_0-1)(Q_2-A^2)}{n_1 n_0}} \approx 0.058, \quad Q_1=\frac{A}{2-A},\ Q_2=\frac{2A^2}{1+A}.
$$

- So any AUC inside about $0.5 \pm 0.11$ is noise. Our daily direction models (0.40–0.51) all sit in that band.
- The hourly model (0.535, 95% interval 0.496–0.577) sits at its edge, and the shuffled-label **placebo** reached 0.512–0.52.
- **Bias–variance view:** when the signal-to-noise ratio is this low, the irreducible (Bayes) error dominates. Extra model capacity only adds variance, which is why gradient boosting *underperformed* the linear HAR model for volatility (Diebold–Mariano test, $p=0.005$).

### M3.14 Reinforcement learning: sample complexity and a non-Markov environment
- Even in the most favourable setting (a generative model of the environment), learning an $\varepsilon$-optimal policy needs on the order of

$$
\tilde O\!\left(\frac{|S|\,|A|}{(1-\gamma)^3\,\varepsilon^2}\right)
$$

samples.
- With $|S||A| = 256$ and $\gamma = 0.95$, this is $256 \times 8000 / \varepsilon^2 \approx 2\times10^6/\varepsilon^2$ transitions, against 365 per year of data.
- Q-learning's convergence theorem also needs every state–action pair visited infinitely often and **stationary** transition probabilities. A market whose dynamics change by regime (M3.2) violates both.
- The agent memorised one bull year and held leverage into the 2022 crash (−79% across all seeds).

## M4. Why the volatility side works

### M4.1 Realised measures: quadratic variation, jumps and semivariance
For a jump-diffusion $d\ln P_t = \mu_t\,dt + \sigma_t\,dW_t + dJ_t$, the sum of squared intraday returns converges to the **quadratic variation**:

$$
RV_t = \sum_{i=1}^{M} r_{t,i}^2 \underset{M\to\infty}{\longrightarrow} \int_{t-1}^{t}\sigma_s^2\,ds + \sum_{t-1<s\le t} (\Delta J_s)^2 .
$$

The **bipower variation**, with $\mu_1 = \mathbb{E}|Z| = \sqrt{2/\pi}$,

$$
BV_t = \mu_1^{-2}\sum_{i=2}^{M} |r_{t,i}|\,|r_{t,i-1}| \;\to\; \int_{t-1}^{t}\sigma_s^2\,ds ,
$$

converges to the **integrated variance alone** (Barndorff-Nielsen & Shephard), so $RV - BV$ isolates the jump component.

The **realised semivariances** $RS^{\pm}_t = \sum_i r_{t,i}^2\,\mathbf{1}\{r_{t,i} \gtrless 0\}$ split $RV$ by sign. Our forecasting regressions give:

| Component | Coefficient on next week's variance |
|---|---|
| smooth (bipower) | 0.58 |
| jump | 0.08 |
| downside semivariance | 0.45 |
| upside semivariance | 0.21 |

Smooth risk persists and jumps fade; **bad** volatility persists about twice as much as good. This is the formal basis of the storm brake's forecast $\sqrt{365\cdot\mathrm{EWMA}_{30}(0.5\,BV + RS^-)}$.

### M4.2 Range-based estimators
- Parkinson's estimator $\hat\sigma^2 = (\ln H/L)^2 / (4\ln 2)$ uses the daily range. For a driftless Brownian motion its variance is about one fifth of that of the squared close-to-close return.
- Empirically, its correlation with next-day realised variance is 0.58, against 0.38 for the squared daily return and 0.62 for hourly RV.
- This is why CTR's volatility percentile uses Parkinson volatility, and why the daily-candle fallback costs almost nothing (Sharpe 1.17 vs 1.16).

### M4.3 The HAR model: a volatility cascade
Corsi's heterogeneous autoregressive model approximates long memory with three horizons:

$$
\ln RV_{t+1} = \beta_0 + \beta_d \ln RV^{(1)}_t + \beta_w \ln RV^{(5\text{–}7)}_t + \beta_m \ln RV^{(22\text{–}30)}_t + u_{t+1}.
$$

- Fitted on 2021–22, the coefficients were $\hat\beta_d=0.29$, $\hat\beta_w=0.51$, $\hat\beta_m=0.13$. The weekly component dominates, the signature of a market populated by traders with different horizons.
- Out of sample (2023), $R^2 = 0.60$ for BTC, with 34% lower error than a random-walk forecast.
- This predictability of $\sigma_{t+1}$ is what every sizing layer exploits.

### M4.4 Proposition: volatility-managed exposure raises the Sharpe ratio
**Setting.** Assume $r_{t+1} = \mu + \sigma_t\varepsilon_{t+1}$, with $\sigma_t$ known at $t$ and $\varepsilon$ i.i.d. with mean 0 and variance 1, independent of $\sigma_t$.

**Constant exposure.** The Sharpe ratio is $SR_0 = \mu/\sqrt{\mathbb{E}[\sigma_t^2]}$.

**Managed exposure.** For $w_t = c/\sigma_t$:

$$
\mathbb{E}[w_t r_{t+1}] = c\,\mu\,\mathbb{E}[\sigma_t^{-1}],\qquad
\mathrm{Var}(w_t r_{t+1}) = c^2\big(1 + \mu^2\mathrm{Var}(\sigma_t^{-1})\big).
$$

**Result.** For daily data $\mu^2 \mathrm{Var}(\sigma^{-1}) \approx 0$. Applying **Jensen's inequality** twice (convexity of $x\mapsto 1/x$, concavity of $\sqrt{\cdot}$):

$$
SR_{\text{managed}} \approx \mu\,\mathbb{E}[\sigma_t^{-1}] \;\ge\; \frac{\mu}{\mathbb{E}[\sigma_t]} \;\ge\; \frac{\mu}{\sqrt{\mathbb{E}[\sigma_t^2]}} = SR_0 .
$$

**Condition.** The proof requires $\mu$ to be roughly independent of $\sigma_t$. Our regime tables confirm this for BTC: mean returns do not differ across volatility terciles, all $|t| < 1.5$.

Our ablation measured the gain directly: the volatility layer moved Sharpe from 0.99 to 1.06 and cut the maximum drawdown from −47% to −38%.

### M4.5 Kelly growth and the calm-trend leverage cap
- The growth-optimal (Kelly) exposure under log utility is $f^*_t = \mu_t/\sigma_t^2$.
- In calm, orderly trends, both terms move favourably: the research shows positive trend payoff ($\mu_t > 0$) in 4 of 4 years, and $\sigma_t$ is below its median.
- So $f^*$ is largest exactly in the calm-trend state. CTR caps exposure at 1.5×, a fractional-Kelly safeguard against estimation error in $\mu_t$, which (M2c) is the least reliable quantity in the system.

### M4.6 Volatility drag and the arithmetic of drawdowns
Geometric growth satisfies $g \approx \mu - \tfrac12\sigma^2$.
- At BTC's 65% annual volatility the drag is about 21% a year. Halving exposure in storms reduces the drag on those days by three quarters.
- Recovering from a loss $L$ requires a gain $L/(1-L)$. Buy-and-hold's −76.6% drawdown needed **+327%** to recover, CTR's −37.5% only **+60%**.
- This asymmetry, not superior prediction, is why CTR ended with about 1.5× buy-and-hold's final equity while capturing less of each bull market.

### M4.7 Trend-quality measures and their random-walk baselines
- **Efficiency ratio** $ER_n = |P_t - P_{t-n}| / \sum_{i=1}^{n}|\Delta P_{t-i+1}|$. For a driftless Gaussian walk, $\mathbb{E}|S_n| = \sigma\sqrt{2n/\pi}$ and $\mathbb{E}\sum|\Delta P| = n\sigma\sqrt{2/\pi}$, so

$$
\mathbb{E}[ER_n] \approx \frac{1}{\sqrt n} = 0.183 \quad (n=30).
$$

  Simulation gives 0.183–0.187; BTC averages 0.213. The market is close to a random walk on average, and only the days well above that baseline (our "efficient" condition) carry trend.
- **Choppiness index** $CI_n = 100\,\log_{10}\!\big(\sum TR / (\max H - \min L)\big)/\log_{10} n$. Path length scales like $n$ and range like $\sqrt n$, so $CI_n \to 50 + O(1/\log n)$ for a random walk. A simulation with hourly-built candles gives 47.2; **BTC averages 49.7**.
- **The consequence for CTR:** choppiness is BTC's normal state, and $CI < 38.2$ marks paths markedly straighter than chance (14% of days). That is exactly where trend payoff was positive in 4 of 4 years.

### M4.8 The 7-vote ensemble: variance reduction and turnover
- If $K$ signals have common variance $\sigma^2$ and pairwise correlation $\rho$, their average has variance $\sigma^2\big(\rho + (1-\rho)/K\big)$. For $K=7$ and $\rho\approx0.7$ that is 74% of a single signal's.
- More importantly, the vote share moves in steps of $1/7$, so the expected turnover $\mathbb{E}|\Delta w_t|$, and with it the cost $c\,\mathbb{E}|\Delta w_t|$, is a fraction of a binary rule's.
- **Mixing horizons:** the votes combine group delays from 9.5 to 99.5 days (M3.5), so the position reacts partly early and partly late, instead of fully at one arbitrary lag. This is why the result is insensitive to the exact lookbacks while a single 30-day rule is not (Sharpe 1.08 at 30 days vs 0.77 / 0.68 at 20 / 45 days).

## M5. Multiple testing: how much of the result could be luck?

If $N$ independent zero-skill strategies are tested over $T$ years, the expected maximum Sharpe ratio is (Bailey & López de Prado)

$$
\mathbb{E}\big[\max_{i\le N} \widehat{SR}_i\big] \approx \sqrt{\tfrac{1}{T}}\Big[(1-\gamma)\,\Phi^{-1}\!\big(1-\tfrac1N\big) + \gamma\,\Phi^{-1}\!\big(1-\tfrac{1}{Ne}\big)\Big], \qquad \gamma \approx 0.5772 .
$$

For $T=4$:

| Independent trials $N$ | Expected best Sharpe by luck |
|---|---|
| 10 | 0.79 |
| 100 | 1.27 |
| 1,000 | 1.63 |

**Honest reading.**
- About 1,000 BTC backtests were logged. Treated as independent, they could produce a Sharpe of 1.16 by chance.
- They are not independent: they are small variations of about a dozen design families (neighbour checks, cost stresses, ablations of the same rules). The effective $N$ is of order 10–20, for which the luck benchmark is about 0.8–1.0.
- This is why the evidence for CTR does not rest on the 2021–24 Sharpe alone. It also rests on:
  1. **stable neighbours:** every neighbouring setting keeps at least 96% of the Sharpe;
  2. **consistency:** every calendar year positive or better than BTC;
  3. **cold starts:** a mean Sharpe of 1.56 across 11 cold-start runs;
  4. **genuinely new data:** 2026, run once, +13.5% vs −2.9%.

  None of these can be produced by selecting the luckiest of many trials.

## References
- Andersen, T., Bollerslev, T., Diebold, F., Labys, P. (2003). Modeling and forecasting realized volatility. *Econometrica*.
- Anis, A., Lloyd, E. (1976). The expected value of the adjusted rescaled Hurst range of independent normal summands. *Biometrika*.
- Azar, M., Munos, R., Kappen, H. (2013). Minimax PAC bounds on the sample complexity of reinforcement learning with a generative model. *Machine Learning*.
- Bailey, D., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management*.
- Barndorff-Nielsen, O., Shephard, N. (2004). Power and bipower variation with stochastic volatility and jumps. *Journal of Financial Econometrics*.
- Barndorff-Nielsen, O., Kinnebrock, S., Shephard, N. (2010). Measuring downside risk: realised semivariance. In *Volatility and Time Series Econometrics*.
- Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics*.
- Grinold, R. (1989). The fundamental law of active management. *Journal of Portfolio Management*.
- Hamilton, J. (1989). A new approach to the economic analysis of nonstationary time series and the business cycle. *Econometrica*.
- Hanley, J., McNeil, B. (1982). The meaning and use of the area under a ROC curve. *Radiology*.
- Hill, B. (1975). A simple general approach to inference about the tail of a distribution. *Annals of Statistics*.
- Kelly, J. (1956). A new interpretation of information rate. *Bell System Technical Journal*.
- Lempérière, Y. et al. (2014). Two centuries of trend following. *Journal of Investment Strategies*.
- Lo, A., MacKinlay, C. (1988). Stock market prices do not follow random walks: evidence from a simple specification test. *Review of Financial Studies*.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Lorden, G. (1971). Procedures for reacting to a change in distribution. *Annals of Mathematical Statistics*.
- Moreira, A., Muir, T. (2017). Volatility-managed portfolios. *Journal of Finance*.
- Page, E. (1954). Continuous inspection schemes. *Biometrika*.
- Parkinson, M. (1980). The extreme value method for estimating the variance of the rate of return. *Journal of Business*.
- Patton, A., Sheppard, K. (2015). Good volatility, bad volatility: signed jumps and the persistence of volatility. *Review of Economics and Statistics*.
- Watkins, C., Dayan, P. (1992). Q-learning. *Machine Learning*.
- Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*.
