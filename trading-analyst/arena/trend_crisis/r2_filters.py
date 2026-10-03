"""Step 2 (H4): can selectivity lift the daily-capture TSMOM above cost? Pre-registered filters, each one trial:
  F1 signal strength |composite z| buckets   F2 relative-vol buckets   F3 full agreement of 4 lookbacks + MA200
  F4 crisis filter: VIX>25 & VIX/VIX3M>1 -> trade TSMOM direction   F5 top-3-by-|z| per slot across cheap classes (judge mechanic)
  F6 breadth: short book only when <30% of index ETFs above MA200, long book only when >70%
Cheap classes only (index/gold/commod); stocks cost 66 bps and are dead on arrival (r1)."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from arena.trend_crisis.common import *
from arena.trend_crisis.panel import LOOKS, breadth

SP = "/tmp/claude-0/-home-user-RSA-DS/54141183-5e85-528e-8612-315d8d6f3985/scratchpad/"
P = pd.read_pickle(SP + "panel.pkl")
P = P[P.cls != "stock"].copy()
fr = load_dev(INDICES)
br = breadth(fr, INDICES).rename("br_c").reset_index().rename(columns={"index": "date"})
P = P.merge(br, on="date", how="left"); P["br_o"] = P.groupby("inst")["br_c"].shift(1)
for suf in ("_c", "_o"):
    P["comp" + suf] = sum(P[f"z{L}{suf}"].clip(-3, 3) for L in LOOKS) / len(LOOKS)
    P["agree" + suf] = (sum(np.sign(P[f"z{L}{suf}"]) for L in LOOKS).abs() == 4) & (np.sign(P["ma200" + suf]) == np.sign(P["comp" + suf]))
    P["rvol" + suf] = P["vol" + suf] / P["vol_long" + suf]
    P["crisis" + suf] = (P["vix" + suf] > 25) & (P["vterm" + suf] > 1.0)

def pnl(sub, leg, dcol):
    d = np.sign(sub[dcol]).fillna(0)
    if leg == "CLOSE":
        net = d * sub["on_ret"] - sub["rt"] * (d != 0) + np.where(d > 0, sub["fin_long"], np.where(d < 0, sub["fin_short"], 0))
    else:
        net = d * sub["in_ret"] - sub["rt"] * (d != 0)
    return d, net

def rep(tag, sub, leg, dcol):
    d, net = pnl(sub, leg, dcol); k = d != 0; n = int(k.sum())
    if n < 30: return
    x = net[k]
    print(f"{tag:55s} {leg:5s} n={n:6d} net={x.mean()*1e4:7.2f} t={x.mean()/x.std()*np.sqrt(n):6.2f} shortshare={(d[k]<0).mean():.2f} "
          f"net_short={x[d[k]<0].mean()*1e4 if (d[k]<0).any() else float('nan'):7.2f}")

pd.set_option("display.width", 250)
for leg, suf in (("CLOSE", "_c"), ("OPEN", "_o")):
    print(f"\n##### leg {leg} #####")
    P["ab"] = pd.cut(P["comp" + suf].abs(), [0, 0.25, 0.5, 0.75, 1.0, 1.5, 3.1])
    for b, g in P.groupby("ab", observed=True):
        rep(f"F1 |comp| in {b}", g, leg, "comp" + suf)
    P["vb"] = pd.cut(P["rvol" + suf], [0, 0.7, 0.9, 1.1, 1.4, 2.0, 10])
    for b, g in P.groupby("vb", observed=True):
        rep(f"F2 rvol in {b}", g, leg, "comp" + suf)
    for cls in ("index", "gold", "commod"):
        rep(f"F3 agree4+MA200 {cls}", P[P["agree" + suf] & (P.cls == cls)], leg, "comp" + suf)
        rep(f"F4 crisis(VIX>25 & term>1) {cls}", P[P["crisis" + suf] & (P.cls == cls)], leg, "comp" + suf)
        rep(f"F4b crisis & short only {cls}", P[P["crisis" + suf] & (P.cls == cls) & (P["comp" + suf] < 0)], leg, "comp" + suf)
        rep(f"F6 breadth<0.3 short / >0.7 long {cls}", P[(P.cls == cls) & (((P["br" + suf] < 0.3) & (P["comp" + suf] < 0)) | ((P["br" + suf] > 0.7) & (P["comp" + suf] > 0)))], leg, "comp" + suf)
    # F5: judge mechanic, top 3 by |comp| per date across cheap instruments
    sub = P[P["comp" + suf].notna()].copy()
    sub["rank"] = sub.groupby("date")["comp" + suf].transform(lambda s: (-s.abs()).rank(method="first"))
    top = sub[sub["rank"] <= 3]
    d, net = pnl(top, leg, "comp" + suf)
    slot = net.groupby(top["date"]).mean()
    print(f"F5 top3/slot  slots={len(slot)} net={slot.mean()*1e4:.2f} t={slot.mean()/slot.std()*np.sqrt(len(slot)):.2f}")
    print((slot.groupby(slot.index.year).mean() * 1e4).round(1).to_string())
    top_idx = sub[(sub.cls == "index")]; top_idx = top_idx[top_idx.groupby("date")["comp" + suf].transform(lambda s: (-s.abs()).rank(method="first")) <= 3]
    d, net = pnl(top_idx, leg, "comp" + suf); slot = net.groupby(top_idx["date"]).mean()
    print(f"F5b top3/slot INDEX ONLY slots={len(slot)} net={slot.mean()*1e4:.2f} t={slot.mean()/slot.std()*np.sqrt(len(slot)):.2f}")
