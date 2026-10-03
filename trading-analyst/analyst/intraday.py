"""Intraday tests on FREE data (yfinance: 5m = last 60 trading days, 60m = ~730 trading days) + a daily archive collector.

PRE-REGISTERED (written before any result was seen; 4 trials total, no tuning):
  T1 GAO-FOLLOW (60m bars, ~730 days): direction = sign(first-hour return 9:30-10:30). Enter the 15:30 bar open, exit at the 16:00 close.
  T2 GAO-FADE   : the mirror of T1.
  T3 ORB-BREAK  (5m bars, 60 days): opening range = first 6 bars (9:30-9:55). First 5m bar from 10:00 whose CLOSE breaks the range sets direction;
                 enter next bar's open, stop at the opposite end of the range, exit at the 15:55-bar close.
  T4 ORB-FADE   : mirror of T3 (enter against the break, stop at the break extreme +1 range... NOT run: only the stop-less mirror is meaningless).  -> dropped, counted as not tested.
Instruments: SPY, QQQ, DIA (index CFD proxies, cost 4bps round trip incl. slippage: judge INDEX class) and GLD (gold, 7bps).
Kill rule: |mean| below 2 standard errors or net <= 8 bps => no edge. Power is reported: with few independent days only big edges are detectable."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ARCHIVE = Path(__file__).resolve().parent.parent / "data" / "intraday"
TICKERS = ["SPY", "QQQ", "DIA", "GLD"]
COST_BPS = {"SPY": 4.0, "QQQ": 4.0, "DIA": 4.0, "GLD": 7.0}


def _download(sym: str, interval: str, period: str) -> pd.DataFrame:
    import yfinance as yf

    d = yf.download(sym, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d[["Open", "High", "Low", "Close"]].rename(columns=str.lower).dropna()
    d.index = d.index.tz_convert("America/New_York")
    return d


def collect():
    """Append the latest 5m/60m bars to the local archive so history keeps growing (free data only keeps 60 days of 5m)."""
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for s in TICKERS:
        for iv, per in (("5m", "60d"), ("60m", "730d")):
            new = _download(s, iv, per)
            p = ARCHIVE / f"{s}_{iv}.csv"
            if p.exists():
                old = pd.read_csv(p, index_col=0, parse_dates=True)
                old.index = pd.to_datetime(old.index, utc=True).tz_convert("America/New_York")
                new = pd.concat([old, new])
                new = new[~new.index.duplicated(keep="last")].sort_index()
            new.to_csv(p)
            print(f"{s} {iv}: {len(new)} bars, {new.index.min().date()} -> {new.index.max().date()}")


def _load(sym, iv):
    p = ARCHIVE / f"{sym}_{iv}.csv"
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    d.index = pd.to_datetime(d.index, utc=True).tz_convert("America/New_York")
    return d


def gao(sym):
    d = _load(sym, "60m"); rows = []
    for day, g in d.groupby(d.index.date):
        g = g.sort_index()
        if len(g) < 7 or g.index[0].strftime("%H:%M") != "09:30" or g.index[-1].strftime("%H:%M") != "15:30":
            continue
        r1 = g["close"].iloc[0] / g["open"].iloc[0] - 1
        rl = g["close"].iloc[-1] / g["open"].iloc[-1] - 1
        rows.append({"date": pd.Timestamp(day), "sym": sym, "r1": r1, "rlast": rl})
    return pd.DataFrame(rows)


def orb(sym):
    d = _load(sym, "5m"); rows = []
    for day, g in d.groupby(d.index.date):
        g = g.sort_index()
        if len(g) < 70 or g.index[0].strftime("%H:%M") != "09:30":
            continue
        orh, orl = g["high"].iloc[:6].max(), g["low"].iloc[:6].min()
        rest = g.iloc[6:]
        dirn, k = 0, None
        for j in range(len(rest) - 1):
            c = rest["close"].iloc[j]
            if c > orh: dirn, k = 1, j + 1; break
            if c < orl: dirn, k = -1, j + 1; break
        if not dirn:
            continue
        entry = rest["open"].iloc[k]; stop = orl if dirn > 0 else orh
        exit_px = rest["close"].iloc[-1]
        for j in range(k, len(rest)):
            if (dirn > 0 and rest["low"].iloc[j] <= stop) or (dirn < 0 and rest["high"].iloc[j] >= stop):
                exit_px = stop; break
        rows.append({"date": pd.Timestamp(day), "sym": sym, "gross": dirn * (exit_px / entry - 1)})
    return pd.DataFrame(rows)


def summarize(name, daily_bps: pd.Series):
    n = len(daily_bps)
    if n < 5:
        return f"{name}: n={n} (too few)"
    m, se = float(daily_bps.mean()), float(daily_bps.std(ddof=1) / np.sqrt(n))
    h = n // 2
    return (f"{name}: n_days={n} | net {m:+.1f} bps/day | SE {se:.1f} | t {m / se:+.2f} | 95% CI [{m - 1.96 * se:+.1f}, {m + 1.96 * se:+.1f}] | "
            f"win {100 * float((daily_bps > 0).mean()):.0f}% | halves {daily_bps.iloc[:h].mean():+.1f}/{daily_bps.iloc[h:].mean():+.1f} | detectable edge (2xSE) ~{2 * se:.1f} bps")


def test():
    g = pd.concat([gao(s) for s in TICKERS]); o = pd.concat([orb(s) for s in TICKERS])
    cost = g["sym"].map(COST_BPS) / 1e4
    for name, sign in (("T1 GAO-FOLLOW (idx+gold)", 1), ("T2 GAO-FADE", -1)):
        net = sign * np.sign(g["r1"]) * g["rlast"] - cost
        for label, mask in (("all", g["sym"].notna()), ("indices only", g["sym"].isin(["SPY", "QQQ", "DIA"]))):
            s = (net[mask.values].groupby(g["date"][mask.values].values).mean() * 1e4).sort_index()
            print(summarize(f"{name} [{label}]", pd.Series(s.values)))
    cost_o = o["sym"].map(COST_BPS) / 1e4
    net_o = o["gross"] - cost_o
    for label, mask in (("all", o["sym"].notna()), ("indices only", o["sym"].isin(["SPY", "QQQ", "DIA"]))):
        s = (net_o[mask.values].groupby(o["date"][mask.values].values).mean() * 1e4).sort_index()
        print(summarize(f"T3 ORB-BREAK [{label}]", pd.Series(s.values)))
