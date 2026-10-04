"""Step 4: decompose the positive CLOSE-leg stacking result of r3. Which class / instrument / feature carries it?
Does it survive without Yahoo continuous futures (whose close->open return contains contract ROLL gaps a CFD never pays)?"""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from arena.trend_crisis.common import *
from arena.trend_crisis.panel import LOOKS, breadth
from arena.trend_crisis.r3_stack import walk_forward, design, ridge, FEATS, SP

P = pd.read_pickle(SP + "panel.pkl"); P = P[P.cls != "stock"].copy()
fr = load_dev(INDICES); br = breadth(fr, INDICES).rename("br_c").reset_index().rename(columns={"index": "date"})
P = P.merge(br, on="date", how="left"); P["br_o"] = P.groupby("inst")["br_c"].shift(1)
for suf in ("_c", "_o"):
    P["rvol" + suf] = P["vol" + suf] / P["vol_long" + suf]
P["tdate"] = P.groupby("inst")["date"].shift(-1)
P = P[np.isfinite(P["on_ret"]) | P["on_ret"].isna()]
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)

BEAR = {"2008": ("2008-01-01", "2008-12-31"), "2020Q1": ("2020-02-20", "2020-03-31"), "2022": ("2022-01-01", "2022-12-31"),
        "GFC 2007-10..2009-03": ("2007-10-01", "2009-03-31"), "bull 2013-17": ("2013-01-01", "2017-12-31"), "2010-11": ("2010-01-01", "2011-12-31")}


def evaluate(Pt, by_class, lam, mult, label):
    pr = walk_forward(Pt, "_c", "on_ret", lam=lam, by_class=by_class)
    e = pr * Pt["vol_c"]; cost = Pt["rt"] + Pt["fin_long"].abs()
    d = np.sign(e).where(e.abs() > mult * cost, 0).fillna(0)
    net = d * Pt["on_ret"] - Pt["rt"] * (d != 0) + np.where(d > 0, Pt["fin_long"], np.where(d < 0, Pt["fin_short"], 0))
    gross = d * Pt["on_ret"]
    k = (d != 0) & e.notna() & net.notna()
    sub = Pt[k].assign(net=net[k], gross=gross[k], d=d[k], sc=e[k].abs())
    sub["rk"] = sub.groupby("date")["sc"].rank(ascending=False, method="first")
    top = sub[sub.rk <= 3]; slot = top.groupby("date")["net"].mean()
    t = slot.mean() / slot.std() * np.sqrt(len(slot))
    print(f"\n===== {label}: by_class={by_class} lam={lam} mult={mult}: slots={len(slot)} net/slot={slot.mean()*1e4:.2f} t={t:.2f} "
          f"trades(top3)={len(top)} short%={(top.d<0).mean():.2f} net_short={top.net[top.d<0].mean()*1e4:.1f} net_long={top.net[top.d>0].mean()*1e4:.1f}")
    print("by class (top-3 trades):"); print(top.groupby("cls").agg(n=("net", "size"), net_bps=("net", lambda x: x.mean()*1e4), gross_bps=("gross", lambda x: x.mean()*1e4), short=("d", lambda x: (x<0).mean())).round(2).to_string())
    print("by instrument:"); print(top.groupby("inst").agg(n=("net", "size"), net_bps=("net", lambda x: x.mean()*1e4), short=("d", lambda x: (x<0).mean()), sum_net=("net", "sum")).round(3).sort_values("sum_net", ascending=False).to_string())
    print("regimes (slot-level):")
    for nm, (a, b) in BEAR.items():
        s = slot[(slot.index >= a) & (slot.index <= b)]; tt = top[(top.date >= a) & (top.date <= b)]
        if len(s) > 5:
            print(f"  {nm:22s} slots={len(s):4d} net/slot={s.mean()*1e4:7.1f} t={s.mean()/s.std()*np.sqrt(len(s)):5.2f} short%={(tt.d<0).mean():.2f} "
                  f"short_net={tt.net[tt.d<0].mean()*1e4 if (tt.d<0).any() else float('nan'):7.1f} long_net={tt.net[tt.d>0].mean()*1e4 if (tt.d>0).any() else float('nan'):7.1f} sum_net_pct={s.sum()*100:.1f}")
    print("year x class net bps (top-3 trades):")
    print((top.groupby([top.date.dt.year, "cls"])["net"].mean().unstack() * 1e4).round(1).to_string())
    return top, slot


# A. reference config from r3
top, slot = evaluate(P, True, 300.0, 2.0, "ALL cheap (index+gold+futures)")
# B. drop Yahoo continuous futures entirely: index ETFs + GLD only (no roll artefacts, real 9:30/16:00 prints)
Pn = P[~P.inst.str.endswith("=F")].copy()
evaluate(Pn, True, 300.0, 2.0, "NO FUTURES (7 index ETFs + GLD)")
evaluate(Pn, False, 300.0, 2.0, "NO FUTURES pooled")
evaluate(Pn, False, 300.0, 1.5, "NO FUTURES pooled mult1.5")
evaluate(Pn, False, 300.0, 1.0, "NO FUTURES pooled mult1.0")
# C. index only
Pi = P[P.cls == "index"].copy()
evaluate(Pi, False, 300.0, 2.0, "INDEX ONLY")
evaluate(Pi, False, 300.0, 1.0, "INDEX ONLY mult1.0")

# D. which features drive the fit? final-year coefficients on the pooled no-futures model (train < 2022)
X = design(Pn, "_c"); y = Pn["on_ret"] / Pn["vol_c"]
ok = X.notna().all(axis=1) & y.notna() & (Pn["date"] < "2021-12-10") & (Pn["tdate"] < "2021-12-10")
w = ridge(X[ok].to_numpy(), y[ok].clip(-5, 5).to_numpy(), 300.0)
sd = X[ok].std()
print("\nridge coefficients x feature sd (vol-normalised return per 1 sd), pooled no-futures, fit <2022:")
print(pd.Series(w[1:] * sd.to_numpy(), index=FEATS).round(4).sort_values().to_string(), "\nintercept", round(w[0], 4))
