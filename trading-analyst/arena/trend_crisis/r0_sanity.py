"""Step 0: download universe (dev cut) and print data sanity per instrument."""
import sys; sys.path.insert(0, ".")
from arena.trend_crisis.common import *

fr = load_dev()
for t, d in fr.items():
    pc = d["close"].shift(1)
    stale = float((d["open"] == pc).mean())
    bad = int(((d[["open", "high", "low", "close"]] <= 0).any(axis=1)).sum())
    rng = ((d.high - d.low) / d.close)
    on = (d.open / pc - 1); intra = d.close / d.open - 1
    rt, lev, _ = rt_cost(t)
    print(f"{t:8s} {d.index.min().date()} n={len(d):5d} stale_open={stale:.2f} bad={bad} medrange={rng.median()*1e4:5.0f}bp "
          f"sd_on={on.std()*1e4:5.0f} sd_intra={intra.std()*1e4:5.0f} mean_on={on.mean()*1e4:5.1f} mean_intra={intra.mean()*1e4:5.1f} rt={rt*1e4:.0f}bp lev={lev:.0f}")
