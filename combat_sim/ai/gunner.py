"""GunnerAI — fires when loaded and in range. Stationary."""

from __future__ import annotations

from ..actions import AttackAction, PassAction
from .base import AI


class GunnerAI(AI):
    """Fires the equipped ranged weapon at the nearest in-range enemy.
    No kiting, no movement. Use KitingAI for the smart version."""

    def decide(self, actor, ctx, *, trigger=None, source=None):
        if trigger is not None:
            return PassAction()

        weapon = actor.weapon
        if not actor.can_use_weapon(weapon, ctx):
            return PassAction()  # still reloading

        from ..targeting import enemies_in_ranged_range
        candidates = enemies_in_ranged_range(actor, weapon, ctx)
        if not candidates:
            return PassAction()

        bf = ctx.engagement.battlefield
        if bf is not None and actor.position is not None:
            from ..geometry import chebyshev
            candidates = sorted(
                candidates,
                key=lambda c: (chebyshev(actor.position, c.position)
                              if c.position is not None else 10**9),
            )
        return AttackAction(target=candidates[0], weapon=weapon)
