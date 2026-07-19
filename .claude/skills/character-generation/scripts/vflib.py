"""Shared library for the Vogelfrei character-generation scripts.

Everything rule-derived (class tables, career pages, equipment prices) is
parsed from the rulebook sources under docs/ at runtime, so content edits
don't require touching these scripts. Only things the rulebook leaves to
table talk (class-fit heuristics, the 2d6/d6 roll tables transcribed from
Class and Career.md) are encoded here.

Money is handled internally in brass pieces (bp):
1 gp = 50 sp = 600 bp, therefore 1 sp = 12 bp.
"""
from __future__ import annotations

import difflib
import json
import random
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Core constants
# ---------------------------------------------------------------------------

ABILITIES = ["Strength", "Toughness", "Agility", "Intelligence", "Willpower", "Leadership"]

CLASSES = [
    "Warrior", "Magic-User", "Cleric", "Ranger", "Rogue", "Peasant",
    "Academic", "Townsman", "Dwarf", "High Elf", "Wood Elf", "Halfling",
]

# Alignment rules (docs/Character/Alignment.md): divine powers must be
# Orderly; Elves and Magic-Users must be Chaotic; everyone else is free.
FORCED_ALIGNMENT = {
    "Cleric": "Order",
    "Magic-User": "Chaos",
    "High Elf": "Chaos",
    "Wood Elf": "Chaos",
}
ALIGNMENTS = ["Order", "Neutral", "Chaos"]

# Transcribed from docs/Character/Class and Career.md (roll tables).
CLASS_ROLL_2D6 = {
    2: "Dwarf", 3: "Halfling", 4: "Rogue", 5: "Ranger", 6: "Townsman",
    7: "Peasant", 8: "Warrior", 9: "Cleric", 10: "Academic",
    11: "Magic-User", 12: "High Elf",
}
CAREER_ROLL_D6 = {
    "Dwarf": ["Artisan", "Karak Ranger", "Engineer", "Brewer", "Miner", "Troll Slayer"],
    "Halfling": ["Artisan", "Charlatan", "Badger Rider", "Herbalist", "Merchant", "Scout"],
    "Rogue": ["Charlatan", "Grave Robber", "Smuggler", "Thief", "Wrecker", "Outlaw"],
    "Ranger": ["Boatman", "Bounty Hunter", "Coachman", "Road Warden", "Peddlar", "Sailor"],
    "Townsman": ["Artisan", "Rat Catcher", "Beggar", "Militia", "Scion", "Merchant"],
    "Peasant": ["Miner", "Villager", "Herbalist", "Hunter", "Scout", "Hedge Witch"],
    "Warrior": ["Mercenary", "Pit Fighter", "Soldier", "Knight", "Witch Hunter", "Duellist"],
    "Cleric": ["Priest", "Zealot", "Warrior Priest", None, None, None],
    "Academic": ["Apothecary", "Barber", "Engineer", "Scholar", "Alchemist", "Cartographer"],
    "Magic-User": ["Wizard", "Witch", "Bright Wizard", "Grey Wizard", "Light Wizard", None],
    "High Elf": ["Artisan", "Wizard", "Sword-master", "Hunter", "Shadow", None],
    "Wood Elf": ["Artisan", "Wizard", "Hunter", "Blade dancer", "Waywatcher", None],
}

# Fit heuristics (not rulebook text): which abilities pay off most for each
# class, used to rank suggestions. Primary abilities count double.
CLASS_HINTS = {
    "Warrior": {"primary": ["Strength", "Toughness"], "secondary": ["Agility"],
                "note": "best Wounds among humans; melee attack runs on Strength"},
    "Magic-User": {"primary": ["Intelligence"], "secondary": ["Agility"],
                   "note": "must be Chaotic; cannot wear armour or use shields"},
    "Cleric": {"primary": ["Willpower"], "secondary": ["Toughness", "Leadership"],
               "note": "must be Orderly; divine miracles"},
    "Ranger": {"primary": ["Agility", "Toughness"], "secondary": ["Strength"],
               "note": "skill points; travel bonuses"},
    "Rogue": {"primary": ["Agility"], "secondary": ["Intelligence", "Leadership"],
              "note": "no fixed social standing"},
    "Peasant": {"primary": ["Toughness"], "secondary": ["Willpower", "Strength"],
                "note": "skill points; +2 reactions with animals"},
    "Academic": {"primary": ["Intelligence"], "secondary": ["Willpower"],
                 "note": "skill points; reads and writes"},
    "Townsman": {"primary": ["Leadership"], "secondary": ["Intelligence", "Agility"],
                 "note": "skill points; +2 urban reactions, Haggle 2-in-6"},
    "Dwarf": {"primary": ["Toughness", "Strength"], "secondary": [],
              "note": "d10 Wounds and the best saves; demihuman"},
    "High Elf": {"primary": ["Intelligence", "Agility"], "secondary": [],
                 "note": "must be Chaotic; arcane demihuman"},
    "Wood Elf": {"primary": ["Agility"], "secondary": ["Intelligence"],
                 "note": "must be Chaotic; wilderness demihuman"},
    "Halfling": {"primary": ["Agility"], "secondary": ["Toughness"],
                 "note": "small; save throws improve fast; demihuman"},
}

BP_PER_SP = 12
BP_PER_GP = 600

WEAPON_CATEGORIES = {"Melee Weapons", "Ranged Weapons", "Firearms"}

# Armour that counts as metal for encumbrance (docs/Adventuring/Time and
# Movement.md); three-quarter and heavier weighs in at +2 instead.
METAL_ARMOUR = {"Jack Chain", "Chain", "Brigandine", "Half-armour",
                "Three-quarter armour", "Full-plate"}
HEAVY_ARMOUR = {"Three-quarter armour", "Full-plate"}

# Encumbrance points -> (label, miles/day, per turn, combat, running)
MOVEMENT_TABLE = [
    (1, "Unencumbered", 24, "120'", "40'", "120'"),
    (2, "Lightly Encumbered", 18, "90'", "30'", "90'"),
    (3, "Heavily Encumbered", 12, "60'", "20'", "60'"),
    (4, "Severely Encumbered", 6, "30'", "10'", "30'"),
]


def die(msg: str, code: int = 1):
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


# ---------------------------------------------------------------------------
# Abilities and dice
# ---------------------------------------------------------------------------

def modifier(score: int) -> int:
    if score <= 3:
        return -3
    if score <= 5:
        return -2
    if score <= 8:
        return -1
    if score <= 12:
        return 0
    if score <= 15:
        return 1
    if score <= 17:
        return 2
    return 3


def canon_ability(text: str) -> str:
    t = text.strip().lower()
    matches = [a for a in ABILITIES if a.lower().startswith(t)]
    if len(matches) != 1:
        die(f"ambiguous or unknown ability '{text}' (use one of: {', '.join(ABILITIES)})")
    return matches[0]


def canon_class(text: str) -> str:
    t = re.sub(r"[\s_-]+", " ", text.strip().lower())
    aliases = {"mu": "Magic-User", "magic user": "Magic-User", "wizard": "Magic-User"}
    if t in aliases:
        return aliases[t]
    matches = [c for c in CLASSES if re.sub(r"[\s-]+", " ", c.lower()) == t]
    if not matches:
        matches = [c for c in CLASSES if c.lower().startswith(t)]
    if len(matches) != 1:
        die(f"ambiguous or unknown class '{text}' (options: {', '.join(CLASSES)})")
    return matches[0]


class Dice:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def roll(self, n: int, sides: int) -> int:
        return sum(self.rng.randint(1, sides) for _ in range(n))

    def roll_expr(self, expr: str) -> int:
        m = re.fullmatch(r"(\d*)\s*d\s*(\d+)", expr.strip())
        if not m:
            die(f"cannot parse die expression '{expr}'")
        return self.roll(int(m.group(1) or 1), int(m.group(2)))


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------

def to_bp(amount: int, unit: str) -> int:
    unit = unit.lower()
    if unit == "bp":
        return amount
    if unit == "sp":
        return amount * BP_PER_SP
    if unit == "gp":
        return amount * BP_PER_GP
    die(f"unknown coin unit '{unit}'")


def parse_money(text: str) -> int:
    m = re.fullmatch(r"(\d+)\s*(bp|sp|gp)", text.strip().lower())
    if not m:
        die(f"cannot parse money value '{text}' (use e.g. '25sp', '3 gp', '10bp')")
    return to_bp(int(m.group(1)), m.group(2))


def fmt_money(bp: int) -> str:
    sign = "-" if bp < 0 else ""
    bp = abs(bp)
    gp, rest = divmod(bp, BP_PER_GP)
    sp, brass = divmod(rest, BP_PER_SP)
    parts = [f"{n} {u}" for n, u in ((gp, "gp"), (sp, "sp"), (brass, "bp")) if n]
    return sign + (" ".join(parts) if parts else "0 sp")


def roll_starting_money(status: str, dice: Dice) -> tuple[int, str]:
    """docs/Character/Starting Possessions.md, level 1."""
    s = status.strip().lower()
    if s == "brass":
        n = dice.roll(10, 6) * 10
        return n, f"Brass status: 10d6 x 10 = {n} bp"
    if s == "silver":
        n = dice.roll(2, 6) * 10
        return n * BP_PER_SP, f"Silver status: 2d6 x 10 = {n} sp"
    if s == "gold":
        n = dice.roll(1, 6)
        return n * BP_PER_GP, f"Gold status: 1d6 = {n} gp"
    die(f"unknown status '{status}' (expected Brass, Silver or Gold)")


# ---------------------------------------------------------------------------
# Repo / state
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "docs" / "Character").is_dir():
            return parent
    die("cannot locate the rulebook: no docs/Character directory above the scripts")


def new_state() -> dict:
    return {
        "version": 1,
        "level": 1,
        "abilities": {},
        "swap_used": False,
        "inventory": [],
        "skills": {},
        "notes": [],
        "log": [],
    }


def load_state(path: Path) -> dict:
    if not path.exists():
        die(f"character file {path} does not exist (run roll_stats.py first)")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def log(state: dict, msg: str):
    state["log"].append(msg)
    print(msg)


# ---------------------------------------------------------------------------
# Markdown table parsing
# ---------------------------------------------------------------------------

def md_tables(text: str) -> list[list[list[str]]]:
    tables, current = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and len(s) > 1:
            cells = [c.strip() for c in s[1:-1].split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells) and any(c for c in cells):
                continue  # separator row
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


# ---------------------------------------------------------------------------
# Class pages
# ---------------------------------------------------------------------------

def class_page(name: str) -> Path:
    return repo_root() / "docs" / "Character" / "Classes" / name / "index.md"


def load_class(name: str) -> dict:
    path = class_page(name)
    if not path.exists():
        die(f"class page not found: {path}")
    text = path.read_text(encoding="utf-8")
    info = {
        "name": name,
        "page": str(path.relative_to(repo_root())),
        "wounds_die": None, "wounds_min": 0, "stamina_die": None,
        "ws": 0, "bs": 0, "skill_points": 0, "saves": {},
    }
    for table in md_tables(text):
        header = [h.lower() for h in table[0]]
        if not header or header[0] != "level":
            continue
        row1 = next((r for r in table[1:] if r and r[0].strip() == "1"), None)
        if row1 is None:
            continue
        cells = dict(zip(header, row1))
        if "wounds" in cells:
            m = re.match(r"(\d*d\d+)\s*\(min\s*(\d+)\)", cells["wounds"])
            if m:
                info["wounds_die"], info["wounds_min"] = m.group(1), int(m.group(2))
            if "stamina" in cells:
                m = re.search(r"\d*d\d+", cells["stamina"])
                if m:
                    info["stamina_die"] = m.group(0)
            if "combat skill points" in cells:
                ws = re.search(r"(\d+)\s*WS", cells["combat skill points"])
                bs = re.search(r"(\d+)\s*BS", cells["combat skill points"])
                info["ws"] = int(ws.group(1)) if ws else 0
                info["bs"] = int(bs.group(1)) if bs else 0
            if "skill points" in cells:
                m = re.search(r"\d+", cells["skill points"])
                if m:
                    info["skill_points"] = int(m.group(0))
        elif "paralyze" in header:
            for col in ("Paralyze", "Poison", "Breath", "Device", "Magic"):
                if col.lower() in cells and cells[col.lower()].strip().isdigit():
                    info["saves"][col] = int(cells[col.lower()])
    if not info["wounds_die"]:
        die(f"could not parse the level table on {path}")
    if not info["saves"]:
        die(f"could not parse the saving-throw table on {path}")
    return info


# ---------------------------------------------------------------------------
# Career pages
# ---------------------------------------------------------------------------

def strip_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text).strip()


def careers_of(klass: str) -> list[Path]:
    d = repo_root() / "docs" / "Character" / "Classes" / klass / "Careers"
    return sorted(d.glob("*.md")) if d.is_dir() else []


def find_career(career: str, klass: str | None = None) -> Path:
    """Locate a career page, preferring the character's own class directory.

    Some careers are shared and live under another class (e.g. Townsman's
    Artisan links to the Dwarf page), so fall back to a repo-wide search.
    """
    root = repo_root() / "docs" / "Character" / "Classes"
    want = career.strip().lower()
    pools = []
    if klass:
        pools.append(careers_of(klass))
    pools.append([p for d in sorted(root.iterdir()) if d.is_dir() for p in careers_of(d.name)])
    for pool in pools:
        exact = [p for p in pool if p.stem.lower() == want]
        if exact:
            return exact[0]
    stems = {p.stem.lower(): p for pool in pools for p in pool}
    close = difflib.get_close_matches(want, stems.keys(), n=3, cutoff=0.6)
    if len(close) == 1:
        return stems[close[0]]
    hint = f" (did you mean: {', '.join(stems[c].stem for c in close)}?)" if close else ""
    die(f"career '{career}' not found{hint}")


def parse_career(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    info = {"name": path.stem, "page": str(path.relative_to(repo_root())),
            "status": None, "combat_skills": None, "skills": None, "trait": None}
    m = re.search(r"\*\*Status\*\*:\s*([A-Za-z]+)", text)
    if m:
        info["status"] = m.group(1).capitalize()
    else:
        fm = re.match(r"---\n(.*?)\n---", text, re.S)
        if fm:
            tag = re.search(r"-\s*(brass|silver|gold)\b", fm.group(1), re.I)
            if tag:
                info["status"] = tag.group(1).capitalize()
    m = re.search(r"\*\*Combat Skills\*\*:\s*(.+)", text)
    if m:
        info["combat_skills"] = strip_links(m.group(1))
    m = re.search(r"\*\*Skills\*\*:\s*(.+)", text)
    if m:
        info["skills"] = strip_links(m.group(1))
    m = re.search(r'!!!\s+tip\s+"Trait"\n((?:[ \t]+\S.*\n?)*)', text)
    if m:
        info["trait"] = " ".join(line.strip() for line in m.group(1).splitlines()).strip()
    return info


# ---------------------------------------------------------------------------
# Equipment database (parsed from docs/Equipment)
# ---------------------------------------------------------------------------

@dataclass
class HCell:
    text: str = ""
    em: bool = False
    strong: bool = False
    rowspan: int = 1
    colspan: int = 1


@dataclass
class Item:
    name: str
    variant: str | None
    category: str
    city_bp: int | None
    rural_bp: int | None
    enc: str  # "normal" | "light" (non-encumbering) | "oversize"
    props: dict = field(default_factory=dict)

    @property
    def display(self) -> str:
        return f"{self.name} ({self.variant})" if self.variant else self.name


class _HTMLTables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self._head, self._body = [], []
        self._row = None
        self._cell = None
        self._in_head = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._head, self._body = [], []
        elif tag == "thead":
            self._in_head = True
        elif tag == "tbody":
            self._in_head = False
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = HCell(rowspan=int(a.get("rowspan", 1)), colspan=int(a.get("colspan", 1)))
        elif tag in ("em", "i") and self._cell is not None:
            self._cell.em = True
        elif tag in ("strong", "b") and self._cell is not None:
            self._cell.strong = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            (self._head if self._in_head else self._body).append(self._row)
            self._row = None
        elif tag == "table":
            self.tables.append((self._head, self._body))

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.text += data


def _expand_grid(rows: list[list[HCell]]) -> list[list[HCell | None]]:
    grid, carry = [], {}
    for row in rows:
        line = {}
        for col, (cell, _left) in carry.items():
            for c in range(col, col + cell.colspan):
                line[c] = cell
        new_carry = {col: (cell, left - 1) for col, (cell, left) in carry.items() if left - 1 > 0}
        col = 0
        for cell in row:
            while col in line:
                col += 1
            for c in range(col, col + cell.colspan):
                line[c] = cell
            if cell.rowspan > 1:
                new_carry[col] = (cell, cell.rowspan - 1)
            col += cell.colspan
        carry = new_carry
        width = max(line) + 1 if line else 0
        grid.append([line.get(c) for c in range(width)])
    return grid


_PRICE_RE = re.compile(r"(\d+)\s*(bp|sp|gp)", re.I)


def _parse_price_cell(text: str) -> int | None:
    t = text.strip()
    if t in ("", "-", "–", "—"):
        return None
    if t == "0":
        return 0
    m = _PRICE_RE.search(t)
    return to_bp(int(m.group(1)), m.group(2)) if m else None


def _md_enc(name: str) -> tuple[str, str]:
    """Return (clean name, enc class) from markdown emphasis markers."""
    stars = len(name) - len(name.lstrip("*"))
    clean = name.strip("*").strip()
    if stars >= 3:
        return clean, "oversize"
    if stars == 1:
        return clean, "light"
    return clean, "normal"


def _header_semantics(head_grid: list[list[HCell | None]]) -> dict[int, str]:
    width = max((len(r) for r in head_grid), default=0)
    sem = {}
    for col in range(width):
        texts = []
        for row in head_grid:
            if col < len(row) and row[col] is not None:
                t = row[col].text.strip()
                if t and t not in texts:
                    texts.append(t)
        h = " ".join(texts).lower()
        if "city" in h and "rural" in h:
            sem[col] = "cost_combo"
        elif "city" in h:
            sem[col] = "city"
        elif "rural" in h:
            sem[col] = "rural"
        elif "damage" in h:
            sem[col] = "damage"
        elif "length" in h:
            sem[col] = "length"
        elif "range" in h:
            sem[col] = "range"
        elif "requirement" in h:
            sem[col] = "requirements"
        elif "melee equivalent" in h:
            sem[col] = "melee_equivalent"
        elif "armor rating" in h or "armour rating" in h:
            sem[col] = "armor_rating"
    return sem


def _armor_props(text: str) -> dict:
    props = {}
    t = text.strip()
    if t.isdigit():
        props["armor_rating"] = int(t)
        return props
    m = re.search(r"\+(\d+)\s*Melee AC", t, re.I)
    if m:
        props["melee_ac"] = int(m.group(1))
    m = re.search(r"\+(\d+)\s*Ranged AC", t, re.I)
    if m:
        props["ranged_ac"] = int(m.group(1))
    return props


def _items_from_grids(head, body, category) -> list[Item]:
    sem = _header_semantics(head)
    # Columns that belong to the item-name block: everything before the first
    # semantic column.
    first_sem = min(sem) if sem else 1
    items = []
    for row in body:
        if not row or row[0] is None:
            continue
        name_cell = row[0]
        name = name_cell.text.strip()
        if not name or name in ("City", "Rural"):
            continue
        variant = None
        for c in range(1, first_sem):
            if c < len(row) and row[c] is not None and row[c] is not name_cell:
                v = row[c].text.strip()
                if v:
                    variant = v
        city = rural = None
        props = {}
        for col, kind in sem.items():
            if col >= len(row) or row[col] is None:
                continue
            text = row[col].text.strip()
            if kind == "city":
                city = _parse_price_cell(text)
            elif kind == "rural":
                rural = _parse_price_cell(text)
            elif kind == "cost_combo":
                parts = text.split("/")
                city = _parse_price_cell(parts[0]) if parts else None
                rural = _parse_price_cell(parts[1]) if len(parts) > 1 else None
            elif kind == "armor_rating":
                props.update(_armor_props(text))
            elif text and text not in ("-", "–", "—"):
                props[kind] = text
        # The emphasis flags mark encumbrance per the Equipment legend.
        flag_cell = name_cell
        if variant is not None and not name_cell.em and not name_cell.strong:
            pass  # group name carries the emphasis when present
        enc = "normal"
        if flag_cell.em and flag_cell.strong:
            enc = "oversize"
        elif flag_cell.em:
            enc = "light"
        items.append(Item(name, variant, category, city, rural, enc, props))
    return items


def _md_grid(table: list[list[str]]):
    """Convert a markdown table into (head, body) HCell grids.

    Handles the Armor.md pattern where a 'City | Rural' row sits in the body.
    """
    head_rows = [table[0]]
    body_rows = []
    for row in table[1:]:
        nonempty = {c for c in row if c}
        if nonempty and nonempty <= {"City", "Rural"}:
            head_rows.append(row)
        else:
            body_rows.append(row)

    def to_cells(rows, is_body):
        out = []
        for r in rows:
            cells = []
            for c in r:
                if is_body:
                    clean, enc = _md_enc(c)
                    cells.append(HCell(text=clean, em=enc in ("light", "oversize"),
                                       strong=enc == "oversize"))
                else:
                    cells.append(HCell(text=c))
            out.append(cells)
        return out

    return to_cells(head_rows, False), to_cells(body_rows, True)


def equipment_db() -> list[Item]:
    root = repo_root() / "docs" / "Equipment"
    items: list[Item] = []
    for path in sorted(root.rglob("*.md")):
        if path.name == "index.md":
            continue
        category = path.stem
        text = path.read_text(encoding="utf-8")
        if "<table" in text:
            parser = _HTMLTables()
            parser.feed(text)
            for head, body in parser.tables:
                items += _items_from_grids(_expand_grid(head), _expand_grid(body), category)
        for table in md_tables(text):
            if len(table[0]) < 2:
                continue
            head, body = _md_grid(table)
            items += _items_from_grids(_expand_grid(head), _expand_grid(body), category)
    return [i for i in items if i.city_bp is not None or i.rural_bp is not None
            or i.props.get("damage") or i.props]


def find_items(db: list[Item], query: str) -> list[Item]:
    q = query.strip().lower()
    exact = [i for i in db if i.display.lower() == q or i.name.lower() == q]
    if exact:
        return exact
    # Ignore "(2H)" style suffixes when matching.
    def base(s):
        return re.sub(r"\s*\(.*?\)", "", s).strip().lower()
    exact = [i for i in db if base(i.display) == q or base(i.name) == q]
    if exact:
        return exact
    subs = [i for i in db if q in i.display.lower()]
    if subs:
        return subs
    names = {i.display.lower(): i for i in db}
    close = difflib.get_close_matches(q, names.keys(), n=5, cutoff=0.6)
    return [names[c] for c in close]


# ---------------------------------------------------------------------------
# Encumbrance / movement (docs/Adventuring/Time and Movement.md)
# ---------------------------------------------------------------------------

def encumbrance(state: dict, worn_armor: str | None) -> dict:
    regular = 0
    oversize = 0
    for entry in state["inventory"]:
        if entry["name"] == worn_armor:
            continue  # worn armour is covered by the armour criteria below
        enc = entry.get("enc", "normal")
        if enc == "light":
            continue
        # Multiple small items of one type count as a single item.
        if enc == "oversize":
            oversize += 1
        else:
            regular += 1
    points = regular // 5 + oversize
    if worn_armor in HEAVY_ARMOUR:
        points += 2
    elif worn_armor in METAL_ARMOUR:
        points += 1
    points += state.get("enc_adjust", 0)
    points = max(points, 0)
    for limit, label, miles, turn, combat, running in MOVEMENT_TABLE:
        if points <= limit:
            movement = {"label": label, "miles_per_day": miles, "per_turn": turn,
                        "combat": combat, "running": running}
            break
    else:
        movement = {"label": "Overencumbered", "miles_per_day": 0, "per_turn": "0'",
                    "combat": "0'", "running": "0'"}
    return {"points": points, "regular_items": regular, "oversize_items": oversize, **movement}
