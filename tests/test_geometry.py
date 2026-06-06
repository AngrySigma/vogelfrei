"""Tests for combat_sim.geometry — pure math, no state."""

from combat_sim.geometry import (
    FT_PER_SQUARE,
    chebyshev,
    sign,
    ideal_step,
    cardinal_alternatives,
)


def test_ft_per_square_is_five():
    """Convention: 1 square = 5 feet. Used by range-band math."""
    assert FT_PER_SQUARE == 5


class TestChebyshev:
    def test_same_square(self):
        assert chebyshev((3, 4), (3, 4)) == 0

    def test_orthogonal(self):
        assert chebyshev((0, 0), (3, 0)) == 3
        assert chebyshev((0, 0), (0, 5)) == 5

    def test_diagonal_costs_one(self):
        """The whole point of Chebyshev: 1 diagonal = 1 square."""
        assert chebyshev((0, 0), (3, 3)) == 3

    def test_mixed(self):
        # max(|dx|, |dy|) = max(2, 5) = 5
        assert chebyshev((1, 1), (3, 6)) == 5

    def test_symmetric(self):
        assert chebyshev((1, 2), (7, 9)) == chebyshev((7, 9), (1, 2))


class TestSign:
    def test_negative(self):
        assert sign(-5) == -1
        assert sign(-1) == -1

    def test_zero(self):
        assert sign(0) == 0

    def test_positive(self):
        assert sign(1) == 1
        assert sign(42) == 1


class TestIdealStep:
    def test_due_east(self):
        assert ideal_step((0, 0), (5, 0)) == (1, 0)

    def test_due_north(self):
        assert ideal_step((0, 0), (0, -3)) == (0, -1)

    def test_diagonal_ne(self):
        """Both axes need movement: take the diagonal."""
        assert ideal_step((0, 0), (5, 5)) == (1, 1)

    def test_diagonal_sw(self):
        assert ideal_step((10, 10), (3, 4)) == (9, 9)

    def test_already_there(self):
        """No step needed when from == to. Returns the same square."""
        assert ideal_step((4, 4), (4, 4)) == (4, 4)

    def test_adjacent(self):
        """Single step lands you on the target."""
        assert ideal_step((0, 0), (1, 1)) == (1, 1)


class TestCardinalAlternatives:
    def test_diagonal_has_two_cardinal_alts(self):
        """Going NE has two fallbacks: just-N or just-E."""
        alts = cardinal_alternatives((0, 0), (3, 3))
        assert set(alts) == {(1, 0), (0, 1)}

    def test_pure_cardinal_has_no_alts(self):
        """Going due east has no cardinal alternative — the only fallback
        would be a perpendicular step, which is not "toward" the target."""
        alts = cardinal_alternatives((0, 0), (5, 0))
        assert alts == []

    def test_due_west(self):
        alts = cardinal_alternatives((5, 5), (0, 5))
        assert alts == []
