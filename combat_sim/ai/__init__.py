"""AI strategies — one per file.

Re-exports the entire suite at package level so callers can do
``from combat_sim.ai import DuellistAI`` as before.

Also re-exports Action types from ``combat_sim.actions`` for backward
compatibility with code that did ``from combat_sim.ai import AttackAction``
during the single-file phase.
"""

from .base import AI
from .berserker import BerserkerAI
from .duellist import DuellistAI
from .cautious import CautiousAI
from .gunner import GunnerAI
from .kiting import KitingAI
from .scripted import ScriptedAI

# Backward-compat re-exports of actions
from ..actions import (
    Action,
    AttackAction,
    CounterAttackAction,
    MultiAttackAction,
    FullDefenceAction,
    PassAction,
    MoveAction,
    MoveAndAttackAction,
)

__all__ = [
    "AI",
    "BerserkerAI", "DuellistAI", "CautiousAI", "GunnerAI", "KitingAI",
    "ScriptedAI",
    "Action", "AttackAction", "CounterAttackAction", "MultiAttackAction",
    "FullDefenceAction", "PassAction", "MoveAction", "MoveAndAttackAction",
]
