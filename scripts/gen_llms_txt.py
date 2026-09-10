#!/usr/bin/env python3
"""Generate llms.txt / llms-full.txt for Vogelfrei.

``llms.txt`` is a small index — the site's name, its description, and every
page in reading order with a one-line summary and its tier gating.
``llms-full.txt`` is the whole rulebook as one Markdown file: ~50k words, small
enough to hand to a model whole, so a reader's assistant can answer from the
actual rules instead of guessing at an OSR average.

Reading order comes from the ``nav`` tree in ``zensical.toml``, which is the
book's table of contents; pages missing from ``nav`` are still emitted, under a
trailing "Unlisted" section, since a page absent from ``nav`` is invisible in
the site navigation and is usually an oversight worth seeing.

Relative Markdown links (``../../Equipment/Armor.md``) are rewritten to
absolute site URLs in ``llms-full.txt``: once the pages are concatenated, a
path relative to the original file resolves to nothing.

Usage:
    python3 scripts/gen_llms_txt.py                  # write both files
    python3 scripts/gen_llms_txt.py --check          # fail if llms.txt is stale
    python3 scripts/gen_llms_txt.py --site-dir site  # + raw .md next to each page
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import quote, urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vf_frontmatter as fm  # noqa: E402
from gen_view_manifest import ALL_TIERS, parse_tier_keys, url_key  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
CONFIG = REPO_ROOT / "zensical.toml"

# zensical.toml leaves site_url commented out (the book is served from both a
# domain root and a GitHub Pages subdirectory), so llms.txt needs its own
# canonical base. Override with --base-url when building for somewhere else.
DEFAULT_BASE_URL = "https://angrysigma.github.io/vogelfrei/"

SUMMARY_MAX = 220
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_PARAGRAPH = ("#", "|", "---", "***", "<", "```", "*[")
# The bold metadata block a spell, miracle or career page opens with is data,
# not a description — "Class: Warrior" tells a reader nothing they can't see.
META_BLOCK = re.compile(r"^\*\*[^*]+\*\*:")
LIST_ITEM = re.compile(r"^(?:[-+*]\s|\d+[.)]\s)")
ADMONITION = re.compile(r"^(?:!!!|\?\?\?\+?)\s+[a-z]+(?:\s+\"[^\"]*\")?\s*$")


# --------------------------------------------------------------------------
# Config and nav
# --------------------------------------------------------------------------

def load_config() -> dict:
    with CONFIG.open("rb") as handle:
        return tomllib.load(handle).get("project", {})


def flatten_nav(nav: list, trail: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str, str]]:
    """Flatten a Zensical nav tree into (section trail, nav title, md path)."""
    out: list[tuple[tuple[str, ...], str, str]] = []
    for item in nav:
        if isinstance(item, str):
            out.append((trail, "", item))
            continue
        for title, value in item.items():
            if isinstance(value, str):
                out.append((trail, title, value))
            elif isinstance(value, list):
                out.extend(flatten_nav(value, trail + (title,)))
    return out


# --------------------------------------------------------------------------
# Page reading
# --------------------------------------------------------------------------

class Page:
    def __init__(self, path: Path, trail: tuple[str, ...], nav_title: str, base: str):
        self.path = path
        self.trail = trail
        self.rel = path.relative_to(DOCS).as_posix()
        raw = path.read_text(encoding="utf-8")
        block, self.body = fm.split_document(raw)
        entries = fm.parse_entries(block) if block is not None else []
        self.tiers = parse_tier_keys(block, self.rel) if block is not None else list(ALL_TIERS)
        self.title = (
            fm.get_scalar(entries, "title")
            or _h1(self.body)
            or nav_title
            or path.stem
        )
        self.url = urljoin(base, quote(url_key(path, DOCS)))

    @property
    def section(self) -> str:
        return " › ".join(self.trail) if self.trail else "Book"

    @property
    def tier_note(self) -> str:
        """A parenthetical naming the tiers this page appears in, if gated."""
        if self.tiers == ALL_TIERS:
            return ""
        return f" [{', '.join(self.tiers)} only]"

    def summary(self) -> str:
        """A one-line gist: the page's first real sentence of prose.

        Skips the furniture a rules page opens with — the title, the metadata
        block, tables, lists. Plain prose wins; an admonition body is only a
        fallback, so a class page is described by its intro rather than by the
        first tip on it, while a career page — whose whole content is a
        `!!! tip "Trait"` — still gets a summary.
        """
        fallback = ""
        for para in re.split(r"\n\s*\n", self.body):
            text = para.strip()
            if not text or text.startswith(SKIP_PARAGRAPH):
                continue
            first, _, rest = text.partition("\n")
            if ADMONITION.match(first.strip()):
                if not fallback:
                    body = " ".join(line.strip() for line in rest.splitlines())
                    fallback = self._sentence(body)
                continue
            if META_BLOCK.match(first) or LIST_ITEM.match(first):
                continue
            sentence = self._sentence(text)
            if sentence:
                return sentence
        return fallback

    @staticmethod
    def _sentence(markdown: str) -> str:
        """The first sentence of a Markdown paragraph, flattened and clipped."""
        text = plain_text(markdown)
        if not text:
            return ""
        sentence = re.split(r"(?<=[.!?])\s", text)[0].strip()
        if len(sentence) > SUMMARY_MAX:
            sentence = sentence[:SUMMARY_MAX].rsplit(" ", 1)[0] + "…"
        return sentence

    def full_body(self, base: str) -> str:
        """The page body with relative links resolved against the live site."""
        return absolutize_links(self.body.strip(), self.rel, base)


def _h1(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def plain_text(markdown: str) -> str:
    """Flatten inline Markdown to readable text for a one-line summary."""
    text = MD_LINK.sub(r"\1", markdown)
    text = re.sub(r"[*_`]{1,3}", "", text)
    return " ".join(text.split())


def absolutize_links(body: str, page_rel: str, base: str) -> str:
    """Rewrite relative Markdown links to absolute site URLs."""
    page_dir = Path(page_rel).parent

    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", target, re.IGNORECASE):
            return match.group(0)
        path_part, _, fragment = target.partition("#")
        if not path_part:
            return match.group(0)
        decoded = path_part.replace("%20", " ")
        resolved = Path(page_dir, decoded).as_posix()
        parts: list[str] = []
        for segment in resolved.split("/"):
            if segment in ("", "."):
                continue
            if segment == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(segment)
        target_path = DOCS.joinpath(*parts) if parts else DOCS
        if target_path.suffix == ".md":
            key = url_key(target_path, DOCS) if target_path.is_relative_to(DOCS) else ""
            url = urljoin(base, quote(key))
        else:
            url = urljoin(base, quote("/".join(parts)))
        if fragment:
            url = f"{url}#{fragment}"
        return f"[{label}]({url})"

    return MD_LINK.sub(replace, body)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def collect_pages(config: dict, base: str) -> list[Page]:
    listed = flatten_nav(config.get("nav", []))
    pages: list[Page] = []
    seen: set[Path] = set()
    for trail, nav_title, rel in listed:
        path = DOCS / rel
        if not path.exists():
            print(f"  warning: nav lists a missing page: {rel}", file=sys.stderr)
            continue
        pages.append(Page(path, trail, nav_title, base))
        seen.add(path)
    unlisted = sorted(p for p in DOCS.rglob("*.md") if p not in seen)
    for path in unlisted:
        print(f"  warning: not in nav, filed under 'Unlisted': "
              f"{path.relative_to(DOCS).as_posix()}", file=sys.stderr)
        pages.append(Page(path, ("Unlisted",), "", base))
    return pages


def render_index(config: dict, pages: list[Page], base: str) -> str:
    name = config.get("site_name", "Vogelfrei")
    description = config.get("site_description", "")
    out = [f"# {name}", ""]
    if description:
        out += [f"> {description}", ""]
    out += [
        "This is the complete rulebook. Pages are listed in reading order.",
        "",
        "The book ships three views of itself — `simple`, `base` and `advanced` —",
        "and a page can belong to any set of them; a bracketed note marks any page",
        "that is not in all three. Nothing is hidden from the reader by tier: the",
        "gating only prunes the site navigation.",
        "",
    ]
    current = None
    for page in pages:
        if page.section != current:
            current = page.section
            if out and out[-1] != "":
                out.append("")
            out += [f"## {current}", ""]
        summary = page.summary()
        line = f"- [{page.title}]({page.url})"
        if summary:
            line += f": {summary}"
        out.append(line + page.tier_note)
    out += [
        "",
        "## Machine-readable",
        "",
        f"- [Full text]({urljoin(base, 'llms-full.txt')}): every page above "
        "concatenated into one Markdown file.",
        f"- [Spells]({urljoin(base, 'data/spells.json')}): Magic-User spells with "
        "class, level, duration, range and rules text.",
        f"- [Miracles]({urljoin(base, 'data/miracles.json')}): Cleric miracles, "
        "same shape as the spells.",
        f"- [Careers]({urljoin(base, 'data/careers.json')}): careers by class, with "
        "status, traits and level progression.",
        "",
    ]
    return "\n".join(out)


def render_full(config: dict, pages: list[Page], base: str) -> str:
    name = config.get("site_name", "Vogelfrei")
    description = config.get("site_description", "")
    out = [f"# {name} — complete text", ""]
    if description:
        out += [f"> {description}", ""]
    out += [
        f"Generated by scripts/gen_llms_txt.py from the sources at {base}.",
        "Pages appear in reading order. Each is preceded by an HTML comment "
        "naming its source file, URL and tiers.",
        "",
    ]
    for page in pages:
        out += [
            "",
            f"<!-- page: {page.rel} | url: {page.url} | "
            f"tiers: {', '.join(page.tiers)} -->",
            "",
            page.full_body(base),
            "",
        ]
    return "\n".join(out).rstrip("\n") + "\n"


def emit_raw(pages: list[Page], site_dir: Path, base: str) -> int:
    """Write each page's Markdown into the built site, next to its HTML.

    A page at ``/Equipment/Armor/`` gets ``/Equipment/Armor/index.md``, so a
    reader (or an agent) can fetch the source of any page by appending
    ``index.md`` to the URL it is already looking at.
    """
    written = 0
    for page in pages:
        key = url_key(page.path, DOCS)
        target = site_dir / key / "index.md"
        if not site_dir.exists():
            print(f"error: site dir not found: {site_dir}", file=sys.stderr)
            return 0
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page.full_body(base) + "\n", encoding="utf-8")
        written += 1
    return written


def main(argv: list[str]) -> int:
    check = "--check" in argv
    base = DEFAULT_BASE_URL
    site_dir: Path | None = None
    for i, arg in enumerate(argv):
        if arg == "--base-url" and i + 1 < len(argv):
            base = argv[i + 1]
        if arg == "--site-dir" and i + 1 < len(argv):
            site_dir = Path(argv[i + 1]).resolve()
    if not base.endswith("/"):
        base += "/"

    config = load_config()
    config.setdefault("site_url", base)
    pages = collect_pages(config, base)

    index_path = DOCS / "llms.txt"
    full_path = DOCS / "llms-full.txt"
    index = render_index(config, pages, base)
    full = render_full(config, pages, base)

    if check:
        current = index_path.read_text(encoding="utf-8") if index_path.exists() else None
        if current != index:
            print("error: docs/llms.txt is stale — re-run scripts/gen_llms_txt.py",
                  file=sys.stderr)
            return 1
        print(f"docs/llms.txt is up to date ({len(pages)} pages)")
        return 0

    index_path.write_text(index, encoding="utf-8")
    full_path.write_text(full, encoding="utf-8")
    words = len(full.split())
    print(f"wrote docs/llms.txt      ({len(pages)} pages)")
    print(f"wrote docs/llms-full.txt ({words:,} words, {len(full) / 1024:.0f} KB)")

    if site_dir is not None:
        written = emit_raw(pages, site_dir, base)
        if written:
            print(f"wrote {written} raw Markdown page(s) under {site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
