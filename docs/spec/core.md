(core)=
# Core and derived forms

On this page, every {term}`form` that the {term}`compiler` accepts is either a {term}`core form` or
{term}`syntactic sugar`. Each syntactic sugar form is given as a {term}`rewrite` into core forms.
Every head, with its kind and the page that defines it, is listed in {doc}`heads`.

This page specifies the language.

(core-kinds)=
## Kinds of form

The head of a form is its first item ({numref}`form-template`): `if` in `(if c a b)`, `circle` in
`(circle p (r 1))`. An item of a form is also called by its head, so `(r 1)` is an `r` item.

```{rule} kinds-of-form
Every form is either syntactic sugar ({numref}`sugar-form`) or a core form. Which kind a form is
depends on the whole form, not only on its head:
`(foreach ((a s) (b t)) …)` is syntactic sugar, and `(foreach a s …)` is core.
```

```{rule} sugar-form
A form is syntactic sugar if and only if it can be rewritten into core forms without computing any value and
without using any type. Looking up a {term}`name` is neither, since lexical scope is fixed by the
text, so a rewrite may resolve a name and read the text of the declaration or the binding that the
name refers to.
A form that needs a value or a type to be rewritten is core, and is rewritten, if at all, in the
expand step, once the prove step has worked out the types and the values ({numref}`compile-steps`).
```

```{rule} built-ins
A {term}`built-in` is a function, constant or type that every source has without declaring or
importing it. The {term}`standard library` is the set of files that come with mtp, which a source
imports like any other file ({doc}`imports`). Neither adds a form to the language: a call of a
built-in function, or of a function of the standard library, is a call, which is a core form, as a
call of a function that the source declares is.
```

By {numref}`declaration-names`, a declared function may take the name of a built-in function that is
not an operator: after `(func max ((real a) (real b)) b)`, `(max 1 2)` is 2.

The compiler rewrites every syntactic sugar form before the prove step ({numref}`compile-steps`), so
the {term}`prover` is given only core forms. The prover proves the {term}`body` of each `foreach`,
motif and animation only once, before any copies are made ({numref}`prove-bodies-once`). At that point
the names of a `foreach` and the parameters of a motif or an animation have no value yet, so a form
whose rewrite would need one of their values is core ({numref}`names-from-values`).

(core-rewrites)=
## Rewrite rules

The {term}`parser` rewrites some syntactic sugar while it reads the source:
a prefixed form `H@X`, a {term}`name string` `@'…'`, an {term}`interpolated string` `f'…'`, a part
after a {term}`list` {term}`literal`, `[…][X]` ({numref}`parser-sugar`), and a head that ends with `_` ({numref}`unnamed-head`). Every
other syntactic sugar form is in the table of the rule below.

(rewrite-when)=
```{rule} sugar-rewrites
Each form in the first column of this table is syntactic sugar, and means exactly the core forms in the
second column, when the conditions in the third column hold. A syntactic sugar form whose conditions do not
hold is a {term}`compile error`. A rewrite may move text or copy it, and each name in the moved or
copied text refers to what it referred to where it was written. A rewrite may give
syntactic sugar forms, which are rewritten in turn, until no syntactic sugar form is left.

In the table, a name in capitals stands for any text that its row allows, and `…` after it for
any number of such texts.

| Written | Means exactly | Conditions |
|---|---|---|
| `N.A`, `N[X]` | `(. N A)`, `(. N X)`. A chain is rewritten from left to right: `p.pos.x` is `(. (. p pos) x)`, and `g[0].r` is `(. (. g 0) r)` | The name is written as an expression or as the target of a writer. A head and the name of a declaration are not rewritten |
| `(when C X)` | `(if C X none)` | Exactly two arguments |
| `(cond (C1 V1) MORE… (else V))`, `(cond (else V))` | `(if C1 V1 (cond MORE… (else V)))`, `V` | |
| `(and A B MORE…)`, `(and A)` | `(if A (and B MORE…) false)`, `A` | |
| `(or A B MORE…)`, `(or A)` | `(if A true (or B MORE…))`, `A` | |
| `(jump V X)` | `(move V (to X) (duration 0))` | Exactly two arguments |
| `(palette N (M C)…)` | `(record N (color M C)…)` | Each item is `(M C)` |
| `(parametric N XS F ARGS…)` | `(polyline N (points (map XS F)) ARGS…)`: the polyline through the points of the curve `F` at the values of `XS`, in order | `F` is a `curve` ({numref}`the-types`), and `XS` a list of reals |
| `(pos [X Y])`, `(pos free@[X Y])` | `(x X) (y Y)`, `(x free@X) (y free@Y)` | |
| `(pos P)`, `(pos free@P)` | `(x (. P 0)) (y (. P 1))`, `(x free@(. P 0)) (y free@(. P 1))` | `P` is not a list literal, and holds no call of `rand`, `rand-int`, `pick` or `shuffle` |
| `(foreach ((N1 S1) (N2 S2) MORE…) ITEMS…)`, `(foreach ((N S)) ITEMS…)` | `(foreach N1 S1 (foreach ((N2 S2) MORE…) ITEMS…))`, `(foreach N S ITEMS…)` | The names are all different |
| `(wait T)`, in a score | `(move none (duration T))` | |
| `(animation N (P…) A B MORE…)` | `(animation N (P…) (in-order A B MORE…))` | |
| `(in-order ARGS… ITEMS…)`, `(at-once ARGS… ITEMS…)` | `(score ARGS… ITEMS…)`, with `(lag 1)` for `in-order`, or `(lag 0)` for `at-once`, added to its `(defaults …)`, which is added when it has none | Its `(defaults …)` gives no `lag` |
| `(on-drag S S.pos ITEMS…)`, `(on-drag S S.x ITEMS…)`, `(on-drag S S.y ITEMS…)` | `(on-drag S (move S.pos (to pointer) (duration 0)) ITEMS…)`, `(on-drag S (move S.x (to (. pointer 0)) (duration 0)) ITEMS…)`, `(on-drag S (move S.y (to (. pointer 1)) (duration 0)) ITEMS…)` | `pointer` is the position of the pointer ({numref}`declarations-and-bindings`) |
| `(on-drag S S.shift ITEMS…)`, `(on-drag S S.shift-x ITEMS…)`, `(on-drag S S.shift-y ITEMS…)` | `(on-drag S (move S.shift (to pointer) (duration 0)) ITEMS…)`, `(on-drag S (move S.shift-x (to (. pointer 0)) (duration 0)) ITEMS…)`, `(on-drag S (move S.shift-y (to (. pointer 1)) (duration 0)) ITEMS…)` | |
```

So `(parametric p (range -2 2 (num 361)) (fn t [t (* t t)]) (stroke #'teal'))` is the parabola
through 361 points from [-2 4] to [2 4], and `(parametric p (range 0 1 (num 50)) f)` draws a
declared function `f`.

:::{admonition} Code differs
:class: note
The compiler reads `parametric` as `(parametric N (for T LO HI) E ARGS…)`, with the curve written as
an expression `E` of the name `T` (compiler.py:434). Bead mtp-of7a makes the compiler follow the rule.
:::

Since a copied random call is a {term}`site` of its own ({numref}`random-site`),
`(pos (pick corners))` would draw `x` and `y` at two sites, so it is an error. A body `let` holds
the point once: `(let ((q (pick corners))) (circle c (pos q)))` is `(x (. q 0)) (y (. q 1))`, which
reads one value.

:::{admonition} Code differs
:class: note
The compiler makes these rewrites while it compiles each form, in the same functions that check
it, and not in a step of their own (for example compiler.py:6471-6479 for `when`, 3074-3087 for
`wait`, 3745-3764 for an animation item, 1669-1729 for a choreo use). Beads mtp-08wd.5, mtp-08wd.6, mtp-08wd.7, mtp-08wd.8
and mtp-08wd.2 will make them in the rewrite step. Where the result differs today:

- `p.r` is read as one name with {term}`name parts <name part>` (parse.py:337-395), and each name
  part after the first as an attribute (compiler.py:5953-5960), so with a local `r`, `xs.r` is an
  error while `(. xs r)` is an item of `xs` (mtp-ydd4.7.5).
- `(wait T)` makes no transition object, while `(move none (duration T))` does
  (compiler.py:3074-3087, 3184-3197). The two .mtpc files differ by that object (mtp-ydd4.7.21).
- A palette has the type `palette` (compiler.py:1454, types.py:148-162), and the namespace that it
  means has the type `namespace` (mtp-ydd4.7.22).
- `(cond (else V))` is {term}`folded <folding>` to the value of `V` and, since it is not a literal,
  marked const (compiler.py:5653-5657), so `(real v (cond (else 3)))` makes `v` a constant, while
  `(real v 3)` is a free variable that a writer may write (mtp-ydd4.7.46).
- `cond` gives a list literal among its values the type of all its other values
  (compiler.py:6629-6641), while an `if` gives it the type of its other branch only
  (compiler.py:6494-6504) (mtp-08wd.2).
- `(pos P)` compiles `P` once and splits it (compiler.py:5594-5611), so a random call in `P` is
  accepted, as one site (mtp-ydd4.7.25).
- A choreo's argument must be known when compiling, a name or a function (compiler.py:1702-1708),
  and is compiled once, then bound to the parameter (mtp-08wd.5).
:::

So a bare name as the target of an `on-drag` is the position of the dragged shape, its `x` or its
`y`, and any other bare name there is a compile error: `(on-drag p k)` must be written with a
move, such as `(on-drag p (move k (to (. pointer 0))))`.

### Copies with `like`

```{rule} like-copies
`(K N (like M) ARGS…)` is syntactic sugar for `(K N ARGS… COPIED…)`. `COPIED…` holds each item of
the declaration of `M`, as written in the source, whose heads do not overlap with those in `ARGS…`. A `(like …)` in
the declaration of `M` is rewritten first, and a `(like …)` is rewritten before any other rewrite of
the declaration that holds it.
```

For example, after `(circle a (r 1) (fill #'red') (stroke #'black'))`, the form
`(circle b (like a) (r 2))` is syntactic sugar for `(circle b (r 2) (fill #'red') (stroke #'black'))`:
`b` has every item of `a` but its radius, and a radius of 2.

`M` is a plain name, and the form is one of these, or it is a {term}`compile error`:

- `K` is a shape head other than `group`, `row` and `column`, and `M` is a shape of kind `K`.
- `K` is a motif or a variant, and `M` is an instance of it.
- `K` is `font`, and `M` is a font.
- `K` is `term`, and `M` is a term of the same formula whose `(term …)` form comes before.
- The form is a `move` or a `movement`, and `M` is a movement declared at the top level.

Two kinds of item are copied in a way of their own. The string of a text is copied too, though it
is a positional argument and has no head. A `(pos P)` of `M` gives both `x` and `y`, so when
`ARGS…` gives exactly one of them, `COPIED…` holds the other, `(x (. P 0))` or `(y (. P 1))`.

Since `(like M)` copies what `M` was written with in the source, a copy does not get the defaults
of `M`'s collection: `(circle b (like a))` outside the group of `a` has only what `a` was written
with. A copied item that is bound is bound to the same expression in the copy: if the radius
of `M` is bound to `(* 2 k)`, so is the radius of the copy, and both follow `k`. A copied item that
is free is a free attribute of the copy, of its own, with the same start: with `(r free@2)`
in `M`, the copy's radius starts at 2, and a writer of `M`'s radius does not write it. The defaults of an instance, `pointer-events` among them, and its `clip` are items of it,
so `(like M)` copies them.

:::{admonition} Code differs
:class: note
`(like M)` on an instance does not copy its `clip` (mtp-ydd4.7.20).
:::

### Dragging a group

```{rule} drag-group-shift
A group, a row or a column is dragged by its `shift`, its `shift-x` or its `shift-y`. In an
`on-drag` on such a collection, whether its `fixed-size` is true or not, when the target is the
collection's own `shift`, `shift-x` or `shift-y`, `pointer` is the collection's `shift` at the press
plus the motion of the pointer since the press, in the frame of the collection's collection. A
target that is the collection's `pos`, `x` or `y` is a {term}`compile error`, "a group has no x of
its own: drag its shift, as (on-drag g g.shift)".
```

By {numref}`sugar-rewrites`, `(on-drag g g.shift)` is
`(on-drag g (move g.shift (to pointer) (duration 0)))`.
No member is written: the members are drawn in the frame of the group, so they move with it and keep
their own positions. `(on-drag g g.x)` is an error twice over: `g.x` of a group is the list of the
`x` of its members, and a drag writes one number.

:::{admonition} Code differs
:class: note
A group has no `shift-x` and no `shift-y`: the compiler and the runtime give it a `translate`, and
the drag writes that, for `(on-drag g g.pos)` too. Bead mtp-1vyc makes the parts of a frame attributes of
the shape, and bead mtp-67wi makes a drag of a group's `pos` an error.
:::

:::{admonition} Code differs
:class: note
For a bare target, the {term}`runtime` moves each member of a group that is not fixed-size by the
motion of the pointer (web/src/drag.ts:113-117, drag.ts:155-162), and moves a fixed-size group by
its `translate` (drag.ts:108-111, drag.ts:149-153). For a move, it writes the group's `x` and `y`
(drag.ts:138-147), and the compiler marks the `translate` as what the drag writes only for a
fixed-size group (compiler.py:4009-4021). Bead mtp-ydd4.7.36 makes the code follow the rule.
:::

### `foreach` over a count or a list whose length is known only while drawing

```{rule} foreach-count
`(foreach N X ITEMS…)`, where `X` is an {term}`int`, means exactly `(foreach N (range 0 X) ITEMS…)`.
```

So the two spellings mean the same, at all times, and every rule about the second applies to the
first. The first is core, and not syntactic sugar, only because an int and a list are told apart by the type
of `X` ({numref}`sugar-form`).

```{rule} foreach-bounded-length
A `foreach` over a list whose length is known only while drawing makes as many copies as the upper
bound of that length that the prover proves ({numref}`prover-finds-ranges`). Copy k, counted from
0, is `none` while k is not below the length. A copy that is `none` and then is not is the same
object as before, with its attributes as they were, what writers wrote to them included. When the prover proves no upper bound of the length
below the {term}`number limit`, the `foreach` is a compile error.
```

So with `(int n 3 (>= 0) (<= 5))`, which a slider writes, `(foreach k n …)` and
`(foreach k (range 0 n) …)` both make 5 copies, and copies 3 and 4 are `none` while `n` is 3. When `n` goes
back to 5, copies 3 and 4 come back as they were.

:::{admonition} Code differs
:class: note
The compiler makes the bounded copies for a count (compiler.py:880-915), but rejects a list whose
length is known only while drawing, `(range 0 n)` included, with "the length of the list a foreach
goes through must be known when compiling" (compiler.py:930-934). Bead mtp-ydd4.7.37 makes the
compiler follow the rule.
:::

### The form `.`

```{rule} dot-name-part
In `(. X Y)`, where `Y` is a bare name with one name part, `Y` is the attribute or the member of `X`
of that name, when `X` has one. Otherwise `Y` is an expression, and its value is a position or a key
of `X`.
```

So `p.r` is the attribute `r` of a circle `p`, and with `(let ((r 1)) xs.r)`, `xs.r` is item 1 of
the list `xs`, as `(. xs r)` is. An attribute or a member of an object is read by its name, even
when another declaration or a binding has the same name: the attributes of a record, the terms of a
formula, and the members of a shape whose type is a motif. A palette is a record
({numref}`sugar-rewrites`), so with `(color yellow #'#ffd700')` and
`(palette marks (yellow #'#e6c200') (blue #'#0072b2'))` at the top level, `marks.yellow` is the
attribute `yellow` of the record `marks`, and not the color `yellow`.

:::{admonition} Code differs
:class: note
compiler.py:6540-6549 reads `Y` as an attribute only when `has_attr` (compiler.py:6175-6188) finds
one, and `has_attr` finds no member of a namespace or a formula. So `(. marks yellow)`
reads the color `yellow` as a key (mtp-ydd4.7.19).
:::

### A score written as a step

```{rule} animation-step
A score written as a member of another score is one step of it. It plays
its own members, a `(loop …)` included, and the `(defaults …)` around it do not apply inside it.
```

:::{admonition} Code differs
:class: note
An animation's body does not accept the head `animation` (compiler.py:3097-3103). A use of a
choreo is compiled to its steps in place (compiler.py:1714-1729) (mtp-ydd4.7.26).
:::

### Names built from values

```{rule} names-from-values
A `(name S)`, and a `(like (name S))`, whose string `S` reads a name bound by a `foreach` or a
parameter of a motif, are core. The prover proves, for every value that those names may take,
that `S` gives the name of a declaration that comes before the form, and that every such
declaration fits the form: for `(name S)`, a type that fits all of them, and for `(like …)`, what
{numref}`like-copies` requires. The expand step replaces each by the name that `S` gives in each
copy, and then makes the copy that {numref}`like-copies` gives.
```

For example, take this `foreach`:

```mtp
(circle d-0 (pos [0 0]) (r 1))
(foreach k (range 1 5)
  (let ((prev @'d-{(- k 1)}'))
    (circle @'d-{k}' (pos [k 0]) (r (/ prev.r 2)))))
```

Each circle has half the radius of the one before it, which `prev` names. The prover proves the
body once, for k from 1 to 4, so `prev` names one of `d-0` to `d-3`, each a circle that comes
before.

:::{admonition} Code differs
:class: note
The compiler makes each copy first, and then compiles `(name S)` and `(like …)` with the values of
that copy (compiler.py:1161-1167, compiler.py:5329-5341) (mtp-08wd.1).
:::
