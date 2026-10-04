"""The two CFD setups.

A  OPEN  : enter at the open, hard stop intraday, flat at the close (pure day trade).
B  CLOSE : enter near the close (~15:55 ET), sell at next open (overnight, no stop: gap risk is modelled).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from .cfd import CFDSpec


@dataclass(frozen=True)
class OpenParams:
    mode: str = "fade"        # fade the gap, or follow it
    gap_atr: float = 0.5      # gap size in ATR units needed to trigger
    trend: bool = True        # trade only in the direction of the 200d trend
    both_sides: bool = False  # allow shorts
    stop_atr: float = 1.0     # intraday stop distance in ATRs
    vix_max: float | None = None


@dataclass(frozen=True)
class CloseParams:
    mode: str = "ibs"         # ibs (close location in day's range) or rsi2
    thr: float = 0.2          # ibs<thr buy ; rsi2<thr*100 buy (thr in 0..1 for both)
    trend: bool = True
    both_sides: bool = False
    stress_atr: float = 1.5   # sizing-only: assumed adverse overnight move in ATRs


def _direction_open(f: pd.DataFrame, p: OpenParams) -> np.ndarray:
    g = f["gap_atr_o"].to_numpy()
    sign = -np.sign(g) if p.mode == "fade" else np.sign(g)
    d = np.where(np.abs(g) >= p.gap_atr, sign, 0.0)
    if not p.both_sides:
        d = np.where(d > 0, d, 0.0)
    if p.trend:
        d = np.where(d == f["trend_o"].to_numpy(), d, 0.0)
    if p.vix_max is not None and "vix_o" in f:
        d = np.where(f["vix_o"].to_numpy() <= p.vix_max, d, 0.0)
    return np.nan_to_num(d)


def _direction_close(f: pd.DataFrame, p: CloseParams) -> np.ndarray:
    if p.mode == "ibs":
        s = f["ibs_c"].to_numpy()
        long_, short_ = s < p.thr, s > 1 - p.thr
    else:
        s = f["rsi2_c"].to_numpy()
        long_, short_ = s < p.thr * 100, s > 100 - p.thr * 100
    d = np.where(long_, 1.0, 0.0)
    if p.both_sides:
        d = np.where(short_, -1.0, d)
    if p.trend:
        d = np.where(d == f["trend_c"].to_numpy(), d, 0.0)
    return np.nan_to_num(d)


def trades_open(f: pd.DataFrame, p: OpenParams, cfd: CFDSpec, instrument: str = "") -> pd.DataFrame:
    d = _direction_open(f, p)
    stop_pct = (p.stop_atr * f["atr_o"]).to_numpy()
    o, h, l, c = (f[k].to_numpy() for k in ("open", "high", "low", "close"))
    long_stop = o * (1 - stop_pct)
    short_stop = o * (1 + stop_pct)
    hit = np.where(d > 0, l <= long_stop, np.where(d < 0, h >= short_stop, False))
    stop_px = np.where(d > 0, long_stop, short_stop)
    exit_px = np.where(hit, stop_px, c)          # same-bar ambiguity resolved against us
    gross = d * (exit_px / o - 1)
    ret = gross - cfd.round_trip_cost()
    return _frame(f, d, ret, gross, stop_pct, "OPEN", instrument, hit)


def trades_close(f: pd.DataFrame, p: CloseParams, cfd: CFDSpec, instrument: str = "") -> pd.DataFrame:
    d = _direction_close(f, p)
    c = f["close"].to_numpy()
    nxt_open = f["open"].shift(-1).to_numpy()
    dates = f.index.to_numpy()
    nights = np.append((dates[1:] - dates[:-1]).astype("timedelta64[D]").astype(float), np.nan)
    gross = d * (nxt_open / c - 1)
    ret = gross - cfd.round_trip_cost() + cfd.financing(d, nights)
    stop_pct = (p.stress_atr * f["atr_c"]).to_numpy()
    out = _frame(f, d, ret, gross, stop_pct, "CLOSE", instrument, np.zeros(len(f), bool))
    return out


def _frame(f, d, ret, gross, stop_pct, setup, instrument, stopped) -> pd.DataFrame:
    t = pd.DataFrame({"date": f.index, "dir": d, "ret": ret, "gross": gross, "stop_pct": stop_pct,
                      "stopped": stopped, "setup": setup, "instrument": instrument})
    t = t[(t["dir"] != 0) & t["ret"].notna() & t["stop_pct"].notna()].reset_index(drop=True)
    # slot order: day t open (0) precedes day t close entry (1); B exits before next day's A enters
    t["slot"] = [(dt.toordinal() * 2) + (0 if s == "OPEN" else 1) for dt, s in zip(t["date"], t["setup"])]
    return t


def params_dict(p) -> dict:
    return asdict(p)
