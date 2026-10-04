"""Sequential compounding account with leverage, risk sizing and an optional drawdown throttle."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .cfd import equity_factor


def throttle_mult(dd: np.ndarray | float, on: bool):
    """Cut risk while in drawdown: 100% -> 50% (>15% dd) -> 25% (>30% dd)."""
    if not on:
        return 1.0
    return np.where(dd > 0.30, 0.25, np.where(dd > 0.15, 0.5, 1.0))


def pack_slots(trades: pd.DataFrame, with_lev: bool = False, default_lev: float = 5.0):
    """Group trades into slots -> padded arrays [n_slots, k]."""
    t = trades.sort_values(["slot"]).reset_index(drop=True)
    slots = t["slot"].to_numpy()
    uniq, start = np.unique(slots, return_index=True)
    counts = np.diff(np.append(start, len(t)))
    k = int(counts.max()) if len(counts) else 1
    ret = np.zeros((len(uniq), k)); stop = np.ones((len(uniq), k)); mask = np.zeros((len(uniq), k))
    lev = np.full((len(uniq), k), float(default_lev))
    has_lev = "lev" in t.columns
    for i, (s, c) in enumerate(zip(start, counts)):
        ret[i, :c] = t["ret"].to_numpy()[s:s + c]
        stop[i, :c] = t["stop_pct"].to_numpy()[s:s + c]
        mask[i, :c] = 1
        if has_lev:
            lev[i, :c] = t["lev"].to_numpy()[s:s + c]
    dates = t.groupby("slot")["date"].first().to_numpy()
    return (dates, ret, stop, mask, lev) if with_lev else (dates, ret, stop, mask)


def run(trades: pd.DataFrame, risk_pct: float, leverage: float, start: float = 1000.0, throttle: bool = False):
    dates, ret, stop, mask, lev = pack_slots(trades, with_lev=True, default_lev=leverage)
    eq = np.empty(len(dates)); e, peak = start, start
    for i in range(len(dates)):
        dd = 1 - e / peak
        e *= float(equity_factor(ret[i], stop[i], mask[i], risk_pct * throttle_mult(dd, throttle), lev[i]))
        peak = max(peak, e); eq[i] = e
        if e <= 0:
            eq[i:] = 0; break
    return pd.Series(eq, index=pd.to_datetime(dates), name="equity")


def stats(trades: pd.DataFrame, eq: pd.Series, start: float = 1000.0) -> dict:
    yrs = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    end = float(eq.iloc[-1])
    dd = float((1 - eq / eq.cummax()).max())
    r = trades["ret"]
    return {
        "trades": int(len(trades)), "years": round(yrs, 2),
        "win_rate": round(float((r > 0).mean()), 3),
        "avg_ret_bps": round(float(r.mean() * 1e4), 2),
        "t_stat": round(float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 and r.std() > 0 else 0.0, 2),
        "profit_factor": round(float(r[r > 0].sum() / max(-r[r < 0].sum(), 1e-12)), 2),
        "end_equity": round(end, 2),
        "cagr": round(float((end / start) ** (1 / yrs) - 1), 3) if end > 0 else -1.0,
        "max_dd": round(dd, 3),
    }
