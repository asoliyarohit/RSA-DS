"""Early-Signal Stock Scanner - research only. Reads a CSV, scores four signals out of 100, ranks candidates,
writes watchlist.csv. No trading, no broker, no network. Standard library only.
sample_data.csv is EXAMPLE DATA (fictional). If the mentions columns are blank (live builder has no attention feed),
that signal is skipped and the remaining weights are rescaled to 100 - stated in the output."""
import csv
import datetime
import sys
from pathlib import Path

WEIGHTS = {"volume": 30, "momentum": 25, "news": 25, "attention": 20}   # educational defaults, NOT proven predictors
THRESHOLD = 50       # minimum score to appear on the watchlist
TOP_N = 5
REQUIRED = ["candidate", "volume_today", "volume_avg_20d", "price_change_5d_pct", "news_items_7d", "mentions_7d", "mentions_avg_7d"]


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def score_row(r):
    vol_ratio = _f(r["volume_today"]) / max(_f(r["volume_avg_20d"]), 1)
    volume = clamp((vol_ratio - 1) / 2)                       # 1x -> 0, 3x+ -> full
    momentum = clamp(_f(r["price_change_5d_pct"]) / 10)       # 0% -> 0, +10%+ -> full
    news = clamp(_f(r["news_items_7d"]) / 5)                  # 5+ items -> full
    m7, m_avg = _f(r["mentions_7d"]), _f(r["mentions_avg_7d"])
    has_att = m7 is not None and m_avg is not None
    attention = clamp((m7 / max(m_avg, 1) - 1) / 2) if has_att else None   # 1x -> 0, 3x+ -> full
    raw = {"volume": volume, "momentum": momentum, "news": news, "attention": attention}
    live = {k: v for k, v in raw.items() if v is not None}
    scale = 100.0 / sum(WEIGHTS[k] for k in live)             # 1.0 when all four signals exist
    parts = {k: round((raw[k] * WEIGHTS[k] * scale) if raw[k] is not None else 0.0, 1) for k in WEIGHTS}
    parts["total"] = round(sum(parts.values()), 1)
    parts["missing"] = ",".join(k for k, v in raw.items() if v is None)
    return parts


def main(path=None, out="watchlist.csv"):
    path = path or str(Path(__file__).with_name("sample_data.csv"))
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("No data rows found in " + path)
    missing = [c for c in REQUIRED if c not in rows[0]]
    if missing:
        sys.exit("CSV is missing columns: " + ", ".join(missing))
    scored = []
    for r in rows:
        s = score_row(r); s["candidate"] = r["candidate"]; scored.append(s)
    scored.sort(key=lambda s: s["total"], reverse=True)
    watch = [s for s in scored if s["total"] >= THRESHOLD][:TOP_N]
    today = datetime.date.today().isoformat()
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "rank", "candidate", "total", "volume", "momentum", "news", "attention", "missing_signals", "status"])
        for i, s in enumerate(watch, 1):
            w.writerow([today, i, s["candidate"], s["total"], s["volume"], s["momentum"], s["news"], s["attention"], s["missing"], "REVIEW REQUIRED"])
    print(f"Scored {len(scored)} candidates. {len(watch)} passed threshold {THRESHOLD}.")
    print(f"{'RANK':<5}{'CANDIDATE':<14}{'TOTAL':>7}{'VOL':>6}{'MOM':>6}{'NEWS':>6}{'ATT':>6}")
    for i, s in enumerate(scored, 1):
        flag = "  <- watchlist" if s in watch else ""
        print(f"{i:<5}{s['candidate']:<14}{s['total']:>7}{s['volume']:>6}{s['momentum']:>6}{s['news']:>6}{s['attention']:>6}{flag}")
    if any(s["missing"] for s in scored):
        print("\nNote: signals with no data were skipped and the rest rescaled to 100.")
    print("\nResearch only. Review every candidate at the original source. Nothing is traded.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
