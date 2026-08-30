# Combat Actions

Each character can perform a single action on their turn. These given options certainly do not contain an exhaustive list of possible actions. The Referee has the final say in what can or cannot be done in one Round.

---
## Move
A character can move their full movement rate at any round using either normal movement speed, or running one. In case the Character is running through reach of any opponent who did not yet act that turn, they may perform an attack against the Character. That attack costs the opponent their action for the Round, and can be declared as a wrestling attempt.

If the Character moves their normal combat distance, they can perform a usual Attack afterwards.

!!! note
    Attack or other action always end the Character's Round, and they cannot move afterwards.

---
## Flee!
When one character or party is running from another, it is not merely a matter of movement rate which decides the outcome unless the chase is over open territory. Otherwise, both sides in a pursuit roll 1d20 and add their movement rate divided by 10. For example, characters with 120' movement roll d20+12. The higher roll wins. Individual rolls for those with different movement rates can be used at the Referee's discretion. You do not have to outrun the enemy, you just have to outrun your slowest ally!

No mapping or other record keeping is allowed during a pursuit. The Referee will declare in general terms where the character goes. "You run down the corridor, past two doors, and duck to the left in a passageway," is a perfectly fine description in a dungeon, with the character not being told details along the way. After all, the character has been running for his life with a flickering light source through hostile territory! Wilderness pursuit will be rather less mysterious of course.

Dropping items or money or treasure or food might make pursuers break off pursuit, depending on why they are pursuing. If a character drops valuable goods, or treasure, in the path of treasure-seeking enemies, those enemies must make a Morale check to stop pursuit. If an unintelligent creature is pursuing, then food is what it wants, and the appropriate food dropped causes a Morale check, with failure meaning the creature stops to eat the food. Dropping an obstacle, such as flaming oil, will normally stop pursuit as well.

**Long pursuits**: in case the parties are divided far enough, the Referee may decide on an initial chase distance. In that case, rolls are compared, and the difference applies to the distance number changing it to appropriate side. Once the distance reaches 0, the chasing side wins. Fleeing side wins once the distance reaches any number assigned by the Referee. Chase can also end for many other reasons: one party might not be able to continue moving due to dead end or a forbidden territory, or the time and resources may come to an end in Wilderness.

---
## Attack
When a Character makes an attack, follow these steps:

1. *Declare and Move*
    - The Character may move up to their normal combat speed.
    - They may make an attack against one enemy within range at any point during their movement.

2. *Determine Opponent's AC*
    A defender's AC is normally a static, precomputed number on the character sheet — built from the following components — so resolving an attack is just a single subtraction against the attacker's roll.

    In **Melee** add the following statistics of the Opponent:
    - 8 (Base AC)
    - Agility Bonus
    - Weapon Skill
    - Armour Rating
    - Shield or off-hand modifier

    In **Ranged** use the following:
    - 11 (Base AC)
    - Agility Bonus
    - Armour Rating

    Most non-human opponents do not use any arms and armour, but their base AC may vary greatly from very high for small agile creatures to almost zero for colossal ones.

3. *Roll for Attack*
    - The attacking player rolls **d20**.
    - Add **Weapon Skill** to the roll in **Melee** or **Ballistic Skill** in **Ranged**
    - Apply **Strength Bonus** to the roll in **Melee** or **Agility Bonus** in **Ranged**
    - Apply **Weapon Length** modifier 

    | Weapon Length vs. Opponent | To Hit Bonus |
    | -------------------------- | ------------ |
    | Longer weapon              | 0            |
    | Equal length               | 0            |
    | Shorter weapon             | -2           |
    | Unarmed                    | -4           |

    The reach advantage of a longer weapon is not a to-hit bonus — it is the penalty the shorter weapon pays to work its way past. This table applies **at measure**, the distance at which a fight opens. A fighter who gets inside a longer weapon escapes it entirely, and can turn it against its owner; see [Measure and Reach](Measure%20and%20Reach.md).

    - Compare the result to the Opponent's AC. **If the roll equals or exceeds the AC, the attack lands.**

4. *Calculate Damage*
    - Roll the **Weapon Damage** die to determine damage dealt.

Damage rules are detailed in [Damage](../Adventuring/Hazards/Damage.md) Section.

### Natural 1 and 20

A **natural 20** on an attack roll always hits, whatever the target's AC and whatever the modifiers, and deals normal damage. A **natural 1** always misses. This mirrors the convention already used for saving throws.

!!! note "Double damage"
    Wherever this book calls for double damage — a Mounted Charge, a braced weapon receiving a charge — roll the weapon's damage dice **twice** and total the result. Double damage is applied normally, depleting Stamina first.

??? example
    **Attacker — Kurt:** Weapon Skill 4, Strength Bonus +1, Short sword (Small, length 2, 1d6)

    **Defender — Hans:** Weapon Skill 2, Agility Bonus +2, Rapier (length 4, 1d8), Light Armour (AR 2)

    **Hans's AC:** 8 (base) + 2 (Agility) + 2 (Weapon Skill) + 2 (Armour Rating) = **14**

    *Kurt is using the shorter weapon, so he rolls d20 and adds Weapon Skill (4) + Strength Bonus (+1) + Weapon Length (-2) = +3:*

    - *Roll = 5: total 8 — miss.*
    - *Roll = 11: total 14 — hit. The total need only **match** the AC, not beat it.*
    - *Roll = 18: total 21 — hit. Kurt rolls 1d6 for damage.*
    - *Roll = 1: miss regardless of the total.*
    - *Roll = 20: hit regardless of the total. Kurt rolls his 1d6 damage as usual.*

    **Now suppose Hans answers.** Kurt declares his attack; before any dice are rolled, Hans declares a **Counterattack**. His rapier is a proper weapon for it and he has not yet acted.

    Hans's Weapon Skill no longer counts toward his AC, which drops to **12** — so Kurt now hits on a roll of 9 rather than 11. In exchange, Hans strikes at the same moment: d20 + Weapon Skill (2) + Weapon Length (0, his rapier is longer) against Kurt's AC.

    Both blows land together. If each kills the other, both die — Hans has bought a guaranteed answer with the opening in his guard.

---

| Special Condition                           | Effect                                                                                              |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Attacking an Unaware Opponent               | +2 to attack roll; target only retains Armour Rating and Base AC                                   |
| Attacking a Prone Opponent                  | +4 to attack roll in Melee; −4 to attack roll in Ranged                                            |
| Attacking an Opponent with WS 1+ and a proper weapon | Opponent may spend their action to Counterattack (see below)                                   |
| Natural 20 on the attack roll               | Always hits                                                                                         |
| Natural 1 on the attack roll                | Always misses                                                                                       |
| Fighting inside an Opponent's reach         | Weapon Length does not apply; a weapon 2+ grades longer deals only d3                               |
| Attacking a Helpless Opponent               | Automatically deal maximum weapon damage in Melee                                                   |
| Outnumbering two-on-one                     | +2 to attack roll                                                                                   |
| Outnumbering three-on-one                   | +4 to attack roll                                                                                   |
| Wrestling in Team                           | +1 per additional attacker; only the best roll applies                                              |
| Firing into Melee                           | −4 to attack roll; if the penalty causes a miss, a random engaged character is hit instead          |
| Firing into a Crowd                         | +1 to attack roll per target after the first; hit target is determined randomly                     |
| Attacking after an Aiming Round             | +2 to attack roll; Attacker's Agility Bonus does not apply to their own AC while Aiming            |
| Ranged attack against quarter cover         | +2 to target's AC                                                                                   |
| Ranged attack against half cover            | +4 to target's AC                                                                                   |
| Ranged attack against three-quarter cover   | +8 to target's AC                                                                                   |
| Ranged attack against full cover            | +10 to target's AC                                                                                  |
| Fighting in darkness                        | −4 to attack roll; ranged attacks miss; all incoming attacks treat the target as Unaware            |
| Mounted combat                              | −4 to ranged attack rolls; +1 to melee attack roll and −1 to Opponent's AC; double damage after running |

### Counterattack
Your enemies do not stand still while you cut them. A character attacked in melee, who has **Weapon Skill 1 or better**, holds a **proper weapon**, and has **not yet acted** this Round, may declare a Counterattack. They strike back at the same moment as the blow aimed at them.

- The Counterattack must be declared **before the attack roll is made**. A defender who waits to see whether the blow lands has waited too long.
- It costs the Defender their action for the Round. They cannot act again on their own initiative.
- For the rest of the Round, the Defender's **Weapon Skill does not count toward their AC** — every attacker benefits, not just the one they answered. They still add Weapon Skill to the Counterattack roll itself.
- Both attacks are resolved and their damage applied **simultaneously**, exactly as with tied [Initiative](Initiative.md). A dying man's arm still finishes its stroke, and two fighters can quite easily kill one another.

Otherwise the Counterattack is an ordinary attack: Weapon Length, reach, and every other modifier apply as usual.

!!! tip "A proper weapon"
    A Counterattack demands a weapon you can check mid-stroke and send back along another line. A sword, a rapier, a staff, even a zweihander in trained hands — all fine. A club, an axe, a pike, a flail, or whatever you snatched off the table is not: once it is swinging, it goes where it was sent. The Referee has the final say, and should rule on how the weapon is *used*, not on what the table calls it.

!!! note "Why anyone would"
    The Defender's AC drops and the Attacker's does not, so striking first is still better than waiting to answer — initiative keeps its value. What the Counterattack buys is certainty: a blow that cannot be pre-empted, landing even if it kills you. Answer a foe who might drop you in one hit; do not answer a mob.

### Brace
A character wielding a weapon long enough to be set against an approach — a Polearm, a Spear in both hands, or a Lance on foot — may spend their action to Brace it.

Until the character's next turn, they attack **simultaneously** with the **first** enemy who reaches them, striking [at measure](Measure%20and%20Reach.md) as that enemy closes the distance. If that enemy was **charging** — running to reach them — the braced weapon deals **double damage**.

Only the first enemy is met this way. A braced pike is a terrible thing to run onto, and no help at all against the second man behind him.

!!! note
    An opponent who spends their action attempting to get **inside** the braced weapon's reach is an enemy reaching the wielder, and triggers the Brace. Closing on a set spear is exactly as unwise as it sounds — though a Close attempt at a walk is not a charge, and does not suffer the doubling.

### Change Weapons and Attack
If a character is not holding the weapon that he wants to use, he can drop what is in his hands and draw a weapon (assuming the weapon is in an accessible place such as on a belt scabbard). There is a –2 penalty to their attack roll during the Round that this happens.

### Wrestling
A character may attempt to wrestle another character to either immobilize or take something out of that character's hands. The attacker must have both hands free or wield a weapon effective for wrestling. A defender who is armed and has not yet acted may answer with a [Counterattack](#counterattack) on the usual terms — it costs their action and their Weapon Skill no longer counts toward their AC — resolved simultaneously with the wrestling attempt.

Wrestling is resolved with a contested roll. Both parties roll 1d20 and apply both their Weapon Skill and Strength modifier. Ties are decided by Agility modifier, or a die roll if both are still tied. The winner decides whether the loser is immobilized, if he will attempt to disarm the loser of the contest, or if he releases the loser. An immobilized opponent can usually take no action other than attempting to escape on his next action, but can instead attack a wrestling opponent with natural or minor weapons. Resolve this with another wrestling roll. Any character immobilized for three successive wrestling contests is considered pinned and helpless — no further attempts to escape can be made. If disarmament is attempted (and this includes snatching any held object, not just taking away weapons), the defender must make a save versus Paralyzation to keep hold of the object that his attacker is attempting to take.

If there are multiple opponents attempting to wrestle a single defender, all attackers make their rolls as normal, but only the best roll is used with a +1 bonus for each additional attacker. Creatures whose physiology or special abilities suggest that they have an advantage when wrestling (tentacles, adhesive, multiple limbs) gain a further +1 bonus to their wrestling roll per Hit Die.

### Subdue
A character can try to beat an intelligent opponent senseless rather than kill them — for ransom, for questioning, or for the watch. The intent must be declared before the attack, and only **blunt blows** qualify: bludgeons, fists, a pommel, or the flat of a blade. Bladed weapons used flat-side suffer a −2 penalty to the attack roll.

Attack and damage are rolled normally, but **subdual damage** is noted separately from real damage. It depletes Stamina first like any other damage; an opponent whose Wounds would be reduced to 0 by subdual damage instead falls senseless or surrenders, having understood perfectly well that the victor could have killed them. No injury is rolled and there is no risk of death. Subdual damage fades quickly — all of it recovers after an hour of rest.

### Full Defence
Characters can decide to focus entirely on defence at the expense of all other activity. A player is free to declare Full Defence at any point during the Round, even out of Initiative sequence, provided that the character has not yet acted. This adds +2 to the Character's AC for the Round, or +4 AC if the Character has Weapon Skill 1 or better.

### Mounted Combat
Mounted characters receive +1 to their melee attack rolls (unless using Minor or Small weapons) and reduce the Opponent's AC by 1 when in melee combat against enemies on foot. Mounted characters suffer a −4 penalty to ranged attack rolls while mounted. A Mounted Charge deals double damage.

---
## Ranged
Ranged attacks follow the same steps as melee but use **Ballistic Skill + Agility Bonus** and a base AC of 11. Several conditions specific to ranged combat are described below.

### Aiming
If using a missile weapon, a character can decide to take a full Round to aim. While Aiming, the Character's Agility Bonus does not apply to their own AC. On the following Round, the Character gains +2 to their attack roll when firing. Aiming time is in addition to normal reload times.

### Cover
Cover is protection behind something that can actually block incoming attacks. Each tier adds to the target's AC, making them harder to hit:

- **Quarter cover (+2 AC):** Bushes, curtains — obscures vision more than it blocks projectiles.

- **Half cover (+4 AC):** Shallow trenches, thin wooden hedges — partially blocks line of sight or presents moderate protection.

- **Three-quarter cover (+8 AC):** Deep trenches, mantlets — conceals most of the body or stops serious projectiles.

- **Full cover (+10 AC):** Arrow slits, murder holes in stone — virtually no line of attack remains.

### Firing into Melee
Firing into melee with a missile weapon is a very uncertain thing. The Character suffers −4 to their attack roll. If the attack misses solely because of this penalty, it still hits — but the target is determined randomly among all engaged characters.

Significantly larger characters or monsters in a mêlée count as two characters for random targeting purposes, and truly gargantuan creatures can be fired upon using the normal rules.

### Firing into Crowds
A Character may choose to fire into a group of targets standing together. They gain +1 to their attack roll for each target after the first. If the attack hits, the target is determined randomly among all characters in the group.

Significantly larger characters or monsters in a mêlée count as two characters for random targeting purposes, and truly gargantuan creatures can be fired upon using the normal rules.

---
## Cast a Spell
Casting a spell during combat is a very risky proposition because the caster leaves himself completely helpless and open to attack while doing so. Magic-Users must be able to speak freely to cast a spell. Clerics must also have their holy symbol in one hand for the entire Round.

Spells take effect at the beginning of the next Round, before the Initiative is rolled. Because the effect is delayed, a caster who is struck *after* casting but before the spell resolves loses the spell entirely — it is expended with no effect. If a character has already taken any damage earlier in a Round, they cannot begin casting a spell that Round.

---
## Use an Item
Character might want to use some item in their possession, taking time according with the item availability:

| Item availability       | Time to get ready |
| ----------------------- | ----------------- |
| In hands or on the belt | None              |
| In a pouch              | 1d3 Rounds        |
| In a sack or a backpack | 3d6 Rounds        |

During this time, the Character can be attacked as an Unaware Opponent; if the Character defends themselves with their normal AC, the Round does not count as searching for an item as they are concentrating on avoiding being hit rather than readying the desired item. It is not a good idea to sit there and rifle through one's pack while somebody is trying to kill you.

---
## Hold Action
Sometimes winning the Initiative over a foe is not all that advantageous because it is important to know what the opponent is going to do before deciding for oneself. Any action can be held until the end of the Round, and at the time the action is taken, it happens simultaneously, not before other actions are taken. For instance, if waiting for an enemy to close later in the Round before attacking, when that enemy closes both attacks happen simultaneously; the one holding his action does not act first.

Waiting with a weapon half-raised costs something: a held action suffers **−2** when it is finally taken.

The Character must name the **trigger** when the action is held — an enemy closing, a caster beginning his incantation, a door opening. Holding an action is a prediction, not a reaction; a defender who wants to answer a blow already aimed at him is making a [Counterattack](#counterattack), and pays for it in AC rather than accuracy.
