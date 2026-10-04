"""Daily briefing: quant gate + regime + news/sentiment -> a plan Claude turns into a narrative."""
from __future__ import annotations

from datetime import date

from . import data, features, news
from .cli import REPORTS, _train_test
from .strategies import CloseParams, _direction_close
from .signals import live


def brief(args):
    f_vix = data.load(data.VIX, refresh=True)["close"]
    vix, vix_chg = float(f_vix.iloc[-1]), float(f_vix.iloc[-1] / f_vix.iloc[-2] - 1)
    n = news.gather()
    lines = [f"# Daily briefing {date.today()}", "",
             f"**Regime:** VIX {vix:.1f} ({vix_chg:+.1%} d/d). News tilt: **{n['tilt']}** (lexicon net {n['net_score']:+d}, UNVALIDATED).",
             f"**Event risk flags:** {', '.join(n['event_flags']) or 'none detected'}", "", "## Headlines"]
    lines += [f"- [{i['score']:+d}] {i['title']} _({i['source']})_" for i in n["items"][:20]]
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"briefing_{date.today()}.md"
    out.write_text("\n".join(lines))
    print("\n".join(lines)); print("\n## Quant gate (validated setups only)")
    live(args)
    print("\nRULES: OPEN setup has NO validated edge -> discretionary only, max 1% risk, needs a written thesis from the headlines above.\n"
          "CLOSE setup needs the quant trigger; news may VETO (event flags / VIX spike) but never create a trade.\n"
          f"Saved headlines to {out}")
