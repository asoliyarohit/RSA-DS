import numpy as np
import pandas as pd

from analyst import features
from analyst.cfd import CFDSpec, equity_factor
from analyst.strategies import CloseParams, OpenParams, trades_close, trades_open


def _ohlc(n=300, seed=1):
    r = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(r.normal(0, 0.01, n)))
    o = c * (1 + r.normal(0, 0.003, n)); h = np.maximum(o, c) * 1.004; l = np.minimum(o, c) * 0.996
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=pd.bdate_range("2020-01-01", periods=n))


def test_round_trip_cost():
    assert abs(CFDSpec().round_trip_cost() - 3.5e-4) < 1e-12


def test_leverage_multiplies_loss_and_is_capped():
    one = np.array([[-0.01]]); m = np.ones((1, 1))
    assert abs(equity_factor(one, np.array([[0.01]]), m, 0.05, 20.0)[0] - 0.95) < 1e-9      # 5x notional * -1%
    assert abs(equity_factor(one, np.array([[0.001]]), m, 0.05, 20.0)[0] - 0.80) < 1e-9     # capped at 20x
    assert equity_factor(np.array([[-0.2]]), np.array([[0.001]]), m, 0.05, 20.0)[0] == 0.0  # wipe-out floors at 0


def test_weekend_financing_is_three_nights():
    c = CFDSpec()
    assert abs(c.financing(np.array([1.0]), np.array([3.0]))[0] + 3 * 0.065 / 365) < 1e-12


def test_no_lookahead_in_features():
    df = _ohlc(); full = features.build(df); cut = features.build(df.iloc[:250])
    cols = ["gap_atr_o", "trend_o", "ibs_c", "rsi2_c", "atr_c"]
    pd.testing.assert_frame_equal(full[cols].iloc[:250], cut[cols], check_exact=False)


def test_stop_resolves_against_us_and_hard_stop_caps_loss():
    f = features.build(_ohlc(seed=3))
    t = trades_open(f, OpenParams(mode="follow", gap_atr=0.0, trend=False, both_sides=True, stop_atr=1.0), CFDSpec())
    s = t[t["stopped"]]
    assert len(s) > 0
    assert (s["ret"] > -(s["stop_pct"] + 0.001)).all()            # loss ~= stop + costs, never worse intraday


def test_overnight_trade_uses_next_open():
    f = features.build(_ohlc(seed=5))
    t = trades_close(f, CloseParams(mode="ibs", thr=1.0, trend=False, both_sides=False), CFDSpec())
    r = t.iloc[10]; i = f.index.get_loc(r["date"])
    assert abs(r["gross"] - (f["open"].iloc[i + 1] / f["close"].iloc[i] - 1)) < 1e-12


def test_event_flags_use_word_boundaries(monkeypatch):
    from analyst import news
    monkeypatch.setattr(news, "_fetch", lambda url, timeout=15: [
        {"title": "Cramer warned viewers", "time": None, "link": ""},
        {"title": "FOMC decision looms as CPI nears", "time": None, "link": ""}])
    flags = news.gather()["event_flags"]
    assert "Geopolitics" not in flags and "Fed decision" in flags and "Inflation print" in flags


def test_journal_math_and_calibration(tmp_path, monkeypatch):
    from analyst import journal as j
    monkeypatch.setattr(j, "REPORTS", tmp_path)
    assert abs(j.spread_bps(99.99, 100.01) - 2.0) < 1e-6
    g, n = j.trade_bps("sell", 100.0, 99.0, fee_bps=3)
    assert abs(g - 100.0) < 1e-6 and abs(n - 97.0) < 1e-6
    for _ in range(29):
        j.log_quote("us500", 7720.0, 7721.0)
    assert not j.calibrate()["US500"]["enough"]
    j.log_quote("US500", 7720.0, 7721.0)
    assert j.calibrate()["US500"]["enough"] and abs(j.calibrate()["US500"]["median_bps"] - 1.3) < 0.05


def _guard(tmp_path, monkeypatch):
    from analyst import guard
    monkeypatch.setattr(guard, "STATE", tmp_path / "g.json")
    monkeypatch.setattr(guard, "evidence_ok", lambda: (True, "ok"))
    return guard


def test_guard_caps_and_never_raises_risk(tmp_path, monkeypatch):
    from datetime import date
    g = _guard(tmp_path, monkeypatch)
    d = g.check(1000, 0.20, date(2026, 1, 5))
    assert d.allowed and d.risk <= g.RISK_CAP + 1e-12


def test_guard_daily_limit_blocks_and_next_day_reopens(tmp_path, monkeypatch):
    from datetime import date
    g = _guard(tmp_path, monkeypatch)
    g.check(1000, 0.02, date(2026, 1, 5))
    assert not g.check(955, 0.02, date(2026, 1, 5)).allowed          # -4.5% in the day
    assert g.check(955, 0.02, date(2026, 1, 6)).allowed


def test_guard_drawdown_halts_until_reset(tmp_path, monkeypatch):
    from datetime import date
    g = _guard(tmp_path, monkeypatch)
    g.check(1000, 0.02, date(2026, 1, 5))
    assert not g.check(790, 0.02, date(2026, 1, 20)).allowed          # -21% from peak
    assert not g.check(1000, 0.02, date(2026, 2, 20)).allowed         # still halted even after recovery
    g.reset()
    assert g.check(1000, 0.02, date(2026, 2, 21)).allowed


def test_guard_loss_streak_halves_risk_and_event_blocks(tmp_path, monkeypatch):
    from datetime import date
    g = _guard(tmp_path, monkeypatch)
    eq = 1000.0
    for i in range(3):
        g.check(eq, 0.02, date(2026, 1, 5 + i)); eq *= 0.99; g.record_close(eq, date(2026, 1, 5 + i))
    d = g.check(eq, 0.04, date(2026, 1, 9))
    assert d.allowed and abs(d.risk - 0.02) < 1e-9
    assert not g.check(eq, 0.02, date(2026, 1, 10), ["Fed decision"]).allowed


def test_guard_evidence_gate_blocks_real_money(tmp_path, monkeypatch):
    from datetime import date
    from analyst import guard
    monkeypatch.setattr(guard, "STATE", tmp_path / "g.json")
    monkeypatch.setattr(guard, "evidence_ok", lambda: (False, "paper record has 0/100"))
    d = guard.check(1000, 0.02, date(2026, 1, 5))
    assert not d.allowed and d.risk == 0.0 and "PAPER ONLY" in d.reasons[0]


def test_judge_detects_score_and_stop_leaks():
    """Regression: a leak hidden in `score` (which ranks/selects trades) or `stop_pct` (which sizes them) must be caught."""
    import types
    from arena import judge

    def make(leak):
        def signals(frames):
            rows = []
            for t, f in frames.items():
                if t == "^VIX":
                    continue
                nxt = (f["open"].shift(-1) / f["close"] - 1)
                for d, v in nxt.items():
                    rows.append({"instrument": t, "date_in": d, "kind": "CLOSE", "dir": 1,
                                 "stop_pct": 0.01 + (abs(v) if leak == "stop" and v == v else 0.0),
                                 "score": float(v) if leak == "score" and v == v else 1.0})
            return pd.DataFrame(rows)
        return types.SimpleNamespace(signals=signals)

    fr = {"AAA": _ohlc(500, 9), "BBB": _ohlc(500, 10), "^VIX": _ohlc(500, 11)}
    assert judge.lookahead_check(make(None), fr)[0]
    assert not judge.lookahead_check(make("score"), fr)[0]
    assert not judge.lookahead_check(make("stop"), fr)[0]


def test_judge_ignores_nonpositive_prices():
    from arena import judge
    idx = pd.bdate_range("2020-04-15", periods=8)
    f = pd.DataFrame({"open": [20, 19, 18, -30, 5, 5, 5, 5.0], "high": [21, 20, 19, -20, 6, 6, 6, 6.0],
                      "low": [19, 18, 17, -40, 4, 4, 4, 4.0], "close": [19, 18, 17, -37, 5, 5, 5, 5.0]}, index=idx)
    sig = pd.DataFrame([{"instrument": "CL=F", "date_in": idx[3], "kind": "OPEN", "dir": -1, "stop_pct": 0.05, "score": 1.0},
                        {"instrument": "CL=F", "date_in": idx[2], "kind": "CLOSE", "dir": -1, "stop_pct": 0.05, "score": 1.0}])
    assert judge.fills(sig, {"CL=F": f}).empty
