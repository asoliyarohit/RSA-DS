"""Pooled walk-forward on single stocks. One param set for ALL tickers (fewer degrees of freedom),
top-N strongest signals per slot (risk is shared), t-stat measured on per-slot averages (no double counting)."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from . import data, features
from .cfd import CFDSpec
from .search import SPLIT
from .strategies import CloseParams, OpenParams, _direction_close, _direction_open, trades_close, trades_open

# Fixed in advance, NOT picked for having won: includes laggards. Still survivorship-biased (no delisted names).
STOCKS = ["AMD", "META", "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "NFLX", "MU", "QCOM", "ADBE", "CRM",
          "INTC", "BA", "GE", "F", "GM", "IBM", "T", "XOM", "CVX", "JPM", "BAC", "C", "DIS", "NKE", "PYPL", "CSCO", "ORCL", "WBA", "KHC"]
STOCK_CFD = CFDSpec(spread_bps=10.0, slippage_bps=3.0, leverage=5.0, benchmark=0.04, markup=0.03, commission_bps=25.0)
TOP_N = 3


def load_frames(refresh=False):
    vix = data.load(data.VIX, refresh=refresh)["close"]
    out = {}
    for s in STOCKS:
        try:
            out[s] = features.build(data.load(s, refresh=refresh), vix)
        except Exception as e:  # missing ticker should not kill the scan
            print(f"skip {s}: {e}")
    return out


def _score(f, setup, p):
    if setup == "OPEN":
        return np.abs(f["gap_atr_o"].to_numpy())
    return np.abs((f["ibs_c"] if p.mode == "ibs" else f["rsi2_c"] / 100).to_numpy() - 0.5)


def pooled_trades(frames, setup, p, cfd):
    fn = trades_open if setup == "OPEN" else trades_close
    parts = []
    for sym, f in frames.items():
        t = fn(f, p, cfd, sym)
        if t.empty:
            continue
        sc = pd.Series(_score(f, setup, p), index=f.index)
        t["score"] = sc.reindex(t["date"]).to_numpy()
        parts.append(t)
    if not parts:
        return pd.DataFrame()
    t = pd.concat(parts)
    t = t.sort_values(["slot", "score"], ascending=[True, False]).groupby("slot").head(TOP_N)
    return t.sort_values("slot").reset_index(drop=True)


def slot_t(t):
    r = t.groupby("slot")["ret"].mean()
    return float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 5 and r.std() > 0 else -9.0


def grid(setup):
    if setup == "OPEN":
        for m, g, tr, bs, st in itertools.product(["fade", "follow"], [0.5, 1.0, 1.5, 2.0, 3.0], [True, False], [False, True], [1.0, 1.5, 2.5]):
            yield OpenParams(mode=m, gap_atr=g, trend=tr, both_sides=bs, stop_atr=st)
    else:
        for m, t, tr, bs in itertools.product(["ibs", "rsi2"], [0.1, 0.2, 0.3], [True, False], [False, True]):
            yield CloseParams(mode=m, thr=t, trend=tr, both_sides=bs, stress_atr=2.5)


def walk_forward(frames, setup, cfd=STOCK_CFD, min_slots=100):
    best, best_t, n = None, -9.0, 0
    for p in grid(setup):
        n += 1
        t = pooled_trades(frames, setup, p, cfd)
        tr = t[t["date"] < SPLIT]
        if tr["slot"].nunique() < min_slots:
            continue
        s = slot_t(tr)
        if s > best_t:
            best, best_t = p, s
    t = pooled_trades(frames, setup, best, cfd)
    tr, te = t[t["date"] < SPLIT], t[t["date"] >= SPLIT]
    return {"setup": setup, "params": best, "grid": n, "train_t": round(best_t, 2),
            "train_slots": int(tr["slot"].nunique()), "train_avg_bps": round(tr["ret"].mean() * 1e4, 1),
            "test_slots": int(te["slot"].nunique()), "test_avg_bps": round(te["ret"].mean() * 1e4, 1),
            "test_t": round(slot_t(te), 2), "test_win": round(float((te["ret"] > 0).mean()), 3),
            "test_worst_bps": round(te["ret"].min() * 1e4, 0), "trades": t}
