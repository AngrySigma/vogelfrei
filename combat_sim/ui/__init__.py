"""Combat-sim UI package.

The Frontend Protocol lives in ``.frontend``. The default terminal
implementation is in ``.terminal``. Run the terminal app with
``python -m combat_sim.ui``.

The Game driver (``.game.run_game``) wires any Frontend together with
the Registry of maps and party templates. To add a new frontend (e.g.
React over WebSocket), implement Frontend and instantiate it instead
of TerminalFrontend.
"""

from .frontend import Frontend, ConditionSet
from .human_ai import HumanAI
from .game import run_game, ScriptedFrontend
from .registry import Registry
from .maps import MapDef, parse_map, parse_map_file, discover_maps
from .parties import (
    PartyTemplate, CreatureSpec, build_party, PARTY_TEMPLATES,
)

__all__ = [
    "Frontend", "ConditionSet",
    "HumanAI",
    "run_game", "ScriptedFrontend",
    "Registry",
    "MapDef", "parse_map", "parse_map_file", "discover_maps",
    "PartyTemplate", "CreatureSpec", "build_party", "PARTY_TEMPLATES",
]
