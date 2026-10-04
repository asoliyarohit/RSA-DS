"""Step 3 (H5): purged walk-forward ridge stacking of the trend / regime features -> expected next-leg return per
instrument. Refit once per calendar year on all data whose TARGET date is <= Dec 31 of the previous year minus a 21-day
embargo (so model for year Y never sees year Y). Trade when |E[ret]| exceeds a multiple of the round-trip cost.
Everything here is pure numpy ridge, deterministic, causal; the same code is imported by strategy.py."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from arena.trend_crisis.common import *
from arena.trend_crisis.panel import LOOKS, breadth

SP = "/tmp/claude-0/-home-user-RSA-DS/54141183-5e85-528e-8612-315d8d6f3985/scratchpad/"
FEATS = ["z21", "z63", "z126", "z252", "z252x21", "ema8", "ema16", "ema32", "dd", "ibs", "r1n", "r5n", "vixma", "vterm", "rvol", "br", "gapn", "ma200"]
LAM = 30.0


def design(P: pd.DataFrame, suf: str) -> pd.DataFrame:
    X = pd.DataFrame(index=P.index)
    for L in LOOKS:
        X[f"z{L}"] = P[f"z{L}{suf}"].clip(-3, 3)
    X["z252x21"] = P["z252x21" + suf].clip(-3, 3)
    for s in (8, 16, 32):
        X[f"ema{s}"] = P[f"ema{s}{suf}"].clip(-3, 3)
    X["dd"] = P["dd" + suf].clip(-1, 0)
    X["ibs"] = P["ibs" + suf] - 0.5
    X["r1n"] = (P["r1" + suf] / P["vol" + suf]).clip(-4, 4)
    X["r5n"] = (P["r5" + suf] / (P["vol" + suf] * np.sqrt(5))).clip(-4, 4)
    X["vixma"] = (P["vix_ma" + suf] - 1).clip(-1, 2)
    X["vterm"] = (P["vterm" + suf].fillna(1.0) - 1).clip(-0.5, 1)
    X["rvol"] = (P["rvol" + suf] - 1).clip(-0.8, 3)
    X["br"] = P["br" + suf].fillna(0.5) - 0.5
    X["gapn"] = (P["gap"] / P["vol" + suf]).clip(-4, 4) if suf == "_o" else 0.0  # today's gap is known at the open only
    X["ma200"] = P["ma200" + suf]
    return X


def ridge(X, y, lam=LAM):
    Xb = np.c_[np.ones(len(X)), X]
    A = Xb.T @ Xb + lam * np.eye(Xb.shape[1]); A[0, 0] -= lam
    return np.linalg.solve(A, Xb.T @ y)


def walk_forward(P: pd.DataFrame, suf: str, target: str, lam=LAM, embargo_days=21, first_year=2006, by_class=False):
    """Returns Series of predicted vol-normalised return for every row, NaN before first_year."""
    X = design(P, suf); y = P[target] / P["vol" + suf]
    ok = X.notna().all(axis=1) & y.notna() & np.isfinite(y)
    pred = pd.Series(np.nan, index=P.index)
    years = sorted(P["date"].dt.year.unique())
    for Y in years:
        if Y < first_year: continue
        cut = pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=embargo_days)
        tr = ok & (P["date"] < cut) & (P["tdate"] < cut)      # tdate = date whose price the target uses
        te = (P["date"].dt.year == Y) & X.notna().all(axis=1)
        if tr.sum() < 500 or te.sum() == 0: continue
        groups = P.loc[te, "cls"].unique() if by_class else [None]
        for g in groups:
            trg = tr & (P["cls"] == g) if g else tr; teg = te & (P["cls"] == g) if g else te
            if trg.sum() < 500: continue
            w = ridge(X[trg].to_numpy(), y[trg].clip(-5, 5).to_numpy(), lam)
            pred[teg] = np.c_[np.ones(teg.sum()), X[teg].to_numpy()] @ w
    return pred


if __name__ == "__main__":
    P = pd.read_pickle(SP + "panel.pkl"); P = P[P.cls != "stock"].copy()
    fr = load_dev(INDICES); br = breadth(fr, INDICES).rename("br_c").reset_index().rename(columns={"index": "date"})
    P = P.merge(br, on="date", how="left"); P["br_o"] = P.groupby("inst")["br_c"].shift(1)
    for suf in ("_c", "_o"):
        P["rvol" + suf] = P["vol" + suf] / P["vol_long" + suf]
    P["tdate"] = P.groupby("inst")["date"].shift(-1)   # CLOSE target uses next open; OPEN target uses same-day close
    pd.set_option("display.width", 250)
    for leg, suf, target in (("CLOSE", "_c", "on_ret"), ("OPEN", "_o", "in_ret")):
        Pt = P.copy()
        if leg == "OPEN": Pt["tdate"] = Pt["date"]
        for by_class in (False, True):
            for lam in (30.0, 300.0):
                pr = walk_forward(Pt, suf, target, lam=lam, by_class=by_class)
                e = pr * Pt["vol" + suf]                      # expected gross return
                cost = Pt["rt"] + (0.0 if leg == "OPEN" else (Pt["fin_long"].abs()))
                ok = e.notna()
                corr = np.corrcoef(e[ok], Pt.loc[ok, target])[0, 1]
                print(f"\n### {leg} by_class={by_class} lam={lam}: OOS rows={ok.sum()} IC(pred,ret)={corr:.4f}")
                for mult in (0.0, 1.0, 1.5, 2.0, 3.0):
                    d = np.sign(e).where(e.abs() > mult * cost, 0).fillna(0)
                    if leg == "CLOSE":
                        net = d * Pt["on_ret"] - Pt["rt"] * (d != 0) + np.where(d > 0, Pt["fin_long"], np.where(d < 0, Pt["fin_short"], 0))
                    else:
                        net = d * Pt["in_ret"] - Pt["rt"] * (d != 0)
                    k = (d != 0) & ok
                    if k.sum() < 30: print(f"  mult={mult}: n={k.sum()}"); continue
                    # judge mechanic: top-3 per date by |e|
                    sub = Pt[k].assign(net=net[k], sc=e[k].abs())
                    sub["rk"] = sub.groupby("date")["sc"].rank(ascending=False, method="first")
                    top = sub[sub.rk <= 3]; slot = top.groupby("date")["net"].mean()
                    yr = (slot.groupby(slot.index.year).mean() * 1e4).round(1)
                    print(f"  mult={mult}: trades={k.sum():6d} net/trade={net[k].mean()*1e4:6.2f} short%={(d[k]<0).mean():.2f} | slots={len(slot)} "
                          f"net/slot={slot.mean()*1e4:6.2f} t={slot.mean()/slot.std()*np.sqrt(len(slot)):5.2f}  years: " + " ".join(f"{y}:{v}" for y, v in yr.items()))
