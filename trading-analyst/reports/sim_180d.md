# 180-day walk-forward simulation (2026-04-07 -> 2026-10-02, 125 trading days), run ONCE on a frozen spec

Spec (frozen before the run; council opus/sonnet/fable): SPY/QQQ/DIA only; ridge trained on 2001->2026-04-06 then frozen; every decision uses data <= T-1;
CLOSE call = buy/sell at T-1 close, exit T open; OPEN call = pre-market for T, enter T open, exit T close (1 sigma stop), no OPEN trade on the 4 verified FOMC days;
S = z_model + 0.10 * z_tone (GDELT 'stock market' & 'earnings' tone, 1-2 day lag, zero weight first 20 days); top-20% days only; VIX>35 no trade; tariff-news-volume veto.
Two specification fixes were made on TRAINING data before the window was ever scored (threshold = 80th pct of daily max |z| on train).
The model families (mode A council sizing ~1.1-1.5x notional, B 1.5% risk, C 10% risk) were all reported; none was picked after the fact.

| | News+price | Price only |
|---|---|---|
| Trades (CLOSE / OPEN) | 55 (37 / 18) | 57 (38 / 19) |
| BUY / SELL calls | 50 / 5 | 52 / 5 |
| Net bps per trade | +18.6 (SE 11.0, t 1.68, CI -3 to +40) | +11.6 (SE 11.2, t 1.03) |
| Hit rate | 62% | 58% |
| End equity from $1,000: council sizing / 1.5% risk / 10% risk | $1,148 / $1,106 / $1,753 | $1,103 / $1,071 / $1,404 |
| Max drawdown (council / 10% risk) | 4% / 20% | 5% / 28% |

Benchmarks: SPY buy-and-hold +17.8% ($1,178) over the same window (1x). Unconditional always-long overnight: +4 to +8 bps/trade; always-long open->close: -2 to -10.
Controls: direction-flipped coin-flip null (misleading here: half the flips are shorts in a bull market) beaten 98-99%; FAIR null (random days, always BUY, same counts)
mean +3.0 bps [-10.5, +16.1], ours beats 97% overall and 83% for BUY-only.

Honest reading
- Not significant (t 1.68, one-sided p ~ 0.05) and fair-null percentile 97%, from 55 trades in ONE bull regime; nearly all calls were BUY (dip-buying in an uptrend).
  Earlier arena candidates also looked good in development and failed the sealed holdout. This is a genuine pre-registered forward test, but it is one draw.
- News added +7 bps per trade vs price-only, but the difference is far inside noise (SE ~11): the 0.10 tone weight flipped only a handful of calls; the tariff-volume veto removed 2 close trades.
- It did NOT beat SPY buy-and-hold in dollars with council sizing ($1,148 vs $1,178), and nowhere near 100x: +15% in 6 months; the 10%-risk mode's +75% is ~within luck (it also had 20% drawdown).
- Council pre-registered predictions: median end $1,000-1,020, edge ~0 to +2 bps; actual was better than predicted. CPI/jobs veto not applied (dates not verifiable); guard evidence-gate disabled for the simulation.
- Day-by-day table: reports/sim_180d_trades.csv. Reproduce: python scripts/run_sim180.py ; python scripts/sim180_controls.py
