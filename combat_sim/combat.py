"""Round loop, attack resolution, critical injuries, damage routing.

This is the only module that mutates creature state during a fight.
Everything else (items, AI strategies, conditions, party layout) is
data or pure functions.

The attack pipeline is intentionally split into small named pieces so
that future rules slot in without rewriting the core:

    ac_against(...)             — defender AC, with condition hooks
                                  and the Unaware AC formula
    collect_to_hit_mods(...)    — every named contribution to the roll
    optional_attack_rules(...)  — rules applied on top of the base
                                  formula (length, outnumber, ...)
                                  — comment any of these out to test
                                  the system without that rule
    resolve_attack(...)         — orchestrates the pipeline

Rule references in comments point to docs/Encounters/Combat Actions.md
and docs/Adventuring/Hazards/Damage.md.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Callable
from collections import Counter

from .dice import Dice
from .stats import length_to_hit_mod, outnumber_bonus, HitModifier
from .creatures import DEAD, Character
from .geometry import FT_PER_SQUARE
from .actions import (
    Action, AttackAction, CounterAttackAction,
    MultiAttackAction, FullDefenceAction, PassAction,
    MoveAction, MoveAndAttackAction,
)

if TYPE_CHECKING:
    from .creatures import Creature
    from .party import Party, Engagement
    from .items import Weapon


# ---------------------------------------------------------------------------
# Context + result types
# ---------------------------------------------------------------------------

@dataclass
class CombatContext:
    dice: Dice
    engagement: "Engagement"
    round_no: int = 0
    log: list[str] = field(default_factory=list)
    acted_this_round: set[int] = field(default_factory=set)
    injuries: Counter = field(default_factory=Counter)
    deaths: Counter = field(default_factory=Counter)
    # Optional observer fired after each creature's action resolves —
    # used by the UI to refresh the rendered view between actors so
    # AI moves don't appear as teleports. Signature:
    #   on_action(actor, action, ctx) -> None
    # Leave as None to opt out (headless / batch runs).
    on_action: Optional[
        "Callable[[Creature, Action, CombatContext], None]"
    ] = None

    def note(self, line: str) -> None:
        self.log.append(line)

    def mark_acted(self, creature) -> None:
        self.acted_this_round.add(id(creature))

    def has_acted(self, creature) -> bool:
        return id(creature) in self.acted_this_round


@dataclass
class AttackResult:
    attacker: "Creature"
    defender: "Creature"
    hit: bool = False
    damage: int = 0
    aborted_by_counter: bool = False
    counterattack: Optional["AttackResult"] = None
    injury: Optional[str] = None
    location: Optional[str] = None


@dataclass
class CombatResult:
    rounds: int
    winner: Optional[str]
    log: list[str]
    injuries: Counter = field(default_factory=Counter)
    deaths: Counter = field(default_factory=Counter)


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------

def counterattack_eligible(defender, attacker_weapon, ctx: CombatContext) -> bool:
    """Per Combat Actions.md: defender must be Trained, must not have
    acted this round, and must wield a melee weapon of equal-or-longer
    length than the weapon currently being swung at them."""
    if ctx.has_acted(defender):
        return False
    if not defender.is_trained:
        return False
    w = defender.weapon
    if w is None or w.is_ranged:
        return False
    if attacker_weapon is None:
        return False
    return w.length >= attacker_weapon.length


# ---------------------------------------------------------------------------
# Defender AC — condition-aware
# ---------------------------------------------------------------------------

def _any_condition_unaware(defender) -> bool:
    return any(c.unaware(defender) for c in defender.conditions)


def _condition_defend_bonus(defender, attacker, weapon, ctx, is_ranged) -> int:
    return sum(c.on_defend(defender, attacker, weapon, ctx, is_ranged)
               for c in defender.conditions)


def ac_against(defender, attacker, weapon, ctx, is_ranged: bool) -> int:
    """Compute defender's AC for this incoming attack.

    Honors the Unaware rule (base AC + AR only) and any active
    defensive conditions (Full Defence, etc.).
    """
    if _any_condition_unaware(defender):
        # Per Combat Actions table: Unaware target only retains
        # Armour Rating and Base AC. No Agi, no WS, no shield.
        base = (11 if is_ranged else defender.base_ac)
        return base + defender.armor.ar
    ac = defender.ac_ranged if is_ranged else defender.ac_melee
    ac += _condition_defend_bonus(defender, attacker, weapon, ctx, is_ranged)
    return ac


# ---------------------------------------------------------------------------
# Optional attack rules — pluggable, additive modifiers
# ---------------------------------------------------------------------------

def length_rule(attacker, defender, weapon, ctx, is_ranged) -> HitModifier | None:
    if is_ranged or weapon is None:
        return None
    d_weapon = defender.weapon
    d_len = d_weapon.length if (d_weapon and not d_weapon.is_ranged) else 0
    mod = length_to_hit_mod(weapon.length, d_len, unarmed=(weapon is None))
    if mod == 0:
        return None
    return HitModifier("Length", mod)


def outnumber_rule(attacker, defender, weapon, ctx, is_ranged,
                  *, extras: int) -> HitModifier | None:
    val = outnumber_bonus(extras)
    if val == 0:
        return None
    return HitModifier(f"Outnumber({extras+1}v1)", val)


def unaware_target_rule(attacker, defender, weapon, ctx, is_ranged) \
        -> HitModifier | None:
    if _any_condition_unaware(defender):
        return HitModifier("UnawareTarget", 2)
    return None


def range_band_rule(attacker, defender, weapon, ctx, is_ranged) \
        -> HitModifier | None:
    """Apply -2/-4 (or -4/-8 for firearms) at medium/long range.

    No-op when there is no battlefield (current default for legacy
    scenarios — every shot is treated as short range)."""
    if not is_ranged or weapon is None:
        return None
    if ctx.engagement.battlefield is None:
        return None
    dist_ft = ctx.engagement.distance_to(attacker, defender) * FT_PER_SQUARE
    if dist_ft <= weapon.range_short:
        return None
    if dist_ft <= weapon.range_medium:
        return HitModifier("RangeMedium",
                           -4 if weapon.firearm else -2)
    if dist_ft <= weapon.range_long:
        return HitModifier("RangeLong",
                           -8 if weapon.firearm else -4)
    return None  # out of range — should have been filtered by candidates


# ---------------------------------------------------------------------------
# Modifier collection
# ---------------------------------------------------------------------------

def collect_to_hit_mods(attacker, defender, weapon, ctx: CombatContext,
                       *, is_ranged: bool, outnumber_extras: int = 0) \
        -> list[HitModifier]:
    """Walk every contribution to the attacker's to-hit roll.

    This is the single place where the attack formula is composed.
    To add a new modifier rule (cover, mounted, charging, drunk, ...)
    write a function returning HitModifier|None and append its result
    here. To *disable* the length rule (for testing), comment out the
    one line.
    """
    mods: list[HitModifier] = []

    # --- core stats ----------------------------------------------------
    if is_ranged:
        if attacker.bs:
            mods.append(HitModifier("BS", attacker.bs))
        if attacker.agi_mod:
            mods.append(HitModifier("Agi", attacker.agi_mod))
    else:
        if attacker.ws:
            mods.append(HitModifier("WS", attacker.ws))
        if attacker.str_mod:
            mods.append(HitModifier("Str", attacker.str_mod))

    if attacker.attack_bonus:
        mods.append(HitModifier("HD/Bonus", attacker.attack_bonus))

    # --- optional pluggable rules --------------------------------------
    if (m := length_rule(attacker, defender, weapon, ctx, is_ranged)):
        mods.append(m)
    if (m := outnumber_rule(attacker, defender, weapon, ctx, is_ranged,
                            extras=outnumber_extras)):
        mods.append(m)
    if (m := unaware_target_rule(attacker, defender, weapon, ctx, is_ranged)):
        mods.append(m)
    if (m := range_band_rule(attacker, defender, weapon, ctx, is_ranged)):
        mods.append(m)

    # --- condition hooks (attacker side) ------------------------------
    for cond in attacker.conditions:
        m = cond.on_attack_out(attacker, defender, weapon, ctx, is_ranged)
        if m:
            mods.append(m)

    return mods


# ---------------------------------------------------------------------------
# Critical-injury table
# ---------------------------------------------------------------------------

def _roll_injury(defender, ctx: CombatContext) -> tuple[str, str]:
    """Per Damage.md: 1d4 + |neg wounds|, with location 1d4."""
    neg = max(0, -defender.wounds)
    total = ctx.dice.d(4) + neg
    if total <= 3:
        kind = "knockout"
    elif total <= 5:
        kind = "minor"
    elif total <= 7:
        kind = "permanent"
    else:
        kind = "death"
    loc = {1: "head", 2: "torso", 3: "arm", 4: "leg"}[ctx.dice.d(4)]
    ctx.injuries[kind] += 1
    return kind, loc


def _counterattack_aborts_blow(kind: str, location: str) -> bool:
    """Per user clarification: arm cut off, leg crushed, head permanent,
    or outright death aborts the original swing."""
    if kind == "death":
        return True
    if kind == "permanent" and location in ("arm", "leg", "head"):
        return True
    return False


# ---------------------------------------------------------------------------
# Attack resolution
# ---------------------------------------------------------------------------

def resolve_attack(attacker, defender, ctx: CombatContext, *,
                  weapon: "Weapon | None" = None,
                  is_counter: bool = False,
                  outnumber_extras: int = 0) -> AttackResult:
    w = weapon if weapon is not None else attacker.weapon
    is_ranged = bool(w and w.is_ranged)
    result = AttackResult(attacker=attacker, defender=defender)

    # 1. Counterattack opportunity (melee only, not on a counter)
    if not is_ranged and not is_counter:
        if (defender.ai is not None
                and counterattack_eligible(defender, w, ctx)):
            reaction = defender.ai.decide(
                defender, ctx,
                trigger=AttackAction(target=defender, weapon=w),
                source=attacker,
            )
            if isinstance(reaction, CounterAttackAction):
                counter = resolve_attack(defender, attacker, ctx, is_counter=True)
                ctx.mark_acted(defender)
                result.counterattack = counter
                if counter.hit and counter.injury is not None:
                    if _counterattack_aborts_blow(counter.injury,
                                                  counter.location or ""):
                        result.aborted_by_counter = True
                        return result
                if counter.hit and not attacker.is_combat_capable:
                    result.aborted_by_counter = True
                    return result

    # 2. AC + AR-ignore
    ac = ac_against(defender, attacker, w, ctx, is_ranged)
    if is_ranged and w is not None and w.ar_ignore:
        ac -= min(w.ar_ignore, defender.armor.ar)

    # 3. To-hit modifier collection
    mods = collect_to_hit_mods(attacker, defender, w, ctx,
                              is_ranged=is_ranged,
                              outnumber_extras=outnumber_extras)
    total_bonus = sum(m.value for m in mods)

    natural_roll = ctx.dice.d(20)
    if natural_roll == 1:
        _apply_post_attack_effects(attacker, w, ctx, fired_ranged=is_ranged)
        return result
    total = natural_roll + total_bonus
    if natural_roll != 20 and total < ac:
        _apply_post_attack_effects(attacker, w, ctx, fired_ranged=is_ranged)
        return result

    result.hit = True

    # 4. Damage
    dmg = ctx.dice.roll(w.damage) if w else 1
    result.damage = dmg

    # 5. Stamina bypass via condition (e.g. Surprised)
    bypass = any(c.bypasses_stamina(defender, ctx) for c in defender.conditions)

    # 6. Apply damage / injury / death
    pre_negative = defender.wounds < 0
    if pre_negative:
        # Any damage when below 0 = instant death (Damage.md)
        defender.wounds = DEAD
        result.injury = "death"
        ctx.deaths[defender.name] += 1
        _on_death(defender, ctx)
        _apply_post_attack_effects(attacker, w, ctx, fired_ranged=is_ranged)
        return result

    defender.absorb_damage(dmg, bypass_stamina=bypass)

    if defender.wounds < 0 and isinstance(defender, Character):
        kind, loc = _roll_injury(defender, ctx)
        result.injury = kind
        result.location = loc
        if kind == "death":
            defender.wounds = DEAD
            ctx.deaths[defender.name] += 1
            _on_death(defender, ctx)
    elif defender.wounds <= 0 and not isinstance(defender, Character):
        defender.wounds = DEAD
        result.injury = "death"
        ctx.deaths[defender.name] += 1
        _on_death(defender, ctx)

    _apply_post_attack_effects(attacker, w, ctx, fired_ranged=is_ranged)
    return result


def _on_death(creature, ctx: CombatContext) -> None:
    """Clean up positional state when a creature dies.

    Dead bodies are removed from the battlefield so they don't block
    movement through their square. A future refinement could leave them
    as 'difficult terrain' — for v1 they simply vanish.
    """
    bf = ctx.engagement.battlefield
    if bf is not None and creature.position is not None:
        bf.deregister(creature)


def _apply_post_attack_effects(attacker, weapon, ctx: CombatContext,
                              *, fired_ranged: bool) -> None:
    """Things that happen *after* an attack resolves, regardless of
    hit/miss. Currently: trigger reload if a ranged weapon with a
    reload time was fired."""
    if not fired_ranged or weapon is None:
        return
    if weapon.reload_rounds <= 0:
        return
    # Matchlock-style reload: base - BS - Agi, floor 1.
    needed = max(1, weapon.reload_rounds - attacker.bs - attacker.agi_mod)
    from .conditions import Reloading
    attacker.add_condition(Reloading(weapon, needed))


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------

def _execute(action: Action, actor, ctx: CombatContext) -> None:
    if isinstance(action, MultiAttackAction):
        for sub in action.attacks:
            if not actor.is_combat_capable:
                return
            target = sub.target if sub.target.is_combat_capable \
                     else ctx.engagement.target_of(actor)
            if target is None:
                return
            extras = ctx.engagement.outnumbering_against(target) - 1
            resolve_attack(actor, target, ctx,
                          weapon=sub.weapon, outnumber_extras=extras)
        return

    if isinstance(action, AttackAction):
        target = action.target if action.target.is_combat_capable \
                 else ctx.engagement.target_of(actor)
        if target is None:
            return
        weapon = action.weapon if action.weapon is not None else actor.weapon
        if not actor.can_use_weapon(weapon, ctx):
            return  # e.g. reloading
        extras = ctx.engagement.outnumbering_against(target) - 1
        resolve_attack(actor, target, ctx,
                      weapon=weapon, outnumber_extras=extras)
        return

    if isinstance(action, MoveAction):
        bf = ctx.engagement.battlefield
        if bf is None:
            return  # no positioning in play; silently no-op
        from .movement import validate_move
        if not validate_move(actor, action.destination, bf):
            return  # illegal move — silently dropped (UI is expected
                    # to pre-validate before submitting)
        actor.move_to(action.destination, bf)
        return

    if isinstance(action, MoveAndAttackAction):
        bf = ctx.engagement.battlefield
        if bf is not None:
            from .movement import validate_move
            if validate_move(actor, action.destination, bf):
                actor.move_to(action.destination, bf)
            else:
                return  # illegal move; the bundled attack is also
                        # dropped (RAW: attack happens after the move)
        _execute(action.attack, actor, ctx)
        return

    if isinstance(action, FullDefenceAction):
        from .conditions import FullDefence
        bonus = 4 if actor.is_trained else 2
        actor.add_condition(FullDefence(bonus))
        return

    if isinstance(action, PassAction):
        return


# ---------------------------------------------------------------------------
# Initiative + round loop
# ---------------------------------------------------------------------------

def _initiative(parties: tuple["Party", "Party"], ctx: CombatContext) \
        -> tuple["Party", "Party"]:
    while True:
        a = ctx.dice.d(6)
        b = ctx.dice.d(6)
        if a != b:
            return (parties[0], parties[1]) if a > b else (parties[1], parties[0])


def _tick_round_end(parties: tuple["Party", "Party"], ctx: CombatContext) -> None:
    for side in parties:
        for member in side.members:
            if not member.conditions:
                continue
            member.conditions = [
                c for c in member.conditions
                if not c.on_round_end(member, ctx)
            ]


def run_round(parties: tuple["Party", "Party"], ctx: CombatContext) -> None:
    ctx.round_no += 1
    ctx.acted_this_round.clear()

    first, second = _initiative(parties, ctx)

    for side in (first, second):
        for member in list(side.combat_capable):
            if ctx.has_acted(member):
                continue
            if not member.is_combat_capable:
                continue
            # Condition hook: turn-start override (Surprised, Stunned, ...)
            override: Action | None = None
            for cond in member.conditions:
                result = cond.on_turn_start(member, ctx)
                if result is not None:
                    override = result
                    break

            if override is not None:
                action = override
            else:
                # AI picks its own target; if there are no enemies left,
                # the AI returns PassAction.
                if not ctx.engagement.enemies_of(member):
                    continue
                action = member.ai.decide(member, ctx)
            _execute(action, member, ctx)
            if ctx.on_action is not None:
                ctx.on_action(member, action, ctx)
            ctx.mark_acted(member)

    _tick_round_end(parties, ctx)


def run_combat(party_a: "Party", party_b: "Party",
              engagement: "Engagement", *,
              dice: Dice, max_rounds: int = 60) -> CombatResult:
    ctx = CombatContext(dice=dice, engagement=engagement)
    while (not party_a.is_defeated and not party_b.is_defeated
           and ctx.round_no < max_rounds):
        run_round((party_a, party_b), ctx)

    winner: Optional[str] = None
    if party_a.is_defeated and party_b.is_defeated:
        winner = None
    elif party_a.is_defeated:
        winner = party_b.name
    elif party_b.is_defeated:
        winner = party_a.name
    return CombatResult(rounds=ctx.round_no, winner=winner, log=ctx.log,
                       injuries=ctx.injuries, deaths=ctx.deaths)
