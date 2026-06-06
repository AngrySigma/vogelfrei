"""The game driver — the pipeline that wires Frontend → Sim → Frontend.

A single ``run_game`` call walks through:
    1. Choose a map
    2. Choose two parties (one per side)
    3. Choose which creatures are human-controlled
    4. Build battlefield + conditions
    5. Run combat round-by-round until one side is defeated

The driver knows nothing about how the player makes choices — it asks
the Frontend. The Frontend knows nothing about how combat resolves —
it just answers prompts and gets render hooks.

Includes ``ScriptedFrontend``, a test-double Frontend that returns
pre-canned answers for every prompt. Used by the game-driver tests.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Callable

from ..dice import Dice
from ..battlefield import Battlefield
from ..combat import CombatContext, run_round, CombatResult
from ..party import Party, Engagement
from ..creatures import DEAD

from .frontend import Frontend, ConditionSet
from .human_ai import HumanAI
from .registry import Registry
from .parties import PartyTemplate, build_party
from .maps import MapDef

if TYPE_CHECKING:
    from ..actions import Action
    from ..creatures import Creature


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_game(frontend: Frontend,
            registry: Registry,
            *,
            seed: Optional[int] = None,
            max_rounds: int = 200) -> CombatResult:
    """Walk the setup pipeline, then run combat to completion.

    The frontend is the only thing that decides what the player sees or
    inputs. The registry is the only thing that decides what content
    (maps, templates) is available.
    """
    # 1. Map
    map_def = frontend.choose_map(registry.maps())

    # 2. Parties
    template_a = frontend.choose_party(registry.templates(side="A"), side="A")
    template_b = frontend.choose_party(registry.templates(side="B"), side="B")

    # Build battlefield first so we can place creatures on it as they're built.
    bf = Battlefield(width=map_def.width, height=map_def.height,
                     blocked=set(map_def.blocked))

    dice = Dice(seed=seed) if seed is not None else Dice()
    party_a = build_party(template_a, map_def, bf, dice=dice)
    party_b = build_party(template_b, map_def, bf, dice=dice)

    # 2b. Human assignment
    humans = frontend.choose_human_controlled(
        party_a.members + party_b.members
    )
    for c in humans:
        c.ai = HumanAI(frontend)

    # 3. Conditions (placeholder)
    _ = frontend.choose_conditions()
    # ConditionSet is currently empty; future versions apply effects here.

    # 4. Combat
    engagement = Engagement(party_a, party_b, battlefield=bf)
    ctx = CombatContext(dice=dice, engagement=engagement,
                       on_action=frontend.on_action_resolved)
    while (not party_a.is_defeated and not party_b.is_defeated
           and ctx.round_no < max_rounds):
        frontend.on_round_start(ctx)
        run_round((party_a, party_b), ctx)

    winner: Optional[str] = None
    if party_a.is_defeated and not party_b.is_defeated:
        winner = party_b.name
    elif party_b.is_defeated and not party_a.is_defeated:
        winner = party_a.name
    result = CombatResult(rounds=ctx.round_no, winner=winner, log=ctx.log,
                         injuries=ctx.injuries, deaths=ctx.deaths)
    frontend.on_combat_end(result, ctx)
    return result


# ---------------------------------------------------------------------------
# ScriptedFrontend — test double
# ---------------------------------------------------------------------------

@dataclass
class ScriptedFrontend:
    """A Frontend that returns pre-canned answers. Used for tests and
    for replaying a fight from logged decisions.

    Setup fields are looked up directly; per-turn answers come from
    ``action_script`` (popped in order) or ``action_policy`` (a callable
    that picks an action given the actor + options).
    """
    map_choice: Optional[Callable[[list[MapDef]], MapDef]] = None
    party_a_choice: Optional[Callable[[list[PartyTemplate]], PartyTemplate]] = None
    party_b_choice: Optional[Callable[[list[PartyTemplate]], PartyTemplate]] = None
    human_choice: Optional[Callable[[list["Creature"]], list["Creature"]]] = None
    conditions_choice: Optional[ConditionSet] = None

    action_script: list["Action"] = field(default_factory=list)
    action_policy: Optional[Callable[..., "Action"]] = None

    # event log for assertions
    events: list[tuple[str, object]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def choose_map(self, maps):
        if self.map_choice is None:
            return maps[0]
        return self.map_choice(maps)

    def choose_party(self, templates, side):
        chooser = self.party_a_choice if side == "A" else self.party_b_choice
        if chooser is None:
            return templates[0]
        return chooser(templates)

    def choose_human_controlled(self, creatures):
        if self.human_choice is None:
            return []
        return self.human_choice(creatures)

    def choose_conditions(self):
        return self.conditions_choice or ConditionSet()

    # ------------------------------------------------------------------
    # Per-turn
    # ------------------------------------------------------------------

    def prompt_action(self, actor, options, ctx):
        if self.action_policy is not None:
            return self.action_policy(actor=actor, options=options, ctx=ctx)
        if self.action_script:
            return self.action_script.pop(0)
        # Default: pass turn.
        from ..actions import PassAction
        return PassAction()

    def prompt_reaction(self, actor, attacker, ctx):
        from ..actions import PassAction
        return PassAction()

    # ------------------------------------------------------------------
    # Rendering — record for inspection
    # ------------------------------------------------------------------

    def on_round_start(self, ctx):
        self.events.append(("round_start", ctx.round_no))

    def on_action_resolved(self, actor, action, ctx):
        self.events.append(("action", (actor.name, type(action).__name__)))

    def on_combat_end(self, result, ctx):
        self.events.append(("end", result.winner))
