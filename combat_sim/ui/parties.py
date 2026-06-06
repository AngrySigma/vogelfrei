"""Party templates + builders for the UI setup phase.

A ``PartyTemplate`` is a named, declarative description of a party.
``build_party(template, map_def, side, ai_overrides)`` instantiates the
template against a specific map: resolves catalog keys (weapons, armor,
AI strategies) to objects, looks up slot positions, places creatures on
the battlefield, and returns a ``Party``.

Templates live in Python for v1 — the catalog is short and the format
changes naturally as we add new careers. A future YAML/TOML loader can
populate ``PARTY_TEMPLATES`` from disk without changing call sites.

Designating a creature as human-controlled is done *after* the party is
built, by replacing its AI with ``HumanAI(frontend)`` — see the game
driver. The template just declares the default (non-human) AI.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .. import items
from ..creatures import Character, Monster
from ..party import Party
from ..battlefield import Battlefield
from ..ai import (
    BerserkerAI, DuellistAI, CautiousAI, GunnerAI, KitingAI,
    ScriptedAI,
)
from ..scenarios import goblin as build_goblin, black_bear as build_black_bear

if TYPE_CHECKING:
    from ..creatures import Creature
    from ..dice import Dice
    from .maps import MapDef


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

AI_REGISTRY: dict[str, type] = {
    "berserker": BerserkerAI,
    "duellist":  DuellistAI,
    "cautious":  CautiousAI,
    "gunner":    GunnerAI,
    "kiting":    KitingAI,
    "scripted":  ScriptedAI,
}


@dataclass
class CreatureSpec:
    """One creature's configuration within a party template.

    ``slot`` selects which numbered position on the map this creature
    occupies (party A uses slots 1-9, party B uses A-I; both are
    1-indexed in the spec).

    ``kind`` is one of:
        "warrior"         — a Character built from catalog items
        "monster:goblin"  — pre-baked goblin (1 HD, AC 14, Small wpn)
        "monster:bear"    — pre-baked black bear (6 HD)
        "monster:bandit"  — Character-like 2 HD humanoid
    """
    slot: int
    name: str
    kind: str = "warrior"
    weapon: str = "SMALL"
    armor: str = "NO_ARMOR"
    offhand: str = "NO_OFFHAND"
    ws: int = 1
    bs: int = 1
    str_mod: int = 0
    agi_mod: int = 0
    wounds: int = 8
    stamina: int = 2
    movement_squares: int = 8
    default_ai: str = "duellist"


@dataclass
class PartyTemplate:
    key: str
    name: str
    description: str
    side: str                         # "A" or "B"
    creatures: list[CreatureSpec]


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class PartyBuildError(ValueError):
    """Raised when a template references a slot or catalog key that
    doesn't exist."""


def _resolve_item(catalog_key: str, attr: str):
    obj = getattr(items, catalog_key, None)
    if obj is None:
        raise PartyBuildError(
            f"unknown {attr} catalog key {catalog_key!r}"
        )
    return obj


def _make_warrior(spec: CreatureSpec) -> Character:
    return Character(
        name=spec.name,
        wounds_max=spec.wounds,
        stamina_max=spec.stamina,
        ws=spec.ws, bs=spec.bs,
        str_mod=spec.str_mod, agi_mod=spec.agi_mod,
        weapon=_resolve_item(spec.weapon, "weapon"),
        armor=_resolve_item(spec.armor, "armor"),
        offhand=_resolve_item(spec.offhand, "offhand"),
        movement_squares=spec.movement_squares,
        ai=_make_ai(spec.default_ai),
    )


def _make_ai(key: str):
    if key not in AI_REGISTRY:
        raise PartyBuildError(f"unknown AI key {key!r}; "
                              f"known: {sorted(AI_REGISTRY)}")
    return AI_REGISTRY[key]()


def _make_monster(spec: CreatureSpec, dice: "Dice") -> "Creature":
    """Pre-baked monster factories. Goblin/Bear use the same builders as
    the sim's scenarios, so behaviour matches. ``bandit`` is a generic
    HD-based humanoid."""
    if spec.kind == "monster:goblin":
        return build_goblin(spec.name, dice)
    if spec.kind == "monster:bear":
        return build_black_bear(spec.name, dice)
    if spec.kind == "monster:bandit":
        # Bandit looks like a Character but uses Monster mechanics
        # (no stamina, simple AC). Two HD by convention.
        from ..scenarios import bandit
        return bandit(spec.name, dice, hd=2)
    raise PartyBuildError(f"unknown monster kind {spec.kind!r}")


def build_party(template: PartyTemplate,
               map_def: "MapDef",
               battlefield: Battlefield,
               *,
               dice: "Dice") -> Party:
    """Instantiate ``template`` against the given map. Each creature is
    placed at the slot position declared in its spec. Returns the
    ``Party`` ready for combat — its AIs are the defaults; the game
    driver swaps in ``HumanAI`` afterwards for player-controlled units.
    """
    if template.side not in ("A", "B"):
        raise PartyBuildError(f"side must be 'A' or 'B', got {template.side!r}")
    slot_map = (map_def.party_a_slots if template.side == "A"
                else map_def.party_b_slots)

    members: list["Creature"] = []
    for spec in template.creatures:
        if spec.slot not in slot_map:
            raise PartyBuildError(
                f"map {map_def.name!r} has no slot {spec.slot} "
                f"for side {template.side}"
            )
        if spec.kind == "warrior":
            c = _make_warrior(spec)
        else:
            c = _make_monster(spec, dice)
        battlefield.register(c, slot_map[spec.slot])
        members.append(c)
    return Party(name=template.name, members=members)


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

PARTY_TEMPLATES: dict[str, PartyTemplate] = {

    "lone_warrior_a": PartyTemplate(
        key="lone_warrior_a",
        name="Lone Warrior",
        description="A single chain-and-shield veteran with a longsword.",
        side="A",
        creatures=[CreatureSpec(
            slot=1, name="Karl",
            kind="warrior",
            weapon="MEDIUM_2H", armor="CHAIN", offhand="SHIELD",
            default_ai="duellist",
        )],
    ),

    "two_warriors_a": PartyTemplate(
        key="two_warriors_a",
        name="Two Warriors",
        description="A buckler-and-longsword man and a spear soldier.",
        side="A",
        creatures=[
            CreatureSpec(slot=1, name="Karl",
                         kind="warrior",
                         weapon="MEDIUM_2H", armor="WAMS", offhand="BUCKLER"),
            CreatureSpec(slot=2, name="Otto",
                         kind="warrior",
                         weapon="SPEAR_2H", armor="WAMS"),
        ],
    ),

    "longbow_archer_a": PartyTemplate(
        key="longbow_archer_a",
        name="Longbow Archer",
        description="A skilled archer (BS 2) using kiting tactics.",
        side="A",
        creatures=[CreatureSpec(
            slot=1, name="Aelwin",
            kind="warrior",
            weapon="LONG_BOW", armor="WAMS",
            ws=1, bs=2, agi_mod=1,
            default_ai="kiting",
        )],
    ),

    "single_goblin_b": PartyTemplate(
        key="single_goblin_b",
        name="Single Goblin",
        description="One lone goblin scout.",
        side="B",
        creatures=[CreatureSpec(slot=1, name="Goblin",
                                kind="monster:goblin")],
    ),

    "goblin_mob_b": PartyTemplate(
        key="goblin_mob_b",
        name="Goblin Mob",
        description="Four goblins, no leader.",
        side="B",
        creatures=[
            CreatureSpec(slot=1, name="Gob1", kind="monster:goblin"),
            CreatureSpec(slot=2, name="Gob2", kind="monster:goblin"),
            CreatureSpec(slot=3, name="Gob3", kind="monster:goblin"),
            CreatureSpec(slot=4, name="Gob4", kind="monster:goblin"),
        ],
    ),

    "bear_b": PartyTemplate(
        key="bear_b",
        name="Black Bear",
        description="A 6 HD black bear with two claws and a bite.",
        side="B",
        creatures=[CreatureSpec(slot=1, name="Bear",
                                kind="monster:bear")],
    ),

    "lone_warrior_b": PartyTemplate(
        key="lone_warrior_b",
        name="Lone Swordsman",
        description="An opposing veteran. Use for warrior-vs-warrior duels.",
        side="B",
        creatures=[CreatureSpec(
            slot=1, name="Hans",
            kind="warrior",
            weapon="MEDIUM_2H", armor="CHAIN", offhand="SHIELD",
            default_ai="duellist",
        )],
    ),

    "swordsman_b": PartyTemplate(
        key="swordsman_b",
        name="Light Swordsman",
        description="A lightly armoured opponent — Wams and a buckler.",
        side="B",
        creatures=[CreatureSpec(
            slot=1, name="Hans",
            kind="warrior",
            weapon="MEDIUM_2H", armor="WAMS", offhand="BUCKLER",
            default_ai="duellist",
        )],
    ),
}
