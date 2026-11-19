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
A form that needs a value or a type to be rewritten is core.
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
| `(on-drag S S.pos ITEMS…)`, `(on-drag S S.x ITEMS…)`, `(on-drag S S.y ITEMS…)` | `(on-drag S (move S.pos (to pointer)) ITEMS…)`, `(on-drag S (move S.x (to (. pointer 0))) ITEMS…)`, `(on-drag S (move S.y (to (. pointer 1))) ITEMS…)` | `pointer` is the position of the pointer ({numref}`declarations-and-bindings`) |
```

So `(parametric p (range -2 2 (num 361)) (fn t [t (* t t)]) (stroke 'teal'))` is the parabola
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

For example, after `(circle a (r 1) (fill 'red') (stroke 'black'))`, the form
`(circle b (like a) (r 2))` is syntactic sugar for `(circle b (r 2) (fill 'red') (stroke 'black'))`:
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
In an `on-drag` on a group, a row or a column, whether its `fixed-size` is true or not, a move
whose target is the `pos`, the `x` or the `y` of that same container writes the container's
`shift-x` and `shift-y` in place of the target: both for `pos`, `shift-x` for `x`, and `shift-y`
for `y`. In that move, `pointer` is `[shift-x shift-y]` of the container at the press plus the
motion of the pointer since the press, in the frame of the container's container.
```

By {numref}`sugar-rewrites`, `(on-drag g g.pos)` is `(on-drag g (move g.pos (to pointer)))`, so
both spellings move the group by its `shift-x` and `shift-y`. No member is written: the members are
drawn in the frame of the group, so they move with it and keep their own positions.

:::{admonition} Code differs
:class: note
A group has no `shift-x` and no `shift-y`: the compiler and the runtime give it a `translate`, and
the drag writes that. Bead mtp-1vyc makes the parts of a frame attributes of the shape.
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
0, exists only while k is below the length. When the prover proves no upper bound of the length
below the {term}`number limit`, the `foreach` is a compile error.
```

So with `(int n 3 (>= 0) (<= 5))`, which a slider writes, `(foreach k n …)` and
`(foreach k (range 0 n) …)` both make 5 copies, and copies 3 and 4 do not exist while `n` is 3.

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
the list `xs`, as `(. xs r)` is. A member of a record, a palette, a formula or an instance is
read by its name, even when another declaration or a binding has the same name. So with
`(color yellow '#ffd700')` and `(palette marks (yellow '#e6c200') (blue '#0072b2'))` at the top
level, `marks.yellow` is the member `yellow` of the palette, and not the color `yellow`.

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
declaration fits the form: for `(name S)`, a type that fits all of them, and for `(like …)`, the
conditions of {numref}`like-copies`. The expand step replaces each
by the name that `S` gives in each copy, and then makes the `(like …)` copy of that row.
```

For example, take this `foreach`:

```mtp
(foreach k 5
  (circle #'d-{k}' (pos [k 0]) (r (if (= k 0) 1 (/ #'d-{(- k 1)}'.r 2)))))
```

The prover proves its body once, for k from 0 to 4. In the branch of the `if` that is taken for k
from 1 to 4, `#'d-{(- k 1)}'` names one of the copies `d-0` to `d-3`, each a circle that comes
before, since the prover narrows the {term}`range` of k in that branch to 1 to 4
({numref}`if-narrowing`).

:::{admonition} Code differs
:class: note
The compiler makes each copy first, and then compiles `(name S)` and `(like …)` with the values of
that copy (compiler.py:1161-1167, compiler.py:5329-5341) (mtp-08wd.1).
:::

(core-core-forms)=
## Forms that are core because a rewrite would need a value or a type

By {numref}`sugar-form`, each form below is core. Its meaning is defined in the page named in the
inventory.

- **`(. X Y)`.** Whether `Y` is an attribute depends on `X` ({numref}`dot-name-part`).
- **`foreach`.** The number of copies is a value, and `(foreach i n …)` is told apart from
  `(foreach x xs …)` by the type of the second item ({numref}`foreach-count`).
- **A motif instance.** Its members are the motif's body with the values of its parameters, made in
  the expand step.
- **A use of an animation.** Its moves are the animation's body with the values of its parameters, made in
  the expand step, as for a motif instance.
- **A variant instance.** It is its base shape with the variant's parameters as attributes, some
  attributes fixed, and the variant as its type. No core form of a shape carries these.
- **`row` and `column`.** Each member is placed after the box of the member before. A rewrite into
  a group with a `translate` on each member would make each member read its own box, which
  depends on that translate.
- **`colormap`.** Its positions must be known when compiling and must not decrease, and the steps
  of a discrete map are worked out from them, so its rewrite needs their values. Each call is
  compiled where it is written, so that the colors that it mixes stay the tokens that they read.
- **`exists-when`.** Its condition may read what is declared between the shape and the
  `exists-when`, so it cannot be moved into the declaration of the shape
  ({numref}`declare-before-use`).
- **`let`.** A rewrite that put each value in place of each use would compute it once for each use,
  with a site of its own for each random call. A rewrite into a variable needs the value's type.
- **`(defaults …)` on an instance.** The members of an instance are made only in the expand step,
  so the prover proves that each value fits its attribute.
- **`(defaults …)` in a score.** A default ease does not apply
  to a move of a {term}`bool`, a string or a choice, so writing the ease into each move needs the
  type of its target. A default duration also applies to the name of a movement in the body, which
  cannot be given a duration without making a new movement.
- **A score of one item.** It is one step, while its item may be several: a play of
  `(in-order (in-order a b))` has one step, and a play of `(in-order a b)` has two.
- **`(map n f)` with an int `n`.** It means `(map (range 0 n) f)`, and is told apart from
  `(map xs f)` by the type of `n`. This is part of the typing of the built-in function `map`
  ({doc}`stdlib`).
- **The {term}`operators <operator>`, `not`, `abs`, `or?`, `none?`, `some?`, `somes` and the box
  points.** They are built-in functions, which the compiler reads itself ({numref}`built-ins`), so
  a declared function may take their names ({numref}`declaration-names`).

(core-inventory)=
## Inventory of heads

Each table lists the heads of one context. The column "Defined in" gives the page where a core
form's meaning is defined, the rule for a syntactic sugar form, or {doc}`stdlib` for a built-in.

(top-level-heads)=
### Top-level forms

The top level of a source holds only the heads of this table and `let`
({numref}`body-let-foreach`), with at most one `scene`.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `import` | core | `(import F)` or `(import F N…)`: the declarations of another file | {doc}`imports` |
| `type` | core | `(type N BASE C…)`: a name for a {term}`refined type` | {numref}`type-notation` |
| `interface` | core | `(interface N (T A C…)…)`: typed attributes that an object must have | {doc}`types` |
| `record` | core | `(record N MEMBER…)`: a mutable object that is not drawn | {doc}`world-model` |
| `palette` | syntactic sugar | `(palette N (M C)…)`: a record of colors | {numref}`sugar-rewrites` |
| `parametric` | syntactic sugar | `(parametric N XS F ARGS…)`: a polyline through the points of the curve `F` at the values of the list `XS` | {numref}`sugar-rewrites` |
| `colormap` | core | `(colormap N [C…] ITEM…)`: a function from a {term}`real` to a color | {doc}`evaluation` |
| `scene` | core | `(scene N ITEM…)`: the scene, of which a source holds at most one | {doc}`world-model` |
| `formula` | core | `(formula N TEX ITEM…)`: typeset math with terms, whose string `TEX` is its positional argument | {doc}`world-model` |
| `motif` | core | `(motif N PARAMS ITEM…)`: a template of shapes | {doc}`world-model` |
| `variant` | core | `(variant N PARAMS SHAPE)`: a new type of shape | {doc}`types` |
| `func`, `func[T]` | core | `(func N PARAMS BODY)`: a named function | {doc}`types`, {doc}`evaluation` |
| `movement` | core | `(movement N TARGET ITEM…)`: a named trajectory | {doc}`time` |
| `animation` | core | `(animation N (P…) ITEM…)`: a template of movements, as a motif is a template of shapes | {doc}`time` |
| `primitive` | core | `(primitive N)`, only in a file of the standard library: the name `N` for a {term}`primitive` | {numref}`primitive-form` |
| `foreach` | core | copies of its declarations, made in the expand step | {doc}`binding-time` |
| `(T N …)` for a type `T` | core | a variable, among them `color` and `font` tokens and `rand-seed` seeds | {doc}`world-model`, {doc}`reaction` |
| {term}`components <component>` | core | {term}`views <view>` and controls (see "Components and their items") | {doc}`page-interface` |
| `doc` | core | a {term}`docstring`, kept in the .mtpc | {doc}`compiled-format` |

So a source need not hold a scene: `(real a 1) (readout r f'{a}')` is a world model with a
variable and a readout, and an empty file is a world model with nothing in it. A source with two
scenes is an error.

:::{admonition} Code differs
:class: note
The error for a second scene is "a file has exactly one scene" (`compiler.py:4854`). Bead
mtp-ydd4.7.59.
:::

### Variables and constraints

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `(T N VALUE C…)` | core | a variable of type `T`, free or bound | {doc}`world-model`, {doc}`reaction` |
| `list` with no item type | core | a list whose item type is the type of its value | {doc}`types` |
| `font` | core | `(font N PART…)`: a font token, given by its parts | {doc}`world-model` |
| `family`, `style`, `weight`, `size` | core | the parts of a font | {doc}`world-model` |
| `like` in a font | syntactic sugar | copies the parts of another font | {numref}`like-copies` |
| `free` | core | `(free X)`: a free value that starts at the value of `X`, written only as the value of a variable or of an attribute | {doc}`reaction`, {doc}`binding-time` |
| `>=`, `>`, `<=`, `<` with one number | core | a bound | {doc}`types` |
| `length` | core | the length of a list | {doc}`types` |
| `one-of` | core | the choices of a string | {doc}`types` |
| `const` | core | a variable or an attribute that rejects every attempted write | {doc}`data-model` |
| `mod` | core | `(mod T lo hi)`: a modular type, whose numbers wrap into an interval | {doc}`types` |

### Type notation

| Notation | Kind | What it is | Defined in |
|---|---|---|---|
| `int`, `ratio`, `real`, `complex`, `unit`, `ease`, `curve`, `bool`, `string`, `color`, `font`, `point`, `transform`, `movement`, `none`, `scene` | core | the {term}`built-in types <built-in type>` | {doc}`types` |
| `circle` and the other shape names | core | the shape types | {doc}`types` |
| `shape`, `positioned`, `sequence`, `sequence[T]` | core | the built-in {term}`interfaces <interface>` | {doc}`types` |
| `list[T]` | core | lists | {doc}`types` |
| `func[P… R]` | core | function types | {doc}`types` |
| `T\|none` | core | a type that allows `none` | {doc}`types` |
| `(T C…)` | core | a refined type | {doc}`types` |
| `colormap` | core | `func[real color]` | {numref}`the-types` |
| a name declared by `type` | core | the type that it names | {numref}`type-notation` |
| a name declared by `interface`, `motif` or `variant` | core | that type | {doc}`types` |
| `rand-seed` | core | the type of seeds, any int | {doc}`types`, {doc}`evaluation` |

### The scene, shapes and containers

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `background` | core | the scene's background | {doc}`world-model` |
| `transform` in the scene | core | how the scene's coordinates are drawn | {doc}`world-model` |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `bezier`, `arc`, `ring`, `text` | core | the shapes | {doc}`world-model` |
| `group` | core | a container | {doc}`world-model` |
| `row`, `column` | core | a group that places its members one after another | {doc}`world-model` |
| `(M N …)` for a motif `M` | core | an instance, an object of kind `instance` | {doc}`world-model` |
| `(V N …)` for a variant `V` | core | an instance of a variant | {doc}`world-model` |
| `(H\|none N …)` for a shape head `H` | core | a shape that may not exist | {doc}`world-model` |
| `exists-when` | core | `(exists-when N C)`: when a shape exists | {doc}`world-model` |
| `let` in a body | core | values worked out once, where the `let` is written | {doc}`binding-time` |
| `foreach` in a body | core | copies of declarations | {doc}`binding-time` |
| a variable in the scene | core | as at the top level | {doc}`world-model` |

### Arguments of shapes and containers

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `x`, `y`, `translate`, `transform`, `fill`, `stroke`, `stroke-width`, `opacity`, `fill-opacity`, `stroke-opacity`, `line-cap`, `line-join`, `drawn`, `pointer-events` on a shape, `r`, `width`, `height`, `rx`, `ry`, `from`, `to`, `a`, `b`, `c`, `points`, `controls`, `head-start`, `head-end`, `head-size`, `value`, `halign`, `valign`, `font` | core | an attribute of the shape | {doc}`world-model` |
| `pos` | syntactic sugar | `x` and `y` given as one point | {numref}`sugar-rewrites` |
| `dash` | core | `(dash L O)`: the dash lengths `L`, and the offset `O`, which is 0 when it is left out | {doc}`world-model` |
| `like` | syntactic sugar | copies another shape's arguments | {numref}`like-copies` |
| `defaults` on a group, a row or a column | core | what a container gives its members | {numref}`container-defaults` |
| `clip` | core | a shape that the members are drawn inside | {doc}`world-model` |
| `fixed-size` | core | a group whose members are measured in screen pixels | {doc}`world-model` |
| `gap`, `align` | core | the spacing and alignment of a row or a column | {doc}`world-model` |

### Motifs and variants

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a parameter `(T N DEFAULT?)` | core | a parameter of a motif, variant, function or animation | {doc}`types` |
| a shape, a bound variable, `foreach`, `let` or `exists-when` in a motif's body | core | the members and values of each instance | {doc}`world-model` |
| `self` | core | the instance being built, inside a motif's body | {doc}`scope` |
| a parameter given to an instance, `(P X)` | core | the parameter's value | {doc}`world-model` |
| `x`, `y`, `translate`, `transform` on an instance | core | the instance's frame | {doc}`world-model` |
| `pos` on an instance | syntactic sugar | as on a shape | {numref}`sugar-rewrites` |
| `clip` on an instance | core | as on a group | {doc}`world-model` |
| `defaults` on an instance | core | what the instance gives the members that its motif makes | {doc}`world-model` |
| `like` on an instance or a variant instance | syntactic sugar | copies another instance's items | {numref}`like-copies` |

The rules about a declaration that reads itself or its container, such as a default that reads
its own group, are to be redesigned around `self`. Until then, the rules of today hold
({numref}`self-reference-today`).

### Records, palettes and interfaces

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a variable in a record | core | a member, kept as `N.M` | {doc}`world-model` |
| `record`, `palette` in a record | core, syntactic sugar | a record inside a record | {doc}`world-model`, {numref}`sugar-rewrites` |
| `(M C)` in a palette | syntactic sugar | `(color M C)` | {numref}`sugar-rewrites` |
| `(T A C…)` in an interface | core | an attribute that an object must have | {doc}`types` |

### Formulas and terms

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a string known when compiling | core | the formula's LaTeX, which marks its terms | {doc}`world-model` |
| `term` | core | `(term T ITEM…)`: a term's attributes | {doc}`world-model` |
| `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding` in a term | core | a term's attributes | {doc}`world-model` |
| a string in a term | core | the LaTeX that the term shows | {doc}`world-model` |
| `like` in a term | syntactic sugar | copies another term's form | {numref}`like-copies` |
| `defaults` in a formula | core | attributes for every term | {numref}`formula-defaults` |
| `exists-when` in a formula | core | when a term exists | {doc}`world-model` |
| a variable in a formula | core | a member, kept as `F.M` | {doc}`world-model` |

### Special forms and other expressions

The heads of this table that are written as {term}`words <word>`, from `.` to `type-of`, are
{term}`keywords <keyword>` ({numref}`keywords`).

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a literal | core | a number, string, TeX string, bool, `none` or list literal | {doc}`lexical`, {doc}`types` |
| a name | core | what the name refers to | {doc}`scope` |
| a name with several name parts, `N.A`, `N[X]` | syntactic sugar | | {numref}`sugar-rewrites` |
| `.` | core | `(. X Y)`: an attribute, member, item or key of `X` | {numref}`dot-name-part` |
| `name` | core | `(name S)`: the name whose text is `S`, known when compiling | {doc}`scope`, {numref}`names-from-values` |
| `if` | core | `(if C A B)` | {doc}`evaluation` |
| `when` | syntactic sugar | `(when C X)` | {numref}`sugar-rewrites` |
| `cond`, `else`, `and`, `or` | syntactic sugar | | {numref}`sugar-rewrites` |
| `let` | core | `(let ((N V)…) BODY)` | {doc}`scope`, {doc}`evaluation` |
| `fn` | core | `(fn PARAMS BODY)`: a function written in place | {doc}`types`, {doc}`evaluation` |
| `as` | core | `(as T LITERAL)`: a literal given a type | {doc}`types` |
| `type-of` | core | `(type-of X)`: the type of `X`, as a string | {doc}`types` |
| `concat` | core | `(concat A B …)`: the strings `A`, `B`, … joined in order. An interpolated string `f'…'` is syntactic sugar for it ({numref}`parser-sugar`) | {doc}`evaluation` |
| `fmt` | core | `(fmt X S)`: the value of `X` written as a string, by the {term}`format spec` `S`, in Python's format-spec mini-language. `S` is known when compiling, and is `''` when it is left out. `(concat)` is `''` | {doc}`evaluation` |
| `free` | core | see "Variables and constraints". In an expression it is a compile error | {doc}`reaction` |
| `(F A…)` for a declared function `F` | core | a call | {doc}`evaluation` |
| `(L A…)` for a local function value `L` | core | a call of a function held by a parameter or a `let` name | {doc}`evaluation` |

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
| `move` | core | `(move TARGET ITEM…)`: a movement written in place | {doc}`time` |
| `from`, `to`, `duration`, `path` | core | the parts of a movement | {doc}`time` |
| `ease` | core | a function from 0 to 1, such as the value of `(steps N)` | {doc}`time` |
| `like` in a movement or a move | syntactic sugar | | {numref}`like-copies` |
| an animation's body of several items | syntactic sugar | one `in-order` | {numref}`sugar-rewrites` |
| `defaults` in a score | core | a duration, an ease and a lag for the movements inside | {doc}`time` |
| `loop` | core | `(loop)` or `(loop N)` | {doc}`time` |
| `score` | core | `(score ITEM…)`: a collection of movements, each placed in time by its own `lag`, as a group is a collection of shapes, written wherever a movement goes | {doc}`time` |
| `lag` | core | `(lag R)` on a movement: it starts once the member before it in its score is the fraction `R` of the way through. `R` is a number from 0 up, and the first member starts when the score starts | {doc}`time` |
| `in-order`, `at-once` | syntactic sugar | a score whose members run one after another, or together | {numref}`sugar-rewrites` |
| `foreach` in a score | core | puts its moves where it is written | {doc}`time`, {doc}`binding-time` |
| the name of a movement, or of an animation with no parameters, in a score | core | plays what it names | {doc}`time` |
| `wait` | syntactic sugar | `(wait T)`: a step of `T` seconds in which nothing moves. With `T` left out, it lasts as long as a move with no `(duration …)` | {numref}`sugar-rewrites` |
| `jump` | syntactic sugar | `(jump V X)`: a move of no duration | {numref}`sugar-rewrites` |
| a use of an animation | core | a movement of the animation's type, with the values of its arguments, as one step | {doc}`time`, {numref}`animation-step` |

### Components and their items

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `canvas`, `readout`, `display` | core | the views | {doc}`page-interface`, {doc}`lifecycle` |
| `slider`, `button`, `play`, `stepper`, `toggle` | core | the controls | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove` | core | listeners on a shape or a term, or for `on-pointermove`, on its canvas | {doc}`reaction`, {doc}`concurrency` |
| `on-show`, `on-hide` | core | listeners that play while a canvas starts or stops drawing a shape | {doc}`reaction`, {doc}`lifecycle` |
| `on-view`, `on-ready`, `on-live`, `on-quiet` | core | listeners on their own view | {doc}`lifecycle` |
| `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom` on a canvas | core | the view box and how the {term}`reader` may move it. `(zoom LO HI)` lets the reader zoom from `LO` to `HI` times, and a canvas without it does not zoom. `(pan B)` says whether the reader may pan, and is `false` when it is left out | {doc}`page-interface` |
| `toggle-duration`, `toggle-ease` | core | how a canvas fades its items in and out | {doc}`time`, {doc}`page-interface` |
| a name, a list literal or an expression in a canvas | core | what the canvas draws | {doc}`page-interface` |
| `font` on a readout | core | the readout's font | {doc}`page-interface` |
| `kind` on a display | core | `'block'` or `'inline'` | {doc}`page-interface` |
| a movement on a control or a listener | core | what the writer plays: a move, a score, or a use of an animation. A writer has at most one | {doc}`reaction`, {doc}`time` |
| the move of a slider | core | a `move` or the name of a movement, its first item | {doc}`page-interface`, {doc}`reaction` |
| the target of `toggle`, `on-pointermove` | core | a name | {doc}`reaction` |
| the target of `on-drag` written as a move | core | `(move TARGET (to X))` | {doc}`reaction`, {numref}`drag-group-shift` |
| the target of `on-drag` written as a name | syntactic sugar | the move of the shape's position | {numref}`sugar-rewrites` |
| `label` | core | a control's label, a string | {doc}`page-interface`, {doc}`accessibility` |
| `stops` on a slider | core | the number of positions of its knob. A slider whose target is an `int` and that gives no `stops` stops at each whole number from its `from` to its `to`, and both of these are then known when compiling, or the source is a {term}`compile error` | {doc}`page-interface` |
| `buttons`, `rest`, `labels` on a play | core | its bars, its rest between steps, its step names | {doc}`page-interface`, {doc}`time` |
| `selected` on a button | core | whether it is the current choice | {doc}`page-interface`, {doc}`accessibility` |
| `active` | core | whether the writer acts | {doc}`reaction` |
| `priority` | core | the writer's priority | {doc}`concurrency` |
| `stop-propagation` | core | whether an event goes up the scene tree | {doc}`reaction` |
| `in` | core | the views that a control belongs to | {doc}`page-interface`, {doc}`lifecycle` |
| a condition | core | a bool form that limits what a writer writes | {doc}`reaction` |
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
| a control, a listener | conditions, such as `(>= k 0)` | yes |
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

(core-summary)=
## Summary

| Head | Kind | Rewrite or defining page |
|---|---|---|
| `H@X`, `#'…'`, `[…][X]` | syntactic sugar, made by the parser | {numref}`parser-sugar` |
| `(H_ …)` | syntactic sugar, made by the parser | {numref}`unnamed-head` |
| `N.A`, `N[X]` | syntactic sugar | {numref}`sugar-rewrites` |
| `when`, `cond`, `and`, `or` | syntactic sugar | {numref}`sugar-rewrites` |
| `palette`, `parametric` | syntactic sugar | {numref}`sugar-rewrites` |
| `like` | syntactic sugar, or core with a `(name …)` | {numref}`like-copies`, {numref}`names-from-values` |
| `pos` | syntactic sugar | {numref}`sugar-rewrites` |
| `foreach` with a list of names | syntactic sugar | {numref}`sugar-rewrites` |
| a name as the target of `on-drag` | syntactic sugar | {numref}`sugar-rewrites` |
| `wait`, `jump`, `in-order`, `at-once`, an animation's body of several items | syntactic sugar | {numref}`sugar-rewrites` |
| `import` | core | {doc}`imports` |
| `type`, a name declared by `type` | core | {numref}`type-notation` |
| `defaults` on a group, a row or a column, and in a formula | core | {numref}`container-defaults`, {numref}`formula-defaults` |
| `interface`, `record` | core | {doc}`types`, {doc}`world-model` |
| `colormap` | core | {doc}`evaluation` |
| `scene`, `background`, `transform` in the scene | core | {doc}`world-model` |
| `formula`, `term` and the attributes of a term | core | {doc}`world-model` |
| `motif`, a motif instance, `self`, `defaults` on an instance | core | {doc}`world-model`, {doc}`scope` |
| `variant`, a variant instance | core | {doc}`types`, {doc}`world-model` |
| `func`, `func[T]`, `fn`, calls | core | {doc}`types`, {doc}`evaluation` |
| `movement`, `move` and their parts | core | {doc}`time` |
| `animation` and its uses | core | {doc}`time`, {numref}`prove-bodies-once` |
| `primitive` | core | {numref}`primitive-form` |
| `score`, `lag`, `loop`, `defaults` in a score | core | {doc}`time`, {numref}`animation-step` |
| `foreach` | core | {numref}`foreach-count`, {numref}`foreach-bounded-length`, {doc}`binding-time` |
| `let` | core | {doc}`scope`, {doc}`binding-time` |
| `(T N …)`, a variable, `font` and its parts | core | {doc}`world-model`, {doc}`reaction` |
| `free` | core | {doc}`reaction`, {doc}`binding-time` |
| the conditions `>=`, `>`, `<=`, `<`, `length`, `one-of`, and `mod`, `is`, `&` | core | {doc}`types` |
| the type notation of "Type notation", `colormap` included | core | {doc}`types` |
| the twelve shapes | core | {doc}`world-model` |
| `row`, `column`, `gap`, `align` | core | {doc}`world-model` |
| the attribute arguments of the shapes, `dash`, `clip`, `fixed-size` | core | {doc}`world-model` |
| `exists-when` | core | {doc}`world-model` |
| `.` | core | {numref}`dot-name-part` |
| `name` | core | {doc}`scope`, {numref}`names-from-values` |
| `if`, `as`, `type-of` | core | {doc}`evaluation`, {doc}`types` |
| `doc` | core | {doc}`compiled-format` |
| the views, the controls and their items | core | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| the fourteen listeners | core | {doc}`reaction`, {doc}`concurrency`, {doc}`lifecycle` |
| a move as the target of `on-drag` | core | {doc}`reaction`, {numref}`drag-group-shift` |
| a condition | core | {doc}`reaction` |
| the operators, `not`, `abs`, the `none` functions and the box points | built-in | {numref}`built-ins` |
| the built-in functions and the collections, `map` over an int included, `steps` | built-in | {doc}`stdlib` |
| the primitives | standard library | {numref}`primitive-form` |
| the constants | built-in |
| the files of the standard library | standard library | {doc}`stdlib` |
