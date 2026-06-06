"""KitingAI — the smart ranged AI.

Lookahead: compute the threat's reach next round and prefer to stand
just outside it. Will retreat when threatened, fire when safe, fire when
cornered, and gracefully fall to PassAction when neither is possible.
"""

from __future__ import annotations

from ..actions import AttackAction, MoveAction, PassAction
from .base import AI


class KitingAI(AI):
    """Ranged strategy with lookahead retreat:

      1. If at safe distance (> threat.movement_squares squares away)
         AND in firing range — fire.
      2. If too close — try to retreat to a square that puts us at safe
         distance. If successful, MoveAction.
      3. Cornered (no retreat square exists): fire if in range, else Pass.
      4. Safe but out of range (large map, weak weapon): hold and Pass.

    "Safe" is defined as ``threat.movement_squares + 1`` squares — far
    enough that the threat cannot reach melee on its next round even if
    it spends its entire movement budget.
    """

    def decide(self, actor, ctx, *, trigger=None, source=None):
        if trigger is not None:
            return PassAction()

        weapon = actor.weapon
        if not actor.can_use_weapon(weapon, ctx):
            return PassAction()

        bf = ctx.engagement.battlefield
        if bf is None:
            # No positioning — degenerate to "fire if loaded".
            from ..targeting import enemies_in_ranged_range
            cands = enemies_in_ranged_range(actor, weapon, ctx)
            if cands:
                return AttackAction(target=cands[0], weapon=weapon)
            return PassAction()

        from ..targeting import (
            enemies_of, enemies_in_ranged_range,
        )
        from ..movement import can_retreat_to_distance

        threats = enemies_of(actor, ctx)
        if not threats:
            return PassAction()

        nearest = min(threats,
                     key=lambda c: ctx.engagement.distance_to(actor, c))
        safe_distance = nearest.movement_squares + 1
        in_ranged = nearest in enemies_in_ranged_range(actor, weapon, ctx)
        safe_now = ctx.engagement.distance_to(actor, nearest) >= safe_distance

        # 1. Safe + in range → fire.
        if safe_now and in_ranged:
            return AttackAction(target=nearest, weapon=weapon)

        # 2. Too close → try to retreat.
        if not safe_now:
            dest = can_retreat_to_distance(actor, nearest,
                                           target_distance=safe_distance,
                                           battlefield=bf)
            if dest is not None:
                return MoveAction(destination=dest)
            # 3. Cornered: fire if we can, else pass.
            if in_ranged:
                return AttackAction(target=nearest, weapon=weapon)
            return PassAction()

        # 4. Safe but out of range — hold position.
        return PassAction()
