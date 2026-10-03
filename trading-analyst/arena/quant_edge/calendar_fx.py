"""Round 4 (exploration, counted): calendar flow effects. TOM overnight per instrument; pre-holiday slots."""
import numpy as np, pandas as pd
from arena.quant_edge.hyp import *  # noqa

idx = C.index
nxt = pd.Series(np.r_[idx[1:], [pd.NaT]], index=idx)
last_of_month = (nxt.dt.month != idx.month) & nxt.notna()
nights = (nxt - pd.Series(idx, index=idx)).dt.days
pre_hol = ((idx.weekday == 4) & (nights > 3)) | ((idx.weekday < 4) & (nights > 1))
for per, sel in (("train", idx <= TRAIN_END), ("valid", idx > TRAIN_END)):
    for name, m in (("TOM-1", last_of_month.values), ("preHol", pre_hol.values)):
        on = R["on_gross"][m & sel]; idd = R["id_gross"][m & sel]
        print(per, name, "n=", int((m & sel).sum()),
              "ETF on/id gross bps:", {e: (round(on[e].mean() * 1e4, 1), round(idd[e].mean() * 1e4, 1)) for e in ETFS})
        print("   stocks on gross mean", round(on[STOCKS].mean().mean() * 1e4, 1), "id", round(idd[STOCKS].mean().mean() * 1e4, 1),
              " frac stocks on>18bps", round((on[STOCKS].mean() > 18e-4).mean(), 2))
