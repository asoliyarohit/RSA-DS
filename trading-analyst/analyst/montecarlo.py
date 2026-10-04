"""Goal solver: probability of turning `start` into `target` under a risk setting.

Block-bootstraps historical trade slots (keeps streaks), applies the SAME sizing/leverage maths as the
backtest, and sweeps risk-per-trade so the trade-off between speed and ruin is explicit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .account import pack_slots, throttle_mult
from .cfd import equity_factor


def simulate(trades, risk_pct, leverage, years, start=1000.0, target=100_000.0, ruin_frac=0.10,
             paths=4000, block=10, throttle=False, seed=7):
    _, ret, stop, mask, lev = pack_slots(trades, with_lev=True, default_lev=leverage)
    n = len(ret)
    span_years = max((pd.to_datetime(trades["date"]).max() - pd.to_datetime(trades["date"]).min()).days / 365.25, 1e-9)
    steps = int(round(n / span_years * years))
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(steps / block))
    starts = rng.integers(0, max(n - block, 1), size=(paths, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(paths, -1)[:, :steps]
    e = np.full(paths, start); peak = e.copy()
    hit = np.zeros(paths, bool); ruined = np.zeros(paths, bool); t_hit = np.full(paths, np.nan)
    for s in range(steps):
        i = idx[:, s]
        dd = 1 - e / peak
        f = equity_factor(ret[i], stop[i], mask[i], risk_pct * throttle_mult(dd, throttle), lev[i])
        e = np.where(hit | ruined, e, e * f)
        peak = np.maximum(peak, e)
        new_hit = (~hit) & (~ruined) & (e >= target)
        t_hit[new_hit] = (s + 1) / steps * years
        hit |= new_hit
        ruined |= (~hit) & (e <= start * ruin_frac)
    return {
        "risk_pct": risk_pct, "p_goal": float(hit.mean()), "p_ruin": float(ruined.mean()),
        "median_end": float(np.median(e)), "median_years_to_goal": float(np.nanmedian(t_hit)) if hit.any() else float("nan"),
        "p10_end": float(np.percentile(e, 10)), "p90_end": float(np.percentile(e, 90)),
    }


def sweep(trades, leverage, years, throttle=False, risks=(0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.20, 0.30), **kw):
    return pd.DataFrame([simulate(trades, r, leverage, years, throttle=throttle, **kw) for r in risks])
