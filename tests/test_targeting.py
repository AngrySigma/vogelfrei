"""Tests for combat_sim.targeting — perception queries + available_actions."""

import pytest

from combat_sim.battlefield import Battlefield
from combat_sim.creatures import Character
from combat_sim.party import Party, Engagement
from combat_sim.combat import CombatContext
from combat_sim.dice import Dice
from combat_sim.items import SMALL, MEDIUM_2H, SHORT_BOW, LONG_BOW
from combat_sim.targeting import (
    enemies_of,
    enemies_in_melee_range,
    enemies_in_ranged_range,
    nearest_enemy,
    available_actions,
)
from combat_sim.actions import (
    AttackAction, MoveAction, MoveAndAttackAction,
    FullDefenceAction, PassAction,
)
from combat_sim.ai import DuellistAI


def make_warrior(name, weapon=SMALL, ws=1):
    return Character(
        name=name, wounds_max=8, stamina_max=2,
        ws=ws, weapon=weapon, ai=DuellistAI(),
    )


def setup(creatures_a, creatures_b, *, battlefield=None):
    pa = Party("A", creatures_a)
    pb = Party("B", creatures_b)
    eng = Engagement(pa, pb, battlefield=battlefield)
    ctx = CombatContext(dice=Dice(seed=0), engagement=eng)
    return pa, pb, eng, ctx


# ---------------------------------------------------------------------------
# No-battlefield mode — preserves legacy "everyone adjacent" semantics
# ---------------------------------------------------------------------------

class TestNoBattlefield:
    def test_all_enemies_in_melee_range(self):
        """Without a battlefield, every enemy is treated as adjacent
        (collapsed to the legacy paired target)."""
        a = make_warrior("A")
        b = make_warrior("B")
        _, _, _, ctx = setup([a], [b])
        assert b in enemies_in_melee_range(a, ctx)

    def test_nearest_enemy_returns_paired(self):
        a, b = make_warrior("A"), make_warrior("B")
        _, _, _, ctx = setup([a], [b])
        assert nearest_enemy(a, ctx) is b


# ---------------------------------------------------------------------------
# Battlefield mode — distance-based filtering
# ---------------------------------------------------------------------------

class TestBattlefieldMelee:
    def test_adjacent_is_melee_candidate(self):
        bf = Battlefield(width=10, height=10)
        a, b = make_warrior("A"), make_warrior("B")
        bf.register(a, (5, 5))
        bf.register(b, (6, 5))  # 1 east
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        assert b in enemies_in_melee_range(a, ctx)

    def test_two_away_not_melee(self):
        bf = Battlefield(width=10, height=10)
        a, b = make_warrior("A"), make_warrior("B")
        bf.register(a, (5, 5))
        bf.register(b, (7, 5))  # 2 east
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        assert b not in enemies_in_melee_range(a, ctx)

    def test_diagonal_adjacent_counts(self):
        """Chebyshev: diagonal = 1, so corner-adjacent is in melee."""
        bf = Battlefield(width=10, height=10)
        a, b = make_warrior("A"), make_warrior("B")
        bf.register(a, (5, 5))
        bf.register(b, (6, 6))
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        assert b in enemies_in_melee_range(a, ctx)


class TestBattlefieldRanged:
    def test_short_bow_in_range(self):
        """Short bow range_long = 450 ft = 90 squares."""
        bf = Battlefield(width=100, height=10)
        a = make_warrior("A", weapon=SHORT_BOW, ws=1)
        a.bs = 1
        b = make_warrior("B")
        bf.register(a, (0, 5))
        bf.register(b, (50, 5))
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        assert b in enemies_in_ranged_range(a, SHORT_BOW, ctx)

    def test_short_bow_out_of_range(self):
        """450 ft / 5 = 90 squares. Place at 95 — out of range."""
        bf = Battlefield(width=200, height=10)
        a = make_warrior("A", weapon=SHORT_BOW)
        a.bs = 1
        b = make_warrior("B")
        bf.register(a, (0, 5))
        bf.register(b, (95, 5))
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        assert b not in enemies_in_ranged_range(a, SHORT_BOW, ctx)

    def test_long_bow_outranges_short_bow(self):
        """Long bow range_long = 900 ft = 180 squares."""
        bf = Battlefield(width=300, height=10)
        a = make_warrior("A", weapon=LONG_BOW)
        a.bs = 1
        b = make_warrior("B")
        bf.register(a, (0, 5))
        bf.register(b, (150, 5))
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        assert b in enemies_in_ranged_range(a, LONG_BOW, ctx)
        assert b not in enemies_in_ranged_range(a, SHORT_BOW, ctx)


class TestNearestEnemy:
    def test_picks_closest(self):
        bf = Battlefield(width=20, height=20)
        a = make_warrior("A")
        b1 = make_warrior("B1")
        b2 = make_warrior("B2")
        bf.register(a, (10, 10))
        bf.register(b1, (5, 10))     # 5 away
        bf.register(b2, (12, 10))    # 2 away
        _, _, _, ctx = setup([a], [b1, b2], battlefield=bf)
        assert nearest_enemy(a, ctx) is b2


# ---------------------------------------------------------------------------
# available_actions — the UI's contract
# ---------------------------------------------------------------------------

class TestAvailableActions:
    def test_always_includes_pass_and_fulldefence(self):
        a, b = make_warrior("A"), make_warrior("B")
        _, _, _, ctx = setup([a], [b])
        actions = available_actions(a, ctx)
        assert any(isinstance(x, PassAction) for x in actions)
        assert any(isinstance(x, FullDefenceAction) for x in actions)

    def test_offers_attack_when_adjacent(self):
        bf = Battlefield(width=10, height=10)
        a, b = make_warrior("A"), make_warrior("B")
        bf.register(a, (5, 5))
        bf.register(b, (6, 5))
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        actions = available_actions(a, ctx)
        attack_targets = [x.target for x in actions
                          if isinstance(x, AttackAction)]
        assert b in attack_targets

    def test_offers_move_and_attack_when_reachable(self):
        bf = Battlefield(width=20, height=20)
        a, b = make_warrior("A"), make_warrior("B")
        bf.register(a, (0, 0))
        bf.register(b, (5, 5))     # 5 squares; archer reaches melee adjacency in one round (movement 8)
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        actions = available_actions(a, ctx)
        mna = [x for x in actions if isinstance(x, MoveAndAttackAction)]
        assert len(mna) >= 1
        assert mna[0].attack.target is b

    def test_offers_move_only_when_too_far(self):
        bf = Battlefield(width=30, height=30)
        a, b = make_warrior("A"), make_warrior("B")
        bf.register(a, (0, 0))
        bf.register(b, (29, 29))   # 29 away; movement 8 not enough to close to adjacency
        _, _, _, ctx = setup([a], [b], battlefield=bf)
        actions = available_actions(a, ctx)
        # No MoveAndAttack should be in the list (can't reach melee)
        assert not any(isinstance(x, MoveAndAttackAction) for x in actions)
        # But there should be a MoveAction toward the enemy
        moves = [x for x in actions if isinstance(x, MoveAction)]
        assert len(moves) >= 1
