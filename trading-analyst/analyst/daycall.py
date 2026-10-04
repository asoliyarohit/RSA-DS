"""Daily call: ONE instrument + direction for the OPEN day trade (CFD BUY/SELL, exit at close).

Composite score uses only information known at 9:30 and weights fixed a priori (NOT fitted):
  +1.5 gap-follow    : |gap| >= 1.5 ATR and 200d trend agrees with the gap
  +1.0 reversal      : fade yesterday's >= 1.5 ATR move
  +1.0 dip/rip       : yesterday closed in the bottom/top 15% of its range, with trend agreeing
  +0.5 trend         : 200d trend direction
Conviction = MEASURED hit rate of that strength bucket for the daily pick (dev <=2022, holdout 2023+), never asserted.
Sizing is 0 (paper only) unless the holdout bucket shows a statistically positive net edge."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, features
from . import universe as u
from .cfd import CFDSpec

STOP_ATR = 1.5
MIN_STRENGTH = 1.5
HOLDOUT = pd.Timestamp("2023-01-01")
BINS = [(1.5, 2.5, "MEDIUM"), (2.5, 3.5, "HIGH"), (3.5, 99, "VERY HIGH")]


def frames(refresh=False):
    vix = data.load(data.VIX, refresh=refresh)["close"]
    fr = {s: features.build(data.load(s, refresh=refresh), vix) for s in ("SPY", "QQQ")}
    fr.update(u.load_frames(refresh))
    return fr


def table(fr, cfd: CFDSpec = u.STOCK_CFD) -> pd.DataFrame:
    out = []
    for sym, f in fr.items():
        ret1 = (f["close"].shift(1) / f["close"].shift(2) - 1) / f["atr_o"]
        ibs1 = f["ibs_c"].shift(1)
        g, tr = f["gap_atr_o"], f["trend_o"]
        c1 = np.where((g.abs() >= 1.5) & (np.sign(g) == tr), np.sign(g), 0.0)
        c2 = np.where(ret1.abs() >= 1.5, -np.sign(ret1), 0.0)
        c3 = np.where((ibs1 < 0.15) & (tr > 0), 1.0, np.where((ibs1 > 0.85) & (tr < 0), -1.0, 0.0))
        comp = 1.5 * c1 + 1.0 * c2 + 1.0 * c3 + 0.5 * tr.fillna(0).to_numpy()
        d = np.sign(comp)
        stop = STOP_ATR * f["atr_o"]
        o, h, l, c = (f[k].to_numpy() for k in ("open", "high", "low", "close"))
        hit = np.where(d > 0, l <= o * (1 - stop), np.where(d < 0, h >= o * (1 + stop), False))
        ret = np.where(hit, -stop.to_numpy(), d * (c / o - 1)) - cfd.round_trip_cost()
        t = pd.DataFrame({"date": f.index, "ticker": sym, "comp": comp, "dir": d, "strength": np.abs(comp),
                          "stop_pct": stop.to_numpy(), "ret": ret, "stopped": hit, "gap_atr": g.to_numpy(),
                          "open": o, "close": c})
        out.append(t[(t["strength"] >= MIN_STRENGTH) & t["stop_pct"].notna() & t["ret"].notna()])
    return pd.concat(out)


def daily_picks(t: pd.DataFrame) -> pd.DataFrame:
    return t.sort_values(["date", "strength", "ticker"], ascending=[True, False, True]).groupby("date").head(1).reset_index(drop=True)


def bucket(s: float) -> str:
    for lo, hi, name in BINS:
        if lo <= s < hi:
            return name
    return "NONE"


def calibration(p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    p = p.assign(bucket=p["strength"].map(bucket), period=np.where(p["date"] >= HOLDOUT, "holdout 2023+", "dev <=2022"))
    for (per, b), g in p.groupby(["period", "bucket"]):
        r = g["ret"]
        t = float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 and r.std() > 0 else 0.0
        rows.append({"period": per, "bucket": b, "n": len(g), "win%": round(100 * float((r > 0).mean()), 1),
                     "avg_net_bps": round(float(r.mean() * 1e4), 1), "t": round(t, 2)})
    return pd.DataFrame(rows).sort_values(["period", "bucket"])


def run(args):
    fr = frames(refresh=True)
    t = table(fr); p = daily_picks(t); cal = calibration(p)
    print("=== MEASURED track record of the daily pick (open->close, 5x CFD costs, 1.5 ATR stop, all 33 instruments, one pick/day) ===")
    print(cal.to_string(index=False))
    day = pd.Timestamp(args.date) if getattr(args, "date", None) else max(f.index[-1] for f in fr.values())
    pick = p[p["date"] == day]
    print(f"\n=== CALL for session {day.date()} (uses only the open and earlier data) ===")
    if pick.empty:
        print("NO TRADE: nothing scored >= 1.5. A day with no setup is the correct output; forcing a trade is how small accounts die."); return
    r = pick.iloc[0]; b = bucket(r["strength"])
    side = "BUY (go long CFD)" if r["dir"] > 0 else "SELL (go short CFD)"
    ho = cal[(cal.period == "holdout 2023+") & (cal.bucket == b)]
    dv = cal[(cal.period == "dev <=2022") & (cal.bucket == b)]
    print(f"{side} {r['ticker']} at the open {r['open']:.2f} | stop {r['stop_pct']:.2%} away | exit at the close | strength {r['strength']:.1f} ({b})")
    for lbl, d_ in (("dev", dv), ("holdout", ho)):
        if len(d_):
            x = d_.iloc[0]; print(f"  measured {lbl}: win {x['win%']}% | avg {x['avg_net_bps']:+.1f} bps net | t {x['t']} | n {x['n']}")
    from datetime import date as _d
    from . import guard
    ok = len(ho) and ho.iloc[0]["avg_net_bps"] > 0 and ho.iloc[0]["t"] > 1.65
    dec = guard.check(args.equity, args.risk[0], _d.today(), [], require_evidence=True)
    risk = dec.risk if ok and dec.allowed else 0.0
    print("  GUARD: " + ("OK" if dec.allowed else "BLOCKED") + " | " + "; ".join(dec.reasons))
    notional = min(risk / r["stop_pct"], 5.0) * args.equity if risk else 0.0
    print(f"  SIZE: {'$%.0f notional (%.0f%% account risk)' % (notional, risk * 100) if risk else 'PAPER ONLY - measured holdout edge is not statistically positive, so risking money is not justified.'}")
    if "ret" in r and day <= max(f.index[-1] for f in fr.values()):
        print(f"  Outcome that day (hindsight, for scoring only): {r['ret'] * 1e4:+.0f} bps net{' (stopped)' if r['stopped'] else ''}")
