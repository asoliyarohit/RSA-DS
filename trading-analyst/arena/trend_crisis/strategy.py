"""trend_crisis: diversified cross-asset long/short book, CLOSE slot only (hold the model's direction overnight).

Universe: 7 major-index ETFs (20x, 4 bps round trip in the judge) + GLD (20x, 7 bps). Yahoo continuous futures ('=F') were
REMOVED on purpose: their close->next-open return contains contract roll gaps that a CFD holder never receives (NG=F showed
+13 bps/night of pure roll artefact), so any "edge" there is fake. Single stocks (66 bps round trip) lose 60+ bps/slot
under every rule tried and are excluded.

Signal: purged walk-forward ridge (refit each 1 Jan on data whose target date is < 1 Jan minus 21 days, pooled across
instruments, vol-normalised target) stacking 18 trend / reversal / regime features: 1-3-6-12m z-momentum, 12-1m momentum,
EMA crossovers, 1y drawdown, IBS, 1d/5d returns, VIX vs its 3m mean, VIX/VIX3M term ratio, relative vol, index breadth,
MA200 sign. Trade instrument i at the close of day d when |E[open_{d+1}/close_d - 1]| > 2 x (round trip + overnight
financing); score = |E[ret]|; stop_pct = 2 x EWMA daily vol (sizing only, CLOSE has no stop).

What the walk-forward actually learned (see REPORT.txt): the dominant features are IBS (-), last-month return (-) and
12-1m momentum (+): a short-horizon REVERSAL + slow trend blend, not pure trend following. Pure TSMOM held daily lost to
costs in every class, including 2008 and 2022 (r1_decomp.py). N_TRIALS counts every configuration evaluated on dev data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

UNIVERSE = ["SPY", "QQQ", "DIA", "EWG", "FEZ", "EWJ", "EWU", "GLD", "^VIX3M"]
N_TRIALS = 122
INDICES = ["SPY", "QQQ", "DIA", "EWG", "FEZ", "EWJ", "EWU"]
LOOKS = (21, 63, 126, 252)
FEATS = ["z21", "z63", "z126", "z252", "z252x21", "ema8", "ema16", "ema32", "dd", "ibs", "r1n", "r5n", "vixma", "vterm", "rvol", "br", "ma200"]
LAM = 300.0           # ridge penalty
MULT = 2.0            # trade when |E[ret]| > MULT x cost
EMBARGO_DAYS = 21
FIRST_YEAR = 2006
RT = {"GLD": 7e-4}    # judge cost model: index 2+2x1 bps, gold 5+2x1 bps; financing long -(0.04+0.03)/365 per night
RT_DEFAULT = 4e-4
FIN_LONG = (0.04 + 0.03) / 365.0


def _feats(f: pd.DataFrame, vix: pd.Series, vix3m: pd.Series | None) -> pd.DataFrame:
    f = f[(f[["open", "high", "low", "close"]] > 0).all(axis=1)]
    c, h, l = f["close"], f["high"], f["low"]
    r = np.log(c).diff()
    out = pd.DataFrame(index=f.index)
    out["on_ret"] = f["open"].shift(-1) / c - 1
    out["tdate"] = pd.Series(f.index, index=f.index).shift(-1)
    vol = r.ewm(span=32, min_periods=20).std()
    out["vol"] = vol
    vol_long = r.rolling(252, min_periods=120).std()
    for L in LOOKS:
        out[f"z{L}"] = ((c / c.shift(L) - 1) / (vol * np.sqrt(L))).clip(-3, 3)
    out["z252x21"] = ((c.shift(21) / c.shift(252) - 1) / (vol * np.sqrt(231))).clip(-3, 3)
    for s, lng in ((8, 24), (16, 48), (32, 96)):
        out[f"ema{s}"] = ((c.ewm(span=s).mean() - c.ewm(span=lng).mean()) / c.rolling(63).std()).clip(-3, 3)
    out["dd"] = (c / c.rolling(252, min_periods=60).max() - 1).clip(-1, 0)
    out["ibs"] = ((c - l) / (h - l).replace(0, np.nan)).fillna(0.5) - 0.5
    out["r1n"] = (r / vol).clip(-4, 4)
    out["r5n"] = (np.log(c).diff(5) / (vol * np.sqrt(5))).clip(-4, 4)
    v = vix.reindex(f.index).ffill()
    out["vixma"] = (v / v.rolling(63).mean() - 1).clip(-1, 2)
    vt = (v / vix3m.reindex(f.index).ffill()) if vix3m is not None else pd.Series(np.nan, index=f.index)
    out["vterm"] = (vt.fillna(1.0) - 1).clip(-0.5, 1)
    out["rvol"] = (vol / vol_long - 1).clip(-0.8, 3)
    out["ma200"] = np.sign(c / c.rolling(200).mean() - 1)
    return out


def _breadth(frames) -> pd.Series:
    cols = {}
    for t in INDICES:
        if t in frames:
            c = frames[t]["close"]; m = c.rolling(200).mean()
            cols[t] = (c > m).astype(float).where(m.notna())
    return pd.DataFrame(cols).mean(axis=1)


def _ridge(X, y, lam):
    Xb = np.c_[np.ones(len(X)), X]
    A = Xb.T @ Xb + lam * np.eye(Xb.shape[1]); A[0, 0] -= lam
    return np.linalg.solve(A, Xb.T @ y)


def _panel(frames) -> pd.DataFrame:
    vix = frames["^VIX"]["close"]; vix3m = frames["^VIX3M"]["close"] if "^VIX3M" in frames else None
    br = _breadth(frames)
    parts = []
    for t in INDICES + ["GLD"]:
        if t not in frames or frames[t].empty:
            continue
        p = _feats(frames[t], vix, vix3m)
        p["br"] = br.reindex(p.index).fillna(0.5) - 0.5
        p["inst"] = t; p["rt"] = RT.get(t, RT_DEFAULT)
        parts.append(p.reset_index().rename(columns={"index": "date"}))
    P = pd.concat(parts, ignore_index=True)
    P = P.rename(columns={P.columns[0]: "date"}) if "date" not in P.columns else P
    return P


def signals(frames) -> pd.DataFrame:
    P = _panel(frames)
    X = P[FEATS]; y = P["on_ret"] / P["vol"]
    ok_x = X.notna().all(axis=1) & P["vol"].gt(0)
    ok = ok_x & y.notna() & np.isfinite(y)
    pred = pd.Series(np.nan, index=P.index)
    for Y in sorted(P["date"].dt.year.unique()):
        if Y < FIRST_YEAR:
            continue
        cut = pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=EMBARGO_DAYS)
        tr = ok & (P["date"] < cut) & (P["tdate"] < cut)          # target date also before the cut: purged
        te = ok_x & (P["date"].dt.year == Y)
        if tr.sum() < 500 or te.sum() == 0:
            continue
        w = _ridge(X[tr].to_numpy(), y[tr].clip(-5, 5).to_numpy(), LAM)
        pred[te] = np.c_[np.ones(int(te.sum())), X[te].to_numpy()] @ w
    e = pred * P["vol"]
    cost = P["rt"] + FIN_LONG
    sel = e.notna() & (e.abs() > MULT * cost)
    S = P[sel]
    return pd.DataFrame({"instrument": S["inst"].values, "date_in": S["date"].values, "kind": "CLOSE",
                         "dir": np.sign(e[sel]).astype(int).values, "stop_pct": (2.0 * S["vol"]).values,
                         "score": e[sel].abs().values})
