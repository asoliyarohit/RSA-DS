import sys; sys.path.insert(0, "/home/user/RSA-DS/trading-analyst")
import numpy as np, pandas as pd
from analyst import sim180 as S, council_sim as cs, data
from arena import judge
idx = {s: data.load(s) for s in cs.IDX}; vix = data.load("^VIX")["close"]
c = cs.calls(idx, vix, S.START, S.END, calendar_block={"OPEN": S.FOMC}, news=True)
sig = c[c.dir != 0]; cal = idx["SPY"].index; days = [d for d in cal if pd.Timestamp(S.START) <= d <= pd.Timestamp(S.END)]
real = judge.fills(sig[["instrument","date_in","kind","dir","stop_pct","score"]], idx)
nC, nO = int((sig.kind=="CLOSE").sum()), int((sig.kind=="OPEN").sum())
# 1) unconditional always-long, every day, per slot type, equal-weight over the 3 indices
rows=[]
for s in cs.IDX:
    f = idx[s]; sig_ = pd.DataFrame({"instrument":s,"date_in":[d for d in days for _ in (0,)],"kind":"OPEN","dir":1,"stop_pct":0.01,"score":1.0})
    sigc = sig_.assign(kind="CLOSE", date_in=[cal[cal.get_loc(d)-1] for d in days])
    for k,df in (("OPEN",sig_),("CLOSE",sigc)):
        t=judge.fills(df,idx); rows.append((s,k,round(t.ret.mean()*1e4,1),len(t)))
print("Unconditional ALWAYS-LONG net bps/trade in the same window:"); [print("  ",r) for r in rows]
# 2) timing placebo: random days, same counts per kind, random index from the 3, always BUY, same stop sizing
rng = np.random.default_rng(3); res=[]; n=800
for _ in range(n):
    parts=[]
    for kind,m in (("CLOSE",nC),("OPEN",nO)):
        ds = rng.choice(days, m, replace=False); ins = rng.choice(cs.IDX, m)
        parts.append(pd.DataFrame({"instrument":ins,"date_in":[cal[cal.get_loc(pd.Timestamp(d))-1] if kind=="CLOSE" else pd.Timestamp(d) for d in ds],"kind":kind,"dir":1,"stop_pct":0.01,"score":1.0}))
    t=judge.fills(pd.concat(parts),idx); res.append(t.ret.mean()*1e4)
res=np.array(res); ours=real.ret.mean()*1e4; ours_buy=real[real.dir>0].ret.mean()*1e4
print(f"Timing placebo (random days, always BUY, same counts): mean {res.mean():+.1f} bps/trade, 5-95% [{np.percentile(res,5):+.1f}, {np.percentile(res,95):+.1f}]")
print(f"Ours all trades {ours:+.1f} bps -> beats {100*(res<ours).mean():.0f}% of timing placebos | ours BUY-only {ours_buy:+.1f} bps -> beats {100*(res<ours_buy).mean():.0f}%")
