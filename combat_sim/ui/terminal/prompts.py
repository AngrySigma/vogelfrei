"""Menus and input parsing for the terminal frontend.

Each function takes a list of choices and returns the chosen object.
Input goes through ``input()`` and is validated until the user gives a
legal answer (or types ``q`` to abort, which raises ``KeyboardInterrupt``).

Action menus group the action list into intuitive sections (attacks,
moves, defence, pass) and offer a 'pick a custom destination' shortcut
that synthesises a ``MoveAction`` outside the legal-actions list when
the player wants to move to a specific square.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional, TypeVar

from ...actions import (
    Action, AttackAction, MoveAction, MoveAndAttackAction,
    FullDefenceAction, PassAction, CounterAttackAction,
)
from ...movement import validate_move, reachable_within
from ...geometry import chebyshev

if TYPE_CHECKING:
    from ...creatures import Creature
    from ...combat import CombatContext


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Generic menu
# ---------------------------------------------------------------------------

def pick_from(items: list[T], *,
             label: Callable[[T], str],
             prompt: str,
             default: int = 1) -> T:
    """Show a numbered list, read a number, return the chosen item.
    Numbers are 1-indexed in the display."""
    if not items:
        raise ValueError("nothing to pick from")
    print()
    for i, item in enumerate(items, 1):
        print(f"  {i}) {label(item)}")
    while True:
        raw = input(f"\n{prompt} [1-{len(items)}, default {default}]: ").strip()
        if raw.lower() in ("q", "quit"):
            raise KeyboardInterrupt
        if not raw:
            return items[default - 1]
        try:
            idx = int(raw)
        except ValueError:
            print(f"  '{raw}' isn't a number — try again.")
            continue
        if not 1 <= idx <= len(items):
            print(f"  {idx} is out of range (1..{len(items)}).")
            continue
        return items[idx - 1]


# ---------------------------------------------------------------------------
# Multi-select
# ---------------------------------------------------------------------------

def pick_many(items: list[T], *,
             label: Callable[[T], str],
             prompt: str) -> list[T]:
    """Comma-separated multi-select. Empty input means 'none'."""
    if not items:
        return []
    print()
    for i, item in enumerate(items, 1):
        print(f"  {i}) {label(item)}")
    while True:
        raw = input(f"\n{prompt} (comma-separated, blank for none): ").strip()
        if not raw:
            return []
        if raw.lower() in ("q", "quit"):
            raise KeyboardInterrupt
        try:
            idxs = [int(p.strip()) for p in raw.split(",") if p.strip()]
        except ValueError:
            print("  Please enter numbers separated by commas.")
            continue
        if any(not 1 <= i <= len(items) for i in idxs):
            print(f"  Numbers must be in 1..{len(items)}.")
            continue
        return [items[i - 1] for i in idxs]


# ---------------------------------------------------------------------------
# Action menu
# ---------------------------------------------------------------------------

def prompt_action_menu(actor: "Creature",
                      options: list[Action],
                      ctx: "CombatContext") -> Action:
    """Render the legal-action list for ``actor`` and read the player's
    choice. Supports a 'pick destination' shortcut for free movement
    that synthesises a ``MoveAction`` outside ``options``.
    """
    print()
    print(f"-- {actor.name}'s turn --")
    grouped = _group_actions(options, actor, ctx)

    # Print the menu
    numbered: list[tuple[str, Action]] = []
    for header, entries in grouped:
        if not entries:
            continue
        print(f"  [{header}]")
        for label, action in entries:
            i = len(numbered) + 1
            print(f"    {i}) {label}")
            numbered.append((label, action))

    has_movement = (ctx.engagement.battlefield is not None
                    and actor.position is not None)
    if has_movement:
        i = len(numbered) + 1
        print(f"    {i}) Move to specific square (m x,y)")

    # Read input
    while True:
        raw = input("\nChoice: ").strip()
        if not raw:
            continue
        if raw.lower() in ("q", "quit"):
            raise KeyboardInterrupt

        # Move-to-coords shortcut: "m x,y" or "m x y"
        if raw.lower().startswith("m"):
            rest = raw[1:].strip()
            coords = _parse_coords(rest)
            if coords is None:
                print("  Couldn't parse coordinates. Use 'm x,y'.")
                continue
            bf = ctx.engagement.battlefield
            if not validate_move(actor, coords, bf):
                print(f"  Can't move to {coords} — not reachable or "
                      f"not passable.")
                _show_reachable(actor, ctx)
                continue
            return MoveAction(destination=coords)

        # Numeric pick
        try:
            idx = int(raw)
        except ValueError:
            print(f"  '{raw}' isn't a number or a coordinate command.")
            continue
        if 1 <= idx <= len(numbered):
            return numbered[idx - 1][1]
        if has_movement and idx == len(numbered) + 1:
            # Same as the 'm' shortcut but interactive — re-prompt
            print("  Enter destination as x,y (e.g. '5,3').")
            continue
        print(f"  {idx} is out of range.")


def _group_actions(options: list[Action],
                  actor: "Creature",
                  ctx: "CombatContext") \
        -> list[tuple[str, list[tuple[str, Action]]]]:
    """Return action groups as (heading, [(label, action), ...])."""
    melee: list[tuple[str, Action]] = []
    ranged: list[tuple[str, Action]] = []
    move_atk: list[tuple[str, Action]] = []
    moves: list[tuple[str, Action]] = []
    defence: list[tuple[str, Action]] = []
    other: list[tuple[str, Action]] = []

    bf = ctx.engagement.battlefield

    for a in options:
        if isinstance(a, AttackAction):
            label = _attack_label(actor, a, bf)
            if a.weapon is not None and a.weapon.is_ranged:
                ranged.append((label, a))
            else:
                melee.append((label, a))
        elif isinstance(a, MoveAndAttackAction):
            move_atk.append((_move_and_attack_label(actor, a, bf), a))
        elif isinstance(a, MoveAction):
            moves.append((_move_label(actor, a, bf), a))
        elif isinstance(a, FullDefenceAction):
            defence.append(("Full Defence (+2 AC, +4 if Trained)", a))
        elif isinstance(a, PassAction):
            other.append(("Pass turn", a))
        else:
            other.append((type(a).__name__, a))

    return [
        ("Melee attacks", melee),
        ("Ranged attacks", ranged),
        ("Move and attack", move_atk),
        ("Movement", moves),
        ("Defence", defence),
        ("Other", other),
    ]


def _attack_label(actor, action: AttackAction, bf) -> str:
    target = action.target
    weapon = action.weapon if action.weapon is not None else actor.weapon
    wname = weapon.name if weapon else "(unarmed)"
    pos = ""
    if bf is not None and target.position is not None:
        d = chebyshev(actor.position, target.position) if actor.position else "?"
        pos = f" @{target.position} (dist {d})"
    return f"Attack {target.name}{pos} with {wname}"


def _move_label(actor, action: MoveAction, bf) -> str:
    if bf is None or actor.position is None:
        return f"Move to {action.destination}"
    d = chebyshev(actor.position, action.destination)
    return f"Move to {action.destination} ({d} sq)"


def _move_and_attack_label(actor, action: MoveAndAttackAction, bf) -> str:
    atk = action.attack
    sub = _attack_label(actor, atk, bf)
    return f"Move to {action.destination} then {sub}"


def _parse_coords(s: str) -> Optional[tuple[int, int]]:
    """Accept '5,3', '5 3', '(5,3)'. Returns (x, y) or None."""
    s = s.strip().strip("()").replace(",", " ")
    parts = s.split()
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _show_reachable(actor, ctx) -> None:
    """Hint for the user: list a sample of reachable squares."""
    bf = ctx.engagement.battlefield
    if bf is None or actor.position is None:
        return
    reach = reachable_within(actor.position, actor.movement_squares,
                            bf, ignoring=actor)
    # Show up to ~12 squares to avoid cluttering the screen
    sample = sorted(reach.items(),
                   key=lambda kv: (kv[1], kv[0]))[:12]
    if sample:
        squares = ", ".join(f"{pos}" for pos, _ in sample)
        print(f"  Reachable (sample): {squares}")


# ---------------------------------------------------------------------------
# Reaction (Counterattack) prompt
# ---------------------------------------------------------------------------

def prompt_reaction_menu(actor: "Creature",
                        attacker: "Creature",
                        ctx: "CombatContext") -> Action:
    """Yes/no on whether to counterattack."""
    print()
    print(f"  >> {attacker.name} attacks {actor.name}!")
    print(f"     {actor.name} may Counterattack (longer-or-equal weapon, trained).")
    while True:
        raw = input("     Counterattack? [y/N]: ").strip().lower()
        if raw in ("", "n", "no"):
            return PassAction()
        if raw in ("y", "yes"):
            return CounterAttackAction()
        if raw == "q":
            raise KeyboardInterrupt
        print("     Please type 'y' or 'n'.")
