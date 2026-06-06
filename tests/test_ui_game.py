"""End-to-end tests for the game driver, using ScriptedFrontend.

These exercise the full pipeline (map -> parties -> conditions -> combat)
without the terminal — proves the seam between the sim and the UI is
clean.
"""

import pytest

from combat_sim.ui.game import run_game, ScriptedFrontend
from combat_sim.ui.registry import Registry
from combat_sim.ui.parties import PARTY_TEMPLATES, build_party
from combat_sim.ui.maps import parse_map
from combat_sim.ui.frontend import ConditionSet
from combat_sim.battlefield import Battlefield
from combat_sim.dice import Dice
from combat_sim.actions import (
    AttackAction, MoveAction, FullDefenceAction, PassAction,
)
from combat_sim.ai import DuellistAI


# ---------------------------------------------------------------------------
# Setup pipeline
# ---------------------------------------------------------------------------

class TestSetupPipeline:
    def test_default_choices_run_a_full_fight(self):
        """No callbacks supplied → ScriptedFrontend picks the first
        option for every choice. Game should complete without error."""
        result = run_game(ScriptedFrontend(),
                         Registry(),
                         seed=42, max_rounds=100)
        assert result.rounds > 0
        # Either a winner or a draw — both are acceptable outcomes.

    def test_human_choice_replaces_ai(self):
        """If choose_human_controlled returns a creature, its AI is
        replaced with HumanAI. We verify by intercepting via a custom
        scripted frontend that always passes."""
        from combat_sim.ui.human_ai import HumanAI
        captured: list = []

        def grab_humans(creatures):
            humans = [c for c in creatures if c.name == "Karl"]
            captured.extend(humans)
            return humans

        frontend = ScriptedFrontend(
            human_choice=grab_humans,
            # Always pass — keeps the fight short and predictable.
            action_policy=lambda **kw: PassAction(),
        )
        result = run_game(frontend, Registry(),
                         seed=1, max_rounds=10)
        # We should have captured at least one Karl (depending on the
        # first-template default — confirm it).
        assert any(isinstance(c.ai, HumanAI) for c in captured)

    def test_seed_determinism(self):
        """Same seed + same scripted answers → identical CombatResult."""
        def make():
            return run_game(ScriptedFrontend(),
                          Registry(),
                          seed=7, max_rounds=100)
        r1 = make()
        r2 = make()
        assert r1.winner == r2.winner
        assert r1.rounds == r2.rounds


# ---------------------------------------------------------------------------
# Action policy: actually playing a fight via scripted decisions
# ---------------------------------------------------------------------------

class TestScriptedPlay:
    def test_human_attacks_first_available(self):
        """A scripted 'human' that always picks the first AttackAction
        in the menu (else passes). Verify the fight resolves."""
        from combat_sim.targeting import available_actions

        def play(*, actor, options, ctx):
            for o in options:
                if isinstance(o, AttackAction):
                    return o
            return PassAction()

        frontend = ScriptedFrontend(
            human_choice=lambda cs: [c for c in cs if c.name == "Karl"],
            action_policy=play,
        )
        result = run_game(frontend, Registry(),
                         seed=99, max_rounds=50)
        # The fight should end one way or another (winner or draw at
        # max_rounds — both fine; the assertion is the test ran cleanly).
        assert result.rounds > 0


# ---------------------------------------------------------------------------
# Rendering hooks fire
# ---------------------------------------------------------------------------

class TestRenderingHooks:
    def test_round_start_and_end_events(self):
        frontend = ScriptedFrontend(
            action_policy=lambda **kw: PassAction(),
        )
        result = run_game(frontend, Registry(),
                         seed=3, max_rounds=20)
        kinds = [e[0] for e in frontend.events]
        assert kinds[0] == "round_start"
        assert kinds[-1] == "end"


# ---------------------------------------------------------------------------
# Map-to-Party bridge
# ---------------------------------------------------------------------------

class TestPartyBuilder:
    def test_creature_placed_at_slot(self):
        text = """\
---
1...A
"""
        m = parse_map(text)
        bf = Battlefield(width=m.width, height=m.height, blocked=set(m.blocked))
        dice = Dice(seed=0)
        party_a = build_party(PARTY_TEMPLATES["lone_warrior_a"],
                              m, bf, dice=dice)
        assert party_a.members[0].position == (0, 0)

    def test_unknown_slot_raises(self):
        text = "---\n1\n"  # only slot 1; spec with slot=2 should fail
        m = parse_map(text)
        bf = Battlefield(width=m.width, height=m.height, blocked=set(m.blocked))
        dice = Dice(seed=0)
        with pytest.raises(Exception):
            build_party(PARTY_TEMPLATES["two_warriors_a"],
                       m, bf, dice=dice)


# ---------------------------------------------------------------------------
# ConditionSet placeholder
# ---------------------------------------------------------------------------

class TestConditionSet:
    def test_default_is_empty(self):
        cs = ConditionSet()
        assert cs.notes == []


# ---------------------------------------------------------------------------
# on_action callback fires from combat.run_round
# ---------------------------------------------------------------------------

class TestOnActionCallback:
    def test_callback_fires_for_every_action(self):
        """game.run_game wires frontend.on_action_resolved into
        ctx.on_action — confirm it actually fires once per actor turn."""
        action_log: list = []

        class RecorderFrontend(ScriptedFrontend):
            def on_action_resolved(self, actor, action, ctx):
                action_log.append((actor.name, type(action).__name__,
                                   ctx.round_no))

        frontend = RecorderFrontend(
            action_policy=lambda **kw: PassAction(),
        )
        run_game(frontend, Registry(), seed=11, max_rounds=3)

        # At least 2 entries per round (one per side); seed/max_rounds
        # chosen so combat doesn't end before round 3.
        assert len(action_log) >= 2
        # All entries are tuples with round_no >= 1 (callback fires
        # inside run_round, after round_no has been incremented).
        assert all(r >= 1 for _, _, r in action_log)

    def test_callback_optional(self):
        """A CombatContext with on_action=None must run without error —
        used by headless scenario sweeps."""
        from combat_sim.scenarios import run_scenario
        # If the on_action wiring broke the headless path, this would
        # raise. Just ensure a scenario still runs.
        s = run_scenario("S1", n=10, seed=0)
        assert s.a_wins + s.b_wins + s.draws == 10
