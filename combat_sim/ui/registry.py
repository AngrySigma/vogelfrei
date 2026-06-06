"""Catalog assembly — what the UI offers the player at setup time.

The registry is the single point of truth for "what maps and parties
exist." The terminal Frontend (and any future frontend) consults it.
Maps are read from disk under ``ui/resources/maps/``; party templates
live in ``parties.py`` for now.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from .maps import MapDef, discover_maps
from .parties import PartyTemplate, PARTY_TEMPLATES


# Where shipped maps live. Override via the constructor for tests.
_DEFAULT_MAP_DIR = Path(__file__).resolve().parent / "resources" / "maps"


class Registry:
    """Container for the maps + templates a Frontend can pick from."""

    def __init__(self, map_dir: Optional[str | Path] = None,
                 templates: Optional[dict[str, PartyTemplate]] = None) -> None:
        self._map_dir = Path(map_dir) if map_dir else _DEFAULT_MAP_DIR
        self._templates = templates if templates is not None else PARTY_TEMPLATES
        self._maps_cache: Optional[list[MapDef]] = None

    def maps(self) -> list[MapDef]:
        if self._maps_cache is None:
            self._maps_cache = discover_maps(self._map_dir)
        return self._maps_cache

    def templates(self, *, side: Optional[str] = None) -> list[PartyTemplate]:
        """All templates, optionally filtered by side ('A' or 'B')."""
        if side is None:
            return list(self._templates.values())
        return [t for t in self._templates.values() if t.side == side]

    def template(self, key: str) -> PartyTemplate:
        return self._templates[key]

    def map_by_name(self, name: str) -> MapDef:
        for m in self.maps():
            if m.name == name:
                return m
        raise KeyError(f"no map named {name!r}; available: "
                       f"{[m.name for m in self.maps()]}")
