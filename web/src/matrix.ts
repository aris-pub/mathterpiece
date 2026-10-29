/** A 3x3 matrix acting on homogeneous coordinates (x, y, 1), stored as its top two rows. */
export class Matrix {
  constructor(
    readonly a: number,
    readonly b: number,
    readonly c: number,
    readonly d: number,
    readonly e: number,
    readonly f: number,
  ) {}

  /** From the JSON's six numbers a b c d e f (rows of the matrix). */
  static of(values: readonly number[]): Matrix {
    const [a = 1, b = 0, c = 0, d = 0, e = 1, f = 0] = values;
    return new Matrix(a, b, c, d, e, f);
  }

  /** this @ other: other applies first. */
  times(o: Matrix): Matrix {
    return new Matrix(
      this.a * o.a + this.b * o.d,
      this.a * o.b + this.b * o.e,
      this.a * o.c + this.b * o.f + this.c,
      this.d * o.a + this.e * o.d,
      this.d * o.b + this.e * o.e,
      this.d * o.c + this.e * o.f + this.f,
    );
  }

  apply(x: number, y: number): [number, number] {
    return [this.a * x + this.b * y + this.c, this.d * x + this.e * y + this.f];
  }

  inverse(): Matrix {
    const det = this.a * this.e - this.b * this.d;
    if (det === 0) throw new Error("this transform has no inverse");
    const ia = this.e / det;
    const ib = -this.b / det;
    const id = -this.d / det;
    const ie = this.a / det;
    return new Matrix(ia, ib, -(ia * this.c + ib * this.f), id, ie, -(id * this.c + ie * this.f));
  }

  /** How much it scales lengths; for a stretch that differs by direction, an average. */
  scale(): number {
    return Math.sqrt(Math.abs(this.a * this.e - this.b * this.d));
  }

  /** As an SVG transform attribute. */
  svg(): string {
    return `matrix(${this.a} ${this.d} ${this.b} ${this.e} ${this.c} ${this.f})`;
  }
}

export const IDENTITY = new Matrix(1, 0, 0, 0, 1, 0);

export function translate(dx: number, dy: number): Matrix {
  return new Matrix(1, 0, dx, 0, 1, dy);
}

/** Left to right: the first matrix applies first. */
export function compose(...matrices: Matrix[]): Matrix {
  return matrices.reduce((acc, m) => m.times(acc), IDENTITY);
}
