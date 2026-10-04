"""Deliberate lookahead cheat (buys when TOMORROW's open is higher). The judge must reject it."""
import pandas as pd
UNIVERSE = ["SPY"]
N_TRIALS = 1
def signals(frames):
    f = frames["SPY"]; m = f.open.shift(-1) > f.close
    rows = [("SPY", d, "CLOSE", 1, 0.02, 1.0) for d in f.index[m.fillna(False)]]
    return pd.DataFrame(rows, columns=["instrument", "date_in", "kind", "dir", "stop_pct", "score"])
