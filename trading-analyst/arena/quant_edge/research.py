"""Research harness (dev data only, <= 2022-12-31). Builds date x ticker panels and evaluates
pre-registered cross-sectional rules with the judge's exact cost model. Every call to `evaluate` = 1 trial."""
from __future__ import annotations

import numpy as np
import pandas as pd

from analyst import data
from arena.judge import cost_for, CUTOFF
from arena.quant_edge.universe import UNIVERSE, ETFS, STOCKS

TRAIN_END = pd.Timestamp("2016-12-31")


def panels():
    fr = {t: data.load(t) for t in UNIVERSE + ["^VIX"]}
    fr = {t: f[f.index <= CUTOFF] for t, f in fr.items()}
    idx = fr["SPY"].index
    P = {k: pd.DataFrame({t: f[k].reindex(idx) for t, f in fr.items() if t != "^VIX"}) for k in ("open", "high", "low", "close")}
    P["vix"] = fr["^VIX"]["close"].reindex(idx).ffill()
    return P


def forward_returns(P):
    """Net per-notional returns exactly as the judge books them (without stops)."""
    O, C = P["open"], P["close"]
    idx = C.index
    nights = pd.Series(np.r_[(idx[1:] - idx[:-1]).days, np.nan], index=idx)
    cost = pd.Series({t: cost_for(t).round_trip_cost() for t in C.columns})
    fin_long = pd.Series({t: -(cost_for(t).benchmark + cost_for(t).markup) for t in C.columns})
    fin_short = pd.Series({t: (cost_for(t).benchmark - cost_for(t).markup) for t in C.columns})
    on_gross = O.shift(-1) / C - 1
    id_gross = C / O - 1
    n = nights.values[:, None] / 365.0
    out = {}
    out["on_long"] = on_gross - cost + n * fin_long.values
    out["on_short"] = -on_gross - cost + n * fin_short.values
    out["id_long"] = id_gross - cost
    out["id_short"] = -id_gross - cost
    out["on_gross"], out["id_gross"] = on_gross, id_gross
    return out


def atr_pct(P, n=14):
    H, L, C = P["high"], P["low"], P["close"]
    pc = C.shift()
    tr = np.maximum(H - L, np.maximum((H - pc).abs(), (L - pc).abs()))
    return tr.rolling(n).mean() / C


def slot_stats(mask, score, R, top=3, label=""):
    """mask/score/R: date x ticker. Keep top-`top` by score per date, average per slot (judge's rule)."""
    s = score.where(mask)
    rk = s.rank(axis=1, ascending=False, method="first")
    sel = rk <= top
    r = R.where(sel)
    sl = r.mean(axis=1).dropna()
    out = {}
    for name, part in (("train", sl[sl.index <= TRAIN_END]), ("valid", sl[sl.index > TRAIN_END]), ("all", sl)):
        if len(part) < 10:
            out[name] = (len(part), np.nan, np.nan); continue
        t = part.mean() / (part.std(ddof=1) / np.sqrt(len(part)))
        out[name] = (len(part), round(part.mean() * 1e4, 1), round(t, 2))
    yr = sl.groupby(sl.index.year).agg(["count", "mean"])
    return out, yr, sl
