# Goal maths: what 1k -> 100k requires (verified by two independent runs: council agent + analyst/frontier.py)

Model: iid trades N(edge, sigma=1%), 5x leverage cap, stop = sigma, success = reach 100x before dropping to 10%. Gaussian, no gaps/fat tails: reality is WORSE.
Net bps per trade needed for P(100x) >= 50% (`python -m analyst.frontier`; 1000/yr 10y cell is resolution-limited):

| trades/yr | 3y | 5y | 10y |
|---|---|---|---|
| 10 | 335 | 196 | 97 |
| 50 | 64 | 40 | 21 |
| 250 | 15 | 10 | 6 |
| 1000 | 6 | 4 | 4 |

- Bold play (use the full 5x cap every trade) maximises P(goal); at a 5x cap Kelly and bold coincide because full Kelly is >5x in every realistic cell.
- The biggest lever is the number of truly independent trades per year (requirement ~ 1/N), then net edge, then volatility.
- Best validated edge so far: none survives the holdout. Best measured candidate ~9 bps at ~50 trades/yr -> P(100x in 10y) ~ 0.5%.
- Gate before any real money (also enforced by `analyst/guard.py`): >=200 settled out-of-sample trades, net edge >= 15 bps with t >= 3, >=100 independent trades/yr,
  net Sharpe >= 1.5. Below that: paper only.
