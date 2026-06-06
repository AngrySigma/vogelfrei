"""DuellistAI — like Berserker, but counterattacks when triggered."""

from __future__ import annotations

from ..actions import AttackAction, CounterAttackAction
from .base import AI
from ._helpers import melee_target_or_move


class DuellistAI(AI):
    """Same proactive logic as Berserker; counterattacks reactively
    whenever the rules permit. The combat layer checks training and
    weapon-length eligibility before invoking this — the AI just says
    'yes, I want to' by returning CounterAttackAction."""

    def decide(self, actor, ctx, *, trigger=None, source=None):
        if trigger is not None and isinstance(trigger, AttackAction):
            return CounterAttackAction()
        return melee_target_or_move(actor, ctx)
