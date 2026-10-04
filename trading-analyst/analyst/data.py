"""Free daily data via yfinance (index levels = what index CFDs track), cached on disk."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Yahoo symbol -> typical broker CFD name
INSTRUMENTS = {"SPY": "US500", "QQQ": "US100"}  # ETFs: real 9:30 opening prints (Yahoo index opens are stale pre-2014)
VIX = "^VIX"


def _download(symbol: str, start: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(symbol, start=start, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].rename(columns=str.lower).dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "date"
    return df


def load(symbol: str, start: str = "2000-01-01", refresh: bool = False) -> pd.DataFrame:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{symbol.strip('^').lower()}_1d.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path, index_col="date", parse_dates=True)
    df = _download(symbol, start)
    if df.empty:
        raise RuntimeError(f"no data returned for {symbol}")
    df.to_csv(path)
    return df
