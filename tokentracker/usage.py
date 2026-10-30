"""Token usage arithmetic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Usage:
    """Token counts for one model call."""

    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input=self.input + other.input,
            output=self.output + other.output,
            cache_read=self.cache_read + other.cache_read,
            cache_write=self.cache_write + other.cache_write,
        )

    @property
    def total(self) -> int:
        """All tokens billed or billed-at-a-discount for this call."""
        return self.input + self.output + self.cache_read + self.cache_write

    @property
    def context_tokens(self) -> int:
        """Tokens that occupied context: everything sent plus everything generated."""
        return self.input + self.cache_read + self.cache_write + self.output
