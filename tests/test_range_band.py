"""Tests for the range-band modifier rule in combat.py."""

import pytest

from combat_sim.battlefield import Battlefield
from combat_sim.creatures import Character
from combat_sim.party import Party, Engagement
from combat_sim.combat import CombatContext, range_band_rule
from combat_sim.dice import Dice
from combat_sim.items import SHORT_BOW, MUSKET
from combat_sim.ai import DuellistAI


def make_archer():
    return Character(
        name="Archer", wounds_max=8, stamina_max=2,
        ws=1, bs=1, weapon=SHORT_BOW, ai=DuellistAI(),
    )


def make_target():
    return Character(name="Target", wounds_max=8, ai=DuellistAI())


def setup_at_distance(weapon, distance_squares):
    bf = Battlefield(width=300, height=10)
    a = Character(name="A", wounds_max=8, stamina_max=2,
                  bs=1, weapon=weapon, ai=DuellistAI())
    b = make_target()
    bf.register(a, (0, 5))
    bf.register(b, (distance_squares, 5))
    eng = Engagement(Party("A", [a]), Party("B", [b]), battlefield=bf)
    ctx = CombatContext(dice=Dice(seed=0), engagement=eng)
    return a, b, ctx


class TestRangeBandWithoutBattlefield:
    def test_returns_none_without_battlefield(self):
        """Range band is a no-op when there is no battlefield (every
        shot is treated as short range — matches legacy behaviour)."""
        a = make_archer()
        b = make_target()
        eng = Engagement(Party("A", [a]), Party("B", [b]))   # no bf
        ctx = CombatContext(dice=Dice(seed=0), engagement=eng)
        assert range_band_rule(a, b, SHORT_BOW, ctx, is_ranged=True) is None


class TestRangeBandShortBow:
    """Short bow: 50/300/450 ft = 10/60/90 squares."""

    def test_within_short_no_penalty(self):
        # Short bow short range = 50 ft = 10 squares. Place at 8.
        a, b, ctx = setup_at_distance(SHORT_BOW, 8)
        assert range_band_rule(a, b, SHORT_BOW, ctx, is_ranged=True) is None

    def test_medium_range_minus_two(self):
        # 50 ft < distance <= 300 ft. Place at 30 squares = 150 ft.
        a, b, ctx = setup_at_distance(SHORT_BOW, 30)
        mod = range_band_rule(a, b, SHORT_BOW, ctx, is_ranged=True)
        assert mod is not None
        assert mod.value == -2
        assert "Medium" in mod.source

    def test_long_range_minus_four(self):
        # Place at 70 squares = 350 ft, > 300 ft.
        a, b, ctx = setup_at_distance(SHORT_BOW, 70)
        mod = range_band_rule(a, b, SHORT_BOW, ctx, is_ranged=True)
        assert mod is not None
        assert mod.value == -4
        assert "Long" in mod.source

    def test_out_of_range_returns_none(self):
        # Past long range = 450 ft = 90 squares. Place at 100.
        a, b, ctx = setup_at_distance(SHORT_BOW, 100)
        assert range_band_rule(a, b, SHORT_BOW, ctx, is_ranged=True) is None


class TestRangeBandFirearm:
    """Firearms double the band penalty per Firearms.md.
    Musket: 50/100/600 ft = 10/20/120 squares."""

    def test_short_range_no_penalty(self):
        a, b, ctx = setup_at_distance(MUSKET, 8)
        assert range_band_rule(a, b, MUSKET, ctx, is_ranged=True) is None

    def test_medium_range_minus_four(self):
        # > 50 ft, <= 100 ft. Place at 15 squares = 75 ft.
        a, b, ctx = setup_at_distance(MUSKET, 15)
        mod = range_band_rule(a, b, MUSKET, ctx, is_ranged=True)
        assert mod is not None
        assert mod.value == -4

    def test_long_range_minus_eight(self):
        # > 100 ft, <= 600 ft. Place at 50 squares = 250 ft.
        a, b, ctx = setup_at_distance(MUSKET, 50)
        mod = range_band_rule(a, b, MUSKET, ctx, is_ranged=True)
        assert mod is not None
        assert mod.value == -8


class TestNonRangedNoBand:
    def test_melee_weapon_returns_none(self):
        from combat_sim.items import SMALL
        a, b, ctx = setup_at_distance(SHORT_BOW, 30)
        # Calling with is_ranged=False (melee path)
        assert range_band_rule(a, b, SMALL, ctx, is_ranged=False) is None
