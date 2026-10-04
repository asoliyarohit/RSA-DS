import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("scanner", Path(__file__).resolve().parents[1] / "scanner" / "scanner.py")
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)


def _row(**k):
    base = dict(candidate="X", volume_today="1000", volume_avg_20d="1000", price_change_5d_pct="0", news_items_7d="0", mentions_7d="10", mentions_avg_7d="10")
    base.update({a: str(b) for a, b in k.items()}); return base


def test_matches_guide_example_output():
    a = sc.score_row(_row(volume_today=2400000, volume_avg_20d=800000, price_change_5d_pct=6.5, news_items_7d=4, mentions_7d=310, mentions_avg_7d=120))
    c = sc.score_row(_row(volume_today=1800000, volume_avg_20d=600000, price_change_5d_pct=-2.0, news_items_7d=6, mentions_7d=520, mentions_avg_7d=140))
    assert (a["total"], a["volume"], a["momentum"], a["news"], a["attention"]) == (82.0, 30.0, 16.2, 20.0, 15.8)
    assert (c["total"], c["momentum"]) == (75.0, 0.0)


def test_missing_attention_is_rescaled_not_zeroed():
    s = sc.score_row(_row(volume_today=3000, volume_avg_20d=1000, price_change_5d_pct=10, news_items_7d=5, mentions_7d="", mentions_avg_7d=""))
    assert abs(s["total"] - 100.0) <= 0.2 and s["missing"] == "attention"   # parts round to 0.1 each, as in the guide
