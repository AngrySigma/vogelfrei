"""Combat simulator for the Vogelfrei OSR ruleset.

Public surface kept intentionally small — most consumers will call
``run_scenario`` from ``combat_sim.scenarios`` or build their own
parties using the catalog in ``combat_sim.items`` and the
``Character`` / ``Monster`` classes in ``combat_sim.creatures``.

For positioned combat, build a ``Battlefield``, ``register`` creatures
on it, then pass it to ``Engagement(party_a, party_b,
battlefield=...)``. Without a battlefield, the engine runs in
abstract-melee-zone mode (every enemy adjacent, no range bands) —
matches the original v1 behaviour.
"""

from .dice import Dice
from .creatures import Creature, Character, Monster
from .items import Weapon, Armor, OffHand
from .actions import (
    Action, AttackAction, CounterAttackAction,
    MultiAttackAction, FullDefenceAction, PassAction,
    MoveAction, MoveAndAttackAction,
)
from .ai import (
    AI, BerserkerAI, DuellistAI, CautiousAI, GunnerAI, KitingAI,
    ScriptedAI,
)
from .conditions import Condition, Surprised, Reloading, FullDefence
from .party import Party, Engagement
from .battlefield import Battlefield
from .geometry import FT_PER_SQUARE, chebyshev
from . import movement
from . import targeting
from .combat import run_combat, CombatContext, AttackResult, CombatResult
from .scenarios import run_scenario, SCENARIOS, Scenario

__all__ = [
    "Dice",
    "Creature", "Character", "Monster",
    "Weapon", "Armor", "OffHand",
    "Action", "AttackAction", "CounterAttackAction",
    "MultiAttackAction", "FullDefenceAction", "PassAction",
    "MoveAction", "MoveAndAttackAction",
    "AI", "BerserkerAI", "DuellistAI", "CautiousAI",
    "GunnerAI", "KitingAI", "ScriptedAI",
    "Condition", "Surprised", "Reloading", "FullDefence",
    "Party", "Engagement", "Battlefield",
    "FT_PER_SQUARE", "chebyshev",
    "movement", "targeting",
    "run_combat", "CombatContext", "AttackResult", "CombatResult",
    "run_scenario", "SCENARIOS", "Scenario",
]
