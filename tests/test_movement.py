"""Tests for combat_sim.movement — composed step/walk/retreat helpers.

All deterministic; no dice rolls.
"""

import pytest

from combat_sim.battlefield import Battlefield
from combat_sim.creatures import Creature
from combat_sim.movement import (
    step_toward,
    walk_toward,
    can_retreat_to_distance,
    threat_can_close_to_melee,
)


def make_creature(name="X", movement=8):
    return Creature(name=name, wounds_max=1, movement_squares=movement)


# ---------------------------------------------------------------------------
# step_toward
# ---------------------------------------------------------------------------

class TestStepToward:
    def test_open_diagonal(self):
        bf = Battlefield(width=10, height=10)
        assert step_toward((0, 0), (5, 5), bf) == (1, 1)

    def test_open_east(self):
        bf = Battlefield(width=10, height=10)
        assert step_toward((0, 0), (5, 0), bf) == (1, 0)

    def test_already_adjacent_takes_final_step(self):
        bf = Battlefield(width=10, height=10)
        # one diagonal away
        assert step_toward((0, 0), (1, 1), bf) == (1, 1)

    def test_blocks_terrain_falls_to_cardinal(self):
        """Ideal step (1,1) blocked; should fall to (1,0) or (0,1)."""
        bf = Battlefield(width=10, height=10, blocked={(1, 1)})
        result = step_toward((0, 0), (5, 5), bf)
        assert result in {(1, 0), (0, 1)}

    def test_all_blocked_returns_none(self):
        """No usable direction — stuck."""
        bf = Battlefield(width=10, height=10,
                        blocked={(1, 0), (0, 1), (1, 1)})
        assert step_toward((0, 0), (5, 5), bf) is None

    def test_creature_blocks(self):
        bf = Battlefield(width=10, height=10)
        wall = make_creature("wall")
        bf.register(wall, (1, 1))
        result = step_toward((0, 0), (5, 5), bf)
        assert result in {(1, 0), (0, 1)}

    def test_own_square_does_not_block(self):
        """When computing a step for me, my own square is passable."""
        bf = Battlefield(width=10, height=10)
        me = make_creature("me")
        bf.register(me, (0, 0))
        # The ideal step from (0,0) toward (5,5) is (1,1); not me; succeeds.
        assert step_toward((0, 0), (5, 5), bf, ignoring=me) == (1, 1)


# ---------------------------------------------------------------------------
# walk_toward
# ---------------------------------------------------------------------------

class TestWalkToward:
    def test_walks_full_distance(self):
        bf = Battlefield(width=20, height=20)
        c = make_creature(movement=8)
        bf.register(c, (0, 0))
        final = walk_toward(c, (15, 15), max_squares=8, battlefield=bf)
        # 8 diagonal steps from (0,0) -> (8,8)
        assert final == (8, 8)

    def test_stops_adjacent_to_target(self):
        """Should stop at adjacency, not walk onto the target itself."""
        bf = Battlefield(width=20, height=20)
        c = make_creature(movement=8)
        bf.register(c, (0, 0))
        final = walk_toward(c, (3, 3), max_squares=8, battlefield=bf)
        # adjacent to (3,3) is (2,2) via diagonal in 2 steps
        assert final == (2, 2)

    def test_walks_around_corner(self):
        """A column of wall in the middle: greedy step should detour
        cardinally and still make progress."""
        bf = Battlefield(width=20, height=20, blocked={(2, 2), (2, 3), (2, 4)})
        c = make_creature(movement=10)
        bf.register(c, (0, 0))
        final = walk_toward(c, (5, 3), max_squares=10, battlefield=bf)
        # Greedy will get to (1,1), then try (2,2) blocked, fall to (1,2),
        # then (2,3) blocked, fall to (1,3)... eventually skirts the wall.
        # Just assert it ended up significantly closer to the target.
        from combat_sim.geometry import chebyshev
        assert chebyshev(final, (5, 3)) < chebyshev((0, 0), (5, 3))

    def test_creature_position_is_unchanged_by_walk_toward(self):
        """walk_toward is a *helper* — does not move the creature.
        That's the caller's job via MoveAction execution."""
        bf = Battlefield(width=20, height=20)
        c = make_creature()
        bf.register(c, (0, 0))
        walk_toward(c, (5, 5), max_squares=8, battlefield=bf)
        assert c.position == (0, 0)
        assert bf.occupant((0, 0)) is c


# ---------------------------------------------------------------------------
# can_retreat_to_distance
# ---------------------------------------------------------------------------

class TestCanRetreatToDistance:
    def test_finds_safe_square_in_open(self):
        bf = Battlefield(width=20, height=20)
        archer = make_creature("archer", movement=8)
        threat = make_creature("threat", movement=6)
        bf.register(archer, (10, 10))
        bf.register(threat, (8, 10))   # 2 away
        dest = can_retreat_to_distance(archer, threat,
                                       target_distance=10, battlefield=bf)
        assert dest is not None
        from combat_sim.geometry import chebyshev
        # within archer's 8-square movement budget...
        assert chebyshev(dest, (10, 10)) <= 8
        # ...and at least 10 squares from threat
        assert chebyshev(dest, (8, 10)) >= 10

    def test_returns_none_when_cornered(self):
        """Archer in a 1-wide corner has nowhere to retreat to."""
        bf = Battlefield(width=20, height=20,
                        blocked={(0, 1), (1, 0), (1, 1)})
        archer = make_creature("archer", movement=8)
        threat = make_creature("threat", movement=6)
        bf.register(archer, (0, 0))
        bf.register(threat, (5, 5))
        # archer must reach distance >= 30 but is walled in at (0,0)
        dest = can_retreat_to_distance(archer, threat,
                                       target_distance=30, battlefield=bf)
        assert dest is None

    def test_returns_none_when_threat_too_close_and_too_fast(self):
        """If even the farthest reachable square doesn't put enough
        distance between us, return None (cornered-by-speed)."""
        bf = Battlefield(width=5, height=5)
        archer = make_creature("archer", movement=2)
        threat = make_creature("threat", movement=10)
        bf.register(archer, (2, 2))
        bf.register(threat, (2, 2 + 1))  # adjacent
        # Archer can move 2; can't get >5 away from threat on a 5x5 map.
        dest = can_retreat_to_distance(archer, threat,
                                       target_distance=10, battlefield=bf)
        assert dest is None


# ---------------------------------------------------------------------------
# threat_can_close_to_melee  (KitingAI lookahead)
# ---------------------------------------------------------------------------

class TestThreatCanCloseToMelee:
    def test_threat_in_range_closes(self):
        bf = Battlefield(width=20, height=20)
        threat = make_creature("threat", movement=8)
        bf.register(threat, (0, 0))
        # Target at (8,8) — threat moves 8 diagonal squares to be adjacent.
        # Adjacency = Chebyshev 1, so threat must reach (7,7) or similar.
        assert threat_can_close_to_melee(threat, (8, 8), bf)

    def test_threat_out_of_reach(self):
        bf = Battlefield(width=30, height=30)
        threat = make_creature("threat", movement=4)
        bf.register(threat, (0, 0))
        # Target far away
        assert not threat_can_close_to_melee(threat, (20, 20), bf)

    def test_threat_blocked_by_wall(self):
        """Threat is close in Chebyshev distance but a wall makes
        pathing impossible within one round."""
        # 1-wide corridor blocked by walls everywhere
        bf = Battlefield(width=20, height=5,
                        blocked={(x, y) for x in range(20) for y in (0, 1, 3, 4)
                                if x != 0})  # only (0,*) and (*, 2) passable
        # Simpler: cage the threat fully
        bf2 = Battlefield(width=10, height=10,
                         blocked={(1, 0), (0, 1), (1, 1)})
        threat = make_creature("threat", movement=8)
        bf2.register(threat, (0, 0))
        # Trapped — even with movement=8, cannot leave the corner
        assert not threat_can_close_to_melee(threat, (5, 5), bf2)
