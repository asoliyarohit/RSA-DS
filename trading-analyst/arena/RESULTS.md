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
