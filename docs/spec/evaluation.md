(evaluation)=
# Evaluation

This page defines how an {term}`expression` is computed: the order in which its parts are
{term}`evaluated <evaluation>`, the {term}`forms <form>` of which only some parts are evaluated,
the arguments at which an expression results in `none`, how `none` propagates, the numbers and their
limits, random values, equality, and how deep a chain of calls can go.

An expression is computed at one of two times ({doc}`binding-time`). When every value that it
reads is known when compiling, the {term}`compiler` computes it in the fold step and writes the
value into the {term}`.mtpc` in place of the expression. This is {term}`folding`. Otherwise the
{term}`runtime` computes it while drawing, again each time a value that it reads changes
({doc}`reactivity`). Every rule on this page applies at both times, unless the rule is stated for one
of them.

## Evaluation changes nothing

This rule exists so that the compiler may compute an expression ahead of time, and the runtime again at any time, and get the same value with no side effects.

```{rule} evaluation-is-pure
Evaluating an expression gives a value and changes nothing, no container, {term}`seed` or page
element. The value depends only on what the expression reads: containers, {term}`bindings <binding>`,
the seeds of its random functions, and, for a read of a position, the frame of the expression
({doc}`scene`).
```

## What a name means

This rule exists so that the place where a name is written determines whether it declares, gives a value or names a container.

```{rule} what-a-name-means
A name means one of three things, by where it is written. `(name S)` and a name string `@'…'` mean
what the name that they spell means where they are written ({numref}`names-from-values`).

- Where a declaration gives its name, the name declares the variable, the object or the function.
- In an expression, the name evaluates to what it refers to: the value that a variable holds, the
  value bound to a `let` or `foreach` name, the object, or the function. A name never evaluates to
  a name.
- As the target of a writer or of a movement, the name means the container, not the value that it holds
  ({numref}`writable-targets`).
```

So with `(real a 1)` and `(circle c (r a))`, `a` in `(r a)` evaluates to 1, `c` in `c.r` evaluates
to the circle, and `a` in `(slider s a (from 0) (to 2))` means the container `a`.

## Evaluation order

This rule exists to fix the order of evaluation, so that every compiler and runtime compute a call the same way.

```{rule} arguments-before-call
A call of a function, a built-in function or an {term}`operator` evaluates every argument, then computes
its result from their values. The forms of {numref}`forms-evaluate-some-parts` are the only exceptions.
```

By {numref}`evaluation-is-pure`, and since every argument is evaluated, the order in which the
arguments of one call are evaluated does not change the value.

This rule exists so that a part that is not evaluated, such as the untaken branch of an `if`, can never make an error or a `none`.

```{rule} forms-evaluate-some-parts
Only some of the parts of these forms are evaluated:

| Form | The parts that are evaluated |
|---|---|
| `(if c a b)` | `c`, then `a` when `c` is true, or `b` when it is false |
| `(or? x d)` | `x`, then `d` only when `x` is `none` |
| `(let ((n1 v1) (n2 v2) …) body)` | the expression of each binding that the {term}`body` or a later expression reads, once, in order, then the body. An expression that nothing reads is not evaluated. An expression that is read is evaluated before the body, even when the branch of the body that reads it is not taken |
| `(fn params body)` | nothing, until the function is called |
```

So in `(let ((s (walk k))) (if c s 0))`, `walk` is called whether `c` is true or not.

`cond`, `and` and `or` are {term}`syntactic sugar` for `if` forms ({numref}`sugar-rewrites`). So the
tests of a `cond` are evaluated in order, up to the first that is true, and then only the value of
that branch. The parts of an `and` are evaluated up to the first that is false, and those of an
`or` up to the first that is true. `(when c x)` is `(if c x none)` ({numref}`rewrite-when`), and its
parts are evaluated in the same way.

The function passed to a list function is called on the items in order. `any` and `all` with a
function may stop at the first item at which the result is known: by {numref}`evaluation-is-pure`,
the value is the same.

### Which parts the prove step proves

This rule exists so that a branch that can never run does not stop a source from compiling.

```{rule} known-condition-takes-one-branch
When the test of an `if` is known in the prove step ({numref}`check-bodies-once`), only the branch taken
is checked and folded.
```

So inside the body of a `foreach` or a motif, the prove step checks both branches of an `if` whose
test reads the binding of the `foreach` or a parameter of the motif, since the body is checked
once for all their values. Each branch is checked for the values for which it runs
({numref}`if-narrowing`). By {numref}`sugar-rewrites`, the same holds for the tests of a `cond`
and the parts of an `and` or an `or`. `or?` and `let` are proved whole: every part is proved, even a
part that would not be evaluated because a value before it is known when compiling. An expression
that results in `none` at known arguments in such a part is a {term}`compile error`
({numref}`none-at-known-arguments`):

```mtp
(real x 0 (const))
(real a (if (= x 0) 0 (/ 1 x)))              ; compiles, and a is 0
(real b (cond ((= x 0) 0) (else (/ 1 x))))   ; compiles, and b is 0
(bool c (and (> x 0) (> (/ 1 x) 2)))         ; compiles, and c is false
(real d (let ((u (/ 1 x))) 0))               ; division by zero, at (/ 1 x)
(real e (if (= x 0) 0 'not a number'))       ; compiles: the string is never proved
```

A folded call is computed by evaluating its body, not by checking it again, so a folded call of a
function that calls itself ends at its base case. The copies of a `foreach` can form a chain, in
which copy k reads copy k - 1 through `(name …)`, as in `(if (= k 0) 1 (* 2 (. (name
f'd-{(- k 1)}') x)))`. {numref}`names-from-values` defines how the prover proves such a name when
the body is checked once.

:::{admonition} Code differs
:class: note
`cond`, `and` and `or` are compiled whole: every part is compiled, even a part that would not be
evaluated (mathterpiece/compiler.py, lines 6519 to 6531 for `and` and `or`, and 6608 to 6662
for `cond`). So `b` and `c` in the example above are rejected with "division by zero". Only while
a call is folded does `cond` stop at the first test that is known to be true (line 6614).
mtp-08wd.2.
:::

## Expressions that result in none

This rule exists to list where an expression has no value, so that the compiler and the runtime give `none` for the same arguments.

```{rule} expressions-that-give-none
Besides an argument that is `none` ({numref}`none-propagates`), an expression results in `none` at
these arguments, when folded and while drawing. At every other argument, an expression does not
result in `none`.

| Expression | Results in `none` at |
|---|---|
| `/` | a divisor of 0 |
| `mod` | a divisor of 0 |
| `^` | 0 to a negative power, and a negative base to a power that is not an {term}`int` |
| `sqrt` | an argument below 0 |
| `log` | an argument of 0 or below, and a base of 0 or below or of 1 |
| `min`, `max` | no items at all |
| `tand`, `secd` | 90 + 180k degrees, for every int k |
| `cscd`, `cotd` | 180k degrees, for every int k |
| `csc`, `cot` | 0. No {term}`real` is exactly π/2, so `tan` and `sec` result in `none` at no argument |
| `asin`, `acos`, `asind`, `acosd` | an argument below -1 or above 1 |
| `asec`, `acsc`, `asecd`, `acscd` | an argument strictly between -1 and 1 |
| `.arg`, the argument of a point or a complex number | the point `[0 0]` and the complex number 0 |
| `rand`, `rand-int` | a `lo` above `hi`, whatever the seed |
| `choice` | an empty {term}`list` |
| `range` | a gap of 0, a negative count `num`, and more than 1,000,000 items |
| `xs[i]` | a position outside -n to n - 1, on a list of n items |
| `g[k]` | a member that the group does not have |
| a bound variable or attribute with a {term}`condition` | a value that breaks the condition ({doc}`types`) |
```

:::{admonition} Code differs
:class: note
- A folded call whose body results in `none` by this rule is a compile error for `min` and `max` of an
  empty list, `range` with more than 1,000,000 items, and `xs[i]` outside -n to n - 1. For example,
  with `(func f ((list[real] x)) (min x))`, `(f (as list[real] {}))` is rejected, and so is
  `(f 3)` with `(func f ((int x)) (. {1 2 3} x))`. `min` and `max` of a known empty list
  (mathterpiece/compiler.py, line 2435) and a known position outside a list (line 6369) raise the
  error directly, and not through `known_or_none` (line 2217), which returns `none` while a call is
  folded. `range` results in `none` there, but the type of the body of `f` does not include `none`, so
  `fold_call` raises the error again (lines 2527 to 2529). Bug mtp-ydd4.7.48.
- `choice` always has a type that includes `none` (mathterpiece/compiler.py, line 2281), so
  `(rand-seed sd 1) (real v (choice {1 2}))` is rejected with "v may be none". Bug mtp-ydd4.7.49.
:::

So no expression results in an infinity or NaN: a real is always finite ({numref}`number-types`).
The functions of the {term}`standard library` are written in mtp, and result in `none` where the
built-in functions that they call result in `none` ({doc}`stdlib`).

This rule exists so that an expression known to have no value is reported when compiling, rather than giving `none` on the page.

```{rule} none-at-known-arguments
An expression whose arguments are known in the prove step ({numref}`check-bodies-once`) and give `none` by
{numref}`expressions-that-give-none` is a compile error, and so are `rand` and `rand-int` with both bounds
known and `lo` above `hi`, though their seed is never known when compiling.
```

So `(sqrt -1)`, `(or? (sqrt -1) 0)` and `(rand-int 10 3)` are compile errors. In
`(scene s (foreach i 3 (circle_ (r (/ 1 i)))))`, `(/ 1 i)` results in `none` when `i` is 0, so its type
includes `none`, and the type of `r` does not include `none`: this is a compile error at
`(/ 1 i)` in the body. With `(r (or? (/ 1 i) 1))`, the scene compiles, and the copy for `i` = 0
has a radius of 1.

:::{admonition} Code differs
:class: note
- The compiler checks each copy of a `foreach` with the value of its variable, so
  `(r (or? (/ 1 i) 1))` is rejected with "division by zero" at copy 0. mtp-08wd.1.
- Neither `rand` nor `rand-int` checks that `lo` is at most `hi`. While drawing, `(rand-int 10 3)`
  evaluates to an int from 4 to 10 by the formula of {numref}`random-values`. The compiler sets the
  {term}`range` of the result from `lo` to `hi` (mathterpiece/compiler.py, lines 2262 and 2273), here
  from 10 to 3, so it accepts `((int (>= 3) (<= 5)) b (rand-int 5 3))`. Bug mtp-y7vp.
:::

A function body is checked once, with each parameter ranging over its declared type
({numref}`check-bodies-once`). A call whose arguments are all known when compiling is folded: the
fold step computes the body with those arguments, and an expression in the body that results in
`none` at those arguments results in `none` there too ({numref}`expressions-that-give-none`). So an
`or?` in the body may replace the `none` with a default. With
`(func[real] f ((real t)) (let ((b (or? (sqrt t) 0))) (if (> t 0) b 1)))`, `(f -1)` is 1. With
`(func f ((real x)) (/ 1 x))`, the result type includes `none`, and `(f 0)` is `none`.
`(func[real] f ((real x)) (/ 1 x))` is a compile error at `(/ 1 x)`, since its body results in
`none` when `x` is 0 and its declared result type does not include `none`.

The prover works out, from the ranges of their arguments, which expressions can result in `none`, and
the type of each such expression includes `none` ({numref}`may-give-none`).

```{mtp-example}
; sec θ has no value at 90°, and there the readout holds its default text
(real theta 60 (>= 0) (<= 180))
(slider turn (animation (move theta (from 0) (to 180) (duration 0))) (label 'θ'))
(readout r (or? f'sec θ = {(secd theta):.3f}' 'sec θ has no value at 90°'))
```

## How none propagates

This rule exists so that the runtime never stops on a missing value: `none` passes through to where it is handled.

```{rule} none-propagates
An attribute of `none` is `none`, so is an {term}`interpolated string` with a part that is `none`, and so
is a list function given `none` for its list. An expression with an argument that is `none` gives `none`, at both times, except:

- `or?`, `none?`, `some?` and `somes`, which give a value that is not `none` ({doc}`stdlib`)
- `=` and `!=` ({numref}`equality-by-content`)
- a call whose parameter's type includes `none`, which evaluates its body with `none`. A parameter
  whose type does not include `none` makes the call `none` without evaluating the body.
- `(list-of …)`, which gives a list holding `none`. A point with a coordinate that is `none` is `none`.
- `if`, which is `none` only when the branch taken is
- `map`, `reversed` and a read of a list's item, which pass `none` items through
```

:::{admonition} Code differs
:class: note
- `_Compiler.call` (mathterpiece/compiler.py, lines 1962 to 1973) folds the body with an argument
  that is `none`, also for a parameter whose type does not include `none`. So with
  `(func h ((real x)) 5)`, a call of `h` with `none` results in 5. Bug mtp-ydd4.7.50.
- `(reversed {1 (f 0)})`, with `(f 0)` known to be `none`, stops the compiler with a Python
  `TypeError`, since `_Compiler.collection` uses the smallest and the largest known item to compute
  the range of the items (line 2679). Bug mtp-ydd4.7.51.
- A list function with a list whose type includes `none` is a compile error, "the
  collection given to map may be none" (`collection_items`, line 2820), so
  `(map (if (= 1 2) {1} none) (fn ((int x)) x))` is rejected. Bug mtp-ydd4.7.52.
:::

This rule exists because a test or a count that meets `none` has no value that the runtime could use.

```{rule} none-never-a-condition
The test of an `if`, the `(active …)` of a {term}`control` or a {term}`listener`, and an item of the list
given to `sum`, `count`, `min`, `max`, `any`, `all` or `reduce` are never `none`. An expression that can
be `none` there is a compile error ({doc}`types`).
```

A shape declared `T|none` is not drawn while it is `none`, and `none` as a `fill` or a `stroke`
means no fill or no stroke. In every other place that the {term}`reader` sees, `none` must be
replaced with a default by `or?`, or left out of a list by `somes` ({doc}`types`).

## Numbers

This rule exists so that the compiler and the runtime hold every number the same way, and so compute the same results.

```{rule} number-types
There are four types of number ({doc}`types`). Each is held this way, when folded and while
drawing:

| Type | Held as |
|---|---|
| `int` | an exact whole number |
| `ratio` | an exact fraction |
| `real` | an IEEE 754 binary64 number that is finite: not an infinity and not NaN |
| `complex` | two binary64 numbers |
```

:::{admonition} Code differs
:class: note
The runtime divides the two numbers of a ratio when it loads the .mtpc (web/src/runtime.ts, lines
934 to 937), and computes ints and ratios as binary64 numbers (web/src/builtins.ts). The compiler
computes them exactly, with Python's `Fraction` and ints (mathterpiece/compiler.py, `_fold`, line
7913). So with `(int n 1)`, which a slider writes to, `(= (+ (/ n 10) 1/5) 3/10)` is false while
drawing, and the readout of the example below holds False at n = 1. `(+ (^ 2 60) 1)` is folded to
1152921504606846977, and the runtime reads that value from the .mtpc as 1152921504606846976.
mtp-ydd4.7.13.
:::

```{mtp-example}
; at n = 1 the sum is exactly 3/10, when folded and while drawing
(int n 1 (>= 0) (<= 10))
(slider pick (animation (move n (from 0) (to 10) (duration 0))) (label 'n'))
(readout r f'n/10 + 1/5 = 3/10 is {(= (+ (/ n 10) 1/5) 3/10)}')
```

This rule exists to define arithmetic on points, which the runtime uses for positions.

```{rule} point-arithmetic
The points form a vector space over the reals: `+` and `-` work coordinate by coordinate, `(* r p)`,
`(* p r)` and `(/ p r)` scale both coordinates by the real `r`, `(- p)` negates both, and the zero is
`[0 0]`.
```

This rule exists so that the compiler can give every arithmetic result a type before it is computed.

```{rule} number-result-types
Where a real meets an int or a ratio, the int or the ratio is first converted to the nearest real, ties
going to the real whose last bit is 0. An arithmetic result has the broadest type of its arguments, in the order `int`, `ratio`, `real`, `complex`,
except that:

- `/` of two ints gives a ratio
- `^` of an int to an int power gives an int when the power's range holds no negative int, and a ratio
  otherwise. With a {term}`complex` argument it gives a complex, and otherwise a real.
- `abs` of a complex gives a real
```

### The number limit

This rule exists so that no number ever overflows, at either time.

```{rule} number-limit
Every number lies within the number limit, -10¹⁵⁰ to 10¹⁵⁰, at both times:

- Every call of an operator or a built-in function gives its exact value, rounded where it is a binary64 number by
  {numref}`correctly-rounded-reals`, then clamped to the limit, number by number, the parts of complex
  numbers, points and lists included.
- A number written to a container is clamped to the limit, number by number.
- A {term}`literal` beyond the limit is a compile error.
- An int or a ratio is clamped to exactly -10¹⁵⁰ or 10¹⁵⁰, and a real to `1e150`, the binary64 number
  nearest to 10¹⁵⁰, just below it, or to minus that number.
```

So no call overflows, and no call results in `none` because of the size of its result. An
int or a ratio inside the number limit stays exact. `(* 1e100 1e100)` is `1e150`, and
`(* (^ 10 100) (^ 10 100))` is exactly 10¹⁵⁰. A call with several arguments is one
call, so `(* 1e150 1e150 1e-200)` is `1e100`, since the exact product of the three is
clamped once.

A starting value known when compiling is a literal or a result, so a starting value beyond the
number limit is always a literal: `(real k 1e200)` is a compile error, and
`(real k (* 1e100 1e100))` and `(real k free@(* 1e100 1e100))` start at `1e150`. A literal is not
clamped, because a literal is not the result of a call.

:::{admonition} Code differs
:class: note
`constrain` (web/src/runtime.ts, line 761) clamps a write only when the value is a single number.
mtp-ydd4.7.18.
:::

### Rounding

This rule exists so that every compiler and runtime round a number to the same result.

```{rule} rounding
Wherever a number is rounded, except a channel of a mixed color ({numref}`mixed-color-channels`), halves
go away from zero, on the number's shortest exact decimal form: 2.5 gives 3, -2.5 gives -3, and 2.675 to
two places gives 2.68. This applies to `round`, to `places`, to a write to an int, and to the
{term}`format spec` of an interpolated string. `round` never gives `none`. A number written to an int is
clamped to the int's range first ({doc}`types`).
```

:::{admonition} Code differs
:class: note
`_round` quantizes a `Decimal` in the default context, whose precision is 28 digits, so
`(int r (round 1e28))` raises `decimal.InvalidOperation`, which is not a compile error and has no
position. Bug mtp-6yga.
:::

This rule exists so that a color that the compiler mixes matches the color that a browser mixes.

```{rule} mixed-color-channels
Each channel of a mixed color is rounded to a whole number, halves up, at both times, as CSS
`color-mix()` does in browsers.
```

So `(mix #'#000000' #'#050505' 0.5)` is `#030303ff`, since its channels are 2.5.

:::{admonition} Code differs
:class: note
The compiler rounds halves to even (Python's `round`, mathterpiece/colors.py, line 237), and the
runtime rounds halves up (`Math.round`, web/src/builtins.ts, line 389). So
`(mix '#000000' '#050505' 0.5)` is `#020202ff` when folded and `#030303ff` while drawing. Bug
mtp-nk2w.
:::

## Randomness

This rule exists so that every random value can be computed again from a seed, and is the same on every page and in every compiler.

```{rule} seed-variable
Every random value is computed from a seed, a free variable of the {term}`built-in type` `rand-seed`,
whose values are the ints. A random function uses the seed of its `(seed s)`, or else the
{term}`default seed` of its file ({numref}`default-seed`). A const variable is not a seed.
```

The random functions `rand`, `rand-int`, `choice`, `shuffled` and `next-seed` are declared in the file
rand of the standard library ({numref}`rand-module`).

This rule exists so that a random function with no `(seed …)` still has exactly one seed.

```{rule} default-seed
A file's default seed is the only seed among the names of its {term}`file scope` ({numref}`scopes`). When
the file scope holds no variable of type `rand-seed`, it is the seed `seed` of the file rand
({ref}`stdlib-rand`), if the source imports that file, directly or not. Otherwise the file has no default
seed.
```

So in a file with several seeds, every call of a random function must hold a `(seed …)`. A file that
holds `(import rand rand-int)` and `(rand-seed dots 7)` has one seed, `dots`, since the import makes
only the name `rand-int` usable, and no name for the seed of the file rand. A file that holds
`(import rand)` may use the name `rand.seed`, so with `(rand-seed dots 7)` it has two seeds. A seed
of the file scope that is declared after a random function is its default seed too, and the random
function is then a compile error by {numref}`declare-before-use`.

These are the messages of the compile errors for a random function with no `(seed …)`, and for a
`(dice-roll)` with no argument:

| When | Message |
|---|---|
| several seeds | "this file declares several seeds: name the one this uses, as (rand 0 1 (seed dots))" |
| the default seed is declared after it | "the seed N is declared after this: a random value uses a seed declared before it" |
| only `const` variables of type `rand-seed` | "N is const, so it is not a seed: a random value uses a seed that is not const" |
| no variable of type `rand-seed`, and the file rand is not imported | "a random value uses a seed: declare one, (rand-seed dots 0), or import the standard one, (import rand seed)" |

This rule exists so that two calls of a random function in one source give different values from the same seed.

```{rule} random-site
Each call of the random function `rand`, `rand-int`, `choice` or `shuffled`, by any name that an
import makes usable for it, has a {term}`site`: a whole number. A call in a branch that is not
taken has a site too. The site is written in the expression in the .mtpc ({doc}`compiled-format`).
The sites are counted from 0, in
the order in which the calls start in the text of the source after the rewrite step
({numref}`compile-steps`), read with these changes:

- Each `(import …)` is read as the declarations of the imported file, in their order in that file.
- Each `foreach` is read as its copies, in the order of the copy index.
- Each declaration `(M …)` of an `M`, for a motif `M`, is read as itself, followed by the body of
  `M`. The body of a `motif` declaration is read only in each `M` that the source declares.
```

So a call that is written in the arguments of another call starts after it, and so comes after it.
So each copy and each shape declared with a motif has sites of its own, and so does each copy of a
call that a {term}`rewrite` makes. In

```mtp
(scene s
  (circle c (r (rand 1 2)) (x (rand (rand 0 1) 5)))
  (foreach i 2 (circle_ (r (rand 0 1))))
  (dot d (k (rand 0 1))))
```

where `dot` is a motif whose body holds one `rand`, the sites are 0 for the `r` of `c`, 1 and 2 for
the outer and the inner call in its `x`, 3 and 4 for the copies of the `foreach`, 5 for the `k` of
`d`, and 6 for the `rand` in the body of `dot`.

:::{admonition} Code differs
:class: note
The compiler counts the sites in the order in which it compiles the calls (`_Compiler.random`,
mathterpiece/compiler.py, line 2255). Within a shape, it compiles the attributes in the order of
the shape's table of attributes (`SHAPE_ATTRS`, line 268), with `pos` last, and not in the order in
which they are written. So in the example above it assigns the sites 0 and 1 to the `x` of `c`,
and the site 2 to the `r` of `c`. It also reads every `import` before any other form (line 745). Bead
mtp-ydd4.7.39 makes the compiler follow the rule.
:::

This rule exists so that every runtime computes the same random value from the same seed and site.

```{rule} random-hash
The hash h of whole numbers x₁, …, xₙ is a whole number below 2³², computed with every product taken modulo
2³², every xor and shift on 32-bit numbers, and `>>` the shift that fills with zeros. For a seed
value s, a site p and a whole number k, u(s, p, k) = h(s, p, k) / 2³², a number from 0 up to 1,
never 1.

    h = 0x811c9dc5
    for each x, in order:
        h = (h xor (x mod 2³²)) × 0x01000193
        h = h xor (h >> 15)
        h = h × 0x2c1b3c6d
        h = h xor (h >> 12)
        h = h × 0x297a2d39
        h = h xor (h >> 15)
```

Since only each x modulo 2³² enters the hash, two seed values that are equal modulo 2³², such as 0,
2³² and -2³², result in the same random values.

This rule exists so that every runtime turns the same hash into the same random value.

```{rule} random-values
With s the value of the seed and p the site:

- `(rand)` is u(s, p, 0), and `(rand lo hi)` is lo + u(s, p, 0) × (hi - lo): a real from `lo` to
  `hi`.
- `(rand-int lo hi)` is lo + ⌊u(s, p, 0) × (hi - lo + 1)⌋: an int from `lo` to `hi`, both included.
- `(choice xs)` on a list of n items, n at least 1, is the item at position ⌊u(s, p, 0) × n⌋.
- `(shuffled xs)` is the items of `xs` in a new order: for i from n - 1 down to 1, the items at
  positions i and ⌊u(s, p, i) × (i + 1)⌋ are swapped.
- `(next-seed s)` is h(s, 0x9e3779b9).
```

This rule exists because a seed may change while drawing, so the compiler must never compute a random value ahead of time.

```{rule} random-never-folded
A random value is known only while drawing ({doc}`binding-time`).
```

So the compiler never computes or folds a random value
({numref}`compiler-never-acts-while-drawing`). By {numref}`random-values`, for one .mtpc, the same
values of the seeds result in the same random values, on every refresh and in every browser, and
when a seed holds a new value, every random value that uses it is computed again ({doc}`reactivity`).
Since the sites are counted when compiling, a change to the source that adds or removes a call of a
random function before another call changes the site of the later call, and with it the value of
the later call.

`dice-roll` is an animation declared in the file rand ({ref}`stdlib-rand`). `(dice-roll s)`
creates a movement that writes `(next-seed s)` to the seed `s`, and `(dice-roll)` is
`(dice-roll d)`, with `d` the default seed ({numref}`default-seed`). Such a write is a roll.
By {numref}`random-values`, a roll changes the random values that use `s`, and no others.

A call of `rand`, `rand-int`, `choice` or `shuffled` inside the body of a function is a compile error.
A free variable may start at a random value with `free@`, and then does not update when the seed
changes.

```{mtp-example}
; every dot is drawn from the seed dots and the site of its rand
(import rand rand roll-dice)
(rand-seed dots 7)
(scene s
  (foreach i 12
    (circle_ (pos [(rand 0 10) (rand 0 4)]) (r 0.2) (fill #'teal'))))
(canvas v (x 0) (y 0) (width 10) (height 4) s)
(button roll (animation (roll-dice dots)) (label 'Roll'))
```

:::{admonition} Code differs
:class: note
The compiler names `dice-roll` `roll-dice`, `choice` `pick` and `shuffled` `shuffle`, as the live example
above does, and writes a control's movement as `(animation …)`.

The type `rand-seed` is an int of at least 0 (`RAND_SEED`, mathterpiece/types.py, line 143), so a
seed that is below 0 is a compile error. mtp-ydd4.7.30.
:::

## Equality

`(!= a b)` is true exactly when `(= a b)` is false.

This rule exists so that the compiler rejects an `=` whose result could only ever be false, or that would compare things with no equality.

```{rule} equality-operands
`(= a b)` and `(!= a b)` are a compile error unless one side's type is a {term}`subtype` of the other's or
one side is `none`, and on a type that includes a function, a movement or an animation. A list of two
numbers is not converted to a point: `(= p xs)`, with `p` a point and `xs` a list of ints, is a compile
error.
```

This rule exists to fix when two values are equal, so that every compiler and runtime give the same result.

```{rule} equality-by-content
Primitives are compared by content, and objects by identity. `=` and `!=` never result in `none`:

| Type | `(= a b)` is true when |
|---|---|
| `none` | both are `none`. `(= none x)` is false for every `x` that is not `none` |
| `int`, `ratio`, `real` | the two are the same number, exactly: 0 and -0 are equal. An int or a ratio compared with a real first becomes the nearest real, as in arithmetic ({numref}`number-result-types`), so `(= a b)` is true exactly when `(- a b)` is 0: `(= 1/3 0.3333333333333333)` is true |
| `complex` | both parts are equal. A complex whose second part is 0 equals the real of its first part |
| `bool`, `string`, a choice | the two are exactly the same |
| `point`, `list[T]` | they have the same length, and the items at each position are equal |
| `color` | they are the same color: `(= ink #'#000080')` is true with `(color ink #'navy')`. A light-dark color equals another when both of its modes do, and a color with the same value in both modes is one color. A token is compared by its value in the {term}`live model`, never by a value that the page's CSS sets for it |
| `font` | every part is equal |
| a shape, a group, a record, a formula, a term and every other object | the two are the same object. Two circles with the same attributes are not equal |
```

Since `=` on reals is exact, `(= (+ 0.1 0.2) 0.3)` is false: the sum is 0.30000000000000004.

:::{admonition} Code differs
:class: note
The compiler accepts `=` and `!=` with every type (mathterpiece/compiler.py, line 6443), so
`(= sind sind)` and `(= t t)` for a transition `t` compile. While drawing, `equal`
(web/src/builtins.ts, line 258) compares functions with `===`, and the runtime makes a new
JavaScript function for each read of a function (web/src/runtime.ts, `functionValue` and
`builtinValue`), so `(= f f)` is false. mtp-08wd.4.
:::

### Matching

The runtime uses a separate, tolerant comparison to check whether the scene is in a state. It is
not equality.

This rule exists so that the runtime can recognize a value that a play or a stepper reached, even after small errors of rounding.

```{rule} matching
Two values {term}`match` when they are equal, except that two reals match when they differ by at most
10⁻¹² or by at most a millionth of the larger one's size, and points and lists of the same length match
when their items do. Only the runtime matches values: no form gives whether two values match.
```

The runtime matches values to read the step of a play or a stepper from the scene, and to check
whether the free variables and attributes that the `on-view` of a canvas writes to still hold their
values from page load.

While drawing, the runtime uses `=` to skip writes: a write of a value equal to the current one is
skipped, and nothing that depends on it is computed again.

(termination)=
## Termination

A function may call itself, directly, through other functions, or through a function value
({numref}`self-reference`). There are no other loops: the number of copies of a `foreach` is
known when compiling, and `range` results in at most 1,000,000 items. So the only computation that
could go on without end is a chain of calls. When folding, every chain ends at the
{term}`call depth limit`. How a chain ends while drawing is the open question Q-evaluation-13 below.

This rule exists so that a function that calls itself can never run forever, when compiling or while drawing.

```{rule} call-depth-limit
The depth of a call of a function declared with `func` or written with `fn` is 1 plus the number of such
calls still being computed when it starts. `max-call-depth`, the call depth limit, is 256. A call known in
the prove step whose folding would go deeper is a compile error of the prove step
({numref}`step-rejects-or-passes`).
```

So with `(func[int] down ((int m)) (if (<= m 0) 0 (+ 1 (down (- m 1)))))`, `(down 255)` is folded
to 255, and `(down 256)` is a compile error, since its innermost call has a depth of 257. A
function is recursive when its name is used in its body, or in the body of a function whose name is
used there, at any depth.

By {numref}`no-errors-after-loading`, no call while drawing may make a {term}`component` fail. What
happens while drawing to a call of a recursive function whose depth would pass `max-call-depth` is
an open question:

:::{admonition} Open question Q-evaluation-13
:class: warning
A call of a recursive function whose arguments are known only while drawing may reach a depth
above `max-call-depth`, and no rule may make that an error while drawing
({numref}`no-errors-after-loading`). The same holds for a call in the body of a `foreach` or a
motif that reads the binding of the `foreach` or a parameter of the motif: it is not known in the
prove step ({numref}`check-bodies-once`), so {numref}`call-depth-limit` does not reject it, and its
arguments are known only once the expand step has made the copies and the shapes declared with
each motif. The options:

- (a) The compiler rejects a recursive function unless the {term}`prover` can prove that every call
  of it stays within `max-call-depth`.
- (b) mtp has no recursion: a function may not call itself, directly or through other functions,
  and the depth limit goes away.
:::

A computation can run for a long time, and the spec sets no limit on time.

:::{admonition} Code differs
:class: note
- **When compiling.** A call with known arguments is folded by compiling its body again with those
  arguments. When the nesting is too deep for Python, at a depth of about 80, the compiler catches
  the `RecursionError` and leaves the call to the runtime (mathterpiece/compiler.py, `fold_call`,
  line 2530). Working out the range of a call does the same (line 2013). So `(down 80)` above is
  folded, while `(down 81)` is not, and `(down 256)` compiles.
- **While drawing.** There is no limit on the depth of calls (web/src/runtime.ts, `call`, line
  1282). Each call uses the JavaScript call stack, and a call that is too deep throws `RangeError:
  Maximum call stack size exceeded`, which is drawn in place of the {term}`view` or the control
  (web/src/elements.ts, `guard`, line 324). In Node 26 this happens past a depth of about 1740,
  and the depth depends on the browser. This breaks {numref}`no-errors-after-loading`.

mtp-ydd4.7.15.
:::

(folding-and-drawing)=
## The same value when folded and while drawing

This rule exists so that whether the compiler folds an expression never changes what the page shows.

```{rule} same-value-at-both-times
An expression evaluates to the same value when it is folded as when it is computed while drawing,
for the same values of what it reads.
```

This rule exists so that the compiler and every runtime compute each built-in function to the same bits.

```{rule} correctly-rounded-reals
Each binary64 number in the result of a built-in function or an operator is the binary64 number nearest
to the exact value at its arguments, ties going to the one whose last bit is 0, at both times.
```

This holds for `+`, `-`, `*`, `/`, `sqrt`, the trigonometric functions in radians and in degrees,
`exp`, `log`, `^`, `mod`, `dist`, `polar`, `lerp`, `sum`, `rand`, and the conversions between
degrees and radians. So `(sind 30)` is exactly 0.5, the functions in degrees result in exact values at
multiples of 90 degrees, and `sum` results in the exact sum rounded once, not in the result of
adding its items one at a time.

Rounding to the nearest binary64 number never puts two numbers in the opposite order, and neither
does clamping to the number limit ({numref}`number-limit`). So when the
prover works out a bound of a range with the same functions, at the ends of an interval on which
the exact function only rises or only falls, or as an exact value that is a binary64 number, such
as 1 for the largest value of `sin`, every value computed at either time lies within the range.
The prover therefore does not widen the ranges that it works out ({numref}`prover-finds-ranges`).

:::{admonition} Code differs
:class: note
The two programs differ in these places, beyond what the rules above allow:

| Where | When compiling | While drawing | Bead |
|---|---|---|---|
| ratios, and ints beyond 2⁵³ | exact | binary64 | mtp-ydd4.7.13 |
| `round` of 10²⁸ or more | the compiler stops | rounds | mtp-6yga |
| the channels of a mixed color | halves to even | halves up | mtp-nk2w |
| the functions on reals other than `+`, `-`, `*`, `/` and `sqrt` | Python's `math` module, which is not correctly rounded | ECMAScript `Math`, which is not correctly rounded | mtp-ydd4.7.38 |
| `sum` of reals | adds the items one at a time | adds the items one at a time | mtp-ydd4.7.38 |
| recursion | folded up to a depth of about 80 | computed up to the stack of the browser | mtp-ydd4.7.15 |
| `mod` of reals | Python's `%`, which is exact | `a - b × ⌊a / b⌋`, so `(mod 5.5 0.1)` is 0 and not 0.0999999999999997 | mtp-ydd4.7.38 |
| the functions in degrees, for large angles | converted to radians first, so `(cosd (+ 1e15 90))` is 0.98478… | `(x × π) / 180` first, so it is 0.98512… | mtp-ydd4.7.38 |

For `(cosd (+ 1e15 90))` the exact value is the cosine of 10 degrees, 0.98481…, so both times
are wrong in the fourth digit. Elsewhere the two differ in the last bits, which
{numref}`correctly-rounded-reals` does not allow: `(sind 30)` is 0.49999999999999994 at both times,
and `sind` differs on 776 of 2,885 angles from -360 to 360 degrees,
a quarter of a degree apart, and `sin`, `cos`, `tan`, `exp`, `log`, `atan`, `asin`, `acos` and
`dist` differ in the last bit on 1 to 41 percent of 1,031 values from -8 to 8. Formatting with a
format spec, `round`, and `sqrt` agreed on every value tried.
:::
