"""Loss-limit guardrail. Rules live in code and persist in reports/guard_state.json.
It can only REDUCE or BLOCK risk, never raise it. Real-money risk is 0 until the paper record earns it."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date as Date
from pathlib import Path

import numpy as np

STATE = Path(__file__).resolve().parent.parent / "reports" / "guard_state.json"

RISK_CAP = 0.05            # never more than 5% of equity at risk per trade
DAILY_LOSS = 0.04          # lose 4% in a day -> no more trades that day
WEEKLY_LOSS = 0.08         # lose 8% in an ISO week -> no more trades that week
MAX_DRAWDOWN = 0.20        # 20% below peak -> HALT until a human runs `guard reset`
DD_HALF = 0.10             # >=10% below peak -> half risk
HIGH_IMPACT = {"Fed decision", "Fed", "Fed chair", "Inflation print", "Jobs report", "Gov shutdown", "Geopolitics"}
EVIDENCE_N, EVIDENCE_T = 100, 1.65


@dataclass
class Decision:
    allowed: bool
    risk: float
    reasons: list[str] = field(default_factory=list)


def _load() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"peak": None, "last_equity": None, "day": None, "day_start": None, "week": None, "week_start": None,
            "consec_losses": 0, "halted": False, "halt_reason": ""}


def _save(s: dict):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1))


def _roll(s: dict, equity: float, day: Date):
    iso = f"{day.isocalendar()[0]}-W{day.isocalendar()[1]:02d}"
    if s["peak"] is None:
        s["peak"] = equity
    s["peak"] = max(s["peak"], equity)
    if s["day"] != str(day):
        s["day"], s["day_start"] = str(day), equity
    if s["week"] != iso:
        s["week"], s["week_start"] = iso, equity
    if s["last_equity"] is None:
        s["last_equity"] = equity


def evidence_ok() -> tuple[bool, str]:
    """Real money only after >=100 settled paper calls with positive mean and t>1.65."""
    from . import journal
    c = journal._read("calls")
    c = c[c["settled"] == 1]
    n = len(c)
    if n < EVIDENCE_N:
        return False, f"paper record has {n}/{EVIDENCE_N} settled calls"
    x = c["net_bps"].astype(float)
    t = float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if x.std() > 0 else 0.0
    if x.mean() <= 0 or t < EVIDENCE_T:
        return False, f"paper edge not proven (avg {x.mean():+.1f} bps, t {t:.2f}, need >0 and t>{EVIDENCE_T})"
    return True, f"paper edge proven (avg {x.mean():+.1f} bps, t {t:.2f}, n {n})"


def check(equity: float, risk: float, day: Date, event_flags=(), require_evidence=True) -> Decision:
    s = _load(); _roll(s, equity, day)
    why: list[str] = []
    dd = 1 - equity / s["peak"]
    if dd >= MAX_DRAWDOWN and not s["halted"]:
        s["halted"], s["halt_reason"] = True, f"drawdown {dd:.0%} >= {MAX_DRAWDOWN:.0%}"
    _save(s)
    if s["halted"]:
        return Decision(False, 0.0, [f"HALTED: {s['halt_reason']} (human must run `guard reset`)"])
    day_loss, week_loss = 1 - equity / s["day_start"], 1 - equity / s["week_start"]
    if day_loss >= DAILY_LOSS:
        return Decision(False, 0.0, [f"daily loss {day_loss:.1%} >= {DAILY_LOSS:.0%}: done for today"])
    if week_loss >= WEEKLY_LOSS:
        return Decision(False, 0.0, [f"weekly loss {week_loss:.1%} >= {WEEKLY_LOSS:.0%}: done for the week"])
    hit = sorted(HIGH_IMPACT & set(event_flags))
    if hit:
        return Decision(False, 0.0, [f"high-impact event risk today: {', '.join(hit)}"])
    r = min(risk, RISK_CAP)
    if risk > RISK_CAP:
        why.append(f"risk capped {risk:.0%} -> {RISK_CAP:.0%}")
    mult = 1.0
    if s["consec_losses"] >= 5:
        mult = 0.25; why.append(f"{s['consec_losses']} losses in a row: risk x0.25")
    elif s["consec_losses"] >= 3:
        mult = 0.5; why.append(f"{s['consec_losses']} losses in a row: risk x0.5")
    if dd >= DD_HALF:
        mult = min(mult, 0.5); why.append(f"drawdown {dd:.0%}: risk x0.5")
    r *= mult
    budget = DAILY_LOSS - day_loss
    if r > budget:
        r = budget; why.append(f"trimmed to remaining daily budget {budget:.1%}")
    if require_evidence:
        ok, msg = evidence_ok()
        if not ok:
            return Decision(False, 0.0, [f"PAPER ONLY: {msg}"] + why)
        why.append(msg)
    return Decision(r > 0, max(r, 0.0), why)


def record_close(equity_after: float, day: Date):
    s = _load(); _roll(s, equity_after, day)
    if equity_after < s["last_equity"]:
        s["consec_losses"] += 1
    elif equity_after > s["last_equity"]:
        s["consec_losses"] = 0
    s["last_equity"] = equity_after
    s["peak"] = max(s["peak"], equity_after)
    if 1 - equity_after / s["peak"] >= MAX_DRAWDOWN:
        s["halted"], s["halt_reason"] = True, f"drawdown >= {MAX_DRAWDOWN:.0%}"
    _save(s)
    return s


def reset():
    if STATE.exists():
        STATE.unlink()


def status() -> dict:
    return _load()
