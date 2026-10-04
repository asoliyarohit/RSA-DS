"""CFD economics: spread, slippage, overnight financing, leverage cap and risk-based sizing.

All returns are expressed per unit of NOTIONAL. Equity impact = notional/equity * return,
which is how leverage multiplies both reward and risk.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CFDSpec:
    spread_bps: float = 1.5      # round-trip quoted spread (US500 ~0.5pt on ~5000 = 1bp)
    slippage_bps: float = 1.0    # per side, on top of spread
    leverage: float = 20.0       # ESMA retail index cap 30:1 (20:1 on majors indices varies); pros up to 100+
    benchmark: float = 0.04      # annual cash rate
    markup: float = 0.025        # broker financing markup (long pays bench+markup, short earns bench-markup)
    commission_bps: float = 0.0  # per side, % of notional (Revolut equity CFDs: 0.25% = 25 bps, min $1)

    def round_trip_cost(self) -> float:
        return (self.spread_bps + 2 * self.slippage_bps + 2 * self.commission_bps) / 1e4

    def financing(self, direction: np.ndarray, nights: np.ndarray) -> np.ndarray:
        """Return contribution (negative = cost) for holding `nights` calendar nights."""
        long_rate = -(self.benchmark + self.markup)
        short_rate = self.benchmark - self.markup
        rate = np.where(direction > 0, long_rate, short_rate)
        return rate * nights / 365.0


def equity_factor(ret, stop_pct, mask, risk_pct, leverage):
    """Equity multiplier for one time slot holding up to k concurrent trades.

    ret, stop_pct, mask: arrays [..., k]. Risk budget is split across active trades.
    Notional per trade = min(risk/stop, leverage)/n_active, in units of equity.
    Result is clipped at 0 (negative-balance protection).
    """
    n = np.maximum(mask.sum(axis=-1, keepdims=True), 1)
    risk_pct = np.asarray(risk_pct, dtype=float)
    if risk_pct.ndim:
        risk_pct = risk_pct[..., None]
    notional = np.minimum(risk_pct / np.maximum(stop_pct, 1e-6), leverage) / n
    pnl = (notional * ret * mask).sum(axis=-1)
    return np.maximum(1.0 + pnl, 0.0)


# Broker profiles. Revolut figures are PLACEHOLDERS (user confirmed 5x leverage available);
# open the Revolut app, check the live spread / overnight fee / min size for US500 & US100 and edit here.
PROFILES = {
    "default": CFDSpec(),
    "revolut": CFDSpec(spread_bps=2.0, slippage_bps=1.0, leverage=5.0, benchmark=0.04, markup=0.03),
    # Verified in Revolut's CFD ex-ante costs report (cdn.revolut.com/legal/terms/RSEUAB-ex-ante-costs-report-CFD-v1.0.pdf):
    # equity CFD fee 0.25% per side (min $1), other CFDs 0; leverage 1:5 stocks, 1:20 major indices (S&P500, NASDAQ100), 1:2 crypto.
    "revolut_index": CFDSpec(spread_bps=2.0, slippage_bps=1.0, leverage=20.0, benchmark=0.04, markup=0.03),
    "revolut_stock": CFDSpec(spread_bps=10.0, slippage_bps=3.0, leverage=5.0, benchmark=0.04, markup=0.03, commission_bps=25.0),
}
