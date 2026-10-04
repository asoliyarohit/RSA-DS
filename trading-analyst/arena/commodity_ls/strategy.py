"""commodity_ls: long/short commodity CFDs, OPEN slot only (enter at open, hard stop, flat at close).

See PREREGISTRATION.txt (hypotheses fixed before testing) and REPORT.txt (results).
Every feature for a trade dated t uses information <= t-1 only (open of t is not even needed).
The ridge combiner (H6) is refit every 1 January on rows strictly before that year (5-day embargo),
so truncating the data at any date T leaves every earlier signal unchanged (judge perturbation test).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

UNIVERSE = ["GLD", "BZ=F", "NG=F", "HO=F", "RB=F", "ZC=F", "ZW=F", "ZS=F"]
N_TRIALS = 11         # H1-H6 pre-registered + H7-H10 post-kill variants + CL=F removal (see REPORT.txt)
MODE = "H1"           # best design-period t among pre-registered rules; NOT VALIDATED
START = pd.Timestamp("2008-01-01")
RIDGE_ALPHA = 100.0
STOP_K = 1.5
FEATS = ["mom20", "mom60", "mom120", "rev1", "dc", "xs", "carry", "vixz"]


def _inst_features(t: str, f: pd.DataFrame) -> pd.DataFrame:
    f = f[["open", "high", "low", "close"]].astype(float)
    o, c = f["open"], f["close"]
    ok = (o > 0) & (c > 0)
    oc = np.log(c.where(ok) / o.where(ok))
    gap = np.log(o.where(ok) / c.shift(1).where(ok.shift(1, fill_value=False)))
    rf = np.log(c.where(ok) / c.shift(1).where(ok.shift(1, fill_value=False))) if t == "GLD" else oc
    rf = rf.clip(-0.25, 0.25)
    sig = rf.rolling(60, min_periods=40).std()
    sig_oc = oc.clip(-0.25, 0.25).rolling(60, min_periods=40).std()
    p = rf.fillna(0).cumsum()
    out = pd.DataFrame(index=f.index)
    for k in (20, 60, 120):
        out[f"mom{k}"] = rf.rolling(k, min_periods=int(k * 0.8)).sum() / (sig * np.sqrt(k))
    out["rev1"] = rf / sig
    hi, lo = p.rolling(20).max(), p.rolling(20).min()
    out["dc"] = np.where(p >= hi, 1.0, np.where(p <= lo, -1.0, 0.0))
    out["dcpos"] = ((p - lo) / (hi - lo) * 2 - 1)
    out["carry"] = 0.0 if t == "GLD" else -gap.clip(-0.1, 0.1).rolling(60, min_periods=40).sum() / (sig * np.sqrt(60))
    out["sig"] = sig
    out["stop"] = STOP_K * sig_oc
    out = out.shift(1)                       # everything known at the close of t-1
    out["y"] = oc / out["sig"]               # label: today's open->close (vol-scaled); NOT a feature
    out["instrument"] = t
    return out


def build(frames: dict) -> pd.DataFrame:
    parts = [_inst_features(t, frames[t]) for t in UNIVERSE if t in frames and len(frames[t]) > 200]
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts).rename_axis("date").reset_index()
    # cross-sectional rank of mom60 among instruments available that day, scaled to [-1, 1]
    r = df.groupby("date")["mom60"].rank()
    n = df.groupby("date")["mom60"].transform("count")
    df["xs"] = np.where(n > 1, (r - 1) / (n - 1).clip(lower=1) * 2 - 1, 0.0)
    v = frames.get("^VIX")
    if v is not None and len(v):
        vc = v["close"].astype(float)
        vz = ((vc - vc.rolling(252, min_periods=100).mean()) / vc.rolling(252, min_periods=100).std())
        # VIX close of the last US session strictly before date t
        vz = vz.dropna()
        pos = np.searchsorted(vz.index.values, df["date"].values, side="left") - 1
        df["vixz"] = np.where(pos >= 0, vz.values[np.clip(pos, 0, None)], 0.0) if len(vz) else 0.0
    else:
        df["vixz"] = 0.0
    df[FEATS] = df[FEATS].replace([np.inf, -np.inf], np.nan)
    return df


def _ridge_pred(df: pd.DataFrame) -> pd.Series:
    pred = pd.Series(np.nan, index=df.index)
    X_all = df[FEATS].clip(-5, 5)
    good = X_all.notna().all(axis=1) & df["sig"].notna()
    years = sorted(df.loc[df["date"] >= START, "date"].dt.year.unique())
    for yr in years:
        y0 = pd.Timestamp(f"{yr}-01-01")
        tr = good & df["y"].notna() & (df["date"] < y0 - pd.Timedelta(days=5))
        te = good & (df["date"] >= y0) & (df["date"] < pd.Timestamp(f"{yr + 1}-01-01"))
        if tr.sum() < 2000 or te.sum() == 0:
            continue
        X = X_all[tr].to_numpy(); y = df.loc[tr, "y"].clip(-5, 5).to_numpy()
        mu, sd = X.mean(0), X.std(0) + 1e-12
        Z = (X - mu) / sd
        ym = y.mean()
        beta = np.linalg.solve(Z.T @ Z + RIDGE_ALPHA * np.eye(Z.shape[1]), Z.T @ (y - ym))
        pred[te] = ((X_all[te].to_numpy() - mu) / sd) @ beta + ym
    return pred


def raw_signal(df: pd.DataFrame, mode: str) -> pd.Series:
    if mode == "H1":
        return df[["mom20", "mom60", "mom120"]].mean(axis=1)
    if mode == "H2":
        return (-df["rev1"]).where(df["rev1"].abs() > 2.0)
    if mode == "H3":
        return (df["dc"] * df["mom20"].abs()).where(df["dc"] != 0)
    if mode == "H4":
        return df["xs"]
    if mode == "H5":
        return df["carry"].where(df["instrument"] != "GLD")
    if mode == "H6":
        return _ridge_pred(df)
    raise ValueError(mode)


def signals_for(frames: dict, mode: str) -> pd.DataFrame:
    df = build(frames)
    cols = ["instrument", "date_in", "kind", "dir", "stop_pct", "score"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    s = raw_signal(df, mode)
    m = s.notna() & (s != 0) & df["stop"].gt(0) & (df["date"] >= START)
    out = pd.DataFrame({"instrument": df.loc[m, "instrument"], "date_in": df.loc[m, "date"], "kind": "OPEN",
                        "dir": np.sign(s[m]).astype(int), "stop_pct": df.loc[m, "stop"].clip(0.005, 0.15),
                        "score": s[m].abs()})
    return out.reset_index(drop=True)[cols]


def signals(frames: dict) -> pd.DataFrame:
    return signals_for(frames, MODE)
