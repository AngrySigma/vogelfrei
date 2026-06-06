"""AI strategy interface.

A strategy is a stateless (or near-stateless) policy that converts a
creature's situation into an Action. Called both proactively (the
creature's own turn — ``trigger=None``) and reactively (e.g.
Counterattack opportunity — ``trigger`` set to the incoming Action and
``source`` set to the triggering creature).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..actions import Action

if TYPE_CHECKING:
    from ..creatures import Creature
    from ..combat import CombatContext


class AI(ABC):
    @abstractmethod
    def decide(self, actor: "Creature", ctx: "CombatContext", *,
               trigger: Action | None = None,
               source: "Creature | None" = None) -> Action:
        ...
