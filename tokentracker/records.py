"""One model call, with whatever we could learn about what it was spent on."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .usage import Usage


@dataclass
class Event:
    """A single model call parsed from a harness log."""

    ts: str = ""
    session: str = ""
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    files: List[str] = field(default_factory=list)
    skill: str = ""
    source: str = ""

    @property
    def targets(self) -> List[str]:
        """Everything this call can be blamed on, deduplicated, order preserved."""
        out: List[str] = []
        for item in list(self.files) + ([f"skill:{self.skill}"] if self.skill else []):
            if item not in out:
                out.append(item)
        return out
