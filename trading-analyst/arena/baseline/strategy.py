"""Baseline: the validated QQQ/SPY IBS trend dip, overnight. Used to prove the judge works."""
import pandas as pd
UNIVERSE = ["SPY", "QQQ"]
N_TRIALS = 24

def signals(frames):
    rows = []
    for s in UNIVERSE:
        f = frames[s]; rng = (f.high - f.low).replace(0, float("nan"))
        ibs = (f.close - f.low) / rng; up = f.close > f.close.rolling(200).mean()
        tr = pd.concat([f.high - f.low, (f.high - f.close.shift()).abs(), (f.low - f.close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean() / f.close
        m = (ibs < 0.2) & up & atr.notna()
        for d in f.index[m]:
            rows.append((s, d, "CLOSE", 1, 1.5 * float(atr[d]), 1 - float(ibs[d])))
    return pd.DataFrame(rows, columns=["instrument", "date_in", "kind", "dir", "stop_pct", "score"])
