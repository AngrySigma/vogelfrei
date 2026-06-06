"""ASCII rendering for the terminal frontend.

Single-purpose: convert combat state into strings. No I/O here — the
frontend calls these and decides when to ``print``. Keeps the visual
language in one place so a future restyle is local.

Conventions:
    creatures are drawn with the first letter of their name, uppercase
    for party A, lowercase for party B
    walls are '#', open squares '.'
    columns are shown above the grid in two rows (tens / units) when
    the map is wider than 10
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...combat import CombatContext
    from ...creatures import Creature
    from ...party import Party
    from ...battlefield import Battlefield


WALL_CHAR = "#"
OPEN_CHAR = "."
DEAD_CHAR = "."        # bodies are deregistered, so dead squares are open


# ---------------------------------------------------------------------------
# Map rendering
# ---------------------------------------------------------------------------

def render_grid(bf: "Battlefield",
                party_a: "Party",
                party_b: "Party") -> str:
    """Return a multi-line string showing the battlefield with column
    and row numbers. Creatures appear as letters keyed to their party."""
    # Build the symbol grid first
    grid: list[list[str]] = [
        [OPEN_CHAR for _ in range(bf.width)]
        for _ in range(bf.height)
    ]
    for (x, y) in bf.blocked:
        if 0 <= x < bf.width and 0 <= y < bf.height:
            grid[y][x] = WALL_CHAR

    # Creatures: A side uppercase, B side lowercase. Use first letter
    # of the name; fall back to '?' for empty names.
    def symbol(c: "Creature", upper: bool) -> str:
        s = (c.name[:1] or "?")
        return s.upper() if upper else s.lower()

    for c in party_a.members:
        if c.position is not None:
            x, y = c.position
            grid[y][x] = symbol(c, upper=True)
    for c in party_b.members:
        if c.position is not None:
            x, y = c.position
            grid[y][x] = symbol(c, upper=False)

    return _format_grid_with_axes(grid, bf.width, bf.height)


def _format_grid_with_axes(grid: list[list[str]],
                          width: int, height: int) -> str:
    lines: list[str] = []
    # Column header — two rows if width >= 10 (tens digits on top)
    if width >= 10:
        top = "    " + " ".join(
            (str(i // 10) if i >= 10 else " ") for i in range(width)
        )
        lines.append(top)
    bottom = "    " + " ".join(str(i % 10) for i in range(width))
    lines.append(bottom)
    # Row separator
    lines.append("   +" + "-" * (2 * width))
    # Body
    for y in range(height):
        row = " ".join(grid[y])
        lines.append(f"{y:2d} | {row}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Status panes
# ---------------------------------------------------------------------------

def render_party_status(party: "Party", *, label: str) -> str:
    lines = [f"{label}: {party.name}"]
    for c in party.members:
        lines.append(f"  {_creature_status_line(c)}")
    return "\n".join(lines)


def _creature_status_line(c: "Creature") -> str:
    from ...creatures import Character, Monster
    if not c.is_alive:
        return f"{c.name}  [dead]"
    if not c.is_combat_capable:
        return f"{c.name}  [down] wounds={c.wounds}"
    pos = f"@{c.position}" if c.position is not None else ""
    base = f"{c.name} {pos}".strip()
    if isinstance(c, Character):
        stamina_str = f"S:{c.stamina_current}/{c.stamina_max}"
    else:
        stamina_str = ""
    wounds_str = f"W:{c.wounds}/{c.wounds_max}"
    weapon = c.weapon.name if c.weapon else "(no weapon)"
    parts = [base, wounds_str]
    if stamina_str:
        parts.append(stamina_str)
    parts.append(f"wpn:{weapon}")
    if isinstance(c, Monster):
        parts.append(f"HD:{c.hd}")
    return "  ".join(parts)


# ---------------------------------------------------------------------------
# Event narration (for the logfile)
# ---------------------------------------------------------------------------

def event_line(actor: "Creature", action) -> str:
    """One-line, greppable summary of a resolved action for the logfile.

    The action's *outcome* (hit/miss/damage) isn't available here — the
    sim resolves that internally and doesn't surface it on the action
    object — so this describes intent, not result. Good enough for a
    play-by-play trail beside the per-frame board snapshots.
    """
    from ...actions import (
        AttackAction, MoveAction, MoveAndAttackAction,
        FullDefenceAction, PassAction, CounterAttackAction,
    )
    if isinstance(action, MoveAndAttackAction):
        return (f"{actor.name} moves to {action.destination} "
                f"and attacks {action.attack.target.name}")
    if isinstance(action, AttackAction):
        return f"{actor.name} attacks {action.target.name}"
    if isinstance(action, CounterAttackAction):
        return f"{actor.name} counterattacks"
    if isinstance(action, MoveAction):
        return f"{actor.name} moves to {action.destination}"
    if isinstance(action, FullDefenceAction):
        return f"{actor.name} takes full defence"
    if isinstance(action, PassAction):
        return f"{actor.name} passes"
    return f"{actor.name}: {type(action).__name__}"


# ---------------------------------------------------------------------------
# Full per-round screen
# ---------------------------------------------------------------------------

def render_round(ctx: "CombatContext") -> str:
    eng = ctx.engagement
    bf = eng.battlefield
    if bf is None:
        # Non-positioned fights (shouldn't happen in the UI flow but be safe)
        return f"=== Round {ctx.round_no} (no battlefield) ==="
    out: list[str] = [f"=== Round {ctx.round_no} ==="]
    out.append(render_grid(bf, eng.a, eng.b))
    out.append("")
    out.append(render_party_status(eng.a, label="A"))
    out.append(render_party_status(eng.b, label="B"))
    return "\n".join(out)
