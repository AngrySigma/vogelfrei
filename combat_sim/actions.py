"""Actions — pure data describing what a creature wants to do.

Separated from ai.py so that other modules (combat, targeting, the
future UI) can import action types without dragging in the strategy
hierarchy. Execution lives in combat._execute.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .creatures import Creature
    from .items import Weapon


class Action:
    """Marker base. Subclasses are pure data — no behaviour."""


@dataclass
class AttackAction(Action):
    target: "Creature"
    weapon: Optional["Weapon"] = None   # overrides actor.weapon if set


@dataclass
class CounterAttackAction(Action):
    """Reactive: target is filled in by the combat layer (the attacker)."""


@dataclass
class MultiAttackAction(Action):
    attacks: list[AttackAction] = field(default_factory=list)


@dataclass
class FullDefenceAction(Action):
    pass


@dataclass
class PassAction(Action):
    pass


@dataclass
class MoveAction(Action):
    """Pure move — no attack this round. Destination must be reachable
    within the actor's movement budget (the AI is expected to plan via
    movement.walk_toward / can_retreat_to_distance before emitting this)."""
    destination: tuple[int, int]


@dataclass
class MoveAndAttackAction(Action):
    """Move up to combat distance, then attack. Per Combat Actions.md
    a character may both move and attack in one round if the move is at
    combat speed (not running). The attack's target must be in melee
    range of the post-move position."""
    destination: tuple[int, int]
    attack: AttackAction
