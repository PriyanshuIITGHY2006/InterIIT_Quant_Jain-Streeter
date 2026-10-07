# Glossary and Research References

Every term, method and research paper used in this project, and **what we took from each**: the idea we implemented, the test we ran, or the warning we followed. Where a published result did not hold on our data, this document says so.

- **Part A** is a glossary of terms.
- **Part B** lists the research by theme. Each entry gives what the source says, what we took from it, and where it is used.

The strategies themselves are documented in `reports/btc_strategy.md` and `reports/eth_strategy.md`; the data research in `reports/data_research_report.md`, `reports/indicator_analysis_report.md` and `reports/ml_research_report.md`.

**Labels** used in "What we took":
- **[built]** implemented in our code and used by a final strategy;
- **[tested]** implemented and tested, but not part of the finals;
- **[guide]** shaped a design choice or our testing discipline;
- **[background]** context only.

---

# Part A: Glossary

| Term | Meaning | Where it appears |
|---|---|---|
| **ADF test** (Augmented Dickey–Fuller) | Tests whether a series has a unit root (is non-stationary); a small p-value means stationary | Notebook 01 §5 |
| **ADX** (Average Directional Index) | Wilder's measure of trend *strength*, regardless of direction | Notebook 02; rejected as a direction signal (BTC report M3.4) |
| **Adaptive warm-up** | Moving averages and percentiles use all bars available until their full window exists, so a strategy can start on data with no history | `src/strategies/market_state.py` |
| **Amihud illiquidity** | \|return\| per unit of traded value; high values mean a thin market | Notebook 02 §6 |
| **Aroon** | Days since the n-day high and low, scaled 0–100; a trend-age indicator | Notebook 02 §10 |
| **ATR** (Average True Range) | Average daily range including gaps; a volatility measure in price units | Keltner channel, squeeze, stop tests |
| **AUC** | Area under the ROC curve; the probability that a classifier ranks a random positive above a random negative. 0.5 = chance | ML research |
| **Banded trend vote** | "Close above its n-day average", with a hysteresis band of 1 × daily volatility so the vote doesn't flip on noise | `src/features/trend.py` (`ma_state_with_band`) |
| **Baum–Welch** | The expectation-maximisation algorithm for fitting a hidden Markov model | `src/ml/hmm.py` |
| **Bipower variation** | Realised variance that is robust to jumps (sum of products of adjacent absolute returns) | Storm brake |
| **Bollinger Bands** | Moving average ± k standard deviations | Squeeze |
| **Borrow / financing cost** | Interest on borrowed USDT for leverage (8%/yr) and on borrowed BTC for shorts (assumed 10%/yr), charged daily in the engine | `src/strategies/execution.py` |
| **Buy-and-hold (B&H)** | The benchmark: buy at the first open and hold, with the same costs | All results |
| **Calm uptrend** | The market state with volatility in the calmer half of the past year and an efficient (or non-choppy) trend; the strategies hold up to 1.5× here | Market-state framework |
| **Calmar ratio** | Annual return ÷ \|max drawdown\| | Results tables |
| **Capitulation** | A deep crash (here: more than 60% below the 365-day high); after one, the BTC strategy does not short | CTR-S short side |
| **Chaikin Money Flow** | Volume-weighted position of each close within its day's range; > 0 accumulation, < 0 distribution | Notebook 02 §6 |
| **Choppiness index** | Sum of true ranges ÷ the n-day high–low range, on a log scale. Below 38.2 = a clean trend; about 50 = a random walk | Regime layer |
| **Cold start** | Running a strategy on data that begins with no history | Robustness tests |
| **Cost hurdle** | Net ≈ N · (e − 0.30%): with N round trips a year and gross edge e per trade, each trade must earn more than the 0.30% round-trip cost | Short-term research |
| **CTR** (Calm-Trend Regime) | Long-only strategy: 7 trend votes × regime size × storm brake × squeeze × 200-day soft gate. The ETH final (CTR-ETH) and the long side of the BTC final | `src/strategies/market_state.py` |
| **CTR-S** | CTR plus a half-size short in calm, fully confirmed, non-capitulation bear markets; the BTC final | `src/strategies/btc_strategy.py` |
| **CUSUM** | Cumulative-sum change detector; flags a shift in the mean | Notebook 02 §10; ML research E1 |
| **CVaR** (expected shortfall) | Average loss on the worst 5% of days | Risk tables |
| **Deflated Sharpe ratio** | A Sharpe ratio corrected for the number of strategies tried, sample length and non-normal returns | `src/backtest/evaluation.py` |
| **Diebold–Mariano test** | Tests whether two forecasts are equally accurate | ML research A |
| **Downside semivariance** | Realised variance from negative returns only ("bad volatility") | Storm brake |
| **Drawdown** | Fall of equity from its running peak; **max drawdown** is the worst | All results |
| **Efficiency ratio** | \|net move\| ÷ sum of \|daily moves\| over n days. 1 = a straight line; about 1/√n = a random walk | Regime layer |
| **Embargo / purging** | Gaps between training and test data so that overlapping labels cannot leak | ML walk-forward |
| **EWMA** | Exponentially weighted moving average | Risk forecast |
| **GARCH / GJR-GARCH** | Volatility models in which today's variance depends on yesterday's shock and variance; GJR adds extra weight on negative shocks (the "leverage effect") | Notebook 01 §7.4 |
| **Garman–Klass, Parkinson, Rogers–Satchell, Yang–Zhang** | Volatility estimators that use the open, high, low and close instead of just the close | `src/features/indicators.py` |
| **HAR model** | Heterogeneous autoregressive volatility model: tomorrow's volatility from the last day, week and month | Notebook 01 §7.3; ML research A |
| **Heikin-Ashi** | Smoothed candles (each one averages the previous candle and today's prices); causal | Notebook 02 §10 |
| **Hidden Markov model (HMM)** | A model with unobserved states (e.g. calm/stormy), each with its own return distribution. Only *filtered* (causal) probabilities are allowed | ML research B |
| **Hill estimator** | Estimates the tail index α in P(\|r\| > x) ~ x<sup>−α</sup> | Notebook 01 §4.3 |
| **Hurst exponent** | R/S statistic: > 0.5 suggests persistence, < 0.5 mean reversion; biased in small samples | Notebook 02 (rejected) |
| **Information coefficient (IC)** | Rank correlation between a signal and the next period's return | Indicator scorecard |
| **Jarque–Bera test** | Tests normality from skewness and kurtosis | Notebook 01 |
| **Kalman filter** | Recursive estimator of a hidden level; only the causal filter is allowed, never the smoother | Notebook 02 §10 |
| **Keltner Channel** | Moving average ± k × ATR | Squeeze |
| **Kelly criterion** | The growth-optimal bet size, f* = μ/σ²; capped in practice ("fractional Kelly") | BTC report M4.5; stage 27 |
| **KPSS test** | Stationarity test whose null is "stationary" (the opposite of ADF) | Notebook 01 §5 |
| **K-means / PCA** | Clustering and dimension reduction, used to group indicators by what they measure | Notebook 02 |
| **Ljung–Box test** | Tests for autocorrelation over many lags at once | Notebook 01 §6.2 |
| **Lookahead bias** | Using information not yet available at decision time; prevented by next-open execution and truncation tests | Project rules |
| **Market state** | One of 7 named states (Storm, Downtrend, Bear rally, Calm uptrend, Volatile uptrend, Uptrend, Fading uptrend) | Market-state framework |
| **Markov switching** | Regime model with hidden states that switch with fixed probabilities | Notebook 02 §10 |
| **Partial dependence plot (PDP)** | How a model's prediction changes with one feature, averaged over the others | ML explainability |
| **Payoff ratio** | Average win ÷ average loss | Risk–reward tables |
| **Profit factor** | Gross wins ÷ gross losses | Risk–reward tables |
| **Q-learning** | Reinforcement-learning algorithm that learns a value for each state–action pair | ML research D, E2 |
| **QLIKE** | A loss function for volatility forecasts that is robust to noisy volatility proxies | ML research A |
| **Realised volatility (RV)** | Sum of squared intraday (hourly) returns over the day | Risk measures |
| **Rebalance band** | An open position is resized only when the target moves more than 0.25 | Execution |
| **RSI / Stochastic RSI** | Wilder's relative strength index (up moves vs down moves), and its stochastic transform | Notebook 02 (rejected for direction) |
| **Sharpe ratio** | Mean daily return ÷ its standard deviation, × √365 (risk-free rate 0) | All results |
| **SHAP** | Shapley-value attribution: how much each feature pushed one prediction | ML explainability |
| **Short squeeze** | A sharp rally that forces shorts to cover; the main risk of the short side | CTR-S risk plan |
| **Soft gate** | × 0.5 on the long size while the banded 200-day trend is down | CTR step 5 |
| **Sortino ratio** | Like Sharpe, but divides by the deviation of negative returns only | All results |
| **Squeeze** | Bollinger Bands inside the Keltner Channel: unusually low volatility, usually followed by expansion | CTR step 4 |
| **Storm brake** | × 0.5 while the downside-weighted volatility forecast is > 1.5 × its 1-year median | CTR step 3 |
| **Supertrend** | ATR band that flips side when price closes through it | Notebook 02 (rejected) |
| **Tail dependence** | Probability that two assets have extreme moves together | ETH report |
| **Taker imbalance** | Share of volume from aggressive buyers versus its norm (Binance taker fields) | Notebook 02 §6 |
| **Time-series momentum (TSMOM)** | Going long an asset after its own past return was positive | The trend votes |
| **Triple-barrier label** | Labels a trade by which comes first: profit target, stop, or time limit | ML research C |
| **Truncation test** | Signals computed on data up to T must equal those computed on the full data, up to T | `src/backtest/checks.py` |
| **Variance ratio** | Var(q-day return) ÷ (q × Var(1-day return)); > 1 trending, < 1 mean-reverting | Notebook 01 §6.4 |
| **Volatility percentile** | Today's volatility ranked within the trailing year (0 to 1) | Regime layer, short condition |
| **Volatility targeting** | Scaling position size inversely to forecast volatility | Stages 2, 10; ETH research |
| **Walk-forward** | Repeated train-then-test on later data, moving forward in time | ML research |

---

# Part B: Research references and what we took from each

## B1. The statistical nature of crypto returns

| Source | What it says | What we took |
|---|---|---|
| Mandelbrot, B. (1963). The variation of certain speculative prices. *Journal of Business*. | Price changes are heavy-tailed, not Gaussian | **[guide]** We measured BTC/ETH tails (notebook 01 §4) before choosing any statistic that assumes normality. |
| Cont, R. (2001). Empirical properties of asset returns: stylized facts and statistical issues. *Quantitative Finance*. | The "stylized facts": no return autocorrelation, heavy tails, volatility clustering, leverage effect | **[guide]** Notebook 01 is organised as a check of each stylized fact on BTC/ETH. All held except the leverage effect, which is absent in crypto (B2). |
| Hill, B. (1975). A simple general approach to inference about the tail of a distribution. *Annals of Statistics*. | An estimator of the tail index α | **[tested]** Notebook 01 §4.3: α ≈ 3 for both coins (hourly kurtosis 13–16), so kurtosis is barely defined. That is why our results use medians, ranks and percentiles instead of means and z-scores. |
| Jarque, C., Bera, A. (1987). A test for normality of observations and regression residuals. *International Statistical Review*. | Normality test from skewness and kurtosis | **[tested]** Rejected normality for every coin-year (notebook 01). |
| Dickey, D., Fuller, W. (1979). Distribution of the estimators for autoregressive time series with a unit root. *Journal of the American Statistical Association*. | The unit-root (ADF) test | **[tested]** Log prices are non-stationary and returns stationary in the mean (notebook 01 §5). So every signal uses returns or ratios, never raw price levels. |
| Kwiatkowski, D., Phillips, P., Schmidt, P., Shin, Y. (1992). Testing the null hypothesis of stationarity against the alternative of a unit root. *Journal of Econometrics*. | KPSS, the complementary stationarity test | **[tested]** Used alongside ADF, since each alone is weak (notebook 01 §5). |
| Ljung, G., Box, G. (1978). On a measure of lack of fit in time series models. *Biometrika*. | A joint test for autocorrelation | **[tested]** Raw returns: tiny autocorrelation, unstable between years. Squared returns: strong and persistent (notebook 01 §6.2). This is the basis of "direction is unpredictable, volatility is not". |
| Lo, A., MacKinlay, C. (1988). Stock market prices do not follow random walks: evidence from a simple specification test. *Review of Financial Studies*. | The variance-ratio test | **[tested]** BTC/ETH variance ratios are close to 1 and change sign between years (notebook 01 §6.4; BTC report M2). No stable trending or mean-reverting regime to exploit directly. |
| Engle, R., Granger, C. (1987). Co-integration and error correction. *Econometrica*. | Cointegration testing | **[tested]** ETH/BTC looked cointegrated over the full sample (p = 0.054), but not within any single year (notebook 01). We dropped pairs and ratio mean-reversion trading. |
| Newey, W., West, K. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*. | HAC standard errors | **[tested]** Used for the overlapping 7-day regressions in notebook 02 §3, so the t-statistics are not inflated. |
| Joe, H. (1997). *Multivariate Models and Dependence Concepts*. Chapman & Hall. | Tail-dependence coefficients | **[tested]** ETH has strong lower-tail and weak upper-tail dependence with BTC: the coins crash together and rally apart (ETH report). This is why ETH gets no extra diversification credit in a crash. |
| Kahneman, D., Tversky, A. (1992). Advances in prospect theory: cumulative representation of uncertainty. *Journal of Risk and Uncertainty*. | Loss aversion and asymmetric reactions to losses and gains | **[background]** One explanation offered in the ETH report for why crashes are sharper and more correlated than rallies. |

## B2. Volatility: measurement and forecasting

| Source | What it says | What we took |
|---|---|---|
| Engle, R. (1982). Autoregressive conditional heteroscedasticity with estimates of the variance of United Kingdom inflation. *Econometrica*. | ARCH: volatility clusters and is forecastable | **[guide]** The foundation of the whole design: size positions by forecastable volatility, not by unforecastable direction. |
| Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics*. | GARCH(1,1) | **[tested]** Fitted in notebook 01 §7.4 (with the `arch` library, research only). Very high persistence for both coins. |
| Glosten, L., Jagannathan, R., Runkle, D. (1993). On the relation between the expected value and the volatility of the nominal excess return on stocks. *Journal of Finance*. | GJR-GARCH: negative shocks raise volatility more (the leverage effect) | **[tested]** No significant leverage effect in BTC or ETH daily returns (notebook 01 §7.4; ETH report). So our downside asymmetry comes from realised semivariance (below), not from GARCH. |
| Parkinson, M. (1980). The extreme value method for estimating the variance of the rate of return. *Journal of Business*. | Volatility from the high–low range, about 5× more efficient than close-to-close | **[built]** `parkinson_vol`. It is the fallback for the realised measures when no hourly data exists (`add_daily_proxies`), so the strategies run on daily candles alone. |
| Garman, M., Klass, M. (1980). On the estimation of security price volatilities from historical data. *Journal of Business*. | An OHLC volatility estimator | **[tested]** `garman_klass_vol`; compared in notebook 02 §2. |
| Rogers, L., Satchell, S. (1991). Estimating variance from high, low and closing prices. *Annals of Applied Probability*. | A drift-independent OHLC estimator | **[tested]** `rogers_satchell_vol`; compared in notebook 02 §2. |
| Yang, D., Zhang, Q. (2000). Drift-independent volatility estimation based on high, low, open, and close prices. *Journal of Business*. | The minimum-variance OHLC estimator, handling overnight gaps | **[tested]** `yang_zhang_vol`. In notebook 02 §2 the estimators ranked within a few percent of each other; for 24/7 crypto, gaps don't matter. |
| Andersen, T., Bollerslev, T., Diebold, F., Labys, P. (2003). Modeling and forecasting realized volatility. *Econometrica*. | Realised volatility from intraday returns is a near-exact measure of daily variance | **[built]** `realised_measures`: daily RV from hourly bars, the input of the storm brake. |
| Barndorff-Nielsen, O., Shephard, N. (2004). Power and bipower variation with stochastic volatility and jumps. *Journal of Financial Econometrics*. | Bipower variation separates smooth volatility from jumps | **[built]** Jumps fade within days, smooth volatility persists (notebook 02 §3). The storm brake weights bipower variation, not raw RV, so a one-off jump doesn't cut the position for weeks. |
| Barndorff-Nielsen, O., Kinnebrock, S., Shephard, N. (2010). Measuring downside risk: realised semivariance. In *Volatility and Time Series Econometrics*. | Realised semivariance splits RV into up and down parts | **[built]** Downside semivariance enters the storm brake's forecast. |
| Patton, A., Sheppard, K. (2015). Good volatility, bad volatility: signed jumps and the persistence of volatility. *Review of Economics and Statistics*. | "Bad" (downside) volatility predicts future volatility far more than "good" volatility | **[built]** Confirmed on BTC: downside semivariance carries about 2× the forecasting weight (notebook 02 §3). This is the BTC-specific design of the storm brake: √(365 · EWMA₃₀(0.5 · BV + RS⁻)). |
| Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics*. | The HAR model: day, week and month volatility terms mimic long memory | **[tested]** Out-of-sample R² 0.60 (BTC) / 0.73 (ETH) on 2023 (notebook 01 §7.3). In ML research A it stayed the champion against gradient boosting. The evidence that volatility is forecastable comes from here. |
| Patton, A. (2011). Volatility forecast comparison using imperfect volatility proxies. *Journal of Econometrics*. | QLIKE is a robust loss for volatility forecasts | **[tested]** The loss function in ML research A. |
| Diebold, F., Mariano, R. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics*. | A test of equal forecast accuracy | **[tested]** HAR + boosting was significantly *worse* than HAR for BTC (p = 0.005) and equal for ETH (p = 0.87), so the ML volatility model was dropped. |
| Moreira, A., Muir, T. (2017). Volatility-managed portfolios. *Journal of Finance*. | Scaling exposure inversely to variance raises the Sharpe ratio | **[built]** The theoretical basis of regime sizing (BTC report M4.4). Our version cuts size in stormy states (× 0.6, storm brake × 0.5) instead of targeting a volatility level. |
| Cederburg, S., O'Doherty, M., Wang, F., Yan, X. (2020). On the performance of volatility-managed portfolios. *Journal of Financial Economics* (via Xu's 2024 review). | Volatility-managed portfolios often fail out of sample, partly because the scaling constant uses future data | **[guide]** Every threshold in our framework is relative to *trailing* history (percentiles within the past year, medians that end at t), never full-sample. A pure 40% volatility target was tested and rejected (stage 10). |
| Ghia, A., Hou, J. (2021). Crypto insights: the impact of volatility targeting. Bloomberg. | Conservative EWMA volatility targeting for BTC/ETH | **[tested]** Early stages used volatility-targeted sizing; it kept positions too small in bull markets (average exposure 0.65–0.74) and was replaced by regime sizing. |

## B3. Technical indicators (originators of the methods we implemented)

| Source | What it introduced | What we took |
|---|---|---|
| Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. | RSI, ATR, ADX | **[built]** ATR (Keltner channel and squeeze). **[tested]** RSI and ADX: no consistent next-week direction signal (notebook 02; BTC report M3.3–M3.4). The one robust RSI finding, BTC bouncing after RSI < 35 in 4 of 4 years, supports the "no shorts after a capitulation" rule. |
| Bollinger, J. (2001). *Bollinger on Bollinger Bands*. McGraw-Hill. | Bollinger Bands, %B, the band squeeze | **[built]** Squeeze (with Keltner). **[tested]** %B as a direction signal: rejected. |
| Keltner, C. (1960). *How to Make Money in Commodities*. | The Keltner channel (later ATR-based) | **[built]** The squeeze's outer band. |
| Carter, J. (2005). *Mastering the Trade*. McGraw-Hill. | The "squeeze": Bollinger Bands inside Keltner channels precede big moves | **[built]** CTR step 4. Our data refined the idea: after a squeeze, *volatility* rises 10–14% but direction is random (notebook 02 §4). So we cut size (× 0.75) instead of betting on a breakout. |
| Kaufman, P. (1995). *Smarter Trading*. McGraw-Hill. | The efficiency ratio (in KAMA) | **[built]** Calm-trend label: 30-day efficiency ratio above its expanding median. |
| Dreiss, E. W. (1990s), the Choppiness Index (practitioner indicator; no formal paper) | Whether the market is trending or chopping | **[built]** Choppiness(14) < 38.2 marks a clean trend: positive trend payoff in 4 of 4 years (notebook 02). We derived its random-walk baseline ourselves (≈ 50, BTC report M4.7). |
| Chande, T., Kroll, S. (1994). *The New Technical Trader*. Wiley. | Stochastic RSI; Aroon (Chande, 1995) | **[tested]** Both in notebook 02; no reliable direction signal. |
| Hurst, H. (1951). Long-term storage capacity of reservoirs. *Transactions of the ASCE*. | The rescaled-range (R/S) statistic | **[tested]** `rolling_hurst`. BTC's "persistence" matched shuffled data, so it was estimator bias (notebook 02); dropped. |
| Anis, A., Lloyd, E. (1976). The expected value of the adjusted rescaled Hurst range of independent normal summands. *Biometrika*. | The small-sample expectation of R/S | **[guide]** Explains the Hurst bias above (BTC report M3.9). |
| Valcu, D. (2004). Using the Heikin-Ashi technique. *Technical Analysis of Stocks & Commodities*. | Heikin-Ashi candles | **[tested]** Proved to be an exponential filter in disguise (BTC report M3.6); no edge after costs. |
| Kalman, R. (1960). A new approach to linear filtering and prediction problems. *Journal of Basic Engineering*. | The Kalman filter | **[tested]** `kalman_trend`, causal filter only. Equivalent to an EWMA with a fixed gain (BTC report M3.7), so no improvement over moving averages. |
| Page, E. (1954). Continuous inspection schemes. *Biometrika*. | The CUSUM change detector | **[tested]** `cusum_state`. Its optimality assumes known pre- and post-change distributions, which crypto violates (BTC report M3.8). The CUSUM regimes barely separated returns. |
| Lorden, G. (1971). Procedures for reacting to a change in distribution. *Annals of Mathematical Statistics*. | CUSUM's minimax optimality | **[guide]** Used to explain *why* CUSUM fails here (M3.8). |
| Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. *Journal of Financial Markets*. | The illiquidity ratio | **[tested]** `amihud`. The most consistent direction signal in notebook 02 (IC ≥ 0 in 8 of 8 coin-years), but it is driven by volume drift and Binance's zero-fee period. It was not used in a strategy. |
| Chaikin, M. (practitioner; no formal paper). Chaikin Money Flow. | Accumulation/distribution from where closes fall in the range | **[tested]** For ETH, positive money flow predicted higher *volatility* (4 of 4 years), not direction. |
| Hotelling, H. (1933). Analysis of a complex of statistical variables into principal components. *Journal of Educational Psychology*. MacQueen, J. (1967). Some methods for classification and analysis of multivariate observations. *Berkeley Symposium*. | PCA and K-means | **[tested]** Clustering indicators by what they measure (volatility, trend, flow). Under heavy tails, the clusters degenerated into "outlier days" vs the rest (BTC report M3.11). |

## B4. Regimes and state models

| Source | What it says | What we took |
|---|---|---|
| Hamilton, J. (1989). A new approach to the economic analysis of nonstationary time series and the business cycle. *Econometrica*. | Markov-switching regime models | **[tested]** `markov_switching_prob` (filtered probabilities only). The regimes separate *variance*, not mean returns (BTC report M3.10). That is the reason our states are defined by volatility and trend quality, not by "bull/bear probability". |
| Baum, L., Petrie, T., Soules, G., Weiss, N. (1970). A maximization technique occurring in the statistical analysis of probabilistic functions of Markov chains. *Annals of Mathematical Statistics*. Rabiner, L. (1989). A tutorial on hidden Markov models and selected applications in speech recognition. *Proceedings of the IEEE*. | Baum–Welch fitting and the forward filter | **[tested]** Written in-house (`src/ml/hmm.py`). It found calm (≈ 26% annual vol) and stormy (≈ 66%) states. These are independent confirmation of our percentile rule, but trading on the HMM did not beat it (Sharpe 0.86 vs 0.88). |
| Koki, C., Leonardos, S., Piliouras, G. (2022). Exploring the predictability of cryptocurrencies via Bayesian hidden Markov models. *Research in International Business and Finance*. | BTC/ETH/XRP show bull, bear and calm regimes; a 4-state model forecasts best | **[guide]** Supported building the market-state framework around a small number of named, persistent states. |
| Goulding, C., Harvey, C., Mazzoleni, M. (2023). Momentum turning points. *Journal of Financial Economics*. | Slow and fast trend signals define Bull, Correction, Bear and Rebound states; intermediate-speed blends beat either speed | **[built]** The 7-vote ensemble (20 to 200 days) blends speeds. The soft gate holds *half* size in "Rebound" states (slow trend down, fast up) instead of zero. **[tested]** Their state-specific returns flipped sign with the lookback in our 4 years of data, so we did not build a dynamic state rule. |
| Goulding, C., Harvey, C., Mazzoleni, M. (2023). Breaking bad trends. *Financial Analysts Journal*. | More turning points per year mean worse trend-following | **[tested]** 2024 was not unusually choppy by this measure, so our weak 2024 validation was not explained by turning points (`tries/reports/research_turning_points.md`). |

## B5. Trend following and momentum

| Source | What it says | What we took |
|---|---|---|
| Moskowitz, T., Ooi, Y. H., Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics*. | An asset's own past return predicts its future return, across 58 futures markets | **[built]** The trend votes are time-series momentum signals. |
| Hurst, B., Ooi, Y. H., Pedersen, L. H. (2017). A century of evidence on trend-following investing. *Journal of Portfolio Management*. | Trend-following has worked since 1880 and is strongest in crises | **[guide]** Why the strategies' main job is defence in bear markets. |
| Lempérière, Y., Deremble, C., Seager, P., Potters, M., Bouchaud, J.-P. (2014). Two centuries of trend following. *Journal of Investment Strategies*. | Trend profits are persistent over two centuries and many asset classes | **[guide]** Cited in BTC report M3.5 as evidence that trend-following is not a data-mined artefact. |
| Liu, Y., Tsyvinski, A. (2021). Risks and returns of cryptocurrency. *Review of Financial Studies*. | Strong crypto time-series momentum at 1–4 week horizons | **[built]** The shortest trend votes (20 and 30 days) sit in this horizon. |
| Liu, Y., Tsyvinski, A., Wu, X. (2022). Common risk factors in cryptocurrency. *Journal of Finance*. | Market, size and momentum factors in the crypto cross-section | **[background]** Cross-sectional; we trade two coins, so not applicable. |
| Detzel, A., Liu, H., Strauss, J., Zhou, G., Zhu, Y. (2021). Learning and predictability via technical analysis: evidence from bitcoin and stocks with hard-to-value fundamentals. *Financial Management*. | Price-to-moving-average ratios from 5 to 100 days predict BTC returns, in and out of sample; MA rules cut drawdowns | **[built]** Moving-average trend states as the direction input, and multiple lookbacks instead of one. |
| Zarattini, C., Pagani, A., Barbon, A. (2025). Catching crypto trends. SSRN working paper. | An ensemble of Donchian channels over 9 lookbacks with volatility targeting; BTC Sharpe ≈ 1.5 | **[guide]** Independent support for an *ensemble* of lookbacks; ours uses moving averages with 7 lookbacks. |
| Kang, S., Ryu, D. (2026). Time-series momentum and market timing in Bitcoin. *Risk Management*. | Slow (12-week) momentum beats fast signals in BTC; fast signals overreact | **[guide]** Supports the weight of slow votes (75–200 days) and the 200-day gate. |
| Grobys, K., Sapkota, N. (2019). Cryptocurrencies and momentum. *Economics Letters*. | No significant cross-sectional momentum, 2014–18 | **[background]** Our momentum is time-series, not cross-sectional. |
| Grobys, K. et al. (2025). Cryptocurrency momentum has (not) its moments. *Financial Markets and Portfolio Management*. | Crypto momentum crashes; volatility scaling helps payoffs but not tail risk | **[guide]** Why we added a separate, downside-specific storm brake instead of relying on volatility scaling alone. |
| Faber, M. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management*. | A 10-month moving-average filter cuts drawdowns | **[built]** The 200-day soft gate is the daily equivalent. |
| Grinold, R. (1989). The fundamental law of active management. *Journal of Portfolio Management*. | Performance ≈ skill (IC) × √breadth | **[guide]** BTC report M3.1: with IC ≈ 0.02 and costs of 0.30% per round trip, more trades cannot rescue a weak direction signal. |
| Quantpedia: Padysak, M., Vojtko, R. (2022). Trend-following and mean-reversion in Bitcoin; and Revisiting trend-following and mean-reversion strategies in Bitcoin (2024). | Buying 10-day highs (MAX) worked and kept working; buying lows (MIN) worked in-sample but failed out of sample | **[tested]** MIN-style dip sleeves (stages 15, 25, 26): they lost after costs. Consistent with the 2024 follow-up. |
| Quantpedia (2024). How to design a simple multi-timeframe trend strategy on Bitcoin. | Daily trend with hourly entries | **[background]** Costs not reported; not pursued. |

## B6. Short-term effects, mean reversion and the short side

| Source | What it says | What we took |
|---|---|---|
| Shen, D., Urquhart, A., Wang, P. (2022). Bitcoin intraday time series momentum. *Financial Review*. | The first half-hour predicts the last half-hour | **[guide]** About 365 round trips a year × 0.30% ≈ 110% a year in costs. Rejected by the cost hurdle (`tries/reports/research_short_term_strategies.md`). |
| Wen, Z., Bouri, E., Xu, Y., Zhao, Y. (2022). Intraday return predictability in the cryptocurrency markets: momentum, reversal, or both. *North American Journal of Economics and Finance*. | Both intraday momentum and reversal exist | **[tested]** We found the 1–4 hour reversal is real but worth only 8–15 bps per trade, below costs. |
| Vojtko, R., Javorská, M. (Quantpedia). Intraday seasonality in Bitcoin. | Long BTC 22:00–24:00 UTC: Sharpe 1.58 (2015–21) | **[tested]** On our data: +2.1 bps/day, t = 0.9, negative in 2022, and hour profiles are negatively correlated across years (notebook 01). Rejected as data snooping. |
| Caporale, G. M., Plastun, A. (2019). The day of the week effect in the cryptocurrency market. *Finance Research Letters*. Aharon, D., Qadan, M. (2019). Bitcoin and the day-of-the-week effect. *Finance Research Letters*. Baur, D., Cahill, D., Godfrey, K., Liu, Z. (2019). Bitcoin time-of-day, day-of-week and month-of-year effects in returns and trading volume. *Finance Research Letters*. | Mixed and time-varying calendar effects | **[tested]** No weekday effect in our data (all \|t\| < 1.1, notebook 01). No calendar rules anywhere. |
| Kosc, K., Sakowski, P., Ślepaczuk, R. (2019). Momentum and contrarian effects on the cryptocurrency market. *Physica A*. Zaremba, A. et al. (2021). Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets. *International Review of Financial Analysis*. Kiefer, Nowotny. Reversal in cryptocurrency returns. SSRN. | Daily reversal *across many coins*; liquid coins show momentum instead | **[background]** Needs a cross-section of illiquid coins; BTC and ETH are the most liquid. Not applicable. |
| Corbet, S., Katsiampa, P. (2020). Asymmetric mean reversion of Bitcoin price returns. *International Review of Financial Analysis*. | Negative extreme returns revert more strongly than positive ones | **[built]** The capitulation rule of the BTC short side: no short once BTC is more than 60% below its 365-day high, where rebounds are sharpest. Without it (variant X1), 2022 was −7.4% instead of −0.3% (stage 32). |
| *The prevalence of price overreactions in the cryptocurrency market* (Caporale and co-authors, 2020); Caporale, G. M., Plastun, A. (2019). Price overreactions in the cryptocurrency market. *Journal of Economic Studies*. | Overreactions after extreme moves are common and partly reverse | **[built]** Same lesson as above: don't short into panics. Also the reason for the short side's calm-volatility condition (volatility percentile ≤ 0.5). Without it (X4), Sharpe fell from 1.16 to 0.95. |
| Zarattini, C., Aziz, A., Barbon, A. (2024). Beat the market: an effective intraday momentum strategy for the S&P 500 ETF (SPY). Concretum working paper. | Intraday "noise area" breakout on SPY | **[background]** Not viable for hourly crypto at our costs. |
| Sifat, I., Mohamad, A., Shariff, M. (2019). Lead-lag relationship between Bitcoin and Ethereum: evidence from hourly and daily data. *Research in International Business and Finance*. *Bitcoin, Ethereum, and the ambiguity of price discovery* (2026). *Journal of Risk and Financial Management*. High-frequency lead-lag studies (Erasmus thesis; Copenhagen Business School). | BTC–ETH lead-lag, mostly at seconds-to-minutes horizons and in high-volatility regimes | **[tested]** On daily data the coins move together on the same day; a "BTC leads ETH" rule lost money (ML research E1). Each strategy uses only its own coin's data. |
| Hudson, R., Urquhart, A. (2021). Technical trading and cryptocurrencies. *Annals of Operations Research*. | About 15,000 rules on BTC/ETH; some survive data-snooping tests; no out-of-sample predictability for BTC | **[guide]** Few rules, conventional parameters, daily frequency. |
| Gerritsen, D., Bouri, E., Ramezanifar, E., Roubaud, D. (2020). The profitability of technical trading rules in the Bitcoin market. *Finance Research Letters*. *Are simple technical trading rules profitable in bitcoin markets?* (2024). *International Review of Economics & Finance*. *The effectiveness of technical trading rules in cryptocurrency markets* (2019). | Profitability is unstable and declining; daily rules are more robust to costs than intraday ones | **[guide]** Daily decisions with multi-day holds; the cost hurdle N · (e − 0.30%). |
| Kaminski, K., Lo, A. (2014). When do stop-loss rules stop losses? *Journal of Financial Markets*. | Under a random walk, stops lower returns; they help only when returns are momentum-driven | **[tested]** A 3 × ATR trailing stop cut BTC's Sharpe from 1.16 to 0.71 (stage 11). Our stops are trend breaks instead, and the short is covered when any condition fails. |
| Schmeling, M., Schrimpf, A., Todorov, K. (2023). Crypto carry. BIS Working Paper 1087. | Futures carry > 10% a year, linked to leverage demand and crashes | **[background]** Needs futures data we don't have. It also informs our assumed 10%/yr short-borrow fee. |
| Anastasopoulos, Gradojevic et al. (2026). Order flow and cryptocurrency returns. *Journal of Financial Markets*. | Order flow has a permanent price impact | **[tested]** Binance taker-buy imbalance (`taker_imbalance_z`) in notebook 02: no stable direction signal at a daily horizon. |

## B7. Position sizing, risk and performance measurement

| Source | What it says | What we took |
|---|---|---|
| Kelly, J. (1956). A new interpretation of information rate. *Bell System Technical Journal*. | Growth-optimal sizing f* = μ/σ² | **[built]** The 1.5× cap applies only in calm trends, where f* is largest; it is a fractional-Kelly safeguard (BTC report M4.5). **[tested]** Full Bayesian regime-Kelly (stage 27): no gain. |
| Sharpe, W. (1966). Mutual fund performance. *Journal of Business*. Sharpe, W. (1994). The Sharpe ratio. *Journal of Portfolio Management*. | The Sharpe ratio | **[built]** Daily equity returns, × √365, risk-free rate 0 (`src/backtest/metrics.py`). |
| Sortino, F., Price, L. (1994). Performance measurement in a downside risk framework. *Journal of Investing*. | The Sortino ratio | **[built]** A required metric. |
| Young, T. (1991). Calmar ratio: a smoother tool. *Futures*. | Annual return ÷ max drawdown | **[built]** Reported as an extra metric; the main reason CTR-S was preferred over CTR (1.22 vs 0.95). |
| Bailey, D., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management*. | Corrects the Sharpe for multiple trials | **[built]** `deflated_sharpe` and the luck table in BTC report M5. With an effective 10–20 independent trials, luck alone reaches about 0.8–1.0. That is why our evidence rests on neighbours, cold starts and unseen years, not on one Sharpe ratio. |
| Bailey, D., Borwein, J., López de Prado, M., Zhu, Q. (2017). The probability of backtest overfitting. *Journal of Computational Finance*. | Estimates how likely the best backtest is overfit | **[guide]** Neighbour checks (≥ 80–96% of the Sharpe kept), pre-registered gates in `docs/evaluation_protocol.md`, and every trial logged in `tries/results/experiment_log.csv`. |
| White, H. (2000). A reality check for data snooping. *Econometrica*. Hansen, P. (2005). A test for superior predictive ability. *Journal of Business & Economic Statistics*. | Tests whether the best of many rules beats a benchmark beyond luck | **[guide]** The same multiple-testing discipline: few rule families, placebos, and a frozen strategy before any test year. |

## B8. Machine learning and reinforcement learning

| Source | What it says | What we took |
|---|---|---|
| López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. | Triple-barrier labels, sample uniqueness weights, purged and embargoed cross-validation, meta-labelling | **[tested]** `src/ml/labels.py` (triple barrier, uniqueness weights) and `src/ml/walkforward.py` (monthly walk-forward with an 8–11 day embargo). The triple-barrier filter scored AUC 0.37–0.47 vs a placebo of 0.52. Its "gain" equalled a constant half-size control. |
| Breiman, L. (2001). Random forests. *Machine Learning*. Friedman, J. (2001). Greedy function approximation: a gradient boosting machine. *Annals of Statistics*. | Random forests; gradient boosting; partial dependence plots | **[tested]** Direction models (AUC 0.40–0.51) and the HAR-residual volatility model. PDPs explain both (`reports/figures/ml_vol_pdp.png`). |
| Lundberg, S., Lee, S.-I. (2017). A unified approach to interpreting model predictions. *NeurIPS*. | SHAP values | **[tested]** The explainability requirement (PDF §5): `reports/figures/ml_vol_shap.png`, `ml_triple_barrier_shap.png`. The volatility model learned the same economics as notebook 02: downside semivariance raises the forecast. |
| Hanley, J., McNeil, B. (1982). The meaning and use of the area under a ROC curve. *Radiology*. | AUC and its standard error | **[tested]** Confidence intervals for the AUCs. ETH's random forest was significantly *worse* than chance (0.40, 95% CI 0.34–0.47). |
| Watkins, C., Dayan, P. (1992). Q-learning. *Machine Learning*. | Tabular Q-learning | **[tested]** Our agent lost about 79% (BTC) and 83% (ETH) across all seeds (ML research D). |
| Azar, M., Munos, R., Kappen, H. (2013). Minimax PAC bounds on the sample complexity of reinforcement learning with a generative model. *Machine Learning*. | How many samples RL needs | **[guide]** 64 states × 4 actions learned from 365 noisy rewards is far below the bound (BTC report M3.14). That explains the RL failure. |
| Jaquart, P., Dann, D., Weinhardt, C. (2021). Short-term bitcoin market prediction via machine learning. *Journal of Finance and Data Science*. | ML beats chance at 1–60 minutes, but trading it loses after costs | **[guide]** Confirmed our decision not to pursue high-frequency ML. |
| Akyildirim, E., Goncu, A., Sensoy, A. (2021). Prediction of cryptocurrency returns using machine learning. *Annals of Operations Research*. Fang, F. et al. (2022). Cryptocurrency trading: a comprehensive survey. *Financial Innovation*. | Surveys of crypto ML | **[background]** Feature choices for the ML study. |
| Gort, B. et al. (2022). Deep reinforcement learning for cryptocurrency trading: practical approach to address backtest overfitting. arXiv. | Deep RL crypto results often overfit | **[guide]** We tested only small, explainable RL with seeds and placebos, and reported the failure. |

## B9. Market structure and ETH-specific context

| Source | What it says | What we took |
|---|---|---|
| Kaiko research (2024). Why is ETH still lagging behind BTC?; Cointelegraph (2024). Three reasons why Ethereum price continues to underperform against BTC. | 2024 ETF flows favoured BTC; activity moved to Solana and Layer 2s | **[background]** Explains ETH's weak 2024 as structural, not a trend-signal failure (`tries/reports/research_turning_points.md`). |
| *Ethereum's proof-of-stake transition: inflation dynamics and …* (2025). *Finance Research Letters*. | A structural break after the Merge (Sept 2022) | **[background]** One reason ETH statistics before and after 2022 differ (ETH report). |
| Hedgeweek (2022). Trend followers turn leaders as CTAs deliver record returns. | Trend-following CTAs earned +27% in 2022 | **[background]** Industry confirmation that trend-following's value is in bear markets. |

---

**Scope:** only published research and public practitioner sources are listed. No other competition team's submission is cited here.
