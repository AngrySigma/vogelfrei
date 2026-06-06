"""Tests for ScriptedAI.

These tests double as the integration smoke test for user-supplied
actions: the UI will inject MoveAction / AttackAction objects into a
ScriptedAI's queue, the combat layer pops them on the actor's turn,
and validate_move rejects illegal destinations.
"""

import pytest

from combat_sim.dice import Dice
from combat_sim.battlefield import Battlefield
from combat_sim.creatures import Character
from combat_sim.party import Party, Engagement
from combat_sim.combat import CombatContext, run_round
from combat_sim.actions import (
    MoveAction, AttackAction, PassAction,
)
from combat_sim.ai import ScriptedAI, DuellistAI
from combat_sim.items import SMALL, MEDIUM_2H


def make_pc(name, weapon=SMALL, ws=1, movement=8):
    return Character(
        name=name, wounds_max=8, stamina_max=2,
        ws=ws, weapon=weapon,
        ai=ScriptedAI(),
        movement_squares=movement,
    )


class TestScriptedAIQueue:
    def test_empty_queue_returns_pass(self):
        from combat_sim.dice import Dice
        pc = make_pc("P")
        # No setup needed for an empty-queue decide — ctx fields unused.
        ai = pc.ai
        # bypass ctx — decide doesn't read it when queue empty
        result = ai.decide(pc, None)
        assert isinstance(result, PassAction)

    def test_pops_queued_actions_in_order(self):
        pc = make_pc("P")
        a1 = MoveAction(destination=(1, 1))
        a2 = MoveAction(destination=(2, 2))
        pc.ai.enqueue(a1)
        pc.ai.enqueue(a2)
        assert pc.ai.decide(pc, None) is a1
        assert pc.ai.decide(pc, None) is a2
        # Queue empty -> Pass
        assert isinstance(pc.ai.decide(pc, None), PassAction)

    def test_trigger_returns_pass_by_default(self):
        """Reactive (counterattack) call returns Pass unless the AI is
        explicitly configured to counter."""
        pc = make_pc("P")
        # Even with queued actions, a trigger is a reactive call —
        # don't consume the queue.
        pc.ai.enqueue(MoveAction(destination=(1, 1)))
        from combat_sim.actions import AttackAction as AA
        result = pc.ai.decide(pc, None,
                              trigger=AA(target=pc, weapon=SMALL))
        assert isinstance(result, PassAction)
        # The queued action should still be there.
        assert len(pc.ai.queue) == 1

    def test_counter_opt_in(self):
        from combat_sim.actions import AttackAction as AA, CounterAttackAction
        pc = make_pc("P")
        pc.ai = ScriptedAI(counter_when_offered=True)
        result = pc.ai.decide(pc, None,
                              trigger=AA(target=pc, weapon=SMALL))
        assert isinstance(result, CounterAttackAction)


# ---------------------------------------------------------------------------
# End-to-end: a scripted MoveAction goes through the round loop.
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def _setup(self, *, a_pos=(0, 0), b_pos=(9, 9), bf_size=10):
        bf = Battlefield(width=bf_size, height=bf_size)
        a = make_pc("A", movement=4)
        b = Character(name="B", wounds_max=8, stamina_max=2,
                      ws=1, weapon=MEDIUM_2H, ai=DuellistAI())
        bf.register(a, a_pos)
        bf.register(b, b_pos)
        eng = Engagement(Party("A", [a]), Party("B", [b]), battlefield=bf)
        ctx = CombatContext(dice=Dice(seed=0), engagement=eng)
        return a, b, eng, ctx

    def test_legal_move_is_applied(self):
        a, b, eng, ctx = self._setup(a_pos=(0, 0), b_pos=(9, 9))
        # Player picks (3, 3) — 3 squares away, within movement 4
        a.ai.enqueue(MoveAction(destination=(3, 3)))
        # Run one round
        run_round((eng.a, eng.b), ctx)
        # A moved to (3, 3); B did its own thing (irrelevant for this test)
        assert a.position == (3, 3)

    def test_illegal_move_silently_dropped(self):
        """Player clicks too far away — combat layer drops the action."""
        a, b, eng, ctx = self._setup(a_pos=(0, 0), b_pos=(9, 9))
        a.ai.enqueue(MoveAction(destination=(8, 8)))   # 8 squares; movement 4
        run_round((eng.a, eng.b), ctx)
        assert a.position == (0, 0)   # unchanged

    def test_move_into_occupied_square_dropped(self):
        # Use a stationary B (ScriptedAI with empty queue → PassAction)
        # so B doesn't vacate (3, 3) before A's turn.
        bf = Battlefield(width=10, height=10)
        a = make_pc("A", movement=8)
        b = Character(name="B", wounds_max=8, stamina_max=2,
                      ws=1, weapon=MEDIUM_2H, ai=ScriptedAI())
        bf.register(a, (0, 0))
        bf.register(b, (3, 3))
        eng = Engagement(Party("A", [a]), Party("B", [b]), battlefield=bf)
        ctx = CombatContext(dice=Dice(seed=0), engagement=eng)
        a.ai.enqueue(MoveAction(destination=(3, 3)))  # B is there
        run_round((eng.a, eng.b), ctx)
        assert a.position == (0, 0)

    def test_move_through_wall_dropped(self):
        """Destination reachable in Chebyshev distance but blocked by a
        wall — validate_move's A* sees no path."""
        bf = Battlefield(width=10, height=10,
                        blocked={(4, y) for y in range(0, 9)})  # wall
        a = make_pc("A", movement=8)
        b = Character(name="B", wounds_max=8, stamina_max=2,
                      ws=1, weapon=MEDIUM_2H, ai=DuellistAI())
        bf.register(a, (0, 0))
        bf.register(b, (8, 0))
        eng = Engagement(Party("A", [a]), Party("B", [b]), battlefield=bf)
        ctx = CombatContext(dice=Dice(seed=0), engagement=eng)
        # (6, 0) is 6 squares away — within movement 8 by Chebyshev,
        # but the wall blocks any path; A* must say no.
        a.ai.enqueue(MoveAction(destination=(6, 0)))
        run_round((eng.a, eng.b), ctx)
        # The move should be dropped — a stays put.
        assert a.position == (0, 0)
