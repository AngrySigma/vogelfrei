# Subsystems Vogelfrei rebuilt

The source text was written for a different chassis. These are the places
where a spell's mechanics stop meaning what they meant. **Report, never
rescale.**

## Wounds and Stamina replace Hit Points

`docs/Adventuring/Hazards/Damage.md`. Two pools, not one:

- **Stamina** — trained reflex. All damage depletes Stamina first; only the
  excess reaches Wounds. Monsters and unintelligent creatures have none, so
  they take everything straight to Wounds.
- **Wounds** — actual injury. Losing Wounds also strips an equal amount of
  Stamina.

Bypasses Stamina entirely: unaware targets, helpless/paralyzed targets,
critical hits (natural 20), poison, falling. Area effects — explosions,
**spell blasts**, breath weapons — do **not** bypass Stamina if the target
is mobile and aware.

### The scale — check which pool the damage reaches

At level 6, against the LotFP hit point pool the source assumes:

| | Wounds | + Stamina | LotFP HP | Wounds alone | Combined |
|---|---|---|---|---|---|
| Warrior / Fighter | ~12 | ~15 | ~30 | **39%** | 89% |
| Magic-User | ~5 | ~9 | ~16 | **32%** | 90% |

At level 1 the pools are near-identical (Warrior 7 vs 8, Magic-User 3 vs 3);
they diverge as levels climb.

So the *combined* pool tracks the source closely — **ordinary damage that
runs through Stamina first is roughly proportionate, and does not
automatically need rescaling.** Area effects (explosions, spell blasts,
breath) explicitly do **not** bypass Stamina, so blast spells are the
milder case.

The problem is concentrated where Stamina is skipped:

- **Damage that bypasses Stamina** — poison above all, plus effects on
  unaware, helpless or paralyzed targets — lands on a pool about **a third**
  the size the source was balanced against. Roughly three times as lethal.
- **Healing** restores Wounds directly and so is worth about **three times**
  what the source intended. A `1d6+level` heal covers a Warrior's entire
  Wound track by 5th level.
- **Per-level damage** still outruns the Wound track, which barely grows —
  a Magic-User gains a Wound at level 3 and again at 6, and nothing else.

Report the pool the effect reaches and the level at which it outgrows it.
Do not rescale.

At **0 Wounds or fewer** a character rolls on the critical injury table
(1d4 + Wounds below zero); further damage kills instantly.

## Armor Class is composed, not absolute

`docs/Encounters/Combat Actions.md`. AC is precomputed from parts:

- **Melee** — 8 (base) + Agility Bonus + Weapon Skill + Armour Rating + shield
- **Ranged** — 11 (base) + Agility Bonus + Armour Rating

Armour Rating runs 2–6 (`docs/Equipment/Armor.md`). A LotFP absolute grant
("the spell grants AC 19") has no slot here — it must become an explicit
**bonus**, and split Melee/Ranged if the source distinguishes missiles from
other attacks.

Vogelfrei states outright that armour makes the wearer **harder to hit, not
damage-resistant**. Any spell granting flat damage reduction contradicts
that principle — report it even though it is easy to transcribe.

## Unchanged — do not report these

- **Hit Dice** still exist and still work for monsters. `Sleep` keeps its
  `4+1 HD` threshold and `2d8 HD` budget verbatim.
- **Saving throws** — five categories, same as the source:
  **Paralyze · Poison · Breath · Device · Magic**. Only report a save the
  source names outside this set.
- Turn/Round/Turn units, silver-standard `sp`, `Referee`.

## Precedents already in the docs

How the user has settled these before. Follow the pattern; still report.

| Spell | Source | Converted to |
|---|---|---|
| `Shield` | "grants AC 19, effective AC 17 for other attacks" | "**+5 bonus to Armour Class**" vs missiles, "**+3**" vs all other — absolute AC became a split bonus |
| `Magic Missile` | `1d4`/level | **`1d3`**/level — damage scaled down for the Wounds pool |
| `Turn Undead` | undead HD 1–7 | table extended to **HD 1–15** |
| `Sleep` | Hit Dice thresholds | kept verbatim — HD is not a divergence |

### An open one worth knowing

`Cure Light Wounds` currently reads "restores **1d6 Wounds** … 1d6+5 at 5th
level" — a straight word swap from the source's Hit Points, with no
rescaling. Against a Warrior's ~7 Wounds that is a full heal from a
first-level miracle. Healing spells are the mirror of the damage problem and
have **not** been settled; report every one.

## Source text

Parsed LotFP corpus at `~/personal/lotfp-parsed/` — `spells.json`
(structured: `name`, `class`, `level`, `meta`, `body`, page numbers) and
`spells.md` (readable). 202 descriptions.

- **Lost Dweomer** (Magic-User 9) is in the source's index but has no
  description anywhere in the book — nothing to convert.
- **Dispel Magic** is described twice, for Cleric 3 and Magic-User 3, with
  different text. Both convert, to their own pages.
