"""Free news + sentiment gathering (RSS only, stdlib). Lexicon scoring is crude and UNVALIDATED:
it is used as context / veto flags, never as a backtested edge. Claude writes the narrative from this."""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = {
    "Yahoo SPY": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY&region=US&lang=en-US",
    "Yahoo QQQ": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=QQQ&region=US&lang=en-US",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "Investing.com": "https://www.investing.com/rss/news_25.rss",
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
}
POS = set("rally surge surges gain gains beat beats record rebound rebounds upgrade optimism cooling easing cut cuts growth strong soar jump jumps boost relief".split())
NEG = set("plunge plunges fall falls drop drops miss misses slump selloff sell-off downgrade fears recession inflation hike hikes tariff tariffs war crisis default weak crash slide slides warning cuts-jobs layoffs shutdown".split())
EVENT_RISK = {  # headline keywords that mean a scheduled/binary event: reduce size or skip
    "fomc": "Fed decision", "fed ": "Fed", "powell": "Fed chair", "cpi": "Inflation print", "payrolls": "Jobs report",
    "nonfarm": "Jobs report", "pce": "Inflation print", "gdp": "GDP", "earnings": "Earnings", "nvidia": "NVDA earnings/news",
    "tariff": "Trade policy", "shutdown": "Gov shutdown", "war": "Geopolitics", "election": "Election",
}


def _fetch(url: str, timeout=15) -> list[dict]:
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout).read()
        root = ET.fromstring(raw)
    except Exception:
        return []
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate") or "")
        except Exception:
            ts = None
        out.append({"title": title, "time": ts, "link": it.findtext("link") or ""})
    return out


def score(title: str) -> int:
    w = re.findall(r"[a-z\-]+", title.lower())
    return sum(x in POS for x in w) - sum(x in NEG for x in w)


def gather(max_per_feed=8) -> dict:
    items, seen = [], set()
    for src, url in FEEDS.items():
        for it in _fetch(url)[:max_per_feed]:
            k = it["title"].lower()[:60]
            if not it["title"] or k in seen:
                continue
            seen.add(k)
            it.update(source=src, score=score(it["title"]))
            items.append(it)
    items.sort(key=lambda x: x["time"].timestamp() if x["time"] else 0, reverse=True)
    flags = sorted({v for it in items for k, v in EVENT_RISK.items()
                    if re.search(rf"\\b{re.escape(k.strip())}\\b", it["title"].lower())})
    net = sum(i["score"] for i in items)
    tilt = "risk-on" if net >= 3 else "risk-off" if net <= -3 else "mixed/neutral"
    return {"items": items, "net_score": net, "tilt": tilt, "event_flags": flags}
