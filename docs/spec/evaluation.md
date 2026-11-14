(evaluation)=
# Evaluation

This part defines how an expression is computed: the order in which its parts are evaluated, the
forms that evaluate only some of their parts, the operations that are {term}`undefined` and
where, how `none` propagates, the numbers and their limits, random values, equality, and how deep
a chain of calls may go.

An expression is computed at one of two times ({doc}`binding-time`). When every value that it
reads is known when compiling, the compiler computes it in the fold step and writes the value into
the .mtpc in place of the expression. This is {term}`folding`. Otherwise the runtime computes it
while drawing, again each time a value that it reads changes ({doc}`reaction`). Every rule in this
part applies at both times, unless the rule is stated for one of them. Where the compiler or the
runtime does something else today, a note that starts with "Code differs" follows the rule.

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
arguments of one call are evaluated does not change the value. The runtime evaluates arguments
from left to right (web/src/runtime.ts, `compileBuiltin` and the case `call` of `compile`).

```{rule} forms-evaluate-some-parts
These forms evaluate only some of their parts:

| Form | Evaluates |
|---|---|
| `(if c a b)` | `c`, then `a` when `c` is true, or `b` when it is false |
| `(or? x d)` | `x`, then `d` only when `x` is `none` |
| `(let ((n1 v1) (n2 v2) …) body)` | each value that the body or a later value reads, once, in order, then the body. A value that nothing reads is not evaluated. A value that is read is evaluated before the body, even when the branch of the body that reads it is not taken |
| `(fn params body)` | nothing, until the function is called |
```

```{rule} cond-and-or-as-if
`cond`, `and` and `or` are sugar, and mean exactly these `if` forms:

| Form | Is |
|---|---|
| `(cond (c1 v1) more… (else v))` | `(if c1 v1 (cond more… (else v)))` |
| `(cond (else v))` | `v` |
| `(and a b …)` | `(if a (and b …) false)` |
| `(and a)` | `a` |
| `(or a b …)` | `(if a true (or b …))` |
| `(or a)` | `a` |
```

So, when compiling and while drawing, `cond` evaluates its tests in order, up to the first that is
true, then the value of that clause only. `and` stops at the first part that is false, and `or` at
the first part that is true. `(when c x)` is `(if c x none)` ({numref}`rewrite-when`), and
evaluates its parts in the same way.

The compiler leaves out every `let` value that nothing reads (mathterpiece/compiler.py, line 6693),
and the runtime evaluates the rest before the body (web/src/runtime.ts, line 1060). So in
`(let ((s (walk k))) (if c s 0))`, `walk` is called while drawing whether `c` is true or not.

The collection functions call their function on the items in order. While drawing, `any` and
`all` with a function stop at the first item at which the result is known (`Array.some` and
`Array.every` in web/src/runtime.ts, `compileCollection`). When folding, the compiler calls the
function on every item first (mathterpiece/compiler.py, line 2794). By
{numref}`evaluation-is-pure` the two give the same value.

### Parts of these forms when compiling

```{rule} known-condition-takes-one-branch
When the condition of an `if` is known when compiling, the prove step proves only the branch that
is taken. The other branch is neither proved nor folded. Inside the body of a `foreach` or a
motif, the variable of the `foreach` and the parameters of the motif are not known in the prove
step, since the body is proved once for all their values ({numref}`prove-bodies-once`).
```

By {numref}`cond-and-or-as-if`, the same holds for the tests of a `cond` and the parts of an `and`
or an `or`. `or?` and `let` are proved whole: every part is proved, also a part that the form
would not evaluate because a value before it is known when compiling. An undefined operation with
known inputs in such a part is a compile error ({numref}`undefined-gives-none`):

```mtp
(real x 0 (const))
(real a (if (= x 0) 0 (/ 1 x)))              ; compiles, and a is 0
(real b (cond ((= x 0) 0) (else (/ 1 x))))   ; compiles, and b is 0
(bool c (and (> x 0) (> (/ 1 x) 2)))         ; compiles, and c is false
(real d (let ((u (/ 1 x))) 0))               ; division by zero, at (/ 1 x)
(real e (if (= x 0) 0 'not a number'))       ; compiles: the string is never proved
```

A folded call is computed by evaluating its body, not by proving it again, so a folded call of a
function that calls itself ends at its base case. A `foreach` copy can start a chain, in which
copy k reads copy k - 1 through a `(name …)` string, as in `(if (= k 0) 1 (* 2 (. (name
$'d-{(- k 1)}') x)))`. How such a name is resolved when the body is proved once is defined in
{doc}`core` (Q-core-3).

:::{admonition} Code differs
:class: note
`cond`, `and` and `or` are compiled whole: every part is compiled, also a part that the form would
not evaluate (mathterpiece/compiler.py, lines 6519 to 6531 for `and` and `or`, and 6608 to 6662
for `cond`). So `b` and `c` in the example above are rejected with "division by zero". Only while
a call is folded does `cond` stop at the first test that is known to be true (line 6614).
mtp-08wd.2.
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
| a call of a function | a call whose depth is above the call depth limit ({numref}`call-depth-limit`) |

Every other built-in function and operator is undefined nowhere.
```

The functions of the standard library are written in mtp, and are undefined where the built-ins
that they call are ({doc}`stdlib`).

```{rule} undefined-gives-none
In the fold step and while drawing, an undefined operation gives `none`. It never stops the
figure, and never gives an infinity or a value that is not a number. In the prove step, an
operation that is undefined at inputs known when compiling is a compile error, at the operation.
The inputs may be written by the illustrator, or read from `const` variables. The variable of a
`foreach` and the parameters of a motif or a function are not such inputs, since their bodies are
proved once ({numref}`prove-bodies-once`).
```

So `(sqrt -1)` and `(or? (sqrt -1) 0)` are compile errors. In
`(scene s (foreach i 3 (circle_ (r (/ 1 i)))))`, `(/ 1 i)` may be undefined, since `i` may be 0, so
its type includes `none`, and `r` does not take `none`: this is a compile error at `(/ 1 i)` in the
body. With `(r (or? (/ 1 i) 1))`, the scene compiles, and the copy for `i` = 0 has a radius of 1.

:::{admonition} Code differs
:class: note
The compiler proves each copy of a `foreach` with the value of its variable, so
`(r (or? (/ 1 i) 1))` is rejected with "division by zero" at copy 0. mtp-08wd.1.
:::

A function body is proved once, with each parameter ranging over its declared type
({numref}`prove-bodies-once`). A call whose arguments are all known when compiling is folded: the
fold step computes the body with those arguments, and an undefined operation in the body gives
`none` ({numref}`undefined-gives-none`). The illustrator wrote the body with parameters, not with
known inputs, so an `or?` in the body can replace the `none` with a default (docs/type-system.md,
section 5.c). With `(func[real] f ((real t)) (let ((b (or? (sqrt t) 0))) (if (> t 0) b 1)))`, `(f
-1)` is 1. With `(func f ((real x)) (/ 1 x))`, the result type includes `none`, and `(f 0)` is
`none`. `(func[real] f ((real x)) (/ 1 x))` is a compile error at `(/ 1 x)`, since its body may give
`none` and its declared result does not include `none`.

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
- `=` and `!=`, by {numref}`equality-by-content`.
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

There are four types of number ({doc}`types`). Each is held this way at both times:

| Type | When compiling and while drawing |
|---|---|
| `int` | an exact whole number |
| `ratio` | an exact fraction |
| `real` | an IEEE 754 binary64 number |
| `complex` | two binary64 numbers |

Ints and ratios are exact ({numref}`number-literals`), and only a real may differ between the two
times ({numref}`same-value-at-both-times`). So the runtime computes values of type `int` as exact
whole numbers and values of type `ratio` as exact fractions, as the compiler does, and an operation
on ints and ratios alone gives the same value when folded as while drawing.

In the .mtpc, a ratio is written as its numerator and denominator in lowest terms
({doc}`compiled-format`).

:::{admonition} Code differs
:class: note
The runtime divides the two numbers of a ratio when it loads the .mtpc (web/src/runtime.ts, lines
934 to 937), and computes ints and ratios as binary64 numbers (web/src/builtins.ts). The compiler
computes them exactly, with Python's `Fraction` and ints (mathterpiece/compiler.py, `_fold`, line
7913). So with `(int n 1)`, which a slider writes, `(= (+ (/ n 10) 1/5) 3/10)` is false while
drawing, and the readout of the example below holds False at n = 1. `(+ (^ 2 60) 1)` is folded to
1152921504606846977, and the runtime reads that value from the .mtpc as 1152921504606846976.
mtp-ydd4.7.13.
:::

```{mtp-example}
; at n = 1 the sum is exactly 3/10, when folded and while drawing
(int n 1 (>= 0) (<= 10))
(slider pick (move n (from 0) (to 10)) (label 'n'))
(readout r $'n/10 + 1/5 = 3/10 is {(= (+ (/ n 10) 1/5) 3/10)}')
```

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

### The limit of every number

```{rule} number-limit
Every number lies within ±10¹⁵⁰, the {term}`number limit`:

- A literal beyond it is a compile error, and so is a starting value known when compiling, also
  one given with `free@`.
- A write of a number beyond it is clamped to it. So is each number of a point or a list that is
  written.
- For the ranges that the prover proves, a value with no limit of its own lies within it.

A computed result may go beyond the number limit. A result beyond the largest real, about 1.8 ×
10³⁰⁸, is an overflow, and is undefined ({numref}`undefined-operations`).
```

With these limits, `(* 2 k)` or `(* 360 t)` can never overflow, while a product of several values
with no limit of their own may (docs/type-system.md, section 5.c).

:::{admonition} Code differs
:class: note
- The compiler checks only literals against the limit (`_Compiler.literal`,
  mathterpiece/compiler.py, line 5882), so `(real k free@(* 1e100 1e100))` starts at 10²⁰⁰, and
  `(real m (* k k))`, which the prover takes to be safe, is `none` while drawing. Bug mtp-mqbu.
- `constrain` (web/src/runtime.ts, line 761) clamps a write only when the value is a single number.
  mtp-ydd4.7.18.
- `sum` while drawing adds with the built-in `+` (web/src/runtime.ts, line 1248), whose
  `Undefined` error is not caught there, so an overflow stops the evaluation and does not give
  `none`. Bug mtp-ec05.
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
infinite binary64 number (web/src/runtime.ts, line 932). With `(real big infty (const))` and a free
`(real y 1)`, `(+ y big)` is `none` while drawing, since its result is infinite. With `y` known
when compiling, the same expression is folded to `infty`. That breaks
{numref}`same-value-at-both-times`, so the code as it is today is not an option. The options:

- (a) An expression computed while drawing never reads an infinity: reading a `const` that holds
  one outside an expression that is folded is a compile error.
- (b) The runtime carries infinities as the compiler does, and gives `none` only where the result
  would reach a place that needs a finite number, such as an attribute of a shape.
:::

### Rounding

```{rule} rounding
Wherever a number is rounded, halves round away from zero, on the number's shortest exact decimal
form, not on its binary value: 2.5 gives 3, -2.5 gives -3, 0.125 to two decimal places gives 0.13,
and 2.675 to two decimal places gives 2.68. The rule applies to `round`, to a write into an int,
and to the format spec of an interpolated string, such as `{x:.2f}`. `round` is undefined nowhere.
A number written into an int is rounded after it is clamped to the int's range, so that it lands
on the nearest int inside the range ({doc}`types`).
```

The runtime rounds the value once before the constraints and once after them, so that an int that
wraps is never rounded up out of its interval (web/src/runtime.ts, lines 763 and 771). The
compiler rounds with Python's `Decimal` (mathterpiece/compiler.py, `_round`, line 6877), and the
runtime with `roundHalfAway` (web/src/builtins.ts, line 181). On 1,031 values from -8 to 8, and on
156 pairs of a value and a format spec, the two agree.

:::{admonition} Code differs
:class: note
`_round` quantizes a `Decimal` in the default context, whose precision is 28 digits, so
`(int r (round 1e28))` raises `decimal.InvalidOperation`, which is not a compile error and has no
position. Bug mtp-6yga.
:::

:::{admonition} Open question Q-evaluation-5
:class: warning
How the channels of a mixed color are rounded. By {numref}`same-value-at-both-times`, both times
must give the same channels. Today the compiler rounds halves to even (Python's `round`,
mathterpiece/colors.py, line 237), and the runtime rounds halves up (`Math.round`,
web/src/builtins.ts, line 287). So `(mix '#000000' '#050505' 0.5)` is `#020202ff` when folded and
`#030303ff` while drawing (bug mtp-nk2w). The options, at both times:

- (a) The channels of a mixed color follow {numref}`rounding`.
- (b) The channels round halves up, as CSS `color-mix()` does in browsers.
- (c) Colors are not rounded until they are drawn, so the channels of a mixed color may be
  fractions.
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

```{rule} random-never-folded
A random value is known only while drawing ({doc}`binding-time`). The compiler never draws one and
never folds one.
```

By {numref}`random-values`, for one .mtpc, the same values of the seeds give the same random
values, on every refresh and in every browser, and when a seed takes a new value, every random
value that follows it is drawn again ({doc}`reaction`). Since the sites are
counted when compiling, a change to the source that adds or removes a random function before
another one changes the site of the later one, and with it the value that the later one draws.
docs/data-model.md, line 283, has "is drawn once, when the page loads", which is wrong: a new seed
draws every value that follows it again, as docs/reference.md, line 101, has.

A roll, `(roll-dice s)`, is a write of `(next-seed s)` into the seed `s`
({numref}`rewrite-roll-dice`). By {numref}`random-values`, it changes the random values that follow
`s`, and no others.

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

A `rand` that follows a `const` seed, such as `(rand-seed s 3 (const))`, is a compile error by
{numref}`seed-variable`. Today the message is "a random value follows a seed: import the standard
one, (import rand), or declare one, (rand-seed dots 0)", although one is declared. The wording of
a message is not normative ({numref}`what-is-normative`).

:::{admonition} Open question Q-evaluation-6
:class: warning
Two points about random values are not settled:

- **`lo` above `hi`.** Neither `rand` nor `rand-int` checks that `lo` is at most `hi`. With
  `(rand-int 10 3)`, {numref}`random-values` gives an int from 4 to 10, not from 3 to 10. The
  compiler gives the result the range from `lo` to `hi` (mathterpiece/compiler.py, lines 2262 and
  2273), here from 10 to 3, so it accepts `((int (>= 3) (<= 5)) b (rand-int 5 3))`, which is a bug
  in every case (mtp-y7vp). The options: (a) `lo` above `hi` is undefined, (b) the two are
  swapped, (c) the compiler proves that `lo` is at most `hi`.
- **Only the seed modulo 2³² counts.** The hash uses x mod 2³² (`x >>> 0`, web/src/random.ts,
  line 9), so the seeds 0 and 2³² draw the same values, and so do 0 and 10¹⁵⁰. The options: (a) the
  spec keeps {numref}`random-hash` as it is, and states this in a sentence, (b) `rand-seed` is
  narrowed to ints below 2³².
:::

## Equality

`=` and `!=` take any two values of one type, and `!=` gives the opposite of `=`.

```{rule} equality-operands
`(= a b)` and `(!= a b)` are a compile error unless the type of one side fits the type of the other,
or one side is `none`. They are a compile error on functions, transitions or animations, or on
values whose type holds one of them, such as a list of functions. A list of two numbers is not
converted to a point for them: `(= p xs)`, with `p` a point and `xs` a list of ints, is a compile
error. A literal list on one side is given the type of the other side, so `(= p [1 2])` compiles.
```

```{rule} equality-by-content
Values compare by content, and mutable objects by identity. `=` and `!=` never give `none`:

| Type | `(= a b)` is true when |
|---|---|
| `none` | both are `none`. `(= none x)` is false for every `x` that is not `none` |
| `int`, `ratio`, `real` | the two are the same number, exactly: 0 and -0 are equal, and an int and a real of the same value are equal |
| `complex` | both parts are equal. A complex whose second part is 0 equals the real of its first part |
| `bool`, `string`, a choice | the two are exactly the same |
| `point`, `list[T]`, `transform` | they have the same length, and the items at each position are equal |
| `color` | they are the same color once parsed: `(= ink '#000080')` is true with `(color ink 'navy')`. A light-dark color equals another when both of its modes do, and a color with the same value in both modes is one color. A token is compared by its value in the live model, never by a value that the page's CSS gives it |
| `font` | every part is equal |
| a shape, a group, a namespace, a formula, a term and every other mutable object | the two are the same object. Two circles with the same attributes are not equal |
```

Since `=` on reals is exact, `(= (sind 30) 0.5)` is false, since `(sind 30)` is
0.49999999999999994. A real may differ in its last digits when folded and while drawing
({numref}`real-error-bound`), so `=` on two reals that come from such functions may be true at one
time and false at the other.

:::{admonition} Code differs
:class: note
The compiler accepts `=` and `!=` with every type (mathterpiece/compiler.py, line 6443), so
`(= sind sind)` and `(= t t)` for a transition `t` compile. While drawing, `equal`
(web/src/builtins.ts, line 156) compares functions with `===`, and the runtime makes a new
JavaScript function for each read of a function (web/src/runtime.ts, `functionValue` and
`builtinValue`), so `(= f f)` is false. mtp-08wd.4.
:::

### Matching

The runtime uses a separate, tolerant comparison to check whether the scene is in a state. It is
not equality.

```{rule} matching
Two values {term}`match` when they are equal, with one difference: two reals match when they
differ by at most 10⁻¹² or by at most a millionth of the larger of their sizes. Points and lists
match when they have the same length and the items at each position match. Bools, strings, choices
and colors match only when they are exactly the same, and `none` matches only `none`. Only the
runtime matches values: no form of the language matches two values.
```

Matching is `same` in web/src/same.ts. The runtime uses it to read the step of a play or a stepper
from the scene (docs/reference.md, line 572, and web/src/player.ts, line 302), and to check
whether the free values that a canvas's `on-view` moves still have their values from page load
(web/src/lifecycle.ts, line 62).

While drawing, the runtime uses `=` to skip writes: a write of a value equal to the current one is
skipped, and nothing that depends on it is computed again (web/src/runtime.ts, line 728).

(termination)=
## Termination

A function may call itself, directly, through other functions, or through a function value
(docs/reference.md, line 124). There are no other loops: a `foreach` makes a number of copies known
when compiling, and `range` gives at most 1,000,000 items. So the only computation that could go
on without end is a chain of calls, and the call depth limit ends every chain.

```{rule} call-depth-limit
The depth of a call of a function, declared with `func` or written with `fn`, is 1 plus the number
of such calls that are still being computed when it starts. Calls of built-in functions do not
count. `max-call-depth` is one constant of this spec, the {term}`call depth limit`, and it is the
same when folding and while drawing. A call whose depth is above it is undefined
({numref}`undefined-operations`). A function is recursive when its body names it, directly or
through the bodies of the functions that it names, and a call of a recursive function has a type
that includes `none` ({doc}`types`).
```

So in `(func[int] down ((int m)) (if (<= m 0) 0 (+ 1 (down (- m 1)))))`, the inner call
`(down (- m 1))` has the type `int|none`, so the body may give `none`, and the declaration is a
compile error. Written `(func down ((int m)) …)`, with the same body, the result type is
`int|none`, and `(down 5)` is 5, when folded and while drawing. A call of `down` with an argument
large enough to pass the limit gives `none`.

Every computation ends, since every chain of calls is at most `max-call-depth` deep. A computation
that ends may still take a long time, and the spec sets no limit on time.

:::{admonition} Code differs
:class: note
- **When compiling.** A call with known arguments is folded by compiling its body again with those
  arguments. When the nesting is too deep for Python, at a depth of about 80, the compiler catches
  the `RecursionError` and leaves the call to the runtime (mathterpiece/compiler.py, `fold_call`,
  line 2530). Working out the range of a call does the same (line 2013). A recursive call is typed
  by the declared result of its function, so `(func[int] down …)` above compiles, and `(down 80)`
  is folded while `(down 81)` is not.
- **While drawing.** There is no limit on the depth of calls (web/src/runtime.ts, `call`, line
  1282). Each call uses the JavaScript call stack, and a call that is too deep throws `RangeError:
  Maximum call stack size exceeded`, which is drawn in place of the view or the control
  (web/src/elements.ts, `guard`, line 324). In Node 26 this happens past a depth of about 1740,
  and the depth depends on the browser.

mtp-ydd4.7.15.
:::

:::{admonition} Open question Q-evaluation-8
:class: warning
The value of `max-call-depth`. Neither the code nor the decisions give one. It must be small
enough that every browser that the runtime supports can compute a chain of that depth, and large
enough for the recursive functions of the examples: `best-in` in bourgain-densities.mtp, `koch` in
koch-snowflake.mtp and `has-divisor` in ulam-spiral.mtp.
:::

(folding-and-drawing)=
## Folding and drawing compared

```{rule} same-value-at-both-times
An expression gives the same value when it is folded as when it is computed while drawing, for the
same values of what it reads, with one exception: a real may differ in its last digits
({numref}`real-error-bound`), and so may a value computed from such a real.
```

```{rule} real-error-bound
`+`, `-`, `*`, `/` and `sqrt` on reals give the correctly rounded binary64 result, at both times.
Every other built-in function on reals gives a result within `max-real-error` units in the last
place of its exact value at the same binary64 inputs. This holds for the trigonometric functions
in radians and in degrees, `exp`, `log`, `^`, `mod`, `dist`, and the conversion between degrees
and radians. `max-real-error` is one constant of this spec, the {term}`real error bound`. At
multiples of 90 degrees, the functions in degrees give exact values.
```

```{rule} prover-widens-reals
When the prover works out the range of a real, it widens the range outward after each operation:
the lower bound is moved down and the upper bound up, by one unit in the last place for the five
correctly rounded operations, and by `max-real-error` units in the last place for every other
function on reals. So a range that the prover proves holds at both times.
```

A folded value is final: the .mtpc holds the value in place of the expression
({numref}`compile-steps`), so the runtime uses it as written and never computes it again.

{numref}`same-value-at-both-times` follows the guides: docs/reference.md, line 613, has "One rule,
the same in the compiler and the runtime", and the comment at line 1 of web/src/builtins.ts has "as
the compiler folds them". The compiler computes with CPython and its `math` module, and the runtime
with JavaScript and its `Math` object.

:::{admonition} Code differs
:class: note
The two programs differ in these places, beyond what the rules above allow:

| Where | When compiling | While drawing | Bead |
|---|---|---|---|
| ratios, and ints beyond 2⁵³ | exact | binary64 | mtp-ydd4.7.13 |
| `round` of 10²⁸ or more | the compiler stops | rounds | mtp-6yga |
| the channels of a mixed color | halves to even | halves up | mtp-nk2w, Q-evaluation-5 |
| an infinite input | carried, `(+ y infty)` is `infty` | `none` | Q-evaluation-4 |
| recursion | folded up to a depth of about 80 | computed up to the stack of the browser | mtp-ydd4.7.15 |
| `mod` of reals | Python's `%`, which is exact | `a - b × ⌊a / b⌋`, so `(mod 5.5 0.1)` is 0 and not 0.0999999999999997 | mtp-ydd4.7.14 |
| the functions in degrees, for large angles | converted to radians first, so `(cosd (+ 1e15 90))` is 0.98478… | `(x × π) / 180` first, so it is 0.98512… | mtp-ydd4.7.14 |
| the range of a real | not widened (`_range_of`, mathterpiece/compiler.py, line 7698) | | mtp-08wd.3 |

For `(cosd (+ 1e15 90))` the exact value is the cosine of 10 degrees, 0.98481…, so both times
are wrong in the fourth digit. Elsewhere the two differ only in the last bits, which
{numref}`real-error-bound` allows: `sind` differs on 776 of 2,885 angles from -360 to 360 degrees,
a quarter of a degree apart, and `sin`, `cos`, `tan`, `exp`, `log`, `atan`, `asin`, `acos` and
`dist` differ in the last bit on 1 to 41 percent of 1,031 values from -8 to 8. Formatting with a
format spec, `round`, and `sqrt` agreed on every value tried.
:::
