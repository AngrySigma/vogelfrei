# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The full source of **Vogelfrei**, an OSR tabletop RPG rulebook, published as a static site with [Zensical](https://zensical.org) (successor to Material for MkDocs). The deliverable is the game text in `docs/` — `main.py` is an unused uv scaffold stub. There are no tests or linters.

## Commands

```bash
uv sync                                   # install dependencies (uv + pyproject.toml/uv.lock; requirements.txt is vestigial)
uv run zensical build                     # build static site → site/ (not committed)
uv run zensical serve                     # live-reload dev server at http://localhost:8000
python3 scripts/add_career_images.py      # add placeholder image frontmatter to new career pages (--dry-run to preview)
```

## Architecture

**Navigation is explicit.** `zensical.toml` defines the entire `nav` tree by hand. A new page in `docs/` will not appear in the site navigation until it is added to `nav` in the appropriate chapter, in reading order. This is the most common step to forget when adding content.

**Content layout** mirrors the book's chapters: `docs/Character/` (with `Classes/<Class>/Careers/`, `Spells/Level N/`, `Miracles/Level N/`, `Special Rules/`), `docs/Equipment/`, `docs/Retainers/`, `docs/Adventuring/`, `docs/Encounters/`. Pages cross-reference each other with relative Markdown links to `.md` files, and use Material-style admonitions (e.g. `!!! tip "Trait"` for career traits).

**Frontmatter drives presentation** via three custom layers that work together:

- `overrides/main.html` — template override: any page with `image:` in frontmatter (path relative to `docs/`, e.g. `assets/img/cover.webp`, plus optional `image_alt:`) gets a figure floated top-right of the article; the home page gets a `--cover` variant. `scripts/add_career_images.py` idempotently wires this frontmatter into every career page, so re-run it after adding careers.
- `docs/javascripts/extra.js` — colors tag chips by class, provides the click-to-zoom lightbox for those figures, and injects **Class**/**Level** lines into spell/miracle metadata blocks by reading the page's rendered tag chips (`magic-user`/`cleric` class tags, `level_N` level tags).
- `docs/stylesheets/extra.css` — styles the spell/miracle metadata block and tag chips; color tokens are CSS custom properties with light/dark (`slate`) variants.

**Spell/miracle page contract.** Both the CSS and JS locate the metadata block as "first paragraph whose first child is `<strong>` and which contains `<br>`". New spell/miracle pages must therefore open (right after the `#` title) with the bold metadata paragraph, using trailing double-space line breaks:

```markdown
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
```

Career pages instead carry `tags:` for class and status (e.g. `warrior`, `gold`) and the `image:`/`image_alt:` pair.

**Instant navigation.** The site uses Zensical's instant navigation, so page swaps don't reload the document. Any JS added to `extra.js` must re-run on the `DOMContentSwitch` event and guard against double-binding/double-injection (see the existing `dataset` guards).

## Deployment

`.github/workflows/deploy.yaml` builds with uv/zensical and deploys `site/` to GitHub Pages. Note: it triggers on pushes to `main`, but the repository's working branch is `master`, so automatic deploys don't fire on normal pushes (manual `workflow_dispatch` works). vogelfrei.ru hosts a separate nightly build.
