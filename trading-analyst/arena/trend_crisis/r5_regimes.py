"""Step 5: judge-consistent per-year / per-regime numbers for the frozen strategy (dev data only, judge's own fills())."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from arena.judge import load_strategy, load_frames, fills, CUTOFF

m = load_strategy("arena/trend_crisis/strategy.py")
fr = {k: v[v.index <= CUTOFF] for k, v in load_frames(list(m.UNIVERSE)).items()}
t = fills(m.signals(fr), fr)
sl = t.groupby("slot").agg(ret=("ret", "mean"), date=("date", "first"))
def line(name, s, tt):
    if len(s) < 3: print(f"{name:24s} slots={len(s)}"); return
    print(f"{name:24s} slots={len(s):5d} bps/slot={s.ret.mean()*1e4:7.1f} t={s.ret.mean()/s.ret.std()*np.sqrt(len(s)):5.2f} "
          f"sum%={s.ret.sum()*100:6.1f} short%={(tt.dir<0).mean():.2f} short_bps={tt.ret[tt.dir<0].mean()*1e4 if (tt.dir<0).any() else float('nan'):7.1f} "
          f"long_bps={tt.ret[tt.dir>0].mean()*1e4 if (tt.dir>0).any() else float('nan'):7.1f} worst={tt.ret.min()*1e4:7.0f}")
print("PER YEAR (judge fills, top-3 per slot):")
for y, s in sl.groupby(sl.date.dt.year):
    line(str(y), s, t[t.date.dt.year == y])
print("\nREGIMES:")
for name, (a, b) in {"2008": ("2008-01-01", "2008-12-31"), "2020Q1 (Feb20-Mar31)": ("2020-02-20", "2020-03-31"), "2022": ("2022-01-01", "2022-12-31"),
                     "GFC Oct07-Mar09": ("2007-10-01", "2009-03-31"), "2011 H2": ("2011-07-01", "2011-12-31"), "2018Q4": ("2018-10-01", "2018-12-31"),
                     "bull 2013-2017": ("2013-01-01", "2017-12-31"), "bull 2009Q2-2010": ("2009-04-01", "2010-12-31"), "2021": ("2021-01-01", "2021-12-31")}.items():
    k = (sl.date >= a) & (sl.date <= b); line(name, sl[k], t[(t.date >= a) & (t.date <= b)])
print("\nBY INSTRUMENT:")
print(t.groupby("instrument").agg(n=("ret", "size"), bps=("ret", lambda x: x.mean()*1e4), short=("dir", lambda x: (x < 0).mean()), sum_pct=("ret", lambda x: x.sum()*100)).round(2).to_string())
print("\nSHORT BOOK vs LONG BOOK overall:", f"short n={(t.dir<0).sum()} bps={t.ret[t.dir<0].mean()*1e4:.1f} t={t.ret[t.dir<0].mean()/t.ret[t.dir<0].std()*np.sqrt((t.dir<0).sum()):.2f};",
      f"long n={(t.dir>0).sum()} bps={t.ret[t.dir>0].mean()*1e4:.1f} t={t.ret[t.dir>0].mean()/t.ret[t.dir>0].std()*np.sqrt((t.dir>0).sum()):.2f}")
# walk-forward halves (the model is already OOS every year; this shows stability)
for a, b in (("2006-01-01", "2014-12-31"), ("2015-01-01", "2022-12-31")):
    k = (sl.date >= a) & (sl.date <= b); line(f"half {a[:4]}-{b[:4]}", sl[k], t[(t.date >= a) & (t.date <= b)])
