"""Step 1 (H1/H2/H3): does holding the TSMOM direction each day, via CLOSE (overnight) and OPEN (intraday) legs, earn more
than the per-slot cost? Per class, per leg, per year and per regime. Signal = sign of 12-1 month return (MOP 2012), also
an equal-weight vote of 1/3/6/12-month signs. Reported gross and net of the judge's cost model. No tuning here."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from arena.trend_crisis.common import *
from arena.trend_crisis.panel import build, LOOKS

fr = load_dev()
P = build(fr, INDICES + COMMOD + STOCKS)
P["year"] = P["date"].dt.year
# signals for the CLOSE slot on d: *_c (known at close d).  For the OPEN slot on d: previous day's _c (shift within inst).
g = P.groupby("inst")
for col in [c for c in P.columns if c.endswith("_c")]:
    P[col.replace("_c", "_o")] = g[col].shift(1)
P["vote_c"] = sum(np.sign(P[f"z{L}_c"]) for L in LOOKS) / len(LOOKS)
P["vote_o"] = sum(np.sign(P[f"z{L}_o"]) for L in LOOKS) / len(LOOKS)

def leg_pnl(P, sig, leg):
    d = np.sign(P[sig]).fillna(0)
    if leg == "CLOSE":
        gross = d * P["on_ret"]
        net = gross - P["rt"] * (d != 0) + np.where(d > 0, P["fin_long"], np.where(d < 0, P["fin_short"], 0))
    else:
        gross = d * P["in_ret"]; net = gross - P["rt"] * (d != 0)
    return d, gross, net

def summarise(mask, label):
    rows = []
    for cls in ("index", "gold", "commod", "stock"):
        for leg in ("CLOSE", "OPEN"):
            for sig in ("z252x21", "vote"):
                s = sig + ("_c" if leg == "CLOSE" else "_o")
                sub = P[mask & (P.cls == cls) & P[s].notna()]
                d, gross, net = leg_pnl(sub, s, leg)
                keep = d != 0
                n = int(keep.sum())
                if n < 50: continue
                nt = net[keep]; gr = gross[keep]
                rows.append(dict(regime=label, cls=cls, leg=leg, sig=sig, n=n, gross_bps=gr.mean()*1e4, net_bps=nt.mean()*1e4,
                                 t_net=nt.mean()/nt.std()*np.sqrt(n), short_share=float((d[keep] < 0).mean()),
                                 net_short_bps=nt[d[keep] < 0].mean()*1e4 if (d[keep] < 0).any() else np.nan,
                                 net_long_bps=nt[d[keep] > 0].mean()*1e4))
    return pd.DataFrame(rows)

pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
print("=== ALL DEV (2001-2022) ===")
print(summarise(P.date.notna(), "all").round(2).to_string(index=False))
bear = {"2008": (P.date >= "2008-01-01") & (P.date <= "2008-12-31"),
        "2020Q1": (P.date >= "2020-02-20") & (P.date <= "2020-03-31"),
        "2022": (P.date >= "2022-01-01") & (P.date <= "2022-12-31"),
        "2000-02 bear": (P.date >= "2000-09-01") & (P.date <= "2002-12-31"),
        "bull 2013-2017": (P.date >= "2013-01-01") & (P.date <= "2017-12-31")}
for k, m in bear.items():
    print(f"=== {k} ===")
    print(summarise(m, k).round(2).to_string(index=False))

print("=== per-year net bps, 12-1 sign, by class and leg (n in brackets) ===")
tab = {}
for cls in ("index", "gold", "commod", "stock"):
    for leg in ("CLOSE", "OPEN"):
        s = "z252x21" + ("_c" if leg == "CLOSE" else "_o")
        sub = P[(P.cls == cls) & P[s].notna()]
        d, gross, net = leg_pnl(sub, s, leg)
        tab[(cls, leg)] = net[d != 0].groupby(sub.year[d != 0]).mean() * 1e4
print(pd.DataFrame(tab).round(1).to_string())

print("=== VIX regime (vix at decision time) net bps 12-1 sign ===")
P["vixb_c"] = pd.cut(P["vix_c"], [0, 15, 20, 25, 35, 100]); P["vixb_o"] = pd.cut(P["vix_o"], [0, 15, 20, 25, 35, 100])
rows = []
for cls in ("index", "gold", "commod", "stock"):
    for leg in ("CLOSE", "OPEN"):
        suf = "_c" if leg == "CLOSE" else "_o"
        sub = P[(P.cls == cls) & P["z252x21" + suf].notna()]
        d, gross, net = leg_pnl(sub, "z252x21" + suf, leg)
        for b, grp in net[d != 0].groupby(sub["vixb" + suf][d != 0], observed=True):
            rows.append(dict(cls=cls, leg=leg, vix=str(b), n=len(grp), net_bps=grp.mean()*1e4, t=grp.mean()/grp.std()*np.sqrt(len(grp))))
print(pd.DataFrame(rows).round(2).to_string(index=False))
P.to_pickle("/tmp/claude-0/-home-user-RSA-DS/54141183-5e85-528e-8612-315d8d6f3985/scratchpad/panel.pkl")
