---
name: spell-formatting
description: Format a Vogelfrei spell or miracle page into the fixed docs layout - frontmatter, the Duration/Range details card, body prose and tables, file placement, nav and index registration - and report every rules inconsistency found instead of silently resolving it. Use when adding, converting or reformatting spell/miracle pages, including bulk conversion from the LotFP source.
---

# Spell & miracle page formatting

Turns spell text into a docs page that matches the existing pages exactly,
and **reports** the places where its mechanics no longer fit Vogelfrei's
rules instead of quietly fixing them.

Two separate jobs, both mandatory:

1. **Fix the format.** The frontmatter and the details card are a strict
   contract — the CSS and JS both parse them (see `CLAUDE.md`). Get these
   byte-exact.
2. **Mark the mechanical inconsistencies.** Where the spell drives a
   subsystem Vogelfrei has rebuilt, leave the text as it stands and list it
   in your response for the user to rule on.

An inconsistency is **mechanical, not verbal**. Wording is yours to
normalise silently; rules are the user's to decide.

- Not an inconsistency: the source says *Armor Class*, *mêlée*, *Evil*,
  *Fighter*. Standardise these on the majority spelling in `docs/` without
  mentioning it — see `reference/house-style.md`.
- **Is** an inconsistency: the spell deals damage on a scale built for hit
  points, when Vogelfrei characters have a handful of Wounds. Or it grants
  a flat Armor Class when Vogelfrei builds AC from components. That is a
  rules decision and it goes in the report.

Never invent a conversion factor, rescale a die, or reinterpret an effect
on your own initiative.

## Where the page goes

| Class | Directory | Called |
|---|---|---|
| `magic-user` | `docs/Character/Classes/Magic-User/Spells/Level N/` | Spells |
| `cleric` | `docs/Character/Classes/Cleric/Miracles/Level N/` | Miracles |

Filename is the spell name verbatim, `.md`, spaces kept
(`Magic Missile.md`). Create the `Level N` directory if it does not exist.

Cleric magic is called a **Miracle** throughout, never a "spell" — in the
directory, the index title and the prose.

## The fixed format

Everything below the details card is ordinary prose and is not constrained.

````markdown
---
title: Magic Missile
class: magic-user
tags:
  - level_1
  - magic-user
---
# Magic Missile

**Duration**: Instantaneous  
**Range**: 60' + 10'/level  

First paragraph of the description.
````

Rules the parsers depend on:

- `title`, `class`, then `tags` — in that order. `class` is exactly
  `magic-user` or `cleric`.
- `tags` is always the pair `level_N` and the class slug, in that order.
  `docs/javascripts/extra.js` reads these chips to inject the **Class** and
  **Level** lines into the card; a missing or misspelled tag silently drops
  them.
- `# <name>` matches `title` and the filename.
- The details card is the **first paragraph after the H1**, and both lines
  end with **two trailing spaces**. The CSS and JS locate it as "first
  paragraph whose first child is `<strong>` and which contains `<br>`", so
  the spaces on the `Duration` line are load-bearing — drop them and the
  `<br>` disappears and the card silently loses its styling. On the final
  line they render identically either way, but every page carries them;
  match that.
- Exactly two card fields, always `**Duration**` then `**Range**`. Every
  existing page has both. If the source has neither or has extra fields
  (`Area of Effect`, `Reversed`), keep the two-line card and report it.
- Blank line after the card, then the body.
- **`tier:`** goes last, after `tags`, when the page is gated to a game tier
  (`tier: advanced` — shorthand for that tier and every higher one; `tiers:
  [simple]` for an exact set). No key means the page shows in every tier.
  Adding or changing it means re-running the manifest generator, below.

### Body

- Plain paragraphs. Blank line between them.
- Curly quotes and apostrophes (`’` `“` `”`), spaced em dashes (` — `).
- Tables are **markdown pipe tables** with a header row — never indented or
  code-fenced text. The source's fixed-width columns must be converted.
- Sub-sections use `## Heading`.
- Link to other rules pages with relative `.md` links, URL-encoding spaces
  (`[Armor Rating](../../../../../Equipment/Armor.md)`). Only link to pages
  that exist — check first, and report the ones that don't.

## Registration (do not skip)

A new page is invisible until it is registered in **both** places:

1. `zensical.toml` — add the full path to the `nav` tree under the right
   class and `Level N` block, in the same order as the index.
2. The class index — `Spells/index.md` or `Miracles/index.md` — as a
   numbered entry under its `### Level N` heading, with the level's own
   numbering, URL-encoded (`[Charm Person](Level%201/Charm%20Person.md)`).

Both lists are ordered as the source book orders that level, not
alphabetically by accident — follow the existing convention in the file.

If you add or change any `tier:`/`tiers:` frontmatter, re-run
`python3 scripts/gen_view_manifest.py`.

## Validate

```bash
python3 .claude/skills/spell-formatting/scripts/validate_spells.py            # whole tree
python3 .claude/skills/spell-formatting/scripts/validate_spells.py <file.md>  # one page
```

It checks the frontmatter contract, the card (including trailing spaces),
name/path/tag agreement, and nav + index registration. It checks **format
only** — it knows nothing about rules. A clean run is required before you
report done; paste nothing that it still flags.

## Reporting inconsistencies

Collect them while converting and put them at the **end of your response**,
never inside the page. Do not edit the rules to match, and do not silently
drop the offending sentence.

`reference/mechanics.md` documents the rebuilt subsystems, with the numbers
and the already-converted precedents. Read it before converting anything
that deals damage, heals, or touches AC.

What counts — the spell drives one of these:

- **Damage that bypasses Stamina** — poison above all, and effects on
  unaware, helpless or paralyzed targets. Wounds alone are about a third of
  the pool the source balanced against, so this damage is roughly three
  times as lethal. Damage that runs through Stamina first is close to
  proportionate and is the milder case.
- **Healing.** Restores Wounds directly, so it is worth about three times
  what the source intended — a `1d6+level` heal covers a Warrior's whole
  Wound track by 5th level.
- **Per-level damage**, which outruns a Wound track that barely grows.
- **Stamina, unstated.** Damage should say whether it lands on Stamina first
  or bypasses it. The source predates the pool and never says.
- **Armor Class.** LotFP grants absolute values ("AC 19"); Vogelfrei
  composes AC and needs an explicit bonus, split Melee/Ranged where the
  source distinguishes missiles from other attacks.
- **Damage reduction.** Vogelfrei armour makes you harder to hit and is
  explicitly *not* damage-resistant, so any flat "reduces damage" grant
  conflicts with the stated principle.
- **Death and 0 Wounds.** Save-or-die and "kills anything under N HD"
  effects bypass the critical-injury table that Vogelfrei resolves dying
  through.
- **Undefined subsystem.** The effect needs a rule Vogelfrei has not
  written.

Also report, though these are cheaper to settle:

- **Existing page conflict** — the spell already exists with different
  numbers. Some are deliberate rebalances. **Never overwrite one**: keep the
  page's values and report the difference.
- **Dangling cross-reference**, and **missing home** (no `Level N`
  directory or nav block yet).

Report as a table, most blocking first:

```markdown
### Inconsistencies

| Spell | Subsystem | Source | Vogelfrei | Left as |
|---|---|---|---|---|
| Fireball | Damage scale | 1d6/level, ~17 at L5 | Warrior peaks near 12 Wounds | verbatim — needs a ruling |
| Cloudkill | Death | kills ≤3 HD outright | critical injury at 0 Wounds | verbatim — bypasses the table |
| Prismatic Sphere | Armor Class | absolute AC | AC is composed | verbatim — needs a bonus |
```

If nothing conflicts, say so in one line — do not pad the table.

When converting in bulk, still report per spell. A long table is the correct
output; do not summarise it away or truncate it to examples.
