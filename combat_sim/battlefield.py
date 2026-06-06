"""Battlefield: terrain + occupancy index.

Owns nothing about distance bands, AI, or movement budgets — those live
in geometry / movement / ai modules. The Battlefield's job is purely:

  1. What are the bounds and walls of this map?
  2. Which creature is at which square right now?

Position is canonically owned by the Creature (``creature.position``).
The battlefield maintains a derived inverse index keyed on (x, y) for
fast "who is at this square?" lookups during attack resolution and
targeting.

Movement happens through ``Creature.move_to(pos, battlefield)``, which
validates against this object then calls ``update_position`` to keep
the inverse index consistent.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .creatures import Creature


@dataclass
class Battlefield:
    width: int
    height: int
    blocked: set[tuple[int, int]] = field(default_factory=set)
    _occupancy: dict[tuple[int, int], "Creature"] = field(default_factory=dict)

    # -- queries --------------------------------------------------------

    def in_bounds(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_terrain_blocked(self, pos: tuple[int, int]) -> bool:
        return pos in self.blocked

    def is_occupied(self, pos: tuple[int, int]) -> bool:
        return pos in self._occupancy

    def occupant(self, pos: tuple[int, int]) -> Optional["Creature"]:
        return self._occupancy.get(pos)

    def is_passable(self, pos: tuple[int, int], *,
                   ignoring: Optional["Creature"] = None) -> bool:
        """A square is passable if it is in bounds, has no terrain, and
        is either empty or occupied only by ``ignoring`` (the moving
        creature itself).
        """
        if not self.in_bounds(pos):
            return False
        if self.is_terrain_blocked(pos):
            return False
        occ = self._occupancy.get(pos)
        if occ is None or occ is ignoring:
            return True
        return False

    # -- mutations ------------------------------------------------------

    def register(self, creature: "Creature", pos: tuple[int, int]) -> None:
        """Place a creature on the board for the first time. Updates
        both the inverse index and ``creature.position``."""
        self._occupancy[pos] = creature
        creature.position = pos

    def update_position(self, creature: "Creature",
                       new_pos: tuple[int, int]) -> None:
        """Move a creature from its current square to ``new_pos``.
        Called by ``Creature.move_to`` after validation."""
        if creature.position is not None:
            self._occupancy.pop(creature.position, None)
        self._occupancy[new_pos] = creature
        creature.position = new_pos

    def deregister(self, creature: "Creature") -> None:
        """Remove a creature from the board (e.g., on death/cleanup)."""
        if creature.position is not None:
            self._occupancy.pop(creature.position, None)
        creature.position = None
