"""Pure lookup functions and shared value types.

These have no side effects and no state. They are the *only* place that
the underlying number tables from the rulebook should be expressed, so
that a future rules tweak touches one location.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class HitModifier:
    """A single named contribution to a to-hit roll.

    Used by the modifier-collection pipeline in combat.py so that every
    factor (WS, length, conditions, outnumbering, ...) is uniformly a
    HitModifier rather than an opaque integer baked into the attack
    formula.
    """
    source: str
    value: int


def ability_modifier(score: int) -> int:
    """Map a 3-18 ability score to its modifier per Ability Scores.md."""
    if score <= 3:
        return -3
    if score <= 5:
        return -2
    if score <= 8:
        return -1
    if score <= 12:
        return 0
    if score <= 15:
        return +1
    if score <= 17:
        return +2
    return +3


def length_to_hit_mod(attacker_length: int, defender_length: int,
                     *, unarmed: bool = False) -> int:
    """Per Combat Actions.md (post weapon-length flip).

    Shorter weapon = -2 to hit, equal/longer = 0, unarmed = -4.
    Longer-weapon advantage is expressed via Counterattack, not via a
    direct to-hit bonus.
    """
    if unarmed:
        return -4
    if attacker_length < defender_length:
        return -2
    return 0


def outnumber_bonus(extra_attackers: int) -> int:
    """Outnumbering bonus for melee — 2-on-1 = +2, 3+-on-1 = +4."""
    if extra_attackers <= 0:
        return 0
    if extra_attackers == 1:
        return 2
    return 4
