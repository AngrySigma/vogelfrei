"""TerminalFrontend — the concrete Frontend for stdlib terminal play.

Sits behind the Frontend Protocol. The game driver doesn't know it's
talking to a terminal; this class just provides the prompts and
renders that print to stdout / read from stdin.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..frontend import ConditionSet
from . import render
from . import prompts

if TYPE_CHECKING:
    from ...actions import Action
    from ...combat import CombatContext, CombatResult
    from ...creatures import Creature
    from ..maps import MapDef
    from ..parties import PartyTemplate


class TerminalFrontend:
    """A Frontend that talks to the user through stdin/stdout."""

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def choose_map(self, maps: list["MapDef"]) -> "MapDef":
        print()
        print("============================")
        print(" Choose a map")
        print("============================")
        return prompts.pick_from(
            maps,
            label=lambda m: f"{m.name} ({m.width}x{m.height}) — {m.description}",
            prompt="Map number",
        )

    def choose_party(self, templates: list["PartyTemplate"],
                     side: str) -> "PartyTemplate":
        print()
        print("============================")
        print(f" Choose party for side {side}")
        print("============================")
        return prompts.pick_from(
            templates,
            label=lambda t: f"{t.name} — {t.description}",
            prompt="Party number",
        )

    def choose_human_controlled(self,
                                creatures: list["Creature"]) -> list["Creature"]:
        print()
        print("============================")
        print(" Choose human-controlled creatures")
        print("============================")
        print("Pick creatures you'll control directly. The rest run on AI.")
        return prompts.pick_many(
            creatures,
            label=lambda c: (f"{c.name} ({type(c).__name__}, "
                            f"W:{c.wounds}/{c.wounds_max}, "
                            f"wpn:{c.weapon.name if c.weapon else '-'})"),
            prompt="Numbers",
        )

    def choose_conditions(self) -> ConditionSet:
        # v1 placeholder — no questions asked. Future: fog of war,
        # light sources, difficult terrain, initial wounds.
        return ConditionSet()

    # ------------------------------------------------------------------
    # Per-turn
    # ------------------------------------------------------------------

    def prompt_action(self, actor: "Creature",
                      options: list["Action"],
                      ctx: "CombatContext") -> "Action":
        # Refresh the map before asking, so the player sees current state.
        print()
        print(render.render_round(ctx))
        return prompts.prompt_action_menu(actor, options, ctx)

    def prompt_reaction(self, actor: "Creature",
                        attacker: "Creature",
                        ctx: "CombatContext") -> "Action":
        # Render the current state before the player decides — the
        # attacker has typically just moved into reach, and the player
        # needs to see *where they came from* before answering. Before
        # this hook the only render they'd seen was round-start, which
        # showed the attacker's old position.
        print()
        print(render.render_round(ctx))
        return prompts.prompt_reaction_menu(actor, attacker, ctx)

    # ------------------------------------------------------------------
    # Render hooks
    # ------------------------------------------------------------------

    def on_round_start(self, ctx: "CombatContext") -> None:
        # Render the round before any decisions happen. For human-
        # controlled creatures, ``prompt_action`` also re-renders so the
        # player sees the latest state right before picking — leading to
        # one double-render per round when a human is first to act,
        # which is acceptable cost for keeping AI-vs-AI fights visible.
        print()
        print(render.render_round(ctx))

    def on_action_resolved(self, actor: "Creature", action: "Action",
                           ctx: "CombatContext") -> None:
        # Render after actions that visibly change the map. Attacks
        # change wounds (textual delta) but not position, so they don't
        # justify a full re-render — the next prompt or round-start will
        # reflect their effect. Move-type actions do change positions
        # and need an immediate render so AI moves don't "teleport"
        # from the player's perspective.
        from ...actions import MoveAction, MoveAndAttackAction
        if isinstance(action, (MoveAction, MoveAndAttackAction)):
            print()
            print(render.render_round(ctx))

    def on_combat_end(self, result: "CombatResult",
                      ctx: "CombatContext") -> None:
        print()
        print("============================")
        print(f" Combat over after {result.rounds} round(s)")
        print(f" Winner: {result.winner or 'draw (max rounds reached)'}")
        print("============================")
        if result.injuries:
            inj = ", ".join(f"{k}={v}" for k, v in sorted(result.injuries.items()))
            print(f"  Injuries this fight: {inj}")
        if result.deaths:
            total = sum(result.deaths.values())
            print(f"  Total deaths: {total}")
