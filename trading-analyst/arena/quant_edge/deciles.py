"""Round 2 (exploration, counted in N_TRIALS): gross forward return by feature decile x VIX regime, stocks only.
Purpose: find where gross magnitude could clear the 16-18 bps stock round trip."""
import sys
import numpy as np, pandas as pd
from arena.quant_edge.hyp import *  # noqa

vixr = pd.cut(P["vix"], [0, 20, 30, 200], labels=["vix<20", "20-30", ">30"])
FEATS = {"z1->on": (z1, R["on_gross"]), "zid->on": (zid, R["on_gross"]), "ibs->on": (ibs, R["on_gross"]),
         "zg->id": (zg, R["id_gross"]), "rngpos->on": (rng_pos, R["on_gross"])}
for name, (f, y) in FEATS.items():
    f = f[STOCKS]; y = y[STOCKS]
    dec = f.rank(axis=1, pct=True).mul(10).clip(upper=9.999).apply(np.floor)
    for per, sel in (("train", f.index <= TRAIN_END), ("valid", f.index > TRAIN_END)):
        rows = {}
        for reg in vixr.cat.categories:
            m = (vixr == reg).values & sel
            s = pd.DataFrame({"d": dec[m].stack(), "y": y[m].stack()}).dropna()
            rows[reg] = (s.groupby("d")["y"].mean() * 1e4).round(1)
        print(name, per); print(pd.DataFrame(rows).T.to_string())
