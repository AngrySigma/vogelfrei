#!/usr/bin/env python3
"""Minimal frontmatter reader/writer shared by Vogelfrei's generator scripts.

Deliberately not a YAML library: the book's frontmatter is a flat mapping of
scalars and simple string lists, and the scripts must round-trip keys they do
not manage (``image``, ``icon``, ``tier``, ...) byte-for-byte. A real YAML
round-trip would need an external dependency; ``python3 scripts/*.py`` runs on
the stdlib alone, without the uv venv.

Frontmatter is modelled as an ordered list of ``Entry`` records, one per
top-level key, each keeping its original source lines. Rewriting replaces only
the managed keys and leaves every other entry exactly as it was written.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Values that YAML would coerce to a non-string type if left bare. A spell with
# `range: 0` or `duration: no` must survive as the string the book wrote.
_YAML_RESERVED = {
    "true", "false", "yes", "no", "on", "off", "null", "none", "~", "",
}
_NEEDS_QUOTE_CHARS = set(":#{}[],&*!|>%@`\"'")


@dataclass
class Entry:
    """One top-level frontmatter key and the raw lines that produced it."""

    key: str
    lines: list[str] = field(default_factory=list)

    @property
    def scalar(self) -> str:
        """The scalar value of this key ('' for a list or an empty key)."""
        head = self.lines[0]
        _, _, rest = head.partition(":")
        return unquote(rest.strip())

    @property
    def items(self) -> list[str]:
        """The list value of this key, in either the inline or block form."""
        head = self.lines[0]
        _, _, rest = head.partition(":")
        rest = rest.strip()
        if rest.startswith("["):
            inner = rest[1:].rsplit("]", 1)[0]
            return [unquote(x.strip()) for x in inner.split(",") if x.strip()]
        out = []
        for line in self.lines[1:]:
            stripped = line.strip()
            if stripped.startswith("- "):
                out.append(unquote(stripped[2:].strip()))
        return out


def unquote(value: str) -> str:
    """Strip one layer of matching YAML quotes from a scalar."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\") if value[0] == '"' else inner
    return value


def yaml_scalar(value: str) -> str:
    """Render a Python string as a YAML scalar, quoting only when needed."""
    text = str(value)
    if (
        text.strip().lower() in _YAML_RESERVED
        or text != text.strip()
        or text[:1] in _NEEDS_QUOTE_CHARS
        or text[:1] == "-"
        or ": " in text
        or " #" in text
        or _looks_numeric(text)
    ):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _looks_numeric(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def split_document(text: str) -> tuple[str | None, str]:
    """Split a Markdown file into (frontmatter block, body).

    Returns ``(None, text)`` when the file has no frontmatter. The block
    excludes both ``---`` fences; the body starts after the closing fence.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            block = "".join(lines[1:i])
            return block.rstrip("\n"), "".join(lines[i + 1:])
    return None, text


def parse_entries(block: str) -> list[Entry]:
    """Parse a frontmatter block into ordered top-level entries."""
    entries: list[Entry] = []
    current: Entry | None = None
    for line in block.splitlines():
        key = _top_level_key(line)
        if key is not None:
            current = Entry(key, [line])
            entries.append(current)
        elif current is not None:
            current.lines.append(line)
    return entries


def _top_level_key(line: str) -> str | None:
    """Return the key if the line opens an unindented ``key:`` entry."""
    if not line or line[0].isspace() or line.lstrip().startswith("#"):
        return None
    key, sep, _ = line.partition(":")
    if not sep or not key or not all(c.isalnum() or c in "_-" for c in key):
        return None
    return key


def find(entries: list[Entry], key: str) -> Entry | None:
    for entry in entries:
        if entry.key == key:
            return entry
    return None


def get_scalar(entries: list[Entry], key: str) -> str | None:
    entry = find(entries, key)
    if entry is None:
        return None
    value = entry.scalar
    return value or None


def get_list(entries: list[Entry], key: str) -> list[str]:
    entry = find(entries, key)
    return entry.items if entry else []


def render(managed: list[tuple[str, object]], leftovers: list[Entry]) -> str:
    """Render a frontmatter block: managed keys first, then untouched entries.

    ``managed`` pairs a key with a string or int (scalar), a list of strings
    (block list) or ``None`` (drop the key). ``leftovers`` render verbatim.
    """
    out: list[str] = []
    for key, value in managed:
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            out.append(f"{key}:")
            out.extend(f"  - {yaml_scalar(item)}" for item in value)
        elif isinstance(value, int) and not isinstance(value, bool):
            out.append(f"{key}: {value}")  # a real YAML integer, e.g. level: 2
        else:
            out.append(f"{key}: {yaml_scalar(str(value))}")
    for entry in leftovers:
        out.extend(entry.lines)
    return "\n".join(out)


def compose(block: str, body: str) -> str:
    """Reassemble a Markdown document from a frontmatter block and a body."""
    return f"---\n{block}\n---\n{body.lstrip(chr(10))}"
