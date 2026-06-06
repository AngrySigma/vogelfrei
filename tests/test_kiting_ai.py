"""Tests for KitingAI's lookahead logic.

Five branches to cover:
    (a) safe + in range -> AttackAction
    (b) too close, can retreat -> MoveAction
    (c) too close, cornered, in range -> AttackAction
    (d) too close, cornered, out of range -> PassAction
    (e) safe but out of range -> PassAction (don't run into danger)

Plus the "outrun by a faster enemy" degenerate case from the user's
feedback: when retreat is impossible because the enemy is faster than
you, still fire if in range.
"""

import pytest

from combat_sim.battlefield import Battlefield
from combat_sim.creatures import Character
from combat_sim.party import Party, Engagement
from combat_sim.combat import CombatContext
from combat_sim.dice import Dice
from combat_sim.items import SHORT_BOW, LONG_BOW, MEDIUM_2H
from combat_sim.ai import KitingAI, DuellistAI
from combat_sim.actions import AttackAction, MoveAction, PassAction


def archer(name="Archer", weapon=SHORT_BOW, movement=8):
    a = Character(
        name=name, wounds_max=8, stamina_max=2,
        ws=1, bs=1, weapon=weapon, ai=KitingAI(),
        movement_squares=movement,
    )
    return a


def melee(name="Swordsman", movement=8):
    return Character(
        name=name, wounds_max=8, stamina_max=2,
        ws=1, weapon=MEDIUM_2H, ai=DuellistAI(),
        movement_squares=movement,
    )


def setup(bf, *, a_pos, b_pos, a_weapon=SHORT_BOW,
          a_mov=8, b_mov=8):
    a = archer(weapon=a_weapon, movement=a_mov)
    b = melee(movement=b_mov)
    bf.register(a, a_pos)
    bf.register(b, b_pos)
    eng = Engagement(Party("A", [a]), Party("B", [b]), battlefield=bf)
    ctx = CombatContext(dice=Dice(seed=0), engagement=eng)
    return a, b, ctx


# ---------------------------------------------------------------------------
# (a) safe + in range -> fire
# ---------------------------------------------------------------------------

class TestSafeAndInRange:
    def test_fires_when_safe_and_in_range(self):
        """Archer 20 squares from swordsman (movement 8 → safe = 9).
        Distance 20 >> safe 9, and well within short bow's 90-square
        long range. Should fire."""
        bf = Battlefield(width=50, height=10)
        a, b, ctx = setup(bf, a_pos=(0, 5), b_pos=(20, 5))
        action = a.ai.decide(a, ctx)
        assert isinstance(action, AttackAction)
        assert action.target is b


# ---------------------------------------------------------------------------
# (b) too close, can retreat -> MoveAction
# ---------------------------------------------------------------------------

class TestRetreatsWhenThreatened:
    def test_retreats_when_threat_too_close(self):
        """Archer 3 squares from swordsman (movement 8 → safe = 9).
        Distance 3 < safe 9, plenty of open field — should move away."""
        bf = Battlefield(width=50, height=20)
        a, b, ctx = setup(bf, a_pos=(20, 10), b_pos=(17, 10))
        action = a.ai.decide(a, ctx)
        assert isinstance(action, MoveAction)
        # New position should put us further from b than we are now.
        from combat_sim.geometry import chebyshev
        new_dist = chebyshev(action.destination, b.position)
        old_dist = chebyshev(a.position, b.position)
        assert new_dist > old_dist


# ---------------------------------------------------------------------------
# (c) too close, cornered, in range -> fire
# ---------------------------------------------------------------------------

class TestCorneredFiresWhenInRange:
    def test_walled_in_corner_fires(self):
        """Tiny 3x3 map; archer in corner, swordsman in opposite corner
        (distance 2). Archer's movement (8) doesn't matter — there's no
        square within the map that is >= safe 9 from b. Should fire."""
        bf = Battlefield(width=3, height=3)
        a, b, ctx = setup(bf, a_pos=(0, 0), b_pos=(2, 2))
        action = a.ai.decide(a, ctx)
        assert isinstance(action, AttackAction)
        assert action.target is b


# ---------------------------------------------------------------------------
# (d) too close, cornered, out of range -> Pass
# ---------------------------------------------------------------------------

class TestCorneredOutOfRangePasses:
    def test_no_retreat_no_range_passes(self):
        """Use a weapon with very short range; archer cornered AND out
        of range — should Pass."""
        from combat_sim.items import Weapon
        # Custom weapon: only short range = 5 ft = 1 square long range.
        toy = Weapon(name="Toy", damage="1d2", length=0, is_ranged=True,
                     range_short=5, range_medium=5, range_long=5)
        bf = Battlefield(width=3, height=3)
        a, b, ctx = setup(bf, a_pos=(0, 0), b_pos=(2, 2), a_weapon=toy)
        # b is 2 squares away, weapon long range = 1 square → b not in range
        action = a.ai.decide(a, ctx)
        assert isinstance(action, PassAction)


# ---------------------------------------------------------------------------
# Outrun-by-faster-enemy: still fires when retreat impossible
# ---------------------------------------------------------------------------

class TestOutrunByFasterEnemy:
    def test_faster_enemy_archer_still_fires(self):
        """Archer movement 4, swordsman movement 12. Safe distance =
        13. On a 30x10 map, even max-retreat (4 squares) cannot put the
        archer 13 away from a foe currently 5 away. Cornered-by-speed:
        archer should fire because b is in range."""
        bf = Battlefield(width=30, height=10)
        a, b, ctx = setup(bf, a_pos=(20, 5), b_pos=(15, 5),
                         a_mov=4, b_mov=12)
        action = a.ai.decide(a, ctx)
        # Best case: even if retreat finds a partial improvement that
        # still doesn't reach safe, it returns None → falls to fire.
        assert isinstance(action, AttackAction)
        assert action.target is b


# ---------------------------------------------------------------------------
# Reloading: weapon unavailable -> Pass
# ---------------------------------------------------------------------------

class TestReloadingPasses:
    def test_passes_while_reloading(self):
        from combat_sim.conditions import Reloading
        bf = Battlefield(width=30, height=10)
        a, b, ctx = setup(bf, a_pos=(0, 5), b_pos=(15, 5))
        a.add_condition(Reloading(a.weapon, rounds=5))
        action = a.ai.decide(a, ctx)
        assert isinstance(action, PassAction)


# ---------------------------------------------------------------------------
# Trigger (reactive): kiter doesn't counter
# ---------------------------------------------------------------------------

class TestReactiveTrigger:
    def test_reactive_returns_pass(self):
        bf = Battlefield(width=30, height=10)
        a, b, ctx = setup(bf, a_pos=(0, 5), b_pos=(15, 5))
        action = a.ai.decide(a, ctx,
                            trigger=AttackAction(target=a, weapon=b.weapon))
        assert isinstance(action, PassAction)
