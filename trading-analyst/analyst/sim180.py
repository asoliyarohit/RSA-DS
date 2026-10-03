"""FROZEN 180-day simulation run (council v1). Run once; report whatever comes out."""
from __future__ import annotations

import numpy as np
import pandas as pd

from arena import judge
from . import council_sim as cs, data
from .cfd import equity_factor

FOMC = {pd.Timestamp(d) for d in ("2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16")}   # verified on federalreserve.gov
START, END = "2026-04-07", "2026-10-02"


def frac_for(mode, row):
    if mode == "A_council":   return float(row["notional_x"])
    if mode == "B_guarded1.5": return min(0.015 / row["stop_pct"], row["lev"])
    if mode == "C_aggr10":    return min(0.10 / row["stop_pct"], row["lev"])


def account(tr, mode, guard=True, start=1000.0):
    e = peak = day_start = wk_start = start; day = wk = None; streak = 0; halted = False; out = []
    for _, r in tr.sort_values("slot").iterrows():
        d = pd.Timestamp.fromordinal(int(r["slot"]) // 2); iso = d.isocalendar()[:2]
        if day != d.date(): day, day_start = d.date(), e
        if wk != iso: wk, wk_start = iso, e
        m = 1.0
        if guard:
            dd = 1 - e / peak
            if dd >= 0.20: halted = True
            lim_day = 0.25 if mode == "C_aggr10" else 0.04
            m = 0.0 if (halted or 1 - e / day_start >= lim_day or (mode != "C_aggr10" and 1 - e / wk_start >= 0.08)) else \
                (0.25 if streak >= 5 else 0.5 if streak >= 3 else 1.0) * (0.5 if dd >= 0.10 and mode != "C_aggr10" else 1.0)
        f = frac_for(mode, r) * m
        before = e; e = max(e * (1 + f * r["ret"]), 0.0); peak = max(peak, e)
        if m > 0: streak = streak + 1 if e < before else 0
        out.append(dict(slot=r["slot"], equity=e, pnl=e - before, frac=f))
    return pd.DataFrame(out)


def placebo(tr, flip_tr, mode, n=3000, seed=11, start=1000.0):
    rng = np.random.default_rng(seed)
    a = tr.sort_values("slot").reset_index(drop=True); b = flip_tr.sort_values("slot").reset_index(drop=True)
    fr = np.array([frac_for(mode, r) for _, r in a.iterrows()])
    flip = rng.random((n, len(a))) < 0.5
    ret = np.where(flip, b["ret"].to_numpy()[None, :], a["ret"].to_numpy()[None, :])
    e = np.full(n, start)
    for k in range(len(a)):
        e = np.maximum(e * (1 + fr[k] * ret[:, k]), 0.0)
    return e


def stats(x):
    x = np.asarray(x, float) * 1e4; n = len(x)
    if n < 3: return dict(n=n)
    se = x.std(ddof=1) / np.sqrt(n)
    return dict(n=n, hit=round(float((x > 0).mean()), 3), mean_bps=round(float(x.mean()), 1), se=round(float(se), 1),
                t=round(float(x.mean() / se), 2), ci95=(round(float(x.mean() - 1.96 * se), 1), round(float(x.mean() + 1.96 * se), 1)))


def main():
    idx = {s: data.load(s) for s in cs.IDX}; vix = data.load("^VIX")["close"]
    out = {}
    for label, news in (("NEWS+PRICE", True), ("PRICE_ONLY", False)):
        c = cs.calls(idx, vix, START, END, calendar_block={"OPEN": FOMC}, news=news)
        sig = c[c.dir != 0][["instrument", "date_in", "kind", "dir", "stop_pct", "score", "notional_x", "S", "T"]].copy()
        tr = judge.fills(sig, idx)
        meta = sig.assign(date=pd.to_datetime(sig["date_in"]), setup=sig["kind"]).drop_duplicates(["instrument", "date", "setup"])
        tr = tr.merge(meta[["instrument", "date", "setup", "notional_x", "S", "T"]], on=["instrument", "date", "setup"], how="left")
        flip = judge.fills(sig.assign(dir=-sig["dir"]), idx)
        out[label] = dict(calls=c, trades=tr, flip=flip)
    return out, idx
