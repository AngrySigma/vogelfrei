"""CLI: ``python -m combat_sim [--scenario KEY] [--n 10000] [--seed 0]``.

With no flags, runs every registered scenario at N=10_000 and prints
description + aggregate stats for each.
"""

from __future__ import annotations
import argparse

from .scenarios import SCENARIOS, run_scenario


def main() -> int:
    ap = argparse.ArgumentParser(prog="combat_sim")
    ap.add_argument("--scenario", "-s",
                    help=f"Scenario key. Default: all. "
                         f"Available: {', '.join(SCENARIOS)}")
    ap.add_argument("--n", type=int, default=10_000,
                    help="Iterations per scenario (default 10000).")
    ap.add_argument("--seed", type=int, default=0,
                    help="Base seed; iteration i uses seed+i.")
    ap.add_argument("--list", action="store_true",
                    help="List scenarios and their descriptions, then exit.")
    args = ap.parse_args()

    if args.list:
        for key, sc in SCENARIOS.items():
            print(f"{key}: {sc.description}")
            print()
        return 0

    keys = [args.scenario] if args.scenario else list(SCENARIOS.keys())
    for k in keys:
        if k not in SCENARIOS:
            print(f"Unknown scenario: {k!r}. "
                  f"Known: {', '.join(SCENARIOS)}")
            return 2
        stats = run_scenario(k, n=args.n, seed=args.seed)
        print(stats.pretty())
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
