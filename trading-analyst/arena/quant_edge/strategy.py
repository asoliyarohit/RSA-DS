"""quant_edge: turn-of-month (TOM) overnight flow effect on broad US index ETFs.

Rule (frozen): on the LAST NYSE trading day of each calendar month, buy the 3 equity index/sector ETFs (of 12) that
closed lowest in their day's range (lowest IBS = (C-L)/(H-L)) at the close (~15:55 ET) and sell at the next day's open
(CLOSE slot). Nothing else. Long only. ~12 slots/year.
Rationale: month-end/start cash flows (payroll, pension and 401k contributions, fund rebalancing, window dressing)
are pre-scheduled, and the new month's demand hits at the first open. Documented since Ariel (1987), Lakonishok &
Smidt (1988), McConnell & Xu (2008); the overnight leg is where the effect concentrates on dev data.

Causality: "last trading day of month" is decided from a rule-based NYSE holiday calendar (weekends, Good Friday,
Memorial Day and the other scheduled holidays), never from the future rows of the price index. Sizing hint
stop_pct = 1 x ATR14 (CLOSE trades have no stop; the judge uses stop_pct only to size).
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import pandas as pd
from pandas.tseries.holiday import (GoodFriday, USLaborDay, USMartinLutherKingJr, USMemorialDay,
                                    USPresidentsDay, USThanksgivingDay)

UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU"]
N_TRIALS = 90   # honest count incl. all dead ends on the 132-stock + 14-ETF research universe (see REPORT.md)


def _observed(d: date) -> date:
    return d - timedelta(1) if d.weekday() == 5 else d + timedelta(1) if d.weekday() == 6 else d


@lru_cache(maxsize=None)
def _nyse_holidays(year: int) -> frozenset:
    rules = [GoodFriday, USMemorialDay, USLaborDay, USMartinLutherKingJr, USPresidentsDay, USThanksgivingDay]
    h = set()
    for r in rules:
        h |= {x.date() for x in r.dates(f"{year}-01-01", f"{year}-12-31")}
    for m, d in ((7, 4), (12, 25)):
        h.add(_observed(date(year, m, d)))
    ny = date(year, 1, 1)
    if ny.weekday() != 5:          # NYSE does not close Dec 31 when Jan 1 falls on a Saturday
        h.add(_observed(ny))
    if year >= 2022:
        h.add(_observed(date(year, 6, 19)))
    return frozenset(h)


def is_last_trading_day_of_month(ts) -> bool:
    d = pd.Timestamp(ts).date()
    hol = _nyse_holidays(d.year)
    x = d + timedelta(1)
    while x.month == d.month:
        if x.weekday() < 5 and x not in hol:
            return False
        x += timedelta(1)
    return True


def signals(frames):
    rows = []
    for s in UNIVERSE:
        f = frames.get(s)
        if f is None or f.empty:
            continue
        pc = f["close"].shift()
        tr = pd.concat([f["high"] - f["low"], (f["high"] - pc).abs(), (f["low"] - pc).abs()], axis=1).max(axis=1)
        atr = (tr.rolling(14).mean() / f["close"])
        for d in f.index:
            a = atr.get(d)
            if pd.notna(a) and a > 0 and pd.notna(f["close"].get(d)) and is_last_trading_day_of_month(d):
                rng = f["high"].get(d) - f["low"].get(d)
                ibs = (f["close"].get(d) - f["low"].get(d)) / rng if rng > 0 else 0.5
                rows.append((s, d, "CLOSE", 1, float(a), float(1.0 - ibs)))
    return pd.DataFrame(rows, columns=["instrument", "date_in", "kind", "dir", "stop_pct", "score"])
