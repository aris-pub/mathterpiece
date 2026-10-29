import pytest

from mathterpiece.matrix import IDENTITY, Matrix, compose


def shift(dx, dy):
    return Matrix(((1, 0, dx), (0, 1, dy), (0, 0, 1)))


SWAP = Matrix(((0, 1, 0), (1, 0, 0), (0, 0, 1)))


class TestMatrix:
    def test_identity_leaves_points_alone(self):
        assert IDENTITY.apply(3, 4) == (3, 4)

    def test_apply_uses_homogeneous_coordinates(self):
        assert shift(1, 2).apply(3, 4) == (4, 6)

    def test_matmul_applies_the_right_matrix_first(self):
        assert (SWAP @ shift(1, 0)).apply(0, 0) == (0, 1)
        assert (shift(1, 0) @ SWAP).apply(0, 0) == (1, 0)

    def test_frozen_and_comparable(self):
        assert shift(1, 2) == shift(1, 2)
        assert hash(shift(1, 2)) == hash(shift(1, 2))

    def test_must_be_three_by_three(self):
        with pytest.raises(ValueError):
            Matrix(((1, 0), (0, 1)))  # ty: ignore[invalid-argument-type]


class TestCompose:
    def test_left_to_right(self):
        assert compose(shift(1, 0), SWAP).apply(0, 0) == (0, 1)
        assert compose(SWAP, shift(1, 0)).apply(0, 0) == (1, 0)

    def test_no_arguments_is_identity(self):
        assert compose() == IDENTITY

    def test_one_argument(self):
        assert compose(SWAP) == SWAP


class TestInverse:
    def test_undoes_the_matrix(self):
        m = Matrix(((0, -2, 3), (2, 0, -1), (0, 0, 1)))
        assert m.inverse().apply(*m.apply(5, 7)) == pytest.approx((5, 7))

    def test_identity(self):
        assert IDENTITY.inverse() == IDENTITY

    def test_singular(self):
        with pytest.raises(ValueError, match="inverse"):
            Matrix(((0, 0, 1), (0, 0, 1), (0, 0, 1))).inverse()
