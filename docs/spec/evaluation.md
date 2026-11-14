(evaluation)=
# Evaluation

This part defines how an expression is computed: the order in which its parts are evaluated, the
forms that evaluate only some of their parts, the operations that are {term}`undefined` and
where, how `none` propagates, the numbers and their limits, random values, equality, and whether a
computation ends.

An expression is computed at one of two times ({doc}`binding-time`). When every value that it
reads is known when compiling, the compiler computes it and writes the value into the .mtpc in
place of the expression. This is {term}`folding`. Otherwise the runtime computes it while drawing,
again each time a value that it reads changes ({doc}`reaction`). Every rule in this part applies at
both times, unless the rule is stated for one of them. Where the current compiler and runtime do
something else, or disagree with each other or with the guides, this part describes what the code
does, and an open question follows.

## Expressions change nothing

```{rule} evaluation-is-pure
{term}`Evaluation <evaluation>` of an expression gives a value and changes nothing: no variable,
no attribute, no seed and no page element. The value depends only on the values that the
expression reads: variables, attributes, parameters, `let` names, the {term}`seeds <seed>` of its
random functions, and, for a read of a position, the frame of the expression that reads it
({doc}`world-model`).
```

Only writers change values, and no expression is a writer ({doc}`reaction`).

## Evaluation order

```{rule} arguments-before-call
A call of a function, a built-in function or an operator evaluates every argument, then computes
its result from their values. The forms of {numref}`forms-evaluate-some-parts` are the only
exceptions.
```

By {numref}`evaluation-is-pure`, and since every argument is evaluated, the order in which the
arguments of one call are evaluated changes neither the value nor whether the computation ends
({ref}`termination`). The runtime
evaluates arguments from left to right (web/src/runtime.ts, `compileBuiltin` and the case `call`
of `compile`).

```{rule} forms-evaluate-some-parts
These forms evaluate only some of their parts:

| Form | Evaluates |
|---|---|
| `(if c a b)` | `c`, then `a` when `c` is true, or `b` when it is false |
| `(when c x)` | the same as `(if c x none)` |
| `(cond (c1 v1) (c2 v2) … (else v))` | the tests in order, up to the first that is true, then the value of that clause only. When no test is true, `v` only |
| `(and a b …)` | the parts from left to right, up to the first that is false. The value is false when a part is false, and true otherwise |
| `(or a b …)` | the parts from left to right, up to the first that is true. The value is true when a part is true, and false otherwise |
| `(or? x d)` | `x`, then `d` only when `x` is `none` |
| `(let ((n1 v1) (n2 v2) …) body)` | each value that the body or a later value reads, once, in order, then the body. A value that nothing reads is not evaluated. A value that is read is evaluated before the body, even when the branch of the body that reads it is not taken |
| `(fn params body)` | nothing, until the function is called |
```

The compiler leaves out every `let` value that nothing reads (mathterpiece/compiler.py, line 6693),
and the runtime evaluates the rest before the body (web/src/runtime.ts, line 1060). So in
`(let ((s (walk k))) (if c s 0))`, `walk` is called while drawing whether `c` is true or not.

The collection functions call their function on the items in order. While drawing, `any` and
`all` with a function stop at the first item at which the result is known (`Array.some` and
`Array.every` in web/src/runtime.ts, `compileCollection`). When folding, the compiler calls the
function on every item first (mathterpiece/compiler.py, line 2794). By
{numref}`evaluation-is-pure` the two give the same value, and they differ only in whether a call
that never ends is reached.

### Parts of these forms when compiling

```{rule} known-condition-takes-one-branch
When the condition of an `if` is known when compiling, the compiler compiles only the branch that
is taken. The other branch is neither type-checked nor folded.
```

So a folded call ends at its base case, and a `foreach` copy can start a chain, as in
`(if (= k 0) 1 (* 2 (. (name $'d-{(- k 1)}') x)))`. In copy 0, the untaken branch refers to
`d--1`, which does not exist (docs/reference.md, line 619).

The other forms of {numref}`forms-evaluate-some-parts` are compiled whole. `cond`, `and`, `or`,
`or?` and `let` compile every part, also a part that the form would not evaluate because a test or
a value before it is known when compiling (mathterpiece/compiler.py, lines 6519 to 6531 and 6608 to
6662). There is one exception: while a call is folded, `cond` stops at the first test that is known
to be true, as `if` does (line 6614). An undefined operation with known inputs in a part that would
not be evaluated is then still a compile error ({numref}`undefined-known-is-error`):

```mtp
(real x 0 (const))
(real a (if (= x 0) 0 (/ 1 x)))              ; compiles, and a is 0
(real b (cond ((= x 0) 0) (else (/ 1 x))))   ; division by zero, at (/ 1 x)
(bool c (and (> x 0) (> (/ 1 x) 2)))         ; division by zero, at (/ 1 x)
(real d (let ((u (/ 1 x))) 0))               ; division by zero, at (/ 1 x)
(real e (if (= x 0) 0 'not a number'))       ; compiles: the string is never checked
```

:::{admonition} Open question Q-evaluation-1
:class: warning
When compiling, the parts that a form would not evaluate are treated in two ways. The untaken
branch of an `if` is not compiled at all, so `(real e (if (= x 0) 0 'not a number'))` compiles
although the branch has the wrong type. `cond`, `and`, `or`, `or?` and `let` compile every part,
so `(cond ((= x 0) 0) (else (/ 1 x)))` is a compile error although `(/ 1 x)` is never evaluated,
while the same choice written with `if` compiles. In docs/reference.md, lines 619 to 624, `cond`,
`and` and `or` evaluate only some of their parts, and the rule for a known condition is given for
`if` only. The options:

- (a) Every form compiles only the parts that it would evaluate, as `if` does. The `cond`, `and`
  and `or` cases above compile. An untaken part may hold a type error that is never reported.
- (b) Every form type-checks every part, and an undefined operation with known inputs is an error
  only in a part that is evaluated. Type errors are always reported. The untaken branch of an `if`
  then needs a check that neither folds nor reports an undefined value, and a `foreach` chain such
  as the one above, whose untaken branch names a shape that does not exist, still has to compile.
- (c) Every form compiles every part, `if` too. This is the simplest rule, but it breaks the
  `foreach` chains and the base cases of folded recursive calls, which compile with `if` today.
:::

## Undefined values

```{rule} undefined-operations
An operation is {term}`undefined` at these inputs, and at no others:

| Operation | Undefined at |
|---|---|
| `+`, `-`, `*` | a result beyond the largest real, about 1.8 × 10³⁰⁸ |
| `/` | a divisor of 0 |
| `mod` | a divisor of 0 |
| `^` | 0 to a negative power, a negative base to a power that is not an int, and a result beyond the largest real |
| `sqrt` | an input below 0 |
| `exp` | a result beyond the largest real |
| `log` | an input of 0 or below, and a base of 0 or below or of 1 |
| `min`, `max` | no items at all |
| `tand`, `secd` | 90 + 180k degrees, for every int k |
| `cscd`, `cotd` | 180k degrees, for every int k |
| `tan`, `sec`, `csc`, `cot` | an input where the result is not a finite number. No real is exactly π/2, so this is only `csc` and `cot` at exactly 0 |
| `asin`, `acos`, `asind`, `acosd` | an input below -1 or above 1 |
| `asec`, `acsc`, `asecd`, `acscd` | an input strictly between -1 and 1 |
| `to-polar` | the point `[0 0]` |
| `pick` | an empty list |
| `range` | a gap of 0, a negative count `num`, and more than 1,000,000 items |
| `xs[i]` | a position outside -n to n - 1, on a list of n items |
| `g[k]` | a member that the group does not have |
| a bound value with a constraint | a value that breaks the constraint ({doc}`types`) |

Every other built-in function and operator is undefined nowhere.
```

The functions of the standard library are written in mtp, and are undefined where the built-ins
that they call are ({doc}`stdlib`).

```{rule} undefined-gives-none
While drawing, an undefined operation gives `none`. It never stops the figure, and never gives an
infinity or a value that is not a number.
```

```{rule} undefined-known-is-error
When compiling, an operation that is undefined at inputs known when compiling is a compile error,
at the operation. The inputs may be written by the illustrator, read from `const` variables, or be
the index of a `foreach` copy.
```

So `(sqrt -1)` and `(or? (sqrt -1) 0)` are compile errors, and so is
`(scene s (foreach i 3 (circle_ (r (/ 1 i)))))`, at copy 0.

```{rule} undefined-in-folded-call
A call of a function whose arguments are all known when compiling is folded: the compiler computes
the body with those arguments. Inside the body, an undefined operation gives `none`, as while
drawing. It is a compile error only when its `none` reaches a place in the body that does not take
`none`, or makes a function whose declared result type does not include `none` give `none`.
```

The illustrator wrote the body with parameters, not with known inputs, so an `or?` in the body can
replace the `none` with a default (docs/type-system.md, section 5.c, and mathterpiece/compiler.py,
`known_or_none`, line 2217). With `(func[real] f ((real t)) (let ((b (or? (sqrt t) 0))) (if (> t
0) b 1)))`, `(f -1)` is 1. With `(func f ((real x)) (/ 1 x))`, `(f 0)` is `none`, and with
`(func[real] f ((real x)) (/ 1 x))`, `(f 0)` is a compile error.

The compiler works out which expressions may be undefined from the ranges of their inputs, and
gives each such expression a type that includes `none` ({doc}`types`). The example below is live:
at 90° the secant is undefined, and the readout holds its default text.

```{mtp-example}
; sec θ is undefined at 90°, and there the readout holds its default text
(real theta 60 (>= 0) (<= 180))
(slider turn (move theta (from 0) (to 180)) (label 'θ'))
(readout r (or? $'sec θ = {(secd theta):.3f}' 'sec θ is undefined at 90°'))
```

## How none propagates

```{rule} none-propagates
An operation that receives `none` as an argument gives `none`, at both times, with these
exceptions:

- `or?`, `none?`, `some?` and `somes`, which give a value that is not `none` for an argument that
  is `none` ({doc}`stdlib`).
- `=` and `!=`, by {numref}`equality-with-none`.
- A call of a function whose parameter is declared `T|none`: the body is evaluated with `none` as
  the parameter. A parameter whose type does not include `none` makes the call `none`, and the body
  is not evaluated.
- A list built from expressions, which holds `none` as an item. A point is the exception: a point
  with a coordinate that is `none` is `none`.
- `if`, `cond` and `when`, whose value is `none` only when the branch taken is `none`.
- `map`, `reverse` and a read of a position of a list, which pass items that are `none` through.

A part of `none` is `none`: when `g[k]` is `none`, so is `g[k].pos`. An interpolated string with a
part that is `none` is `none`. A collection function given `none` in place of its collection gives
`none`.
```

```{rule} none-never-a-condition
The condition of an `if`, a `cond`, an `and` or an `or`, and the `when` of a component, never
receive `none`. Neither do the items given to `sum`, `count`, `min`, `max`, `any`, `all` and
`reduce`. A form that might give them `none` is a compile error ({doc}`types`).
```

Where `none` must stop, and the forms that stop it, are defined in {doc}`types`. A shape declared
`T|none` is not drawn while it is `none`. `none` as a `fill` or a `stroke` means no fill or no
stroke. In every other place that reaches the reader, `none` is replaced with a default by `or?`,
or left out of a list by `somes`.

When compiling, a value known to be `none` propagates by the same rule: an operation with such an
argument is known to give `none` (mathterpiece/compiler.py, `apply_builtin`, line 2204).

## Numbers

There are four types of number ({doc}`types`). Each is held this way at each time:

| Type | When compiling | While drawing |
|---|---|---|
| `int` | an exact whole number, of any size | an IEEE 754 binary64 number, exact up to 2⁵³ |
| `ratio` | an exact fraction | a binary64 number, the quotient of the fraction |
| `real` | a binary64 number | a binary64 number |
| `complex` | two binary64 numbers | two binary64 numbers |

In the .mtpc, a ratio is written as its numerator and denominator in lowest terms
({doc}`compiled-format`), and the runtime divides them when it loads the .mtpc
(web/src/runtime.ts, line 934).

```{rule} number-result-types
An arithmetic operation gives the broadest type of its inputs, in the order `int`, `ratio`,
`real`, `complex`, with these exceptions:

- `/` of an int by an int gives a ratio.
- `^` of an int to an int power gives an int when the power is at least 0, and a ratio when it may
  be negative. With a complex input it gives a complex, and otherwise a real.
- `abs` of a complex gives a real.

When the inputs of an operation include a ratio and a real, the ratio is converted to a real
first.
```

:::{admonition} Open question Q-evaluation-2
:class: warning
Ratios and ints are exact when compiling and not exact while drawing. The compiler computes ratios
with Python's `Fraction` and ints with Python's ints of any size (mathterpiece/compiler.py, `_fold`,
line 7913). The runtime computes both as binary64 numbers (web/src/runtime.ts, line 934, and
web/src/builtins.ts). So the same expression gives two values:

- With `(int m 1 (const))`, `(= (+ (/ m 10) 1/5) 3/10)` is folded to true. With `(int n 1)`, which
  a slider writes, `(= (+ (/ n 10) 1/5) 3/10)` is false while drawing, since 0.1 + 0.2 is
  0.30000000000000004 in binary64.
- `(+ (^ 2 60) 1)` is folded to 1152921504606846977, and the runtime reads that value from the
  .mtpc as 1152921504606846976. With n = 1, `(^ (* 3 n) 40)` while drawing is
  12157665459056929000, and the exact value is 12157665459056928801.

In docs/type-system.md, section 2, ratios are "exact fractions such as `1/3`", at both times. The
options:

- (a) The runtime computes ratios exactly, as pairs of whole numbers, and ints exactly beyond 2⁵³.
  Both times agree. Arithmetic while drawing is slower, and the numbers of a ratio can grow without
  bound.
- (b) A ratio is exact only when compiling, by a rule of the spec. Equality of ratios then depends
  on the time.
- (c) The compiler folds ratios and ints in binary64 too, as the runtime computes them. Both times
  agree, and no number is exact beyond binary64.

In the live example below, the comparison is computed while drawing, and at n = 1 the readout
holds False.
:::

```{mtp-example}
; at n = 1 the sum is 3/10, but the comparison is made in binary64 while drawing
(int n 1 (>= 0) (<= 10))
(slider pick (move n (from 0) (to 10)) (label 'n'))
(readout r $'n/10 + 1/5 = 3/10 is {(= (+ (/ n 10) 1/5) 3/10)}')
```

### The limit of every number

```{rule} number-limit
Every number lies within ±10¹⁵⁰, the {term}`number limit`:

- A literal beyond it is a compile error.
- A write of a number beyond it is clamped to it.
- For the ranges that the compiler proves, a value with no limit of its own lies within it.

A computed result may go beyond the number limit. A result beyond the largest real, about 1.8 ×
10³⁰⁸, is an overflow, and is undefined ({numref}`undefined-operations`).
```

With these limits, `(* 2 k)` or `(* 360 t)` can never overflow, while a product of several values
with no limit of their own may (docs/type-system.md, section 5.c).

:::{admonition} Open question Q-evaluation-3
:class: warning
{numref}`number-limit` is not kept everywhere:

- **A starting value known when compiling is not checked.** `(real k free@(* 1e100 1e100))` starts
  at 10²⁰⁰. The compiler checks only literals against the limit (`_Compiler.literal`,
  mathterpiece/compiler.py, line 5882), and the runtime clamps only writes (`constrain`,
  web/src/runtime.ts, line 761). The compiler then proves `(real m (* k k))` safe, since by the
  number limit `k` lies within ±10¹⁵⁰, and while drawing `m` is `none` although its type does not
  include `none`.
- **A point or a list written whole is not clamped.** `constrain` clamps a write only when the
  value is a single number. After a write of a point variable, of a line's `from`, or of a list,
  its items may lie beyond the limit.
- **`sum` while drawing does not give `none` on an overflow.** It adds with the built-in `+`
  (web/src/runtime.ts, line 1248), whose `Undefined` error is not caught there, so the error stops
  the evaluation. Within the number limit a sum overflows only with more than about 10¹⁵⁸ items, so
  this is reached only through the first point.

The options for the first two points: (a) check a starting value known when compiling against the
limit, as a literal is, and clamp the items of a point or a list on a write. (b) Treat the limit as
a rule for literals and single numbers only, and make the compiler prove ranges without assuming
it. The third point is a bug in either case.
:::

### Infinity

```{rule} infinity-only-when-compiling
`infty`, also written `∞`, is above every number, and `(- infty)` is below every number. Both lie
beyond the number limit, and both are values known when compiling only:

- When compiling, arithmetic carries them: `(+ infty 1)` is `infty` and `(/ 1 infty)` is 0.
  `(- infty infty)`, `(* 0 infty)` and `(/ infty infty)` are undefined.
- A variable that may hold one is `const`, and an attribute of a shape never holds one.
- While drawing, a result that is infinite is undefined, so it gives `none`, as an overflow does.
```

:::{admonition} Open question Q-evaluation-4
:class: warning
An infinity known when compiling can be an input of an expression that is computed while drawing.
In the .mtpc it is written as `"infty"` ({doc}`compiled-format`), and the runtime reads it as an
infinite binary64 number (web/src/runtime.ts, line 932). With `(real big infty (const))` and a free `(real y
1)`:

- `(< y big)` is true and `(min y big)` is 1, while drawing.
- `(+ y big)` is `none` while drawing, since its result is infinite. With `y` known when compiling,
  the same expression is folded to `infty`.

In docs/type-system.md, section 5.c, infinities "appear only in values known when compiling". It
is not stated whether such a value may be an input of an expression computed while drawing. The
options:

- (a) An expression computed while drawing never reads an infinity: reading a `const` that holds one
  outside an expression that is folded is a compile error.
- (b) It may read one, and a result that is infinite is `none`, as today. Then the same expression
  gives `infty` when folded and `none` while drawing, against {numref}`same-value-at-both-times`.
- (c) The runtime carries infinities as the compiler does, and gives `none` only where the result
  would reach a place that needs a finite number, such as an attribute of a shape.
:::

### Rounding

```{rule} rounding
Wherever a number is rounded, halves round away from zero, on the number's shortest exact decimal
form, not on its binary value: 2.5 gives 3, -2.5 gives -3, 0.125 to two decimal places gives 0.13,
and 2.675 to two decimal places gives 2.68. The rule applies to `round`, to a write into an int,
and to the format spec of an interpolated string, such as `{x:.2f}`.
```

```{rule} write-into-int
While drawing, a number written into an int is rounded by {numref}`rounding`, after it is clamped
to the int's range, so that it lands on the nearest int inside the range ({doc}`types`).
```

The runtime rounds the value once before the constraints and once after them, so that an int that
wraps is never rounded up out of its interval (web/src/runtime.ts, lines 763 and 771). The
compiler rounds with Python's `Decimal` (mathterpiece/compiler.py, `_round`, line 6877), and the
runtime with `roundHalfAway` (web/src/builtins.ts, line 181). On 1,031 values from -8 to 8, and on
156 pairs of a value and a format spec, the two agree.

:::{admonition} Open question Q-evaluation-5
:class: warning
Two places round in another way, or fail:

- **`round` of a known value of 10²⁸ or more stops the compiler.** `_round` quantizes a `Decimal`
  in the default context, whose precision is 28 digits, so `(int r (round 1e28))` raises
  `decimal.InvalidOperation`, which is not a compile error and has no position. While drawing the
  same value rounds to itself. In docs/reference.md, line 653, `round` is never undefined.
- **Mixing colors rounds each channel differently at the two times.** The compiler rounds halves to
  even (Python's `round`, mathterpiece/colors.py, line 237), and the runtime rounds halves up
  (`Math.round`, web/src/builtins.ts, line 287). So `(mix '#000000' '#050505' 0.5)` is `#020202ff`
  when folded and `#030303ff` while drawing, and `=` on the two is false. {numref}`rounding` does
  not name the channels of a color.

The options for colors: (a) the channels of a mixed color follow {numref}`rounding`, at both
times. (b) The channels round halves up, as CSS `color-mix()` does in browsers, at both times. (c)
Colors are not rounded until they are drawn, so the channels of a mixed color may be fractions. The first point
is a bug with one fix: the compiler rounds as the runtime does.
:::

## Randomness

```{rule} seed-variable
Every random value is computed from a {term}`seed`: a free variable of the built-in type
`rand-seed`, an int of at least 0. A random function follows the seed named in it with `(seed s)`,
or, without one, the only seed that the file declares or imports. In a file with several seeds,
every random function is written with `(seed s)`. A `const` variable is not a seed.
```

```{rule} random-site
Each place in the source where `rand`, `rand-int`, `pick` or `shuffle` is written has a
{term}`site`: a whole number, counted from 0 in the order in which the compiler compiles them,
after the copies of each `foreach` and the members of each motif instance are written out. Each
copy and each instance therefore has sites of its own. The site is written in the expression in
the .mtpc ({doc}`compiled-format`).
```

```{rule} random-hash
The hash h of whole numbers x₁, …, xₙ is a 32-bit word, computed with every product taken modulo
2³², every xor and shift on 32-bit words, and `>>` the shift that fills with zeros:

    h = 0x811c9dc5
    for each x, in order:
        h = (h xor (x mod 2³²)) × 0x01000193
        h = h xor (h >> 15)
        h = h × 0x2c1b3c6d
        h = h xor (h >> 12)
        h = h × 0x297a2d39
        h = h xor (h >> 15)

For a seed value s, a site p and a whole number k, u(s, p, k) = h(s, p, k) / 2³², a number from 0
up to 1, never 1.
```

```{rule} random-values
With s the value of the seed and p the site:

- `(rand)` is u(s, p, 0), and `(rand lo hi)` is lo + u(s, p, 0) × (hi - lo): a real from `lo` up
  to `hi`, never `hi`.
- `(rand-int lo hi)` is lo + ⌊u(s, p, 0) × (hi - lo + 1)⌋: an int from `lo` to `hi`, both included.
- `(pick xs)` on a list of n items is the item at position ⌊u(s, p, 0) × n⌋, and `none` when the
  list is empty.
- `(shuffle xs)` is the items of `xs` in a new order: for i from n - 1 down to 1, the items at
  positions i and ⌊u(s, p, i) × (i + 1)⌋ are swapped.
- `(next-seed s)` is h(s, 0x9e3779b9).
```

These are the functions `unit`, `shuffle` and `nextSeed` of web/src/random.ts, and the case
`rand` of `compile` in web/src/runtime.ts, line 1069.

```{rule} random-same-on-refresh
A random value is computed while drawing, and is never folded. For one .mtpc, the same values of
the seeds give the same random values, on every refresh and in every browser.
```

A random value is therefore known only while drawing ({doc}`binding-time`). Since the sites are
counted when compiling, a change to the source that adds or removes a random function before
another one changes the site of the later one, and with it the value that the later one draws.

```{rule} rolling-the-dice
A roll is a write of `(next-seed s)` into the seed `s`. It changes the random values that follow
`s`, and no others. `(roll-dice s)` stands for `(move s (to (next-seed s)) (duration 0))`
({doc}`time`).
```

`rand`, `rand-int`, `pick` and `shuffle` inside the body of a function are a compile error for now
(mathterpiece/compiler.py, line 2247). A free variable may start at a random value with `free@`,
and then never follows the seed (docs/reference.md, line 106).

```{mtp-example}
; every dot is drawn from the seed dots and the site of its rand
(rand-seed dots 7)
(scene s
  (foreach i 12
    (circle_ (pos [(rand 0 10) (rand 0 4)]) (r 0.2) (fill 'teal'))))
(canvas v (x 0) (y 0) (width 10) (height 4) s)
(button roll (animation (roll-dice dots)) (label 'Roll'))
```

:::{admonition} Open question Q-evaluation-6
:class: warning
Four points about random values are not settled:

- **`lo` above `hi`.** Neither `rand` nor `rand-int` checks that `lo` is at most `hi`. With `(rand-int
  10 3)`, {numref}`random-values` gives an int from 4 to 10, not from 3 to 10. The compiler gives
  the result the range from `lo` to `hi` (mathterpiece/compiler.py, lines 2262 and 2273), here
  from 10 to 3, so it accepts `((int (>= 3) (<= 5)) b (rand-int 5 3))`. The options: (a) `lo` above
  `hi` is undefined, (b) the two are swapped, (c) the compiler proves that `lo` is at most `hi`.
- **Only the seed modulo 2³² counts.** The hash uses x mod 2³² (`x >>> 0`, web/src/random.ts,
  line 9), so the seeds 0 and 2³² draw the same values, and so do 0 and 10¹⁵⁰. The options: (a) a
  rule of the spec states this, (b) `rand-seed` is narrowed to ints below 2³².
- **When the number is drawn.** In docs/data-model.md, line 283, the number of `rand` "is drawn
  once, when the page loads". In docs/reference.md, line 101, "a new seed draws every value that
  follows it again". The runtime does the second. One of the two guides needs a fix.
- **A `const` seed.** `(rand-seed s 3 (const))` is not counted as a seed, and the error message for
  a `rand` that follows it is "a random value follows a seed: import the standard one, (import
  rand), or declare one, (rand-seed dots 0)", although one is declared.
:::

## Equality

`=` and `!=` take any two values of one type, and `!=` gives the opposite of `=`. When both sides
are known when compiling, the compiler folds `=` with Python's `==` on the values
(mathterpiece/compiler.py, `_fold`, line 7913). While drawing, the runtime compares them with
`equal` (web/src/builtins.ts, line 156).

```{rule} equality-of-one-type
`(= a b)` and `(!= a b)` are a compile error unless the type of one side fits the type of the
other, or one side is `none`. A list of two numbers is not converted to a point for them: `(= p
xs)`, with `p` a point and `xs` a list of ints, is a compile error. A literal list on one side is
given the type of the other side, so `(= p [1 2])` compiles.
```

```{rule} equality-with-none
`(= none none)` is true, and `(= none x)` is false for every `x` that is not `none`. `=` and `!=`
never give `none`.
```

The spec does not yet define what `=` means for each type (Q-evaluation-7). The code does this
today:

| Type | `(= a b)` is true when |
|---|---|
| `int`, `ratio`, `real` | the two are the same number, exactly: 0 and -0 are equal, an int and a real of the same value are equal. When compiling, ratios are compared exactly, and while drawing as binary64 numbers (Q-evaluation-2). `(= (sind 30) 0.5)` is false, since `(sind 30)` is 0.49999999999999994 |
| `complex` | both parts are equal. A complex whose second part is 0 equals the real of its first part |
| `bool`, `string`, a choice | the two are exactly the same |
| `point`, `list[T]`, `transform` | they have the same length, and the items at each position are equal |
| `color` | they are the same color once parsed: `(= ink '#000080')` is true with `(color ink 'navy')`. A light-dark color equals another when both of its modes do, and a color with the same value in both modes is one color (docs/reference.md, lines 737 and 738). A token is compared by its value in the live model, never by a value that the page's CSS gives it |
| `font` | every part is the same |
| a shape, a group, a namespace, a formula, a term and every other mutable object | the two are the same object. Two circles with the same attributes are not equal |
| `transition`, `animation` | the two are the same declaration. Two transitions declared with the same arguments are not equal |
| a function | never, while drawing. `(= f f)` is false, and so is `(= sind sind)`. The runtime makes a new JavaScript function for each read of a function (web/src/runtime.ts, `functionValue` and `builtinValue`), and `equal` compares functions with `===`. The compiler never folds `=` on functions |

### Matching

A separate, tolerant comparison is used where the runtime checks whether the scene is in a state.

```{rule} matching
Two values {term}`match` when they are equal, with one difference: two reals match when they
differ by at most 10⁻¹² or by at most a millionth of the larger of their sizes. Points and lists
match when they have the same length and the items at each position match. Bools, strings, choices
and colors match only when they are exactly the same, and `none` matches only `none`.
```

Matching is `same` in web/src/same.ts. The runtime uses it to read the step of a play or a stepper
from the scene (docs/reference.md, line 572, and web/src/player.ts, line 302), and to check
whether the free values that a canvas's `on-view` moves still have their values from page load
(web/src/lifecycle.ts, line 62). Two complex numbers, two objects and two functions match only when
they are the same JavaScript value.

While drawing, the runtime also uses `=` to skip writes: a write of a value equal to the current
one is skipped, and nothing that depends on it is computed again (web/src/runtime.ts, line 728).

:::{admonition} Open question Q-evaluation-7
:class: warning
Equality is not defined for each type, and two notions of it exist: exact `=`, and matching. The
table above describes the code. The guides define equality only for `none` (docs/reference.md,
line 642), for light-dark colors (lines 737 and 738) and for matching (line 572). The questions and
their options:

- **Functions.** Today `(= f f)` is false while drawing. (a) A function equals itself: two
  functions are equal when they come from the same declaration, or the same `fn` with the same
  values around it. The runtime then compares functions by declaration and captured values. (b)
  `=` on functions is a compile error. (c) As today, which makes `=` on functions useless.
- **Transitions, animations and other objects.** (a) The same object, as today. (b) The same
  arguments, as for values. With (a), two transitions with the same arguments are not equal. With
  (b), a transition equals every transition with the same trajectory. In docs/type-system.md,
  section 2, transitions and animations are listed among the values, which never change, and not
  among the mutable objects.
- **Reals.** (a) Exact, as today, which makes `(= (sind 30) 0.5)` false, and makes the result depend
  on the time (Q-evaluation-2, Q-evaluation-9). (b) `=` matches, as plays do. Then `=` is not
  transitive: a may match b, and b match c, while a does not match c. (c) Exact `=`, and a separate
  built-in function for matching, for the illustrator to choose.
- **Which notion the runtime uses.** Skipping a write uses `=`, and reading the step of a play
  uses matching. It is open whether every comparison that the runtime makes for itself should use
  one notion.
:::

(termination)=
## Termination

A function may call itself, directly, through other functions, or through a function value
(docs/reference.md, line 124). Nothing in the language requires that a call ends. There are no
other loops: a `foreach` makes a number of copies known when compiling, and `range` gives at most
1,000,000 items. So a computation that does not end is a chain of calls that does not end.

What the code does today:

- **When compiling.** A call with known arguments is folded by compiling its body again with those
  arguments. When the nesting is too deep for Python, the compiler catches the `RecursionError` and
  leaves the call to the runtime (mathterpiece/compiler.py, `fold_call`, line 2530). Working out the
  range of a call does the same (line 2013). A call that never ends therefore compiles. With a
  simple function that counts down, `(func[int] down ((int m)) (if (<= m 0) 0 (+ 1 (down (- m
  1)))))`, `(down 80)` is folded and `(down 81)` is not. Folded calls are kept by their arguments,
  so a call with the same arguments is folded once.
- **While drawing.** There is no limit on the depth of calls or on the time that a computation
  takes (web/src/runtime.ts, `call`, line 1282). Each call uses the JavaScript call stack. With the
  function above, `(down n)` gives a value up to n = 1740 or so in Node 26, and the limit depends on
  the browser. Deeper, and for a call that never ends, JavaScript throws `RangeError: Maximum call
  stack size exceeded`. The runtime does not turn it into `none`. The error stops the evaluation, and
  the message of the error is drawn in place of the view or the control that was being drawn
  (web/src/elements.ts, `guard`, line 324). A computation that ends but takes a long time freezes
  the page.

:::{admonition} Open question Q-evaluation-8
:class: warning
Termination is not guaranteed, and the spec does not define what happens when a computation does
not end. Two consequences of the code today: a call such as `(down 100)`, whose arguments are all
known, is computed while drawing, since the compiler stops folding at a depth of about 80, so
whether an expression is folded depends on the depth of its calls. And the same figure may work in
one browser and fail in another, whose stack is smaller. The options:

- (a) Keep recursion unlimited, and define a computation that does not end, or that is too deep
  for the runtime, as an error of the figure, with its message drawn in place of the component.
  Simple, but a figure may fail for some values of a slider only.
- (b) Give both times one depth limit, such as 10,000 nested calls, past which a call is undefined
  and gives `none`. Every recursive call then has a type that includes `none`, and the compiler folds
  up to the same depth as the runtime. Calls that run for long but are not deep still never end.
- (c) Allow only recursion that the compiler proves to end, such as a call whose int argument
  decreases by at least 1 at each step and stops at a bound. Every figure then ends, and some
  recursive functions that end are rejected.
- (d) Make a recursive call with known arguments that the compiler cannot fold a compile error.
  The compiler then finds some calls that never end, but not those whose arguments are known only
  while drawing.
:::

(folding-and-drawing)=
## Folding and drawing compared

```{rule} same-value-at-both-times
An expression gives the same value when it is folded as when it is computed while drawing, for the
same values of what it reads.
```

This rule is the intent of the guides and the code: docs/reference.md, line 613, has "One rule, the
same in the compiler and the runtime", and the comment at line 1 of web/src/builtins.ts has "as the
compiler folds them". The compiler computes
with CPython and its `math` module, and the runtime with JavaScript and its `Math` object, and the
two differ in these places:

| Where | When compiling | While drawing | Open question |
|---|---|---|---|
| ratios | exact | binary64 | Q-evaluation-2 |
| ints beyond 2⁵³ | exact | binary64 | Q-evaluation-2 |
| `round` of 10²⁸ or more | the compiler stops | rounds | Q-evaluation-5 |
| the channels of a mixed color | halves to even | halves up | Q-evaluation-5 |
| an infinite input | carried, `(+ y infty)` is `infty` | `none` | Q-evaluation-4 |
| recursion | folded up to a depth of about 80 | computed up to the stack of the browser | Q-evaluation-8 |
| `sin`, `cos`, `exp`, `log`, `atan`, `asin`, `acos`, `dist` and the rest | CPython's `math` | JavaScript's `Math` | Q-evaluation-9 |
| degrees to radians, and back | `x × (π/180)` | `(x × π) / 180` | Q-evaluation-9 |
| `mod` of reals | Python's `%`, which is exact | `a - b × ⌊a / b⌋` | Q-evaluation-9 |

Formatting with a format spec, `round`, and `sqrt` agreed on every value tried.

:::{admonition} Open question Q-evaluation-9
:class: warning
The elementary functions, the conversion between degrees and radians, and `mod` of reals give
different binary64 results at the two times. On the same inputs, computed with
mathterpiece/builtins.py and with web/src/builtins.ts:

- `sind` differs on 776 of 2,885 angles from -360 to 360 degrees, a quarter of a degree apart. The
  difference is in the last bits, as for -359.75, where it is 0.004363309284746544 when folded and
  0.004363309284747432 while drawing. `cosd`, `tand`, `secd`, `cscd`, `cotd`
  and `to-rad` differ on 692 to 1,265 of the same angles. Part of the difference comes from the
  conversion: Python's `math.radians` multiplies by π/180, and the runtime computes `(x × π) / 180`
  (web/src/builtins.ts, line 52).
- `sin`, `cos`, `tan`, `exp`, `log`, `atan`, `asin`, `acos` and `dist` differ in the last bit on
  1 to 41 percent of 1,031 values from -8 to 8.
- `mod` of reals: `(mod 5.5 0.1)` is 0.0999999999999997 when folded and 0 while drawing. Python's
  `%` is exact, and the runtime computes `a - b × ⌊a / b⌋` (web/src/builtins.ts, line 46).
- For large angles the two differ by more than the last bits: `(cosd (+ 1e15 90))` is
  0.9847837611566258 when folded and 0.9851213048563215 while drawing.

Both times give exact values at multiples of 90 degrees, by a table of right angles
(web/src/builtins.ts, line 43, and mathterpiece/builtins.py, line 41), so the undefined points of
{numref}`undefined-operations` agree. Other values agree only to the last bits. `(= (sind 30) 0.5)`
is false at both times. The options:

- (a) Require the same bits: both programs use one algorithm for each function, such as correctly
  rounded functions, and the same order of operations for conversions and `mod`. Both times then
  agree exactly, at the cost of work in both programs.
- (b) Allow results that differ in the last bits for these functions, and state this in
  {numref}`same-value-at-both-times`. Then `=` on such results may differ between the two times
  (Q-evaluation-7).
- (c) Fold these functions only when the result is exact, as at right angles, and leave the rest
  to the runtime. Both times agree, and less is folded.
:::
