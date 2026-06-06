"""Tests for the map file parser."""

import pytest
from pathlib import Path

from combat_sim.ui.maps import (
    parse_map, parse_map_file, discover_maps, MapDef, MapParseError,
)


SAMPLE_MAPS = Path(__file__).parent.parent / "combat_sim" / "ui" / "resources" / "maps"


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

class TestParseMap:
    def test_minimal_map(self):
        text = """\
---
.....
.1...
....A
.....
"""
        m = parse_map(text)
        assert m.width == 5
        assert m.height == 4
        assert m.blocked == set()
        assert m.party_a_slots == {1: (1, 1)}
        assert m.party_b_slots == {1: (4, 2)}

    def test_walls(self):
        text = """\
---
###
#1#
###
"""
        m = parse_map(text)
        # 9 walls minus the slot in the middle
        assert (0, 0) in m.blocked
        assert (1, 1) not in m.blocked   # that's the slot
        assert m.party_a_slots == {1: (1, 1)}
        assert len(m.blocked) == 8

    def test_metadata(self):
        text = """\
name: My Map
description: A test map.
---
1A
"""
        m = parse_map(text)
        assert m.name == "My Map"
        assert m.description == "A test map."
        assert m.party_a_slots == {1: (0, 0)}
        assert m.party_b_slots == {1: (1, 0)}

    def test_comments_skipped(self):
        text = """\
// top-level comment
// another
name: With Comments
// even here
---
1A
"""
        m = parse_map(text)
        assert m.name == "With Comments"

    def test_unknown_metadata_ignored(self):
        """Forward-compat: unknown keys don't crash old parsers."""
        text = """\
name: Test
future_thing: some-value
---
1A
"""
        m = parse_map(text)
        assert m.name == "Test"

    def test_short_rows_padded(self):
        """Trailing-shorter rows pad with OPEN, no errors."""
        text = """\
---
#####
#...
##
"""
        m = parse_map(text)
        assert m.width == 5
        assert m.height == 3
        # the short row should be padded with OPEN, not WALL
        assert (4, 1) not in m.blocked
        assert (4, 2) not in m.blocked

    def test_multiple_party_slots(self):
        text = """\
---
12345
ABCDE
"""
        m = parse_map(text)
        assert m.party_a_slots == {1: (0, 0), 2: (1, 0), 3: (2, 0),
                                   4: (3, 0), 5: (4, 0)}
        assert m.party_b_slots == {1: (0, 1), 2: (1, 1), 3: (2, 1),
                                   4: (3, 1), 5: (4, 1)}


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

class TestErrors:
    def test_missing_separator(self):
        text = "name: X\n.....\n"
        with pytest.raises(MapParseError):
            parse_map(text)

    def test_unknown_symbol(self):
        text = "---\n.@.\n"
        with pytest.raises(MapParseError) as exc:
            parse_map(text)
        assert "@" in str(exc.value)

    def test_duplicate_party_a_slot(self):
        text = "---\n1..1\n"
        with pytest.raises(MapParseError) as exc:
            parse_map(text)
        assert "duplicate" in str(exc.value).lower()

    def test_duplicate_party_b_slot(self):
        text = "---\nA.A.\n"
        with pytest.raises(MapParseError) as exc:
            parse_map(text)
        assert "duplicate" in str(exc.value).lower()

    def test_empty_grid(self):
        text = "name: X\n---\n"
        with pytest.raises(MapParseError):
            parse_map(text)

    def test_unrecognised_line_before_grid(self):
        text = "this is not a metadata line\n---\n1A\n"
        with pytest.raises(MapParseError):
            parse_map(text)


# ---------------------------------------------------------------------------
# Bundled sample maps load cleanly
# ---------------------------------------------------------------------------

class TestSampleMaps:
    def test_all_samples_parse(self):
        maps = discover_maps(SAMPLE_MAPS)
        assert len(maps) >= 4
        # Every shipped map has at least one slot per side, otherwise the
        # UI can't place anyone.
        for m in maps:
            assert m.party_a_slots, f"{m.name} has no A slots"
            assert m.party_b_slots, f"{m.name} has no B slots"

    def test_discover_is_alphabetical(self):
        maps = discover_maps(SAMPLE_MAPS)
        names = [m.source_path.split("/")[-1] for m in maps]
        assert names == sorted(names)

    def test_pillar_matches_m1_geometry(self):
        """The pillar map and the M1 sim scenario must use the same
        wall coordinates — they're the same battle."""
        m = parse_map_file(SAMPLE_MAPS / "pillar.txt")
        # Pillar at x=7 for y=2..7 in both M1 and the file.
        for y in range(2, 8):
            assert (7, y) in m.blocked
        assert (7, 1) not in m.blocked   # gap at top
        assert (7, 8) not in m.blocked   # gap at bottom
