# ARENA PROTOCOL (binding for every competitor)

**Objective:** the setup with the highest honest probability of taking a 1,000 account to 100,000 as fast as possible,
trading CFDs with **max 5x leverage**, two daily decisions only: **OPEN** (enter at open, exit same-day close, hard stop)
and **CLOSE** (enter ~15:55 ET close, sell at next open). Free data/tools only (yfinance, numpy/pandas/scipy/sklearn).

**You are judged, not believed.** The judge (`arena/judge.py`) recomputes every fill from raw prices, applies one cost model,
runs a perturbation lookahead test, and reports the Deflated Sharpe Ratio using YOUR declared `N_TRIALS`.
Valid edge = no lookahead AND t(slot) > 1.65 AND DSR > 0.5 AND bootstrap 95% CI lower bound > 0 AND >= 60 slots.

Rules
1. Development data ends **2022-12-31**. Never download, plot, print or reason from data after it. 2023+ is the sealed holdout; only the judge's `--final` touches it (the owner runs that). Peeking = disqualification.
2. Do not edit `arena/judge.py`, `analyst/*`. Work only in `arena/<your_name>/`.
3. `N_TRIALS` = honest count of every parameter set / feature / idea you evaluated on dev data (include dead ends). Under-reporting is cheating.
4. Inside dev, use your own walk-forward (e.g. fit <=2016, validate 2017-2022). Prefer few parameters, economic rationale, and robustness across tickers/years over a high in-sample score.
5. A negative result is a valid result. If nothing survives, say so with evidence; never p-hack to look good.
6. Contract and usage are in the docstring of `arena/judge.py`. Run `python -m arena.judge arena/<name>/strategy.py --dev` (takes a few minutes with many tickers; data is cached under data/).
7. Deliver: `arena/<name>/strategy.py` (frozen, deterministic), `arena/<name>/REPORT.md` (hypotheses, rationale, what failed, dev walk-forward table, final N_TRIALS, known weaknesses), then commit on your branch.
