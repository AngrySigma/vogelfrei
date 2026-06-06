"""Immutable view-models the renderer consumes.

The worker thread (running the sim) builds these at safe points between
actions and hands them to the main render thread. Because they are
plain snapshots of primitive values — never live ``Creature`` objects —
the render thread can read them without racing the worker's mutations.

Nothing here imports pygame; it's all data + one read-only helper.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...actions import Action
    from ...combat import CombatContext
    from ...creatures import Creature

Tile = tuple[int, int]


@dataclass(frozen=True)
class TokenView:
    """One creature as the renderer sees it."""
    name: str
    x: int
    y: int
    side: str            # "A" or "B"
    wounds: int
    wounds_max: int
    stamina: int
    stamina_max: int
    is_monster: bool
    is_down: bool        # wounds <= 0 (prone / unconscious), still on field
    is_active: bool      # whose turn it is right now


@dataclass(frozen=True)
class BoardView:
    """A complete, render-ready picture of the battlefield."""
    width: int
    height: int
    blocked: frozenset[Tile]
    tokens: tuple[TokenView, ...]
    round_no: int


@dataclass(frozen=True)
class DecisionRequest:
    """What the player is being asked, with every choice pre-resolved to
    a concrete ``Action`` so the render thread never touches sim logic.

    - ``buttons``: ordered (label, action) pairs for the side panel.
    - ``move_targets``: tile -> MoveAction for each clickable destination.
    - ``attack_targets``: tile -> AttackAction for each clickable enemy.
    """
    actor_name: str
    kind: str                                   # "action" | "reaction"
    buttons: tuple[tuple[str, "Action"], ...]
    move_targets: dict[Tile, "Action"] = field(default_factory=dict)
    attack_targets: dict[Tile, "Action"] = field(default_factory=dict)


def _side_of(creature: "Creature", ctx: "CombatContext") -> str:
    return "A" if creature in ctx.engagement.a.members else "B"


def snapshot_board(ctx: "CombatContext",
                   active: Optional["Creature"] = None) -> BoardView:
    """Read the live engagement and freeze it into a ``BoardView``.

    Called from the worker thread inside render hooks / prompts, where
    the board is in a consistent between-actions state.
    """
    from ...creatures import Monster

    eng = ctx.engagement
    bf = eng.battlefield
    width = bf.width if bf is not None else 0
    height = bf.height if bf is not None else 0
    blocked = frozenset(bf.blocked) if bf is not None else frozenset()

    tokens: list[TokenView] = []
    for side, party in (("A", eng.a), ("B", eng.b)):
        for c in party.members:
            if c.position is None:
                continue  # dead creatures are deregistered (no position)
            tokens.append(TokenView(
                name=c.name,
                x=c.position[0],
                y=c.position[1],
                side=side,
                wounds=c.wounds,
                wounds_max=c.wounds_max,
                stamina=c.stamina(),
                stamina_max=getattr(c, "stamina_max", 0),
                is_monster=isinstance(c, Monster),
                is_down=not c.is_combat_capable,
                is_active=(c is active),
            ))

    return BoardView(
        width=width,
        height=height,
        blocked=blocked,
        tokens=tuple(tokens),
        round_no=ctx.round_no,
    )
