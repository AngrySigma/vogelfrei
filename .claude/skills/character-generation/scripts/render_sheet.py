#!/usr/bin/env python3
"""Step 7 — render the finished character as a Markdown sheet."""
import argparse
from pathlib import Path

from vflib import ABILITIES, fmt_money, load_state


def render(state: dict) -> str:
    out = []
    name = state.get("name", "Unnamed")
    career = state.get("career", "?")
    klass = state.get("class", "?")
    out.append(f"# {name} — {career} ({klass}, Level {state.get('level', 1)})")
    bio = state.get("bio", {})
    line = [f"**Alignment**: {state.get('alignment', '?')}",
            f"**Status**: {state.get('status', '?')}"]
    if bio:
        line.append(f"**Bio**: {bio.get('sex', '?')}, {bio.get('age', '?')} years, "
                    f"{bio.get('height', '?')}, {bio.get('build', '?')} build")
    if state.get("culture"):
        line.append(f"**Culture**: {state['culture']}")
    out.append("  \n".join(line))

    out.append("\n## Abilities\n")
    out.append("| Ability | Score | Mod |")
    out.append("| --- | --- | --- |")
    for a in ABILITIES:
        v = state["abilities"].get(a, {})
        out.append(f"| {a} | {v.get('score', '?')} | {v.get('mod', 0):+d} |")

    combat = state.get("combat", {})
    enc = combat.get("encumbrance", {})
    out.append("\n## Combat\n")
    out.append(f"- **Wounds**: {state.get('wounds', '?')}   **Stamina**: {state.get('stamina', '?')}")
    out.append(f"- **WS**: +{state.get('ws', 0)}   **BS**: +{state.get('bs', 0)}")
    out.append(f"- **Melee AC**: {combat.get('melee_ac', '?')}   "
               f"**Ranged AC**: {combat.get('ranged_ac', '?')}")
    armor = combat.get("armor_worn") or "none"
    if combat.get("shield"):
        armor += f" + {combat['shield']}"
    out.append(f"- **Armour**: {armor} (Armour Rating {combat.get('armor_rating', 0)})")
    if enc:
        out.append(f"- **Encumbrance**: {enc['points']} points — {enc['label']} "
                   f"({enc['miles_per_day']} miles/day, {enc['combat']} per combat round)")

    saves = state.get("saves", {})
    if saves:
        out.append("\n## Saving Throws\n")
        cols = list(saves)
        out.append("| " + " | ".join(cols) + " |")
        out.append("|" + " --- |" * len(cols))
        out.append("| " + " | ".join(str(saves[c]) for c in cols) + " |")

    if combat.get("weapons"):
        out.append("\n## Weapons\n")
        out.append("| Weapon | Damage | Length/Range | Requirement | Notes |")
        out.append("| --- | --- | --- | --- | --- |")
        for w in combat["weapons"]:
            qty = f"{w['qty']}x " if w["qty"] > 1 else ""
            out.append(f"| {qty}{w['name']} | {w['damage'] or '—'} | {w['reach'] or '—'} "
                       f"| {w['requirements']} | {w['note'] or ''} |")

    if state.get("career_trait"):
        out.append("\n## Career Trait\n")
        out.append(f"> {state['career_trait']}")
    if state.get("career_combat_skills"):
        out.append(f"\n**Career Combat Skills**: {state['career_combat_skills']}")
    if state.get("career_skills"):
        out.append(f"\n**Career Skills**: {state['career_skills']}")
    if state.get("skills"):
        out.append("\n## Skills\n")
        for name_, rating in sorted(state["skills"].items()):
            out.append(f"- {name_}: {rating}-in-6")
    if state.get("skill_points"):
        out.append(f"\n*Unspent skill points: {state['skill_points']}*")

    out.append("\n## Inventory\n")
    if state.get("inventory"):
        for e in state["inventory"]:
            price = fmt_money(e["unit_bp"] * e["qty"])
            out.append(f"- {e['qty']}x {e['name']} ({price})")
    else:
        out.append("- (empty)")
    out.append(f"\n**Purse**: {fmt_money(state.get('money_bp', 0))}")

    if state.get("notes"):
        out.append("\n## Notes\n")
        for n in state["notes"]:
            out.append(f"- {n}")

    refs = [p for p in (state.get("class_page"), state.get("career_page")) if p]
    if refs:
        out.append("\n---\n*Rules*: " + " · ".join(refs))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--out", type=Path, help="write the sheet here instead of stdout")
    args = ap.parse_args()

    sheet = render(load_state(args.file))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(sheet, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(sheet)


if __name__ == "__main__":
    main()
