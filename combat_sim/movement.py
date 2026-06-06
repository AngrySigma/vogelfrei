"""Movement helpers built on top of geometry + battlefield.

Two layers:

  1. Search primitives — ``find_path`` (A*) and ``reachable_within``
     (BFS). Pure: take positions, return paths / cost maps. No
     creature-state mutation.

  2. AI-facing helpers — ``walk_toward``, ``can_retreat_to_distance``,
     ``threat_can_close_to_melee``. Built on the primitives. Also pure
     — they compute destinations the combat layer then applies via
     ``Creature.move_to``.

Plus ``validate_move`` — the defensive gate the combat layer (and a
future interactive UI) calls before accepting any user-supplied
``MoveAction`` destination.
"""

from __future__ import annotations
import heapq
import itertools
from collections import deque
from typing import TYPE_CHECKING, Optional

from .geometry import chebyshev

if TYPE_CHECKING:
    from .creatures import Creature
    from .battlefield import Battlefield


# Eight Chebyshev neighbour offsets.
_NEIGHBOURS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
              if not (dx == 0 and dy == 0)]


# ---------------------------------------------------------------------------
# A* shortest path
# ---------------------------------------------------------------------------

def find_path(start: tuple[int, int],
             goal: tuple[int, int],
             battlefield: "Battlefield",
             *, ignoring: Optional["Creature"] = None,
             stop_distance: int = 0) -> Optional[list[tuple[int, int]]]:
    """A* shortest path from ``start`` to a square within
    ``stop_distance`` Chebyshev squares of ``goal``.

    ``stop_distance=0`` (default) requires the path to end exactly on
    ``goal``. ``stop_distance=1`` is the "move into melee" case — stop
    on any square adjacent to ``goal``.

    Returns the path as a list of squares including both endpoints, or
    ``None`` if no path exists. The path length is
    ``len(path) - 1`` steps.

    Heuristic is Chebyshev distance, which is admissible (and exact) for
    8-way movement with uniform cost 1, so A* returns the optimal path.
    """
    if chebyshev(start, goal) <= stop_distance:
        return [start]

    # Heap entries: (f_score, tie_breaker, position)
    tie = itertools.count()
    open_heap: list[tuple[int, int, tuple[int, int]]] = [
        (chebyshev(start, goal), next(tie), start)
    ]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], int] = {start: 0}

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if chebyshev(current, goal) <= stop_distance:
            return _reconstruct(came_from, current)

        for dx, dy in _NEIGHBOURS:
            neighbour = (current[0] + dx, current[1] + dy)
            if not battlefield.is_passable(neighbour, ignoring=ignoring):
                continue
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbour, 10**9):
                came_from[neighbour] = current
                g_score[neighbour] = tentative_g
                f = tentative_g + chebyshev(neighbour, goal)
                heapq.heappush(open_heap, (f, next(tie), neighbour))

    return None


def _reconstruct(came_from: dict[tuple[int, int], tuple[int, int]],
                end: tuple[int, int]) -> list[tuple[int, int]]:
    path = [end]
    while end in came_from:
        end = came_from[end]
        path.append(end)
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# BFS for "all squares I can reach within N steps"
# ---------------------------------------------------------------------------

def reachable_within(start: tuple[int, int],
                    max_squares: int,
                    battlefield: "Battlefield",
                    *, ignoring: Optional["Creature"] = None) \
        -> dict[tuple[int, int], int]:
    """Map every square reachable from ``start`` within ``max_squares``
    steps to its minimum step cost.

    Used by:
      * ``walk_toward`` to pick the closest reachable square to a target
      * ``can_retreat_to_distance`` to enumerate retreat candidates
      * ``threat_can_close_to_melee`` for the kiting lookahead
      * ``validate_move`` to gate user-supplied destinations
      * (future) the interactive UI to highlight clickable squares

    Uniform step cost (1) → plain deque BFS. Passability check is
    inlined for speed; this routine is called many times per round in
    kiting scenarios and was a measurable hot spot.
    """
    width = battlefield.width
    height = battlefield.height
    blocked = battlefield.blocked
    occupancy = battlefield._occupancy

    visited: dict[tuple[int, int], int] = {start: 0}
    frontier: deque[tuple[int, int]] = deque([start])
    while frontier:
        current = frontier.popleft()
        cost = visited[current]
        if cost >= max_squares:
            continue
        new_cost = cost + 1
        cx, cy = current
        for dx, dy in _NEIGHBOURS:
            nx, ny = cx + dx, cy + dy
            neighbour = (nx, ny)
            if neighbour in visited:
                continue
            # Inlined is_passable
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if neighbour in blocked:
                continue
            occ = occupancy.get(neighbour)
            if occ is not None and occ is not ignoring:
                continue
            visited[neighbour] = new_cost
            frontier.append(neighbour)
    return visited


# ---------------------------------------------------------------------------
# Validation for user-supplied move destinations
# ---------------------------------------------------------------------------

def validate_move(actor: "Creature",
                 destination: tuple[int, int],
                 battlefield: "Battlefield") -> bool:
    """True if ``actor`` can legally move to ``destination`` this round.

    Checks:
      * destination is in bounds, not terrain-blocked, not occupied
        (by anyone other than the actor itself)
      * a path of length <= ``actor.movement_squares`` exists

    Implementation uses ``reachable_within`` (BFS bounded by movement
    budget) rather than full A* — much cheaper on large open maps, and
    correct because we only ever validate destinations within budget.

    This is the gate the combat layer applies to *any* ``MoveAction``,
    whether it came from an AI or from an interactive player click.
    The UI can also call this to grey out illegal squares before the
    player commits.
    """
    if actor.position is None:
        return False
    if not battlefield.is_passable(destination, ignoring=actor):
        return False
    reach = reachable_within(actor.position, actor.movement_squares,
                            battlefield, ignoring=actor)
    return destination in reach


# ---------------------------------------------------------------------------
# AI-facing movement helpers
# ---------------------------------------------------------------------------

def step_toward(from_pos: tuple[int, int],
               to_pos: tuple[int, int],
               battlefield: "Battlefield",
               *, ignoring: Optional["Creature"] = None) \
        -> Optional[tuple[int, int]]:
    """First square along the A*-optimal path from ``from_pos`` to
    ``to_pos``. Returns the destination itself if it is one step away.
    Returns ``None`` when no path exists (truly stuck).
    """
    if from_pos == to_pos:
        return from_pos
    path = find_path(from_pos, to_pos, battlefield,
                    ignoring=ignoring, stop_distance=0)
    if path is None or len(path) < 2:
        return None
    return path[1]


def walk_toward(creature: "Creature",
               target_pos: tuple[int, int],
               max_squares: int,
               battlefield: "Battlefield",
               *, stop_distance: int = 1) -> tuple[int, int]:
    """Pick a destination within ``max_squares`` steps that lands at
    Chebyshev distance ``stop_distance`` from ``target_pos`` if possible,
    otherwise the closest reachable square.

    ``stop_distance=1`` is the standard "walk into melee" case — stop
    adjacent, not on top of the target. ``stop_distance=0`` aims to
    land exactly on the target (used for retreating to a chosen square).

    Implementation: BFS bounded to the movement budget — O(k^2) where
    k is movement_squares. Replaced full A* here because A* with the
    Chebyshev heuristic explores many tied-f nodes on open fields and
    became the dominant cost in kiting scenarios.
    """
    if creature.position is None:
        return creature.position
    start = creature.position
    if chebyshev(start, target_pos) <= stop_distance:
        return start  # already close enough; don't move

    reach = reachable_within(start, max_squares, battlefield,
                            ignoring=creature)

    # Prefer squares that respect stop_distance — landing closer than
    # stop_distance is "overshooting" (e.g. stepping onto the target).
    valid = [(chebyshev(sq, target_pos), cost, sq)
             for sq, cost in reach.items()
             if chebyshev(sq, target_pos) >= stop_distance]
    if valid:
        valid.sort()
        return valid[0][2]

    # No square within budget satisfies stop_distance — return closest
    # reachable to target. This branch is rare; happens when the actor
    # is so close that every reachable square is "inside" stop_distance.
    best = start
    best_key = (chebyshev(start, target_pos), 0)
    for sq, cost in reach.items():
        key = (chebyshev(sq, target_pos), cost)
        if key < best_key:
            best = sq
            best_key = key
    return best


def can_retreat_to_distance(creature: "Creature",
                           threat: "Creature",
                           *, target_distance: int,
                           battlefield: "Battlefield") \
        -> Optional[tuple[int, int]]:
    """Find a square within the creature's movement budget that puts it
    at least ``target_distance`` Chebyshev squares from ``threat``.

    Returns the *farthest* such square so subsequent rounds have room,
    or ``None`` if no reachable square satisfies the constraint.
    """
    if creature.position is None or threat.position is None:
        return None
    reachable = reachable_within(creature.position,
                                creature.movement_squares,
                                battlefield, ignoring=creature)
    threat_pos = threat.position
    best: Optional[tuple[int, int]] = None
    best_dist = -1
    for sq in reachable:
        dist = chebyshev(sq, threat_pos)
        if dist >= target_distance and dist > best_dist:
            best = sq
            best_dist = dist
    return best


def threat_can_close_to_melee(threat: "Creature",
                             target_pos: tuple[int, int],
                             battlefield: "Battlefield") -> bool:
    """Will ``threat`` be in melee with a creature at ``target_pos``
    after using its full movement budget next round?

    BFS within budget; if any reachable square is adjacent to the target,
    the answer is yes. Correct because BFS within budget exhaustively
    enumerates reachable squares.
    """
    if threat.position is None:
        return False
    if chebyshev(threat.position, target_pos) <= 1:
        return True
    reach = reachable_within(threat.position, threat.movement_squares,
                            battlefield, ignoring=threat)
    return any(chebyshev(sq, target_pos) <= 1 for sq in reach)
