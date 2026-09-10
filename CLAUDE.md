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
- `docs/javascripts/extra.js` — colors tag chips by class and provides the click-to-zoom lightbox for those figures. It used to inject **Class**/**Level** lines into spell metadata blocks by scraping the rendered tag chips; those lines are now written into the Markdown by `scripts/gen_game_data.py`, so they exist without JS and cannot drift from the data.
- `docs/javascripts/vf-view.js` — the game-tier switcher (see **Game tiers** below); reads the generated `vf-view-manifest.js` and prunes the sidebar to the selected tier.
- `docs/stylesheets/extra.css` — styles the spell/miracle metadata block, tag chips, illustrations, and the tier switcher; color tokens are CSS custom properties with light/dark (`slate`) variants.

**Spell/miracle page contract.** The CSS locates the metadata block as "first paragraph whose first child is `<strong>` and which contains `<br>`" — so a spell or miracle page opens, right after the `#` title, with a bold metadata paragraph using trailing double-space line breaks. **Frontmatter is the source of truth and the paragraph is generated from it** by `scripts/gen_game_data.py`; edit the frontmatter, then re-run the script rather than editing the block by hand.

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

**Machine-readable data.** `scripts/gen_game_data.py` emits `docs/data/{spells,miracles,careers}.json`, which ship with the site. Each spell/miracle row carries class, level, duration, range, rules text, tiers and URL; each career row carries status, combat skills, trait, level progression, and a `complete` flag that is false for the ~42 careers still stubbed. Consumers — the `character-generation` skill, anything reading the rules programmatically — should read these rather than re-parse the prose.

**`llms.txt`.** `scripts/gen_llms_txt.py` writes `docs/llms.txt` (an index of every page in `nav` order with a one-line summary and its tier gating) and `docs/llms-full.txt` (the whole book, ~50k words, as one Markdown file). Reading order comes from the `nav` tree in `zensical.toml`; a page missing from `nav` is emitted under a trailing "Unlisted" section **and warned about**, which makes the script a cheap check for the nav omission described above. Relative links are rewritten to absolute site URLs in the full text, since a path relative to the original file means nothing once the pages are concatenated. `llms-full.txt` is gitignored and built in CI — committing it would duplicate every prose edit in git history; `llms.txt` and the JSON files are small and are committed.

**Game tiers.** The book ships three views — `simple`, `base`, `advanced` — and readers switch between them with the eye button in the header. Tier membership is an explicit **set**, not a cumulative rank, so a page can exist in Simple and nowhere else. Pages declare it in frontmatter:

```yaml
tier: base        # shorthand for this tier and every higher one -> [base, advanced]
tiers: [simple]   # explicit set: appears in EXACTLY these tiers
```

No key means the page shows in every tier — which is why the core spine of the book carries no key at all, and only the ~79 pages that deviate appear in the manifest. As it stands Simple shows 84 of 162 pages (the four classic classes, core combat, core equipment), Base 153, Advanced 161. **Gating a class index means gating its careers too**, or the switcher prunes the class and leaves an orphaned "Careers" section behind it. `scripts/gen_view_manifest.py` resolves both forms into `docs/javascripts/vf-view-manifest.js`, which `docs/javascripts/vf-view.js` reads to prune the sidebar. **Re-run the generator after changing any `tier:`/`tiers:` frontmatter** — the deploy workflow also regenerates it, so a stale committed copy won't reach production, but `zensical serve` will show stale gating until you do.

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

**Don't inject anything into the theme header and expect it to stay.** The theme hydrates `.md-header__inner` after `extra_javascript` runs and discards children it doesn't own — a node inserted there vanishes with no error, which is why the tier button silently disappeared after a rebuild. `vf-view.js` handles this with a `MutationObserver` that re-mounts the control, falling back to a floating container after `VF_MAX_HEADER_ATTEMPTS`. If you add a similar observer, have its callback do **only** the idempotent re-mount: an earlier version re-ran the full apply, whose banner insert/remove was itself a mutation, and it looped forever at ~20 Hz.

## Deployment

`.github/workflows/deploy.yaml` regenerates the view manifest, the game data and `llms.txt`, builds with uv/zensical, drops each page's Markdown source next to its rendered HTML (so appending `index.md` to any page URL returns the source), and deploys `site/` to GitHub Pages on pushes to `master` (plus manual `workflow_dispatch`). vogelfrei.ru hosts a separate nightly build from its own source, which has drifted from this repo — don't assume the two sites carry the same features.
