---
name: character-generation
description: Generate a complete level-1 Vogelfrei player character (stats, class and career, alignment, bio, name, equipment, AC). Use when asked to create, roll, or generate a character, PC, NPC, or pregen for Vogelfrei.
---

# Vogelfrei character generation

Produces a finished level-1 character following the rulebook's creation
order (docs/Character/index.md). Dice, table lookups and validation are
scripted; you (the agent) make only the judgement calls: class/career
choice, equipment selection, and names when no list fits.

Conventions:

- Run everything from the repository root with `python3`. In the commands
  below `$S` = `.claude/skills/character-generation/scripts`.
- All state lives in one JSON file passed as `--file`. Put it in
  `characters/` (gitignored), e.g. `characters/kurt.json`.
- Every roll script accepts `--seed N` for reproducibility. Do not set it
  for real characters — let the dice fall.
- The scripts parse class pages, career pages and equipment tables straight
  from `docs/`, so they are the authority on numbers. Never compute prices,
  saves or AC yourself; if you believe a script contradicts the rulebook,
  report it instead of overriding silently.

## Step 0 — read the request

Determine before rolling:

- **Mode**: if the request says "quick", "pregen", "pregenerated", "fast",
  "batch" or similar — **quick mode**: never ask the player anything, make
  every choice yourself. Otherwise **interactive mode**: confirm the class
  decision (step 2) with the player; everything else only if genuinely
  unclear.
- **Preferences**: class(es) or career(s); culture/name/sex/age; alignment
  wish (only free classes can use it); any equipment wishes.

## Step 1 — roll abilities

```
python3 $S/roll_stats.py --file characters/<slug>.json [--reroll-unsuitable]
```

3d6 in order. Pass `--reroll-unsuitable` in quick mode. In interactive mode
run it bare: if the modifier total comes out negative, tell the player they
may discard by the book and ask whether to reroll (`--force` to overwrite).

## Step 2 — choose class and career

```
python3 $S/class_options.py --file characters/<slug>.json
```

This ranks all twelve classes for the rolled array, suggests the single
two-score swap that would most improve each, and lists careers with Status
(Gold/Silver/Brass — that is the starting-money bracket). A character is
allowed **one** swap of two ability scores, ever; it is applied in step 3,
so treat it as part of the class decision.

- **2a. No preference given**: pick from the top of the ranking, weighing
  the notes (forced alignment, Magic-User armour ban, wounds die) and any
  personality the request implies. Interactive mode: present the 2–3 best
  class+career combinations (with the swap each would use and one line of
  why) and let the player choose. Quick mode: decide yourself, prefer the
  best mechanical fit with a Status that can afford its concept.
- **2b. Preference given**: make the preferred class/career work, using the
  swap if that fixes a weak key ability. If the array still fights the
  preference (key modifiers negative even after the best swap), say so and
  propose the closest-fitting alternatives from the ranking — interactive:
  ask; quick: pick the preference anyway if merely mediocre, or the best
  alternative if it is truly hopeless, and note why on the sheet.
- The rulebook default is *rolling* class (2d6) and career (d6):
  `class_options.py --roll` does both. Use it when the request asks for a
  by-the-book random character.

## Step 3 — apply class, career, alignment, money

```
python3 $S/apply_class.py --file characters/<slug>.json \
    --class Warrior --career Mercenary [--swap str int] [--alignment chaos]
```

One command fills wounds, stamina, saves, WS/BS, skill points, alignment
(Clerics are forced Order; Magic-Users and Elves forced Chaos; others
default Neutral) and rolls starting money by career Status. Some career
pages are still blank on Status — the script will stop and ask for
`--status brass|silver|gold`; judge from the career's social standing.

## Step 4 — bio and name

```
python3 $S/roll_bio.py  --file characters/<slug>.json [--sex male] [--age 30]
python3 $S/roll_name.py --file characters/<slug>.json [--culture scotland] [--pick]
```

Bio (sex, age, height, build) is scripted; pass overrides the player gave.
Default naming culture is 17th-century England, with built-in period lists
for England, Wales, Scotland and Ireland. Other cultures go through the
randomuser.me API; if the culture is unmapped or the network is down the
script exits with code 3 — then invent a period-appropriate name yourself
and record it with `--set 'Name'`. Interactive: show candidates and let the
player choose; quick: `--pick`.

## Step 5 — buy equipment

Browse the rulebook hierarchically instead of dumping full lists: start at
`docs/Equipment/index.md` for the category overview, then open only the
category pages the concept needs ("a musketeer? open Firearms and Armor").
`python3 $S/buy.py catalog [Category]` gives exact purchasable names and
parsed prices when you need them.

Record every purchase — this is the validation layer (budget, ambiguous
names, city/rural pricing, encumbrance flags):

```
python3 $S/buy.py --file characters/<slug>.json add "Buff Coat"
python3 $S/buy.py --file characters/<slug>.json add "Rations (Standard/Day)" --qty 5
python3 $S/buy.py --file characters/<slug>.json list
```

Guidance: characters start with free travelling clothes (don't buy them). A
sensible kit covers a weapon the character can actually use (Trained melee
weapons need WS +1, most ranged need BS +1, firearms always do), armour if
the class allows and the purse survives it, light, food, a container, and
one or two career-flavoured tools. Spend most of the purse but keep some
coin — poverty is a story, an empty purse is a problem. If an item exists
on a page but the parser missed it, record it with `--price` read off the
page. Watch encumbrance in `list`; Brass-status characters cannot afford to
be fussy.

## Step 6 — finalize and render

```
python3 $S/finalize.py --file characters/<slug>.json [--wear "Buff Coat"]
python3 $S/render_sheet.py --file characters/<slug>.json --out characters/<slug>.md
```

`finalize.py` fills armour/weapon slots, computes Melee/Ranged AC,
encumbrance and movement, and prints WARNINGs (untrained weapons,
Magic-User armour ban, no weapon). Resolve warnings by adjusting purchases
(`buy.py remove` refunds) and re-running, or keep them deliberately and
mention them to the player.

## Step 7 — class-specific finishing

Class features (spells, miracles, skill-point spending, career traits in
play) are finished by a per-class skill run on the same `--file`:

| Class | Skill |
| --- | --- |
| Warrior | `class-warrior` (.claude/skills/class-warrior/SKILL.md) |
| Magic-User | `class-magic-user` (.claude/skills/class-magic-user/SKILL.md) |
| Cleric | `class-cleric` (.claude/skills/class-cleric/SKILL.md) |
| Rogue | `class-rogue` (.claude/skills/class-rogue/SKILL.md) |
| others | none planned yet |

If the class skill exists, follow it now. If not, do the minimum by hand:
read the class index page (`class_page` in the JSON), its Special Rules
pages, and the career page (`career_page`); record starting talents,
possessions and career skills with
`python3 $S/annotate.py --file ... --note ... --skill "Name=2"`, and tell
the player which parts (e.g. spell selection) still need a follow-up.

Finally re-render the sheet and present the character: lead with who they
are in one or two sentences, then the sheet. Relay any warnings honestly.
