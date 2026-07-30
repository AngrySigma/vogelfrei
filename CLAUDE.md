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
python3 scripts/gen_view_manifest.py      # rebuild the game-tier manifest (--check to fail if stale)
```

## Architecture

**Navigation is explicit.** `zensical.toml` defines the entire `nav` tree by hand. A new page in `docs/` will not appear in the site navigation until it is added to `nav` in the appropriate chapter, in reading order. This is the most common step to forget when adding content.

**Content layout** mirrors the book's chapters: `docs/Character/` (with `Classes/<Class>/Careers/`, `Spells/Level N/`, `Miracles/Level N/`, `Special Rules/`), `docs/Equipment/`, `docs/Retainers/`, `docs/Adventuring/`, `docs/Encounters/`. Pages cross-reference each other with relative Markdown links to `.md` files, and use Material-style admonitions (e.g. `!!! tip "Trait"` for career traits).

**Frontmatter drives presentation** via three custom layers that work together:

- `overrides/main.html` — template override: any page with `image:` in frontmatter (path relative to `docs/`, e.g. `assets/img/cover.webp`, plus optional `image_alt:`) gets a figure floated top-right of the article; the home page gets a `--cover` variant. `scripts/add_career_images.py` idempotently wires this frontmatter into every career page, so re-run it after adding careers.
- `docs/javascripts/extra.js` — colors tag chips by class, provides the click-to-zoom lightbox for those figures, and injects **Class**/**Level** lines into spell/miracle metadata blocks by reading the page's rendered tag chips (`magic-user`/`cleric` class tags, `level_N` level tags).
- `docs/javascripts/vf-view.js` — the game-tier switcher (see **Game tiers** below); reads the generated `vf-view-manifest.js` and prunes the sidebar to the selected tier.
- `docs/stylesheets/extra.css` — styles the spell/miracle metadata block, tag chips, illustrations, and the tier switcher; color tokens are CSS custom properties with light/dark (`slate`) variants.

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

**Game tiers.** The book ships three views — `simple`, `base`, `advanced` — and readers switch between them with the eye button in the header. Tier membership is an explicit **set**, not a cumulative rank, so a page can exist in Simple and nowhere else. Pages declare it in frontmatter:

```yaml
tier: base        # shorthand for this tier and every higher one -> [base, advanced]
tiers: [simple]   # explicit set: appears in EXACTLY these tiers
```

No key means the page shows in every tier. `scripts/gen_view_manifest.py` resolves both forms into `docs/javascripts/vf-view-manifest.js`, which `docs/javascripts/vf-view.js` reads to prune the sidebar. **Re-run the generator after changing any `tier:`/`tiers:` frontmatter** — the deploy workflow also regenerates it, so a stale committed copy won't reach production, but `zensical serve` will show stale gating until you do.

Gating is cosmetic only: hidden pages are still built, still linked, still in the search index, and still reachable by URL. Landing on one shows a banner offering to switch tiers. Because the manifest is keyed by URL path and matched by longest suffix, it works under both a domain root (vogelfrei.ru) and a subdirectory (GitHub Pages `/vogelfrei/`) — but avoid a manifest key that is a path-suffix of another, or the shorter one will cross-match.

**Instant navigation.** The site uses Zensical's instant navigation, so page swaps don't reload the document. JS that must re-run per page subscribes to `window.document$`, Material's observable of the current document — it replays to late subscribers and emits again on every swap:

```js
run();                                  // scripts load at end of <body>: act before first paint
if (window.document$ && typeof window.document$.subscribe === "function") {
  window.document$.subscribe(run);
} else {
  document.addEventListener("DOMContentLoaded", run);
}
```

There is **no `DOMContentSwitch` event** — it is dispatched nowhere in the theme bundle; earlier code listening for it silently never re-ran. Keep per-page work idempotent anyway (see the existing `dataset` guards), since the initial `run()` and the first `document$` emission both fire.

`extra_javascript` in `zensical.toml` is load-ordered: `vf-view-manifest.js` (data only) must precede `vf-view.js` (reads it on load).

## Deployment

`.github/workflows/deploy.yaml` regenerates the view manifest, builds with uv/zensical, and deploys `site/` to GitHub Pages on pushes to `master` (plus manual `workflow_dispatch`). vogelfrei.ru hosts a separate nightly build from its own source, which has drifted from this repo — don't assume the two sites carry the same features.
