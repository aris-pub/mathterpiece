from dataclasses import dataclass

type Row = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class Matrix:
    # A 3x3 matrix acting on homogeneous coordinates (x, y, 1), so translations are matrices too.
    rows: tuple[Row, Row, Row]

    def __post_init__(self):
        if len(self.rows) != 3 or any(len(row) != 3 for row in self.rows):
            raise ValueError("a transform matrix is 3x3")

    def __matmul__(self, other: "Matrix") -> "Matrix":
        def row(r: Row) -> Row:
            a, b, c = (sum(r[k] * other.rows[k][j] for k in range(3)) for j in range(3))
            return a, b, c

        r0, r1, r2 = self.rows
        return Matrix((row(r0), row(r1), row(r2)))

    def inverse(self) -> "Matrix":
        (a, b, c), (d, e, f), _ = self.rows
        det = a * e - b * d
        if det == 0:
            raise ValueError("this transform has no inverse")
        ia, ib, id_, ie = e / det, -b / det, -d / det, a / det
        return Matrix(((ia, ib, -(ia * c + ib * f)), (id_, ie, -(id_ * c + ie * f)), (0, 0, 1)))

    def apply(self, x: float, y: float) -> tuple[float, float]:
        (a, b, c), (d, e, f), _ = self.rows
        return a * x + b * y + c, d * x + e * y + f


IDENTITY = Matrix(((1, 0, 0), (0, 1, 0), (0, 0, 1)))


def compose(*matrices: Matrix) -> Matrix:
    result = IDENTITY
    for m in matrices:
        result = m @ result
    return result
