"""event_regime: day-2 continuation after a volume-confirmed earnings/news-style gap, gated by VIX regime.

Event (detected from price/volume only, day E, all known at E's close):
    |open_E / close_{E-1} - 1| >= 2.0 x ATR14 (ATR measured up to E-1)
    volume_E >= 3.0 x mean(volume over the 50 sessions before E)        (news/earnings proxy)
    close_E - open_E has the same sign as the gap                       (the market accepted the news)
    VIX close on E < 30                                                 (regime gate: not a macro-panic tape)
Trade: OPEN on the next session E+1 in the gap direction, hard stop 2 x ATR14, exit at E+1 close.
Score = |gap| in ATR units (judge keeps the 3 strongest per slot).

VOLUME: the judge's frames carry OHLC only, so daily volume is fetched here via yfinance (split-adjusted),
cached in trading-analyst/data/vol_<ticker>.csv, never requested past the last date in the frames handed in
(so a --dev run never downloads 2023+ data), and re-indexed onto each frame's own dates. Volume of day E is
used only for a decision taken at E+1's open, so it is causal. If volume for a ticker cannot be fetched,
that ticker produces no signals (deterministic given the cache).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Fixed list, chosen before testing: the repo's original 31 large caps (tech-heavy) + 61 S&P-100 style large caps
# added as an out-of-universe check. Survivorship-biased (current names). WBA and BK dropped: Yahoo returned no data.
ORIG = ["AMD", "META", "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "NFLX", "MU", "QCOM", "ADBE", "CRM", "INTC", "BA",
        "GE", "F", "GM", "IBM", "T", "XOM", "CVX", "JPM", "BAC", "C", "DIS", "NKE", "PYPL", "CSCO", "ORCL", "KHC"]
EXTRA = ("ABBV ABT ACN AIG AMGN AMT AVGO AXP BKNG BLK BMY CAT CHTR CL CMCSA COF COP COST CVS DHR DUK EMR EXC FDX GD GILD GS "
         "HD HON JNJ KO LIN LLY LMT LOW MA MCD MDT MET MMM MO MRK MS NEE PEP PFE PG PM RTX SBUX SO SPG TGT TMO TXN UNH UNP "
         "UPS USB V VZ WFC WMT").split()
UNIVERSE = ORIG + EXTRA
N_TRIALS = 35  # see REPORT.md: 9 index calendar/VIX ideas, 2 index regime ideas, 3 event variants, 21 robustness/gate/universe runs

GAP_ATR, VOL_X, STOP_ATR, VIX_MAX = 2.0, 3.0, 2.0, 30.0
VOL_DIR = Path(__file__).resolve().parents[2] / "data"


def _volume(ticker: str, need_end: pd.Timestamp) -> pd.Series | None:
    path = VOL_DIR / f"vol_{ticker.lower()}.csv"
    s = None
    if path.exists():
        s = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
    if s is None or s.index.max() < need_end - pd.Timedelta(days=5):
        try:
            import yfinance as yf
            df = yf.download(ticker, start="2000-01-01", end=(need_end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                             auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            v = df["Volume"].astype(float)
            v.index = pd.to_datetime(v.index).tz_localize(None)
            v = v[v.index <= need_end]
            if len(v):
                VOL_DIR.mkdir(exist_ok=True)
                v.rename("volume").to_csv(path)
                s = v
        except Exception:
            pass
    return s


def _atr(f: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = pd.concat([f.high - f.low, (f.high - f.close.shift()).abs(), (f.low - f.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean() / f.close


def signals(frames):
    cols = ["instrument", "date_in", "kind", "dir", "stop_pct", "score"]
    vix = frames.get("^VIX")
    rows = []
    for s in UNIVERSE:
        f = frames.get(s)
        if f is None or len(f) < 60:
            continue
        f = f.dropna(subset=["open"])
        vol = _volume(s, f.index.max())
        if vol is None:
            continue
        vol = vol.reindex(f.index).replace(0, np.nan)
        vavg = vol.rolling(50, min_periods=40).mean().shift(1)
        a = _atr(f).shift(1)
        gap = (f.open / f.close.shift(1) - 1) / a
        conf = np.sign(f.close - f.open) == np.sign(gap)
        vx = vix["close"].reindex(f.index).ffill() if vix is not None else pd.Series(np.nan, index=f.index)
        ev = (gap.abs() >= GAP_ATR) & (vol / vavg >= VOL_X) & conf & (vx < VIX_MAX) & a.notna()
        idx = f.index
        for i in np.flatnonzero(ev.to_numpy()):
            if i + 1 >= len(idx):
                continue
            rows.append((s, idx[i + 1], "OPEN", int(np.sign(gap.iloc[i])), STOP_ATR * float(a.iloc[i]), float(abs(gap.iloc[i]))))
    return pd.DataFrame(rows, columns=cols)
