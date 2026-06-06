"""Map file format + parser.

A map file is plain text, designed to be hand-editable. Optional
``key: value`` metadata lines at the top, then a ``---`` separator,
then the ASCII grid.

Grid symbols::

    .         passable
    #         wall (terrain-blocked)
    1 .. 9    party A slot index (where member [N] starts)
    A .. I    party B slot index

Comment lines start with ``//`` and are ignored anywhere. Blank lines
above the separator are ignored. Width is the longest grid row;
shorter rows are right-padded with ``.``. Height is the number of grid
rows.

Each slot symbol must appear at most once. The party builder picks the
slot a creature wants by ``CreatureSpec.slot`` and looks it up here.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


WALL = "#"
OPEN = "."
COMMENT = "//"
SEP = "---"
SLOTS_A = "123456789"
SLOTS_B = "ABCDEFGHI"


@dataclass
class MapDef:
    """A parsed map. Positions are (x, y) with y growing downward, so
    grid row 0 corresponds to y=0 and prints at the top."""
    name: str
    width: int
    height: int
    blocked: set[tuple[int, int]]
    party_a_slots: dict[int, tuple[int, int]]
    party_b_slots: dict[int, tuple[int, int]]
    description: str = ""
    source_path: str | None = None


class MapParseError(ValueError):
    """Raised when a map file is malformed."""


def parse_map(text: str, *, source_path: str | None = None) -> MapDef:
    """Parse a map file's contents. ``source_path`` is recorded for error
    messages and stored on the resulting ``MapDef`` for diagnostics."""
    name = ""
    description_parts: list[str] = []
    grid_lines: list[str] = []
    in_grid = False

    for raw in text.splitlines():
        line = raw.rstrip("\n").rstrip("\r")
        stripped = line.strip()
        if not in_grid:
            if stripped.startswith(COMMENT) or not stripped:
                continue
            if stripped == SEP:
                in_grid = True
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip().lower()
                value = value.strip()
                if key == "name":
                    name = value
                elif key == "description":
                    description_parts.append(value)
                else:
                    # Unknown metadata key — silently accepted for forward
                    # compatibility (new metadata won't break old parsers).
                    pass
            else:
                raise MapParseError(
                    f"unrecognised line before grid separator: {line!r}"
                    + (f" (in {source_path})" if source_path else "")
                )
        else:
            # Grid lines: preserve as-is (whitespace inside the grid is
            # never expected; trailing spaces are tolerated but ignored).
            grid_lines.append(line.rstrip())

    if not grid_lines:
        raise MapParseError(
            "no grid found (missing '---' separator or empty grid)"
            + (f" in {source_path}" if source_path else "")
        )

    return _build_mapdef(name, "\n".join(description_parts),
                        grid_lines, source_path)


def parse_map_file(path: str | Path) -> MapDef:
    p = Path(path)
    return parse_map(p.read_text(encoding="utf-8"), source_path=str(p))


def _build_mapdef(name: str, description: str,
                 grid_lines: list[str],
                 source_path: str | None) -> MapDef:
    # Drop trailing blank rows (so a file with trailing newlines parses cleanly)
    while grid_lines and not grid_lines[-1].strip():
        grid_lines.pop()
    if not grid_lines:
        raise MapParseError("empty grid")

    width = max(len(row) for row in grid_lines)
    height = len(grid_lines)
    blocked: set[tuple[int, int]] = set()
    party_a: dict[int, tuple[int, int]] = {}
    party_b: dict[int, tuple[int, int]] = {}

    for y, row in enumerate(grid_lines):
        # Right-pad with OPEN so non-rectangular maps work.
        padded = row.ljust(width, OPEN)
        for x, ch in enumerate(padded):
            if ch == OPEN:
                continue
            if ch == WALL:
                blocked.add((x, y))
            elif ch in SLOTS_A:
                slot_id = int(ch)
                if slot_id in party_a:
                    raise MapParseError(
                        f"duplicate party A slot '{ch}' at ({x}, {y})"
                        + (f" in {source_path}" if source_path else "")
                    )
                party_a[slot_id] = (x, y)
            elif ch in SLOTS_B:
                slot_id = SLOTS_B.index(ch) + 1
                if slot_id in party_b:
                    raise MapParseError(
                        f"duplicate party B slot '{ch}' at ({x}, {y})"
                        + (f" in {source_path}" if source_path else "")
                    )
                party_b[slot_id] = (x, y)
            else:
                raise MapParseError(
                    f"unknown grid symbol {ch!r} at ({x}, {y})"
                    + (f" in {source_path}" if source_path else "")
                )

    if not name:
        # Derive from filename when metadata is missing.
        name = Path(source_path).stem if source_path else "untitled"

    return MapDef(
        name=name,
        description=description,
        width=width,
        height=height,
        blocked=blocked,
        party_a_slots=party_a,
        party_b_slots=party_b,
        source_path=source_path,
    )


def discover_maps(root: str | Path) -> list[MapDef]:
    """Load every ``.txt`` file under ``root`` as a MapDef. Order is
    alphabetical by filename for deterministic UI ordering."""
    p = Path(root)
    files = sorted(p.glob("*.txt"))
    return [parse_map_file(f) for f in files]
