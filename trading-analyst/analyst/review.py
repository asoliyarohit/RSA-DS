"""Post-mortem for one session: what the OPEN rule would have traded (info available at 9:30 only) vs the hindsight best.
Hindsight list is NOT a strategy - it only shows how much of the day's move a causal rule can capture."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import universe as u
from .cfd import CFDSpec


def review(args):
    cfd: CFDSpec = u.STOCK_CFD
    fr = u.load_frames(refresh=True)
    spy = fr["SPY"] if "SPY" in fr else next(iter(fr.values()))
    day = pd.Timestamp(args.date) if getattr(args, "date", None) else spy.index[-1]
    if day not in spy.index:
        print(f"{day.date()} is not a trading day in the data"); return
    risk, thr, stop_atr = args.risk[0], args.gap_atr, 2.5
    rows = []
    for sym, f in fr.items():
        if day not in f.index:
            continue
        r = f.loc[day]
        if np.isnan(r["atr_o"]) or np.isnan(r["gap_atr_o"]):
            continue
        o, h, l, c = r["open"], r["high"], r["low"], r["close"]
        rc = c / o - 1                                           # raw open->close
        d = float(np.sign(r["gap_atr_o"])) if abs(r["gap_atr_o"]) >= thr else 0.0
        if d and r["trend_o"] != d:                              # same trend filter as the validated rule
            d = 0.0
        stop = stop_atr * r["atr_o"]
        hit = (l <= o * (1 - stop)) if d > 0 else (h >= o * (1 + stop)) if d < 0 else False
        ret = d * ((-stop if hit else 0) if hit else rc) - cfd.round_trip_cost() if d else np.nan
        best_dir = np.sign(rc)
        rows.append({"ticker": sym, "gap_atr": round(float(r["gap_atr_o"]), 2), "oc_pct": round(rc * 100, 2),
                     "signal": {1.0: "BUY", -1.0: "SELL", 0.0: "-"}[d], "stopped": bool(hit), "net_bps": ret * 1e4 if d else np.nan,
                     "stop_pct": stop, "hind_pct": round(abs(rc) * 100, 2), "hindsight_dir": "BUY" if best_dir > 0 else "SELL"})
    t = pd.DataFrame(rows)
    print(f"=== Session review {day.date()} | {len(t)} instruments | rule: follow gap >= {thr} ATR in 200d-trend direction, stop {stop_atr} ATR, exit close ===")
    sig = t[t["signal"] != "-"].sort_values("net_bps", ascending=False)
    if sig.empty:
        print("\nCAUSAL RULE: no trade triggered at the open (NO TRADE is the honest output on most days).")
    else:
        print("\nCAUSAL RULE (known at the open):")
        for r in sig.itertuples():
            notional = min(risk / r.stop_pct, cfd.leverage)
            print(f"  {r.signal:4} {r.ticker:6} gap {r.gap_atr:+.2f} ATR | net {r.net_bps:+.0f} bps | 5x sized @ {risk:.0%} risk: "
                  f"{notional * r.net_bps / 1e4:+.1%} of equity{' | STOPPED' if r.stopped else ''}")
        eq = sum(min(risk / r.stop_pct, cfd.leverage) / max(len(sig), 1) * r.net_bps / 1e4 for r in sig.itertuples())
        print(f"  Portfolio (risk split across {len(sig)}): {eq:+.2%} of equity")
    print("\nHINDSIGHT TOP-8 open->close moves (impossible to know in advance):")
    for r in t.sort_values("hind_pct", ascending=False).head(8).itertuples():
        caught = f"rule said {r.signal}" if r.signal != "-" else "rule: no signal"
        print(f"  {r.hindsight_dir:4} {r.ticker:6} {r.hind_pct:>5}% (gap {r.gap_atr:+.2f} ATR) -> {caught}")
    cap = sig["net_bps"].sum() / 1e4 if not sig.empty else 0.0
    print(f"\nCaptured by rule (sum of net moves): {cap:.2%} vs hindsight top-8 total {t.sort_values('hind_pct', ascending=False).head(8)['hind_pct'].sum():.1f}%")
    print("Caveat: one day proves nothing. Judge the rule only by the sealed-holdout statistics in arena/RESULTS.md.")
