"""CautiousAI — Full Defence when battered, otherwise like Duellist."""

from __future__ import annotations

from ..actions import (
    AttackAction, CounterAttackAction, FullDefenceAction, PassAction,
)
from .base import AI
from ._helpers import melee_target_or_move


class CautiousAI(AI):
    """Switches to Full Defence when out of stamina and below half
    wounds. Otherwise behaves like Duellist."""

    def decide(self, actor, ctx, *, trigger=None, source=None):
        if trigger is not None:
            if actor.stamina() > 0 and isinstance(trigger, AttackAction):
                return CounterAttackAction()
            return PassAction()
        below_half = actor.wounds <= max(1, actor.wounds_max // 2)
        if actor.stamina() == 0 and below_half:
            return FullDefenceAction()
        return melee_target_or_move(actor, ctx)
