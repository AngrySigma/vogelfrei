"""Perception queries.

Pure functions used by both the AI strategies and (in the future) the
interactive UI. Everything here is read-only over the combat context.

The thin wrappers around Engagement methods exist so callers don't have
to know whether the system has a battlefield or not — the engagement
hides that distinction.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .actions import (
    Action,
    AttackAction,
    MoveAction,
    MoveAndAttackAction,
    FullDefenceAction,
    PassAction,
)
from .geometry import chebyshev

if TYPE_CHECKING:
    from .creatures import Creature
    from .combat import CombatContext
    from .items import Weapon


def enemies_of(actor: "Creature", ctx: "CombatContext") -> list["Creature"]:
    return ctx.engagement.enemies_of(actor)


def enemies_in_melee_range(actor: "Creature",
                          ctx: "CombatContext") -> list["Creature"]:
    return ctx.engagement.melee_candidates(actor)


def enemies_in_ranged_range(actor: "Creature", weapon: "Weapon",
                           ctx: "CombatContext") -> list["Creature"]:
    return ctx.engagement.ranged_candidates(actor, weapon)


def nearest_enemy(actor: "Creature",
                 ctx: "CombatContext") -> Optional["Creature"]:
    return ctx.engagement.nearest_enemy(actor)


def available_actions(actor: "Creature",
                     ctx: "CombatContext") -> list[Action]:
    """Enumerate every legal action ``actor`` could take right now.

    This is the UI's contract: feed it to a menu, let the player click.
    The AI is welcome to use it too, though most go straight to their
    preferred branch without enumerating.

    Layers, in display order:
      1. AttackAction for every melee-range enemy
      2. AttackAction for every ranged-range enemy (if weapon ranged + ready)
      3. MoveAndAttackAction for every enemy reachable within combat movement
      4. MoveAction toward and away from nearest enemy (capped — UI can
         expand to per-square if needed; this keeps the list short)
      5. FullDefenceAction (always available)
      6. PassAction (always available)
    """
    actions: list[Action] = []

    # 1. Melee attacks
    for e in enemies_in_melee_range(actor, ctx):
        actions.append(AttackAction(target=e))

    # 2. Ranged attacks (if weapon is ranged and currently usable)
    w = actor.weapon
    if w is not None and w.is_ranged and actor.can_use_weapon(w, ctx):
        for e in enemies_in_ranged_range(actor, w, ctx):
            actions.append(AttackAction(target=e, weapon=w))

    # 3. Move-and-attack against reachable enemies
    bf = ctx.engagement.battlefield
    if bf is not None and actor.position is not None:
        from .movement import walk_toward
        for e in enemies_of(actor, ctx):
            if e.position is None:
                continue
            dest = walk_toward(actor, e.position,
                              actor.movement_squares, bf)
            if (chebyshev(dest, e.position) <= 1
                    and dest != actor.position):
                actions.append(MoveAndAttackAction(
                    destination=dest,
                    attack=AttackAction(target=e),
                ))

        # 4. Pure-move toward / away from nearest
        nearest = nearest_enemy(actor, ctx)
        if nearest is not None and nearest.position is not None:
            toward = walk_toward(actor, nearest.position,
                                actor.movement_squares, bf)
            if toward != actor.position:
                actions.append(MoveAction(destination=toward))
            from .movement import can_retreat_to_distance
            safe = nearest.movement_squares + 1
            retreat = can_retreat_to_distance(actor, nearest,
                                              target_distance=safe,
                                              battlefield=bf)
            if retreat is not None and retreat != actor.position:
                actions.append(MoveAction(destination=retreat))

    # 5. Full Defence (always)
    actions.append(FullDefenceAction())

    # 6. Pass (always)
    actions.append(PassAction())

    return actions
