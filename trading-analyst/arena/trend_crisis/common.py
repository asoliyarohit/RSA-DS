"""Shared dev-data loader for trend_crisis research. HARD CUT at 2022-12-31: nothing after it is ever returned."""
from __future__ import annotations
import sys
import numpy as np, pandas as pd
sys.path.insert(0, ".")
from analyst import data
from arena.judge import cost_for

CUTOFF = pd.Timestamp("2022-12-31")
INDICES = ["SPY", "QQQ", "DIA", "EWG", "FEZ", "EWJ", "EWU"]                    # major index tier, 20x, 4 bps rt
COMMOD = ["GC=F", "GLD", "CL=F", "BZ=F", "NG=F", "SI=F", "HG=F"]                 # gold 20x 7bps; others 10x 12 bps
STOCKS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "XOM", "JNJ", "PG", "UNH", "HD", "BAC", "PFE", "KO",
          "WMT", "CVX", "INTC", "CSCO", "DIS", "BA", "CAT", "GS", "IBM", "MRK", "WFC", "C", "GE", "T"]  # 5x, 66 bps rt
AUX = ["^VIX", "^VIX3M"]
CANDIDATES = INDICES + COMMOD + STOCKS + AUX


def load_dev(tickers=CANDIDATES):
    fr = {}
    for t in tickers:
        try:
            d = data.load(t)
        except Exception as e:
            print("skip", t, e, file=sys.stderr); continue
        fr[t] = d[d.index <= CUTOFF].copy()
    return fr


def rt_cost(t):
    c = cost_for(t); return c.round_trip_cost(), c.leverage, c
