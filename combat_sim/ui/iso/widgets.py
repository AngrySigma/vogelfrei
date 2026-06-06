"""Button geometry and hit-testing — no pygame, just rectangles.

Kept separate from drawing so layout and click-resolution are pure and
unit-testable. ``render.py`` reads these rects to draw; ``app.py`` reads
them to resolve clicks into actions.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...actions import Action

Rect = tuple[int, int, int, int]  # (x, y, w, h)


@dataclass(frozen=True)
class Button:
    label: str
    action: "Action"
    rect: Rect

    def hit(self, pos: tuple[int, int]) -> bool:
        px, py = pos
        x, y, w, h = self.rect
        return x <= px <= x + w and y <= py <= y + h


def stack_buttons(labelled_actions: list[tuple[str, "Action"]],
                  *, panel_x: int, panel_top: int, panel_w: int,
                  btn_h: int = 34, gap: int = 8,
                  pad: int = 12) -> list[Button]:
    """Lay out a vertical stack of buttons down the side panel.

    Returns one ``Button`` per (label, action), top to bottom.
    """
    out: list[Button] = []
    x = panel_x + pad
    w = panel_w - 2 * pad
    y = panel_top
    for label, action in labelled_actions:
        out.append(Button(label=label, action=action, rect=(x, y, w, btn_h)))
        y += btn_h + gap
    return out


def button_at(buttons: list[Button], pos: tuple[int, int]) -> "Button | None":
    """First button whose rect contains ``pos`` (top-most wins)."""
    for b in buttons:
        if b.hit(pos):
            return b
    return None
