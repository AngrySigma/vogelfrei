---
name: party-generation
description: Generate a whole Vogelfrei party or character pack at once - N level-1 characters with party-wide constraints, rolled and planned centrally, then built in parallel by one sub-agent per character. Use when asked for a party, a pack, pregens for a table, a crew, or several Vogelfrei characters at once.
---

# Vogelfrei party generation

Builds a *pack* of characters instead of one. The work splits in two:

- **You, the lead**, do everything that has to see the whole party: read the
  constraints, roll every array, assign class / career / Status / concept so
  the roster is varied and covers the adventure, and set the equipment
  doctrine.
- **One sub-agent per character** then runs the ordinary
  `character-generation` skill (and the class skill) on its own assignment.

Each character is a separate JSON file, so the sub-agents never write to the
same state — that is what makes the fan-out safe. Do not let two agents share
a file.

Conventions:

- Run everything from the repository root with `python3`.
- `$S` = `.claude/skills/character-generation/scripts` (the per-character
  scripts), `$P` = `.claude/skills/party-generation/scripts` (these).
- The party lives in one directory under `characters/` (gitignored):
  `characters/<party-slug>/` holding `pc1.json … pcN.json`, `party.md` (the
  brief you write) and `pack.md` (the assembled output).
- Slots keep their numbered filenames for the whole run. Never rename a
  `pcN.json` — names live *inside* the JSON, and a rename breaks the
  assignment a sub-agent was handed.

## Step 1 — read the request

Settle these before rolling. They are party-wide and only you can see them:

- **Count** — how many characters.
- **Level** — these skills build level 1 only. If a higher level is asked
  for, say so and build level 1, or stop and ask.
- **Culture / setting** — e.g. "17th-century England, all human". This fixes
  the naming culture (`roll_name.py --culture`) and the class pool: all-human
  means dropping Dwarf, Halfling, High Elf and Wood Elf (`--humans-only`).
- **Class spread** — "a variety of classes and careers", "two fighters and a
  healer", or nothing. Nothing means you choose for coverage.
- **The adventure** — what the party is walking into. This drives concepts,
  motivations and, more than anything, the kit.
- **Equipment doctrine** — the party-wide kit rules: what the mission needs,
  what it does not, what is shared. A one-night raid on a tower needs light,
  rope and a crowbar, not a week of rations; a wilderness crawl is the
  reverse. Write this down — sub-agents cannot see each other's purchases, so
  shared gear must be *assigned* to named slots.
- **Alignment constraints** — watch for a conflict before you assign:
  Clerics are forced Order, Magic-Users and both Elf classes forced Chaos
  (`docs/Character/Alignment.md`). A party required to be all-Order cannot
  contain a Magic-User.

## Step 2 — roll the whole party

```
python3 $P/roll_party.py --dir characters/<party-slug> --count 8 \
    [--humans-only] [--classes "Warrior,Cleric,Rogue,..."] [--reroll-unsuitable]
```

One 3d6-in-order array per character, written to `pcN.json`. The output then
gives you everything the assignment needs:

- every array with modifiers and the by-the-book suitability total,
- a **class-fit matrix** over the allowed pool — rows are PCs, columns
  classes, so you can read the whole assignment problem off one table,
- each PC's four strongest classes with the single two-score **swap** that
  would most improve each, and the class's caveat (forced alignment, the
  Magic-User armour ban, wounds die),
- which careers are **fully written** in the rulebook vs still stubs
  (from `docs/data/careers.json`),
- the wounds/stamina/WS/BS line per class, for judging party durability.

Pass `--reroll-unsuitable` unless the request wants the dice kept honest; for
a pack of pregens, rerolling the unsuitable arrays is the kind thing to do.
Use `--seed` only if reproducibility was asked for.

## Step 3 — assign the roster

This is the judgement step and it is yours alone. Read the fit matrix and
assign each slot a class, a career, a Status, an optional swap, an alignment
and a concept. Aim for:

- **Coverage before optimisation.** A pack wants a front line, someone who
  can open a lock or spot a trap, a light source in more than one pair of
  hands, and — if the class pool allows — one source of healing or magic.
  Match the adventure: a dungeon of dead magic wants someone literate.
- **Variety, as asked.** Do not assign the same career twice unless the
  request wants a unit. Spread Status too: an all-Gold party has no texture,
  an all-Brass one fields nobody who can take a hit.
- **Fit, then concept.** Give each class to a slot the matrix likes. Where
  two slots fit equally, decide on concept.
- **Only assign careers that are actually written.** `roll_party.py` lists
  the complete ones from `docs/data/careers.json`. Before you commit a career
  a character will be built on, **open the page and look** — the flag is
  derived, and roughly two thirds of the 60 career pages are stubs. A page
  can carry a Status and nothing else: no skills, no trait, a blank six-row
  progression table. Building a PC on one produces a character sheet with a
  class name and no mechanics, which is worse than no character.
  Whole classes have nothing written: as it stands **no Townsman, Dwarf,
  Halfling, High Elf or Wood Elf career is finished**. **Rogue is the
  exception that looks like a stub and is not** — it has no careers by
  design, and everything mechanical sits on the class page.
  Also check the progression table for content the book does not have: the
  Apothecary's "+1 potion recipe" at levels 2/4/6 refers to recipes that
  exist nowhere, so that career dead-ends the moment it levels.
  If the request wants breadth the written careers cannot supply, say so and
  build the honest roster — a second differentiated character of a supported
  class beats a hollow one of a fresh class.
- **Status is the budget.** Gold starts with 1d6 gp, Silver 2d6×10 sp, Brass
  10d6×10 bp (`docs/Character/Starting Possessions.md`) — roughly 175 sp,
  70 sp and 29 sp on average. Tools are cheap at any Status (rope 3 sp,
  crowbar 2 sp, lantern 3 sp), but a Brass purse will not stretch to both
  armour and a real weapon (a buff coat is 25 sp, a medium weapon 20 sp), so
  a concept that needs both needs Silver at least. Set Status deliberately,
  especially for the stub careers and for the careerless Rogue, where the
  script has nothing to read.
- **Motivation, not a full hook.** If the request asks for characters drawn
  to a specific adventure, give each a reason to be there in a line or two —
  greed, a debt, a rumour, a missing brother, professional curiosity. Leave
  the Referee room; do not write their arc.
- **A motivation must survive round one.** Check each one against the others
  before you write it: a character whose stated reason for going is to *stop*
  what the rest of the party came to do is a fight at second zero, not a
  hook. Check it against the fiction too — a crusade against a tower nobody
  has been near in fifty years is not a motive, it is a contrivance.
- **Name the faith; never write a Cleric as established clergy.** The
  period's church is real and powerful — and a Cleric is *not* its clergy.
  They keep some older or stranger rite at its margins, hiding inside it or
  hunted by it: "different religions, and even different sects within the
  same religion, execute their magical rituals differently", and whether
  miracles are divine favour or "merely ritualized forms of sympathetic
  magic" is left openly debated (`Cleric/Special Rules/Miracles.md`). A
  Cleric commands nobody and holds no institutional authority.
  **"Keeper of a small local faith" is not a concept — it is a blank.** Name
  the god or the sect, say what it wants, give the character a cover, and use
  real regional folklore where it fits. And **roll the blessings first, then
  write the belief to explain them** (`Blessings.md`: three on 1d20 rerolling
  duplicates, or a single chosen one). Three tasteful picks tell you nothing;
  a rolled Protection/Hunt/Savagery tells you what kind of god this is.
  Nor is alignment a morality: it "does not necessarily determine a
  character's allegiance, morality or actions" (`Alignment.md`) — an Order
  Cleric and a Chaos Magic-User are on opposite cosmological sides, not
  opposite moral ones, and neither fact by itself gives a character a
  grievance.
- **Check the module against the concept.** A social specialist is dead
  weight in a dungeon with nothing in it that talks; a wilderness expert is
  dead weight in a tower. Find out what the adventure actually contains
  before you hand someone a specialism, and if a concept has no surface to
  act on, either change it or give it something to work with (a retainer,
  see `docs/Retainers/`).
- **Nobody ships at lethal Wounds.** After you fix the classes, check what
  each character's Toughness modifier does to their wounds die. A level-1 PC
  who lands on 2 Wounds dies to one hit of almost anything and is not a
  playable pregen — spend the ability swap to fix it, even at the cost of a
  score the concept liked. Swap into an ability the character genuinely does
  not use (a talker's Strength) rather than one that pays out broadly
  (Willpower feeds every non-spell save).

Then write the brief. `characters/<party-slug>/party.md` holds the shared
context, and each slot gets its own section:

```markdown
# <Party name>

**Setting**: 17th-century England, all human, all level 1.
**Adventure**: one night inside a dead wizard's tower.
**Naming culture**: england (roll_name.py --culture england)

**Equipment doctrine**
- A single night's work: no rations beyond a day's bread for two or three of them.
- Everyone carries their own light. Assign: pc1 lantern + oil, pc3 lantern, others torches.
- The party needs exactly one of each: crowbar (pc4), 50' rope (pc6), 10' pole (pc2).
- Spend most of the purse. Loot-hauling capacity matters: sacks over chests.

## pc1 — <Career> (<Class>), Status <Brass|Silver|Gold>
Swap: <A> <-> <B>  (or: none)
Alignment: <Order|Neutral|Chaos>
Concept: <two lines: who they are, why they are going into the tower>
Kit notes: <the party duties above plus anything career-specific>
```

Say explicitly in each section whether a class skill exists for that class —
`class-warrior`, `class-magic-user`, `class-cleric` and `class-rogue` do;
Ranger, Peasant, Academic and Townsman do not, and those sub-agents must fall
back to step 7 of `character-generation` (read the class and career pages and
record grants by hand with `annotate.py`).

## Step 4 — fan out, one sub-agent per character

Spawn them with the Agent tool, `subagent_type: "general-purpose"`, **all in
one message** so they run in parallel. A sub-agent starts cold: it inherits
none of this conversation, so the prompt must carry everything it needs.

Each prompt must contain:

1. The repository root and that it works **only** on
   `characters/<party-slug>/pcN.json` — never another slot's file, never the
   party brief.
2. **The abilities are already rolled. Do not run `roll_stats.py`, and do not
   reroll or edit the scores.** It starts at step 3 of
   `character-generation` (`apply_class.py`).
3. The assignment verbatim: class, career (or "no career, Rogue" with the
   Status), the swap, the alignment, the Status.
4. The concept, the motivation, and the kit notes including that slot's share
   of the shared gear.
5. The naming culture, and any sex/age constraint.
6. "Follow the `character-generation` skill from step 3 onward, in quick mode
   — never ask questions, decide yourself. Then follow the `class-<x>` skill
   if one exists for this class; otherwise do step 7 by hand."
7. "Report back: the character's name, class/career, Melee and Ranged AC,
   Wounds, what they carry, remaining purse, and any WARNING `finalize.py`
   printed that you left unresolved."

Tell every sub-agent, in these words or close to them: **"Do not invent
mechanics. If a page leaves something blank, record that it is blank and say
so in your report rather than filling the gap yourself."** A cold agent
handed a stub career will otherwise write plausible-sounding rules onto a
character sheet, and plausible-sounding rules are the hardest kind to catch
later.

Do not let a sub-agent choose its own class or career — that decision is the
one thing that has to be made across the whole party, and it is already made.
If a sub-agent reports that its assignment does not work (a key modifier is
hopeless even after the swap), or you find the assignment itself was wrong,
**reset that one slot and rebuild it** rather than letting it improvise:

```
python3 $P/reset_slot.py --file characters/<party-slug>/pcN.json [--dry-run]
```

That clears class, career, Status, money, inventory, notes, skills and the
derived combat block, **keeps the rolled abilities**, releases the ability
swap and deletes the stale sheet. It exists because `apply_class.py` refuses
a character that already has a class and points you at
`roll_stats.py --force`, which would reroll the dice — the one thing that
must not change when you reassign a slot. Then respawn just that agent,
telling it what the previous build was and why it was discarded.

## Step 5 — assemble and check

```
python3 $P/party_pack.py --dir characters/<party-slug> \
    --title "<Party name>" --brief characters/<party-slug>/party.md
```

Writes `pack.md`: the brief, a roster table (name, class/career, Status,
alignment, Wounds/Stamina, Melee/Ranged AC, movement, purse), the open flags,
then every full sheet.

It **exits 2 and names the gap** if any character did not finish the
pipeline — no class, no name, no bio, empty inventory, no `finalize.py` run,
no class-specific finishing. That is your check on the fan-out: a sub-agent
that died halfway shows up here rather than in the player's pack. Re-run the
missing steps for that slot (or respawn that one agent) and assemble again.
`--allow-incomplete` writes the pack anyway; use it only when you intend to
hand over something unfinished and say so.

Read the open flags before presenting. "needs training" on a firearm is fine
if the career covers it — say which. "no weapon in the inventory" on a
fighter is a real miss.

## Step 6 — present the pack

Lead with the party in a few lines: what this crew is, how it covers the
adventure, where it is thin. Then the roster table, then point to `pack.md`
for the full sheets. Name the open flags honestly and say what is left for
the Referee to decide.
