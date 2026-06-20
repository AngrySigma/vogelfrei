#!/usr/bin/env python3
"""Add a frontmatter `image:` (+ `image_alt:`) to every career page.

Careers live at docs/Character/Classes/*/Careers/*.md. This wires each one
to a portrait illustration rendered top-right by overrides/main.html.

Idempotent: pages that already declare `image:` are left untouched, so it is
safe to re-run after adding new careers. Currently points every career at the
shared cover as a placeholder; swap individual paths to real art as it lands.

Usage:
    python3 scripts/add_career_images.py            # apply
    python3 scripts/add_career_images.py --dry-run   # preview only
"""
from __future__ import annotations

import sys
from pathlib import Path

IMAGE = "assets/img/cover.webp"  # placeholder until per-career art exists
CAREERS = Path("docs/Character/Classes")


def process(path: Path, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    name = path.stem  # e.g. "Pit Fighter"
    alt = f"{name} illustration"
    image_lines = f"image: {IMAGE}\nimage_alt: {alt}\n"

    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end == -1:
            print(f"!! {path}: malformed frontmatter, skipped")
            return False
        front = text[4:end + 1]
        if "image:" in front:
            return False  # already wired
        new = "---\n" + front + image_lines + text[end + 1:]
    else:
        # No frontmatter: prepend a minimal block.
        new = f"---\n{image_lines}---\n{text}"

    if not dry_run:
        path.write_text(new, encoding="utf-8")
    print(f"+- {path}")
    return True


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    files = sorted(CAREERS.glob("*/Careers/*.md"))
    changed = sum(process(f, dry_run) for f in files)
    verb = "would update" if dry_run else "updated"
    print(f"\n{verb} {changed}/{len(files)} career pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
