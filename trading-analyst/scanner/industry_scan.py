"""Industry-category early-signal scan (research only). Free data: yfinance daily bars + Yahoo per-ticker RSS headlines.
Score = the guide's transparent score on volume / momentum / news (attention skipped, weights rescaled). Bullish side uses +5d change,
bearish-pressure side uses -5d change (descriptive for a CFD SELL reading list, NOT a prediction). AI / war keyword hits are shown for reading only."""
import importlib.util
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analyst import news  # noqa: E402

spec = importlib.util.spec_from_file_location("sc", HERE / "scanner.py"); sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)

CATS = {
    "1 AI chips & semis": "NVDA AMD AVGO TSM MU ASML ARM MRVL QCOM INTC".split(),
    "2 AI software & cloud": "MSFT GOOGL META AMZN ORCL PLTR CRM SNOW NOW ADBE".split(),
    "3 AI infrastructure & power": "VRT SMCI ANET DELL CEG VST ETN GEV EQIX DLR".split(),
    "4 Defense & aerospace (war)": "LMT RTX NOC GD LHX BA KTOS HII AVAV TDG".split(),
    "5 Cybersecurity": "CRWD PANW ZS FTNT NET S OKTA CHKP CYBR RBRK".split(),
    "6 Energy (war/oil)": "XOM CVX COP OXY SLB EOG MPC LNG VLO HAL".split(),
    "7 Gold, metals & uranium": "NEM AEM WPM KGC FCX SCCO MP CCJ AA GOLD".split(),
    "8 Financials": "JPM BAC GS MS V MA BLK SCHW C WFC".split(),
    "9 Healthcare & pharma": "LLY UNH JNJ PFE MRK ABBV ISRG VRTX TMO REGN".split(),
    "10 Consumer & industrial": "WMT COST HD NKE MCD CAT DE GE UPS TSLA".split(),
}
AI_RE = re.compile(r"\b(ai|a\.i\.|artificial intelligence|gpu|chips?|data ?centers?|openai|nvidia|llm|generative|semiconductor)\b", re.I)
WAR_RE = re.compile(r"\b(war|ukraine|russia|iran|israel|gaza|taiwan|china|missile|military|defen[cs]e|nato|drone|sanction|conflict|pentagon|tariffs?)\b", re.I)


def headlines(t):
    return t, news._fetch(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")


def run(per_cat=3):
    import yfinance as yf

    tickers = sorted({t for v in CATS.values() for t in v})
    px = yf.download(tickers, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by="ticker", threads=True)
    with ThreadPoolExecutor(8) as ex:
        hl = dict(ex.map(headlines, tickers))
    cut = datetime.now(timezone.utc) - timedelta(days=7)
    rows = []
    for cat, ts in CATS.items():
        for t in ts:
            try:
                d = px[t].dropna(subset=["Close"])
                if len(d) < 25:
                    continue
                c, v = d["Close"], d["Volume"]
                items = [i for i in hl.get(t, []) if i["time"] and i["time"] >= cut]
                txt = [i["title"] for i in items]
                chg5 = float((c.iloc[-1] / c.iloc[-6] - 1) * 100)
                base = dict(candidate=t, volume_today=v.iloc[-1], volume_avg_20d=v.iloc[-21:-1].mean(), news_items_7d=len(items), mentions_7d="", mentions_avg_7d="")
                lng = sc.score_row({**base, "price_change_5d_pct": chg5})
                sht = sc.score_row({**base, "price_change_5d_pct": -chg5})
                bear = sht["total"] > lng["total"]
                s = sht if bear else lng
                tr = pd.concat([d["High"] - d["Low"], (d["High"] - c.shift()).abs(), (d["Low"] - c.shift()).abs()], axis=1).max(axis=1)
                rows.append(dict(category=cat, ticker=t, price=round(float(c.iloc[-1]), 2), d1=round(float((c.iloc[-1] / c.iloc[-2] - 1) * 100), 1), d5=round(chg5, 1),
                                 vol_x=round(float(v.iloc[-1] / v.iloc[-21:-1].mean()), 2), atr_pct=round(float(tr.rolling(14).mean().iloc[-1] / c.iloc[-1] * 100), 1),
                                 news7=len(items), ai=sum(bool(AI_RE.search(x)) for x in txt), war=sum(bool(WAR_RE.search(x)) for x in txt),
                                 side="SELL-pressure" if bear else "BUY-pressure", score=s["total"], vol=s["volume"], mom=s["momentum"], news=s["news"]))
            except Exception:
                continue
    df = pd.DataFrame(rows)
    top = df.sort_values(["category", "score"], ascending=[True, False]).groupby("category").head(per_cat).reset_index(drop=True)
    top["rank"] = top["score"].rank(ascending=False, method="first").astype(int)
    top = top.sort_values("rank")
    top.to_csv(HERE / "industry_watchlist.csv", index=False)
    return df, top, str(c.index[-1].date())


if __name__ == "__main__":
    df, top, last = run()
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(f"Data through {last}. Scanned {len(df)} stocks in {df.category.nunique()} categories; top 3 per category shown (research only).\n")
    print(top[["rank", "category", "ticker", "price", "d1", "d5", "vol_x", "atr_pct", "news7", "ai", "war", "side", "score", "vol", "mom", "news"]].to_string(index=False))
