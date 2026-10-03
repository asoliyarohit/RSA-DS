---
name: trading-analyst
description: Daily CFD analyst for a small Revolut account. Runs the deterministic briefing (quant gate + free news/sentiment), then writes the narrative for the open day-trade and the near-close trade sold at next open. Use when asked for today's trade, a market briefing, or position sizing.
---
# Trading analyst (CFD, Revolut)

Principle: scripts compute, Claude explains, the human executes. Never place orders.

## Workflow
1. `cd trading-analyst && python -m analyst brief --equity <balance> --risk <0.02-0.30> --broker revolut`
2. Read the headlines and flags. Write a narrative with: (a) what moved the market overnight and why,
   (b) the regime (VIX level/change, trend), (c) the trade or "NO TRADE", (d) what invalidates it.
3. **Near-close trade (CLOSE)** - only if the quant gate fires. Entry ~15:55 ET, exit = SELL at next open.
   News may veto (event flags, VIX spike >20% d/d, binary event tonight) but may NEVER create the trade.
4. **Open trade (OPEN)** - the backtest found NO edge for gap setups (out-of-sample t<1). Treat any open trade
   as discretionary: needs a written thesis from today's news, hard stop, max 1% account risk, logged in
   `reports/journal.csv` so it can be forward-tested. If no thesis is convincing, say NO TRADE.
5. Always state: notional, margin, stress loss in $, and that overnight gaps can exceed the stress loss.

## Guardrail (enforced in code, not by judgment)
Before ANY sizing, run `python -m analyst guard check --equity <bal> --risk <r>`. If it says BLOCKED or risk 0, there is no trade; do not argue
with it, do not re-run with different numbers. After each closed trade run `guard record --equity-after <bal>`.

## Non-negotiables
- Never promise the 1k -> 100k outcome; quote the solver's probability (`python -m analyst solve`).
- Never raise risk after a loss to "get it back"; the drawdown throttle halves/quarters risk at -15%/-30%.
- Revolut spread/fees/leverage in `analyst/cfd.py` PROFILES are placeholders - confirm in the app.
- Skip trading on days the user cannot monitor or on a held position through binary events.
