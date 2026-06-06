"""Conditions: persistent status effects with hooks.

A Condition is a small bundle of state attached to a Creature
(``creature.conditions: list[Condition]``). Each condition exposes a
set of hooks that the combat layer calls at well-defined moments:

    on_turn_start(c, ctx) -> Action | None
        If non-None, overrides the AI's decision for the turn. Used by
        Surprised to skip a round, by Stunned later, etc.

    on_attack_out(c, target, weapon, ctx, is_ranged) -> HitModifier | None
        Adds a modifier to outgoing attacks. Used e.g. by Aim, Charge,
        Drunk (future).

    on_defend(c, attacker, weapon, ctx, is_ranged) -> int
        AC bonus while defending. Used by FullDefence (future), Prone
        ranged-defense modifier, etc.

    can_use_weapon(c, weapon, ctx) -> bool
        Blocks use of a specific weapon. Used by Reloading.

    bypasses_stamina(c, ctx) -> bool
        If True, incoming damage skips Stamina. Used by Surprised
        (matches the 'attacking an unaware target' rule).

    unaware(c) -> bool
        If True, defender uses the Unaware AC formula (base + AR only)
        instead of full AC. Used by Surprised.

    on_round_end(c, ctx) -> bool
        Tick. Return True to remove the condition.

The base class is a no-op for every hook so concrete conditions only
override the ones they care about.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .ai import Action, PassAction
from .stats import HitModifier

if TYPE_CHECKING:
    from .creatures import Creature
    from .combat import CombatContext
    from .items import Weapon


class Condition:
    name: str = "Condition"

    def on_turn_start(self, c: "Creature", ctx: "CombatContext") -> Optional[Action]:
        return None

    def on_attack_out(self, c: "Creature", target: "Creature",
                     weapon: "Weapon | None", ctx: "CombatContext",
                     is_ranged: bool) -> Optional[HitModifier]:
        return None

    def on_defend(self, c: "Creature", attacker: "Creature",
                 weapon: "Weapon | None", ctx: "CombatContext",
                 is_ranged: bool) -> int:
        return 0

    def can_use_weapon(self, c: "Creature", weapon: "Weapon | None",
                      ctx: "CombatContext") -> bool:
        return True

    def bypasses_stamina(self, c: "Creature", ctx: "CombatContext") -> bool:
        return False

    def unaware(self, c: "Creature") -> bool:
        return False

    def on_round_end(self, c: "Creature", ctx: "CombatContext") -> bool:
        return False


# ---------------------------------------------------------------------------
# Concrete conditions
# ---------------------------------------------------------------------------

class Surprised(Condition):
    """Surprised characters skip their first round; while surprised,
    incoming attacks bypass Stamina and use the Unaware AC formula
    (base AC + AR only). Removed at the end of the round."""

    name = "Surprised"

    def on_turn_start(self, c, ctx):
        return PassAction()

    def bypasses_stamina(self, c, ctx):
        return True

    def unaware(self, c):
        return True

    def on_round_end(self, c, ctx):
        return True


class Reloading(Condition):
    """Locks a specific weapon for ``rounds_remaining`` rounds.

    For matchlock firearms reload is base 10 minus BS minus Agi (per
    Firearms.md). For crossbows reload is a small fixed number (1 for
    light, 2 for heavy). The combat layer adds this condition after a
    successful firing of a ranged weapon with reload_rounds > 0.

    Simplification vs RAW: in the rules, reload only ticks during rounds
    where the character isn't moving or defending. Here it ticks every
    round. Tighten when movement is modelled.
    """

    name = "Reloading"

    def __init__(self, weapon: "Weapon", rounds: int):
        self.weapon = weapon
        self.rounds_remaining = rounds

    def can_use_weapon(self, c, weapon, ctx):
        return weapon is not self.weapon

    def on_round_end(self, c, ctx):
        self.rounds_remaining -= 1
        return self.rounds_remaining <= 0


class FullDefence(Condition):
    """+2 AC (+4 if Trained) until end of round."""

    name = "FullDefence"

    def __init__(self, bonus: int):
        self.bonus = bonus

    def on_defend(self, c, attacker, weapon, ctx, is_ranged):
        return self.bonus

    def on_round_end(self, c, ctx):
        return True
