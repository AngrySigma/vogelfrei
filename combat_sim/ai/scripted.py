"""ScriptedAI — the AI that asks the player (or a test).

Used for two purposes:

  1. Interactive play. The UI builds a queue of Actions as the user
     clicks through menus / map squares, then ``decide`` returns each
     in turn when the combat layer asks the AI what the creature wants
     to do.

  2. Reproducible scenario tests. A test can hand-script "this PC
     moves to (3, 5) on round 1, attacks on round 2" without writing
     a bespoke strategy.

This is intentionally minimal: it neither validates actions nor reacts
to triggers (it Passes on counterattack opportunities by default).
Validation is the combat layer's job — ``validate_move`` already gates
illegal MoveActions. Reactive intelligence is the UI's job (the player
can be asked "do you want to counterattack?" via a separate prompt).
"""

from __future__ import annotations
from collections import deque
from typing import Iterable, Optional

from ..actions import Action, PassAction, CounterAttackAction
from .base import AI


class ScriptedAI(AI):
    def __init__(self, actions: Optional[Iterable[Action]] = None,
                 *, counter_when_offered: bool = False) -> None:
        self.queue: deque[Action] = deque(actions or [])
        self.counter_when_offered = counter_when_offered

    def enqueue(self, action: Action) -> None:
        """Add an action to the back of the queue. The combat layer
        will pop it on the next ``decide`` call."""
        self.queue.append(action)

    def decide(self, actor, ctx, *, trigger=None, source=None):
        if trigger is not None:
            # Reactive trigger — typically a Counterattack offer.
            # Default policy: never counter unless explicitly enabled.
            if self.counter_when_offered:
                return CounterAttackAction()
            return PassAction()
        if not self.queue:
            return PassAction()
        return self.queue.popleft()
