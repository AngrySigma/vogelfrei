#!/usr/bin/env python3
"""Check spell/miracle pages against the docs format contract.

    validate_spells.py             # whole tree
    validate_spells.py FILE...     # named pages

Format only — it knows nothing about rules. Exits non-zero if anything fails.
"""
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs"
NAV = ROOT / "zensical.toml"

AREAS = {
    "magic-user": (DOCS / "Character/Classes/Magic-User/Spells", "spell"),
    "cleric": (DOCS / "Character/Classes/Cleric/Miracles", "miracle"),
}
CARD_KEYS = ("Duration", "Range")


def pages():
    for base, _ in AREAS.values():
        for p in sorted(base.glob("Level */*.md")):
            yield p


def split_frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    return (m.group(1), m.group(2)) if m else (None, text)


def check(path, nav_text):
    """Return a list of problem strings for one page."""
    out = []
    try:
        rel = path.relative_to(DOCS)
    except ValueError:
        return [f"path: outside docs/ ({path})"]
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return ["no YAML frontmatter"]

    title = re.search(r"^title:\s*(.+)$", fm, re.M)
    klass = re.search(r"^class:\s*(.+)$", fm, re.M)
    tags = re.findall(r"^\s*-\s*(\S+)\s*$", fm, re.M)

    if not title:
        out.append("frontmatter: missing `title`")
    if not klass:
        out.append("frontmatter: missing `class`")
    elif klass.group(1).strip() not in AREAS:
        out.append(f"frontmatter: class `{klass.group(1).strip()}` "
                   f"not one of {sorted(AREAS)}")

    # key order must be title, class, tags
    keys = re.findall(r"^([a-z_]+):", fm, re.M)
    lead = [k for k in keys if k in ("title", "class", "tags")]
    if lead != ["title", "class", "tags"]:
        out.append(f"frontmatter: key order {lead}, expected "
                   f"['title', 'class', 'tags']")

    # directory / level / tags agreement
    m = re.match(r"Level (\d+)$", path.parent.name)
    if not m:
        out.append(f"path: `{path.parent.name}` is not a `Level N` directory")
    elif klass and klass.group(1).strip() in AREAS:
        lvl, slug = m.group(1), klass.group(1).strip()
        want = [f"level_{lvl}", slug]
        if tags != want:
            out.append(f"tags: {tags}, expected {want}")
        base = AREAS[slug][0]
        if base not in path.parents:
            out.append(f"path: class `{slug}` but page is under `{rel}`")

    # title / H1 / filename must agree
    h1 = re.search(r"^#\s+(.+)$", body, re.M)
    if not h1:
        out.append("body: no `# ` H1")
    else:
        name = h1.group(1).strip()
        if title and title.group(1).strip() != name:
            out.append(f"H1 `{name}` != title `{title.group(1).strip()}`")
        if name != path.stem:
            out.append(f"H1 `{name}` != filename `{path.stem}`")

    # the details card: first paragraph after the H1
    if h1:
        after = body[h1.end():].lstrip("\n").split("\n")
        card = []
        for line in after:
            if not line.strip():
                break
            card.append(line)
        if len(card) != 2:
            out.append(f"card: {len(card)} line(s), expected exactly 2 "
                       f"(Duration, Range)")
        for i, key in enumerate(CARD_KEYS):
            if i >= len(card):
                out.append(f"card: missing `**{key}**`")
                continue
            line = card[i]
            if not line.startswith(f"**{key}**: "):
                out.append(f"card line {i + 1}: {line.strip()[:40]!r} "
                           f"does not start with `**{key}**: `")
            last = i == len(CARD_KEYS) - 1
            if not line.endswith("  "):
                out.append(
                    f"card line {i + 1} (`{key}`): needs two trailing spaces "
                    + ("(convention; 30/32 pages have them — renders the same)"
                       if last else
                       "— they make the <br> the card detection requires")
                )
            elif line.endswith("   "):
                out.append(f"card line {i + 1} (`{key}`): more than two "
                           f"trailing spaces")
            if not line.strip().removeprefix(f"**{key}**:").strip():
                out.append(f"card: `{key}` has no value")

    # tables must be pipe tables, not leftover fixed-width source
    for line in body.split("\n"):
        if "\t" in line:
            out.append(f"body: literal tab in {line.strip()[:40]!r} "
                       f"(convert to a pipe table)")
            break

    # registration
    nav_path = str(rel).replace("\\", "/")
    if f'"{nav_path}"' not in nav_text:
        out.append(f"zensical.toml: not in `nav` (add \"{nav_path}\")")
    if klass and klass.group(1).strip() in AREAS:
        index = AREAS[klass.group(1).strip()][0] / "index.md"
        if index.exists():
            link = f"{quote(path.parent.name)}/{quote(path.name)}"
            if link not in index.read_text(encoding="utf-8"):
                out.append(f"{index.relative_to(DOCS)}: no entry "
                           f"(expected link `{link}`)")
    return out


def main():
    args = [Path(a).resolve() for a in sys.argv[1:]]
    targets = args or list(pages())
    if not targets:
        print("no spell pages found")
        return 1

    nav_text = NAV.read_text(encoding="utf-8") if NAV.exists() else ""
    failed = 0
    for p in targets:
        if not p.exists():
            print(f"FAIL {p}\n       - file does not exist")
            failed += 1
            continue
        problems = check(p, nav_text)
        if problems:
            failed += 1
            print(f"FAIL {p.relative_to(DOCS) if DOCS in p.parents else p}")
            for msg in problems:
                print(f"       - {msg}")

    ok = len(targets) - failed
    print(f"\n{ok}/{len(targets)} page(s) OK" + (f", {failed} failed" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
