(well-formedness)=
# Well-formedness

A {term}`world model` whose {term}`names <name>` resolve ({ref}`scope`) and whose
{term}`expressions <expression>` have types ({doc}`types`) must still pass the rules of this page:
its dependencies make no cycle, its writers write only what may be written, the moves that run
together do not write the same value, and every {term}`condition` is proved. All of them are
checked in the prove step ({numref}`compile-steps`), and a source that breaks one is a
{term}`compile error`. The last section defines the {term}`prover`: exactly what it proves, and the
{term}`ranges <range>` with which it proves it.

This page specifies the language.

## No cycles

```{rule} no-dependency-cycles
The value of every bound variable and attribute is computed from the values that its expression
reads ({doc}`reaction`). These reads make no cycle: no bound value reads itself, directly or
through other bound values.
```

By {numref}`declare-before-use`, an expression reads only declarations and bindings that come
before it, so a cycle could only come from a read inside the {term}`form` of the declaration or the
binding that is read. The rules of today for such reads are below. An animation uses only animations
declared before it, so no animation uses itself ({numref}`sugar-rewrites`), and no file imports itself
({numref}`import-same-file`). A function may call itself: a call is not a read of a value, and how deep a chain of calls goes is defined in
{numref}`call-depth-limit`, with the case of drawing still open (Q-evaluation-13).

```{rule} self-reference-today
These rules hold for a use of a name inside the form that declares or binds it:

1. A function may call itself in its own {term}`body`.
2. A variable, a `let` name and a parameter never read themselves: `(real k (+ k 1))` is a compile
   error.
3. A shape, a variant instance and a motif instance never read one of their own attributes in
   their own form, whether directly, in a `free@` starting value, through a position on their
   group known when compiling, or through a function.
4. A shape in a group, at any depth, never reads the group whole in its own form: an attribute of
   every member, such as `g.x`, a collection function over the group or over `g.members`, a
   function given `g.members`, or a member by a position known only while drawing. `(count g)` and
   `g.length` may be read. The count and the {term}`list` of a `foreach` inside the group never read
   the group.
5. A container never reads itself in its own `clip` or in its own `(defaults …)`, also once the
   defaults are given to its members ({numref}`container-defaults`).

Each read that items 2 to 5 forbid is a compile error.
```

The other cases of a declaration that reads itself or its container, such as an `exists-when` that
reads its own shape or a member that reads the `translate` of its group, are part of the same
redesign (Q-scope-1), and this spec does not define them yet.

## What a writer may write

The {term}`controls <control>` and the {term}`listeners <listener>` are the writers
({doc}`concurrency`). A writer writes its target, and the moves of its animation write theirs.

```{rule} writable-targets
The target of a writer and of a move is a name: a variable, an attribute of a shape, of an
instance or of a term, or a member of a record or a formula, with `(name s)` allowed in place of
a name ({numref}`names-from-values`). A target may be written only when it is free
({doc}`world-model`), its type does not hold `(const)`, it is not a token (a variable of type
`color` or `font`), and it is not fixed by a variant ({numref}`motif-and-variant-types`). Besides:

- A name that is not a variable or an attribute, such as a group or a record by its name alone,
  is never a target.
- A target that stands for several values, as {doc}`concurrency`, section "Values", gives, is
  writable only when each of those values is: a `pos`, an attribute of a group or an instance that
  is not its own, and the `x`, the `y` and the `pos` of a line, a triangle, a polyline, a polygon
  and a bezier. An attribute of a container with no members is never a target.
- A member of a group chosen by a position is chosen by a position known when compiling.
- A move of an `on-show` or an `on-hide` writes the stand-in of its shape, so it may write an
  attribute of that shape that is bound ({doc}`lifecycle`).

Every other target is a compile error.
```

So `(slider s (move m (from 0) (to 1)))` with `(real m (* 2 k))` is a compile error, and so is a
move of a `(const)` variable or of a color variable. Two writers may write the same value: that is
not an error, and {doc}`concurrency` defines what happens when they meet.

```{rule} written-values
Each value that a write gives must {term}`fit` the type of its target ({numref}`fits`), with the
comparisons, the wraps and the choices of the conditions of that type left out, since the write
brings the value into those ({numref}`writes-into-constraints`). This holds for the `from` and the
`to` of a move and of a movement, the `to` of the move of an `on-drag`, and the values of a
toggle and a slider. A value whose type includes `none` is written only into a target whose type
includes `none`.
```

So `(move k (to (* 3 a)))` into `(real k 1 (>= 0) (<= 2))` compiles, and the write clamps each
value to 0 or 2. `(move n (to 2.5))` into an `int` is a compile error, while the values between
the ends of a move into an {term}`int` are rounded. A `(length n)` is kept, so a move of a list
declared `(length 2)` to a list of length 3 is a compile error.

(writer-conditions)=
```{rule} writer-guards
Each guard of a control or a listener ({numref}`bodies-table`) is a comparison `(OP A B)`, OP
one of `<`, `<=`, `>` and `>=`, in which one side is a read of a variable or an attribute that the
writer writes, and the other side, the limit, does not depend on that variable or attribute,
directly or through bound values. Every other guard is a compile error.
```

What a guard does to a write is defined in {doc}`reaction`. A writer that writes the `pos` of a
shape writes its `x` and its `y` ({numref}`writable-targets`), so its guards may limit either,
as `(on-drag c c.pos (<= c.x 5) (>= c.y 0))`, and `c.pos.x` and `c.pos[0]` are `c.x`.

:::{admonition} Code differs
:class: note
- The compiler checks the end of a move against its target without the constraints of the target
  (`_loose` in `compiler.py:5794`, `checked`), so a move of a list declared `(length 2)` to a list
  of three items compiles.
- A condition is refused only when its limit reads the target directly (`compiler.py:4486`,
  `condition`), so a limit that reads it through a bound variable compiles.

Bead mtp-ydd4.7.44.
:::

## Moves that run at the same time

```{rule} moves-at-once
Two parts of one `at-once` that write the same value at times that overlap are a compile error.
The values that a move writes are those of {doc}`concurrency`, section "Values". The times are
these:

- Each part of an `at-once` starts when the `at-once` starts, and the moves inside it start at the
  times that {doc}`time` gives them.
- A move writes from its start up to its start plus its duration, and a loop that never ends
  writes forever.
- Two times overlap when they start at the same instant, or when each starts before the other ends.
```

So `(at-once (move k (to 2) (duration 1)) (move k (to 3) (duration 1)))` is a compile error, and
`(at-once (move k (to 0) (duration 0)) (in-order (wait 2) (move k (to 1))))` is not. For a
polyline `pl`, `(at-once (move pl.x (to 3)) (move pl.points (to [[0 0] [2 0]])))` is a compile
error, and `(at-once (move pl.x (to 3)) (move pl.y (to 3)))` is not. A container's `translate` and
`transform` are its own, so `(at-once (move g.translate (to [1 1])) (move c.x (to 3)))` is allowed
for a member `c` of `g`.

## The prover

```{rule} prover-proves
The prover proves exactly these, and nothing else:

1. The type of every expression, and that it fits where it is given ({numref}`form-types`).
2. That every value meets the conditions of the type expected where it is given
   ({numref}`constraint-proof`).
3. Which operations may give `none`, and so which types include `none` ({numref}`may-give-none`),
   and that an operation whose inputs are known gives no `none` ({numref}`none-at-known-inputs`).
4. An upper bound of the count, or of the length of the list, of a `foreach` that is known only
   while drawing ({numref}`foreach-bounded-length`).
5. That a name built from a value names a declaration that fits ({numref}`names-from-values`).
6. The {term}`call depth limit` of a call known in the prove step ({numref}`call-depth-limit`).
7. The rules of this page before this section.

For numbers, its only reasoning is the ranges of {numref}`ranges` and {numref}`range-rules`, and
the narrowing of {numref}`if-narrowing`. It proves each body once ({numref}`prove-bodies-once`).
```

So the prover never uses a relation between two values: in `(/ 1 (- k k))` the divisor may be 0 for
the prover, although it is always 0. It never counts, never searches for a value, and narrows a
range only by the conditions of {numref}`if-narrowing`.

```{rule} ranges
A range is a closed interval of {term}`reals <real>`, from a lower end to an upper end, each of them
an int, a {term}`ratio` or a binary64 number, the lower at most the upper. The prover works out a
range for every expression of type `int`, `ratio` or `real`, with or without `none`. The range of an
expression holds every value other than `none` that the expression can give, when
{term}`folded <folding>` and while drawing.
```

The prover works out each end of a range with the functions that {term}`evaluation` uses: exactly
for ints and ratios ({numref}`number-types`), and with the functions of
{numref}`correctly-rounded-reals` for reals. So by the argument that follows
{numref}`correctly-rounded-reals`, a range worked out at the ends of the ranges of the inputs holds
every value that either time computes. A strict bound gives the range the nearest value past its
number that the type holds, as {numref}`if-narrowing` does: the range of `(real k (> 0))` is from
the smallest binary64 number above 0 to `1e150`, so `(/ 1 k)` is a `real`, and the range of
`(int n (> 0))` is from 1 to 10¹⁵⁰. A ratio has no smallest value above a number, so for a ratio,
`(> c)` gives the end c, as `(>= c)` does.

```{rule} range-rules
The range of each expression is the following. Where the table gives several ranges, the range is
the part that they share.

| Expression | Its range |
|---|---|
| a number known in the prove step | from the number to the number |
| the range of a type | the ends that its comparisons give: c for a `(>= c)` and a `(<= c)`, and for a `(> c)` and a `(< c)` the nearest value past c that the type holds, which is the next int for an int, the next binary64 number for a real, and c for a ratio. From lo to hi for `(wrap lo hi)`, and the end of the {term}`number limit` for a side with no bound ({numref}`number-limit`) |
| a read of a free variable or attribute | the range of its type |
| a read of a bound variable or attribute | the range of its expression, and the range of the conditions of its declared type, each side with no bound left out. A read through a `translate` or a `transform` ({doc}`world-model`): the range of its type |
| a parameter, in its body | the range of its type ({numref}`prove-bodies-once`), and for a parameter of an `fn` given to a {term}`built-in` function, the range that {doc}`stdlib` gives it |
| a `let` name | the range of its value |
| the name of a `foreach` over a count X | from 0 to the upper end of the range of X, minus 1 |
| the name of a `foreach` over a list | the range of the items of the list |
| an item of a list | the range of the item type of the list |
| `(- A)` | from minus the upper end of A to minus its lower end |
| `(+ A B …)` | from the sum of the lower ends to the sum of the upper ends |
| `(- A B …)` | from the lower end of A minus the upper ends of the others to the upper end of A minus their lower ends |
| `(* A B …)` | the smallest and the largest of the products that take one end of the range of each argument |
| `(/ A B)` | when the range of B does not hold 0, the smallest and the largest of the four quotients of the ends. When it holds 0, the whole number limit |
| `(mod A B)` | from the smaller of 0 and the lower end of B to the larger of 0 and the upper end of B |
| `(^ A B)` | when the lower end of A is 0 or more, the smallest and the largest of the four powers of the ends. When B is known in the prove step and is an int n, the smallest and the largest of the powers n of the ends of A, and 0 when the range of A holds 0 and n is above 0. Otherwise the whole number limit |
| `(abs A)` | from 0 to the larger of minus the lower end and the upper end, when the range of A holds 0, and otherwise from the smaller to the larger of the absolute values of the ends |
| `(if C A B)`, `(or? A D)` | from the smaller of the lower ends to the larger of the upper ends. With C known in the prove step, the range of the branch taken. The range of each branch of an `if` is worked out with the ranges that {numref}`if-narrowing` gives, and a branch that never runs by that rule is left out |
| a call of a function declared with `func`, outside its own body, not folded | the range of its body worked out again with the range of each parameter being the range of its argument, and the range of its result type. This only gives a range: the body is proved once |
| a call of a function inside its own body | the range of its result type |
| a call of another built-in function | the range that {doc}`stdlib` gives for it |
| any other expression | the range of its type |

Every range is clamped to the number limit, as the values of the expression are
({numref}`number-limit`): an end beyond it is replaced by the end of the number limit, 10¹⁵⁰ or
-10¹⁵⁰ for an int or a ratio, and `1e150` or `-1e150` for a real. The whole number limit is the
range from the lower end to the upper end of the number limit. Each end in the table that is worked
out from several ends, such as the sum of the lower ends, is one call of the operation on those
ends, and is clamped once.
```

The item type of a list {term}`literal` whose items are not all known, and whose items all have
ranges, holds `(>= lo)` and `(<= hi)`, lo and hi being the smallest lower end and the largest upper
end of the items. So `(map g (fn p (dist o p)))` is a `list[(real (>= 0))]` ({doc}`stdlib`).

With `(real k 1 (>= 0) (<= 10))`, the range of `(* 2 k)` is 0 to 20, and of `(- 5 k)`, -5 to 5. With
`(func clamp ((real x) (real lo) (real hi)) (min hi (max lo x)))`, `(clamp x 0 1)` has the range 0
to 1 whatever `x` is, by the row for a call.

```{rule} may-give-none
The type of an operation that is not folded includes `none` when the ranges of its arguments, each
taken on its own, hold an input at which it gives `none` by {numref}`operations-that-give-none`.
For a part of a list or a group:

| Operation | Its type includes `none` unless |
|---|---|
| `xs[i]`, an item of a list | the length n of `xs` is known ({numref}`known-lengths`), and the range of `i` lies from -n to n - 1 |
| `g[k]`, a member of a group by an int | the range of `k` lies from -n to n - 1, n being the number of members |
| `g[k]`, a member of a group by a {term}`string` | the type of `k` is a {term}`choice type` whose choices are all names of members of `g` |
```

So with `(real k 1)`, `(/ 1 k)` is a `real|none`, and with `(real k 1 (>= 1))`, a `real`. With
`(int f 0 (>= 0) (<= 3))`, `xs[f]` on a bound list of four items is never `none`. With
`(type side string (one-of 'left' 'right'))` and a group `arms` whose members are named `left` and
`right`, `arms[s]` is never `none` for a `side` `s`.

```{rule} constraint-proof
A value given where the expected type holds a condition C meets C when one of these holds:

- C is a modular type, which every value meets once brought in ({numref}`modular-types`).
- The value is known in the prove step and meets C.
- The type of the value fits the expected type with C as its only condition ({numref}`fits`).
- C is a comparison, and the range of the value lies inside it: its lower end is at least c for
  `(>= c)` and above c for `(> c)`, and its upper end is at most c for `(<= c)` and below c for
  `(< c)`.

When a value does not meet C:

| The value | Then |
|---|---|
| a value known in the prove step | a compile error |
| the value of a bound variable or attribute | {numref}`prover-finds-ranges` |
| an argument of a call, of an instance or of a use of an animation | a compile error |
| the body of a function declared with a result type R | when R includes `none`, a call gives `none` where the value of the body breaks C, and the write step writes the `check` for it. Otherwise a compile error |
| an item of a list literal whose item type is expected | a compile error |
| a value that a writer writes | no proof: {numref}`written-values` |
```

So `(real k 5 (<= 3))` is a compile error. With `(real a 1)` and
`(func g (((real (>= 0)) x)) (* 2 x))`, `(g a)` is a compile error, and `(g (abs a))` is not. With
`(func[(real|none (>= 0))] h ((real x)) x)`, `(h a)` is `none` while `a` is below 0.

```{mtp-example}
; k is at least 1, so the prover proves that 1/k is never none
(real k 2 (>= 1) (<= 5))
(scene s (circle c (r (/ 1 k)) (fill #'teal')))
(canvas v (x -1.2) (y -1.2) (width 2.4) (height 2.4) s)
(slider size (move k (from 1) (to 5)) (label 'k'))
```

### Narrowing in an `if`

```{rule} if-narrowing
A branch of an `if` is proved only for the values for which it runs. In `(if (OP N c) A B)`, where
N is a name whose range the prover works out, c is a number known in the prove step, and OP is one
of `=`, `!=`, `<`, `<=`, `>` and `>=`, the range of N in A is the part of its range for which the
comparison holds, and in B the part for which it fails. With lo and hi the ends of the range of N:

- For an int N, the part in A is from the smallest to the largest of the ints from lo to hi for
  which the comparison holds, and the part in B is the same for the ints for which it fails. So
  with c an int from lo + 1 to hi, `(< N c)` gives A the upper end c - 1, and `(!= N c)` changes
  the range only when c is lo or hi.
- For a real N, a part in which N is at most c is from lo to the smaller of hi and c, and a part in
  which N is at least c is from the larger of lo and c to hi. A part in which N is below c is from
  lo to the smaller of hi and the largest binary64 number below c, and a part in which N is above c
  is from the larger of lo and the smallest binary64 number above c to hi. So `(> N 0)` gives A a
  range that does not hold 0. The part in which N is c is from c to c, and the part in which N is
  not c is the range of N with an end that equals c moved to the next binary64 number inside it.
- For a ratio N, a part in which N is below c, or at most c, is from lo to the smaller of hi and c,
  and a part in which N is above c, or at least c, is from the larger of lo and c to hi. The part in
  which N is c is from c to c, and the part in which N is not c is from lo to hi.
- When a part holds no int, for an int N, or when its lower end is above its upper end, or when lo
  and hi are both c in the part in which N is not c, the branch never runs, and the prover proves
  nothing in it.

The range of N changes only for the reads of N in A and in B that read the same declaration or
binding as the N of the condition. A value that is computed from N outside the `if`, such as a
`let` name, keeps its range. In an `if` inside A or B, the range of N is the part that the outer `if` gives.
`(OP c N)` narrows as the comparison with N first that holds for the same values: `(< c N)` as
`(> N c)`, and `(= c N)` as `(= N c)`. `cond`, `when`, `and` and `or` narrow through their
{term}`rewrites <rewrite>` into `if` ({numref}`sugar-rewrites`). No other condition narrows a range.
```

In the source below, the body of the `foreach` is proved for `k` from 0 to 59
({numref}`prove-bodies-once`). So `k` in the second branch of `(if (= k 0) …)` is from 1 to 59,
and `@'dot-{(- k 1)}'` names one of the copies `dot-0` to `dot-58` ({numref}`names-from-values`).

```mtp
(int n 24 (>= 1) (<= 60))
(scene s
  (foreach k n
    (circle @'dot-{k}' (r 0.1)
      (pos (if (= k 0) [3 0] (* 0.9 @'dot-{(- k 1)}'.pos))))))
```

With `(int k 1 (>= 0) (<= 5))`, `(if (< k 3) A B)` gives `k` the
range 0 to 2 in A and 3 to 5 in B, and `(if (> k 7) A B)` never runs A. With `(real x 1)`,
`(if (> x 0) (sqrt x) 0)` is a `real`, since `x` in the first branch is from the smallest binary64
number above 0 to `1e150`. In `(if (> x 0) (/ 1 x) 0)`, `x` in the first branch has the same range,
which does not hold 0, so `(/ 1 x)` is a `real` there. In `(if (and (> k 0) (< k 3)) A B)`, the condition is the
`if` of the rewrite of `and`, which is not a comparison, so the range of `k` in A is not narrowed.
`(if (< 0 k) A B)`, with the name on the right, does not narrow either.

:::{admonition} Code differs
:class: note
The compiler has no narrowing. So
`(func[real] f (((int (>= 0) (<= 5)) k)) (if (= k 0) 0 (/ 1 k)))` is the error "this value may be
none" at `(/ 1 k)`, although `k` in that branch is from 1 to 5. examples/spiral-of-copies.mtp
compiles today only because the compiler proves each copy of a `foreach` with its own value of `k`
(mtp-08wd.1). Bead mtp-ydd4.7.55.
:::
