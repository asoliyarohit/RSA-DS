"""Frozen walk-forward simulation. For each trading day T the system sees ONLY data through the close of T-1 and issues
  CLOSE call (dated T-1): enter T-1 close, sell at T open      OPEN call (dated T): enter T open (pre-market decision), exit T close, hard stop
Ridge models (pooled over instruments, ATR-normalised) are retrained monthly on rows whose labels were already known.
Fills/costs/leverage come from arena.judge.fills, i.e. the same single source of truth as the arena.
SPEC (weights, vetoes, risk) is passed in and must be frozen BEFORE running."""
from __future__ import annotations

import numpy as np
import pandas as pd

from arena import judge
from . import data, gdelt
from . import universe as u
from .cfd import equity_factor
from .features import rsi

UNIVERSE = ["SPY", "QQQ", "DIA", "GLD"] + [s for s in u.STOCKS if s != "WBA"]
FEATS = ["r1", "r5", "r20", "ibs", "rsi2", "trend", "gap", "oc", "vix", "vixchg"]

DEFAULT = dict(start="2026-04-07", end=None, alpha=1000.0, min_edge_bps=0.0, stop_atr=1.5, stress_atr=2.0,
               news_w={}, veto={}, risk_aggr=0.25, risk_guard=0.05, classes=None, mode="t1")


def panel(frames, vix):
    out = {}
    for s, f in frames.items():
        c, o, h, l = f["close"], f["open"], f["high"], f["low"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean() / c
        p = pd.DataFrame(index=f.index)
        p["atr"] = atr
        p["r1"] = c.pct_change() / atr; p["r5"] = c.pct_change(5) / atr; p["r20"] = c.pct_change(20) / atr
        p["ibs"] = (c - l) / (h - l).replace(0, np.nan) - 0.5
        p["rsi2"] = rsi(c, 2) / 100 - 0.5
        p["trend"] = ((c / c.rolling(200).mean() - 1) / atr).clip(-10, 10)
        p["gap"] = (o / c.shift() - 1) / atr; p["oc"] = (c / o - 1) / atr
        v = vix.reindex(f.index).ffill()
        p["vix"] = np.log(v); p["vixchg"] = v.pct_change()
        p["y_co"] = (o.shift(-1) / c - 1) / atr
        p["y_oc"] = (c.shift(-1) / o.shift(-1) - 1) / atr
        out[s] = p
    return out


def ridge_fit(X, y, alpha):
    mu, sd = X.mean(0), X.std(0).replace(0, 1)
    Z = ((X - mu) / sd).to_numpy(); ym = y.mean()
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y.to_numpy() - ym))
    return mu, sd, w, ym


def ridge_pred(model, X):
    mu, sd, w, ym = model
    return ((X - mu) / sd).to_numpy() @ w + ym


def run_calls(frames, vix, spec):
    spec = {**DEFAULT, **spec}
    P = panel(frames, vix)
    cal = frames["SPY"].index
    start = pd.Timestamp(spec["start"]); end = pd.Timestamp(spec["end"]) if spec["end"] else cal[-1]
    days = [d for d in cal if start <= d <= end]
    news = gdelt.load()
    nz = {}
    for col in news.columns:  # trailing 60d z-score, using only days <= t
        x = news[col]; nz[col] = ((x - x.rolling(60, min_periods=20).mean()) / x.rolling(60, min_periods=20).std())
    nz = pd.DataFrame(nz) if nz else pd.DataFrame()
    rows, models, cur_month = [], None, None
    for T in days:
        i = cal.get_loc(T); t = cal[i - 1]                       # decisions use rows <= t = T-1
        if cur_month != (T.year, T.month):                         # monthly retrain on rows with fully-known labels
            cutoff = cal[i - 2]
            tr = pd.concat([p.loc[:cutoff].assign(sym=s) for s, p in P.items()]).dropna(subset=FEATS + ["y_co", "y_oc"])
            tr = tr[np.isfinite(tr[FEATS]).all(axis=1)]
            models = {k: ridge_fit(tr[FEATS], tr[k].clip(-6, 6), spec["alpha"]) for k in ("y_co", "y_oc")}
            cur_month = (T.year, T.month)
        veto = None
        vx = float(np.exp(P["SPY"].loc[t, "vix"])); vch = float(P["SPY"].loc[t, "vixchg"])
        if spec["veto"].get("vix_max") and vx > spec["veto"]["vix_max"]: veto = f"VIX {vx:.1f}"
        if spec["veto"].get("vix_jump") and vch > spec["veto"]["vix_jump"]: veto = f"VIX jump {vch:.0%}"
        for q, z in spec["veto"].get("news_z", {}).items():
            if q in nz.columns and t in nz.index and nz.loc[t, q] > z: veto = f"news spike {q}"
        tilt_z = sum(w * float(nz.loc[t, k]) for k, w in spec["news_w"].items() if k in nz.columns and t in nz.index and np.isfinite(nz.loc[t, k])) if len(nz) else 0.0
        for kind, ycol, date_in in (("CLOSE", "y_co", t), ("OPEN", "y_oc", T)):
            best = None
            for s in UNIVERSE:
                if spec["classes"] and judge.cost_for(s).leverage not in spec["classes"]:
                    continue
                r = P[s].loc[t, FEATS]
                if not np.isfinite(r.to_numpy(dtype=float)).all() or not np.isfinite(P[s].loc[t, "atr"]):
                    continue
                atr = float(P[s].loc[t, "atr"])
                pred = float(ridge_pred(models[ycol], r.to_frame().T)[0]) + tilt_z
                bps = pred * atr * 1e4
                cost = judge.cost_for(s).round_trip_cost() * 1e4
                nights = float((cal[i] - t).days) if kind == "CLOSE" else 0.0
                fin = nights * (0.07 / 365) * 1e4 if (kind == "CLOSE" and bps > 0) else 0.0
                edge = abs(bps) - cost - fin
                if best is None or edge > best["edge"]:
                    best = dict(sym=s, bps=bps, edge=edge, atr=atr)
            if best is None or veto or best["edge"] <= spec["min_edge_bps"]:
                rows.append(dict(T=T, date_in=date_in, kind=kind, instrument="", dir=0, why=veto or "no predicted net edge")); continue
            rows.append(dict(T=T, date_in=date_in, kind=kind, instrument=best["sym"], dir=int(np.sign(best["bps"])), pred_bps=best["bps"],
                             edge_bps=best["edge"], stop_pct=(spec["stop_atr"] if kind == "OPEN" else spec["stress_atr"]) * best["atr"],
                             score=best["edge"], why=""))
    return pd.DataFrame(rows)


def settle(calls, frames):
    c = calls[calls["dir"] != 0].copy()
    c["date_in"] = pd.to_datetime(c["date_in"])
    t = judge.fills(c[["instrument", "date_in", "kind", "dir", "stop_pct", "score"]], frames)
    return t


def account(trades, mode, spec, start=1000.0):
    """mode 'aggr': constant risk; 'guard': analyst.guard rules replicated (5% cap, 4% day, 8% week, 20% DD halt, streak/DD halving)."""
    eq = start; peak = start; day = None; day_start = start; wk = None; wk_start = start; streak = 0; halted = False
    out = []
    for slot, g in trades.sort_values("slot").groupby("slot", sort=True):
        d = pd.Timestamp.fromordinal(int(slot) // 2)
        iso = d.isocalendar()[:2]
        if day != d.date(): day, day_start = d.date(), eq
        if wk != iso: wk, wk_start = iso, eq
        risk = spec["risk_aggr"]
        if mode == "guard":
            dd = 1 - eq / peak
            if dd >= 0.20: halted = True
            risk = min(spec["risk_guard"], 0.05) * (0.25 if streak >= 5 else 0.5 if streak >= 3 else 1.0) * (0.5 if dd >= 0.10 else 1.0)
            if halted or 1 - eq / day_start >= 0.04 or 1 - eq / wk_start >= 0.08:
                risk = 0.0
            risk = min(risk, max(0.04 - (1 - eq / day_start), 0.0))
        before = eq
        f = float(equity_factor(g["ret"].to_numpy(), g["stop_pct"].to_numpy(), np.ones(len(g)), risk, g["lev"].to_numpy()))
        eq = max(eq * f, 0.0); peak = max(peak, eq)
        if risk > 0: streak = streak + 1 if eq < before else 0
        out.append(dict(slot=slot, date=d, equity=eq, pnl=eq - before, risk=risk))
    return pd.DataFrame(out)


def placebo(trades, flipped, spec, mode, n=2000, seed=5, start=1000.0):
    """Same instruments/slots/sizing, direction randomised per trade. Shows how much of a result is luck."""
    rng = np.random.default_rng(seed)
    t = trades.sort_values("slot").reset_index(drop=True); fl = flipped.sort_values("slot").reset_index(drop=True)
    flip = rng.random((n, len(t))) < 0.5
    ret = np.where(flip, fl["ret"].to_numpy()[None, :], t["ret"].to_numpy()[None, :])
    e = np.full(n, start)
    for k in range(len(t)):
        risk = spec["risk_aggr"] if mode == "aggr" else min(spec["risk_guard"], 0.05)
        notional = np.minimum(risk / t["stop_pct"].iloc[k], t["lev"].iloc[k])
        e = np.maximum(e * (1 + notional * ret[:, k]), 0.0)
    return e
