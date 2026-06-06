"""Shared helpers for melee-oriented AIs.

Kept module-private (``_helpers``) — strategies import from here, but
nothing outside the ai subpackage should depend on these.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..actions import (
    Action, AttackAction, MoveAction, MoveAndAttackAction, PassAction,
)

if TYPE_CHECKING:
    from ..creatures import Creature
    from ..combat import CombatContext


def melee_target_or_move(actor: "Creature", ctx: "CombatContext") -> Action:
    """Standard melee-AI decision tree:
      * if any enemy is in melee range, AttackAction on the first
      * else if an enemy is reachable in one round, MoveAndAttackAction
      * else MoveAction toward nearest
      * else PassAction

    Falls back to "attack the paired target" when there is no
    battlefield (Engagement.melee_candidates handles the collapse).
    """
    from ..targeting import enemies_in_melee_range, nearest_enemy
    from ..movement import walk_toward
    from ..geometry import chebyshev

    melee = enemies_in_melee_range(actor, ctx)
    if melee:
        return AttackAction(target=melee[0])

    target = nearest_enemy(actor, ctx)
    if target is None:
        return PassAction()

    bf = ctx.engagement.battlefield
    if bf is None or actor.position is None or target.position is None:
        # Without positioning, the engagement's candidate query already
        # collapsed to the paired target — fall through.
        return AttackAction(target=target)

    dest = walk_toward(actor, target.position,
                      actor.movement_squares, bf)
    if chebyshev(dest, target.position) <= 1:
        if dest == actor.position:
            return AttackAction(target=target)
        return MoveAndAttackAction(
            destination=dest,
            attack=AttackAction(target=target),
        )
    if dest == actor.position:
        return PassAction()
    return MoveAction(destination=dest)
