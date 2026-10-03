"""Round 3 (exploration, counted): ETFs only (4 bps round trip). Gross overnight/intraday by IBS bucket x VIX regime,
and turn-of-month (TOM) calendar effect per slot."""
import numpy as np, pandas as pd
from arena.quant_edge.hyp import *  # noqa

E = [e for e in ETFS]
vixr = pd.cut(P["vix"], [0, 20, 30, 200], labels=["vix<20", "20-30", ">30"])
ib = pd.cut(ibs[E].stack(), [-.01, .1, .2, .5, .8, .9, 1.01]).unstack()
for per, sel in (("train", C.index <= TRAIN_END), ("valid", C.index > TRAIN_END)):
    rows = {}
    for reg in vixr.cat.categories:
        m = (vixr == reg).values & sel
        s = pd.DataFrame({"b": ib[m].stack(), "y": R["on_gross"][E][m].stack()}).dropna()
        rows[reg] = (s.groupby("b", observed=True)["y"].agg(["mean", "count"]).assign(mean=lambda d: (d["mean"] * 1e4).round(1)))["mean"]
    print("ETF ibs->on gross", per); print(pd.DataFrame(rows).T.to_string())

# turn of month: trading-day index within month, from start (1..) and from end (-1..)
d = pd.Series(C.index, index=C.index)
ym = C.index.to_period("M")
k_start = d.groupby(ym).cumcount() + 1
k_end = -(d.groupby(ym).cumcount(ascending=False) + 1)
tom = pd.Series(np.where(k_end >= -4, k_end, np.where(k_start <= 5, k_start, 0)), index=C.index)
for per, sel in (("train", C.index <= TRAIN_END), ("valid", C.index > TRAIN_END)):
    on = R["on_gross"][["SPY", "QQQ", "IWM"]].mean(axis=1)[sel]
    idd = R["id_gross"][["SPY", "QQQ", "IWM"]].mean(axis=1)[sel]
    t = pd.DataFrame({"on": on.groupby(tom[sel]).mean() * 1e4, "id": idd.groupby(tom[sel]).mean() * 1e4,
                      "n": on.groupby(tom[sel]).count()}).round(1)
    print("TOM gross (SPY/QQQ/IWM avg) by day-of-month code", per); print(t.T.to_string())
