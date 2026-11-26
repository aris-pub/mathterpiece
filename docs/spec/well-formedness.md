(well-formedness)=
# Well-formedness

A source whose {term}`names <name>` resolve ({ref}`scope`) and whose
{term}`expressions <expression>` have types ({doc}`types`) must also meet the rules of this page:
its dependencies make no cycle, its writers write only to containers that may be written to, the moves
that run together do not write to the same container, and every {term}`condition` is proved. The
compiler checks all of them in the prove step ({numref}`compile-steps`), and a source that breaks
one is a {term}`compile error`. The last section defines the {term}`prover`: exactly what it
proves, and the {term}`ranges <range>` that it uses to prove it.



## No cycles

This rule exists because the runtime computes a bound container from the containers that it reads, and a cycle gives that computation no place to start.

```{rule} no-dependency-cycles
The value of every bound container is computed from the values that its expression reads
({doc}`reactivity`). These reads make no cycle: no bound container reads itself, directly or through
other bound containers.
```

By {numref}`declare-before-use`, an expression reads only declarations and bindings that come
before it, so a cycle could only come from a read inside the {term}`form` of the declaration or the
binding that is read. The rule below lists such reads. A call of a function is not a read of a
container, so a function that calls itself makes no cycle. The depth of a chain of calls is limited
by {numref}`call-depth-limit`.

This rule exists because a form that reads what it declares could need a value before there is one, and the compiler must reject those cases before the page opens.

```{rule} self-reference
These rules hold for a use of a name inside the form that declares or binds it:

1. A function may call itself in its own {term}`body`.
2. A variable, a `let` name and a parameter may not read themselves: `(real k (+ k 1))` is a
   compile error.
3. A shape in a group, at any depth, may not read the whole group in its own form: an attribute of
   all the members, such as `g.x`, a list function over `g.members`, a call of a function with
   `g.members` as an argument, or a member chosen by a position known only while drawing. It may
   read `(count g.members)`. The count and the {term}`list` of a `foreach` inside
   the group may not read the group.
4. The `clip` and the `(defaults …)` of a collection may not read the collection, also after the
   defaults are given to its members ({numref}`collection-defaults`).

A shape may read its own attributes, by
its name or through the name that the `(as N)` of its motif binds, as long as
{numref}`no-dependency-cycles` holds.
```

Every other read of a declaration in its own form, or of its collection, such as an `exists-when`
that reads its own shape or a member that reads the `shift` of its group, is limited only by
{numref}`no-dependency-cycles`.

## What a writer may write to

The {term}`controls <control>` and the {term}`listeners <listener>` are the writers
({doc}`concurrency`). A writer writes to its target and to the targets of the moves in its movements.

This rule exists because the runtime keeps a bound or const container equal to its expression, so a write to one would have no effect.

```{rule} writable-targets
The target of a writer or of a move is a free container ({numref}`variables`), written as a name
or a qualified name ({numref}`what-a-name-means`). Also:

- A target that stands for several containers ({doc}`concurrency`, the part "Containers") may be
  written to only when each of them is free. Such targets are a `pos`, an attribute of a group that
  stands for the attributes of its members, and the `x`, the `y` and the `pos` of a line, a
  triangle, a polyline, a polygon and a bezier. An attribute of a collection with no members may not
  be a target.
- An item of a list, and a member of a group chosen by its position, must be chosen by a position
  known when compiling. Writing to an item puts a new list into the container that holds the list.
- A move of an `on-show` or an `on-hide` writes to the stand-in of its shape, so it may write to an
  attribute of that shape that is bound ({doc}`lifecycle`).

Every other target is a compile error.
```

So `(slider s m (from 0) (to 1))` with `(real m (* 2 k))` is a compile error, and so is a move of a
const variable. Two writers may write to the same container, and
{doc}`concurrency` defines what happens then.

This rule exists to specify which part of a write the compiler checks, and which part the runtime enforces.

```{rule} written-values
The compiler checks a written value against the type of its target without its conditions. Each
write enforces the conditions while drawing ({numref}`writes-to-conditions`).
```

So with `(real k 1 (>= 0) (<= 2))`, `(move k (to (* 3 a)))` compiles, and a value below 0 is
written as 0, and a value above 2 as 2. With an {term}`int` `n`, `(move n (to 2.5))` is a compile
error, since 2.5 is not an int, and the values between the ends of a move to `n` are rounded. A
move to a list declared `(length 2)` with a `to` of length 3 compiles, and no list of length 3 is
written.

This rule exists because the runtime clamps each write to the guards of its writer, which is possible only when each guard bounds the written container.

(writer-conditions)=
```{rule} writer-guards
Each guard of a control or a listener ({numref}`bodies-table`) is a comparison `(OP A B)`, with OP one
of `<`, `<=`, `>` and `>=`, one side a read of a container that the writer writes to, and the other
side, the limit, not depending on that container, directly or through bound containers. Any other
guard is a compile error.
```

What a guard does to a write is defined in {doc}`reactivity`. A writer that writes to the `pos` of a
shape writes to its `x` and its `y` ({numref}`writable-targets`), so its guards may limit either,
as in `(on-drag c c.pos (<= c.x 5) (>= c.y 0))`, and `c.pos.x` and `c.pos[0]` are the same as `c.x`.

:::{admonition} Code differs
:class: note
- The runtime does not refuse a list of the wrong length: `constrain` brings only a single number
  into its conditions ({doc}`evaluation`, the note under {numref}`number-limit`).
- The compiler refuses a guard only when its limit reads the target directly (`compiler.py:4486`,
  `condition`), so a limit that reads the target through a bound variable compiles.

Bead mtp-ydd4.7.44.
:::

## Moves that run at the same time

This rule exists because two moves of one score that write to the same container at once would leave the value of the container undefined.

```{rule} moves-at-once
Two moves of one score that write to the same container ({doc}`concurrency`, "Containers") at times
that overlap are a compile error. A move writes from its start, set by {doc}`time`, up to its start plus
its duration, and a loop that never ends writes forever. Two times overlap when they start at the same
instant, or when each starts before the other ends.
```

So `(at-once (move k (to 2) (duration 1)) (move k (to 3) (duration 1)))` is a compile error, and
`(at-once (move k (to 0) (duration 0)) (in-order (wait 2) (move k (to 1))))` is not. For a
polyline `pl`, `(at-once (move pl.x (to 3)) (move pl.points (to {[0 0] [2 0]})))` is a compile
error, and `(at-once (move pl.x (to 3)) (move pl.y (to 3)))` is not. The `shift` of a group is a
container of the group and not of its members, so `(at-once (move g.shift (to [1 1])) (move c.x (to 3)))`
is allowed for a member `c` of `g`.

## The prover

This rule exists to fix exactly what the prover proves, so that every conforming compiler accepts and rejects the same sources.

```{rule} prover-proves
The prover proves exactly these, and nothing else:

1. The type of every expression except a clause, and that it is a subtype of the type expected where
   it is written ({numref}`form-types`).
2. That every value meets the conditions of that type ({numref}`constraint-proof`).
3. Which operations may give `none`, and so which types include it ({numref}`may-give-none`), and that
   an operation with known inputs does not ({numref}`none-at-known-inputs`).
4. An upper bound of the length of a `foreach` that is known only while drawing
   ({numref}`foreach-bounded-length`).
5. That each `(name S)` is an object whose type is a subtype of the type expected where it is
   written ({numref}`names-from-values`).
6. That a call known in the prove step stays within the {term}`call depth limit` ({numref}`call-depth-limit`).
7. The rules of the sections above.

For numbers it uses only the ranges of {numref}`ranges` and {numref}`range-rules` and the narrowing of
{numref}`if-narrowing`, and it checks each body once ({numref}`check-bodies-once`).
```

So the prover never uses a relation between two values: the range of the divisor of
`(/ 1 (- k k))` holds values other than 0, although the divisor is always 0. The prover never
counts and never searches for a value.

This rule exists to define the ranges that the prover works with, which the rules after it use.

```{rule} ranges
A range is a closed interval of {term}`reals <real>`, its ends each an int, a {term}`ratio` or a
binary64 number, the lower at most the upper. The prover works out a range for every expression of
type `int`, `ratio` or `real`, or a union of one with `none`, holding every value but `none` that the
expression can take, folded or while drawing.
```

The prover works out each end of a range with the functions that {term}`evaluation` uses: exactly
for ints and ratios ({numref}`number-types`), and with the functions of
{numref}`correctly-rounded-reals` for reals. So by the argument after
{numref}`correctly-rounded-reals`, a range worked out at the ends of the ranges of the inputs holds
every value that is computed when folding and while drawing. By the row for the range of a type in
{numref}`range-rules`, the range of `(real k (> 0))` is from the smallest binary64 number above 0
to `1e150`, so `(/ 1 k)` is a `real`, and the range of `(int n (> 0))` is from 1 to 10¹⁵⁰. A ratio
has no smallest value above a number, so for a ratio, the end of `(> c)` is c, as for `(>= c)`.

This rule exists so that every compiler works out the same range for each expression.

```{rule} range-rules
The range of each expression is the following. Where the table lists several ranges, the range is
the part that they share.

| Expression | Its range |
|---|---|
| a number known in the prove step | from the number to the number |
| the range of a type | the ends set by its comparisons: c for a `(>= c)` and a `(<= c)`, and for a `(> c)` and a `(< c)` the nearest value past c that the type holds, which is the next int for an int, the next binary64 number for a real, and c for a ratio. From lo to hi for a modular type `(mod T lo hi)`, and the end of the {term}`number limit` for a side with no bound ({numref}`number-limit`) |
| a read of a free container | the range of its type |
| a read of a bound container | the range of its expression, and the range of the conditions of its declared type, each side with no bound left out |
| a parameter, in its body | the range of its type ({numref}`check-bodies-once`), and for a parameter of an `fn` passed to a {term}`built-in` function, the range that {doc}`stdlib` lists for it |
| a `let` name | the range of its value |
| the name of a `foreach` over a count X | from 0 to the upper end of the range of X, minus 1 |
| the name of a `foreach` over a list | the range of the items of the list |
| an item of a list | the range of the item type of the list |
| `(- A)` | from minus the upper end of A to minus its lower end |
| `(+ A B …)` | from the sum of the lower ends to the sum of the upper ends |
| `(- A B …)` | from the lower end of A minus the upper ends of the others to the upper end of A minus their lower ends |
| `(* A B …)` | the smallest and the largest of the products of one end of the range of each argument |
| `(/ A B)` | when the range of B does not hold 0, the smallest and the largest of the four quotients of the ends. When it holds 0, the whole number limit |
| `(mod A B)` | from the smaller of 0 and the lower end of B to the larger of 0 and the upper end of B |
| `(^ A B)` | when the lower end of A is 0 or more, the smallest and the largest of the four powers of the ends. When B is known in the prove step and is an int n, the smallest and the largest of the powers n of the ends of A, and 0 when the range of A holds 0 and n is above 0. Otherwise the whole number limit |
| `(abs A)` | from 0 to the larger of minus the lower end and the upper end, when the range of A holds 0, and otherwise from the smaller to the larger of the absolute values of the ends |
| `(if C A B)`, `(or? A D)` | from the smaller of the lower ends to the larger of the upper ends. With C known in the prove step, the range of the branch taken. The range of each branch of an `if` is worked out with the ranges that {numref}`if-narrowing` sets, and a branch that never runs by that rule is left out |
| a call of a function declared with `func`, outside its own body, not folded | the range of its body worked out again with the range of each parameter being the range of its argument, and the range of its result type. This row sets only a range: the body is checked once |
| a call of a function inside its own body | the range of its result type |
| a call of another built-in function | the range that {doc}`stdlib` lists for it |
| any other expression | the range of its type |

Every range is clamped to the number limit, as the values of the expression are
({numref}`number-limit`): an end beyond it is replaced by the end of the number limit, 10¹⁵⁰ or
-10¹⁵⁰ for an int or a ratio, and `1e150` or `-1e150` for a real. The whole number limit is the
range from the lower end to the upper end of the number limit. Each end in the table that is worked
out from several ends, such as the sum of the lower ends, is one call of the operation on those
ends, and is clamped once.

The item type of a `(list-of …)` whose items are not all known in the prove step, and whose items
all have ranges, holds `(>= lo)` and `(<= hi)`, lo and hi being the smallest lower end and the
largest upper end of the items.
```

So `(map g (fn p (dist o p)))` is a `list[(real (>= 0))]` ({doc}`stdlib`).

With `(real k 1 (>= 0) (<= 10))`, the range of `(* 2 k)` is 0 to 20, and of `(- 5 k)`, -5 to 5. With
`(func clamp ((real x) (real lo) (real hi)) (min hi (max lo x)))`, `(clamp x 0 1)` has the range 0
to 1 whatever `x` is, by the row for a call.

This rule exists to determine which operations may result in `none`, and so which types must include `none`.

```{rule} may-give-none
The type of an operation that is not folded includes `none` when the ranges of its arguments, each
taken on its own, hold an input at which it evaluates to `none` by
{numref}`operations-that-give-none`. For an item of a list and a member of a group:

| Operation | Its type includes `none` unless |
|---|---|
| `xs[i]`, an item of a list | the length n of `xs` is known ({numref}`known-lengths`), and the range of `i` lies within -n to n - 1 |
| `g[k]`, a member of a group by an int | the range of `k` lies within -n to n - 1, n being the number of members |
| `g[k]`, a member of a group by a {term}`string` | the type of `k` is a {term}`choice type` whose choices are all names of members of `g` |
```

So with `(real k 1)`, `(/ 1 k)` is a `real|none`, and with `(real k 1 (>= 1))`, a `real`. With
`(int f 0 (>= 0) (<= 3))`, `xs[f]` on a bound list of four items is never `none`. With
`(type side string (one-of 'left' 'right'))` and a group `arms` whose members are named `left` and
`right`, `arms[s]` is never `none` for a `side` `s`.

This rule exists to specify when the prover counts a condition as proved, and what the compiler does when it is not.

```{rule} constraint-proof
A value written where the expected type holds a condition C meets C when one of these holds:

- The value is known in the prove step and meets C.
- The type of the value is a subtype of the expected type with C as its only condition ({numref}`subtypes`).
- C is a comparison, and the range of the value lies inside it: its lower end is at least c for
  `(>= c)` and above c for `(> c)`, and its upper end is at most c for `(<= c)` and below c for
  `(< c)`.

When a value does not meet C:

| The value | Then |
|---|---|
| a value known in the prove step | a compile error |
| the value of a bound container | {numref}`prover-finds-ranges` |
| an argument of a call, or of `(M …)` or `(A …)` for a motif `M` or an animation `A` | a compile error |
| the body of a function declared with a result type R | when R includes `none`, a call evaluates to `none` where the value of the body breaks C, and the write step writes the `check` for it. Otherwise a compile error |
| an item of a `(list-of …)` whose item type is expected | a compile error |
| a value that a writer writes | not proved: {numref}`written-values` |
```

So `(real k 5 (<= 3))` is a compile error. With `(real a 1)` and
`(func g (((real (>= 0)) x)) (* 2 x))`, `(g a)` is a compile error, and `(g (abs a))` is not. With
`(func[(real|none (>= 0))] h ((real x)) x)`, `(h a)` is `none` while `a` is below 0.

```{mtp-example}
; k is at least 1, so the prover proves that 1/k is never none
(real k 2 (>= 1) (<= 5))
(scene s (circle c (r (/ 1 k)) (fill #'teal')))
(canvas v (x -1.2) (y -1.2) (width 2.4) (height 2.4) s)
(slider size (animation (move k (from 1) (to 5) (duration 0))) (label 'k'))
```

### Narrowing in an `if`

This rule exists so that the prover accepts a branch of an `if` that is safe only because of the test of the `if`.

```{rule} if-narrowing
A branch of an `if` is checked only for the values for which it runs. In `(if (OP N c) A B)`, where
N is a name whose range the prover works out, c is a number known in the prove step, and OP is one
of `=`, `!=`, `<`, `<=`, `>` and `>=`, the range of N in A is the part of its range for which the
comparison holds, and in B the part for which it fails. With lo and hi the ends of the range of N:

- For an int N, the part in A is from the smallest to the largest of the ints from lo to hi for
  which the comparison holds, and the part in B is the same for the ints for which it fails. So
  with c an int from lo + 1 to hi, `(< N c)` sets the upper end of the range in A to c - 1, and
  `(!= N c)` changes the range only when c is lo or hi.
- For a real N, a part in which N is at most c is from lo to the smaller of hi and c, and a part in
  which N is at least c is from the larger of lo and c to hi. A part in which N is below c is from
  lo to the smaller of hi and the largest binary64 number below c, and a part in which N is above c
  is from the larger of lo and the smallest binary64 number above c to hi. So with `(> N 0)`, the
  range of N in A does not hold 0. The part in which N is c is from c to c, and the part in which N
  is not c is the range of N with an end that equals c moved to the next binary64 number inside it.
- For a ratio N, a part in which N is below c, or at most c, is from lo to the smaller of hi and c,
  and a part in which N is above c, or at least c, is from the larger of lo and c to hi. The part in
  which N is c is from c to c, and the part in which N is not c is from lo to hi.
- When a part holds no int, for an int N, or when its lower end is above its upper end, or when lo
  and hi are both c in the part in which N is not c, the branch never runs, and the prover checks
  nothing in it.

The range of N changes only for the reads of N in A and in B that read the same declaration or
binding as the N of the condition. A name whose value is computed from N outside the `if`, such as a
`let` name, keeps its range. In an `if` inside A or B, the range of N is the part set by the outer
`if`. `(OP c N)` narrows as the comparison with N first that holds for the same values: `(< c N)`
as `(> N c)`, and `(= c N)` as `(= N c)`. `cond`, `when`, `and` and `or` narrow through their
{term}`rewrites <rewrite>` into `if` ({numref}`sugar-rewrites`). No other condition narrows a range.
```

In the source below, the body of the `foreach` is checked for `k` from 0 to 59
({numref}`check-bodies-once`). So `k` in the second branch of `(if (= k 0) …)` is from 1 to 59,
and `@'dot-{(- k 1)}'` refers to one of the copies `dot-0` to `dot-58` ({numref}`names-from-values`).

```mtp
(int n 24 (>= 1) (<= 60))
(scene s
  (foreach k n
    (circle @'dot-{k}' (r 0.1)
      (pos (if (= k 0) [3 0] (* 0.9 @'dot-{(- k 1)}'.pos))))))
```

With `(int k 1 (>= 0) (<= 5))`, `(if (< k 3) A B)` sets the range of `k` to 0 to 2 in A and to 3 to
5 in B, and `(if (> k 7) A B)` never runs A. With `(real x 1)`, `(if (> x 0) (sqrt x) 0)` is a
`real`, since `x` in the first branch is from the smallest binary64 number above 0 to `1e150`. In
`(if (> x 0) (/ 1 x) 0)`, `x` in the first branch has the same range, which does not hold 0, so
`(/ 1 x)` is a `real` there. In `(if (and (> k 0) (< k 3)) A B)`, the condition is the `if` of the
rewrite of `and`, which is not a comparison, so the range of `k` in A is not narrowed.

:::{admonition} Code differs
:class: note
The compiler has no narrowing. So
`(func[real] f (((int (>= 0) (<= 5)) k)) (if (= k 0) 0 (/ 1 k)))` is the error "this value may be
none" at `(/ 1 k)`, although `k` in that branch is from 1 to 5. examples/spiral-of-copies.mtp
compiles today only because the compiler checks each copy of a `foreach` with its own value of `k`
(mtp-08wd.1). Bead mtp-ydd4.7.55.
:::
