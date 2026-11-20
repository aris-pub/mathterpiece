(core)=
# Core and derived forms

On this page, every {term}`form` that the {term}`compiler` accepts is either a {term}`core form` or
{term}`syntactic sugar`. Each syntactic sugar form is given as a {term}`rewrite` into core forms,
and each core form with the page of the spec where its meaning is defined. The built-in functions
are listed in a table of their own.

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
a prefixed form `H@X`, a {term}`name string` `#'…'`, an {term}`interpolated string` `f'…'`, a part
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
of `M`'s container: `(circle b (like a))` outside the group of `a` has only what `a` was written
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
`on-drag` on such a container, whether its `fixed-size` is true or not, when the target is the
container's own `shift`, `shift-x` or `shift-y`, `pointer` is the container's `shift` at the press
plus the motion of the pointer since the press, in the frame of the container's container. A
target that is the container's `pos`, `x` or `y` is a {term}`compile error`, "a group has no x of
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
  (let ((prev #'d-{(- k 1)}'))
    (circle #'d-{k}' (pos [k 0]) (r (/ prev.r 2)))))
```

Each circle has half the radius of the one before it, which `prev` names. The prover proves the
body once, for k from 1 to 4, so `prev` names one of `d-0` to `d-3`, each a circle that comes
before.

:::{admonition} Code differs
:class: note
The compiler makes each copy first, and then compiles `(name S)` and `(like …)` with the values of
that copy (compiler.py:1161-1167, compiler.py:5329-5341) (mtp-08wd.1). The example writes its name
strings `#'…'`, as the compiler reads them today, in place of `@'…'` (mtp-c1hl).
:::

(core-inventory)=
## Inventory of heads

Each table lists the heads of one context. The column "Defined in" gives the page where a core
form's meaning is defined, the rule for a syntactic sugar form, or {doc}`stdlib` for a built-in.

(top-level-heads)=
### Top-level forms

The top level of a source holds only the heads of these tables, with at most one `scene`.

**Declarations of types**

| Head | Kind | Defined in |
|---|---|---|
| `type` | core | {numref}`type-notation` |
| `interface` | core | {doc}`types` |
| `motif` | core | {doc}`world-model` |
| `variant` | core | {doc}`types` |
| `animation` | core | {doc}`time` |

**Declarations of objects**

| Head | Kind | Defined in |
|---|---|---|
| `scene` | core | {doc}`world-model` |
| `formula` | core | {doc}`world-model` |
| `record` | core | {doc}`world-model` |
| `font` | core | {doc}`data-model` |
| `palette` | syntactic sugar | {numref}`sugar-rewrites` |
| `parametric` | syntactic sugar | {numref}`sugar-rewrites` |
| `movement` | core | {doc}`time` |
| {term}`components <component>` | core | {doc}`page-interface` |

**Declarations of functions**

| Head | Kind | Defined in |
|---|---|---|
| `func`, `func[T]` | core | {doc}`types`, {doc}`evaluation` |
| `colormap` | core | {doc}`evaluation` |
| `primitive` | core | {numref}`primitive-form` |

**Declarations of variables**

| Head | Kind | Defined in |
|---|---|---|
| `(T N …)` for a type `T` | core | {doc}`data-model`, {doc}`reaction` |
| `var` | core | {doc}`data-model` |

**Forms around declarations**

| Head | Kind | Defined in |
|---|---|---|
| `import` | core | {doc}`imports` |
| `let` | core | {doc}`binding-time` |
| `foreach` | core | {doc}`binding-time` |
| `doc` | core | {doc}`compiled-format` |

So a source need not hold a scene: `(real a 1) (readout r f'{a}')` is a world model with a
variable and a readout, and an empty file is a world model with nothing in it. A source with two
scenes is an error.

:::{admonition} Code differs
:class: note
The error for a second scene is "a file has exactly one scene" (`compiler.py:4854`). Bead
mtp-ydd4.7.59.
:::

### Variables and conditions

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `(T N VALUE C…)` | core | a variable declaration | {doc}`world-model`, {doc}`reaction` |
| `list` with no item type | core | a type | {doc}`types` |
| `font` | core | a font declaration | {doc}`world-model` |
| `family`, `style`, `weight`, `size` | core | attributes of a font | {doc}`world-model` |
| `like` in a font | syntactic sugar | a named argument of a font | {numref}`like-copies` |
| `free` | core | an expression | {doc}`reaction`, {doc}`binding-time` |
| `>=`, `>`, `<=`, `<` with one number | core | conditions | {doc}`types` |
| `length` | core | a condition | {doc}`types` |
| `one-of` | core | a condition | {doc}`types` |
| `const` | core | a named argument of a variable or an attribute | {doc}`data-model` |
| `mod` | core | a type | {doc}`types` |

### Type notation

| Notation | Kind | What it is | Defined in |
|---|---|---|---|
| `int`, `ratio`, `real`, `complex`, `unit`, `ease`, `curve`, `bool`, `string`, `color`, `font`, `point`, `transform`, `movement`, `none`, `scene` | core | the {term}`built-in types <built-in type>` | {doc}`types` |
| `circle` and the other shape names | core | the shape types | {doc}`types` |
| `shape`, `positioned`, `sequence`, `sequence[T]` | core | built-in types and {term}`interfaces <interface>` | {doc}`types` |
| `list[T]` | core | a list type | {doc}`types` |
| `func[P… R]` | core | a function type | {doc}`types` |
| `T\|none` | core | a union with `none` | {doc}`types` |
| `(T C…)` | core | a refined type | {doc}`types` |
| `colormap` | core | a type | {numref}`the-types` |
| a name declared by `type` | core | the type that it names | {numref}`type-notation` |
| a name declared by `interface`, `motif` or `variant` | core | that type | {doc}`types` |
| `rand-seed` | core | a type | {doc}`types`, {doc}`evaluation` |

### The scene, shapes and containers

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `background` | core | a named argument of the scene | {doc}`world-model` |
| `transform` in the scene | core | a named argument of the scene | {doc}`world-model` |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `bezier`, `arc`, `ring`, `text` | core | shape declarations | {doc}`world-model` |
| `group` | core | a group declaration | {doc}`world-model` |
| `row`, `column` | core | group declarations | {doc}`world-model` |
| `(M N …)` for a motif `M` | core | a declaration of a shape whose type is the motif | {doc}`world-model` |
| `(V N …)` for a variant `V` | core | a declaration of a thing whose type is the variant | {doc}`world-model` |
| `(H\|none N …)` for a shape head `H` | core | a declaration of a shape that may be `none` | {doc}`world-model` |
| `exists-when` | core | a body item | {doc}`world-model` |
| `let` in a body | core | a let | {doc}`binding-time` |
| `foreach` in a body | core | a foreach | {doc}`binding-time` |
| a variable in the scene | core | a variable declaration | {doc}`world-model` |

### Arguments of shapes and containers

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `x`, `y`, `translate`, `transform`, `fill`, `stroke`, `stroke-width`, `opacity`, `fill-opacity`, `stroke-opacity`, `line-cap`, `line-join`, `drawn`, `pointer-events` on a shape, `r`, `width`, `height`, `rx`, `ry`, `from`, `to`, `a`, `b`, `c`, `points`, `controls`, `head-start`, `head-end`, `head-size`, `value`, `halign`, `valign`, `font` | core | named arguments of a shape | {doc}`world-model` |
| `pos` | syntactic sugar | a named argument | {numref}`sugar-rewrites` |
| `dash` | core | a named argument | {doc}`world-model` |
| `like` | syntactic sugar | a named argument | {numref}`like-copies` |
| `defaults` on a group, a row or a column | core | a named argument | {numref}`container-defaults` |
| `clip` | core | a named argument | {doc}`world-model` |
| `fixed-size` | core | a named argument | {doc}`world-model` |
| `gap`, `align` | core | named arguments of a row or a column | {doc}`world-model` |

### Motifs and variants

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a parameter `(T N DEFAULT?)` | core | a parameter | {doc}`types` |
| a shape, a bound variable, `foreach`, `let` or `exists-when` in a motif's body | core | body items of a motif | {doc}`world-model` |
| `self` | core | a name | {doc}`scope` |
| a parameter given to an instance, `(P X)` | core | a named argument of a shape of a motif type | {doc}`world-model` |
| `x`, `y`, `translate`, `transform` on an instance | core | named arguments of a shape of a motif type | {doc}`world-model` |
| `pos` on an instance | syntactic sugar | a named argument | {numref}`sugar-rewrites` |
| `clip` on an instance | core | a named argument | {doc}`world-model` |
| `defaults` on an instance | core | a named argument | {doc}`world-model` |
| `like` on an instance or a variant instance | syntactic sugar | a named argument | {numref}`like-copies` |

The rules about a declaration that reads itself or its container, such as a default that reads
its own group, are to be redesigned around `self`. Until then, the rules of today hold
({numref}`self-reference-today`).

### Records, palettes and interfaces

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a variable in a record | core | a body item | {doc}`world-model` |
| `record`, `palette` in a record | core, syntactic sugar | a body item | {doc}`world-model`, {numref}`sugar-rewrites` |
| `(M C)` in a palette | syntactic sugar | a body item | {numref}`sugar-rewrites` |
| `(T A C…)` in an interface | core | a body item | {doc}`types` |

### Formulas and terms

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a string known when compiling | core | the positional argument of a formula | {doc}`world-model` |
| `term` | core | a body item of a formula | {doc}`world-model` |
| `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding` in a term | core | named arguments of a term | {doc}`world-model` |
| a string in a term | core | the positional argument of a term | {doc}`world-model` |
| `like` in a term | syntactic sugar | a named argument | {numref}`like-copies` |
| `defaults` in a formula | core | a named argument | {numref}`formula-defaults` |
| `exists-when` in a formula | core | a body item | {doc}`world-model` |
| a variable in a formula | core | a body item | {doc}`world-model` |

### Special forms and other expressions

The heads of this table that are written as {term}`words <word>`, from `.` to `type-of`, are
{term}`keywords <keyword>` ({numref}`keywords`).

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a literal | core | an expression | {doc}`lexical`, {doc}`types` |
| a name | core | an expression | {doc}`scope` |
| a name with several name parts, `N.A`, `N[X]` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| `.` | core | an expression | {numref}`dot-name-part` |
| `name` | core | an expression | {doc}`scope`, {numref}`names-from-values` |
| `if` | core | an expression | {doc}`evaluation` |
| `when` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| `cond`, `else`, `and`, `or` | syntactic sugar | expressions | {numref}`sugar-rewrites` |
| `let` | core | an expression | {doc}`scope`, {doc}`evaluation` |
| `fn` | core | an expression | {doc}`types`, {doc}`evaluation` |
| `as` | core | an expression | {doc}`types` |
| `type-of` | core | an expression | {doc}`types` |
| `concat` | core | an expression | {doc}`evaluation` |
| `fmt` | core | an expression | {doc}`evaluation` |
| `free` | core | an expression | {doc}`reaction` |
| `(F A…)` for a declared function `F` | core | an expression | {doc}`evaluation` |
| `(L A…)` for a local function value `L` | core | an expression | {doc}`evaluation` |

### Built-in functions and the standard library

These heads name built-in functions, except the primitives, which the standard library names. Each call is a core call ({numref}`built-ins`).

| Heads | What they are |
|---|---|
| `+`, `-`, `*`, `/`, `^`, `mod`, `=`, `!=`, `<`, `<=`, `>`, `>=` | the operators |
| `not`, `abs`, `or?`, `none?`, `some?`, `somes` | logic, absolute value and `none` |
| `sqrt`, `sign`, `floor`, `ceil`, `exp` | numbers |
| `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, `sind`, `cosd`, `tand`, `secd`, `cscd`, `cotd`, `asin`, `acos`, `atan`, `acot`, `asec`, `acsc`, `asind`, `acosd`, `atand`, `acotd`, `asecd`, `acscd`, `rad`, `turn`, `deg`, `to-rad`, `to-turn` | angles |
| `polar`, `to-polar`, `dist` | points |
| `rotate`, `translate`, `scale`, `transform` | transforms |
| `mix`, `lighten`, `darken`, `light-dark` | colors |
| `round`, `log`, `min`, `max`, `lerp` | with a varying number or type of arguments |
| `range` | `(range LO HI (gap G))`: the numbers from `LO`, `G` apart, up to `HI` and not including it. `G` is 1 when the range gives neither `gap` nor `num`. `(range LO HI (num N))`: `N` numbers evenly apart, from `LO` to `HI`, both included. `gap` and `num` are {term}`named arguments <named argument>` of `range` |
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | random values and seeds: {term}`primitives <primitive>`, which a source names only through the file rand of the standard library ({numref}`primitive-form`). `rand`, `rand-int`, `pick` and `shuffle` take the named argument `(seed S)`, and follow the {term}`default seed` of the file that holds them when it is left out ({numref}`default-seed`) |
| `steps` | an ease: `(steps N (at P))` gives the ease of N equal jumps, each at the fraction P of its interval, so jump k comes at (k − 1 + P)/N. P is from 0 to 1 and known when compiling, and is 1 when `(at …)` is left out. So `(steps 1 (at P))` is 0 before P and 1 from P on |
| `map`, `where`, `sort`, `reverse`, `reduce`, `sum`, `count`, `any`, `all` | collections |
| `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right` | points on a shape's box |
| `pi`, `tau`, `euler` | constants |
| the files `colors`, `eases`, `fonts`, `marks`, `math`, `rand` | the standard library, written in mtp, and the file `rand` names the primitives ({ref}`stdlib-rand`) |

:::{admonition} Code differs
:class: note
The compiler accepts `(range n)` as `(range 0 n (gap 1))`, and rejects a `range` that gives
neither `gap` nor `num`, such as `(range 0 n)`, with "range is (range n), (range start stop (gap g))
or (range start stop (num n))". Bead mtp-z8i1 makes the compiler follow the rule.
:::

A call of `steps` gives an ease, which is a function, so `steps` is a built-in function and not a
keyword. By {numref}`declaration-names`, a declaration or a binding named `steps` takes the place
of the built-in function from that declaration or binding on.

:::{admonition} Code differs
:class: note
The compiler has `(step N)`, whose jumps come at the start of each interval, and `(step-ease P)`,
with one jump at P, in place of `steps` (compiler.py:3092-3107, web/src/transitions.ts:22). It reads
them only as the whole value of an `ease`, and not as calls. So after `(real step 3)`,
`(ease (step 2))` still compiles as the ease of two jumps, and `(step 2)` in any other place is the
error "unknown function". Beads mtp-ydd4.7.40 and mtp-6a4r make the compiler follow the rule.
:::

### Movements

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `move` | core | an expression | {doc}`time` |
| `from`, `to`, `duration`, `path` | core | named arguments of a movement | {doc}`time` |
| `ease` | core | a named argument of a movement | {doc}`time` |
| `like` in a movement or a move | syntactic sugar | a named argument | {numref}`like-copies` |
| an animation's body of several items | syntactic sugar | the body of an animation | {numref}`sugar-rewrites` |
| `defaults` in a score | core | a named argument | {doc}`time` |
| `loop` | core | a named argument of a score | {doc}`time` |
| `score` | core | an expression | {doc}`time` |
| `lag` | core | a named argument of a movement | {doc}`time` |
| `in-order`, `at-once` | syntactic sugar | expressions | {numref}`sugar-rewrites` |
| `foreach` in a score | core | a body item | {doc}`time`, {doc}`binding-time` |
| the name of a movement, or of an animation with no parameters, in a score | core | a body item | {doc}`time` |
| `wait` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| `jump` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| a use of an animation | core | an expression | {doc}`time`, {numref}`animation-step` |

### Components and their items

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `canvas`, `readout`, `display` | core | view declarations | {doc}`page-interface`, {doc}`lifecycle` |
| `slider`, `button`, `play`, `stepper`, `toggle` | core | control declarations | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove` | core | listeners | {doc}`reaction`, {doc}`concurrency` |
| `on-show`, `on-hide` | core | listeners that play while a canvas starts or stops drawing a shape | {doc}`reaction`, {doc}`lifecycle` |
| `on-view`, `on-ready`, `on-live`, `on-quiet` | core | listeners on their own view | {doc}`lifecycle` |
| `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom` on a canvas | core | named arguments of a canvas | {doc}`page-interface` |
| `toggle-duration`, `toggle-ease` | core | named arguments of a canvas | {doc}`time`, {doc}`page-interface` |
| a name, a list literal or an expression in a canvas | core | body items of a canvas | {doc}`page-interface` |
| `font` on a readout | core | a named argument of a readout | {doc}`page-interface` |
| `kind` on a display | core | a named argument of a display | {doc}`page-interface` |
| a movement on a control or a listener | core | a positional argument of a writer | {doc}`reaction`, {doc}`time` |
| the move of a slider | core | the positional argument of a slider | {doc}`page-interface`, {doc}`reaction` |
| the target of `toggle`, `on-pointermove` | core | a positional argument | {doc}`reaction` |
| the target of `on-drag` written as a move | core | the positional argument of an `on-drag` | {doc}`reaction`, {numref}`drag-group-shift` |
| the target of `on-drag` written as a name | syntactic sugar | the positional argument of an `on-drag` | {numref}`sugar-rewrites` |
| `label` | core | a named argument of a control | {doc}`page-interface`, {doc}`accessibility` |
| `stops` on a slider | core | a named argument of a slider | {doc}`page-interface` |
| `buttons`, `rest`, `labels` on a play | core | named arguments of a play | {doc}`page-interface`, {doc}`time` |
| `selected` on a button | core | a named argument of a button | {doc}`page-interface`, {doc}`accessibility` |
| `active` | core | a named argument of a writer | {doc}`reaction` |
| `priority` | core | a named argument of a writer | {doc}`concurrency` |
| `stop-propagation` | core | a named argument of a listener | {doc}`reaction` |
| `in` | core | a named argument of a control | {doc}`page-interface`, {doc}`lifecycle` |
| a guard | core | a body item of a writer | {doc}`reaction` |
| `doc` on a component | core | its docstring | {doc}`compiled-format` |

:::{admonition} Code differs
:class: note
The compiler shows a label written `(label $'…')` as typeset LaTeX, and any other label as plain
text, so the spelling of a string changes its meaning. Bead mtp-z8x5 makes the compiler follow the rule.
:::

:::{admonition} Code differs
:class: note
A canvas without `(zoom …)` zooms from 1 to 10 times, `(zoom B)` turns zooming on or off, and a
canvas without `(pan …)` pans (compiler.py:3790-3815, 4386-4391). Bead mtp-ff0r makes the compiler
follow the rule.
:::

### Bodies

:::{table} The bodies of mtp ({numref}`contexts`). A head that the table does not list has no body. "let, foreach" says whether the body may hold a `let` and a `foreach` ({numref}`body-let-foreach`).
:name: bodies-table

| Head | Its body | let, foreach |
|---|---|---|
| the top level of a source | the heads of {ref}`top-level-heads` | yes |
| the top level of a {term}`file to import` | the forms of {numref}`import-file-holds` | yes |
| `import` | the names to import, or none to import the whole file | no |
| `scene` | shapes, variables, `exists-when` | yes |
| `group`, `row`, `column` | shapes, `exists-when` | yes |
| `motif` | shapes, variables that are bound or known when compiling, `exists-when` | yes |
| `formula` | terms, `exists-when` and variables. The string is its positional argument ({numref}`formula-terms`) | yes |
| `record` | variables, records, palettes | yes |
| `palette` | items `(member color)` | yes |
| `interface` | items `(T attribute constraint…)` | yes |
| `type`, a variable `(T name …)` | {term}`conditions <condition>`, such as `(>= 0)` | yes |
| `animation`, `score`, `in-order`, `at-once` | movements: `move`, `jump`, `wait`, a score, the name of a movement, a use of an animation | yes |
| `defaults` | items `(attribute value)`, and in a score, `(duration …)`, `(ease …)` and `(lag …)` | yes |
| `canvas` | at least one thing to draw: a name of a shape or of the scene, a list literal, or an expression that gives a shape, `none` or a list of shapes, such as `(when c d)`. Listeners ({numref}`listeners-in-views`) | yes |
| `readout`, `display` | listeners ({numref}`listeners-in-views`) | yes |
| a control, a listener | guards, such as `(>= k 0)` | yes |
| `let`, `foreach` | items of the kinds that the body around them holds | yes |
| `in` | the views that a control belongs to | no |
| `labels` | strings | no |
| `transform` | transforms, such as `(rotate 90)` | no |
| a call that takes any number of arguments, such as `(+ a b c)` | its arguments | no |
:::

So `(canvas v)` is an error, because a canvas holds at least one thing to draw, and `(canvas v s)`
and `(canvas v c)` are allowed.

:::{admonition} Code differs
:class: note
`(canvas v)` compiles, to a canvas that draws nothing. Bead mtp-ydd4.7.59.
:::

### Heads that are errors

These heads were once part of the language, or belong in another context. No body holds them, so
each is a compile error ({numref}`contexts`). The compiler gives a message about what to write in
their place. They are not forms of the language.

| Head | Where | The message, in short |
|---|---|---|
| `step` | in a score | use `(labels …)` and `(in-order …)` |
| `autoplay` | on a control | use a canvas's `(on-ready …)` |
| `exclusive` | on a writer | use `(priority n)` |
| `when` | on a control or a listener | use `(active bool)` |
| `value` | on a toggle | give the bool its start where it is declared |
| `buttons` | on a stepper | a stepper stops after each step |
| `dash-offset` | as an item | write `(dash [4 2] 1)` |
| `move` | in a canvas | a canvas takes no move |
| `term` | at the top level | a term is given inside its formula |
| `pointer-events` | on a group, a row, a column or an instance | write `(defaults (pointer-events B))` |

:::{admonition} Code differs
:class: note
The compiler accepts `(pointer-events B)` on a group, a row, a column or an instance as a default
for its members (compiler.py:4895-4941, 5395-5443). Bead mtp-327t makes it a compile error.
:::
