"""Regression: existing scenarios must reproduce the baseline numbers
captured before the battlefield work began.

Baseline taken at n=2000, seed=0. Without a battlefield, the engine
must behave exactly as it did before — these scenarios are the contract.

The positioned scenarios (S11/S12/C13) are NOT in this test; they were
introduced by this very change, so they have no pre-existing baseline.
"""

import pytest

from combat_sim.scenarios import run_scenario


BASELINE_N2000_SEED0 = {
    # key:    (a_wins, b_wins)
    "S1":   (983,  1017),
    "S1b":  (1293, 707),
    "S2":   (994,  1006),
    "S3":   (1509, 491),
    "S7":   (115,  1885),
    "S7b":  (706,  1294),
    "S9":   (1911, 89),
    "S9b":  (1998, 2),
    "C8":   (1632, 368),
    "C10":  (984,  1016),
    "C10s": (553,  1447),
}


@pytest.mark.parametrize("scenario_key,expected",
                        sorted(BASELINE_N2000_SEED0.items()))
def test_scenario_reproduces_baseline(scenario_key, expected):
    """At fixed seed, the number of wins per side must be exactly equal
    to the baseline. Any drift indicates that the no-battlefield code
    path changed behaviour — that's a regression."""
    stats = run_scenario(scenario_key, n=2000, seed=0)
    assert (stats.a_wins, stats.b_wins) == expected, (
        f"Drift in {scenario_key}: got ({stats.a_wins}, {stats.b_wins}), "
        f"expected {expected}"
    )
