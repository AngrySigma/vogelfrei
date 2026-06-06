"""Scenario library + aggregate runner.

A Scenario carries: a short ``key``, a ``description`` printed with
results so the reader knows what they're looking at, and a ``builder``
that takes a Dice and returns ``(party_a, party_b)`` ready to fight.

Adding a scenario: define a builder, wrap it in Scenario(...), register
in SCENARIOS.

Monster AC defaults — set per species, not from a single global default:
    Goblin   14   small, agile, hard to pin down
    Bandit   8    human; computed from armor/agility
    Bear     12   slow but tough hide
"""

from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter
from typing import Callable

from .dice import Dice
from .creatures import Character, Monster
from .items import (
    SMALL, MEDIUM_1H, MEDIUM_2H, GREAT, RAPIER, SPEAR_1H, SPEAR_2H,
    POLEARM, MINOR, IMPROVISED,
    SHORT_BOW, LONG_BOW, HEAVY_XBOW, LIGHT_XBOW, MUSKET, PISTOL,
    NO_ARMOR, WAMS, BUFF_COAT, CHAIN, HALF_PLATE, FULL_PLATE,
    NO_OFFHAND, BUCKLER, SHIELD,
    CLAW_D4, CLAW_D6, BITE_D6, BITE_D8,
    Weapon,
)
from .ai import BerserkerAI, DuellistAI, CautiousAI, GunnerAI, KitingAI
from .conditions import Surprised
from .party import Party, Engagement
from .battlefield import Battlefield
from .combat import run_combat


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

def warrior(name: str, *, weapon: Weapon, armor=NO_ARMOR, offhand=NO_OFFHAND,
            ws: int = 1, bs: int = 1,
            str_mod: int = 0, agi_mod: int = 0,
            wounds: int = 8, stamina: int = 2,
            ai=None) -> Character:
    return Character(
        name=name,
        wounds_max=wounds,
        stamina_max=stamina,
        ws=ws, bs=bs,
        str_mod=str_mod, agi_mod=agi_mod,
        weapon=weapon, armor=armor, offhand=offhand,
        ai=ai or DuellistAI(),
    )


def peasant(name: str, dice: Dice, *, weapon: Weapon = MINOR) -> Character:
    return Character(
        name=name,
        wounds_max=max(1, dice.d(4)),
        stamina_max=0,
        ws=0, bs=0,
        weapon=weapon,
        ai=BerserkerAI(),
    )


def monster(name: str, dice: Dice, *, hd: int, die: int = 6,
            base_ac: int = 8, agi_mod: int = 0,
            weapon: Weapon | None = None,
            natural_attacks: list[Weapon] | None = None,
            ai=None) -> Monster:
    wounds = sum(dice.d(die) for _ in range(hd))
    return Monster(
        name=name,
        wounds_max=max(1, wounds),
        base_ac=base_ac,
        agi_mod=agi_mod,
        attack_bonus=hd,
        hd=hd,
        weapon=weapon or SMALL,
        natural_attacks=natural_attacks or [],
        ai=ai or BerserkerAI(),
    )


# species-tuned monster shortcuts
def goblin(name: str, dice: Dice) -> Monster:
    """1 HD, d4 wounds, AC 14 (small + agile), Small weapon, +1 to hit."""
    return monster(name, dice, hd=1, die=4, base_ac=14, weapon=SMALL)


def bandit(name: str, dice: Dice, *, hd: int = 2,
           weapon: Weapon = SMALL, armor=NO_ARMOR) -> Monster:
    """Humanoid bandit. Uses human-style AC (base 8 + armor)."""
    m = monster(name, dice, hd=hd, die=6, base_ac=8, weapon=weapon)
    # mutate armor after construction (Monster inherits Creature.ac_melee)
    m.armor = armor
    return m


def black_bear(name: str, dice: Dice) -> Monster:
    """6 HD, d6 wounds, AC 12 (tough hide, slow), 2 claws + bite, +6 to hit."""
    return monster(name, dice, hd=6, die=6, base_ac=12,
                   natural_attacks=[CLAW_D4, CLAW_D4, BITE_D6])


# ---------------------------------------------------------------------------
# Scenario type
# ---------------------------------------------------------------------------

BattleSetup = tuple[Party, Party, Engagement]


@dataclass
class Scenario:
    key: str
    description: str
    builder: Callable[[Dice], BattleSetup]


def _pair(pa: Party, pb: Party, bf: Battlefield | None = None) -> BattleSetup:
    return pa, pb, Engagement(pa, pb, battlefield=bf)


# ---------------------------------------------------------------------------
# Scenario builders — return (party_a, party_b, engagement)
# ---------------------------------------------------------------------------

def s1_matched_smallweapon(dice: Dice) -> BattleSetup:
    return _pair(
        Party("A", [warrior("Hans", weapon=SMALL)]),
        Party("B", [warrior("Kurt", weapon=SMALL)]),
    )


def s1b_spear_vs_small(dice: Dice) -> BattleSetup:
    return _pair(
        Party("Spear", [warrior("Hans", weapon=SPEAR_2H)]),
        Party("Small", [warrior("Kurt", weapon=SMALL)]),
    )


def s2_armored_standoff(dice: Dice) -> BattleSetup:
    return _pair(
        Party("A", [warrior("Hans", weapon=SMALL, armor=CHAIN, offhand=SHIELD)]),
        Party("B", [warrior("Kurt", weapon=SMALL, armor=CHAIN, offhand=SHIELD)]),
    )


def s3_medium_vs_small(dice: Dice) -> BattleSetup:
    return _pair(
        Party("Medium", [warrior("Hans", weapon=MEDIUM_2H)]),
        Party("Small", [warrior("Kurt", weapon=SMALL)]),
    )


def s7_musket_vs_plate(dice: Dice) -> BattleSetup:
    g = warrior("Soldat", weapon=MUSKET, bs=1, ws=1, armor=WAMS,
                ai=GunnerAI())
    k = warrior("Ritter", weapon=MEDIUM_2H, armor=FULL_PLATE)
    return _pair(Party("Gunner", [g]), Party("Knight", [k]))


def s7b_xbow_vs_plate(dice: Dice) -> BattleSetup:
    c = warrior("Crossbowman", weapon=HEAVY_XBOW, bs=1, ws=1, armor=WAMS,
                ai=GunnerAI())
    k = warrior("Ritter", weapon=MEDIUM_2H, armor=FULL_PLATE)
    return _pair(Party("Xbow", [c]), Party("Knight", [k]))


def s9_lone_warrior_vs_2hd(dice: Dice) -> BattleSetup:
    return _pair(
        Party("Warrior", [warrior("Albrecht", weapon=MEDIUM_2H,
                                   armor=CHAIN, offhand=SHIELD)]),
        Party("Bandit", [bandit("Bandit", dice, hd=2)]),
    )


def s9b_party_vs_bear(dice: Dice) -> BattleSetup:
    members = [warrior(f"W{i}", weapon=MEDIUM_2H, armor=CHAIN, offhand=SHIELD)
               for i in range(4)]
    return _pair(Party("Party", members),
                 Party("Bear", [black_bear("Bear", dice)]))


def c8_aborting_counter(dice: Dice) -> BattleSetup:
    return _pair(
        Party("Duellist", [warrior("Duellist", weapon=RAPIER,
                                    agi_mod=1, ws=2)]),
        Party("Brawler", [warrior("Brawler", weapon=SMALL,
                                   ws=1, str_mod=1)]),
    )


def c10_goblin_ambush(dice: Dice) -> BattleSetup:
    pcs = [warrior("Karl", weapon=MEDIUM_2H, armor=WAMS, offhand=BUCKLER),
           warrior("Otto", weapon=SPEAR_2H, armor=WAMS)]
    goblins = [goblin(f"Gob{i}", dice) for i in range(4)]
    return _pair(Party("PCs", pcs), Party("Goblins", goblins))


def c10s_goblin_surprise(dice: Dice) -> BattleSetup:
    pcs = [warrior("Karl", weapon=MEDIUM_2H, armor=WAMS, offhand=BUCKLER),
           warrior("Otto", weapon=SPEAR_2H, armor=WAMS)]
    for p in pcs:
        p.add_condition(Surprised())
    goblins = [goblin(f"Gob{i}", dice) for i in range(4)]
    return _pair(Party("PCs", pcs), Party("Goblins", goblins))


# ---------------------------------------------------------------------------
# Positioned scenarios — opt in to Battlefield
# ---------------------------------------------------------------------------

def s11_archer_kites(dice: Dice) -> BattleSetup:
    """Open 100x10 field. Skilled archer (BS 2, Agi +1, KitingAI) in the
    centre, lightly-armoured swordsman at one end. With matched movement
    the archer cannot outrun the swordsman forever — but the long field
    gives many rounds of kiting and shooting before being cornered.
    Direct comparison with a static GunnerAI on the same map would
    isolate the value of kiting vs. standing still."""
    bf = Battlefield(width=100, height=10)
    a = warrior("Archer", weapon=LONG_BOW, bs=2, ws=1, agi_mod=1,
                ai=KitingAI())
    b = warrior("Swordsman", weapon=MEDIUM_2H, armor=WAMS, offhand=BUCKLER)
    bf.register(a, (50, 5))
    bf.register(b, (0, 5))
    return _pair(Party("Archer", [a]), Party("Swordsman", [b]), bf)


def s12_musket_with_range(dice: Dice) -> BattleSetup:
    """Direct comparison to S7: matchlock musket gunner vs full-plate
    knight, but placed at short range (8 squares = 40 ft). One shot
    with no range penalty, ar_ignore 5 → effective ranged AC = 12. Then
    the knight closes in one round and we get S7's bad reload situation,
    but at least the one shot lands meaningfully."""
    bf = Battlefield(width=15, height=5)
    g = warrior("Soldat", weapon=MUSKET, bs=1, ws=1, armor=WAMS,
                ai=GunnerAI())
    k = warrior("Ritter", weapon=MEDIUM_2H, armor=FULL_PLATE)
    bf.register(g, (0, 2))
    bf.register(k, (8, 2))
    return _pair(Party("Gunner", [g]), Party("Knight", [k]), bf)


def m1_pillar_detour(dice: Dice) -> BattleSetup:
    """POSITIONED — A* showcase. A wall column at x=7 (y=2..7) sits
    between PC and goblin. The direct east-west line is blocked; both
    must detour through the gap at the top or bottom of the column.

    Greedy step planning (the pre-A* primitive) would stall here: from
    (6, 5) walking east, the ideal step (7, 5) is wall, both cardinal
    alternatives (7, 4) and (7, 6) are also wall, and step_toward
    returned None — *stuck*. A* sees the column from a distance, plans
    a detour through y=1 or y=8, and the fight resolves.
    """
    width, height = 15, 10
    walls = {(7, y) for y in range(2, 8)}
    bf = Battlefield(width=width, height=height, blocked=walls)
    pc = warrior("Karl", weapon=MEDIUM_2H, armor=WAMS, offhand=BUCKLER)
    gob = goblin("Gob", dice)
    bf.register(pc, (3, 5))
    bf.register(gob, (12, 5))
    return _pair(Party("PC", [pc]), Party("Goblin", [gob]), bf)


def c13_corridor_choke(dice: Dice) -> BattleSetup:
    """Two PCs in a 1-square-wide corridor against 4 goblins. Walls on
    y=0 and y=2 force a single-file line so only one attacker engages
    at a time. Outnumbering bonus is neutered. Compare to C10."""
    width = 12
    walls = {(x, 0) for x in range(width)} | {(x, 2) for x in range(width)}
    bf = Battlefield(width=width, height=3, blocked=walls)
    pcs = [warrior("Karl", weapon=MEDIUM_2H, armor=WAMS, offhand=BUCKLER),
           warrior("Otto", weapon=SPEAR_2H, armor=WAMS)]
    goblins = [goblin(f"Gob{i}", dice) for i in range(4)]
    bf.register(pcs[0], (0, 1))
    bf.register(pcs[1], (1, 1))
    bf.register(goblins[0], (11, 1))
    bf.register(goblins[1], (10, 1))
    bf.register(goblins[2], (9, 1))
    bf.register(goblins[3], (8, 1))
    return _pair(Party("PCs", pcs), Party("Goblins", goblins), bf)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, Scenario] = {
    s.key: s for s in [
        Scenario("S1",
            "Two equal level-1 Warriors, unarmored, both wielding Small "
            "weapons (length 2, d6). Pure symmetry check — should produce ~50/50.",
            s1_matched_smallweapon),
        Scenario("S1b",
            "Same matchup but A wields Spear 2H (length 5, d6) vs B's Small "
            "(length 2, d6). Identical damage dice; only difference is reach. "
            "Tests whether length flip + counterattack actually helps the "
            "longer weapon when damage is held constant.",
            s1b_spear_vs_small),
        Scenario("S2",
            "Two equal warriors, Chain + Shield, Small weapons. Heavy-armor "
            "standoff — measures how much armor lengthens a fight.",
            s2_armored_standoff),
        Scenario("S3",
            "Medium 2H (length 3, d8) vs Small (length 2, d6). Length flip + "
            "damage advantage combined. Expect Medium ~75% win rate.",
            s3_medium_vs_small),
        Scenario("S7",
            "Matchlock musket gunner (wams) vs full-plate knight in melee "
            "range. Gunner fires (d10, ignores 5 AR), then must reload for "
            "10 - BS - Agi rounds while the knight chops him. Tests whether "
            "one shot is enough.",
            s7_musket_vs_plate),
        Scenario("S7b",
            "Heavy crossbow (d8, ignores 3 AR, reload 2) vs full-plate "
            "knight in melee. Two shots before the knight kills him?",
            s7b_xbow_vs_plate),
        Scenario("S9",
            "Lone chain+shield Warrior with Medium 2H vs single 2-HD bandit "
            "(human stats, SMALL weapon, +2 to hit). Baseline 'is level-1 PC "
            "competent vs 2 HD?'",
            s9_lone_warrior_vs_2hd),
        Scenario("S9b",
            "Four chain+shield Warriors vs a black bear (6 HD, ~21 W, AC 12, "
            "+6 to hit, 2 claws + bite per round). Wilderness encounter "
            "stress test — does the party survive, and at what cost?",
            s9b_party_vs_bear),
        Scenario("C8",
            "Rapier-duellist (length 4, WS 2, Agi +1) vs Small-weapon "
            "brawler (length 2, WS 1, Str +1). Maximal counterattack "
            "pressure; measures how often the 'permanent injury aborts the "
            "blow' rule actually fires.",
            c8_aborting_counter),
        Scenario("C10",
            "Two armored PCs (Medium 2H + buckler, Spear 2H) vs four goblins "
            "(AC 14, 1 HD d4, +1 to hit, Small). No surprise. Baseline for "
            "the surprise variant below.",
            c10_goblin_ambush),
        Scenario("C10s",
            "Same matchup, but the PCs begin Surprised: they skip round 1 "
            "and incoming attacks bypass Stamina and use the Unaware AC "
            "formula (base + AR only, no Agi/WS/shield). Direct comparison "
            "with C10 measures the cost of surprise.",
            c10s_goblin_surprise),
        Scenario("S11",
            "POSITIONED. 100x10 open field. Skilled longbow archer (BS 2, "
            "Agi +1, KitingAI) in the centre vs a wams+buckler swordsman "
            "advancing from the edge. With room to retreat, kiting + "
            "range bands turn the fight in the archer's favour despite "
            "matched movement speeds.",
            s11_archer_kites),
        Scenario("S12",
            "POSITIONED. 15x5 field. Musket gunner at one end, full-plate "
            "knight 8 squares away. Even with positioning, the musket's "
            "single shot + 10-round reload cycle is brutal against plate. "
            "Direct counterpart to S7 — shows that range alone doesn't "
            "save a one-shot weapon against a melee threat that can close "
            "in one round.",
            s12_musket_with_range),
        Scenario("C13",
            "POSITIONED. Two PCs in a 1-square-wide corridor vs 4 goblins. "
            "Terrain forces single-file combat: only the lead PC and lead "
            "goblin engage at a time. Outnumbering bonus is gone, BUT the "
            "rear PC cannot help until the front PC falls — a double-edged "
            "geometry. Compare to C10's 49.5%.",
            c13_corridor_choke),
        Scenario("M1",
            "POSITIONED — A* showcase. A 6-square wall column sits "
            "between a PC and a goblin on a straight east-west line. "
            "Greedy step planning would have stalled (ideal step + both "
            "cardinal alternatives are all walls). A* sees the obstacle "
            "and detours through the gap.",
            m1_pillar_detour),
    ]
}


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------

@dataclass
class ScenarioStats:
    scenario: Scenario
    n: int
    a_wins: int = 0
    b_wins: int = 0
    draws: int = 0
    total_rounds: int = 0
    a_remaining_wounds: int = 0
    b_remaining_wounds: int = 0
    a_alive_members: int = 0
    b_alive_members: int = 0
    injuries: Counter = field(default_factory=Counter)
    deaths: int = 0

    @property
    def a_winrate(self) -> float:
        return self.a_wins / max(1, self.n)

    @property
    def b_winrate(self) -> float:
        return self.b_wins / max(1, self.n)

    @property
    def draw_rate(self) -> float:
        return self.draws / max(1, self.n)

    @property
    def mean_rounds(self) -> float:
        return self.total_rounds / max(1, self.n)

    def pretty(self) -> str:
        desc_wrapped = _wrap(self.scenario.description, width=72, indent="    ")
        parts = [
            f"--- {self.scenario.key} ---",
            desc_wrapped,
            "",
            f"  n={self.n}",
            f"  A wins: {self.a_winrate:6.1%}   "
            f"B wins: {self.b_winrate:6.1%}   "
            f"draws: {self.draw_rate:6.1%}",
            f"  Mean rounds: {self.mean_rounds:.2f}",
            f"  Avg A wounds remaining: {self.a_remaining_wounds/max(1,self.n):.2f}",
            f"  Avg B wounds remaining: {self.b_remaining_wounds/max(1,self.n):.2f}",
            f"  Avg A standing: {self.a_alive_members/max(1,self.n):.2f}   "
            f"Avg B standing: {self.b_alive_members/max(1,self.n):.2f}",
        ]
        if self.injuries:
            inj = ", ".join(
                f"{k} {v/max(1,self.n):.2f}/fight"
                for k, v in sorted(self.injuries.items())
            )
            parts.append(f"  Injuries per fight: {inj}")
        if self.deaths:
            parts.append(f"  Deaths per fight: {self.deaths/max(1,self.n):.2f}")
        return "\n".join(parts)


def _wrap(text: str, *, width: int = 72, indent: str = "") -> str:
    import textwrap
    return textwrap.fill(text, width=width,
                         initial_indent=indent, subsequent_indent=indent)


def run_scenario(scenario_key: str, *, n: int = 10_000,
                 seed: int = 0) -> ScenarioStats:
    sc = SCENARIOS[scenario_key]
    stats = ScenarioStats(scenario=sc, n=n)
    for i in range(n):
        dice = Dice(seed + i)
        party_a, party_b, engagement = sc.builder(dice)
        result = run_combat(party_a, party_b, engagement, dice=dice)
        if result.winner == party_a.name:
            stats.a_wins += 1
        elif result.winner == party_b.name:
            stats.b_wins += 1
        else:
            stats.draws += 1
        stats.total_rounds += result.rounds
        stats.a_remaining_wounds += party_a.total_wounds_remaining()
        stats.b_remaining_wounds += party_b.total_wounds_remaining()
        stats.a_alive_members += len(party_a.combat_capable)
        stats.b_alive_members += len(party_b.combat_capable)
        for k, v in result.injuries.items():
            stats.injuries[k] += v
        stats.deaths += sum(result.deaths.values())
    return stats
