"""Isometric tile <-> screen projection. Pure math, no pygame import.

The board is a grid of (x, y) tile coordinates. We project to a 2:1
isometric diamond: moving +x goes down-right, +y goes down-left. The
``origin`` is the screen pixel at the *centre* of tile (0, 0).

Kept dependency-free so it can be unit-tested headless and so the
mouse-picking inverse stays trivially checkable.

    sx = ox + (x - y) * (tile_w / 2)
    sy = oy + (x + y) * (tile_h / 2)
"""

from __future__ import annotations

Point = tuple[float, float]
Tile = tuple[int, int]


def tile_to_screen(x: int, y: int, origin: Point,
                   tile_w: int, tile_h: int) -> tuple[int, int]:
    """Centre pixel of tile (x, y)."""
    ox, oy = origin
    sx = ox + (x - y) * (tile_w / 2)
    sy = oy + (x + y) * (tile_h / 2)
    return int(round(sx)), int(round(sy))


def screen_to_tile(sx: float, sy: float, origin: Point,
                   tile_w: int, tile_h: int) -> Tile:
    """Inverse of :func:`tile_to_screen` — the tile under a pixel.

    Rounds to the nearest tile centre. Callers should bounds-check the
    result against the board; this does not.
    """
    ox, oy = origin
    dx = (sx - ox) / (tile_w / 2)   # == (x - y)
    dy = (sy - oy) / (tile_h / 2)   # == (x + y)
    x = (dx + dy) / 2
    y = (dy - dx) / 2
    return int(round(x)), int(round(y))


def diamond_points(x: int, y: int, origin: Point,
                   tile_w: int, tile_h: int) -> list[tuple[int, int]]:
    """The four corner pixels of tile (x, y), clockwise from the top.
    Suitable for ``pygame.draw.polygon`` and point-in-polygon tests."""
    cx, cy = tile_to_screen(x, y, origin, tile_w, tile_h)
    hw, hh = tile_w // 2, tile_h // 2
    return [
        (cx, cy - hh),   # top
        (cx + hw, cy),   # right
        (cx, cy + hh),   # bottom
        (cx - hw, cy),   # left
    ]


def board_origin(board_w: int, board_h: int, screen_w: int, top_margin: int,
                 tile_w: int, tile_h: int) -> Point:
    """Pick an ``origin`` that centres the whole board horizontally and
    sits it ``top_margin`` pixels down.

    The leftmost pixel of the diamond layout is tile (0, board_h-1)'s
    left corner; the rightmost is tile (board_w-1, 0)'s right corner.
    Centre the span, and drop the top tile (0,0) below the margin.
    """
    # Horizontal extent spans (board_w + board_h) half-widths.
    total_w = (board_w + board_h) * (tile_w / 2)
    ox = (screen_w - total_w) / 2 + board_h * (tile_w / 2)
    oy = top_margin + tile_h / 2
    return ox, oy
