"""E1. CUSUM regime detector on a causal Kalman reference (method from the cited Inter IIT 13.0 Team 67
report, re-implemented under our rules; protocol v9b §15b-E).

Kalman: local-level model on log price, filtered (causal) estimate only.
CUSUM:  S_hi = max(0, S_hi + d - k), S_lo = max(0, S_lo - d - k), d = log price - reference,
        k = 0.5 sigma, h = 4 sigma, sigma = 30-day std of daily log returns.
State:  1 after S_hi > h (bullish), 0 after S_lo > h (bearish); both sums reset after a signal.
"""
import numpy as np
import pandas as pd

Q_OVER_R, K_MULT, H_MULT = 0.01, 0.5, 4.0


def kalman_level(x: pd.Series, q_over_r: float = Q_OVER_R) -> pd.Series:
    """Causal Kalman filter for a random-walk level observed with noise (observation variance set to 1)."""
    v = x.to_numpy()
    level, p = v[0], 1.0
    out = np.empty(len(v))
    for t, obs in enumerate(v):
        p += q_over_r                          # predict
        gain = p / (p + 1.0)
        level += gain * (obs - level)          # update with today's observation only
        p *= 1 - gain
        out[t] = level
    return pd.Series(out, index=x.index)


def cusum_regime(close: pd.Series) -> pd.Series:
    log_p = np.log(close)
    d = (log_p - kalman_level(log_p)).to_numpy()
    sigma = log_p.diff().rolling(30, min_periods=10).std().to_numpy()
    s_hi = s_lo = 0.0
    state, out = np.nan, np.full(len(d), np.nan)
    for t in range(len(d)):
        if np.isnan(sigma[t]):
            continue
        k, h = K_MULT * sigma[t], H_MULT * sigma[t]
        s_hi = max(0.0, s_hi + d[t] - k)
        s_lo = max(0.0, s_lo - d[t] - k)
        if s_hi > h:
            state, s_hi, s_lo = 1.0, 0.0, 0.0
        elif s_lo > h:
            state, s_hi, s_lo = 0.0, 0.0, 0.0
        out[t] = state
    return pd.Series(out, index=close.index)
