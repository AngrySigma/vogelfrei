#!/usr/bin/env python3
"""Step 6 — fill the armour and weapon slots and compute derived numbers.

AC per docs/Encounters/Combat Actions.md:
  Melee AC  = 8  + Agility bonus + WS + Armour Rating + shield melee bonus
  Ranged AC = 11 + Agility bonus      + Armour Rating + shield ranged bonus

Also computes encumbrance and movement, flags weapons the character is not
trained for, and enforces the Magic-User armour ban.
"""
import argparse
from pathlib import Path

from vflib import (encumbrance, equipment_db, find_items, fmt_money, load_state,
                   log, save_state)


def db_item(db, name):
    matches = find_items(db, name)
    return matches[0] if matches else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--wear", help="armour to wear (default: highest Armour Rating owned)")
    args = ap.parse_args()

    state = load_state(args.file)
    if not state.get("class"):
        import sys
        print("error: apply a class before finalizing", file=sys.stderr)
        raise SystemExit(1)
    db = equipment_db()
    agi = state["abilities"]["Agility"]["mod"]
    ws, bs = state.get("ws", 0), state.get("bs", 0)
    warnings = []

    armors, shields, weapons = [], [], []
    for e in state["inventory"]:
        props = e.get("props", {})
        if "armor_rating" in props:
            armors.append(e)
        elif "melee_ac" in props or "ranged_ac" in props:
            shields.append(e)
        elif e["category"] in ("Melee Weapons", "Ranged Weapons", "Firearms"):
            weapons.append(e)

    if state["class"] == "Magic-User" and (armors or shields):
        warnings.append("Magic-Users cannot wear armour or use shields — "
                        "owned pieces are carried, not worn")
        armors, shields = [], []

    worn = None
    if args.wear:
        worn = next((a for a in armors if args.wear.lower() in a["name"].lower()), None)
        if worn is None:
            warnings.append(f"--wear '{args.wear}' does not match an owned armour; ignored")
    if worn is None and armors:
        worn = max(armors, key=lambda a: a["props"]["armor_rating"])
    ar = worn["props"]["armor_rating"] if worn else 0

    shield = max(shields, key=lambda s: (s["props"].get("melee_ac", 0)
                                         + s["props"].get("ranged_ac", 0))) if shields else None
    if len(shields) > 1:
        warnings.append("several shields owned; using " + shield["name"])
    sh_melee = shield["props"].get("melee_ac", 0) if shield else 0
    sh_ranged = shield["props"].get("ranged_ac", 0) if shield else 0

    slots = []
    for e in weapons:
        props = e.get("props", {})
        req = props.get("requirements", "")
        if e["category"] == "Firearms":
            req = "Trained"  # per the Weapon Requirements table: all firearms are BS-trained
        note = ""
        if e["category"] == "Firearms" and bs < 1:
            note = "UNUSABLE: firearms need Trained BS (+1)"
        elif e["category"] == "Ranged Weapons" and "Trained" == req and bs < 1:
            note = "UNUSABLE: needs Trained BS (+1)"
        elif e["category"] == "Melee Weapons" and "Trained" == req and ws < 1:
            note = "counts as Improvised (d3): needs Trained WS (+1)"
        slots.append({"name": e["name"], "qty": e["qty"], "category": e["category"],
                      "damage": props.get("damage"),
                      "reach": props.get("length") or props.get("range"),
                      "requirements": req or "Untrained", "note": note})
        if note:
            warnings.append(f"{e['name']}: {note}")

    if not weapons:
        warnings.append("no weapon in the inventory")
    enc = encumbrance(state, worn_armor=worn["name"] if worn else None)

    state["combat"] = {
        "melee_ac": 8 + agi + ws + ar + sh_melee,
        "ranged_ac": 11 + agi + ar + sh_ranged,
        "armor_worn": worn["name"] if worn else None,
        "armor_rating": ar,
        "shield": shield["name"] if shield else None,
        "weapons": slots,
        "encumbrance": enc,
    }
    state["warnings"] = warnings

    log(state, f"Melee AC {state['combat']['melee_ac']} "
               f"(8 {agi:+d} Agi +{ws} WS +{ar} AR +{sh_melee} shield); "
               f"Ranged AC {state['combat']['ranged_ac']} "
               f"(11 {agi:+d} Agi +{ar} AR +{sh_ranged} shield)")
    log(state, f"Wearing: {worn['name'] if worn else 'no armour'}"
               + (f", carrying {shield['name']}" if shield else ""))
    for s in slots:
        log(state, f"Weapon: {s['qty']}x {s['name']} — {s['damage'] or '?'} dmg, "
                   f"{s['requirements']}{'; ' + s['note'] if s['note'] else ''}")
    log(state, f"Encumbrance {enc['points']} points -> {enc['label']} "
               f"({enc['miles_per_day']} miles/day, {enc['combat']} combat move)")
    log(state, f"Money left: {fmt_money(state.get('money_bp', 0))}")
    for w in warnings:
        print(f"WARNING: {w}")
    save_state(args.file, state)
    print("\nNext: render_sheet.py, then the class-specific skill (e.g. class-warrior).")


if __name__ == "__main__":
    main()
