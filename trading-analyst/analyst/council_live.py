"""Live daily calls from the FROZEN council model (trained to 2026-04-06). Paper-logged; guard decides real size."""
from __future__ import annotations

from datetime import date as Date

import numpy as np
import pandas as pd

from . import council_sim as cs, data, guard, journal

FOMC = {pd.Timestamp(d) for d in ("2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09")}  # Oct 27-28 verified; Dec date UNVERIFIED -> check federalreserve.gov


def next_session(last: pd.Timestamp) -> pd.Timestamp:
    d = last + pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d += pd.Timedelta(days=1)
    return d


def close_call_is_timely(last_bar: pd.Timestamp, now_utc: pd.Timestamp | None = None) -> bool:
    """A CLOSE call dated L is only placeable before 16:00 ET on L; later runs are shown but never logged."""
    now = (now_utc or pd.Timestamp.now(tz="UTC")).tz_convert("America/New_York")
    return now < pd.Timestamp(last_bar.date(), tz="America/New_York") + pd.Timedelta(hours=16)


def live(args):
    idx = {s: data.load(s, refresh=True) for s in cs.IDX}; vix = data.load("^VIX", refresh=True)["close"]
    L = idx["SPY"].index[-1]; T = next_session(L)
    ext = {}
    for s, f in idx.items():                       # placeholder row for the next session so the decision code can address it
        g = f.copy(); g.loc[T] = np.nan; ext[s] = g
    vx = vix.copy(); vx.loc[T] = np.nan
    c = cs.calls(ext, vx, T, T, calendar_block={"OPEN": FOMC}, news=True)
    print(f"Data through {L.date()} (the near-close bar if run before 16:00 ET). CLOSE call for {L.date()}, OPEN call for {T.date()}.")
    print("Frozen model trained to 2026-04-06; GDELT news needs `python -m analyst.gdelt` to be fresh (stale news is ignored, weight 0).")
    eq = args.equity; flags = []
    d = guard.check(eq, 0.015, Date.today(), flags)
    print(f"GUARD: {'ALLOWED' if d.allowed else 'BLOCKED'} | {'; '.join(d.reasons)}\n")
    for r in c.itertuples():
        if r.dir == 0:
            print(f"  {r.kind:5}: NO TRADE ({r.why})"); continue
        side = "BUY " if r.dir > 0 else "SELL"
        notional = eq * r.notional_x
        stop = f" | stop {r.stop_pct:.2%}" if r.kind == "OPEN" else " | no stop possible overnight"
        print(f"  {r.kind:5}: {side} {r.instrument} | S {r.S:+.2f} | notional ${notional:,.0f} ({r.notional_x:.1f}x){stop} | exit: " + ("sell at next open" if r.kind == "CLOSE" else "close"))
    if args.log:
        if not close_call_is_timely(L):
            c = c[c["kind"] != "CLOSE"]
            print(f"\nNOTE: the {L.date()} close has passed, so that CLOSE call is NOT logged (it could not have been placed). Run again before 16:00 ET for the next close call.")
        journal.log_council(c)
        print("logged to reports/journal_council.csv (paper). Settle later with: python -m analyst council settle")
