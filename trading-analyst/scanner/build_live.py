"""Build live_data.csv for scanner.py from FREE sources: yfinance (volume, 5d change) and Yahoo per-ticker RSS (news items in 7 days).
No attention feed is included, so the mentions columns are blank and the attention signal is skipped. Research only; data may be delayed or wrong."""
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analyst import news, universe  # noqa: E402


def build(tickers=None, out=HERE / "live_data.csv"):
    import yfinance as yf

    tickers = tickers or universe.STOCKS
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    rows = []
    for t in tickers:
        d = yf.download(t, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if d.empty or len(d) < 25:
            continue
        if hasattr(d.columns, "levels"):
            d.columns = d.columns.get_level_values(0)
        vol_today, vol_avg = float(d["Volume"].iloc[-1]), float(d["Volume"].iloc[-21:-1].mean())
        chg5 = (float(d["Close"].iloc[-1]) / float(d["Close"].iloc[-6]) - 1) * 100
        items = news._fetch(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")
        n7 = sum(1 for it in items if it["time"] is not None and it["time"] >= cutoff)
        rows.append([t, int(vol_today), int(vol_avg), round(chg5, 2), n7, "", ""])
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate", "volume_today", "volume_avg_20d", "price_change_5d_pct", "news_items_7d", "mentions_7d", "mentions_avg_7d"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out} (last bar {d.index[-1].date()})")


if __name__ == "__main__":
    build()
