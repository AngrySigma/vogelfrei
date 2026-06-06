"""HumanAI — the bridge from the combat layer to the Frontend.

A creature whose ``ai`` is ``HumanAI(frontend)`` defers every decision
to the player by calling into the frontend. This is the only AI that
talks to humans; everything else (BerserkerAI, KitingAI, ...) is
purely algorithmic.

The combat layer doesn't need to know any of this — ``HumanAI`` simply
implements ``AI.decide`` and returns whatever Action the frontend
emits.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..ai import AI
from ..actions import Action, AttackAction, PassAction
from ..targeting import available_actions

if TYPE_CHECKING:
    from ..creatures import Creature
    from ..combat import CombatContext
    from .frontend import Frontend


class HumanAI(AI):
    """An AI that asks a Frontend for every decision."""

    def __init__(self, frontend: "Frontend") -> None:
        self.frontend = frontend

    def decide(self, actor: "Creature", ctx: "CombatContext", *,
               trigger: Action | None = None,
               source: "Creature | None" = None) -> Action:
        if trigger is not None:
            # Reactive prompt — typically a Counterattack offer.
            # ``source`` is the attacker; an empty fallback to PassAction
            # makes the call safe if the frontend somehow returns None.
            if source is None:
                return PassAction()
            return self.frontend.prompt_reaction(actor, source, ctx)

        options = available_actions(actor, ctx)
        return self.frontend.prompt_action(actor, options, ctx)
