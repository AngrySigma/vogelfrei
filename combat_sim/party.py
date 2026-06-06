"""Party + Engagement.

A Party is a named list of Creatures — the unit at which initiative,
morale, and victory conditions are checked. Members never switch
parties during a fight.

Engagement is the **positioning hook** plus the candidate-query layer
the AI consults. It can run in two modes:

  * No battlefield (current default for existing scenarios): every
    conscious enemy is in melee/ranged range; distance is always 1.
    Backwards-compatible with all pre-positioning code paths.

  * With a battlefield: candidates are filtered by Chebyshev distance.
    Melee range = ≤1 square. Ranged range = ≤ ``weapon.range_long``
    converted from feet via ``FT_PER_SQUARE``.

The old ``target_of`` and ``outnumbering_against`` methods are kept as
thin shims over the new queries so callers in combat.py don't break
during the transition.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .geometry import chebyshev, FT_PER_SQUARE

if TYPE_CHECKING:
    from .creatures import Creature
    from .battlefield import Battlefield
    from .items import Weapon


@dataclass
class Party:
    name: str
    members: list["Creature"]

    @property
    def combat_capable(self) -> list["Creature"]:
        return [m for m in self.members if m.is_combat_capable]

    @property
    def is_defeated(self) -> bool:
        return not self.combat_capable

    def total_wounds_remaining(self) -> int:
        return sum(max(0, m.wounds) for m in self.members)


class Engagement:
    """Tracks who can target whom, optionally informed by a battlefield."""

    def __init__(self, party_a: Party, party_b: Party, *,
                 battlefield: Optional["Battlefield"] = None) -> None:
        self.a = party_a
        self.b = party_b
        self.battlefield = battlefield

    # -- party membership helpers --------------------------------------

    def _own_and_enemy(self, creature) -> tuple[Party, Party]:
        if creature in self.a.members:
            return self.a, self.b
        return self.b, self.a

    def enemies_of(self, creature) -> list["Creature"]:
        _, enemy = self._own_and_enemy(creature)
        return enemy.combat_capable

    # -- candidate queries ---------------------------------------------

    def _paired_target(self, creature) -> Optional["Creature"]:
        """Legacy index-based pairing used when no battlefield is present.
        Member i of party A targets member i of party B (wrapping if the
        sides have different sizes — that's how outnumbering used to
        kick in)."""
        own, enemy = self._own_and_enemy(creature)
        enemies = enemy.combat_capable
        if not enemies:
            return None
        own_capable = own.combat_capable
        if creature not in own_capable:
            return None
        idx = own_capable.index(creature)
        return enemies[idx % len(enemies)]

    def melee_candidates(self, creature) -> list["Creature"]:
        enemies = self.enemies_of(creature)
        if self.battlefield is None or creature.position is None:
            # Without a battlefield, target selection is the legacy
            # index-based pairing. Return a singleton list so AI helpers
            # that ``pick first`` behave as before.
            paired = self._paired_target(creature)
            return [paired] if paired is not None else []
        return [
            e for e in enemies
            if e.position is not None
            and chebyshev(creature.position, e.position) <= 1
        ]

    def ranged_candidates(self, creature, weapon: "Weapon") \
            -> list["Creature"]:
        enemies = self.enemies_of(creature)
        if self.battlefield is None or creature.position is None:
            paired = self._paired_target(creature)
            return [paired] if paired is not None else []
        max_squares = weapon.range_long // FT_PER_SQUARE
        return [
            e for e in enemies
            if e.position is not None
            and chebyshev(creature.position, e.position) <= max_squares
        ]

    def nearest_enemy(self, creature) -> Optional["Creature"]:
        enemies = self.enemies_of(creature)
        if not enemies:
            return None
        if self.battlefield is None or creature.position is None:
            return self._paired_target(creature)
        ordered = sorted(
            enemies,
            key=lambda e: (chebyshev(creature.position, e.position)
                           if e.position is not None else 10**9),
        )
        return ordered[0]

    def distance_to(self, c1, c2) -> int:
        if self.battlefield is None or c1.position is None or c2.position is None:
            return 1
        return chebyshev(c1.position, c2.position)

    def in_melee_with(self, target) -> list["Creature"]:
        """Enemies of ``target`` currently engaging it for outnumbering
        purposes.

        With a battlefield: anyone within 1 square.
        Without: anyone whose paired target is this creature — preserves
        the legacy "extras pile on" outnumbering count.
        """
        own, _ = self._own_and_enemy(target)
        other = self.b if own is self.a else self.a
        attackers = other.combat_capable
        if self.battlefield is None or target.position is None:
            return [a for a in attackers
                    if self._paired_target(a) is target]
        return [
            a for a in attackers
            if a.position is not None
            and chebyshev(a.position, target.position) <= 1
        ]

    # -- back-compat shims used by combat.py ---------------------------

    def target_of(self, attacker) -> Optional["Creature"]:
        """Used by combat._execute as a fallback when an action's target
        has died mid-multi-attack. Picks nearest enemy."""
        return self.nearest_enemy(attacker)

    def outnumbering_against(self, target) -> int:
        return len(self.in_melee_with(target))
