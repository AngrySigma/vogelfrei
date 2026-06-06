"""Pure grid math — no imports from anywhere in combat_sim, no state.

Every other module that touches coordinates routes through here so the
geometry choice (8-way Chebyshev, 5 ft per square) lives in exactly one
place.
"""

from __future__ import annotations


FT_PER_SQUARE: int = 5


def chebyshev(p1: tuple[int, int], p2: tuple[int, int]) -> int:
    """Distance in squares for 8-way movement. Diagonal = 1."""
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))


def sign(n: int) -> int:
    """-1, 0, or +1 — the direction component for one axis."""
    if n < 0:
        return -1
    if n > 0:
        return 1
    return 0


def ideal_step(from_pos: tuple[int, int],
              to_pos: tuple[int, int]) -> tuple[int, int]:
    """One square from ``from_pos`` in the best direction toward ``to_pos``.

    Greedy: take the diagonal if both axes need movement, otherwise the
    straight step. Returns ``from_pos`` itself when already there.
    """
    dx = sign(to_pos[0] - from_pos[0])
    dy = sign(to_pos[1] - from_pos[1])
    return (from_pos[0] + dx, from_pos[1] + dy)


def cardinal_alternatives(from_pos: tuple[int, int],
                         to_pos: tuple[int, int]) -> list[tuple[int, int]]:
    """Single-axis fallback steps when the ideal diagonal is blocked.

    For a diagonal target, returns the two cardinal steps that still make
    progress toward ``to_pos``. For a pure cardinal target, returns []
    (the only fallback would be perpendicular, which is not "toward").
    """
    dx = sign(to_pos[0] - from_pos[0])
    dy = sign(to_pos[1] - from_pos[1])
    if dx == 0 or dy == 0:
        return []
    return [
        (from_pos[0] + dx, from_pos[1]),
        (from_pos[0],      from_pos[1] + dy),
    ]
