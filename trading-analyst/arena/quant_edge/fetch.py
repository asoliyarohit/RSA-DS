"""Warm the data cache (uses analyst.data.load exactly like the judge). Research never reads past 2022-12-31."""
import sys, time
from analyst import data
from arena.quant_edge.universe import UNIVERSE

for t in UNIVERSE + ["^VIX"]:
    for k in range(3):
        try:
            d = data.load(t); print(t, len(d), d.index[0].date(), flush=True); break
        except Exception as e:
            print("retry", t, e, file=sys.stderr); time.sleep(2)
