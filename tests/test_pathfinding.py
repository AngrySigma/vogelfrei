"""Tests for the A* shortest-path search and BFS reachability search.

These are the foundations the movement helpers (walk_toward,
can_retreat_to_distance, threat_can_close_to_melee) are built on, and
they are also what the future UI will use to highlight reachable
squares when the player picks a destination.
"""

import pytest

from combat_sim.battlefield import Battlefield
from combat_sim.creatures import Creature
from combat_sim.movement import (
    find_path, reachable_within, validate_move,
)
from combat_sim.geometry import chebyshev


def make_creature(name="X", movement=8):
    return Creature(name=name, wounds_max=1, movement_squares=movement)


# ---------------------------------------------------------------------------
# find_path — A* shortest path
# ---------------------------------------------------------------------------

class TestFindPath:
    def test_open_field_straight_line(self):
        bf = Battlefield(width=10, height=10)
        path = find_path((0, 0), (5, 0), bf)
        # 5 steps east, path length 6 (inclusive of start)
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (5, 0)
        assert len(path) == 6

    def test_open_field_diagonal(self):
        bf = Battlefield(width=10, height=10)
        path = find_path((0, 0), (3, 3), bf)
        # Chebyshev: 3 diagonal steps, path length 4
        assert path is not None
        assert path[-1] == (3, 3)
        assert len(path) == 4

    def test_start_equals_goal(self):
        bf = Battlefield(width=10, height=10)
        path = find_path((5, 5), (5, 5), bf)
        assert path == [(5, 5)]

    def test_routes_around_wall(self):
        """A vertical wall blocks the direct line — A* must detour."""
        bf = Battlefield(width=10, height=10,
                        blocked={(2, y) for y in range(0, 8)})
        # Direct path (0, 0) -> (5, 0) is 5 squares east, blocked by (2, 0).
        # Detour: go up around the wall.
        path = find_path((0, 0), (5, 0), bf)
        assert path is not None
        assert path[-1] == (5, 0)
        # Should still be reasonably short (wall is 8 tall, gap at y=8/9)
        # Optimal: (0,0) -> (1,1) -> ... -> route over the top -> (5,0).
        # Length should exceed pure-line (6) but not by too much.
        assert len(path) > 6
        # Confirm no step is into a blocked square.
        for sq in path:
            assert not bf.is_terrain_blocked(sq)

    def test_no_path_when_fully_walled(self):
        """Goal is in a sealed room."""
        bf = Battlefield(width=10, height=10,
                        blocked={(4, 4), (4, 5), (4, 6),
                                 (5, 4),         (5, 6),
                                 (6, 4), (6, 5), (6, 6)})
        path = find_path((0, 0), (5, 5), bf)
        assert path is None

    def test_passes_through_own_square(self):
        """When ``ignoring`` is the moving creature, its own start
        square is not an obstacle."""
        bf = Battlefield(width=10, height=10)
        me = make_creature("me")
        bf.register(me, (3, 3))
        # find a path from my position to elsewhere — must work
        path = find_path((3, 3), (5, 5), bf, ignoring=me)
        assert path is not None
        assert path[-1] == (5, 5)

    def test_blocked_by_other_creature(self):
        """Another creature on the direct line forces a detour."""
        bf = Battlefield(width=10, height=10)
        wall = make_creature("wall")
        bf.register(wall, (2, 0))  # blocks the direct east path
        path = find_path((0, 0), (5, 0), bf)
        assert path is not None
        # Path must avoid (2, 0).
        assert (2, 0) not in path

    def test_stop_distance_one_ends_adjacent(self):
        """With stop_distance=1 (the 'move into melee' case) the path
        ends one square from the goal, not on it."""
        bf = Battlefield(width=10, height=10)
        path = find_path((0, 0), (5, 5), bf, stop_distance=1)
        assert path is not None
        # Last square should be adjacent to goal
        assert chebyshev(path[-1], (5, 5)) <= 1
        # And it should NOT be the goal itself (unless start was already
        # adjacent — not the case here)
        assert path[-1] != (5, 5)

    def test_stop_distance_zero_ends_on_goal(self):
        bf = Battlefield(width=10, height=10)
        path = find_path((0, 0), (5, 5), bf, stop_distance=0)
        assert path is not None
        assert path[-1] == (5, 5)


# ---------------------------------------------------------------------------
# reachable_within — BFS for the UI's "highlight reachable squares"
# ---------------------------------------------------------------------------

class TestReachableWithin:
    def test_open_field_radius_two(self):
        bf = Battlefield(width=10, height=10)
        reach = reachable_within((5, 5), 2, bf)
        # Chebyshev disc radius 2 = 5x5 = 25 squares including centre
        assert (5, 5) in reach
        assert reach[(5, 5)] == 0
        assert reach[(7, 7)] == 2
        assert reach[(7, 5)] == 2
        assert (8, 5) not in reach   # outside radius 2

    def test_excludes_blocked_squares(self):
        bf = Battlefield(width=10, height=10, blocked={(6, 5)})
        reach = reachable_within((5, 5), 3, bf)
        assert (6, 5) not in reach

    def test_wall_extends_path_cost(self):
        """A square reachable in 1 step via diagonal but blocked by a
        wall costs more (must go around)."""
        bf = Battlefield(width=10, height=10,
                        blocked={(6, 5), (6, 6), (6, 4)})
        reach = reachable_within((5, 5), 5, bf)
        # (7, 5) is normally 2 diagonals away (cost 2) but the wall at
        # (6, 5) blocks the direct route. Must detour.
        # (5,5) -> (5,4) -> ? — Going around the wall, fastest is
        # (5,5) -> (5,3) -> ... actually multiple routes possible.
        # Just confirm cost > 2 (which it would be without the wall).
        assert reach.get((7, 5), 999) > 2

    def test_bounds_respected(self):
        bf = Battlefield(width=4, height=4)
        reach = reachable_within((0, 0), 10, bf)
        # Map is only 4x4 = 16 squares total
        assert len(reach) <= 16
        # Out-of-bounds not present
        assert (5, 5) not in reach
        assert (-1, 0) not in reach


# ---------------------------------------------------------------------------
# validate_move — defensive gate for user-supplied destinations
# ---------------------------------------------------------------------------

class TestValidateMove:
    def test_accepts_in_budget(self):
        bf = Battlefield(width=20, height=20)
        c = make_creature(movement=8)
        bf.register(c, (5, 5))
        assert validate_move(c, (10, 10), bf) is True   # 5 squares away

    def test_rejects_beyond_budget(self):
        bf = Battlefield(width=30, height=30)
        c = make_creature(movement=4)
        bf.register(c, (0, 0))
        assert validate_move(c, (10, 10), bf) is False  # 10 > movement 4

    def test_rejects_blocked_destination(self):
        bf = Battlefield(width=10, height=10, blocked={(3, 3)})
        c = make_creature(movement=8)
        bf.register(c, (0, 0))
        assert validate_move(c, (3, 3), bf) is False

    def test_rejects_occupied_destination(self):
        bf = Battlefield(width=10, height=10)
        a = make_creature("A", movement=8)
        b = make_creature("B")
        bf.register(a, (0, 0))
        bf.register(b, (3, 3))
        assert validate_move(a, (3, 3), bf) is False

    def test_rejects_out_of_bounds(self):
        bf = Battlefield(width=10, height=10)
        c = make_creature(movement=8)
        bf.register(c, (5, 5))
        assert validate_move(c, (15, 15), bf) is False

    def test_rejects_unreachable_due_to_wall(self):
        """Destination in a sealed room — can't be reached even with
        infinite movement budget."""
        bf = Battlefield(width=10, height=10,
                        blocked={(4, 4), (4, 5), (4, 6),
                                 (5, 4),         (5, 6),
                                 (6, 4), (6, 5), (6, 6)})
        c = make_creature(movement=100)
        bf.register(c, (0, 0))
        assert validate_move(c, (5, 5), bf) is False
