---
name: spell-formatting
description: Format a Vogelfrei spell or miracle page into the fixed docs layout - frontmatter, the Duration/Range details card, body prose and tables, file placement, nav and index registration - and report every rules inconsistency found instead of silently resolving it. Use when adding, converting or reformatting spell/miracle pages, including bulk conversion from the LotFP source.
---

# Spell & miracle page formatting

Turns spell text into a docs page that matches the existing pages exactly,
and **reports** anything that does not line up with the current rules
instead of quietly fixing it.

Two separate jobs, both mandatory:

1. **Fix the format.** The frontmatter and the details card are a strict
   contract — the CSS and JS both parse them (see `CLAUDE.md`). Get these
   byte-exact.
2. **Mark the inconsistencies.** Anything in the source text that conflicts
   with Vogelfrei's rules is *left in place* and listed in your response for
   the user to decide. You do not invent rulings.

Never resolve a rules conflict on your own initiative. Formatting is yours;
rules are the user's.

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

`reference/terminology.md` has the known LotFP → Vogelfrei mappings and the
places where the docs already disagree with themselves. Apply the settled
mappings silently — those are not inconsistencies. Report anything else.

What to report:

- **Unmapped terminology** — a term with no Vogelfrei equivalent, or one
  where the docs are split (`Armor Rating` vs `Armor Class`).
- **Missing subsystem** — the text leans on a rule Vogelfrei has not
  defined, or one it defines differently.
- **Existing page conflict** — the spell already exists in `docs/` with
  different numbers. Vogelfrei has deliberately rebalanced some spells
  (Magic Missile is `1d3`/level, not `1d4`). **Never overwrite a
  divergence** — keep the existing page's numbers and report the difference.
- **Dangling cross-reference** — a link target that does not exist.
- **Missing home** — no `Level N` directory or nav block for that level yet.
- **Class mismatch** — the source lists the spell for a class Vogelfrei
  assigns differently.

Report as a table, most blocking first, each row saying what the source
said, what the docs say, and what you did:

```markdown
### Inconsistencies

| Spell | Kind | Source says | Vogelfrei | Left as |
|---|---|---|---|---|
| Magic Missile | Existing conflict | 1d4/level | 1d3/level | kept 1d3, not overwritten |
| Cloudkill | Missing subsystem | kills ≤3 HD outright | no HD-threshold rule | verbatim, needs a ruling |
```

If nothing conflicts, say so in one line — do not pad the table.

When converting in bulk, still report per spell. A long table is the
correct output; do not summarise it away or truncate it to examples.
