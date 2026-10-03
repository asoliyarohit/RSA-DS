"""Indicators. Every column is tagged by WHEN it is known:
  *_c  -> known at the close of day t (usable for the near-close entry)
  *_o  -> known at the open of day t (built only from day t-1 and earlier + today's open)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, n: int = 2) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def build(df: pd.DataFrame, vix: pd.Series | None = None) -> pd.DataFrame:
    f = df.copy()
    pc = f["close"].shift(1)
    tr = pd.concat([f["high"] - f["low"], (f["high"] - pc).abs(), (f["low"] - pc).abs()], axis=1).max(axis=1)
    f["atr_c"] = tr.rolling(14).mean() / f["close"]          # ATR as % of price, through close t
    f["sma200_c"] = f["close"].rolling(200).mean()
    f["trend_c"] = np.sign(f["close"] - f["sma200_c"])        # +1 up / -1 down at close t
    rng = (f["high"] - f["low"]).replace(0, np.nan)
    f["ibs_c"] = (f["close"] - f["low"]) / rng
    f["rsi2_c"] = rsi(f["close"], 2)
    # known at open of day t: previous-day values + today's gap
    f["gap_o"] = f["open"] / pc - 1
    f["atr_o"] = f["atr_c"].shift(1)
    f["trend_o"] = f["trend_c"].shift(1)
    f["gap_atr_o"] = f["gap_o"] / f["atr_o"]
    if vix is not None:
        v = vix.reindex(f.index).ffill()
        f["vix_c"] = v
        f["vix_o"] = v.shift(1)
    return f
