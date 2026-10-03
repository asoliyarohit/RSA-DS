# Arena results (sealed holdout 2023-01-01 -> 2026-10, run once per frozen strategy)

Setting: CFDs, max 5x leverage, OPEN day trade + CLOSE->next-open overnight only, free data, one cost model (judge recomputes all fills).

| Competitor | Idea | Dev (<=2022) t / DSR | Holdout edge/slot | Holdout t | Holdout 95% CI (bps) | Holdout DSR | Best 5y policy, 1k ->(median) | P(100k) |
|---|---|---|---|---|---|---|---|---|
| quant_edge | month-end overnight, 3 weakest-close equity ETFs | 3.59 / 0.83 | -15.6 bps | -1.91 | [-31.9, +0.2] | 0.00 | ~830 | 0% |
| event_regime | day-2 continuation after volume-confirmed >=2 ATR gap, VIX<30 | 4.41 / 0.99 | +8.6 bps | 0.42 | [-31, +50] | 0.04 | ~940 | 0% |
| ml_cross | pooled ridge cross-section, CLOSE, stocks | 4.36 / 0.996 | +1.6 bps | 0.06 | [-53, +57] | 0.03 | ~990 | 0% |
| baseline (QQQ/SPY IBS dip) | prior finding | 1.72 / 0.40 | not run | | | | | |

Verdict: NO setup validated. All three passed the dev gate and all three failed out of sample. Integrity: judge and analyst/ untouched
by every competitor; lookahead perturbation test passed; each holdout run once. Remaining caveats: stock universes are current survivors,
costs for stock CFDs are assumed, closes stand in for 15:55 fills, and dev-stage selection choices made after seeing results are not covered by DSR.

What this says about the goal: published-style daily edges on liquid US CFDs are 0-15 bps per trade after costs and decay with time.
At 5x leverage and 10-50 independent bets a year, that compounds to roughly flat-to-+15%/yr, not 100x. Competitor-reported weaknesses
(edge decay after 2016, too few bets, crowded closes, no overnight stop) were confirmed by the holdout.

Reproduce: cd trading-analyst && python -m arena.judge arena/<name>/strategy.py --final

## Addendum: red-team corrections (council, verified against Revolut's own CFD cost report)
- **Judge leak fixed.** A strategy hiding future info in `score` (trade selection) or `stop_pct` (sizing) passed as VALID (t=38).
  The perturbation test now compares score and stop_pct too; regression test added. The three competitors did not use this leak
  (all failed the holdout), but any earlier "VALID" dev verdict from the judge is now suspect only if it relied on score/stop.
- **Costs were too low for single stocks/ETFs.** Revolut equity CFDs charge 0.25%/side (min $1) = ~50 bps round trip before spread. The judge and
  universe stock profile now include 25 bps/side commission. Index CFDs (US500/US100) have no commission.
- **Leverage differs by instrument:** 1:5 stocks, 1:20 major indices (S&P 500, NASDAQ 100), 1:10 minor indices, 1:2 crypto. The 5x figure applies to shares only.
- Daily-bar proxies for the 9:30 open / 15:55 close are noisy (measured 6-19 bps close-vs-15:55 error): sub-15 bps edges are not resolvable on daily bars.

## Council experiment H1 (pre-registered): gamma-conditioned index open trade - KILLED on dev
SqueezeMetrics GEX (free). Follow gap when previous GEX<0; fade gap >=0.5 ATR when GEX>=0; N_TRIALS=2, no tuning.
Dev (<=2022): 1003 slots, -4.3 bps/slot, t -1.22, DSR 0.04 -> kill criterion hit (t<2). Holdout never run.
Remaining council candidates, untested: H2 (overnight dip-buy on more indices/gold/FX, needs real bid/ask), H3 (earnings-announcement premium on stock CFDs; the 50 bps commission makes it unlikely), H5 (pre-FOMC drift, 8 trades/yr, immaterial).

## Round 2 (user scope: indices, commodities, stocks only; long/short; judge with per-instrument leverage/costs). None passed dev; no holdout run.
| Agent | Lane | Dev avg bps/slot | t | DSR | slots/yr | Required bps (50% x 100x in 10y) | Closeness | N_TRIALS |
|---|---|---|---|---|---|---|---|---|
| macro_ls (sonnet) | 7 index ETFs, ridge, OPEN+CLOSE | +1.1 | 0.32 | 0.08 | 76 | 41 | 0.03 | 14 |
| commodity_ls (opus) | GLD/Brent/futures trend, OPEN only | -2.4 | -0.95 | 0.005 | 252 | 35 | -0.07 | 11 |
| trend_crisis (fable) | indices+GLD, stacked ridge, CLOSE | +6.0 | 1.75 | 0.20 | 106 | 163 | 0.04 | 122 |
Findings: (1) 'direction is irrelevant / shorts earn in down markets' is NOT supported: shorts roughly break even in slow bears, miss fast crashes
(2020 Q1 the model was long: -65 bps/slot) and bleed in bull years. (2) Naive daily-capture trend-following loses net in every class (gross ~2-12 bps vs 4-66 bps costs).
(3) Data traps found: Yahoo futures roll gaps (a CFD never receives them), stale opens on metals, WTI -$37 print, same-day VIX leak (IC 0.21 -> 0.05 once lagged), foreign-index ETFs priced as 20x CFDs.
(4) Judge fixes this round: per-instrument leverage tiers, non-positive-price guard.

## Intraday tests (user chose option 2): free 60m (730 days) + 5m (60 days) bars; 4 pre-registered trials (analyst/intraday.py)
- T1 Gao FOLLOW (first-hour direction -> last half-hour), SPY/QQQ/DIA/GLD, 721 days: -5.0 bps/day net (t -9.1); indices only -4.0. Gross ~ -0.3 bps.
- T2 Gao FADE: -4.5 bps/day net (t -8.1). Gross ~ +0.3 bps. => the first-hour -> last-half-hour link is ZERO in 2023-26 (resolution +/-1.4 bps).
- T3 ORB breakout (5m, 60 days only): -10.3 bps/day net (t -2.95). Gross ~ -5.5 bps (breakouts failed). The mirror (fade the break) was NOT pre-registered; its gross would be ~+5.5 bps vs ~4.8 bps cost, i.e. ~0 net, so it is not pursued.
- The archive (data/intraday/) is committed so 5m history keeps growing past the 60-day free limit: `python -m analyst intraday call` once a day.
