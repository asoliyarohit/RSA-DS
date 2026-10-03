"""Live trade plan for the two daily decision points. Deterministic; the human executes."""
from __future__ import annotations

import pandas as pd

from . import data, features
from .strategies import CloseParams, OpenParams, _direction_close, _direction_open


def _plan(name, f, i, d, stop_pct, equity, risk, lev, exit_rule):
    px = float(f["close"].iloc[i]) if name == "CLOSE" else float(f["open"].iloc[i])
    notional = min(risk / stop_pct, lev) * equity
    stop_px = px * (1 - d * stop_pct) if name == "OPEN" else None
    return (f"  {'BUY ' if d > 0 else 'SELL'} {name}: ref {px:,.2f} | notional ${notional:,.0f} ({notional / equity:.1f}x equity) "
            f"| margin ${notional / lev:,.0f} | stress loss ${notional * stop_pct:,.0f} ({notional * stop_pct / equity:.1%} of equity)"
            + (f" | HARD STOP {stop_px:,.2f}" if stop_px else " | NO stop possible overnight: gap risk is real")
            + f" | exit: {exit_rule}")


def live(args):
    from .cli import _train_test

    rows, _, cfd = _train_test(args)
    risk = args.risk[0]
    print(f"Account ${args.equity:,.0f} | risk/trade {risk:.0%} | leverage cap {cfd.leverage:g}x\n")
    vix = data.load(data.VIX, refresh=True)["close"]
    for sym, name in data.INSTRUMENTS.items():
        f = features.build(data.load(sym, refresh=True), vix)
        last = f.index[-1]
        stale = (pd.Timestamp.today().normalize() - last).days
        print(f"{name} ({sym}) bar {last.date()}" + (f"  [STALE {stale}d - market closed/holiday?]" if stale > 3 else ""))
        for r in (x for x in rows if x["instrument"] == name):
            if not r["PASSES_GATE"]:
                print(f"  {r['setup']}: no validated edge -> NO TRADE"); continue
            if r["setup"] == "CLOSE":
                p = CloseParams(**r["params"]); d = float(_direction_close(f.tail(1), p)[0])
                st = p.stress_atr * float(f["atr_c"].iloc[-1])
                print(_plan("CLOSE", f, -1, d, st, args.equity, risk, cfd.leverage, "SELL at next open") if d else "  CLOSE: conditions not met -> NO TRADE")
            else:
                p = OpenParams(**r["params"]); d = float(_direction_open(f.tail(1), p)[0])
                st = p.stop_atr * float(f["atr_o"].iloc[-1])
                print(_plan("OPEN", f, -1, d, st, args.equity, risk, cfd.leverage, "flat at close") if d else "  OPEN: conditions not met -> NO TRADE")
