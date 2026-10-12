#!/usr/bin/env python3
"""Party step 3 — check every character is finished, then assemble the pack.

Reads pc1.json … pcN.json from --dir, verifies each one actually completed the
character-generation pipeline, and writes a single Markdown pack: a roster
table followed by every full sheet.

Exits 2 if any character is incomplete, so a party run cannot quietly ship a
half-generated PC. Use --allow-incomplete to write the pack anyway.
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "character-generation" / "scripts"))

from render_sheet import render  # noqa: E402
from vflib import die, fmt_money, load_state  # noqa: E402


def slot_key(path: Path):
    m = re.search(r"(\d+)", path.stem)
    return (int(m.group(1)) if m else 0, path.stem)


def problems(state: dict) -> list[str]:
    """What is still missing from a finished level-1 character."""
    out = []
    if not state.get("abilities"):
        out.append("no ability scores")
    if not state.get("class"):
        out.append("no class (apply_class.py never ran)")
    if not state.get("status"):
        out.append("no Status")
    if not state.get("name"):
        out.append("no name (roll_name.py never ran)")
    if not state.get("bio"):
        out.append("no bio (roll_bio.py never ran)")
    if not state.get("inventory"):
        out.append("empty inventory (nothing bought)")
    combat = state.get("combat") or {}
    if not combat:
        out.append("no derived combat block (finalize.py never ran)")
    elif combat.get("melee_ac") is None:
        out.append("no Melee AC")
    if state.get("class") in ("Magic-User", "Cleric", "Rogue", "Warrior"):
        if not state.get("notes") and not state.get("skills"):
            out.append(f"no class-specific finishing recorded "
                       f"(class-{state['class'].lower()} skill never ran)")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, required=True, help="the party directory")
    ap.add_argument("--out", type=Path, help="write the pack here (default: <dir>/pack.md)")
    ap.add_argument("--title", default="Party", help="pack title")
    ap.add_argument("--brief", type=Path,
                    help="a Markdown brief to quote above the roster (e.g. <dir>/party.md)")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="write the pack even if characters are unfinished")
    args = ap.parse_args()

    files = sorted(args.dir.glob("pc*.json"), key=slot_key)
    if not files:
        die(f"no pc*.json files in {args.dir} (run roll_party.py first)")

    states, broken = [], {}
    for f in files:
        st = load_state(f)
        states.append((f, st))
        p = problems(st)
        if p:
            broken[f.name] = p

    out = [f"# {args.title}", ""]
    if args.brief and args.brief.exists():
        out.append(args.brief.read_text(encoding="utf-8").strip())
        out.append("")

    out.append("## Roster")
    out.append("")
    out.append("| # | Name | Class / Career | Status | Align | W / S | AC (M/R) | Move | Purse |")
    out.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for i, (f, st) in enumerate(states, 1):
        combat = st.get("combat") or {}
        enc = combat.get("encumbrance") or {}
        career = st.get("career")
        klass = st.get("class") or "?"
        cc = f"{career} ({klass})" if career else klass
        ac = (f"{combat.get('melee_ac', '?')} / {combat.get('ranged_ac', '?')}"
              if combat else "—")
        move = f"{enc['miles_per_day']} mi, {enc['combat']}" if enc else "—"
        out.append(
            f"| {i} | {st.get('name', '—')} | {cc} | {st.get('status', '—')} "
            f"| {st.get('alignment', '—')} "
            f"| {st.get('wounds', '?')} / {st.get('stamina', '?')} | {ac} | {move} "
            f"| {fmt_money(st.get('money_bp', 0))} |")

    warned = [(st.get("name") or f.stem, w)
              for f, st in states for w in (st.get("warnings") or [])]
    if warned:
        out.append("")
        out.append("### Open flags")
        out.append("")
        for who, w in warned:
            out.append(f"- **{who}**: {w}")

    for f, st in states:
        out.append("")
        out.append("---")
        out.append("")
        out.append(render(st).strip())

    dest = args.out or (args.dir / "pack.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"{len(states)} characters -> {dest}")
    for name, ps in broken.items():
        print(f"INCOMPLETE {name}: {'; '.join(ps)}", file=sys.stderr)
    if broken and not args.allow_incomplete:
        print(f"\nerror: {len(broken)} character(s) unfinished — rerun the missing steps "
              f"(or pass --allow-incomplete)", file=sys.stderr)
        raise SystemExit(2)
    if warned:
        print(f"{len(warned)} open flag(s) carried into the pack — relay them to the player.")


if __name__ == "__main__":
    main()
