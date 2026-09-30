"""Load the processed candle files."""
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def load_market(symbol: str, timeframe: str = "1h", split: str = "full") -> pd.DataFrame:
    """symbol: BTCUSDT / ETHUSDT, timeframe: 1h / 4h / 1d, split: full / train / val / test."""
    path = PROCESSED_DIR / timeframe / f"{symbol}_{split}.csv"
    return pd.read_csv(path, index_col="timestamp", parse_dates=True)
