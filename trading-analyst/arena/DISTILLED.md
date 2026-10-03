# What was distilled from the four reference sources (and what was not)

| Source | Retrieved | Kept | Rejected |
|---|---|---|---|
| Oft3r/agentic-trading-desk | full README | AI fetches / scripts compute / human approves; hard mandate limits; order simulation before placing; circuit breaker (halt after -4% day); news = context only, from a whitelisted source (prompt-injection defence); 3-pillar scorecard idea (trend, momentum, cross-asset macro ratios RSP/SPY, HYG/LQD, IWM/SPY, XLY/XLP) | No backtest by its own admission; prose rules unenforced (their own hook exists because the model broke them) |
| agensi.io trading skills | listing page only (289 skills, mostly paid, anonymous creators) | Ideas: breakout ranking (Minervini/CAN SLIM), EV calculator, multi-timeframe scanner | Installing unvetted paid skills (supply-chain risk, not free) |
| valuefocus.io review | page is JS-rendered; ~370 chars of stub | nothing | cannot be distilled |
| snyk.io top-8 finance skills | article text | Monte Carlo, DCF/scenario thinking, time-series stats, backtest hygiene; warning about malicious/unvetted skills | Third-party skills themselves |

Lessons applied: enforce rules in code not prose; judge recomputes every trade from raw prices; a backtest without
out-of-sample + multiple-testing correction is not evidence; macro cross-asset ratios are candidate features for the arena.
