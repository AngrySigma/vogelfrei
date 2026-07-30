#!/usr/bin/env python3
"""Generate the client-side view manifest for Vogelfrei's game-tier system.

Scans every Markdown page under the docs directory for an optional frontmatter
key naming the tiers the page belongs to:

    tier: base                         # shorthand: this tier AND all higher ones
    tiers: [simple]                    # explicit set: appears in EXACTLY these

and emits a small JavaScript file that ``javascripts/vf-view.js`` consumes to
prune the navigation client-side.

Tier model
----------
A page is visible in a *set* of tiers. The default (no key) is ALL tiers, so a
page is shown everywhere unless it says otherwise. Both keys resolve to an
explicit set:

    (nothing)        -> [simple, base, advanced]   (always visible)
    tier: base       -> [base, advanced]           (base and up; not Simple)
    tier: advanced   -> [advanced]
    tiers: [simple]  -> [simple]                   (Simple ONLY — a simplified
                                                    page that higher tiers
                                                    replace with detailed ones)

``tiers`` is what makes membership non-cumulative, which a ``tier:`` minimum
cannot express. That is the Retainers case: "Basic Retainers" exists only in
the Simple view, and the Base/Advanced views replace it with the three detailed
pages instead.

Usage
-----
Run before ``zensical build`` / ``zensical serve`` (the deploy workflow does
this automatically):

    python3 scripts/gen_view_manifest.py             # write the manifest
    python3 scripts/gen_view_manifest.py --check     # fail if it is stale

The page URL keys mirror Zensical's ``use_directory_urls`` mapping
(``X/Y.md`` -> ``X/Y/``, ``X/index.md`` -> ``X/``), preserving the original case
and spaces. The JS side decodes link pathnames before matching, so the keys are
stored un-encoded.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = REPO_ROOT / "docs"
OUTPUT_REL = Path("javascripts") / "vf-view-manifest.js"

TIER_ORDER = ["simple", "base", "advanced"]
VALID_TIERS = set(TIER_ORDER)
ALL_TIERS = list(TIER_ORDER)


def split_frontmatter(text: str) -> str | None:
    """Return the raw YAML frontmatter block, or None if there isn't one."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def parse_tier_keys(block: str, where: str) -> list[str]:
    """Extract the tier set from a frontmatter block with a minimal parser.

    Only top-level (unindented) ``tier:``/``tiers:`` keys count, so a nested key
    inside another mapping cannot be mistaken for one. Supports both the inline
    ``[a, b]`` and the block ``- item`` list forms.
    """
    tier_single: str | None = None
    tiers_explicit: list[str] | None = None
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Top-level keys only: no leading whitespace.
        if line[:1].isspace() or not line.strip():
            i += 1
            continue
        stripped = line.strip()
        if stripped.startswith("tiers:"):
            tiers_explicit, i = _parse_list(lines, i, stripped[len("tiers:"):].strip())
        elif stripped.startswith("tier:"):
            value = stripped[len("tier:"):].strip().strip("'\"").lower()
            if value in VALID_TIERS:
                tier_single = value
            elif value:
                print(f"  warning: {where}: unknown tier {value!r} (ignored)", file=sys.stderr)
        i += 1
    return resolve_tiers(tier_single, tiers_explicit, where)


def _parse_list(lines: list[str], i: int, rest: str) -> tuple[list[str], int]:
    """Parse a YAML list value; returns the items and the last consumed index."""
    if rest.startswith("["):
        inner = rest.strip("[]")
        items = [x.strip().strip("'\"").lower() for x in inner.split(",") if x.strip()]
        return items, i
    items = []
    j = i + 1
    while j < len(lines) and lines[j].strip().startswith("- "):
        items.append(lines[j].strip()[2:].strip().strip("'\"").lower())
        j += 1
    return items, j - 1


def resolve_tiers(
    tier_single: str | None, tiers_explicit: list[str] | None, where: str
) -> list[str]:
    """Resolve the tier keys to an explicit, order-normalized tier set."""
    if tiers_explicit is not None:
        unknown = [t for t in tiers_explicit if t not in VALID_TIERS]
        if unknown:
            print(f"  warning: {where}: unknown tier(s) {unknown} (ignored)", file=sys.stderr)
        resolved = [t for t in TIER_ORDER if t in tiers_explicit]
        if not resolved:
            print(f"  warning: {where}: empty 'tiers', treating as all tiers", file=sys.stderr)
            return list(ALL_TIERS)
        return resolved
    if tier_single is not None:
        return TIER_ORDER[TIER_ORDER.index(tier_single):]
    return list(ALL_TIERS)


def url_key(md_path: Path, docs_dir: Path) -> str:
    """Map a Markdown file to its directory-URL key (no leading slash)."""
    rel = md_path.relative_to(docs_dir).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "index":
        parts.pop()
    key = "/".join(parts)
    return f"{key}/" if key else ""


def build_manifest(docs_dir: Path) -> dict[str, dict]:
    pages: dict[str, dict] = {}
    for md_path in sorted(docs_dir.rglob("*.md")):
        block = split_frontmatter(md_path.read_text(encoding="utf-8"))
        if block is None:
            continue
        where = md_path.relative_to(docs_dir).as_posix()
        tiers = parse_tier_keys(block, where)
        # Only record pages that deviate from the default. A page visible in all
        # tiers needs no entry: the JS treats a missing key as "always visible".
        if tiers == ALL_TIERS:
            continue
        key = url_key(md_path, docs_dir)
        if key == "":
            print(f"  warning: {where}: the home page cannot be gated (ignored)", file=sys.stderr)
            continue
        pages[key] = {"tiers": tiers}
    return pages


def render_js(pages: dict[str, dict]) -> str:
    pages_json = json.dumps(pages, ensure_ascii=False, indent=2, sort_keys=True)
    return (
        "/* AUTO-GENERATED by scripts/gen_view_manifest.py — do not edit by hand.\n"
        "   Maps page URLs to the game tiers they appear in, for javascripts/vf-view.js. */\n"
        f"window.VF_TIERS = {json.dumps(TIER_ORDER)};\n"
        f"window.VF_PAGES = {pages_json};\n"
    )


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("-")]
    check = "--check" in argv
    docs_dir = Path(args[0]).resolve() if args else DEFAULT_DOCS
    if not docs_dir.is_dir():
        print(f"error: docs dir not found: {docs_dir}", file=sys.stderr)
        return 1

    pages = build_manifest(docs_dir)
    output = docs_dir / OUTPUT_REL
    rendered = render_js(pages)
    rel = output.relative_to(REPO_ROOT) if output.is_relative_to(REPO_ROOT) else output

    if check:
        current = output.read_text(encoding="utf-8") if output.exists() else None
        if current != rendered:
            print(f"error: {rel} is stale — re-run scripts/gen_view_manifest.py", file=sys.stderr)
            return 1
        print(f"{rel} is up to date ({len(pages)} gated page(s))")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"wrote {rel}: {len(pages)} gated page(s)")
    for key, entry in sorted(pages.items()):
        print(f"  {key} -> {', '.join(entry['tiers'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
