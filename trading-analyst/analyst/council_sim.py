"""Council v1 frozen spec (opus model + sonnet risk). Indices only: SPY, QQQ, DIA. Decisions use info <= T-1 close.
S = z_model + W_TONE * z_tone ; trade the index with largest |S| if |S| >= THRESH.  CLOSE news lag = 2 days, OPEN = 1 day (GDELT day ends 8pm ET)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from arena import judge
from . import data, gdelt

IDX = ["SPY", "QQQ", "DIA"]
W_TONE, TONE_WARMUP_DAYS = 0.10, 20   # threshold = 80th percentile of |z_model| on TRAIN data per call type (intent: 'top 20% of training scores')
FEATS = ["ibs", "r1", "r5", "oc", "gap", "trend", "vixz", "dvix"]


def panel(frames, vix):
    P = {}
    for s in IDX:
        f = frames[s]; c, o, h, l = f["close"], f["open"], f["high"], f["low"]
        sig = c.pct_change().rolling(20).std()
        v = np.log(vix.reindex(f.index).ffill())
        p = pd.DataFrame(index=f.index)
        p["sig"] = sig
        p["ibs"] = (c - l) / (h - l).replace(0, np.nan) - 0.5
        p["r1"] = c.pct_change() / sig; p["r5"] = c.pct_change(5) / sig
        p["oc"] = (c / o - 1) / sig; p["gap"] = (o / c.shift() - 1) / sig
        p["trend"] = np.sign(c / c.rolling(200).mean() - 1)
        p["vixz"] = (v - v.rolling(60).mean()) / v.rolling(60).std(); p["dvix"] = v.diff()
        p["y_co"] = (o.shift(-1) / c - 1) / sig; p["y_oc"] = (c.shift(-1) / o.shift(-1) - 1) / sig
        P[s] = p
    return P


def train(P, cutoff_pos, cal):
    """pooled ridge, lambda = N, rows with labels known up to cutoff date."""
    cutoff = cal[cutoff_pos]
    tr = pd.concat([p.loc[:cutoff] for p in P.values()]).dropna(subset=FEATS + ["y_co", "y_oc"])
    X = tr[FEATS]; mu, sd = X.mean(), X.std().replace(0, 1); Z = ((X - mu) / sd).to_numpy(); dates = tr.index
    models = {}
    for k in ("y_co", "y_oc"):
        y = tr[k].clip(-6, 6); ym = y.mean()
        w = np.linalg.solve(Z.T @ Z + len(Z) * np.eye(len(FEATS)), Z.T @ (y.to_numpy() - ym))
        pt = Z @ w + ym
        psd = float(pt.std())
        models[k] = (w, ym, psd, float(np.percentile(pd.Series(np.abs(pt / psd), index=dates).groupby(level=0).max(), 80)))   # top-20% of DAYS by max |z| across the 3 indices
    return mu, sd, models


def calls(frames, vix, start, end=None, calendar_block=None, news=True, model_start="2026-04-07"):
    P = panel(frames, vix); cal = frames["SPY"].index
    days = [d for d in cal if d >= pd.Timestamp(start) and (end is None or d <= pd.Timestamp(end))]
    i0 = cal.get_loc(pd.Timestamp(model_start))
    mu, sd, models = train(P, i0 - 2, cal)                       # FROZEN model: labels known as of model_start-1 (sim and live share it)
    g = gdelt.load() if news else pd.DataFrame()
    zt = {}
    for col in ("stock market|tone", "earnings|tone"):
        if col in g.columns:
            x = g[col]; zt[col] = ((x - x.rolling(60, min_periods=20).mean()) / x.rolling(60, min_periods=20).std()).clip(-3, 3)
    zv = {}
    for col in ("tariffs|vol", "Federal Reserve|vol", "recession|vol", "oil prices|vol"):
        if col in g.columns:
            x = g[col]; zv[col] = (x - x.rolling(60, min_periods=20).mean()) / x.rolling(60, min_periods=20).std()
    rows = []
    for T in days:
        i = cal.get_loc(T); t = cal[i - 1]; n = i - i0
        vx = float(np.exp(P["SPY"].loc[t, "vixz"] * 0 + np.log(vix.reindex(cal).ffill().loc[t])))
        for kind, key, date_in, lag in (("CLOSE", "y_co", t, 2), ("OPEN", "y_oc", T, 1)):
            nd = cal[i - lag] if i - lag >= 0 else t
            tone = np.nanmean([zt[c].get(nd, np.nan) for c in zt]) if zt else 0.0
            w_t = 0.0 if (n < TONE_WARMUP_DAYS or not np.isfinite(tone)) else W_TONE
            best = None
            for s in IDX:
                r = P[s].loc[t, FEATS]
                if not np.isfinite(r.to_numpy(dtype=float)).all() or not np.isfinite(P[s].loc[t, "sig"]):
                    continue
                w, ym, psd, cut = models[key]
                zm = (float(((r - mu) / sd).to_numpy() @ w) + ym) / psd
                S = zm + w_t * (tone if np.isfinite(tone) else 0.0)
                if best is None or abs(S) > abs(best["S"]):
                    best = dict(sym=s, S=S, sig=float(P[s].loc[t, "sig"]))
            why, size_mult = "", 1.0
            if best is None or abs(best["S"]) < models[key][3]: why = "below threshold"
            elif vx > 35: why = f"VIX {vx:.0f}>35"
            elif calendar_block and (T if kind == "OPEN" else t) in calendar_block.get(kind, set()): why = "scheduled event"
            else:
                if vx > 30: size_mult = 0.5
                spike = [c for c in zv if np.isfinite(zv[c].get(nd, np.nan)) and zv[c].get(nd) > 3]
                if spike:
                    if kind == "CLOSE": why = f"news volume spike {spike[0]}"
                    else: size_mult *= 0.5
            if why:
                rows.append(dict(T=T, kind=kind, date_in=date_in, instrument="", dir=0, why=why)); continue
            rows.append(dict(T=T, kind=kind, date_in=date_in, instrument=best["sym"], dir=int(np.sign(best["S"])), S=best["S"],
                             stop_pct=best["sig"] * 1.0 if kind == "OPEN" else best["sig"] * 2.0, score=abs(best["S"]), size_mult=size_mult,
                             notional_x=min(4.0, 0.015 / best["sig"]) * min(1.0, abs(best["S"]) / 2) * size_mult, why=""))
    return pd.DataFrame(rows)
