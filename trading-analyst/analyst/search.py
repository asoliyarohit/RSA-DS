"""Small grid + walk-forward: choose on TRAIN only, report untouched TEST."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .cfd import CFDSpec
from .strategies import CloseParams, OpenParams, trades_close, trades_open

SPLIT = pd.Timestamp("2015-01-01")
MIN_TRAIN_TRADES = 80


def grid_open():
    for m, g, tr, bs, st in itertools.product(["fade", "follow"], [0.2, 0.3, 0.5, 0.75, 1.0], [True, False], [False, True], [0.75, 1.0, 1.5]):
        yield OpenParams(mode=m, gap_atr=g, trend=tr, both_sides=bs, stop_atr=st)


def grid_close():
    for m, t, tr, bs in itertools.product(["ibs", "rsi2"], [0.1, 0.2, 0.3], [True, False], [False, True]):
        yield CloseParams(mode=m, thr=t, trend=tr, both_sides=bs)


def _t(r: pd.Series) -> float:
    return float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 and r.std() > 0 else -9.0


def select(f: pd.DataFrame, setup: str, cfd: CFDSpec, instrument: str):
    gen, fn = (grid_open, trades_open) if setup == "OPEN" else (grid_close, trades_close)
    best, best_t, n_tested = None, -9.0, 0
    for p in gen():
        n_tested += 1
        tr = fn(f, p, cfd, instrument)
        tr = tr[tr["date"] < SPLIT]
        if len(tr) < MIN_TRAIN_TRADES:
            continue
        t = _t(tr["ret"])
        if t > best_t:
            best, best_t = p, t
    return best, best_t, n_tested


def evaluate(f, setup, p, cfd, instrument):
    fn = trades_open if setup == "OPEN" else trades_close
    tr = fn(f, p, cfd, instrument)
    return tr[tr["date"] < SPLIT], tr[tr["date"] >= SPLIT]
