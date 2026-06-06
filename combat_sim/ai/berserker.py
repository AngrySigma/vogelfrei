"""BerserkerAI — closes to melee and swings, never counterattacks."""

from __future__ import annotations

from ..actions import (
    AttackAction, MultiAttackAction, PassAction,
)
from .base import AI
from ._helpers import melee_target_or_move


class BerserkerAI(AI):
    """Closes to melee and swings. Monster multi-attacks fan out into
    one AttackAction per natural weapon when a melee target exists."""

    def decide(self, actor, ctx, *, trigger=None, source=None):
        if trigger is not None:
            return PassAction()

        # Monster multi-attack: only relevant if we have a melee candidate.
        from ..targeting import enemies_in_melee_range
        nat = getattr(actor, "natural_attacks", None)
        if nat:
            melee = enemies_in_melee_range(actor, ctx)
            if melee:
                target = melee[0]
                return MultiAttackAction(
                    attacks=[AttackAction(target=target, weapon=w) for w in nat]
                )
            # No melee target — fall through to close distance.

        return melee_target_or_move(actor, ctx)
