"""The Frontend Protocol — the seam between the combat simulator and
whatever surface presents it to a human (terminal, React, etc.).

The same ``Game`` driver works against any concrete Frontend. The
terminal implementation lives in ``combat_sim.ui.terminal``. A future
React frontend would implement the same Protocol over a WebSocket
bridge.

All methods are intentionally synchronous — the terminal driver is
blocking by nature, and async support can be added later by wrapping
the methods in a thin async layer at the boundary.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..actions import Action
    from ..combat import CombatContext, CombatResult
    from ..creatures import Creature
    from .maps import MapDef
    from .parties import PartyTemplate


@dataclass
class ConditionSet:
    """Placeholder for the conditions-setup phase.

    Empty in v1. Future fields will hold fog-of-war state, light
    sources, difficult-terrain sets, initial wounds, etc. The dataclass
    exists now so the ``Frontend.choose_conditions`` return type stays
    stable when those fields are added.
    """
    # Reserved for fog of war, light sources, difficult terrain,
    # initial wounds, etc. Intentionally empty.
    notes: list[str] = field(default_factory=list)


@runtime_checkable
class Frontend(Protocol):
    """The interface every UI implementation must provide.

    The setup methods run once at the start of a game. The per-turn
    methods are called from inside ``HumanAI.decide`` whenever a human-
    controlled creature needs an action. The render hooks fire at
    well-defined moments so a frontend can update its display.
    """

    # ------------------------------------------------------------------
    # Setup phase
    # ------------------------------------------------------------------

    def choose_map(self, maps: list["MapDef"]) -> "MapDef":
        ...

    def choose_party(self, templates: list["PartyTemplate"],
                     side: str) -> "PartyTemplate":
        ...

    def choose_human_controlled(self,
                                creatures: list["Creature"]) -> list["Creature"]:
        """Return the subset of ``creatures`` the player will drive
        directly. The driver replaces their AIs with HumanAI."""
        ...

    def choose_conditions(self) -> ConditionSet:
        """Set up battle conditions (fog of war, etc.). v1 returns an
        empty ConditionSet."""
        ...

    # ------------------------------------------------------------------
    # Per-turn (called from HumanAI)
    # ------------------------------------------------------------------

    def prompt_action(self, actor: "Creature",
                      options: list["Action"],
                      ctx: "CombatContext") -> "Action":
        """Ask the player what ``actor`` should do this turn. ``options``
        is the result of ``targeting.available_actions(actor, ctx)``;
        the frontend is free to add a custom 'move to specific square'
        flow that synthesises new ``MoveAction``s outside the list."""
        ...

    def prompt_reaction(self, actor: "Creature",
                        attacker: "Creature",
                        ctx: "CombatContext") -> "Action":
        """Ask whether ``actor`` wants to Counterattack the incoming
        attack from ``attacker``. Return CounterAttackAction or
        PassAction."""
        ...

    # ------------------------------------------------------------------
    # Rendering hooks (no return value — for view updates only)
    # ------------------------------------------------------------------

    def on_round_start(self, ctx: "CombatContext") -> None:
        ...

    def on_action_resolved(self, actor: "Creature", action: "Action",
                           ctx: "CombatContext") -> None:
        ...

    def on_combat_end(self, result: "CombatResult",
                      ctx: "CombatContext") -> None:
        ...
