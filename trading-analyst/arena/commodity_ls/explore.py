"""Post-kill exploratory variants (each counted in N_TRIALS). Dev data only. python -m arena.commodity_ls.explore"""
import numpy as np
import pandas as pd

from arena import judge
from arena.commodity_ls import research as R
from arena.commodity_ls import strategy as S

fr = R.load()
for md in ["H1", "H2", "H3", "H4", "H5", "H6"]:  # gross edge context (no new trial)
    t = judge.fills(S.signals_for(fr, md), fr)
    cost = np.where(t.instrument == "GLD", 7, 12)
    print(md, "gross bp/trade", round(((t.ret * 1e4) + cost).mean(), 1))
# H7: continuation after extreme day (H2 flipped)
sig = S.signals_for(fr, "H2"); sig["dir"] *= -1
R.summarize(judge.fills(sig, fr), "H7 cont")
# H8: H1 with a 3-sigma stop
S.STOP_K = 3.0
R.summarize(judge.fills(S.signals_for(fr, "H1"), fr), "H8 H1stop3")
S.STOP_K = 1.5
# H9 / H10: gold overnight long (CLOSE) / gold intraday short (OPEN), every day (documented 'gold night effect')
g = fr["GLD"]; g = g[g.index >= "2008-01-01"]
for name, kind, d in (("H9 GLDnight+", "CLOSE", 1), ("H10 GLDday-", "OPEN", -1)):
    s = pd.DataFrame({"instrument": "GLD", "date_in": g.index, "kind": kind, "dir": d, "stop_pct": 0.02, "score": 1.0})
    sl = R.summarize(judge.fills(s, fr), name)
    print(R.per_year(sl).T.to_string())
