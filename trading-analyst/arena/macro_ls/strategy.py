"""macro_ls: index-only pooled ridge on vol-normalised own-features, purged yearly walk-forward refit inside signals().
Trades only the top 5% |prediction| (threshold from the TRAINING predictions) in OPEN and CLOSE slots. Gold/oil loaded as context only."""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge

IDX = ['SPY', 'QQQ', 'DIA', 'EWG', 'FEZ', 'EWJ', 'EWU']
UNIVERSE = IDX + ['GC=F', 'CL=F']
N_TRIALS = 14   # 2 leaked-feature runs + 6 ridge variants (kind x cross x alpha) + feature corr scan + ~5 earlier design iterations
ALPHA, Q, FIRST, EMBARGO = 3000.0, 0.95, 2010, 5


def _panel(frames, kind):
    rows = []
    for t in IDX:
        f = frames.get(t)
        if f is None or len(f) < 300:
            continue
        o, h, l, c = f.open, f.high, f.low, f.close
        lr = np.log(c / c.shift()); vol20 = lr.rolling(20).std()
        on = np.log(o / c.shift()); idr = np.log(c / o)
        if kind == 'OPEN':
            vol = vol20.shift(1)
            d = pd.DataFrame({'gap': on / vol, 'id1': idr.shift() / vol, 'on1': on.shift() / vol,
                              'r5': np.log(c.shift() / c.shift(6)) / vol / np.sqrt(5),
                              'r20': np.log(c.shift() / c.shift(21)) / vol / np.sqrt(20),
                              'ibs': ((c - l) / (h - l)).shift() - .5})
            y = idr
        else:
            vol = vol20
            d = pd.DataFrame({'id0': idr / vol, 'on0': on / vol, 'r5': np.log(c / c.shift(5)) / vol / np.sqrt(5),
                              'r20': np.log(c / c.shift(20)) / vol / np.sqrt(20), 'ibs': (c - l) / (h - l) - .5})
            y = np.log(o.shift(-1) / c)
        d['y'] = y / vol; d['vol'] = vol; d['inst'] = t
        d.index.name = 'date'
        rows.append(d.reset_index())
    return pd.concat(rows, ignore_index=True)


def signals(frames):
    out = []
    for kind in ('OPEN', 'CLOSE'):
        P = _panel(frames, kind)
        fc = [c for c in P.columns if c not in ('date', 'inst', 'y', 'vol')]
        P[fc] = P[fc].clip(-4, 4)
        X = P.dropna(subset=fc + ['vol']).copy()
        X['date'] = pd.to_datetime(X['date'])
        last = X.date.max().year
        for yr in range(FIRST, last + 1):
            b = pd.Timestamp(f'{yr}-01-01')
            tr = X[(X.date >= '2004-06-01') & (X.date < b - pd.Timedelta(days=EMBARGO))].dropna(subset=['y'])
            te = X[(X.date >= b) & (X.date < pd.Timestamp(f'{yr + 1}-01-01'))]
            if len(tr) < 3000 or te.empty:
                continue
            tr = tr.assign(y=tr.y.clip(-4, 4))
            m = Ridge(alpha=ALPHA).fit(tr[fc], tr.y)
            th = np.quantile(np.abs(m.predict(tr[fc])), Q)
            p = m.predict(te[fc]); sel = np.abs(p) >= th
            s = te[sel]
            out.append(pd.DataFrame({'instrument': s.inst.values, 'date_in': s.date.values, 'kind': kind,
                                     'dir': np.sign(p[sel]).astype(int),
                                     'stop_pct': np.clip(2.0 * s.vol.values, 0.005, 0.05),
                                     'score': np.abs(p[sel])}))
    if not out:
        return pd.DataFrame(columns=['instrument', 'date_in', 'kind', 'dir', 'stop_pct', 'score'])
    return pd.concat(out, ignore_index=True)
