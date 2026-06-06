"""All pygame drawing for the iso view. Imports pygame.

Pure presentation: given a :class:`BoardView`, an optional
:class:`DecisionRequest`, and the laid-out buttons, paint a frame. No
sim logic, no threading — the caller (``IsoApp``) owns those.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import pygame

from . import isogeometry as iso
from .widgets import Button

if TYPE_CHECKING:
    from .snapshot import BoardView, DecisionRequest, TokenView
    from ...combat import CombatResult


# -- palette ----------------------------------------------------------------
BG = (22, 23, 28)
FLOOR_A = (58, 64, 72)
FLOOR_B = (50, 56, 64)
WALL = (32, 33, 40)
WALL_TOP = (44, 46, 56)
MOVE_HL = (66, 120, 92)
ATTACK_HL = (150, 64, 60)
SIDE_A = (88, 142, 224)
SIDE_B = (214, 92, 80)
MONSTER_TINT = (40, 30, 20)
ACTIVE_RING = (244, 212, 84)
DOWN = (96, 96, 102)
HP_BG = (40, 16, 16)
HP_FG = (96, 200, 96)
ST_FG = (90, 150, 230)
PANEL = (30, 31, 38)
PANEL_LINE = (60, 62, 72)
BTN = (58, 62, 78)
BTN_HOVER = (78, 84, 104)
TEXT = (228, 230, 236)
TEXT_DIM = (150, 154, 164)


@dataclass(frozen=True)
class Layout:
    tile_w: int
    tile_h: int
    origin: tuple[float, float]
    panel_x: int
    panel_w: int
    screen_w: int
    screen_h: int
    top_margin: int = 64


def compute_layout(board: "BoardView", screen_w: int, screen_h: int) -> Layout:
    """Fit the board into the area left of the side panel."""
    panel_w = 300
    panel_x = screen_w - panel_w
    area_w = panel_x - 24
    top_margin = 56
    area_h = screen_h - top_margin - 24

    span = max(1, board.width + board.height)
    # 2:1 iso: tile_h == tile_w / 2. Fit both axes, cap at a sane size.
    tw_for_w = (2 * area_w) // span
    tw_for_h = (4 * area_h) // span   # height span uses th = tw/2
    tile_w = max(16, min(56, tw_for_w, tw_for_h))
    tile_h = max(8, tile_w // 2)

    origin = iso.board_origin(board.width, board.height, panel_x,
                              top_margin, tile_w, tile_h)
    return Layout(tile_w=tile_w, tile_h=tile_h, origin=origin,
                  panel_x=panel_x, panel_w=panel_w,
                  screen_w=screen_w, screen_h=screen_h,
                  top_margin=top_margin)


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------

def _draw_tiles(screen, board: "BoardView", lo: Layout) -> None:
    for y in range(board.height):
        for x in range(board.width):
            pts = iso.diamond_points(x, y, lo.origin, lo.tile_w, lo.tile_h)
            if (x, y) in board.blocked:
                pygame.draw.polygon(screen, WALL_TOP, pts)
                pygame.draw.polygon(screen, WALL, pts, 2)
            else:
                colour = FLOOR_A if (x + y) % 2 == 0 else FLOOR_B
                pygame.draw.polygon(screen, colour, pts)
                pygame.draw.polygon(screen, BG, pts, 1)


def _draw_highlights(screen, request: "DecisionRequest", lo: Layout) -> None:
    surf = pygame.Surface((lo.screen_w, lo.screen_h), pygame.SRCALPHA)
    for tile in request.move_targets:
        pts = iso.diamond_points(tile[0], tile[1], lo.origin,
                                 lo.tile_w, lo.tile_h)
        pygame.draw.polygon(surf, (*MOVE_HL, 90), pts)
        pygame.draw.polygon(surf, (*MOVE_HL, 200), pts, 2)
    for tile in request.attack_targets:
        pts = iso.diamond_points(tile[0], tile[1], lo.origin,
                                 lo.tile_w, lo.tile_h)
        pygame.draw.polygon(surf, (*ATTACK_HL, 120), pts)
        pygame.draw.polygon(surf, (*ATTACK_HL, 230), pts, 2)
    screen.blit(surf, (0, 0))


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def _draw_token(screen, fonts, tok: "TokenView", lo: Layout) -> None:
    cx, cy = iso.tile_to_screen(tok.x, tok.y, lo.origin, lo.tile_w, lo.tile_h)
    r = max(6, int(lo.tile_h * 0.7))
    top = cy - r  # lift the body so it stands on the tile

    base = SIDE_A if tok.side == "A" else SIDE_B
    body = DOWN if tok.is_down else base

    if tok.is_active:
        pygame.draw.circle(screen, ACTIVE_RING, (cx, top), r + 5, 3)

    if tok.is_monster:
        # diamond body to read as "not a humanoid"
        pts = [(cx, top - r), (cx + r, top), (cx, top + r), (cx - r, top)]
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, MONSTER_TINT, pts, 2)
    else:
        pygame.draw.circle(screen, body, (cx, top), r)
        pygame.draw.circle(screen, (12, 12, 16), (cx, top), r, 2)

    initial = (tok.name[:1] or "?").upper()
    label = fonts["small"].render(initial, True, TEXT)
    screen.blit(label, (cx - label.get_width() // 2,
                        top - label.get_height() // 2))

    _draw_bars(screen, tok, cx, top - r - 10, r)


def _draw_bars(screen, tok: "TokenView", cx: int, y: int, r: int) -> None:
    w = max(20, r * 2)
    x = cx - w // 2
    # wounds
    frac = 0.0 if tok.wounds_max <= 0 else max(0.0, tok.wounds / tok.wounds_max)
    pygame.draw.rect(screen, HP_BG, (x, y, w, 4))
    pygame.draw.rect(screen, HP_FG, (x, y, int(w * frac), 4))
    # stamina (characters only)
    if tok.stamina_max > 0:
        sfrac = max(0.0, tok.stamina / tok.stamina_max)
        pygame.draw.rect(screen, HP_BG, (x, y + 5, w, 3))
        pygame.draw.rect(screen, ST_FG, (x, y + 5, int(w * sfrac), 3))


def _draw_tokens(screen, fonts, board: "BoardView", lo: Layout) -> None:
    # Painter's order: smaller (x+y) is "further back", draw first.
    for tok in sorted(board.tokens, key=lambda t: (t.x + t.y, t.y)):
        _draw_token(screen, fonts, tok, lo)


# ---------------------------------------------------------------------------
# Panel + chrome
# ---------------------------------------------------------------------------

def _draw_header(screen, fonts, board: "BoardView",
                 request: Optional["DecisionRequest"], lo: Layout) -> None:
    txt = f"Round {board.round_no}"
    if request is not None:
        verb = "reacts" if request.kind == "reaction" else "to act"
        txt += f"   —   {request.actor_name} {verb}"
    screen.blit(fonts["big"].render(txt, True, TEXT), (24, 16))


def _draw_panel(screen, fonts, buttons: list[Button],
                request: Optional["DecisionRequest"],
                mouse: tuple[int, int], lo: Layout) -> None:
    pygame.draw.rect(screen, PANEL, (lo.panel_x, 0, lo.panel_w, lo.screen_h))
    pygame.draw.line(screen, PANEL_LINE, (lo.panel_x, 0),
                     (lo.panel_x, lo.screen_h), 2)

    title = "Actions" if request is not None else "Waiting…"
    screen.blit(fonts["big"].render(title, True, TEXT),
                (lo.panel_x + 12, 16))

    if request is None:
        hint = fonts["small"].render("AI is taking its turn.", True, TEXT_DIM)
        screen.blit(hint, (lo.panel_x + 12, 52))
        return

    for b in buttons:
        x, y, w, h = b.rect
        hot = b.hit(mouse)
        pygame.draw.rect(screen, BTN_HOVER if hot else BTN, b.rect,
                         border_radius=6)
        pygame.draw.rect(screen, PANEL_LINE, b.rect, 1, border_radius=6)
        label = fonts["small"].render(b.label, True, TEXT)
        screen.blit(label, (x + 10, y + (h - label.get_height()) // 2))

    tip = fonts["small"].render("Click a green tile to move, red to attack.",
                                True, TEXT_DIM)
    screen.blit(tip, (lo.panel_x + 12, lo.screen_h - 32))


def _draw_overlay(screen, fonts, result: "CombatResult", lo: Layout) -> None:
    veil = pygame.Surface((lo.screen_w, lo.screen_h), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 150))
    screen.blit(veil, (0, 0))
    winner = result.winner or "Draw (round limit)"
    lines = [f"Combat over after {result.rounds} round(s)",
             f"Winner: {winner}",
             "Press any key or close the window."]
    cy = lo.screen_h // 2 - 40
    for i, line in enumerate(lines):
        font = fonts["big"] if i == 1 else fonts["small"]
        surf = font.render(line, True, TEXT)
        screen.blit(surf, ((lo.screen_w - surf.get_width()) // 2, cy + i * 36))


# ---------------------------------------------------------------------------
# Top-level frame
# ---------------------------------------------------------------------------

def draw_setup(screen, fonts) -> None:
    screen.fill(BG)
    lines = ["Setting up the battle…",
             "Answer the prompts in your terminal."]
    cy = screen.get_height() // 2 - 30
    for i, line in enumerate(lines):
        font = fonts["big"] if i == 0 else fonts["small"]
        surf = font.render(line, True, TEXT if i == 0 else TEXT_DIM)
        screen.blit(surf, ((screen.get_width() - surf.get_width()) // 2,
                           cy + i * 40))


def draw_frame(screen, fonts, board: "BoardView",
               request: Optional["DecisionRequest"], buttons: list[Button],
               lo: Layout, mouse: tuple[int, int],
               result: "Optional[CombatResult]" = None) -> None:
    screen.fill(BG)
    _draw_tiles(screen, board, lo)
    if request is not None:
        _draw_highlights(screen, request, lo)
    _draw_tokens(screen, fonts, board, lo)
    _draw_header(screen, fonts, board, request, lo)
    _draw_panel(screen, fonts, buttons, request, mouse, lo)
    if result is not None:
        _draw_overlay(screen, fonts, result, lo)
