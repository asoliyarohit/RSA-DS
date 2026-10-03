"""Gamma-conditioned index OPEN trade (council H1, pre-registered, N_TRIALS=2, thresholds NOT tuned).
GEX = SqueezeMetrics dealer gamma exposure, daily, computed after each close. We only ever use the value dated BEFORE the trade day.
 Trial 1: previous GEX < 0 (dealers short gamma => moves amplified): FOLLOW the opening gap, any size, stop 1.5 ATR, exit close.
 Trial 2: previous GEX >= 0 and |gap| >= 0.5 ATR (dealers dampen): FADE the gap, stop 1.5 ATR, exit close.
Kill criteria (pre-registered): dev t < 2 or < 8 bps net => dead, holdout never run."""
import io
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

UNIVERSE = ["SPY", "QQQ"]
N_TRIALS = 2
URL = "https://squeezemetrics.com/monitor/static/DIX.csv"
CACHE = Path(__file__).resolve().parents[2] / "data" / "gex.csv"


def _gex() -> pd.Series:
    if CACHE.exists():
        d = pd.read_csv(CACHE, parse_dates=["date"])
    else:
        raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        d = pd.read_csv(io.BytesIO(raw), parse_dates=["date"]); CACHE.parent.mkdir(exist_ok=True); d.to_csv(CACHE, index=False)
    return d.set_index("date")["gex"]


def signals(frames):
    gex = _gex()
    rows = []
    for s in UNIVERSE:
        f = frames[s]
        pc = f["close"].shift(1)
        tr = pd.concat([f["high"] - f["low"], (f["high"] - pc).abs(), (f["low"] - pc).abs()], axis=1).max(axis=1)
        atr = (tr.rolling(14).mean() / f["close"]).shift(1)              # known at the open
        gap = f["open"] / pc - 1
        gap_atr = gap / atr
        prev_gex = gex.reindex(f.index.union(gex.index)).sort_index().shift(1).reindex(f.index)   # strictly previous value
        prev_gex = prev_gex.ffill()
        t1 = (prev_gex < 0) & gap.ne(0) & atr.notna()
        t2 = (prev_gex >= 0) & (gap_atr.abs() >= 0.5) & atr.notna()
        for d in f.index[t1.fillna(False)]:
            rows.append((s, d, "OPEN", int(np.sign(gap[d])), 1.5 * float(atr[d]), abs(float(gap_atr[d]))))
        for d in f.index[t2.fillna(False)]:
            rows.append((s, d, "OPEN", -int(np.sign(gap[d])), 1.5 * float(atr[d]), abs(float(gap_atr[d]))))
    return pd.DataFrame(rows, columns=["instrument", "date_in", "kind", "dir", "stop_pct", "score"])
