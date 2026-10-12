# Spell, miracle and career page contracts

Read this before creating or editing a page under `docs/Character/Spells/`, `docs/Character/Miracles/` or `docs/Character/Classes/*/Careers/`.

The CSS locates the metadata block as "first paragraph whose first child is `<strong>` and which contains `<br>`" — so a spell or miracle page opens, right after the `#` title, with a bold metadata paragraph using trailing double-space line breaks. **Frontmatter is the source of truth and the paragraph is generated from it** by `scripts/gen_game_data.py`; edit the frontmatter, then re-run the script rather than editing the block by hand.

```markdown
---
title: Magic Missile
class: magic-user
level: 1
duration: Instantaneous
range: 60' + 10'/level
tags:
  - level_1
  - magic-user
---
# Magic Missile

**Class**: Magic-User  
**Level**: 1  
**Duration**: Instantaneous  
**Range**: 60' + 10'/level  
```

A new page needs only `title` and the prose: the generator lifts `class` and `level` out of the path and tags, and `duration`/`range` out of the block if they are only written there, then normalizes all of it. It also regenerates `tags` (`level_N` + the class slug) while preserving any hand-added tag.

Career pages instead carry `tags:` for class and status (e.g. `warrior`, `gold`) and the `image:`/`image_alt:` pair. **Careers are read-only to the generator** — they are half-written and structurally uneven (Magic-User careers carry a spell-slot table and no metadata block at all), so nothing on them is rewritten; they are only extracted.
