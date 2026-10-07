"""Technical and volatility indicators, written in-house (no TA libraries).

Every function is causal: the value on bar t uses data up to bar t's close only.
Daily inputs need open/high/low/close/volume (and taker_buy_base, quote_volume where noted);
the "realised" functions turn hourly bars into one value per day.
Annualisation uses 365 days (crypto trades every day).
"""
import numpy as np
import pandas as pd

DAYS = 365


# ---------------------------------------------------------------- volatility estimators (annualised)
def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
                     axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average True Range with Wilder smoothing (in price units)."""
    return true_range(df).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()


def close_to_close_vol(close: pd.Series, n: int = 30) -> pd.Series:
    return np.log(close).diff().rolling(n).std() * np.sqrt(DAYS)


def parkinson_vol(df: pd.DataFrame, n: int = 30) -> pd.Series:
    """Uses the high-low range: ~5x more efficient than close-to-close for a driftless random walk."""
    hl = np.log(df["high"] / df["low"]) ** 2
    return np.sqrt(hl.rolling(n).mean() / (4 * np.log(2)) * DAYS)


def garman_klass_vol(df: pd.DataFrame, n: int = 30) -> pd.Series:
    hl = np.log(df["high"] / df["low"]) ** 2
    co = np.log(df["close"] / df["open"]) ** 2
    return np.sqrt((0.5 * hl - (2 * np.log(2) - 1) * co).rolling(n).mean() * DAYS)


def rogers_satchell_vol(df: pd.DataFrame, n: int = 30) -> pd.Series:
    """Robust to drift (trending markets), unlike Parkinson and Garman-Klass."""
    h, l, o, c = (np.log(df[k]) for k in ("high", "low", "open", "close"))
    rs = (h - c) * (h - o) + (l - c) * (l - o)
    return np.sqrt(rs.rolling(n).mean() * DAYS)


def yang_zhang_vol(df: pd.DataFrame, n: int = 30) -> pd.Series:
    """Combines overnight (open vs previous close), open-to-close and Rogers-Satchell parts."""
    o, c = np.log(df["open"]), np.log(df["close"])
    overnight = (o - c.shift(1)).rolling(n).var()
    open_close = (c - o).rolling(n).var()
    h, l = np.log(df["high"]), np.log(df["low"])
    rs = ((h - c) * (h - o) + (l - c) * (l - o)).rolling(n).mean()
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    return np.sqrt((overnight + k * open_close + (1 - k) * rs) * DAYS)


def rolling_percentile(x: pd.Series, window: int = 365, min_periods: int = 90) -> pd.Series:
    """Where today's value ranks within the trailing window (0 = lowest, 1 = highest). Causal."""
    return x.rolling(window, min_periods=min_periods).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)


def vol_of_vol(vol: pd.Series, n: int = 30) -> pd.Series:
    """Standard deviation of log-volatility changes: how unstable the volatility itself is."""
    return np.log(vol).diff().rolling(n).std()


# ---------------------------------------------------------------- volatility regime / compression
def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std()
    upper, lower = mid + k * sd, mid - k * sd
    return pd.DataFrame({"bb_mid": mid, "bb_upper": upper, "bb_lower": lower,
                         "bb_width": (upper - lower) / mid, "bb_pct_b": (close - lower) / (upper - lower)})


def keltner(df: pd.DataFrame, n: int = 20, m: float = 1.5) -> pd.DataFrame:
    mid = df["close"].ewm(span=n, adjust=False).mean()
    a = atr(df, n)
    return pd.DataFrame({"kc_mid": mid, "kc_upper": mid + m * a, "kc_lower": mid - m * a})


def squeeze(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """1 while the Bollinger Bands sit inside the Keltner Channel: unusually compressed volatility."""
    bb, kc = bollinger(df["close"], n), keltner(df, n)
    return ((bb["bb_upper"] < kc["kc_upper"]) & (bb["bb_lower"] > kc["kc_lower"])).astype(float)


# ---------------------------------------------------------------- trend versus chop
def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    """Wilder's Directional Movement: +DI, -DI and ADX (trend strength, direction-free)."""
    up, down = df["high"].diff(), -df["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = true_range(df).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / tr
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return pd.DataFrame({"plus_di": plus_di, "minus_di": minus_di, "adx": dx.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()})


def choppiness(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Choppiness Index (0-100): high = sideways chop, low = trending."""
    path = true_range(df).rolling(n).sum()
    span = df["high"].rolling(n).max() - df["low"].rolling(n).min()
    return 100 * np.log10(path / span) / np.log10(n)


def efficiency_ratio(close: pd.Series, n: int = 30) -> pd.Series:
    """|net move| / sum of |moves| over n bars: 1 = straight line, ~0 = pure back-and-forth."""
    return (close - close.shift(n)).abs() / close.diff().abs().rolling(n).sum()


def _hurst_rs(r: np.ndarray) -> float:
    """Rescaled-range Hurst estimate on one window of returns (chunk sizes 8..len/2)."""
    sizes, rs = [], []
    size = 8
    while size <= len(r) // 2:
        chunks = r[: len(r) // size * size].reshape(-1, size)
        dev = np.cumsum(chunks - chunks.mean(axis=1, keepdims=True), axis=1)
        s = chunks.std(axis=1)
        ok = s > 0
        if ok.any():
            sizes.append(size)
            rs.append(((dev.max(axis=1) - dev.min(axis=1))[ok] / s[ok]).mean())
        size *= 2
    return np.polyfit(np.log(sizes), np.log(rs), 1)[0] if len(sizes) >= 2 else np.nan


def rolling_hurst(close: pd.Series, window: int = 128) -> pd.Series:
    """> 0.5 trending (persistent), < 0.5 mean-reverting, ~0.5 random walk. Noisy on short windows."""
    r = np.log(close).diff()
    return r.rolling(window).apply(lambda w: _hurst_rs(w), raw=True)


def supertrend(df: pd.DataFrame, n: int = 10, m: float = 3.0) -> pd.Series:
    """+1 above the ATR trailing line, -1 below it (classic Supertrend direction)."""
    a = atr(df, n).to_numpy()
    hl2 = ((df["high"] + df["low"]) / 2).to_numpy()
    close = df["close"].to_numpy()
    upper, lower = hl2 + m * a, hl2 - m * a
    direction = np.zeros(len(close))
    fu, fl, d = np.nan, np.nan, 1.0
    for t in range(len(close)):
        if np.isnan(a[t]):
            continue
        fu = upper[t] if np.isnan(fu) or upper[t] < fu or close[t - 1] > fu else fu
        fl = lower[t] if np.isnan(fl) or lower[t] > fl or close[t - 1] < fl else fl
        if d == 1 and close[t] < fl:
            d = -1.0
        elif d == -1 and close[t] > fu:
            d = 1.0
        direction[t] = d
    return pd.Series(direction, index=df.index)


# ---------------------------------------------------------------- stretch (overbought / oversold)
def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def stoch_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    r = rsi(close, n)
    return (r - r.rolling(n).min()) / (r.rolling(n).max() - r.rolling(n).min())


def zscore(x: pd.Series, n: int = 50) -> pd.Series:
    return (x - x.rolling(n).mean()) / x.rolling(n).std()


def drawdown_from_high(close: pd.Series, n: int = 90) -> pd.Series:
    """How far below its n-day high the price is (0 = at the high, -0.3 = 30% below)."""
    return close / close.rolling(n, min_periods=1).max() - 1


# ---------------------------------------------------------------- flow and liquidity
def chaikin_money_flow(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Where closes land inside the day's range, volume-weighted: > 0 accumulation, < 0 distribution."""
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    mfv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / rng * df["volume"]
    return mfv.rolling(n).sum() / df["volume"].rolling(n).sum()


def relative_volume(df: pd.DataFrame, n: int = 30) -> pd.Series:
    """log(today's USDT volume / its trailing n-day median): > 0 busier than usual."""
    qv = df["quote_volume"]
    return np.log(qv / qv.rolling(n).median())


def taker_imbalance_z(df: pd.DataFrame, n: int = 30) -> pd.Series:
    """Z-score of the share of volume from aggressive buyers versus its own recent level."""
    return zscore(df["taker_buy_base"] / df["volume"], n)


def amihud(df: pd.DataFrame, n: int = 30) -> pd.Series:
    """Illiquidity: average |daily return| per $1M traded (higher = thinner market)."""
    illiq = np.log(df["close"]).diff().abs() / df["quote_volume"] * 1e6
    return illiq.rolling(n).mean()


# ---------------------------------------------------------------- realised measures from hourly bars
def realised_measures(hourly: pd.DataFrame) -> pd.DataFrame:
    """One row per UTC day from that day's hourly log returns.

    rv          realised variance (sum r^2)
    rs_up/down  realised semivariances (sum r^2 for r > 0 / r < 0)
    bv          bipower variation (pi/2 * sum |r_t||r_t-1|): robust to jumps
    jump_share  max(rv - bv, 0) / rv: share of the day's variance that came from jumps
    signed_jump (rs_up - rs_down) / rv: > 0 upside-dominated, < 0 downside-dominated variation
    rskew       realised skewness: sqrt(N) sum r^3 / rv^1.5
    rkurt       realised kurtosis: N sum r^4 / rv^2
    """
    r = np.log(hourly["close"]).diff()
    day = r.index.floor("1D")
    g = pd.DataFrame({"r": r, "r2": r ** 2, "r3": r ** 3, "r4": r ** 4,
                      "up2": r.clip(lower=0) ** 2, "dn2": r.clip(upper=0) ** 2,
                      "bp": r.abs() * r.abs().shift(1), "n": r.notna().astype(float)}).groupby(day)
    s = g.sum()
    rv = s["r2"]
    bv = np.pi / 2 * s["bp"]
    out = pd.DataFrame({
        "rv": rv, "rs_up": s["up2"], "rs_down": s["dn2"], "bv": bv,
        "jump_share": ((rv - bv).clip(lower=0) / rv),
        "signed_jump": (s["up2"] - s["dn2"]) / rv,
        "rskew": np.sqrt(s["n"]) * s["r3"] / rv ** 1.5,
        "rkurt": s["n"] * s["r4"] / rv ** 2,
    })
    out.index.name = "timestamp"
    return out


# ---------------------------------------------------------------- indicators from the cited reference report
# Inter IIT 13.0 Team 67 report (docs/references/): re-implemented here, causal versions only.
def atr_pct(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """ATR as a fraction of the open price (the report filters trades on ATR < 1% / > 2.5% of price, hourly)."""
    return atr(df, n) / df["open"]


def ema_ribbon(close: pd.Series, spans=(7, 14, 28)) -> pd.Series:
    """+1 if EMA7 > EMA14 > EMA28 (bullish order), -1 if EMA7 < EMA14 < EMA28, else 0."""
    e = [close.ewm(span=s, adjust=False).mean() for s in spans]
    return pd.Series(np.select([(e[0] > e[1]) & (e[1] > e[2]), (e[0] < e[1]) & (e[1] < e[2])], [1, -1], 0),
                     index=close.index).astype(float)


def aroon(df: pd.DataFrame, n: int = 25) -> pd.DataFrame:
    """Aroon up/down: how recently (in % of n bars) the n-bar high / low was set; oscillator = up - down."""
    up = df["high"].rolling(n + 1).apply(lambda w: w.argmax(), raw=True) / n * 100
    down = df["low"].rolling(n + 1).apply(lambda w: w.argmin(), raw=True) / n * 100
    return pd.DataFrame({"aroon_up": up, "aroon_down": down, "aroon_osc": up - down})


def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Heikin-Ashi candles (causal: each uses the current bar and the previous HA candle only).
    ha_close = (o+h+l+c)/4; ha_open = (prev ha_open + prev ha_close)/2. `ha_trend` = +1 green, -1 red;
    `ha_streak` = signed number of consecutive candles of the same colour."""
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    o = np.empty(len(df))
    o[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    hc = ha_close.to_numpy()
    for t in range(1, len(df)):
        o[t] = (o[t - 1] + hc[t - 1]) / 2
    trend = np.sign(hc - o)
    streak = np.zeros(len(df))
    for t in range(len(df)):
        streak[t] = trend[t] if t == 0 or trend[t] != trend[t - 1] else streak[t - 1] + trend[t]
    return pd.DataFrame({"ha_open": o, "ha_close": hc, "ha_trend": trend, "ha_streak": streak}, index=df.index)


def causal_gaussian(x: pd.Series, sigma: float = 5.0) -> pd.Series:
    """One-sided (causal) Gaussian smoother: weights exp(-k^2 / 2 sigma^2) on the current and PAST bars only.
    (A centred Gaussian filter, as in the report, uses future bars and is not allowed.)"""
    k = np.arange(int(3 * sigma) + 1)
    w = np.exp(-k ** 2 / (2 * sigma ** 2))
    w = w / w.sum()
    return x.rolling(len(w)).apply(lambda v: np.dot(v[::-1], w), raw=True)


def kalman_trend(close: pd.Series, q_over_r: float = 0.01) -> pd.DataFrame:
    """Causal Kalman local-level filter on log price: filtered level, its daily slope, and the
    deviation of price from the level in units of 30-day return volatility."""
    from src.ml.cusum import kalman_level
    log_p = np.log(close)
    level = kalman_level(log_p, q_over_r)
    vol = log_p.diff().rolling(30, min_periods=10).std()
    return pd.DataFrame({"kalman_level": np.exp(level), "kalman_slope": level.diff(),
                         "kalman_dev": (log_p - level) / vol}, index=close.index)


def cusum_state(close: pd.Series) -> pd.Series:
    """CUSUM regime on the Kalman reference: 1 bullish, 0 bearish (see src/ml/cusum.py)."""
    from src.ml.cusum import cusum_regime
    return cusum_regime(close)


def rolling_corr_hourly(hourly_a: pd.DataFrame, hourly_b: pd.DataFrame, hours: int = 168) -> pd.Series:
    """Correlation of the two coins' hourly returns over the last `hours` hours, sampled at each day's
    last hour (so the daily value is known at the day's close)."""
    ra, rb = np.log(hourly_a["close"]).diff(), np.log(hourly_b["close"]).diff()
    corr = ra.rolling(hours, min_periods=hours // 2).corr(rb.reindex(ra.index))
    return corr.groupby(corr.index.floor("1D")).last()


def markov_switching_prob(returns: pd.Series, first_fit_days: int = 180) -> pd.Series:
    """P(high-variance regime) from a 2-regime Markov-switching model (statsmodels, switching mean and
    variance). Refit at each year start on data up to the previous day; FILTERED probabilities only."""
    import warnings
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
    r = returns.dropna() * 100
    out = pd.Series(np.nan, index=returns.index)
    starts = [r.index[first_fit_days]] + [d for d in pd.date_range(r.index[0], r.index[-1], freq="YS", tz=r.index.tz)
                                          if d > r.index[first_fit_days]]
    starts.append(r.index[-1] + pd.Timedelta(days=1))
    for a, b in zip(starts[:-1], starts[1:]):
        train = r[r.index < a]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = MarkovRegression(train, k_regimes=2, switching_variance=True).fit(disp=False)
            upto = r[r.index < b]
            filt = MarkovRegression(upto, k_regimes=2, switching_variance=True).filter(fit.params).filtered_marginal_probabilities
        high = int(np.argmax([fit.params[f"sigma2[{i}]"] for i in range(2)]))
        part = filt.iloc[:, high] if hasattr(filt, "iloc") else pd.Series(filt[:, high], index=upto.index)
        out[part.index[part.index >= a]] = part[part.index >= a].to_numpy()
    return out


def vol_clusters(features: pd.DataFrame, k: int = 3, first_fit_days: int = 180) -> pd.Series:
    """PCA + K-means volatility clusters (the report's experiment), refit at each year start on past data only.
    Clusters are relabelled 0 = calmest ... k-1 = most volatile by their mean of the first feature."""
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    X = features.dropna()
    out = pd.Series(np.nan, index=features.index)
    starts = [X.index[first_fit_days]] + [d for d in pd.date_range(X.index[0], X.index[-1], freq="YS", tz=X.index.tz)
                                          if d > X.index[first_fit_days]]
    starts.append(X.index[-1] + pd.Timedelta(days=1))
    for a, b in zip(starts[:-1], starts[1:]):
        train, test = X[X.index < a], X[(X.index >= a) & (X.index < b)]
        scaler = StandardScaler().fit(train)
        pca = PCA(n_components=2).fit(scaler.transform(train))
        km = KMeans(k, n_init=10, random_state=0).fit(pca.transform(scaler.transform(train)))
        order = np.argsort([train.iloc[km.labels_ == c, 0].mean() for c in range(k)])
        relabel = {c: i for i, c in enumerate(order)}
        labels = km.predict(pca.transform(scaler.transform(test)))
        out[test.index] = [relabel[c] for c in labels]
    return out
