"""Forward-test journal. Three CSVs in reports/ (prefixed journal_):
  quotes.csv : Revolut bid/ask you type in  -> measured spread (bps) per instrument
  trades.csv : your real fills              -> realised P&L incl. overnight fees
  calls.csv  : daily call logged as a PAPER trade, settled later from real prices -> forward track record
Nothing here talks to a broker. Numbers are only as good as what you enter."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPORTS = Path(__file__).resolve().parent.parent / "reports"
MIN_QUOTES = 30
FIELDS = {
    "quotes": ["ts_utc", "instrument", "bid", "ask", "mid", "spread_bps", "note"],
    "trades": ["ts_utc", "instrument", "side", "entry", "exit", "fee_bps", "gross_bps", "net_bps", "note"],
    "calls": ["date", "ticker", "dir", "strength", "bucket", "open_ref", "settled", "net_bps"],
}


def _path(kind: str) -> Path:
    REPORTS.mkdir(exist_ok=True)
    return REPORTS / f"journal_{kind}.csv"


def _read(kind: str) -> pd.DataFrame:
    p = _path(kind)
    return pd.read_csv(p) if p.exists() else pd.DataFrame(columns=FIELDS[kind])


def _append(kind: str, row: dict):
    p = _path(kind); new = not p.exists()
    with p.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS[kind])
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS[kind]})


def spread_bps(bid: float, ask: float) -> float:
    if not (bid > 0 and ask >= bid):
        raise ValueError("need 0 < bid <= ask")
    return (ask - bid) / ((ask + bid) / 2) * 1e4


def trade_bps(side: str, entry: float, exit_: float, fee_bps: float = 0.0) -> tuple[float, float]:
    d = {"buy": 1, "sell": -1}[side.lower()]
    gross = d * (exit_ / entry - 1) * 1e4
    return gross, gross - fee_bps


def log_quote(instrument, bid, ask, note=""):
    sp = spread_bps(bid, ask)
    _append("quotes", {"ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "instrument": instrument.upper(),
                       "bid": bid, "ask": ask, "mid": (bid + ask) / 2, "spread_bps": round(sp, 2), "note": note})
    return sp


def log_trade(instrument, side, entry, exit_, fee_bps=0.0, note=""):
    g, n = trade_bps(side, entry, exit_, fee_bps)
    _append("trades", {"ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "instrument": instrument.upper(),
                       "side": side.lower(), "entry": entry, "exit": exit_, "fee_bps": fee_bps,
                       "gross_bps": round(g, 1), "net_bps": round(n, 1), "note": note})
    return g, n


def calibrate() -> dict:
    q = _read("quotes")
    out = {}
    for inst, g in q.groupby("instrument"):
        out[inst] = {"n": len(g), "median_bps": round(float(g["spread_bps"].median()), 2),
                     "p90_bps": round(float(g["spread_bps"].quantile(0.9)), 2), "enough": len(g) >= MIN_QUOTES}
    return out


def stats(net: pd.Series) -> dict:
    n = len(net)
    t = float(net.mean() / (net.std(ddof=1) / np.sqrt(n))) if n > 2 and net.std() > 0 else 0.0
    return {"n": n, "win%": round(100 * float((net > 0).mean()), 1) if n else 0.0, "avg_bps": round(float(net.mean()), 1) if n else 0.0, "t": round(t, 2)}


def log_call():
    from . import daycall
    fr = daycall.frames(refresh=True); t = daycall.table(fr); p = daycall.daily_picks(t)
    day = max(f.index[-1] for f in fr.values()); pick = p[p["date"] == day]
    if pick.empty:
        print(f"{day.date()}: NO TRADE logged (nothing scored >= {daycall.MIN_STRENGTH})"); return
    r = pick.iloc[0]
    calls = _read("calls")
    if len(calls) and (calls["date"].astype(str) == str(day.date())).any():
        print(f"{day.date()} already logged"); return
    _append("calls", {"date": day.date(), "ticker": r["ticker"], "dir": int(r["dir"]), "strength": round(r["strength"], 2),
                      "bucket": daycall.bucket(r["strength"]), "open_ref": round(r["open"], 4), "settled": 0})
    print(f"logged PAPER {'BUY' if r['dir'] > 0 else 'SELL'} {r['ticker']} for {day.date()}")


def settle():
    from . import daycall
    calls = _read("calls")
    if calls.empty:
        print("no calls logged"); return
    fr = daycall.frames(refresh=True); t = daycall.table(fr)
    for i, c in calls[calls["settled"] == 0].iterrows():
        m = t[(t["ticker"] == c["ticker"]) & (t["date"] == pd.Timestamp(c["date"]))]
        if len(m) and pd.Timestamp(c["date"]) < max(f.index[-1] for f in fr.values()) + pd.Timedelta(days=1):
            calls.loc[i, ["settled", "net_bps"]] = [1, round(float(m.iloc[0]["ret"]) * 1e4, 1)]
    calls.to_csv(_path("calls"), index=False)


def report():
    q, tr, ca = _read("quotes"), _read("trades"), _read("calls")
    print("== Revolut spreads (from your quotes) ==")
    cal = calibrate()
    for k, v in cal.items():
        flag = "" if v["enough"] else f"  (need {MIN_QUOTES}+ quotes before trusting; have {v['n']})"
        print(f"  {k}: median {v['median_bps']} bps | p90 {v['p90_bps']} bps{flag}")
    if not cal:
        print("  none yet: python -m analyst journal quote --instrument US500 --bid 7720.1 --ask 7721.0")
    if cal and all(v["enough"] for v in cal.values()):
        print("  -> update PROFILES['revolut'].spread_bps in analyst/cfd.py to the median above, then re-run backtest/arena.")
    print("\n== Your real fills ==")
    print("  " + (str(stats(tr["net_bps"])) if len(tr) else "none yet"))
    print("\n== Forward paper track record of the daily call (settled from real prices) ==")
    s = ca[ca["settled"] == 1]
    print("  " + (str(stats(s["net_bps"].astype(float))) if len(s) else "none settled yet"))
    print("  Judge the system only when n >= 100 settled calls; fewer than that is noise.")
