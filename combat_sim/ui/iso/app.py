"""IsoApp — the pygame main loop, and ``run_iso_game`` the CLI entry.

The main thread owns pygame (init, window, event loop, drawing). A
daemon worker thread runs ``run_game`` against the :class:`IsoFrontend`;
the two communicate only through the frontend's thread-safe surface.

Click resolution priority on a human turn: side-panel button → enemy
token (attack) → highlighted tile (move). All choices are pre-resolved
to ``Action`` objects by the frontend, so this loop never touches sim
logic.
"""

from __future__ import annotations
import threading
from typing import TYPE_CHECKING, Optional

import pygame

from ..game import run_game
from . import render
from .render import Layout
from .isogeometry import screen_to_tile
from .widgets import stack_buttons, button_at, Button

if TYPE_CHECKING:
    from .frontend import IsoFrontend
    from ..registry import Registry
    from ..frontend import Frontend

WINDOW_W, WINDOW_H = 1280, 760
FPS = 60
_PANEL_TOP = 52


class IsoApp:
    def __init__(self, iso_frontend: "IsoFrontend",
                 game_frontend: "Frontend", registry: "Registry",
                 *, seed: Optional[int] = None) -> None:
        self.iso = iso_frontend
        self.game_frontend = game_frontend
        self.registry = registry
        self.seed = seed
        self._worker: Optional[threading.Thread] = None
        self._error: Optional[BaseException] = None

    # ------------------------------------------------------------------

    def _run_worker(self) -> None:
        try:
            run_game(self.game_frontend, self.registry, seed=self.seed)
        except (KeyboardInterrupt, EOFError):
            pass  # window closed mid-fight; just unwind
        except BaseException as exc:  # surface sim crashes to the main loop
            self._error = exc

    def _layout_buttons(self, request, lo: Layout) -> list[Button]:
        if request is None:
            return []
        return stack_buttons(list(request.buttons),
                             panel_x=lo.panel_x, panel_top=_PANEL_TOP,
                             panel_w=lo.panel_w)

    def _handle_click(self, pos, request, buttons: list[Button],
                      lo: Layout) -> None:
        if request is None:
            return
        b = button_at(buttons, pos)
        if b is not None:
            self.iso.submit_action(b.action)
            return
        tile = screen_to_tile(pos[0], pos[1], lo.origin, lo.tile_w, lo.tile_h)
        if tile in request.attack_targets:
            self.iso.submit_action(request.attack_targets[tile])
        elif tile in request.move_targets:
            self.iso.submit_action(request.move_targets[tile])

    # ------------------------------------------------------------------

    def run(self) -> int:
        pygame.init()
        pygame.display.set_caption("Vogelfrei — Combat")
        screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        fonts = {
            "small": pygame.font.SysFont(None, 22),
            "big": pygame.font.SysFont(None, 30),
        }
        clock = pygame.time.Clock()

        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

        running = True
        while running:
            board = self.iso.snapshot()
            request = self.iso.pending_request()
            phase = self.iso.phase
            result = self.iso.result

            lo = render.compute_layout(board, WINDOW_W, WINDOW_H) \
                if board is not None else None
            buttons = self._layout_buttons(request, lo) if lo else []

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif phase == "done" and event.type in (
                        pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    running = False
                elif (event.type == pygame.MOUSEBUTTONDOWN
                      and event.button == 1 and lo is not None):
                    self._handle_click(event.pos, request, buttons, lo)

            mouse = pygame.mouse.get_pos()
            if board is None or phase == "setup":
                render.draw_setup(screen, fonts)
            else:
                render.draw_frame(screen, fonts, board, request, buttons, lo,
                                  mouse, result if phase == "done" else None)
            pygame.display.flip()
            clock.tick(FPS)

        # Shut down: unblock the worker if it's waiting on a decision.
        self.iso.abort()
        if self._worker is not None:
            self._worker.join(timeout=1.0)
        pygame.quit()

        if self._error is not None:
            raise self._error
        return 0


def run_iso_game(iso_frontend: "IsoFrontend", game_frontend: "Frontend",
                 registry: "Registry", *,
                 seed: Optional[int] = None) -> int:
    """Wire the app and run it. ``iso_frontend`` holds the shared render
    state; ``game_frontend`` is what ``run_game`` drives (the iso
    frontend itself, or a preset wrapper around it)."""
    return IsoApp(iso_frontend, game_frontend, registry, seed=seed).run()
