"""Seedable dice roller.

A thin wrapper over ``random.Random`` that accepts dice specs like
``"1d6"`` or ``"2d8+1"``. Every Dice instance is independent so that
each simulation run can be reproduced from its seed alone.
"""

from __future__ import annotations
import random
import re

_SPEC = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


class Dice:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def d(self, sides: int) -> int:
        return self.rng.randint(1, sides)

    def roll(self, spec: str) -> int:
        m = _SPEC.match(spec)
        if not m:
            raise ValueError(f"bad dice spec: {spec!r}")
        n = int(m.group(1) or 1)
        sides = int(m.group(2))
        mod_str = (m.group(3) or "").replace(" ", "")
        mod = int(mod_str) if mod_str else 0
        return sum(self.d(sides) for _ in range(n)) + mod
