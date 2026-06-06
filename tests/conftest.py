"""Shared fixtures for the combat_sim test suite.

Keep these tiny — most tests construct their own minimal inputs to keep
the failure trace short and obvious.
"""

import pytest

from combat_sim.dice import Dice


@pytest.fixture
def fixed_dice():
    """Reproducible dice. Use only when the test actually rolls dice."""
    return Dice(seed=42)


@pytest.fixture
def empty_battlefield():
    """A 10x10 open field with no terrain. Tests place creatures themselves."""
    from combat_sim.battlefield import Battlefield
    return Battlefield(width=10, height=10)
