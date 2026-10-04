# quant_edge: report (deliverable required by arena/PROTOCOL.md rule 7)

**Deliverable:** `strategy.py` buys the 3 lowest-IBS of 12 equity index/sector ETFs at the close of the last NYSE trading day of each month and sells them at the next open. That is about 12 slots a year.
**Judge `--dev`:** VALID EDGE. 275 slots, +14.8 bps/slot, t=3.59, DSR=0.829 (N_TRIALS=90), 95% CI [6.5, 22.6] bps, win rate 63%, top-5 share of profit 23%, lookahead OK.
**Goal:** P(1k -> 100k in 5y) = **0%**. Best policy: 10% risk, median 1.55k after 5y, historical 2000-2022 1k -> 8.05k with 21.6% max DD.
The edge is real enough to pass the gate, but there are far too few bets to compound toward 100x at 5x leverage.

## Approach and pre-registered hypotheses
Research universe: 132 liquid US stocks across all sectors, including laggards and mid-caps (`universe.py`, fixed before testing), plus the 14 judge ETFs. Dev data only (<= 2022-12-31). Internal walk-forward: train 2000-2016, validate 2017-2022. Costs are the judge's model: stocks 16 bps round trip plus financing, ETFs 4 bps plus financing.
No volume is available in the judge's frames (OHLC only), so volume-shock signals were impossible.

| Round | Hypotheses | Trials counted | Result |
|---|---|---|---|
| 1 `hyp.py` | 13 cross-sectional rules (top 3/slot): overnight reversal of residual z-return, intraday-loser rebound, near-20d-low + IBS, ETF IBS dip, short winners overnight, overnight momentum; OPEN: idiosyncratic gap fade/follow both sides, ETF gap fade, intraday momentum | 13 | **All dead.** Stock train/valid nets were mostly -5 to -35 bps. O4 (follow gap-down short) was -35 bps train and +21 valid (sign flip = noise). |
| 2 `deciles.py` | gross return by decile x VIX regime for 5 features (stocks) | 30 | Classic daily reversal (IBS, range position, gap fade) is strong in 2000-2016 (gross up to 20-30 bps in the extreme decile) but decays to ~0-15 bps in 2017-2022. That is below the 16-18 bps stock round trip. |
| 3 `etf.py` | ETF IBS bucket x VIX; turn-of-month day codes -4..+5, overnight and intraday | 38 | ETF IBS dip does not hold up (high-VIX cells flip sign between periods). **TOM day -1 overnight: +15 bps gross train, +26 bps valid.** Other codes are inconsistent. |
| 4 `calendar_fx.py` | TOM-1 and pre-holiday, per ETF and stocks | 4 | TOM overnight is positive on every equity ETF in both periods (TLT is negative, which fits equity flows). Stocks have bigger gross (+13/+26) but costs kill train. Pre-holiday dies in valid. |
| 5 `tom.py` | A: TOM on SPY/QQQ/IWM; B: TOM on 12 equity ETFs, top 3 by lowest IBS | 2 | A: +10 bps, t=2.15 (DSR < 0.5). **B: +14.9 bps, t=3.59** (chosen). |
| | buffer for unlogged looks | 3 | |
| **Total N_TRIALS** | | **90** | |

## Rationale
Month-end and month-start flows (payroll, 401k and pension contributions, index and fund rebalancing) are scheduled in advance. The literature documents the effect: Ariel 1987, Lakonishok-Smidt 1988, McConnell-Xu 2008. Buying the ETFs that closed weakest on the day adds a liquidity-provision tilt. There are 2 rules and 0 fitted numeric parameters (top 3 is fixed by the judge). "Last trading day" comes from a rule-based NYSE holiday calendar, never from future index rows. It had 0 mismatches against realised dates from 2000 to 2022.

## Dev walk-forward (variant B, judge cost model)
| Period | Slots | Net bps/slot | t |
|---|---|---|---|
| Train 2000-2016 | 203 | 14.9 | 3.28 |
| Validate 2017-2022 | 71 | 14.6 | 1.58 |
| All dev (judge) | 275 | 14.8 | 3.59 |

Net bps by year: 2000 42, 01 15, 02 20, 03 29, 04 11, 05 37, 06 14, 07 -2, 08 40, 09 4, 10 47, 11 5, 12 25, 13 12, 14 -12, 15 -22, 16 -7, 17 22, 18 -13, 19 31, 20 -10, 21 46, 22 10. 17 of 23 years were positive.

## Known weaknesses
1. **Frequency.** 12 bets a year cannot reach 100x. P(goal) = 0 at every risk level. Nothing with higher frequency survived costs: the stock round trip (16 bps + financing) is larger than every daily stock edge in 2017-2022.
2. **Validation-period t is only 1.58.** The edge was flat to negative in 2014-2016, and the anomaly is well known, so it may keep decaying. The magnitude was stable (14.9 vs 14.6 bps), but the sample is small.
3. **Execution and selection risk.** It assumes fills at the official close (in practice ~15:55) and the 9:30 open. Month-end closes are crowded. The worst trade was -401 bps (an overnight gap with no stop). The 12-ETF set and IBS tilt were picked among 2 variants after seeing the TOM result in round 3, which DSR only partly corrects for. The stock research universe is survivorship-biased (5 delisted tickers had no data).
