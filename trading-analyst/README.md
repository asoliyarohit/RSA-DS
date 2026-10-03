# Trading Analyst (CFD, free stack)

Goal: grow a small Revolut CFD account as fast as the evidence allows, with two daily decisions:
**OPEN** (day trade, flat at close) and **CLOSE** (buy ~15:55 ET, sell at next open).

Free only: yfinance daily data (SPY/QQQ as US500/US100 proxies, VIX), RSS news (Yahoo, MarketWatch, Investing, Fed), pandas/numpy.
Design borrowed from Oft3r/agentic-trading-desk: AI fetches and explains, deterministic scripts calculate, the human executes.

```
pip install -r requirements.txt
python -m analyst backtest            # walk-forward: pick on <2015, test untouched after
python -m analyst solve --years 3     # Monte Carlo: P(1k -> 100k) per risk level
python -m analyst brief --equity 1000 --risk 0.05   # news + sentiment + quant gate (daily)
python -m pytest -q
```

## What the evidence says (honest)
| Setup | Out-of-sample result | Verdict |
|---|---|---|
| CLOSE -> next open, US500 (RSI2 trend dip) | +11 bps/trade, t=2.6 | usable edge |
| CLOSE -> next open, US100 (IBS trend dip) | +9 bps/trade, t=2.4 | usable edge |
| OPEN -> close gap fade/follow (both) | t=0.2 / 0.9 | **no edge after costs** |

- Combined validated edge ~10 bps/trade, ~50 trades/yr. Monte Carlo (out-of-sample trades, 20x, 30% risk/trade):
  **P(1k -> 100k) = 0% in 3 yrs, ~24% in 10 yrs** (~4% with the drawdown throttle). Lower risk is far worse.
- So 100x in the shortest time is not achievable *with evidence* from these setups; 100x is gambling-level risk.
  More frequency/instruments/intraday data (needs paid history) is the only lever; add setups only through the same walk-forward gate.
- Data caveat: Yahoo index (^GSPC) opens are stale before ~2014, so ETFs are used. Entry at "close" uses the daily close as proxy for 15:55.
- Not modelled: guaranteed stops, weekend/holiday gaps beyond history, Revolut re-quotes, min sizes. Revolut costs are placeholders in `analyst/cfd.py`.
- Sentiment is a lexicon over headlines: unvalidated, used only as veto/context. See `skills/trading-analyst/SKILL.md`.

Not financial advice. CFDs lose money for most retail accounts.
