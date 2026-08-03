# Damage

### Stamina

Stamina represents the ability of a trained character to control a dangerous situation: to duck at the last moment, roll with a blow, twist away from a blade, and keep fighting despite exhaustion. It is not the same as physical toughness — it is the hard-won awareness and reflex of someone who has survived many fights. After several battles with no rest, Stamina runs out. The next hit lands clean.

!!! important "Battle-ready"
    **Stamina is a separate pool from Wounds.** All incoming damage depletes Stamina first. Only when Stamina reaches 0 does excess damage carry over into Wounds. A character with Stamina remaining cannot be pushed below 0 Wounds in a single hit unless the damage exceeds both pools combined.

!!! danger "A wound takes the fight out of you"
    **Whenever a character loses Wounds, they lose an equal amount of Stamina**, to a minimum of 0. Torn flesh does not leave a fighter's readiness intact: a knife in the kidney costs you both the blood and the will to keep dancing.

    This matters most for damage that skips the Stamina pool entirely. A poisoned or ambushed character cannot be driven to their last Wound and then carry on fighting fresh — the wound strips their Stamina with it, and the next ordinary blow goes straight to the bone.

!!! tip "Beast Nature"
    **Only intelligent, trained beings have Stamina.** Monsters and unintelligent creatures do not — all damage they receive goes directly to their Wounds. Their durability comes from toughness, size, and natural armour, not from experience or readiness.

#### What bypasses Stamina

Not all damage can be avoided through skill. The following sources go directly to Wounds, ignoring Stamina entirely:

- **Attacking an unaware target** — the victim has no opportunity to react (see [Combat Actions](../../Encounters/Combat%20Actions.md))

- **Attacking a helpless or paralyzed target** — the body cannot answer; skill is irrelevant

- **Critical hits** — a natural 20 finds the gap no amount of readiness can close (see [Combat Actions](../../Encounters/Combat%20Actions.md#critical-hits))

- **Poison and venoms** — physiological; no amount of experience stops a toxin already in the blood

- **Falling** — too fast for trained reflexes to intercept; see [Environmental](Environmental.md) for the exception available to certain careers

Area effects — explosions, spell blasts, breath weapons, collapsing ceilings — **do not** bypass Stamina, provided the character is mobile and aware. A soldier who rolls clear of a fireball, or dives from a dragon’s breath, is burning Stamina to do so. If the character is helpless or pinned when the area effect hits, Stamina is bypassed as normal.

---
### Damage

When a character (or creature) suffers damage, the amount is deducted from Stamina first; only once Stamina is exhausted does damage reduce Wounds. Any Wounds lost carry an equal loss of Stamina with them, whether the damage arrived through the Stamina pool or bypassed it.

A character reduced to **0 Wounds or fewer** cannot carry equipment or stand, and can do nothing but crawl at a movement rate of 10'. They may instead spend a single action — casting a spell, or standing up to move and attack — after which they faint for 1d6 hours.

Being reduced to 0 Wounds or fewer also causes a **critical injury**. Roll 1d4 and add the number of Wounds below zero the character has reached. For example, a character with 2 Wounds who takes 4 damage is driven to -2 Wounds and rolls 1d4+2. Any damage received while already at 0 Wounds or fewer kills the character instantly.

!!! note "Examples assume no Stamina"
    Every damage example in this book is written as though the character has already been reduced to 0 Stamina. Stamina always depletes first, so a character with Stamina remaining absorbs the blow there instead and never reaches the Wounds column at all.

| Roll Total | Effect                         |
| ---------- | ------------------------------ |
| 1-3        | Knocked out. No lasting damage |
| 4-5        | Minor wound                    |
| 6-7        | Permanent injury               |
| 8+         | Death                          |

#### Determine target location

Severity tells you how bad the injury is; location tells you where it landed. Roll 1d6 for the region struck, then roll on that region's table for the exact spot. The Referee narrates what that means in play.

| d6  | Region |
| --- | ------ |
| 1   | Head   |
| 2-3 | Torso  |
| 4-5 | Arm    |
| 6   | Leg    |

| d6 | Head        | Torso    | Arm (d2: primary / secondary) | Leg (d2: left / right) |
| -- | ----------- | -------- | ----------------------------- | ---------------------- |
| 1  | Scalp       | Shoulder | Shoulder joint                | Hip                    |
| 2  | Face        | Chest    | Upper arm                     | Thigh                  |
| 3  | Jaw         | Ribs     | Elbow                         | Knee                   |
| 4  | Ear         | Gut      | Forearm                       | Shin                   |
| 5  | Eye         | Back     | Wrist                         | Ankle                  |
| 6  | Skull       | Spine    | Hand                          | Foot                   |
