#!/usr/bin/env python3
"""Reassign one party slot: clear everything except the rolled abilities.

The party workflow says to reassign a slot and re-run it when an assignment
turns out wrong. `apply_class.py` refuses to touch a character that already
has a class and tells you to start over with `roll_stats.py --force` — but
that would reroll the dice, which is exactly what must NOT happen: the array
is the one thing the lead already committed to.

This keeps the ability scores (and the party slot label) and throws away
class, career, Status, alignment, money, inventory, notes, skills and the
derived combat block, so the slot can be built again from step 3.

The ability swap is released too: a swap spent by the discarded build was
spent on a class that is no longer there.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "character-generation" / "scripts"))

from vflib import die, load_state, new_state, save_state  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, required=True, help="the pcN.json to reset")
    ap.add_argument("--keep-swap", action="store_true",
                    help="leave swap_used set (only if the new build reuses the same swap)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    old = load_state(args.file)
    if not old.get("abilities"):
        die(f"{args.file} has no rolled abilities to keep — reroll it with roll_party.py")

    # An unswapped character still holds its original roll; a swapped one does
    # not, and there is no record of the pre-swap order, so say so plainly.
    if old.get("swap_used") and not args.keep_swap:
        print("note: this build spent the ability swap, so the scores below are the "
              "SWAPPED order, not the original roll. The swap is released for reuse, "
              "but re-applying the same swap would undo it — check the assignment.")

    fresh = new_state()
    fresh["abilities"] = old["abilities"]
    if old.get("party_slot"):
        fresh["party_slot"] = old["party_slot"]
    if args.keep_swap:
        fresh["swap_used"] = bool(old.get("swap_used"))
    roll = next((l for l in old.get("log", []) if l.startswith("Rolled 3d6")), None)
    fresh["log"].append(roll or "Abilities carried over from the previous build of this slot")
    fresh["log"].append(f"Slot reset for reassignment (was {old.get('class') or '?'}"
                        + (f" / {old['career']}" if old.get("career") else "") + ")")

    scores = ", ".join(f"{a} {v['score']} ({v['mod']:+d})"
                       for a, v in fresh["abilities"].items())
    print(f"kept: {scores}")
    print(f"dropped: class, career, Status, alignment, money, inventory, "
          f"{len(old.get('notes', []))} note(s), {len(old.get('skills', {}))} skill(s), combat block")
    print(f"swap_used: {fresh.get('swap_used', False)}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return
    save_state(args.file, fresh)
    sheet = args.file.with_suffix(".md")
    if sheet.exists():
        sheet.unlink()
        print(f"removed stale sheet {sheet}")
    print(f"\nreset {args.file} — rebuild it from step 3 (apply_class.py)")


if __name__ == "__main__":
    main()
