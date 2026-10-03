"""Dev-only research harness: evaluates each pre-registered hypothesis with the JUDGE's own fills() on data <= 2022-12-31.
python -m arena.commodity_ls.research [MODE ...]"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from arena import judge
from arena.commodity_ls import strategy as S

CUT = pd.Timestamp("2022-12-31")


def load():
    fr = judge.load_frames(S.UNIVERSE)
    return {k: v[v.index <= CUT] for k, v in fr.items()}


def tstat(x):
    x = pd.Series(x)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else 0.0


def summarize(t: pd.DataFrame, label: str):
    sl = t.groupby("slot").agg(ret=("ret", "mean"), date=("date", "first"))
    des, val = sl[sl.date < "2016-01-01"], sl[sl.date >= "2016-01-01"]
    print(f"{label:10s} slots={len(sl)} avg={sl.ret.mean()*1e4:6.1f}bp t={tstat(sl.ret):5.2f} | design 08-15 n={len(des)} "
          f"{des.ret.mean()*1e4:6.1f}bp t={tstat(des.ret):5.2f} | valid 16-22 n={len(val)} {val.ret.mean()*1e4:6.1f}bp t={tstat(val.ret):5.2f} "
          f"| win={(t.ret>0).mean():.3f} stophit={(t.ret <= -(t.stop_pct + 0.0012) + 1e-9).mean():.2f}")
    return sl


def per_year(sl):
    g = sl.groupby(sl.date.dt.year)["ret"]
    return pd.DataFrame({"n": g.size(), "bps": (g.mean() * 1e4).round(1), "t": g.apply(tstat).round(2)})


def regime(sl, frames):
    """Bear regime = equal-weight roll-free commodity index more than 20% below its 252d high (causal: as of t-1)."""
    df = S.build(frames)
    rf = df.pivot(index="date", columns="instrument", values="rev1") * df.pivot(index="date", columns="instrument", values="sig")
    idx = rf.mean(axis=1).fillna(0).cumsum()
    dd = (idx - idx.rolling(252, min_periods=60).max())  # log drawdown, already lagged (features are shifted)
    bear = dd < np.log(0.8)
    b = bear.reindex(sl.date.values).fillna(False).values
    cl = df[df.instrument == "BZ=F"].set_index("date")
    clp = (cl["rev1"] * cl["sig"]).fillna(0).cumsum()
    cl_bear = (clp - clp.rolling(252, min_periods=60).max()) < np.log(0.5)
    c = cl_bear.reindex(sl.date.values).fillna(False).values
    out = {}
    for name, m in (("commodity_bear(<-20%)", b), ("not_bear", ~b), ("oil_down>50%", c)):
        x = sl.ret[m]
        out[name] = (int(m.sum()), round(float(x.mean() * 1e4), 1) if len(x) else None, round(tstat(x), 2))
    return out


if __name__ == "__main__":
    frames = load()
    modes = sys.argv[1:] or ["H1", "H2", "H3", "H4", "H5", "H6"]
    for md in modes:
        sig = S.signals_for(frames, md)
        t = judge.fills(sig, frames)
        sl = summarize(t, md)
        if "-v" in sys.argv or len(modes) == 1:
            print(per_year(sl).T.to_string())
            print(regime(sl, frames))
            print(t.groupby("instrument")["ret"].agg(["size", lambda x: x.mean() * 1e4]).round(1).T.to_string())
