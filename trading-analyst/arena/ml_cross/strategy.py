"""ml_cross: regularised pooled cross-sectional model for OPEN (open->close) and CLOSE (close->next open) decisions.

Causal by construction:
  * features for an OPEN decision on day T use only data up to close T-1 plus open[T];
  * features for a CLOSE decision on day T use data up to close T;
  * the model is re-fit once per calendar year (fixed Jan-1 boundaries, never "the last date in the data"),
    on rows whose labels were fully known >= EMBARGO_DAYS before the boundary.
See REPORT.md for the research log, N_TRIALS accounting and the evidence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

UNIVERSE = ['AAPL', 'ABT', 'ADBE', 'AIG', 'AMAT', 'AMD', 'AMGN', 'AMZN', 'AVGO', 'AXP', 'BA', 'BAC', 'BKNG', 'BLK',
            'BMY', 'C', 'CAT', 'CL', 'CMCSA', 'COP', 'COST', 'CRM', 'CSCO', 'CVS', 'CVX', 'DE', 'DHR', 'DIA', 'DIS',
            'DUK', 'EBAY', 'F', 'FDX', 'GE', 'GILD', 'GLD', 'GM', 'GOOGL', 'GS', 'HAL', 'HD', 'HON', 'IBM', 'INTC',
            'IWM', 'JNJ', 'JPM', 'KMB', 'KO', 'LLY', 'LMT', 'LOW', 'MA', 'MCD', 'MDT', 'MET', 'META', 'MMM', 'MO',
            'MRK', 'MS', 'MSFT', 'MU', 'NEE', 'NFLX', 'NKE', 'NVDA', 'ORCL', 'OXY', 'PEP', 'PFE', 'PG', 'PM', 'PNC',
            'PYPL', 'QCOM', 'QQQ', 'RTX', 'SBUX', 'SCHW', 'SLB', 'SO', 'SPY', 'T', 'TGT', 'TLT', 'TMO', 'TSLA', 'TXN',
            'UNH', 'UNP', 'UPS', 'USB', 'V', 'VZ', 'WFC', 'WMT', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY',
            'XOM']
N_TRIALS = 20  # 17 evaluated model/selection variants + 3 diagnostic breakdowns that steered choices (REPORT.md)

ETFS = {"SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "TLT", "GLD"}
SECTOR = {
    **{t: "XLK" for t in "AAPL MSFT NVDA INTC CSCO ORCL IBM ADBE CRM QCOM TXN AMD MU AMAT AVGO V MA PYPL GOOGL META".split()},
    **{t: "XLY" for t in "NFLX CMCSA DIS AMZN TSLA HD LOW MCD NKE SBUX TGT EBAY BKNG F GM".split()},
    **{t: "XLU" for t in "T VZ NEE DUK SO".split()},
    **{t: "XLP" for t in "KO PEP PG WMT COST MO PM CL KMB".split()},
    **{t: "XLF" for t in "JPM BAC WFC C GS MS AXP BLK SCHW USB PNC MET AIG".split()},
    **{t: "XLV" for t in "JNJ PFE MRK ABT LLY UNH AMGN GILD BMY CVS MDT TMO DHR".split()},
    **{t: "XLE" for t in "XOM CVX COP SLB OXY HAL".split()},
    **{t: "XLI" for t in "BA CAT DE GE HON MMM UPS FDX LMT RTX UNP".split()},
}
COST = {"etf": 4e-4, "stock": 16e-4}          # judge round-trip cost per notional
LONG_FIN_NIGHT = 0.07 / 365                   # judge financing for a long held one night (short earns ~1%/yr)

OPEN_FEATS = ["gap", "gap_mkt", "id1", "r5", "r20", "r60", "ibs1", "ma20", "onmom", "idmom", "rel5", "vixz", "dvix", "vol", "etf"]
CLOSE_FEATS = ["id0", "on0", "r5", "r20", "r60", "ibs0", "ma20", "onmom", "idmom", "rel5", "mkt0", "vixz", "dvix", "vol", "fri", "etf"]

# ---- frozen configuration (chosen on 2004-2016 walk-forward only; see REPORT.md) ----
CFG = dict(model="ridge", alpha=1e4, first_year=2004, embargo_days=5, clip=4.0, atr_n=20,
           kinds=("CLOSE",), trade_etfs=False, gate=True, margin=1.0, max_per_slot=3, stop_atr=1.5)


def _wide(frames):
    tick = [t for t in frames if t != "^VIX"]
    idx = frames["SPY"].index if "SPY" in frames else frames[tick[0]].index
    for t in tick:
        idx = idx.union(frames[t].index)
    W = {k: pd.DataFrame({t: frames[t][k] for t in tick}).reindex(idx) for k in ("open", "high", "low", "close")}
    vix = frames["^VIX"]["close"].reindex(idx) if "^VIX" in frames else pd.Series(np.nan, idx)
    return W, vix


def build_panel(frames, atr_n=20, clip=4.0):
    """Long panel (date, ticker) with OPEN_FEATS / CLOSE_FEATS, ATR scales and labels (NaN when unknown)."""
    W, vix = _wide(frames)
    O, H, L, C = W["open"], W["high"], W["low"], W["close"]
    pc = C.shift(1)
    tr = pd.concat([(H - L), (H - pc).abs(), (L - pc).abs()]).groupby(level=0).max()
    atr_c = (tr.rolling(atr_n, min_periods=atr_n).mean() / C)          # known at close T
    atr_o = atr_c.shift(1)                                               # known at open T
    on_raw = O / pc - 1                                                  # overnight (gap) return of T
    id_raw = C / O - 1                                                   # intraday return of T
    stale_o = pd.DataFrame(np.isclose(O, pc, rtol=1e-7), O.index, O.columns)          # knowable at the open
    stale = stale_o | pd.DataFrame(np.isclose(O, H) & np.isclose(O, L), O.index, O.columns)  # knowable at the close
    gap_o = on_raw.mask(stale_o)                                         # OPEN-time gap feature
    on = on_raw.mask(stale); idr = id_raw.mask(stale)                    # Yahoo stale opens (mostly pre-2008)
    r = lambda n: (C / C.shift(n) - 1)
    rng = (H - L).where(H > L)
    ibs = (C - L) / rng - 0.5
    ma20 = C.rolling(20, min_periods=20).mean()
    onmom = on.rolling(20, min_periods=10).mean()
    idmom = idr.rolling(20, min_periods=10).mean()
    r5 = r(5)
    sec = pd.DataFrame({t: r5[SECTOR.get(t, "SPY")] if SECTOR.get(t, "SPY") in r5 else np.nan for t in C.columns})
    rel5 = r5 - sec
    lv = np.log(vix)
    vixz = (lv - lv.rolling(252, min_periods=60).mean())
    dvix = lv.diff()
    spy = "SPY" if "SPY" in C else C.columns[0]
    bc = lambda s: pd.DataFrame({t: s for t in C.columns})
    lvol = np.log(atr_c)
    vol_c = lvol.sub(lvol.mean(axis=1), axis=0)
    etf = bc(pd.Series(0.0, C.index)).copy()
    for t in C.columns:
        etf[t] = 1.0 if t in ETFS else 0.0
    sq = np.sqrt
    ac, ao = atr_c, atr_o
    feats_close = {
        "id0": idr / ac, "on0": on / ac, "r5": r5 / (ac * sq(5)), "r20": r(20) / (ac * sq(20)), "r60": r(60) / (ac * sq(60)),
        "ibs0": ibs, "ma20": (C - ma20) / (C * ac), "onmom": onmom / ac * sq(20), "idmom": idmom / ac * sq(20),
        "rel5": rel5 / (ac * sq(5)), "mkt0": bc(idr[spy] / ac[spy]), "vixz": bc(vixz), "dvix": bc(dvix),
        "vol": vol_c, "fri": bc(pd.Series((C.index.dayofweek == 4).astype(float), C.index)), "etf": etf,
    }
    s1 = lambda x: x.shift(1)
    feats_open = {
        "gap": gap_o / ao, "gap_mkt": bc(gap_o[spy] / ao[spy]), "id1": s1(idr) / ao, "r5": s1(r5) / (ao * sq(5)),
        "r20": s1(r(20)) / (ao * sq(20)), "r60": s1(r(60)) / (ao * sq(60)), "ibs1": s1(ibs),
        "ma20": (O - s1(ma20)) / (O * ao), "onmom": s1(onmom) / ao * sq(20), "idmom": s1(idmom) / ao * sq(20),
        "rel5": s1(rel5) / (ao * sq(5)), "vixz": bc(s1(vixz)), "dvix": bc(s1(dvix)), "vol": s1(vol_c), "etf": etf,
    }
    y_open = (idr / ao).clip(-clip, clip)
    nxt_on = on.shift(-1)
    y_close = (nxt_on / ac).clip(-clip, clip)
    out = {}
    for kind, feats, y, scale in (("OPEN", feats_open, y_open, ao), ("CLOSE", feats_close, y_close, ac)):
        cols = {k: v.stack(future_stack=True) for k, v in feats.items()}
        cols["y"] = y.stack(future_stack=True)
        cols["raw"] = (id_raw if kind == "OPEN" else on_raw.shift(-1)).stack(future_stack=True)
        cols["atr"] = scale.stack(future_stack=True)
        P = pd.DataFrame(cols)
        P.index.names = ["date", "ticker"]
        need = (OPEN_FEATS if kind == "OPEN" else CLOSE_FEATS) + ["atr"]
        P = P.replace([np.inf, -np.inf], np.nan).dropna(subset=need)
        P = P[P["atr"] > 0]
        out[kind] = P
    return out


def _fit_predict(model, Xtr, ytr, Xte, alpha):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Ztr, Zte = np.clip((Xtr - mu) / sd, -5, 5), np.clip((Xte - mu) / sd, -5, 5)
    if model == "ridge":
        A = Ztr.T @ Ztr + alpha * np.eye(Ztr.shape[1]); ym = ytr.mean()
        b = np.linalg.solve(A, Ztr.T @ (ytr - ym))
        return Zte @ b + ym
    if model == "hgb":
        from sklearn.ensemble import HistGradientBoostingRegressor
        m = HistGradientBoostingRegressor(max_depth=3, max_iter=150, learning_rate=0.05, min_samples_leaf=3000,
                                          l2_regularization=1.0, early_stopping=False, random_state=0)
        m.fit(Ztr, ytr)
        return m.predict(Zte)
    raise ValueError(model)


def walk_forward(P, feats, model="ridge", alpha=1e4, first_year=2004, embargo_days=5, last_year=None):
    """Annual expanding-window refit; returns predictions (in ATR units) for rows dated >= first_year."""
    years = sorted(set(P.index.get_level_values("date").year))
    dates = P.index.get_level_values("date")
    preds = []
    for Y in years:
        if Y < first_year or (last_year and Y > last_year):
            continue
        b = pd.Timestamp(Y, 1, 1)
        tr = (dates < b - pd.Timedelta(days=embargo_days)) & P["y"].notna().to_numpy()
        te = (dates >= b) & (dates < pd.Timestamp(Y + 1, 1, 1))
        if tr.sum() < 5000 or te.sum() == 0:
            continue
        p = _fit_predict(model, P.loc[tr, feats].to_numpy(float), P.loc[tr, "y"].to_numpy(float),
                         P.loc[te, feats].to_numpy(float), alpha)
        preds.append(pd.Series(p, index=P.index[te]))
    return pd.concat(preds) if preds else pd.Series(dtype=float)


def edge_table(P, pred, kind):
    """Cost-aware expected net return per row for long and short; returns DataFrame with dir & net edge."""
    D = P.loc[pred.index, ["atr"]].copy()
    D["pred_ret"] = pred * D["atr"]
    tick = D.index.get_level_values("ticker")
    cost = np.where(tick.isin(list(ETFS)), COST["etf"], COST["stock"])
    fin_long = LONG_FIN_NIGHT * np.where(D.index.get_level_values("date").dayofweek == 4, 3, 1) if kind == "CLOSE" else 0.0
    long_net = D["pred_ret"] - cost - fin_long
    short_net = -D["pred_ret"] - cost
    D["dir"] = np.where(long_net >= short_net, 1, -1)
    D["net"] = np.maximum(long_net, short_net)
    D["cost"] = cost
    return D


def select(D, kind, margin, max_per_slot, stop_atr):
    """Trade only where predicted net edge > margin * round-trip cost; keep the best max_per_slot per day."""
    S = D[D["net"] > margin * D["cost"]].copy()
    if S.empty:
        return pd.DataFrame(columns=["instrument", "date_in", "kind", "dir", "stop_pct", "score"])
    S = S.reset_index().sort_values(["date", "net"], ascending=[True, False]).groupby("date").head(max_per_slot)
    return pd.DataFrame({"instrument": S["ticker"].values, "date_in": S["date"].values, "kind": kind,
                         "dir": S["dir"].astype(int).values, "stop_pct": (stop_atr * S["atr"]).clip(0.003, 0.25).values,
                         "score": S["net"].values})


def decay_gate(sig, P, window="365D", min_slots=20):
    """Self-disabling switch for CLOSE signals: trade day d only if the strategy's own realised slot mean
    (judge cost model) over the trailing year, using slots dated < d (all exited by the open of d), is > 0."""
    if sig.empty:
        return sig
    key = pd.MultiIndex.from_arrays([pd.to_datetime(sig["date_in"]), sig["instrument"]])
    raw = P["raw"].reindex(key).to_numpy()
    d = key.get_level_values(0)
    dates = P.index.get_level_values("date").unique().sort_values()
    pos = dates.searchsorted(d)
    nxt_all = np.append(dates.to_numpy(dtype="datetime64[ns]"), np.datetime64("NaT", "ns"))
    nights = ((nxt_all[pos + 1] - d.to_numpy(dtype="datetime64[ns]")) / np.timedelta64(1, "D")).astype(float)
    cost = np.where(sig["instrument"].isin(list(ETFS)), COST["etf"], COST["stock"])
    fin = np.where(sig["dir"].to_numpy() > 0, -0.07, 0.01) * nights / 365.0
    ret = sig["dir"].to_numpy() * raw - cost + fin
    slot = pd.Series(ret, index=d).groupby(level=0).mean().dropna()
    trail = slot.rolling(window, min_periods=min_slots).mean()
    # gate for day d uses only slots strictly before d
    allowed = trail.reindex(dates).ffill().shift(1)
    ok = allowed.reindex(d).to_numpy() > 0
    return sig[ok].reset_index(drop=True)


def signals(frames, cfg=None):
    c = {**CFG, **(cfg or {})}
    panels = build_panel(frames, c["atr_n"], c["clip"])
    out = []
    for kind in c["kinds"]:
        P = panels[kind]; feats = OPEN_FEATS if kind == "OPEN" else CLOSE_FEATS
        pred = walk_forward(P, feats, c["model"], c["alpha"], c["first_year"], c["embargo_days"])
        if pred.empty:
            continue
        E = edge_table(P, pred, kind)
        if not c["trade_etfs"]:
            E = E[~E.index.get_level_values("ticker").isin(list(ETFS))]
        s = select(E, kind, c["margin"], c["max_per_slot"], c["stop_atr"])
        if c["gate"] and kind == "CLOSE":
            s = decay_gate(s, P)
        out.append(s)
    if not out:
        return pd.DataFrame(columns=["instrument", "date_in", "kind", "dir", "stop_pct", "score"])
    return pd.concat(out, ignore_index=True)
