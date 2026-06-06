"""Tests for combat_sim.battlefield — terrain + occupancy index."""

import pytest

from combat_sim.battlefield import Battlefield
from combat_sim.creatures import Creature


def make_creature(name="X"):
    """Bare creature for positioning tests. Combat fields don't matter."""
    return Creature(name=name, wounds_max=1)


class TestInBounds:
    def test_inside(self):
        bf = Battlefield(width=10, height=5)
        assert bf.in_bounds((0, 0))
        assert bf.in_bounds((9, 4))
        assert bf.in_bounds((5, 2))

    def test_outside(self):
        bf = Battlefield(width=10, height=5)
        assert not bf.in_bounds((-1, 0))
        assert not bf.in_bounds((10, 0))
        assert not bf.in_bounds((0, 5))
        assert not bf.in_bounds((0, -1))


class TestTerrainBlocking:
    def test_default_no_blocked(self):
        bf = Battlefield(width=10, height=10)
        assert not bf.is_terrain_blocked((3, 3))

    def test_blocked_set(self):
        bf = Battlefield(width=10, height=10, blocked={(3, 3), (4, 4)})
        assert bf.is_terrain_blocked((3, 3))
        assert bf.is_terrain_blocked((4, 4))
        assert not bf.is_terrain_blocked((2, 2))


class TestOccupancy:
    def test_empty_unoccupied(self):
        bf = Battlefield(width=10, height=10)
        assert not bf.is_occupied((1, 1))
        assert bf.occupant((1, 1)) is None

    def test_register_places_creature(self):
        bf = Battlefield(width=10, height=10)
        c = make_creature("A")
        bf.register(c, (3, 4))
        assert bf.is_occupied((3, 4))
        assert bf.occupant((3, 4)) is c
        assert c.position == (3, 4)

    def test_deregister_clears_square(self):
        bf = Battlefield(width=10, height=10)
        c = make_creature()
        bf.register(c, (2, 2))
        bf.deregister(c)
        assert not bf.is_occupied((2, 2))
        assert c.position is None


class TestPassability:
    def test_open_square(self):
        bf = Battlefield(width=10, height=10)
        assert bf.is_passable((5, 5))

    def test_terrain_blocks(self):
        bf = Battlefield(width=10, height=10, blocked={(5, 5)})
        assert not bf.is_passable((5, 5))

    def test_occupied_blocks(self):
        bf = Battlefield(width=10, height=10)
        bf.register(make_creature(), (5, 5))
        assert not bf.is_passable((5, 5))

    def test_occupant_ignored_when_passed(self):
        """A creature can re-enter / pass through its own square."""
        bf = Battlefield(width=10, height=10)
        c = make_creature()
        bf.register(c, (5, 5))
        assert bf.is_passable((5, 5), ignoring=c)
        # other creatures still see it as blocked
        other = make_creature("other")
        assert not bf.is_passable((5, 5), ignoring=other)

    def test_out_of_bounds_not_passable(self):
        bf = Battlefield(width=10, height=10)
        assert not bf.is_passable((-1, 0))
        assert not bf.is_passable((10, 0))


class TestUpdatePosition:
    def test_move_clears_old_square(self):
        bf = Battlefield(width=10, height=10)
        c = make_creature()
        bf.register(c, (1, 1))
        bf.update_position(c, (2, 2))
        assert not bf.is_occupied((1, 1))
        assert bf.is_occupied((2, 2))
        assert bf.occupant((2, 2)) is c
        assert c.position == (2, 2)

    def test_creature_move_to_returns_true_on_success(self):
        """move_to is the canonical way to move; round-trips through battlefield."""
        bf = Battlefield(width=10, height=10)
        c = make_creature()
        bf.register(c, (0, 0))
        ok = c.move_to((1, 1), bf)
        assert ok
        assert c.position == (1, 1)
        assert bf.occupant((1, 1)) is c

    def test_creature_move_to_rejects_blocked(self):
        bf = Battlefield(width=10, height=10, blocked={(1, 1)})
        c = make_creature()
        bf.register(c, (0, 0))
        ok = c.move_to((1, 1), bf)
        assert not ok
        assert c.position == (0, 0)        # unchanged
        assert bf.occupant((0, 0)) is c    # still in old square

    def test_creature_move_to_rejects_occupied(self):
        bf = Battlefield(width=10, height=10)
        a = make_creature("A")
        b = make_creature("B")
        bf.register(a, (0, 0))
        bf.register(b, (1, 1))
        ok = a.move_to((1, 1), bf)
        assert not ok
        assert a.position == (0, 0)
