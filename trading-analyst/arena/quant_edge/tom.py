"""Round 5 (counted): turn-of-month overnight, judge cost model. Two pre-declared variants only."""
import numpy as np, pandas as pd
from arena.quant_edge.hyp import *  # noqa
from arena.quant_edge.strategy import is_last_trading_day_of_month

idx = C.index
tom = pd.Series([is_last_trading_day_of_month(d) for d in idx], index=idx)
nxt = pd.Series(np.r_[idx[1:], [pd.NaT]], index=idx)
truth = (nxt.dt.month != idx.month) & nxt.notna()
print("calendar mismatches vs realised index:", list(idx[(tom != truth) & nxt.notna()].date))
M = pd.DataFrame(np.repeat(tom.values[:, None], C.shape[1], 1), index=idx, columns=C.columns)
EQ = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU"]
core = pd.DataFrame(False, index=idx, columns=C.columns); core[["SPY", "QQQ", "IWM"]] = True
eqm = pd.DataFrame(False, index=idx, columns=C.columns); eqm[EQ] = True
for name, m, sc in (("A TOM SPY/QQQ/IWM", M & core & ok, -ibs), ("B TOM 12 equity ETFs, top3 lowest IBS", M & eqm & ok, -ibs)):
    out, yr, sl = slot_stats(m, sc, R["on_long"])
    print(name, out, "yrs+:", round((yr["mean"] > 0).mean(), 2))
    print((yr["mean"] * 1e4).round(0).astype(int).to_dict())
