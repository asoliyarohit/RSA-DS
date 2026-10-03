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
