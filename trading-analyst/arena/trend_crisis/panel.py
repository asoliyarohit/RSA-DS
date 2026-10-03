"""Build the per-instrument daily panel used by every research step (dev data only).

For each instrument and day d:
  on_ret   : CLOSE slot gross return, long  = open[d+1]/close[d]-1      (decision made at close d, info <= close d)
  in_ret   : OPEN  slot gross return, long  = close[d]/open[d]-1        (decision made at open d, info <= close d-1 + open d)
  signals suffixed _c are computed from closes up to and including d (valid for the CLOSE slot of d, and for OPEN slot of d+1
  after shifting). Signals used for OPEN on d are the _c values shifted by one day (= known at close d-1), plus gap_d.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from arena.trend_crisis.common import *

LOOKS = (21, 63, 126, 252)


def feats(f: pd.DataFrame, vix: pd.Series | None = None, vix3m: pd.Series | None = None) -> pd.DataFrame:
    f = f[(f[["open", "high", "low", "close"]] > 0).all(axis=1)].copy()
    c, o, h, l = f["close"], f["open"], f["high"], f["low"]
    r = np.log(c).diff()
    out = pd.DataFrame(index=f.index)
    out["on_ret"] = o.shift(-1) / c - 1
    out["nights"] = (pd.Series(f.index, index=f.index).shift(-1) - pd.Series(f.index, index=f.index)).dt.days
    out["in_ret"] = c / o - 1
    out["gap"] = o / c.shift(1) - 1
    out["high_r"] = h / o - 1; out["low_r"] = l / o - 1              # for stop evaluation on OPEN slots
    vol = r.ewm(span=32, min_periods=20).std()
    out["vol_c"] = vol
    out["vol_long_c"] = r.rolling(252, min_periods=120).std()
    for L in LOOKS:
        out[f"z{L}_c"] = (c / c.shift(L) - 1) / (vol * np.sqrt(L))
    out["z252x21_c"] = (c.shift(21) / c.shift(252) - 1) / (vol * np.sqrt(231))      # 12-1 month
    out["ma200_c"] = np.sign(c / c.rolling(200).mean() - 1)
    out["ma50_c"] = np.sign(c / c.rolling(50).mean() - 1)
    # EMA crossover trend (Baz et al 2015 style), 3 speeds, normalised by price vol
    for s, lng in ((8, 24), (16, 48), (32, 96)):
        x = (c.ewm(span=s).mean() - c.ewm(span=lng).mean()) / (c.rolling(63).std())
        out[f"ema{s}_c"] = x
    out["dd_c"] = c / c.rolling(252, min_periods=60).max() - 1                     # drawdown from 1y high
    out["ibs_c"] = ((c - l) / (h - l).replace(0, np.nan)).fillna(0.5)
    out["r1_c"] = r
    out["r5_c"] = np.log(c).diff(5)
    if vix is not None:
        v = vix.reindex(f.index).ffill()
        out["vix_c"] = v
        out["vix_ma_c"] = v / v.rolling(63).mean()
        if vix3m is not None:
            out["vterm_c"] = v / vix3m.reindex(f.index).ffill()
    return out


def build(fr: dict, tickers) -> pd.DataFrame:
    vix = fr["^VIX"]["close"]; vix3m = fr["^VIX3M"]["close"] if "^VIX3M" in fr else None
    parts = []
    for t in tickers:
        if t not in fr:
            continue
        p = feats(fr[t], vix, vix3m); p["inst"] = t
        rt, lev, cfd = rt_cost(t)
        p["rt"] = rt; p["lev"] = lev
        p["fin_long"] = -(cfd.benchmark + cfd.markup) * p["nights"] / 365
        p["fin_short"] = (cfd.benchmark - cfd.markup) * p["nights"] / 365
        p["cls"] = "index" if t in INDICES else "stock" if t in STOCKS else "gold" if t in ("GC=F", "GLD") else "commod"
        parts.append(p.reset_index())
    return pd.concat(parts, ignore_index=True)


def breadth(fr: dict, tickers) -> pd.Series:
    """Fraction of index ETFs above their 200d MA, as of each close (causal)."""
    cols = {}
    for t in tickers:
        c = fr[t]["close"]; cols[t] = (c > c.rolling(200).mean()).astype(float).where(c.rolling(200).mean().notna())
    return pd.DataFrame(cols).mean(axis=1)
