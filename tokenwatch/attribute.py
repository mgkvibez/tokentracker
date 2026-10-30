"""Who to blame for the tokens.

A model call cannot be split exactly: one request may read three files and
invoke a skill. We split that call's tokens evenly across everything it touched
and put calls that touch nothing into an explicit `unattributed` bucket, so the
percentages always add up to 100% of what was actually spent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .pricing import cost, load_prices
from .records import Event
from .usage import Usage

UNATTRIBUTED = "(unattributed)"


@dataclass
class Analysis:
    total: Usage = field(default_factory=Usage)
    cost_usd: Optional[float] = None
    unpriced_models: List[str] = field(default_factory=list)
    sessions: Dict[str, Usage] = field(default_factory=dict)
    session_cost: Dict[str, float] = field(default_factory=dict)
    buckets: Dict[str, Usage] = field(default_factory=dict)
    bucket_cost: Dict[str, float] = field(default_factory=dict)
    events: int = 0

    def share(self, name: str) -> float:
        """Percent of total tokens attributed to one bucket."""
        if not self.total.total:
            return 0.0
        return 100.0 * self.buckets.get(name, Usage()).total / self.total.total

    def top(self, n: int = 5) -> List[Tuple[str, Usage]]:
        return sorted(self.buckets.items(), key=lambda kv: -kv[1].total)[:n]


def _split(usage: Usage, parts: int) -> List[Usage]:
    """Divide a call evenly, giving the remainder to the first part."""
    if parts <= 0:
        return []
    fields = ("input", "output", "cache_read", "cache_write")
    shares = []
    for i in range(parts):
        share = {}
        for f in fields:
            value = getattr(usage, f)
            base, rem = divmod(value, parts)
            share[f] = base + (rem if i == 0 else 0)
        shares.append(Usage(**share))
    return shares


def analyse(events: List[Event], prices_path: Optional[str] = None) -> Analysis:
    """Aggregate events into per-session and per-target totals."""
    prices = load_prices(prices_path)
    result = Analysis()
    unpriced = set()

    for event in events:
        result.events += 1
        result.total = result.total + event.usage
        result.sessions[event.session] = result.sessions.get(event.session, Usage()) + event.usage

        call_cost = cost(event.usage, event.model, prices)
        if call_cost is None and event.model:
            unpriced.add(event.model)
        elif call_cost is not None:
            result.cost_usd = (result.cost_usd or 0.0) + call_cost
            result.session_cost[event.session] = result.session_cost.get(event.session, 0.0) + call_cost

        targets = event.targets or [UNATTRIBUTED]
        for target, share in zip(targets, _split(event.usage, len(targets))):
            result.buckets[target] = result.buckets.get(target, Usage()) + share
            if call_cost is not None:
                result.bucket_cost[target] = result.bucket_cost.get(target, 0.0) + call_cost / len(targets)

    result.unpriced_models = sorted(unpriced)
    return result
