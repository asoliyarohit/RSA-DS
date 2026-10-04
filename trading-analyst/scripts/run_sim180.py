import sys; sys.path.insert(0, "/home/user/RSA-DS/trading-analyst")
import numpy as np, pandas as pd, json
from analyst import sim180 as S
out, idx = S.main()
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
R = {}
for label, o in out.items():
    tr, c = o["trades"], o["calls"]
    print(f"\n######## {label}: decision days {c['T'].nunique()}, calls {len(c)}, trades {len(tr)}; no-trade reasons: {c[c.dir==0]['why'].value_counts().to_dict()}")
    print("ALL      ", S.stats(tr.ret)); 
    for k in ("CLOSE","OPEN"): print(k.ljust(9), S.stats(tr[tr.setup==k].ret))
    for d,nm in ((1,"BUY"),(-1,"SELL")): print(nm.ljust(9), S.stats(tr[tr.dir==d].ret))
    for mode in ("A_council","B_guarded1.5","C_aggr10"):
        a = S.account(tr, mode, guard=True); a0 = S.account(tr, mode, guard=False)
        pl = S.placebo(tr, o["flip"], mode)
        end0 = a0.equity.iloc[-1]; pct = float((pl < end0).mean() * 100)
        dd = float((1 - a0.equity / a0.equity.cummax()).max())
        print(f"{mode:13} guard-on end ${a.equity.iloc[-1]:8.0f} | guard-off end ${end0:8.0f} maxDD {dd:.0%} | random-direction control: median ${np.median(pl):.0f}, 5-95% [${np.percentile(pl,5):.0f}, ${np.percentile(pl,95):.0f}] -> ours beats {pct:.0f}% of coin-flip runs")
        R[(label,mode)] = (a, a0)
o = out["NEWS+PRICE"]; tr = o["trades"].sort_values("slot")
spy = idx["SPY"].loc["2026-04-07":"2026-10-02"]; print(f"\nSPY buy&hold 1x (open Apr-7 to close Oct-2): {spy.close.iloc[-1]/spy.open.iloc[0]-1:+.1%}  => $1000 -> ${1000*spy.close.iloc[-1]/spy.open.iloc[0]:.0f}")
a = R[("NEWS+PRICE","A_council")][0].set_index("slot")
tr = tr.merge(a[["equity","pnl"]], left_on="slot", right_index=True)
tr["side"] = np.where(tr.dir>0,"BUY","SELL"); tr["net_bps"]=(tr.ret*1e4).round(1)
tr["gross_bps"]=((tr.ret + tr.instrument.map(lambda s: S.judge.cost_for(s).round_trip_cost()))*1e4).round(0)
cols=["date","setup","instrument","side","S","net_bps","pnl","equity"]
tr["S"]=tr["S"].round(2); tr["pnl"]=tr["pnl"].round(2); tr["equity"]=tr["equity"].round(1)
print("\nDAY-BY-DAY (mode A, council sizing, guard on):"); print(tr[cols].to_string(index=False))
tr[cols].to_csv("/home/user/RSA-DS/trading-analyst/reports/sim_180d_trades.csv", index=False)
