"""Round 1: the pre-registered hypothesis list (written before looking at any conditional result).
Each rule = 1 trial. Top-3 per slot by score, judge cost model. Train <=2016, validate 2017-2022."""
import pickle, sys
import numpy as np, pandas as pd
from arena.quant_edge.research import slot_stats, atr_pct, TRAIN_END
from arena.quant_edge.universe import ETFS, STOCKS
from arena.judge import cost_for

P, R = pickle.load(open(sys.argv[1], "rb"))
O, H, L, C = P["open"], P["high"], P["low"], P["close"]
spy = C["SPY"]
r1 = C.pct_change()
vol = r1.rolling(20).std()
res1 = r1.sub(r1["SPY"], axis=0)
z1 = res1 / vol
idr = C / O - 1
zid = idr.sub(idr["SPY"], axis=0) / vol
gap = O / C.shift() - 1
zg = gap.sub(gap["SPY"], axis=0) / vol.shift()          # known at open
ibs = (C - L) / (H - L).replace(0, np.nan)
rng_pos = (C - L.rolling(20).min()) / (H.rolling(20).max() - L.rolling(20).min())
on_hist = (O / C.shift() - 1).rolling(20).sum()          # past 20 overnight returns, incl. today's gap (known at close)
id_hist = idr.shift().rolling(20).sum()                   # past 20 intraday returns up to yesterday (known at open)
up = (spy > spy.rolling(200).mean())
upT = pd.DataFrame(np.repeat(up.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
atr = atr_pct(P).shift()                                   # known at open
stk = pd.DataFrame(False, index=C.index, columns=C.columns); stk[STOCKS] = True
etf = ~stk


def open_ret(dirn, stop_k=1.5):
    s = stop_k * atr
    cost = pd.Series({t: cost_for(t).round_trip_cost() for t in C.columns})
    if dirn > 0:
        hit = L <= O * (1 - s); px = np.where(hit, O * (1 - s), C)
        return pd.DataFrame(px, index=C.index, columns=C.columns) / O - 1 - cost
    hit = H >= O * (1 + s); px = np.where(hit, O * (1 + s), C)
    return -(pd.DataFrame(px, index=C.index, columns=C.columns) / O - 1) - cost


IDL, IDS = open_ret(1), open_ret(-1)
ok = C.notna() & vol.notna() & atr.notna()

H_LIST = {
    # CLOSE -> next open
    "C1 stk long lowest resid z1": (stk & ok, -z1, R["on_long"]),
    "C2 stk long z1<-2": (stk & ok & (z1 < -2), -z1, R["on_long"]),
    "C3 stk long lowest intraday z": (stk & ok & (zid < -2), -zid, R["on_long"]),
    "C4 stk long near 20d low & ibs<.2": (stk & ok & (rng_pos < .1) & (ibs < .2), -rng_pos, R["on_long"]),
    "C5 etf long ibs<.2 uptrend": (etf & ok & (ibs < .2) & (C > C.rolling(200).mean()), -ibs, R["on_long"]),
    "C6 stk short z1>2": (stk & ok & (z1 > 2), z1, R["on_short"]),
    "C7 stk long overnight-momentum top": (stk & ok, on_hist, R["on_long"]),
    # OPEN -> close
    "O1 stk fade gap down zg<-2 (long)": (stk & ok & (zg < -2), -zg, IDL),
    "O2 stk fade gap up zg>2 (short)": (stk & ok & (zg > 2), zg, IDS),
    "O3 stk follow gap up zg>2 (long)": (stk & ok & (zg > 2), zg, IDL),
    "O4 stk follow gap down zg<-2 (short)": (stk & ok & (zg < -2), -zg, IDS),
    "O5 etf fade gap down (long)": (etf & ok & (gap < -0.5 * atr), -gap / atr, IDL),
    "O6 stk long intraday-momentum top": (stk & ok, id_hist, IDL),
}
if __name__ == "__main__":
    for name, (m, sc, ret) in H_LIST.items():
        out, yr, sl = slot_stats(m, sc, ret)
        pos = (yr["mean"] > 0).mean()
        print(f"{name:40s} train n/bps/t={out['train']}  valid={out['valid']}  yrs+={pos:.2f}")
