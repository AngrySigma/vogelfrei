# LotFP → Vogelfrei terminology

Derived by comparing the 32 converted pages against the LotFP *Rules & Magic*
source. **Settled** mappings are applied silently. Everything else is
reported.

## Settled — apply without asking

| LotFP | Vogelfrei | Note |
|---|---|---|
| Cleric spell | **Miracle** | directory, index title and prose |
| Fighter | **Warrior** | |
| Specialist | **Rogue** | |
| Elf | **High Elf** / **Wood Elf** | two classes; ask which if the text depends on it |
| Lawful / Law | **Orderly** / **Order** | |
| Evil (alignment sense) | **Chaos** / **Chaotic** | `Detect Evil` → `Detect Chaos`, `Protection from Evil` → `Protection from Chaos` |
| `&` in a spell name | **and** | `Purify Food & Drink` → `Purify Food and Drink` |
| mêlée | **melee** | 36 uses vs 5; prefer `melee` |
| Armor Class / AC | **Armor Rating** | link it: `[Armor Rating](../../../../../Equipment/Armor.md)` |
| Magical Device (save) | **Device** | |
| Breath Weapon (save) | **Breath** | |

Unchanged: `Referee`, `Magic-User`, `Hit Dice`, silver-standard `sp`,
`saving throw versus <category>`, Turn/Round/Turn units.

## Saving throws

Vogelfrei uses five categories, as in the class tables:

**Paralyze · Poison · Breath · Device · Magic**

Write `saving throw versus Magic` (the dominant form, 19 uses) over
`save versus Magic`.

## Alignment

**Order · Neutrality · Chaos** (`docs/Character/Alignment.md`). There is no
Good/Evil axis. Clerics must be Orderly; Magic-Users and Elves must be
Chaotic — a spell keyed to a caster's alignment may need a ruling, so report
it.

## Where the docs already disagree with themselves

Not caused by conversion — flag if you touch a page containing one, but do
not mass-fix them without being asked.

| Split | Counts | Preferred |
|---|---|---|
| `Armor Rating` / `Armor Class` | 9 / 2 | `Armor Rating` |
| `melee` / `mêlée` | 36 / 5 | `melee` |
| `Armor` / `Armour` | mixed | follow the target page |
| `Paralyze` (tables) / `Paralyzation` (prose) | — | unresolved, report |
| `Referee` / `GM` | 54 / 4 | `Referee` |

## Known deliberate rebalances

Vogelfrei intentionally differs from LotFP here. **Never overwrite these**
with source values.

| Spell | LotFP | Vogelfrei |
|---|---|---|
| Magic Missile | 1d4/level | **1d3**/level |
| Turn Undead | undead HD 1–7 | table extended to **HD 1–15** |

Treat any other numeric difference on an existing page as possibly
deliberate too: keep the page's value and report it.

## Source text

The parsed LotFP corpus lives outside the repo at `~/personal/lotfp-parsed/`
(`spells.json` structured, `spells.md` readable) — 202 descriptions with
`name`, `class`, `level`, `meta`, `body`, and printed page numbers.

Two source facts worth knowing:

- **Lost Dweomer** (Magic-User 9) is listed in LotFP's index but has no
  description anywhere in the book — there is nothing to convert.
- **Dispel Magic** is described twice, separately for Cleric 3 and
  Magic-User 3, with different text. Both convert, to their own pages.
