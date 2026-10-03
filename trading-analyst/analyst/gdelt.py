"""Point-in-time daily news tone/volume from GDELT DOC API (free, 1 request / 5 s, ~6 months of daily history)."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data" / "gdelt"
QUERIES = ["stock market", "Federal Reserve", "inflation", "tariffs", "recession", "earnings", "oil prices", "interest rates"]
MODES = {"tone": "timelinetone", "vol": "timelinevolraw"}


def _get(query: str, mode: str, span="6m", tries=5):
    u = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(
        {"query": f'"{query}" sourcelang:eng', "mode": mode, "format": "json", "timespan": span})
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
            return json.loads(raw)["timeline"][0]["data"]
        except Exception:
            time.sleep(8 + 4 * i)
    return None


def fetch(refresh=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    for q in QUERIES:
        for key, mode in MODES.items():
            p = CACHE / f"{q.replace(' ', '_')}_{key}.csv"
            if p.exists() and not refresh:
                continue
            d = _get(q, mode); time.sleep(6)
            if d is None:
                print(f"FAILED {q} {key}"); continue
            df = pd.DataFrame(d); df["date"] = pd.to_datetime(df["date"].str[:8]); df[["date", "value"]].to_csv(p, index=False)
            print(f"{q} {key}: {len(df)} days {df['date'].min().date()} -> {df['date'].max().date()}")


def load() -> pd.DataFrame:
    """DataFrame indexed by date, columns '<query>|tone' and '<query>|vol'."""
    cols = {}
    for q in QUERIES:
        for key in MODES:
            p = CACHE / f"{q.replace(' ', '_')}_{key}.csv"
            if p.exists():
                cols[f"{q}|{key}"] = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"]
    return pd.DataFrame(cols).sort_index()


if __name__ == "__main__":
    fetch()
