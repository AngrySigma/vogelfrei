#!/usr/bin/env python3
"""Step 3 — apply class and career: swap (optional), Wounds, Stamina, saves,
WS/BS, skill points, alignment, Status and starting money.

Everything is parsed live from the class and career pages under
docs/Character/Classes/.
"""
import argparse
from pathlib import Path

from vflib import (ALIGNMENTS, CAREER_ROLL_D6, Dice, FORCED_ALIGNMENT, canon_ability,
                   canon_class, die, find_career, fmt_money, load_class, load_state,
                   log, modifier, parse_career, roll_starting_money, save_state)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--class", dest="klass", required=True)
    ap.add_argument("--career")
    ap.add_argument("--roll-career", action="store_true",
                    help="roll the career on the rulebook d6 table")
    ap.add_argument("--swap", nargs=2, metavar=("A", "B"),
                    help="swap two ability scores (allowed once, ever)")
    ap.add_argument("--alignment", help="Order, Neutral or Chaos (free classes only)")
    ap.add_argument("--status", help="override career Status if the page leaves it blank")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    state = load_state(args.file)
    if state.get("class"):
        die(f"class already applied ({state['class']}); start over with roll_stats.py --force")
    dice = Dice(args.seed)
    klass = canon_class(args.klass)

    if args.swap:
        if state.get("swap_used"):
            die("the one allowed ability swap was already used")
        a, b = (canon_ability(x) for x in args.swap)
        ab = state["abilities"]
        ab[a]["score"], ab[b]["score"] = ab[b]["score"], ab[a]["score"]
        for x in (a, b):
            ab[x]["mod"] = modifier(ab[x]["score"])
        state["swap_used"] = True
        log(state, f"Swapped {a} ({ab[a]['score']}) <-> {b} ({ab[b]['score']})")

    career_name = args.career
    if args.roll_career and not career_name:
        while career_name is None:
            career_name = CAREER_ROLL_D6[klass][dice.roll(1, 6) - 1]
        log(state, f"Rolled career: {career_name}")
    if not career_name:
        die("give --career or --roll-career (see class_options.py for the lists)")

    info = load_class(klass)
    career_path = find_career(career_name, klass)
    career = parse_career(career_path)
    if klass.lower() not in str(career_path).lower():
        print(f"note: career page lives outside the {klass} directory: {career['page']}")

    status = (args.status or career["status"] or "").capitalize()
    if status not in ("Brass", "Silver", "Gold"):
        die(f"career page {career['page']} has no usable Status; "
            f"pass --status brass|silver|gold (your judgement)")

    alignment = FORCED_ALIGNMENT.get(klass)
    if alignment and args.alignment and args.alignment.capitalize() != alignment:
        die(f"{klass} must be {alignment} (docs/Character/Alignment.md)")
    if not alignment:
        alignment = (args.alignment or "Neutral").capitalize()
        if alignment == "Neutrality":
            alignment = "Neutral"
        if alignment not in ALIGNMENTS:
            die(f"unknown alignment '{args.alignment}' (options: {', '.join(ALIGNMENTS)})")

    tough = state["abilities"]["Toughness"]["mod"]
    wounds_roll = dice.roll_expr(info["wounds_die"])
    wounds = max(max(wounds_roll, info["wounds_min"]) + tough, 1)
    stamina = dice.roll_expr(info["stamina_die"]) if info["stamina_die"] else 0
    money_bp, money_desc = roll_starting_money(status, dice)

    state.update({
        "class": klass, "class_page": info["page"],
        "career": career["name"], "career_page": career["page"],
        "career_combat_skills": career["combat_skills"],
        "career_skills": career["skills"],
        "career_trait": career["trait"],
        "status": status, "alignment": alignment,
        "wounds": wounds, "stamina": stamina,
        "saves": info["saves"], "ws": info["ws"], "bs": info["bs"],
        "skill_points": info["skill_points"],
        "money_bp": money_bp,
    })
    log(state, f"Class {klass} / {career['name']} (Status {status}, {alignment})")
    log(state, f"Wounds: {info['wounds_die']} = {wounds_roll} (min {info['wounds_min']}) "
               f"{tough:+d} Toughness -> {wounds}; Stamina {info['stamina_die']} = {stamina}")
    log(state, f"Saves: {info['saves']}; WS {info['ws']}, BS {info['bs']}"
               + (f"; Skill Points {info['skill_points']}" if info["skill_points"] else ""))
    log(state, f"Starting money — {money_desc} ({fmt_money(money_bp)})")
    if career["trait"]:
        print(f"\nCareer trait: {career['trait']}")
    if career["skills"]:
        print(f"Career skills: {career['skills']}")
    print("\nNext: roll_bio.py, roll_name.py, then buy equipment (buy.py).")
    save_state(args.file, state)


if __name__ == "__main__":
    main()
