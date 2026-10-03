"""Required-edge frontier under a leverage cap: P(reach 100x before falling to 10%) for iid trades N(edge, sigma^2).
Equity factor = 1 + L*r with L = 5 (cap), stop = sigma. Gaussian, no gaps/fat tails/overlap -> real results are WORSE."""
from __future__ import annotations

import numpy as np


def p_goal(edge_bps, trades_per_year, years, sigma=0.01, L=5.0, target=100.0, ruin=0.10, paths=3000, seed=3):
    rng = np.random.default_rng(seed)
    n = int(round(trades_per_year * years))
    e = np.ones(paths); done = np.zeros(paths, bool); hit = np.zeros(paths, bool)
    for _ in range(n):
        r = rng.normal(edge_bps / 1e4, sigma, paths)
        e = np.where(done, e, np.maximum(e * (1 + L * r), 0.0))
        h = (~done) & (e >= target); hit |= h; done |= h | (e <= ruin)
    return float(hit.mean())


def required_edge(trades_per_year, years, p=0.5, **kw):
    lo, hi = 0.0, 3000.0
    for _ in range(11):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if p_goal(mid, trades_per_year, years, **kw) < p else (lo, mid)
    return round(hi, 1)


if __name__ == "__main__":
    print("net bps/trade needed for P(100x) >= 50%  (5x cap, sigma 1%)")
    print("trades/yr |    3y     5y    10y")
    for N in (10, 50, 250, 1000):
        print(f"{N:>9} | " + "  ".join(f"{required_edge(N, y):>6}" for y in (3, 5, 10)))
