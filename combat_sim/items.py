"""Weapons, armor, off-hand items.

Frozen dataclasses — items themselves never mutate. A creature *holds*
items; it does not own a unique copy of "Wams". The catalog at the
bottom of the module is the single source of truth and can be imported
directly into scenario builders.

To add a new weapon, define it here. To express a *quality* (silvered,
masterwork, blessed) wrap or extend the dataclass — do not mutate the
base catalog entry.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Weapon:
    name: str
    damage: str            # dice spec, e.g. "1d6"
    length: int            # 0..5
    is_ranged: bool = False
    requires_trained: bool = False
    range_short: int = 0
    range_medium: int = 0
    range_long: int = 0
    ar_ignore: int = 0     # AR ignored at all ranges
    ar_ignore_short: int = 0  # AR ignored only at short range (firearms)
    reload_rounds: int = 0  # base reload time; modified by BS+Agi at fire time
    firearm: bool = False   # if True, triggers Morale check on enemies <=7 morale


@dataclass(frozen=True)
class Armor:
    name: str
    ar: int


@dataclass(frozen=True)
class OffHand:
    name: str
    melee_ac_bonus: int = 0
    ranged_ac_bonus: int = 0


# --- Melee catalog -----------------------------------------------------------

IMPROVISED = Weapon("Improvised", "1d3", 0)
MINOR = Weapon("Minor", "1d4", 1)
SMALL = Weapon("Small", "1d6", 2)
MEDIUM_1H = Weapon("Medium (1H)", "1d4", 2, requires_trained=True)
MEDIUM_2H = Weapon("Medium (2H)", "1d8", 3, requires_trained=True)
GREAT = Weapon("Great", "1d10", 4, requires_trained=True)
SPEAR_1H = Weapon("Spear (1H)", "1d4", 4, requires_trained=True)
SPEAR_2H = Weapon("Spear (2H)", "1d6", 5, requires_trained=True)
RAPIER = Weapon("Rapier", "1d8", 4, requires_trained=True)
POLEARM = Weapon("Polearm", "1d8", 5, requires_trained=True)
STAFF = Weapon("Staff", "1d6", 4)

# --- Ranged catalog ----------------------------------------------------------

SHORT_BOW = Weapon("Short Bow", "1d6", 0, is_ranged=True, requires_trained=True,
                   range_short=50, range_medium=300, range_long=450,
                   reload_rounds=0)
LONG_BOW = Weapon("Long Bow", "1d6", 0, is_ranged=True, requires_trained=True,
                  range_short=50, range_medium=600, range_long=900,
                  reload_rounds=0)
LIGHT_XBOW = Weapon("Light Crossbow", "1d6", 0, is_ranged=True,
                    range_short=50, range_medium=150, range_long=400,
                    ar_ignore=1, reload_rounds=1)  # fires every other round
HEAVY_XBOW = Weapon("Heavy Crossbow", "1d8", 0, is_ranged=True, requires_trained=True,
                    range_short=50, range_medium=200, range_long=600,
                    ar_ignore=3, reload_rounds=2)  # fires every third round

# --- Firearms ---------------------------------------------------------------

# Matchlock musket base reload = 10 rounds, modified by BS+Agi at fire time.
MUSKET = Weapon("Musket", "1d10", 0, is_ranged=True, requires_trained=True,
                range_short=50, range_medium=100, range_long=600,
                ar_ignore=5, reload_rounds=10, firearm=True)
PISTOL = Weapon("Pistol", "1d8", 0, is_ranged=True,
                range_short=25, range_medium=50, range_long=100,
                ar_ignore=5, reload_rounds=10, firearm=True)

# --- Natural attacks (monsters) ---------------------------------------------

CLAW_D4 = Weapon("Claw", "1d4", 2)
CLAW_D6 = Weapon("Claw", "1d6", 2)
BITE_D6 = Weapon("Bite", "1d6", 2)
BITE_D8 = Weapon("Bite", "1d8", 2)

# --- Armor catalog -----------------------------------------------------------

NO_ARMOR = Armor("None", 0)
WAMS = Armor("Wams", 2)
BUFF_COAT = Armor("Buff Coat", 2)
JACK_CHAIN = Armor("Jack Chain", 3)
CHAIN = Armor("Chain", 4)
BRIGANDINE = Armor("Brigandine", 4)
HALF_PLATE = Armor("Half-armour", 4)
THREE_QUARTER = Armor("Three-quarter armour", 5)
FULL_PLATE = Armor("Full-plate", 6)

# --- Off-hand ----------------------------------------------------------------

NO_OFFHAND = OffHand("None")
BUCKLER = OffHand("Buckler", melee_ac_bonus=2)
SHIELD = OffHand("Shield", melee_ac_bonus=2, ranged_ac_bonus=3)
PAVISE = OffHand("Pavise", ranged_ac_bonus=5)
