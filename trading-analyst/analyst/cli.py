"""python -m analyst backtest | solve | signal"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from . import data, features
from .account import run, stats
from .cfd import PROFILES, CFDSpec
from .montecarlo import sweep
from .search import SPLIT, evaluate, select
from .strategies import CloseParams, OpenParams

REPORTS = Path(__file__).resolve().parent.parent / "reports"


def _frames(refresh=False):
    vix = data.load(data.VIX, refresh=refresh)["close"]
    return {sym: features.build(data.load(sym, refresh=refresh), vix) for sym in data.INSTRUMENTS}


def _train_test(args):
    cfd = PROFILES[args.broker]
    if args.leverage:
        cfd = CFDSpec(**{**cfd.__dict__, "leverage": args.leverage})
    frames = _frames(args.refresh)
    rows, kept = [], []
    for sym, f in frames.items():
        for setup in ("OPEN", "CLOSE"):
            p, t_train, n = select(f, setup, cfd, data.INSTRUMENTS[sym])
            if p is None:
                rows.append({"instrument": data.INSTRUMENTS[sym], "setup": setup, "PASSES_GATE": False, "note": "no param set had enough trades"}); continue
            tr, te = evaluate(f, setup, p, cfd, data.INSTRUMENTS[sym])
            t_test = (te["ret"].mean() / (te["ret"].std(ddof=1) / len(te) ** 0.5)) if len(te) > 2 else 0
            # gate: edge must exist in-sample (t>2) AND survive untouched out-of-sample (mean>0, t>1)
            ok = t_train > 2 and te["ret"].mean() > 0 and t_test > 1
            rows.append({"instrument": data.INSTRUMENTS[sym], "setup": setup, "params": asdict(p), "grid_size": n,
                         "train_n": len(tr), "train_avg_bps": round(tr["ret"].mean() * 1e4, 2), "train_t": round(t_train, 2),
                         "test_n": len(te), "test_avg_bps": round(te["ret"].mean() * 1e4, 2), "test_t": round(float(t_test), 2),
                         "PASSES_GATE": bool(ok)})
            if ok:
                kept.append(pd.concat([tr, te]))
    return rows, kept, cfd


def cmd_backtest(args):
    rows, kept, cfd = _train_test(args)
    print(f"Walk-forward (select on <{SPLIT.date()}, test untouched after). Costs: spread {cfd.spread_bps}bp RT, "
          f"slip {cfd.slippage_bps}bp/side, financing {cfd.benchmark + cfd.markup:.1%} long.")
    for r in rows:
        print(json.dumps(r))
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "walkforward.json").write_text(json.dumps(rows, indent=1))
    if not kept:
        print("\nNO setup passed the gate. Nothing is tradeable on this evidence. (This is the honest answer.)")
        return
    trades = pd.concat(kept).sort_values("date")
    trades.to_csv(REPORTS / "trades.csv", index=False)
    for risk in args.risk:
        eq = run(trades, risk, cfd.leverage, args.start, throttle=args.throttle)
        print(f"\nrisk/trade {risk:.0%}  ->", json.dumps(stats(trades, eq, args.start)))


def cmd_solve(args):
    rows, kept, cfd = _train_test(args)
    if not kept:
        print("No validated setups -> goal probability cannot be estimated honestly. Stop here."); return
    trades = pd.concat(kept).sort_values("date")
    oos = trades[trades["date"] >= SPLIT]
    for label, tr in (("ALL history (optimistic: includes train)", trades), ("OUT-OF-SAMPLE only (honest)", oos)):
        for th in (False, True):
            print(f"\n== {label} | throttle={th} | {args.start:.0f} -> {args.target:.0f} in {args.years}y | lev {cfd.leverage:g}x ==")
            print(sweep(tr, cfd.leverage, args.years, throttle=th, start=args.start, target=args.target).round(3).to_string(index=False))


def cmd_signal(args):
    from .signals import live
    live(args)


def cmd_brief(args):
    from .briefing import brief
    brief(args)


def cmd_stocks(args):
    from . import universe as u
    fr = u.load_frames(args.refresh)
    for setup in ("OPEN", "CLOSE"):
        r = u.walk_forward(fr, setup); r.pop("trades")
        print(r)


def cmd_review(args):
    from .review import review
    review(args)


def cmd_daycall(args):
    from .daycall import run
    run(args)


def main():
    ap = argparse.ArgumentParser(prog="analyst")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("backtest", cmd_backtest), ("solve", cmd_solve), ("signal", cmd_signal), ("brief", cmd_brief), ("stocks", cmd_stocks), ("review", cmd_review), ("daycall", cmd_daycall)):
        p = sp.add_parser(name); p.set_defaults(fn=fn)
        p.add_argument("--leverage", type=float, default=0.0, help="override broker leverage cap")
        p.add_argument("--broker", choices=list(PROFILES), default="revolut")
        p.add_argument("--start", type=float, default=1000.0)
        p.add_argument("--refresh", action="store_true")
        p.add_argument("--throttle", action="store_true")
        p.add_argument("--risk", type=float, nargs="+", default=[0.02, 0.05, 0.10])
        p.add_argument("--target", type=float, default=100_000.0)
        p.add_argument("--years", type=float, default=3.0)
        p.add_argument("--equity", type=float, default=1000.0)
        p.add_argument("--date", default=None, help="session to review, default last bar")
        p.add_argument("--gap-atr", dest="gap_atr", type=float, default=2.0)
    a = ap.parse_args(); a.fn(a)
