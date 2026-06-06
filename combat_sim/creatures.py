"""Creature hierarchy.

The base ``Creature`` holds everything common: wounds, ability mods,
weapon, armor, AI hook, current state. ``Character`` adds Stamina and
the damage routing that absorbs hits into Stamina first. ``Monster``
adds Hit Dice (which feed an attack bonus per the LotFP convention),
multi-attack support via ``natural_attacks``, and skips Stamina.

State convention:
    wounds > 0           — combat capable
    0 >= wounds > -inf   — prone / unconscious (Character only)
                           or dead (Monster)
    wounds == DEAD       — flagged dead by the combat layer

Anything that crosses below 0 triggers the critical-injury table (for
Characters); a Character below 0 who takes any further damage dies
outright per the rules.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .items import Weapon, Armor, OffHand, NO_OFFHAND, IMPROVISED, NO_ARMOR

if TYPE_CHECKING:
    from .ai import AI
    from .conditions import Condition


DEAD = -10_000  # sentinel: definitively, mechanically dead


@dataclass
class Creature:
    name: str
    wounds_max: int
    base_ac: int = 8
    str_mod: int = 0
    agi_mod: int = 0
    ws: int = 0
    bs: int = 0
    weapon: Weapon = IMPROVISED
    armor: Armor = NO_ARMOR
    offhand: OffHand = NO_OFFHAND
    morale: int = 7
    attack_bonus: int = 0          # extra to-hit (e.g. monster HD)
    ai: Optional["AI"] = None
    conditions: list["Condition"] = field(default_factory=list)

    # Battlefield-related — both None outside positioned scenarios.
    # ``movement_squares`` is the *combat-speed* walking rate (40' per
    # round / 5' per square = 8 squares for unencumbered). A character
    # using combat speed may both move and attack in the same round
    # (see Combat Actions.md). ``running_squares`` is the optional
    # higher-rate move (120' / 5 = 24 squares) for the run-only,
    # no-attack-this-round case; currently exposed as data only — the
    # combat layer does not yet consume it.
    movement_squares: int = 8
    running_squares: int = 24
    position: Optional[tuple[int, int]] = None

    wounds: int = field(init=False)

    def __post_init__(self) -> None:
        self.wounds = self.wounds_max

    # -- conditions ---------------------------------------------------------

    def has_condition(self, cls) -> bool:
        return any(isinstance(c, cls) for c in self.conditions)

    def add_condition(self, cond: "Condition") -> None:
        self.conditions.append(cond)

    def can_use_weapon(self, weapon, ctx) -> bool:
        for c in self.conditions:
            if not c.can_use_weapon(self, weapon, ctx):
                return False
        return True

    # -- positioning --------------------------------------------------------

    def move_to(self, pos: tuple[int, int], battlefield) -> bool:
        """Attempt to move to ``pos``. Validates passability against the
        battlefield (in bounds, no terrain, not occupied by another
        creature). On success, updates both ``self.position`` and the
        battlefield's occupancy index. Returns True on success."""
        if not battlefield.is_passable(pos, ignoring=self):
            return False
        battlefield.update_position(self, pos)
        return True

    # -- AC -----------------------------------------------------------------

    @property
    def ac_melee(self) -> int:
        return (self.base_ac + self.agi_mod + self.ws
                + self.armor.ar + self.offhand.melee_ac_bonus)

    @property
    def ac_ranged(self) -> int:
        return (11 + self.agi_mod
                + self.armor.ar + self.offhand.ranged_ac_bonus)

    # -- training / status --------------------------------------------------

    @property
    def is_trained(self) -> bool:
        return self.ws >= 1

    @property
    def is_combat_capable(self) -> bool:
        return self.wounds > 0

    @property
    def is_alive(self) -> bool:
        return self.wounds > DEAD

    # -- damage routing -----------------------------------------------------

    def stamina(self) -> int:
        """Override in Character. Monsters have none."""
        return 0

    def absorb_damage(self, amount: int, *, bypass_stamina: bool = False) -> tuple[int, int]:
        """Apply damage to this creature.

        Returns ``(stamina_lost, wounds_lost)``.

        Default (Monster) routes everything to wounds. ``Character``
        overrides to deplete Stamina first.
        """
        self.wounds -= amount
        return 0, amount


@dataclass
class Character(Creature):
    """Trained, intelligent humanoids. Have Stamina; eligible for the
    critical-injury table; track training status for Counterattack."""

    stamina_max: int = 0
    stamina_current: int = field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.stamina_current = self.stamina_max

    def stamina(self) -> int:
        return self.stamina_current

    def absorb_damage(self, amount: int, *, bypass_stamina: bool = False) -> tuple[int, int]:
        if bypass_stamina or self.stamina_current <= 0:
            self.wounds -= amount
            return 0, amount
        absorbed = min(self.stamina_current, amount)
        self.stamina_current -= absorbed
        remainder = amount - absorbed
        if remainder > 0:
            self.wounds -= remainder
        return absorbed, remainder


@dataclass
class Monster(Creature):
    """Beasts and unintelligent foes.

    - No Stamina; all damage hits Wounds directly (the default
      ``absorb_damage`` is correct).
    - ``hd`` is Hit Dice. Per LotFP, attack bonus = HD; we keep
      ``attack_bonus`` on the base class and just default it from HD in
      the factory functions in ``scenarios``.
    - ``natural_attacks`` allows multi-attack rounds. If empty, the
      monster uses ``self.weapon`` like any other creature.
    - Monsters die outright on wounds <= 0 (no injury table).
    """

    hd: int = 1
    natural_attacks: list[Weapon] = field(default_factory=list)
