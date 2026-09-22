#!/usr/bin/env python3
"""Make Vogelfrei's spell, miracle and career data machine-readable.

Two jobs, one pass over the book:

1. **Spells and miracles** — frontmatter is the source of truth. The script
   resolves ``class``, ``level``, ``duration`` and ``range`` for every spell and
   miracle page (reading them from frontmatter, or lifting them out of the
   rendered body block the first time a page is processed), then rewrites both
   the frontmatter and the bold metadata paragraph under the ``#`` title from
   those values. That paragraph is what the reader sees and what
   ``stylesheets/extra.css`` styles, so its shape is fixed by the page contract
   in CLAUDE.md; the script is what keeps it in step with the data.

2. **Careers** — read-only. Career pages are half-written and structurally
   uneven (Magic-User careers carry a spell-slot table and no metadata block at
   all), so nothing is rewritten; the script only extracts what is there.

It then emits ``docs/data/{spells,miracles,careers}.json``, which ship with the
site and give the character-generation skills — and any other consumer — a
structured view of the rules instead of prose to parse.

Usage:
    python3 scripts/gen_game_data.py             # sync pages + write JSON
    python3 scripts/gen_game_data.py --dry-run   # report changes, write nothing
    python3 scripts/gen_game_data.py --check     # fail if anything is stale
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vf_frontmatter as fm  # noqa: E402
from gen_view_manifest import parse_tier_keys, url_key  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
DATA_DIR = DOCS / "data"
CLASSES = DOCS / "Character" / "Classes"

# Display labels for the class slugs that appear in spell/miracle frontmatter.
CLASS_LABELS = {"magic-user": "Magic-User", "cleric": "Cleric"}

META_LINE = re.compile(r"^\*\*(?P<label>[^*]+)\*\*:\s*(?P<value>.*?)\s*$")
TABLE_ROW = re.compile(r"^\s*\|(?P<cells>.*)\|\s*$")
ADMONITION = re.compile(r'^!!!\s+(?P<type>[a-z]+)\s+"(?P<title>[^"]*)"\s*$')
LEVEL_DIR = re.compile(r"^Level\s+(\d+)$", re.IGNORECASE)
LEVEL_TAG = re.compile(r"^level_(\d+)$")


# --------------------------------------------------------------------------
# Body helpers
# --------------------------------------------------------------------------

def split_body(body: str) -> tuple[list[str], list[str], list[str]]:
    """Split a page body into (lines before the metadata block, block, rest).

    The metadata block is the run of ``**Label**: value`` lines that follows the
    ``#`` title. When a page has none, the middle list is empty and the split
    point sits just after the title's trailing blank line.
    """
    lines = body.splitlines()
    i = 0
    while i < len(lines) and not lines[i].startswith("# "):
        i += 1
    if i == len(lines):  # no H1 at all
        return lines, [], []
    head_end = i + 1
    j = head_end
    while j < len(lines) and not lines[j].strip():
        j += 1
    block_start = j
    last = j
    while j < len(lines):
        if META_LINE.match(lines[j]):
            j += 1
            last = j
        elif not lines[j].strip():
            j += 1  # careers separate their labels with blank lines
        else:
            break
    if last == block_start:
        return lines[:head_end], [], lines[head_end:]
    return lines[:block_start], lines[block_start:last], lines[last:]


def parse_meta_block(block: list[str]) -> dict[str, str]:
    """Read a metadata block's ``**Label**: value`` lines into a dict."""
    out: dict[str, str] = {}
    for line in block:
        m = META_LINE.match(line)
        if m:
            value = m.group("value").strip()
            # Values may be links (careers write **Class**: [Warrior](...)).
            out[m.group("label").strip().lower()] = value
    return out


def strip_link(value: str) -> str:
    """Reduce ``[Warrior](../index.md)`` to ``Warrior``; pass plain text through."""
    m = re.fullmatch(r"\[([^\]]*)\]\([^)]*\)", value.strip())
    return m.group(1).strip() if m else value.strip()


INLINE_TRAIT = re.compile(r"^\*{2,3}Trait\*{2,3}\s*:\s*(?P<body>.+?)\s*$")


def parse_trait(lines: list[str]) -> str | None:
    """Return the career's trait text.

    Career pages write the trait two ways: as a ``!!! tip "Trait"`` admonition
    (most of them) and as an inline ``***Trait***: ...`` line (the Academic
    careers). Both are real content, so both must be read — reading only the
    admonition silently dropped the Apothecary's and Barber's traits and made
    those careers look emptier than they are.
    """
    for line in lines:
        m = INLINE_TRAIT.match(line.strip())
        if m and m.group("body").strip():
            return m.group("body").strip()
    for i, line in enumerate(lines):
        m = ADMONITION.match(line)
        if not m or m.group("title").strip().lower() != "trait":
            continue
        body: list[str] = []
        for follow in lines[i + 1:]:
            if not follow.strip():
                if body:
                    break
                continue
            if not follow[0].isspace():
                break
            body.append(follow.strip())
        if body:
            return " ".join(body)
    return None


def parse_progression(lines: list[str]) -> list[dict[str, str]]:
    """Parse a ``| Level | Progression |`` table into rows, skipping empties."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in lines:
        m = TABLE_ROW.match(line)
        if not m:
            if header is not None:
                break  # table ended
            continue
        cells = [c.strip() for c in m.group("cells").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue  # separator row
        row = {k: v for k, v in zip(header, cells) if v}
        if len(row) > 1:  # more than just the level number
            rows.append(row)
    return rows


def body_text(rest: list[str]) -> str:
    """The page's prose after the metadata block, as Markdown."""
    return "\n".join(rest).strip()


# --------------------------------------------------------------------------
# Spells and miracles
# --------------------------------------------------------------------------

def spell_pages(kind_dir: str) -> list[Path]:
    return sorted(
        p for p in CLASSES.rglob(f"*/{kind_dir}/**/*.md") if p.name != "index.md"
    )


def resolve_spell(path: Path, kind_dir: str) -> tuple[dict, str]:
    """Resolve one spell/miracle page to its data and its canonical source."""
    text = path.read_text(encoding="utf-8")
    block, body = fm.split_document(text)
    entries = fm.parse_entries(block) if block is not None else []
    rel = path.relative_to(DOCS).as_posix()

    head, meta_lines, rest = split_body(body)
    meta = parse_meta_block(meta_lines)
    tags = fm.get_list(entries, "tags")

    title = fm.get_scalar(entries, "title") or _h1(head) or path.stem

    # class: frontmatter, then the class tag, then the owning class directory.
    klass = fm.get_scalar(entries, "class")
    if not klass:
        klass = next((t for t in tags if t in CLASS_LABELS), None)
    if not klass:
        klass = _class_from_path(path)

    # level: frontmatter, then the level_N tag, then the "Level N" directory.
    level = fm.get_scalar(entries, "level")
    if not level:
        level = next(
            (m.group(1) for t in tags if (m := LEVEL_TAG.match(t))), None
        )
    if not level:
        level = next(
            (m.group(1) for part in path.parts if (m := LEVEL_DIR.match(part))), None
        )

    duration = fm.get_scalar(entries, "duration") or meta.get("duration") or ""
    rng = fm.get_scalar(entries, "range") or meta.get("range") or ""

    label = CLASS_LABELS.get(klass or "", (klass or "").title())
    managed_keys = {"title", "class", "level", "duration", "range", "tags"}
    leftovers = [e for e in entries if e.key not in managed_keys]

    canon_tags = []
    if level:
        canon_tags.append(f"level_{level}")
    if klass:
        canon_tags.append(klass)
    for tag in tags:  # keep any hand-added tags, in place, without duplicates
        if tag not in canon_tags:
            canon_tags.append(tag)

    new_block = fm.render(
        [
            ("title", title),
            ("class", klass),
            ("level", int(level) if level and level.isdigit() else level),
            ("duration", duration),
            ("range", rng),
            ("tags", canon_tags),
        ],
        leftovers,
    )

    display = []
    if label:
        display.append(f"**Class**: {label}  ")
    if level:
        display.append(f"**Level**: {level}  ")
    display.append(f"**Duration**: {duration}  ")
    display.append(f"**Range**: {rng}  ")

    new_body = "\n".join([*head, *display, *rest])
    if not new_body.endswith("\n"):
        new_body += "\n"
    canonical = fm.compose(new_block, new_body)

    data = {
        "name": title,
        "kind": "miracle" if kind_dir == "Miracles" else "spell",
        "class": klass,
        "level": int(level) if level and level.isdigit() else None,
        "duration": duration,
        "range": rng,
        "text": body_text(rest),
        "tags": canon_tags,
        "tiers": parse_tier_keys(block, rel) if block is not None else ["simple", "base", "advanced"],
        "url": url_key(path, DOCS),
        "source": rel,
    }
    return data, canonical


def _h1(lines: list[str]) -> str | None:
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _class_dir(path: Path) -> str:
    """The class directory owning this page, e.g. "Magic-User", "Wood Elf"."""
    parts = path.relative_to(CLASSES).parts
    return parts[0] if parts else ""


def _class_from_path(path: Path) -> str | None:
    """The class slug for a page, e.g. "magic-user", "wood-elf"."""
    name = _class_dir(path)
    return name.lower().replace(" ", "-") if name else None


# --------------------------------------------------------------------------
# Careers
# --------------------------------------------------------------------------

def career_pages() -> list[Path]:
    return sorted(CLASSES.glob("*/Careers/*.md"))


def resolve_career(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    block, body = fm.split_document(text)
    entries = fm.parse_entries(block) if block is not None else []
    rel = path.relative_to(DOCS).as_posix()

    head, meta_lines, rest = split_body(body)
    meta = parse_meta_block(meta_lines)
    tags = fm.get_list(entries, "tags")

    klass = _class_dir(path) or strip_link(meta.get("class", ""))
    status = strip_link(meta.get("status", ""))
    combat = meta.get("combat skills", "")
    skills = meta.get("skills", "")
    trait = parse_trait(rest)
    progression = parse_progression(rest)

    return {
        "name": fm.get_scalar(entries, "title") or _h1(head) or path.stem,
        "class": klass,
        "class_slug": _class_from_path(path) or "",
        "status": status or None,
        "combat_skills": combat or None,
        "skills": skills or None,
        "trait": trait,
        "progression": progression,
        # A career is written when it has actual mechanical content: a trait,
        # a non-empty progression table, or its skills. A Status on its own is
        # NOT enough — several pages (e.g. Townsman/Rat Catcher) carry only a
        # Status with every other field blank, and counting those as complete
        # sends character generators off to build on nothing.
        "complete": bool(trait or progression or skills or combat),
        "tags": tags,
        "image": fm.get_scalar(entries, "image"),
        "tiers": parse_tier_keys(block, rel) if block is not None else ["simple", "base", "advanced"],
        "url": url_key(path, DOCS),
        "source": rel,
    }


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    dry_run = "--dry-run" in argv
    stale: list[str] = []
    rewritten: list[str] = []

    collections: dict[str, list[dict]] = {}
    for kind_dir, name in (("Spells", "spells"), ("Miracles", "miracles")):
        rows = []
        for path in spell_pages(kind_dir):
            data, canonical = resolve_spell(path, kind_dir)
            rows.append(data)
            current = path.read_text(encoding="utf-8")
            if current != canonical:
                rel = path.relative_to(REPO_ROOT).as_posix()
                if check:
                    stale.append(rel)
                elif dry_run:
                    rewritten.append(rel)
                else:
                    path.write_text(canonical, encoding="utf-8")
                    rewritten.append(rel)
        rows.sort(key=lambda r: ((r["level"] or 99), r["name"]))
        collections[name] = rows

    collections["careers"] = sorted(
        (resolve_career(p) for p in career_pages()),
        key=lambda r: (r["class_slug"], r["name"]),
    )

    for name, rows in collections.items():
        target = DATA_DIR / f"{name}.json"
        rendered = dump({"count": len(rows), name: rows})
        rel = target.relative_to(REPO_ROOT).as_posix()
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == rendered:
            continue
        if check:
            stale.append(rel)
        elif dry_run:
            rewritten.append(rel)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
            rewritten.append(rel)

    if check:
        if stale:
            print("error: game data is stale — re-run scripts/gen_game_data.py", file=sys.stderr)
            for rel in stale:
                print(f"  {rel}", file=sys.stderr)
            return 1
        print(
            f"game data is up to date "
            f"({len(collections['spells'])} spells, {len(collections['miracles'])} miracles, "
            f"{len(collections['careers'])} careers)"
        )
        return 0

    verb = "would update" if dry_run else "updated"
    for rel in rewritten:
        print(f"  {verb} {rel}")
    incomplete = sum(1 for c in collections["careers"] if not c["complete"])
    print(
        f"\n{verb} {len(rewritten)} file(s); "
        f"{len(collections['spells'])} spells, {len(collections['miracles'])} miracles, "
        f"{len(collections['careers'])} careers ({incomplete} still stubs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
