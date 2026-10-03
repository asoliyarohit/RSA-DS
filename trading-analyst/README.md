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

## STATUS: arena verdict (read first)
Three independent competitors (rules, event/regime, ML) each built a strategy on data to 2022; all passed the dev judge and
**all three failed the sealed 2023+ holdout** (see `arena/RESULTS.md`). No validated edge exists in this repo today. Do not trade it
with real money; paper trade and journal only. 1k -> 100k is not supported by any evidence we could produce.

`python -m analyst daycall` gives one BUY/SELL open->close CFD call per session with a MEASURED track record (weights fixed a priori, not fitted).
Result: it LOSES after costs (dev t=-2.8, holdout 2023+ t=-4.2, 44% win), so it sizes to PAPER ONLY. Flipping its sign after seeing this would be curve-fitting, and gross edge is only ~-12 bps vs ~16 bps costs anyway.

## What the evidence says (honest)
| Setup | Out-of-sample result | Verdict |
|---|---|---|
| CLOSE -> next open, US500 (RSI2 trend dip) | +11 bps/trade, t=2.6 | usable edge |
| CLOSE -> next open, US100 (IBS trend dip) | +9 bps/trade, t=2.4 | usable edge |
| OPEN -> close gap fade/follow (both) | t=0.2 / 0.9 | **no edge after costs** |

- Combined validated edge ~9 bps/trade after Revolut-style costs, ~50 trades/yr.
- **Revolut at 5x leverage (confirmed by user)** caps position size, so risk per trade tops out near 7%.
  Monte Carlo on out-of-sample trades: **P(1k -> 100k) = 0% in 3 yrs, 0% in 10 yrs, ~3-4% in 20 yrs.**
  Median outcome at 8% risk: ~2.8k after 10 yrs, ~7.8k after 20 yrs (about +10-15%/yr). At 20x it was ~24% in 10 yrs,
  but that leverage is not available to this account.
- Conclusion: 100x is not reachable from these setups. A realistic target is 2-4x in 10 years with ~25% max drawdown.
  More validated setups/instruments/intraday data are the only lever. Add them only through the same walk-forward gate.
- **Single stocks at 5x (31 large caps incl. laggards, pooled walk-forward, `python -m analyst stocks`):**
  overnight hold FAILS out of sample (-9 bps/trade, t=-4.4). Opening gap-and-go (follow gaps >= 3 ATR in trend direction, 2.5 ATR stop)
  made +50 bps/trade OOS (t~2, only ~17 trades/yr) but it is fragile: train t was just 1.1, the 5 best trades are 65% of profit
  (18 bps without them) and 4 of 12 OOS years lost money. Compounded OOS: ~6%/yr at 5% risk, ~19%/yr with ~50% drawdown at 20% risk.
  P(1k -> 100k) ~0% in 3-5 yrs, ~1% in 10 yrs. Headline 10% moves are visible only in hindsight; the average follow-through is ~0.5%.
  Caveats: survivorship bias (no delisted names), stock CFD costs assumed (10 bps spread, 3 bps slippage), earnings gaps not modelled separately.
- Data caveat: Yahoo index (^GSPC) opens are stale before ~2014, so ETFs are used. Entry at "close" uses the daily close as proxy for 15:55.
- Not modelled: guaranteed stops, weekend/holiday gaps beyond history, Revolut re-quotes, min sizes. Revolut costs are placeholders in `analyst/cfd.py`.
- Sentiment is a lexicon over headlines: unvalidated, used only as veto/context. See `skills/trading-analyst/SKILL.md`.

Not financial advice. CFDs lose money for most retail accounts.
