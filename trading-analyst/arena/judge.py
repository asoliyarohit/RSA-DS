"""Arena judge. A competitor supplies ONLY decisions (signals); the judge recomputes every fill from raw
prices with one cost model, tests for lookahead, corrects for multiple testing, and scores the user's goal.

strategy.py contract:
    UNIVERSE: list[str]                       # Yahoo tickers (free); "^VIX" is always added
    N_TRIALS: int                             # honest count of configs/ideas tried (for deflated Sharpe)
    def signals(frames: dict[str, DataFrame]) -> DataFrame
        columns: instrument, date_in, kind ('OPEN'|'CLOSE'), dir (+1/-1), stop_pct (>0), score (higher = stronger)
        OPEN  = enter at that day's open, hard stop at stop_pct, exit at that day's close
        CLOSE = enter at that day's close (~15:55), exit at NEXT trading day's open, no stop (gap risk is real)
    frames[ticker]: open/high/low/close (dividend-adjusted), daily, causal use only.
Usage:  python -m arena.judge arena/NAME/strategy.py --dev      (data stops 2022-12-31)
        python -m arena.judge arena/NAME/strategy.py --final    (judge/owner only: full data, scores 2023+)
"""
from __future__ import annotations

import argparse, importlib.util, json, sys
from statistics import NormalDist

import numpy as np
import pandas as pd

from analyst import data
from analyst.account import pack_slots, run, stats
from analyst.cfd import PROFILES, CFDSpec
from analyst.montecarlo import simulate

CUTOFF = pd.Timestamp("2022-12-31")
LEVERAGE = 5.0  # default only; real caps come per instrument from cost_for()
TOP_N = 3
INDEX_ETFS = {"SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "TLT", "GLD"}
STOCK_COST = CFDSpec(spread_bps=10.0, slippage_bps=3.0, leverage=LEVERAGE, benchmark=0.04, markup=0.03, commission_bps=25.0)  # Revolut equity CFD fee 0.25%/side
ETF_COST = CFDSpec(**{**PROFILES["revolut"].__dict__, "leverage": LEVERAGE})
N = NormalDist()


MAJOR_INDEX = {"SPY", "QQQ", "DIA", "EWG", "FEZ", "EWJ", "EWU", "^GSPC", "^NDX", "^DJI", "^GDAXI", "^N225", "^FTSE", "^STOXX50E"}
GOLD = {"GLD", "GC=F"}
# Leverage tiers VERIFIED in Revolut's CFD cost report: stocks 1:5, major indices 1:20, gold 1:20, other commodities 1:10, crypto 1:2.
# FX is 1:20 for minors (majors may be higher); we use 20. Spread/slippage numbers below are ASSUMPTIONS until the journal has real quotes.
CRYPTO_COST = CFDSpec(spread_bps=30.0, slippage_bps=5.0, leverage=2.0, benchmark=0.04, markup=0.03)
FX_COST = CFDSpec(spread_bps=2.0, slippage_bps=0.5, leverage=20.0, benchmark=0.0, markup=0.03)
GOLD_COST = CFDSpec(spread_bps=5.0, slippage_bps=1.0, leverage=20.0, benchmark=0.04, markup=0.03)
COMMODITY_COST = CFDSpec(spread_bps=8.0, slippage_bps=2.0, leverage=10.0, benchmark=0.04, markup=0.03)
INDEX_COST = CFDSpec(**{**PROFILES["revolut_index"].__dict__})
STOCK_COST = CFDSpec(spread_bps=10.0, slippage_bps=3.0, leverage=5.0, benchmark=0.04, markup=0.03, commission_bps=25.0)  # equity CFD fee 0.25%/side


def cost_for(t: str) -> CFDSpec:
    if t.endswith("-USD"):
        return CRYPTO_COST
    if t.endswith("=X"):
        return FX_COST
    if t in GOLD:
        return GOLD_COST
    if t.endswith("=F"):
        return COMMODITY_COST
    if t in MAJOR_INDEX:
        return INDEX_COST
    return STOCK_COST


def load_strategy(path):
    spec = importlib.util.spec_from_file_location("competitor", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def load_frames(universe, end=None):
    fr = {}
    for t in sorted(set(universe) | {"^VIX"}):
        try:
            d = data.load(t)
        except Exception as e:
            print(f"[judge] skip {t}: {e}", file=sys.stderr); continue
        fr[t] = d[d.index <= end] if end is not None else d
    return fr


def fills(sig: pd.DataFrame, frames) -> pd.DataFrame:
    """Recompute net per-notional return for each signal from raw prices. Single source of truth."""
    rows = []
    for r in sig.itertuples(index=False):
        f = frames.get(r.instrument)
        if f is None or pd.Timestamp(r.date_in) not in f.index or not (r.stop_pct > 0) or r.dir not in (1, -1):
            continue
        d = pd.Timestamp(r.date_in); i = f.index.get_loc(d); cfd = cost_for(r.instrument)
        o, h, l, c = (float(f[k].iloc[i]) for k in ("open", "high", "low", "close"))
        nxt_o = float(f["open"].iloc[i + 1]) if i + 1 < len(f) else float("nan")
        # non-positive or missing prices (e.g. WTI -$37 on 2020-04-20) make percentage returns meaningless: no fill, no phantom profit
        if min(o, h, l, c) <= 0 or (r.kind == "CLOSE" and not nxt_o > 0) or not np.isfinite([o, h, l, c]).all():
            continue
        if r.kind == "OPEN":
            stop = o * (1 - r.dir * r.stop_pct)
            hit = (l <= stop) if r.dir > 0 else (h >= stop)
            ret = max(r.dir * ((stop if hit else c) / o - 1), -1.0) - cfd.round_trip_cost()
        elif r.kind == "CLOSE":
            if i + 1 >= len(f):
                continue
            nights = float((f.index[i + 1] - d).days)
            ret = r.dir * (float(f["open"].iloc[i + 1]) / c - 1) - cfd.round_trip_cost() \
                + float(cfd.financing(np.array([r.dir]), np.array([nights]))[0])
        else:
            continue
        rows.append({"instrument": r.instrument, "date": d, "setup": r.kind, "dir": r.dir, "ret": ret, "lev": cfd.leverage,
                     "stop_pct": float(r.stop_pct), "score": float(getattr(r, "score", 0.0)),
                     "slot": d.toordinal() * 2 + (0 if r.kind == "OPEN" else 1)})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t = t.sort_values(["slot", "score"], ascending=[True, False]).groupby("slot").head(TOP_N)
    return t.sort_values("slot").reset_index(drop=True)


def _keys(s, kind=None, upto=None, strict=False):
    s = s.copy(); s["date_in"] = pd.to_datetime(s["date_in"])
    if kind:
        s = s[s["kind"] == kind]
    if upto is not None:
        s = s[s["date_in"] < upto] if strict else s[s["date_in"] <= upto]
    s = s.assign(stop_pct=s["stop_pct"].astype(float).round(6),
                 score=(s["score"].astype(float) if "score" in s else 0.0).round(6))
    return set(map(tuple, s[["instrument", "date_in", "kind", "dir", "stop_pct", "score"]].astype(str).values))


def lookahead_check(m, frames_full, n_points=6, seed=11) -> tuple[bool, str]:
    """Causality test by perturbation. For random dates T:
       (1) data <= T          : CLOSE signals dated <= T and OPEN signals dated < T must equal the full-data run.
       (2) data < T + open[T] : OPEN signals dated T (high/low/close of T hidden) must equal the full-data run.
    Any peek at tomorrow's prices, or at today's close for an open-time decision, changes the signals."""
    full = m.signals(frames_full)
    ref = frames_full[sorted(k for k in frames_full if k != "^VIX")[0]]
    idx = ref.index[(ref.index > ref.index[300]) & (ref.index <= CUTOFF)]
    rng = np.random.default_rng(seed)
    for T in rng.choice(idx, size=n_points, replace=False):
        T = pd.Timestamp(T)
        cut_close = {k: v[v.index <= T] for k, v in frames_full.items()}
        cut_open = {}
        for k, v in frames_full.items():
            w = v[v.index <= T].copy()
            if T in w.index:
                w.loc[T, ["high", "low", "close"]] = np.nan
            cut_open[k] = w
        sc, so = m.signals(cut_close), m.signals(cut_open)
        for name, got, want in (
            ("CLOSE<=T", _keys(sc, "CLOSE", T), _keys(full, "CLOSE", T)),
            ("OPEN<T", _keys(sc, "OPEN", T, True), _keys(full, "OPEN", T, True)),
            ("OPEN@T", _keys(so, "OPEN", T), _keys(full, "OPEN", T)),
        ):
            if got != want:
                return False, f"LOOKAHEAD at {T.date()} ({name}): {len(got ^ want)} signals change when future/intraday data is hidden"
    return True, ""


def dsr(r: pd.Series, n_trials: int) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) on per-slot returns."""
    T = len(r)
    if T < 20 or r.std() == 0:
        return 0.0
    sr = r.mean() / r.std(ddof=1)
    g = 0.5772156649
    sr0 = np.sqrt(1.0 / T) * ((1 - g) * N.inv_cdf(1 - 1 / max(n_trials, 2)) + g * N.inv_cdf(1 - 1 / (max(n_trials, 2) * np.e)))
    sk, ku = float(r.skew()), float(r.kurt()) + 3
    den = np.sqrt(max(1 - sk * sr + (ku - 1) / 4 * sr ** 2, 1e-9))
    return float(N.cdf((sr - sr0) * np.sqrt(T - 1) / den))


def boot_ci(r: pd.Series, B=4000, seed=1):
    rng = np.random.default_rng(seed); x = r.to_numpy()
    m = rng.choice(x, size=(B, len(x))).mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def evaluate(path, final=False):
    m = load_strategy(path)
    uni = list(m.UNIVERSE); n_trials = int(m.N_TRIALS)
    frames_full = load_frames(uni)
    frames_cut = {k: v[v.index <= CUTOFF] for k, v in frames_full.items()}
    ok, why = lookahead_check(m, frames_cut)
    out = {"strategy": str(path), "mode": "FINAL" if final else "DEV", "n_trials": n_trials, "lookahead_ok": ok, "note": why}
    frames = frames_full if final else frames_cut
    t = fills(m.signals(frames), frames)
    if t.empty:
        out["verdict"] = "NO TRADES"; return out
    lo = t if not final else t[t["date"] > CUTOFF]
    sl = lo.groupby("slot")["ret"].mean()
    out.update({"slots": int(len(sl)), "trades": int(len(lo)), "slots_per_year": round(len(sl) / max((lo.date.max() - lo.date.min()).days / 365.25, 1e-9), 1),
                "avg_bps_slot": round(float(sl.mean() * 1e4), 1), "t_slot": round(float(sl.mean() / (sl.std(ddof=1) / np.sqrt(len(sl)))), 2),
                "ci95_bps": [round(x * 1e4, 1) for x in boot_ci(sl)], "dsr": round(dsr(sl, n_trials), 3),
                "win_rate": round(float((lo.ret > 0).mean()), 3), "worst_trade_bps": round(float(lo.ret.min() * 1e4), 0),
                "top5_share_of_profit": round(float(sl.nlargest(5).sum() / sl.sum()), 2) if sl.sum() > 0 else None})
    best = None
    for risk in (0.03, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
        for th in (False, True):
            r = simulate(lo, risk, LEVERAGE, 5.0, throttle=th, paths=3000)
            r.update(throttle=th)
            eq = run(lo, risk, LEVERAGE, 1000.0, throttle=th)
            r["hist_end"] = round(float(eq.iloc[-1]), 0); r["hist_maxdd"] = round(float((1 - eq / eq.cummax()).max()), 3)
            if r["hist_maxdd"] <= 0.5 and (best is None or r["p_goal"] > best["p_goal"] or (r["p_goal"] == best["p_goal"] and r["median_end"] > best["median_end"])):
                best = r
    out["best_policy_5y"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in (best or {}).items()}
    try:
        from analyst.frontier import required_edge
        sig = float(lo["stop_pct"].median()); L = float(lo["lev"].median()); N = min(max(out["slots_per_year"], 1.0), 1000.0)
        out["required_bps_50pct_3y"] = required_edge(N, 3, sigma=sig, L=L, paths=1500)
        out["required_bps_50pct_10y"] = required_edge(N, 10, sigma=sig, L=L, paths=1500)
        out["closeness_to_10y_goal"] = round(out["avg_bps_slot"] / out["required_bps_50pct_10y"], 2)
    except Exception as e:  # never let the diagnostic break scoring
        out["frontier_error"] = str(e)
    valid = ok and out["t_slot"] > 1.65 and out["dsr"] > 0.5 and out["ci95_bps"][0] > 0 and len(sl) >= 60
    out["verdict"] = "VALID EDGE" if valid else "NOT VALIDATED (do not trade)"
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("strategy"); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dev", action="store_true"); g.add_argument("--final", action="store_true")
    a = ap.parse_args()
    print(json.dumps(evaluate(a.strategy, final=a.final), indent=1, default=str))
