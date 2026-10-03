"""Research harness and research log for ml_cross (dev data only, <= 2022-12-31). Every variant is counted in N_TRIALS.

RESEARCH LOG
Verdict: the judge's --dev run says VALID EDGE (t 4.36, DSR 0.996). That edge comes from 2004-2013, mostly 2008-09.
In the 2017-2022 validation window, every variant is roughly 0 bps after costs. Expected holdout result: about 0.

Setup:
- Universe: 92 large caps plus 14 ETFs. BK was dropped (no Yahoo data). Survivorship-biased.
- Labels, scaled by ATR(20) and clipped at +-4: OPEN = open to close; CLOSE = close to next open.
- Features: 15 for OPEN, 16 for CLOSE. They are gap/intraday returns, r5/20/60, IBS, MA20 distance, overnight and intraday
  20-day momentum, sector-relative r5, SPY move, VIX z and change, relative vol, Friday flag, ETF flag.
- Stale Yahoo opens are masked. For OPEN features the mask uses only data known at the open.
- Model: ridge (alpha 1e4), re-fit each Jan-1 on an expanding window, with a 5-day embargo. First prediction year is 2004.

Rank-IC (daily Spearman):
- OPEN: A 0.079, B 0.036.
- CLOSE: A 0.110, B 0.050.
- It decays from about 0.13 in 2004-07 to about 0.02-0.04 in 2021-22.

Stock decile tables, realised bps net of cost in the predicted direction (decile 0 / 5 / 8 / 9):
- OPEN A: -16.8 / -10.8 / -5.4 / -1.4.  OPEN B: -14.3 / -13.1 / -11.0 / -11.5.
- CLOSE A: -15.3 / -11.3 / -7.1 / +1.1.  CLOSE B: -14.4 / -10.8 / -8.9 / -5.3.

Trials, judge fills, top-3 slots. A = 2004-16, B = 2017-22. bps per slot (t):
  T1 ridge OPEN, both directions  -1.0(-0.2) / -2.0(-0.4)   | T2 ridge CLOSE, both directions  21.7(3.7) / 1.1(0.2)
  T3/T4 HistGB OPEN/CLOSE  0.6 / 20.1 | -2.4 / 5.0           | T5 CLOSE long only  25.4(4.1) / 0.9(0.1)
  T6 OPEN long only  -4.8 / -15.7(-2.2)                      | T7 CLOSE ETFs only  -1.4 / 4.0
  T8 score = net/ATR  17.6(3.8) / -0.1                        | T9 margin 2x cost  31.9(3.0) / 9.3(0.7)
  T10/T11 alpha 1e2 / 1e5  18.5, 36.2 / 1.5, 1.6               | T12 CLOSE stocks only  44.8(4.3) / -4.1(-0.2)
  T13 trade only when VIX z > 0  33.1(2.7) / 6.8(0.6)          | T14 VIX interactions  17.2(3.0) / 1.1
  T15 logistic P(long > cost)  9.1(3.3) / -1.7                 | T16 T2 + decay gate  28.2(4.4) / -0.3
  T17 = T12 + decay gate (FROZEN)  45.9(4.6) / -4.6(-0.2), 161 slots
N_TRIALS = 20: 17 variants plus 3 diagnostic breakdowns. Selection rule: best A-window t-stat.
The decay gate was added after I saw the 2014-18 losses, so it is partly hindsight.

T17 by year (bps per slot; gate off in 2015, 2018 and 2019):
2004 31, 2005 -75, 2006 16, 2007 15, 2008 51, 2009 98, 2010 11, 2011 51, 2012 25, 2013 86, 2014 0, 2016 18, 2017 -63, 2020 13, 2021 2, 2022 -26.

Why it failed:
- OPEN gap-fading never covers the 16 bps stock cost.
- CLOSE learns short-term reversal plus overnight premium. That is liquidity provision: it pays in stress regimes and has decayed since about 2014.
- Gradient boosting, logistic regression, VIX interactions and ETF-only trading added nothing.

Weaknesses:
- Edge decay: B is about 0.
- Hindsight in the gate and stocks-only choices.
- Worst trade is -41.6% (overnight gap, no stop). Historical max drawdown is 48.5%.
- Survivorship bias, close used as a proxy for the 15:55 fill, and assumed stock CFD costs.

Usage (from trading-analyst/):  python -c "from arena.ml_cross import research as R; R.run('T2', 'CLOSE')"
"""
from __future__ import annotations

import sys, json, pickle
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analyst import data
from arena.ml_cross import strategy as S

CUT = pd.Timestamp("2022-12-31")
CACHE = Path(__file__).resolve().parent / ".cache"
CACHE.mkdir(exist_ok=True)


def frames():
    fr = {}
    for t in sorted(set(S.UNIVERSE) | {"^VIX"}):
        try:
            d = data.load(t)
        except Exception:
            continue
        fr[t] = d[d.index <= CUT]
    return fr


def panels():
    p = CACHE / "panels.pkl"
    if p.exists():
        return pickle.loads(p.read_bytes())
    P = S.build_panel(frames())
    p.write_bytes(pickle.dumps(P))
    return P


def daily_ic(P, pred):
    D = pd.DataFrame({"p": pred, "r": P.loc[pred.index, "raw"]}).dropna()
    ic = D.groupby(level="date").apply(lambda g: spearmanr(g.p, g.r)[0] if len(g) > 10 else np.nan).dropna()
    return ic


def report(P, pred, kind, margin=1.0, k=3):
    ic = daily_ic(P, pred)
    by_year = ic.groupby(ic.index.year).mean()
    E = S.edge_table(P, pred, kind)
    E["raw"] = P.loc[E.index, "raw"]
    E["real_net"] = E["dir"] * E["raw"] - E["cost"]
    if kind == "CLOSE":
        E["real_net"] -= np.where(E["dir"] > 0, S.LONG_FIN_NIGHT, 0) * np.where(E.index.get_level_values("date").dayofweek == 4, 3, 1)
    E = E.dropna(subset=["raw"])
    # pooled deciles of predicted return (in-direction gross) - net of cost
    E["dec"] = pd.qcut(E["net"].rank(method="first"), 10, labels=False)
    dec = E.groupby("dec").agg(pred_net_bps=("net", lambda x: 1e4 * x.mean()), real_net_bps=("real_net", lambda x: 1e4 * x.mean()), n=("net", "size"))
    sel = E[E["net"] > margin * E["cost"]].reset_index().sort_values(["date", "net"], ascending=[True, False]).groupby("date").head(k)
    slot = sel.groupby("date")["real_net"].mean()
    yrs = lambda s: s.groupby(s.index.year)
    tab = pd.DataFrame({"ic": by_year, "slots": yrs(slot).size(), "slot_bps": yrs(slot).mean() * 1e4}).round(4)
    def tstat(x):
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 else float("nan")
    summ = {}
    for name, lo, hi in (("A_2004_2016", 2004, 2016), ("B_2017_2022", 2017, 2022)):
        i = ic[(ic.index.year >= lo) & (ic.index.year <= hi)]; s = slot[(slot.index.year >= lo) & (slot.index.year <= hi)]
        summ[name] = {"ic_mean": round(float(i.mean()), 4), "ic_t": round(tstat(i), 2), "slots": int(len(s)),
                      "slot_bps": round(float(s.mean() * 1e4), 1), "slot_t": round(tstat(s), 2)}
    return summ, tab, dec


def run(name, kind, model="ridge", alpha=1e4, feats=None, margin=1.0, k=3, verbose=True):
    P = panels()[kind]
    feats = feats or (S.OPEN_FEATS if kind == "OPEN" else S.CLOSE_FEATS)
    key = CACHE / f"pred_{kind}_{model}_{alpha}_{abs(hash(tuple(feats))) % 10**8}.pkl"
    if key.exists():
        pred = pickle.loads(key.read_bytes())
    else:
        pred = S.walk_forward(P, feats, model, alpha)
        key.write_bytes(pickle.dumps(pred))
    summ, tab, dec = report(P, pred, kind, margin, k)
    if verbose:
        print(f"=== {name}: kind={kind} model={model} alpha={alpha} margin={margin} k={k} nfeat={len(feats)}")
        print(json.dumps(summ))
        print(tab.to_string())
        print(dec.round(1).to_string())
    return summ, tab, dec, pred


def judge_eval(sig, fr=None, n_trials=10, label=""):
    """Score a signal frame with the judge's own fills() (dev data), by period and year."""
    from arena import judge as J
    fr = fr or frames()
    t = J.fills(sig, fr)
    sl = t.groupby("slot").agg(ret=("ret", "mean"), date=("date", "first"))
    out = {}
    for name, lo, hi in (("A", 2004, 2016), ("B", 2017, 2022), ("ALL", 2004, 2022)):
        s = sl[(sl.date.dt.year >= lo) & (sl.date.dt.year <= hi)]["ret"]
        if len(s) < 3:
            continue
        out[name] = {"slots": len(s), "bps": round(s.mean() * 1e4, 1), "t": round(s.mean() / s.std(ddof=1) * np.sqrt(len(s)), 2),
                     "dsr": round(J.dsr(s, n_trials), 3), "top5": round(float(s.nlargest(5).sum() / s.sum()), 2) if s.sum() > 0 else None}
    yr = sl.groupby(sl.date.dt.year)["ret"].agg(["size", "mean"]); yr["mean"] = (yr["mean"] * 1e4).round(1)
    print(f"--- {label}", json.dumps(out)); print(yr.T.to_string())
    return t, out


def make_sig(kind, pred, P, dirs=(1, -1), etf=None, margin=1.0, k=3, stop_atr=1.5):
    E = S.edge_table(P, pred, kind)
    E = E[E["dir"].isin(dirs)]
    if etf is not None:
        isetf = E.index.get_level_values("ticker").isin(list(S.ETFS))
        E = E[isetf == etf]
    return S.select(E, kind, margin, k, stop_atr)
