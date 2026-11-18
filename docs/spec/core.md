(core)=
# Core and derived forms

On this page, every {term}`head` that the {term}`compiler` accepts is sorted into three kinds:
{term}`core form`, {term}`syntactic sugar` and {term}`library`. Each syntactic sugar {term}`form` is given as a
{term}`rewrite` into core forms. Each core form is given with the page of the spec where its
meaning is defined.

This page specifies the language.

(core-kinds)=
## Kinds of form

The head of a form is its first item ({numref}`form-template`): `if` in `(if c a b)`, `circle` in
`(circle p (r 1))`. An item of a form is also called by its head, so `(r 1)` is an `r` item.

```{rule} kinds-of-form
Every head belongs to exactly one of three kinds: syntactic sugar ({numref}`sugar-form`), library
({numref}`library-form`) or core. A head that is neither syntactic sugar nor library is core.
```

```{rule} sugar-form
A form is syntactic sugar if and only if it can be rewritten into core forms without computing any value and
without using any type. Looking up a {term}`name` is neither, since lexical scope is fixed by the
text, so a rewrite may resolve a name and read the text of the declaration or the binding that the
name refers to.
A form that needs a value or a type to be rewritten is core.
```

```{rule} library-form
The library is the built-in functions, which are implemented natively, and the files of the
standard library, which are written in mtp. A call of a library function is a call, which is a
core form. The library holds functions, constants
and declarations, and no form of the language.
```

By {numref}`declaration-names`, a declared function may take the name of a library function: after
`(func + ((real a) (real b)) 7)`, `(+ 1 2)` is 7.

The compiler rewrites every syntactic sugar form before the prove step ({numref}`compile-steps`), so
the {term}`prover` is given only core forms. The prover proves the {term}`body` of each `foreach`,
motif and choreo only once, before any copies are made ({numref}`prove-bodies-once`). At that point
the names of a `foreach` and the parameters of a motif or a choreo have no value yet, so a form
whose rewrite would need one of their values is core ({numref}`names-from-values`).

### How a rewrite is written

A rewrite is a pair of mtp fragments: the form as written, then the core forms that it means. In
a fragment, a name in capitals stands for any text of the kind that the rule names: `X` for an
{term}`expression`, `N` for a name, `T` for a type, `ARGS…` for any number of items. Everything else
is written as it is.

(core-rewrites)=
## Rewrite rules

The {term}`parser` makes the rewrites of the lexical shorthands while it reads the source:
a prefixed form `H@X`, a {term}`name string` `#'…'`, a part after a {term}`list` {term}`literal`,
`[…][X]` ({numref}`shorthand-forms`), and a head that ends with `_` ({numref}`unnamed-head`). Every
other syntactic sugar form is in the table of the rule below.

(rewrite-when)=
(rewrite-roll-dice)=
```{rule} sugar-rewrites
Each form in the first column of this table is syntactic sugar, and means exactly the core forms in the
second column, when the conditions in the third column hold. A syntactic sugar form whose conditions do not
hold is a {term}`compile error`. A rewrite may move text or copy it, and each name in the moved or
copied text refers to what it referred to where it was written. A rewrite may give
syntactic sugar forms, which are rewritten in turn, until no syntactic sugar form is left. A `(like …)` is rewritten
before any other rewrite of the declaration that it copies.

| Written | Means exactly | Conditions |
|---|---|---|
| `N.A`, `N[X]` | `(. N A)`, `(. N X)`. A chain is rewritten from left to right: `p.pos.x` is `(. (. p pos) x)`, and `g[0].r` is `(. (. g 0) r)` | The name is written as an expression or as the target of a writer. A head and the name of a declaration are not rewritten |
| `(when C X)` | `(if C X none)` | Exactly two arguments |
| `(cond (C1 V1) MORE… (else V))`, `(cond (else V))` | `(if C1 V1 (cond MORE… (else V)))`, `V` | |
| `(and A B MORE…)`, `(and A)` | `(if A (and B MORE…) false)`, `A` | |
| `(or A B MORE…)`, `(or A)` | `(if A true (or B MORE…))`, `A` | |
| `(maybe T)`, in a type | `T\|none` | |
| the type `colormap` | the type `func[real color]` | |
| a type `N`, declared `(type N BASE C…)` | the type `(BASE C…)` | |
| `(range X)` | `(range 0 X (gap 1))` | `X` is not a `(gap …)` or `(num …)` item |
| `(R ARGS…)`, with `R` a name of the primitive `rand`, `rand-int`, `pick` or `shuffle` ({numref}`primitive-form`), and no `(seed …)` | `(R ARGS… (seed S))` | `S` is the {term}`default seed` of the file that holds the form ({numref}`default-seed`) |
| `(D)`, with `D` a name of the choreo `roll-dice` of the file rand of the standard library ({ref}`stdlib-rand`) | `(D S)` | `S` as for a random function |
| `(jump V X)`, where a move may be written | `(move V (to X) (duration 0))` | Exactly two arguments |
| `(import F)` | the top-level declarations of `F.mtp`, after its own rewrites, each under the name `F.N`. Each `F.N` and each `(. F N)` in the source is a use of that name | `F.mtp` holds only what a {term}`file to import` holds ({numref}`import-file-holds`). A file imported several times, directly or through other files, is put in once |
| `(import F N1 N2…)` | the same, and each `Ni` in the source is a use of `F.Ni` | Each `Ni` is a name that `F.mtp` gives ({numref}`import-files`) |
| `(palette N (M C)…)` | `(namespace N (color M C)…)` | Each item is `(M C)` |
| `(parametric N (for T LO HI) E ITEMS…)` | `(polyline N (points (map (range LO HI (num S)) (fn T E))) ITEMS…)`, where `S` is the `S` of a `(samples S)` among `ITEMS…`, which the polyline does not get, or 361 when there is none | `T` is a name. At most one `(samples S)` |
| `(K N (like M) ARGS…)` | `(K N ARGS… COPIED…)`. `COPIED…` is each item of the declaration of `M`, as written, after its own `(like …)` is rewritten, whose head `ARGS…` does not give. A positional {term}`string` of a text is copied too. A `(pos P)` of `M` gives both `x` and `y`: when `ARGS…` gives exactly one of them, `COPIED…` holds the other, `(x (. P 0))` or `(y (. P 1))` | `M` is a plain name. `K` is a shape head other than `group`, `row` and `column`, and `M` a shape of kind `K`. Or `M` is an instance of the motif or the variant `K`. Or `K` is `font` and `M` a font. Or `K` is `term` and `M` a term of the same formula, whose `(term …)` form comes before. Or the form is a `move` or a `transition`, and `M` is a transition declared at the top level |
| `(pointer-events B)`, on a group, a row, a column or an instance | the same container, with `(pointer-events B)` moved into its `(defaults …)`, which is added when it has none | Its `(defaults …)` gives no `pointer-events` |
| `(defaults (A V)…)`, on a group, a row or a column | the same container without it, with each `(A V)` added to each member, at any depth, that takes `A` from a container ({doc}`world-model`) and does not give `A`, the nearest container first. For a member that is an instance, `(A V)` is added to the instance's own `(defaults …)` | Each `A` is one that a container gives its members ({doc}`world-model`) |
| `(defaults (A V)…)`, in a formula | the same formula without it, with each `(A V)` added to the `(term T …)` form of each term `T` of the formula that does not give `A`, and a form `(term T (A V)…)` added for each term that has none | The terms are those marked in the formula's string |
| `(dash L)` | `(dash L 0)` | |
| `(pos [X Y])` | `(x X) (y Y)` | |
| `(pos P)` | `(x (. P 0)) (y (. P 1))` | `P` is not a list literal, and holds no call of `rand`, `rand-int`, `pick` or `shuffle` |
| `(pos free@[X Y])`, `(pos free@P)` | `(x free@X) (y free@Y)`, `(x free@(. P 0)) (y free@(. P 1))` | As for `(pos P)` |
| `(foreach ((N1 S1) (N2 S2) MORE…) ITEMS…)`, `(foreach ((N S)) ITEMS…)` | `(foreach N1 S1 (foreach ((N2 S2) MORE…) ITEMS…))`, `(foreach N S ITEMS…)` | The names are all different |
| `(wait T)`, `(wait)`, in an animation's body | `(move none (duration T))`, `(move none)` | |
| `(animation OPT… A B MORE…)`, and the body of a choreo | `(animation OPT… (in-order A B MORE…))` | `OPT…` are the {term}`named arguments <named argument>` of the animation, the `(defaults …)` and the `(loop …)` |
| `(on-drag S M.pos ITEMS…)`, `(on-drag S M.x ITEMS…)`, `(on-drag S M.y ITEMS…)` | `(on-drag S (move M.pos (to pointer)) ITEMS…)`, `(on-drag S (move M.x (to (. pointer 0))) ITEMS…)`, `(on-drag S (move M.y (to (. pointer 1))) ITEMS…)` | `M` names the shape or the term `S` |
```

Of the declarations that an `(import …)` puts in, the {term}`.mtpc` holds only those that the source
uses ({numref}`mtpc-imported-declarations`).

A use of a choreo, `(C A1 … Ak)`, is core, as a motif instance is. It is written where a move, an
animation or a step of an animation's body may be written, and k is at least the position of the
last parameter with no default. In the expand step it becomes an `(animation …)` whose body is the
body of the choreo, with each parameter replaced by the value of its argument, or by its default
when the use gives no argument for it. So a use written as a step of an animation's body is one
step ({numref}`animation-step`). The prover proves that each argument {term}`fits <fit>` the type
of its parameter. An argument may be any expression that may be written in the body in the places
where its parameter is written, so `(pulse (* 2 k))` is an error when the parameter is a duration,
by {doc}`binding-time`, and is accepted when it is a `to`. A parameter stands for a value or a
shape, never for a variable: a move in the body may move an attribute of a shape given as a
parameter, such as `who.opacity`, and never the parameter itself. The one exception is a parameter
of type `rand-seed`, which stands for a seed: its argument is the name of a seed, and in the body
the parameter is replaced by that seed and not by its value, so a move of the parameter moves the
seed. Any other argument for such a parameter is a compile error, "the argument for P is the name
of a seed, as in (C dots)". So the choreo `roll-dice` of the file rand,
`(choreo roll-dice ((rand-seed s)) (jump s (next-seed s)))`, moves the seed that its use names.

:::{admonition} Code differs
:class: note
The compiler writes each use of a choreo out where it is written (compiler.py:1669-1729), proves
the body again for each use, compiles a choreo whose parameters all have defaults once more without
a use, and binds a parameter that is not a seed and is given a name to that name, so that a move of
the parameter moves what it names (mtp-ydd4.7.56).
:::

Since `(like M)` copies what `M` was written with in the source, a copy does not get the defaults
of `M`'s container: `(circle b (like a))` outside the group of `a` has only what `a` was written
with. The copy follows what `M`'s items read: if the radius of `M` is `(* 2 k)`, so is the radius
of the copy. The defaults of an instance, and its `pointer-events` and its `clip`, are items of it,
so `(like M)` copies them.

Since a copied random call is a {term}`site` of its own ({numref}`random-site`),
`(pos (pick corners))` would draw `x` and `y` at two sites, so it is an error. A body `let` holds
the point once: `(let ((q (pick corners))) (circle c (pos q)))` is `(x (. q 0)) (y (. q 1))`, which
reads one value.

:::{admonition} Code differs
:class: note
The compiler makes these rewrites while it compiles each form, in the same functions that check
it, and not in a step of their own (for example compiler.py:6471-6479 for `when`, 3074-3087 for
`wait`, 3745-3764 for an animation item, 1669-1729 for a choreo use, 745-826 for imports,
5543-5576 for the defaults of a group). Beads mtp-08wd.5, mtp-08wd.6, mtp-08wd.7, mtp-08wd.8
and mtp-08wd.2 will make them in the rewrite step. Where the result differs today:

- `p.r` is read as one name with {term}`name parts <name part>` (parse.py:337-395), and each name
  part after the first as an attribute (compiler.py:5953-5960), so with a local `r`, `xs.r` is an
  error while `(. xs r)` is an item of `xs` (mtp-ydd4.7.5).
- `(like M)` on an instance copies neither its `pointer-events` (compiler.py:4749, 4759-4762) nor
  its `clip` (mtp-ydd4.7.20).
- `(wait T)` makes no transition object, while `(move none (duration T))` does
  (compiler.py:3074-3087, 3184-3197). The two .mtpc files differ by that object (mtp-ydd4.7.21).
- A palette has the type `palette` (compiler.py:1454, types.py:148-162), and the namespace that it
  means has the type `namespace` (mtp-ydd4.7.22).
- `(cond (else V))` is {term}`folded <folding>` to the value of `V` and, since it is not a literal,
  marked const (compiler.py:5653-5657), so `(real v (cond (else 3)))` makes `v` a constant, while
  `(real v 3)` is a free variable that a writer may write (mtp-ydd4.7.46).
- `_through` (compiler.py:7280-7290) rewrites only a name with several name parts, so after
  `(import lib)`, `lib.k` is accepted, and `(. lib k)` is a compile error, "unknown name 'lib'"
  (compiler.py:6056) (mtp-ydd4.7.47).
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

### Dragging a group

```{rule} drag-group-translate
In an `on-drag` on a group, a row or a column, whether its `fixed-size` is true or not, a move
whose target is the `pos`, the `x` or the `y` of that same container writes the container's
`translate` in place of the target: all of it for `pos`, its first number for `x`, and its second
number for `y`. In that move, `pointer` is the `translate` of the container at the press plus the
motion of the pointer since the press, in the frame of the container's container.
```

By {numref}`sugar-rewrites`, `(on-drag g g.pos)` is `(on-drag g (move g.pos (to pointer)))`, so
both spellings move the group by its `translate`, and the members keep their own positions.

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
`(foreach N X ITEMS…)`, where `X` is an {term}`int`, means exactly `(foreach N (range X) ITEMS…)`.
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
`(foreach k (range n) …)` both make 5 copies, and copies 3 and 4 do not exist while `n` is 3.

:::{admonition} Code differs
:class: note
The compiler makes the bounded copies for a count (compiler.py:880-915), but rejects a list whose
length is known only while drawing, `(range n)` included, with "the length of the list a foreach
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
the list `xs`, as `(. xs r)` is. A member of a namespace, a palette, a formula or an instance is
read by its name, even when another declaration or a binding has the same name. So with
`(color yellow '#ffd700')` and `(palette marks (yellow '#e6c200') (blue '#0072b2'))` at the top
level, `marks.yellow` is the member `yellow` of the palette, and not the color `yellow`.

:::{admonition} Code differs
:class: note
compiler.py:6540-6549 reads `Y` as an attribute only when `has_attr` (compiler.py:6175-6188) finds
one, and `has_attr` finds no member of a namespace or a formula. So `(. marks yellow)`
reads the color `yellow` as a key (mtp-ydd4.7.19).
:::

### An animation written as a step

```{rule} animation-step
An `(animation ITEM…)` written as an item of an animation's body is one step of that body. It plays
its own body, a `(loop …)` included, as the name of an animation with the same body does
({doc}`time`). The `(defaults …)` around it do not apply inside it.
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
conditions of the row for `(like M)` in {numref}`sugar-rewrites`. The expand step replaces each
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
- **A use of a choreo.** Its moves are the choreo's body with the values of its parameters, made in
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
- **`(defaults …)` in an animation, an `at-once` or an `in-order`.** A default ease does not apply
  to a move of a {term}`bool`, a string or a choice, so writing the ease into each move needs the
  type of its target. A default duration also applies to the name of a transition in the body, which
  cannot be given a duration without making a new transition.
- **An `in-order` or an `at-once` of one item.** It is one step, while its item may be several: a
  play of `(animation (in-order (in-order a b)))` has one step, and a play of
  `(animation (in-order a b))` has two.
- **`(map n f)` with an int `n`.** It means `(map (range n) f)`, and is told apart from
  `(map xs f)` by the type of `n`. This is part of the typing of the library function `map`
  ({doc}`stdlib`).
- **The {term}`operators <operator>`, `not`, `abs`, `or?`, `none?`, `some?`, `somes` and the box
  points.** They are library functions, which the compiler reads itself ({numref}`library-form`), so
  a declared function may take their names ({numref}`declaration-names`).

(core-inventory)=
## Inventory of heads

Each table lists the heads of one context. The column "Defined in" gives the page where a core
form's meaning is defined, the rule for a syntactic sugar form, or {doc}`stdlib` for the library.

(top-level-heads)=
### Top-level forms

The top level of a source holds only the heads of this table and `let`
({numref}`body-let-foreach`), with at most one `scene`.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `import` | syntactic sugar | `(import F)` or `(import F N…)`: the declarations of another file | {numref}`sugar-rewrites` |
| `type` | syntactic sugar | `(type N BASE C…)`: a name for a {term}`refined type` | {numref}`sugar-rewrites` |
| `interface` | core | `(interface N (T A C…)…)`: typed attributes that an object must have | {doc}`types` |
| `namespace` | core | `(namespace N MEMBER…)`: a mutable object that is not drawn | {doc}`world-model` |
| `palette` | syntactic sugar | `(palette N (M C)…)`: a namespace of colors | {numref}`sugar-rewrites` |
| `parametric` | syntactic sugar | a polyline through the points of a parametric curve | {numref}`sugar-rewrites` |
| `colormap` | core | `(colormap N [C…] ITEM…)`: a function from a {term}`real` to a color | {doc}`evaluation` |
| `scene` | core | `(scene N ITEM…)`: the scene, of which a source holds at most one | {doc}`world-model` |
| `formula` | core | `(formula N ITEM…)`: typeset math with terms | {doc}`world-model` |
| `motif` | core | `(motif N PARAMS ITEM…)`: a template of shapes | {doc}`world-model` |
| `variant` | core | `(variant N PARAMS SHAPE)`: a new type of shape | {doc}`types` |
| `func`, `func[T]` | core | `(func N PARAMS BODY)`: a named function | {doc}`types`, {doc}`evaluation` |
| `transition` | core | `(transition N TARGET ITEM…)`: a named trajectory | {doc}`time` |
| `animation` | core | `(animation N ITEM…)`: a named animation | {doc}`time` |
| `choreo` | core | `(choreo N PARAMS ITEM…)`: a template of moves, as a motif is a template of shapes | {doc}`time` |
| `primitive` | core | `(primitive N)`, only in a file of the standard library: the name `N` for a {term}`primitive` | {numref}`primitive-form` |
| `foreach` | core | copies of its declarations, made in the expand step | {doc}`binding-time` |
| `(T N …)` for a type `T` | core | a variable, among them `color` and `font` tokens and `rand-seed` seeds | {doc}`world-model`, {doc}`reaction` |
| {term}`components <component>` | core | {term}`views <view>` and controls (see "Components and their items") | {doc}`page-interface` |
| `doc` | core | a {term}`docstring`, kept in the .mtpc | {doc}`compiled-format` |

So a source need not hold a scene: `(real a 1) (readout r $'{a}')` is a world model with a
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
| `like` in a font | syntactic sugar | copies the parts of another font | {numref}`sugar-rewrites` |
| `free` | core | `(free X)`: a free value that starts at the value of `X`, written only as the value of a variable or of an attribute | {doc}`reaction`, {doc}`binding-time` |
| `>=`, `>`, `<=`, `<` with one number | core | a bound | {doc}`types` |
| `length` | core | the length of a list | {doc}`types` |
| `one-of` | core | the choices of a string | {doc}`types` |
| `const` | core | a value that no writer may write | {doc}`types` |
| `wrap` | core | an interval that a number wraps into | {doc}`types` |

### Type notation

| Notation | Kind | What it is | Defined in |
|---|---|---|---|
| `int`, `ratio`, `real`, `complex`, `bool`, `string`, `color`, `font`, `point`, `transform`, `transition`, `animation`, `none`, `scene` | core | the {term}`built-in types <built-in type>` | {doc}`types` |
| `circle` and the other shape names | core | the shape types | {doc}`types` |
| `shape`, `positioned`, `sequence`, `sequence[T]` | core | the built-in {term}`interfaces <interface>` | {doc}`types` |
| `list[T]` | core | lists | {doc}`types` |
| `func[P… R]` | core | function types | {doc}`types` |
| `T\|none` | core | a type that allows `none` | {doc}`types` |
| `(T C…)` | core | a refined type | {doc}`types` |
| `(maybe T)` | syntactic sugar | `T\|none` | {numref}`sugar-rewrites` |
| `colormap` | syntactic sugar | `func[real color]` | {numref}`sugar-rewrites` |
| a name declared by `type` | syntactic sugar | the type that it names | {numref}`sugar-rewrites` |
| a name declared by `interface`, `motif` or `variant` | core | that type | {doc}`types` |
| `rand-seed` | core | the type of seeds, any int | {doc}`types`, {doc}`evaluation` |

### The scene, shapes and containers

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `background` | core | the scene's background | {doc}`world-model` |
| `transform` in the scene | core | how the scene's coordinates are drawn | {doc}`world-model` |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text` | core | the shapes | {doc}`world-model` |
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
| `dash` with two arguments | core | the dash lengths and `dash-offset` | {doc}`world-model` |
| `dash` with one argument | syntactic sugar | an offset of 0 | {numref}`sugar-rewrites` |
| `like` | syntactic sugar | copies another shape's arguments | {numref}`sugar-rewrites` |
| `defaults` on a group, a row or a column | syntactic sugar | what a container gives its members | {numref}`sugar-rewrites` |
| `clip` | core | a shape that the members are drawn inside | {doc}`world-model` |
| `fixed-size` | core | a group whose members are measured in screen pixels | {doc}`world-model` |
| `pointer-events` on a group, a row or a column | syntactic sugar | a default for the members | {numref}`sugar-rewrites` |
| `gap`, `align` | core | the spacing and alignment of a row or a column | {doc}`world-model` |

### Motifs and variants

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a parameter `(T N DEFAULT?)` | core | a parameter of a motif, variant, function or choreo | {doc}`types` |
| a shape, a bound variable, `foreach`, `let` or `exists-when` in a motif's body | core | the members and values of each instance | {doc}`world-model` |
| `self` | core | the instance being built, inside a motif's body | {doc}`scope` |
| a parameter given to an instance, `(P X)` | core | the parameter's value | {doc}`world-model` |
| `x`, `y`, `translate`, `transform` on an instance | core | the instance's frame | {doc}`world-model` |
| `pos` on an instance | syntactic sugar | as on a shape | {numref}`sugar-rewrites` |
| `clip` on an instance | core | as on a group | {doc}`world-model` |
| `defaults` on an instance | core | what the instance gives the members that its motif makes | {doc}`world-model` |
| `pointer-events` on an instance | syntactic sugar | a default for the members | {numref}`sugar-rewrites` |
| `like` on an instance or a variant instance | syntactic sugar | copies another instance's items | {numref}`sugar-rewrites` |

The rules about a declaration that reads itself or its container, such as a default that reads
its own group, are to be redesigned around `self`. Until then, the rules of today hold
({numref}`self-reference-today`).

### Namespaces, palettes and interfaces

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a variable in a namespace | core | a member, kept as `N.M` | {doc}`world-model` |
| `namespace`, `palette` in a namespace | core, syntactic sugar | a namespace inside a namespace | {doc}`world-model`, {numref}`sugar-rewrites` |
| `(M C)` in a palette | syntactic sugar | `(color M C)` | {numref}`sugar-rewrites` |
| `(T A C…)` in an interface | core | an attribute that an object must have | {doc}`types` |

### Formulas and terms

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a {term}`TeX string` | core | the formula's LaTeX, which marks its terms | {doc}`world-model` |
| `term` | core | `(term T ITEM…)`: a term's attributes | {doc}`world-model` |
| `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding`, `tex` in a term | core | a term's attributes | {doc}`world-model` |
| `like` in a term | syntactic sugar | copies another term's form | {numref}`sugar-rewrites` |
| `defaults` in a formula | syntactic sugar | attributes for every term | {numref}`sugar-rewrites` |
| `exists-when` in a formula | core | when a term exists | {doc}`world-model` |
| a variable in a formula | core | a member, kept as `F.M` | {doc}`world-model` |

### Special forms and other expressions

The heads of this table that are written as {term}`words <word>`, from `.` to `type-of`, are
{term}`keywords <keyword>` ({numref}`keywords`).

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a literal | core | a number, string, TeX string, {term}`interpolated string`, bool, `none` or list literal | {doc}`lexical`, {doc}`types` |
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
| `free` | core | see "Variables and constraints". In an expression it is a compile error | {doc}`reaction` |
| `(F A…)` for a declared function `F` | core | a call | {doc}`evaluation` |
| `(L A…)` for a local function value `L` | core | a call of a function held by a parameter or a `let` name | {doc}`evaluation` |

### Library functions

These heads name functions of the library. Each call is a core call ({numref}`library-form`).

| Heads | What they are |
|---|---|
| `+`, `-`, `*`, `/`, `^`, `mod`, `=`, `!=`, `<`, `<=`, `>`, `>=` | the operators |
| `not`, `abs`, `or?`, `none?`, `some?`, `somes` | logic, absolute value and `none` |
| `sqrt`, `sign`, `floor`, `ceil`, `exp` | numbers |
| `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, `sind`, `cosd`, `tand`, `secd`, `cscd`, `cotd`, `asin`, `acos`, `atan`, `acot`, `asec`, `acsc`, `asind`, `acosd`, `atand`, `acotd`, `asecd`, `acscd`, `rad`, `turn`, `deg`, `to-rad`, `to-turn` | angles |
| `polar`, `to-polar`, `dist` | points |
| `rotate`, `translate`, `scale`, `transform` | transforms |
| `mix`, `lighten`, `darken`, `light-dark` | colors |
| `round`, `log`, `min`, `max`, `lerp`, `range` | with a varying number or type of arguments |
| `gap`, `num` | the third argument of `range` |
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | random values and seeds: {term}`primitives <primitive>`, which a source names only through the file rand of the standard library ({numref}`primitive-form`) |
| `steps` | an ease: `(steps N (at P))` gives the ease of N equal jumps, each at the fraction P of its interval, so jump k comes at (k − 1 + P)/N. P is from 0 to 1 and known when compiling, and is 1 when `(at …)` is left out. So `(steps 1 (at P))` is 0 before P and 1 from P on |
| `seed` | the last argument of a random function, `(seed S)` |
| `map`, `where`, `sort`, `reverse`, `reduce`, `sum`, `count`, `any`, `all` | collections |
| `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right` | points on a shape's box |
| `pi`, `tau`, `euler` | constants |
| the files `colors`, `ease`, `fonts`, `marks`, `math`, `rand`, `types` | the standard library, written in mtp, and the file `rand` names the primitives ({ref}`stdlib-rand`) |

A call of `steps` gives an ease, which is a function, so `steps` is a library function and not a
keyword. By {numref}`declaration-names`, a declaration or a binding named `steps` takes the place
of the library function from that declaration or binding on.

:::{admonition} Code differs
:class: note
The compiler has `(step N)`, whose jumps come at the start of each interval, and `(step-ease P)`,
with one jump at P, in place of `steps` (compiler.py:3092-3107, web/src/transitions.ts:22). It reads
them only as the whole value of an `ease`, and not as calls. So after `(real step 3)`,
`(ease (step 2))` still compiles as the ease of two jumps, and `(step 2)` in any other place is the
error "unknown function". Beads mtp-ydd4.7.40 and mtp-6a4r make the compiler follow the rule.
:::

### Transitions and animations

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `move` | core | `(move TARGET ITEM…)`: a transition written in place | {doc}`time` |
| `from`, `to`, `duration`, `path` | core | the parts of a transition | {doc}`time` |
| `ease` | core | a function from 0 to 1, such as the value of `(steps N)` | {doc}`time` |
| `like` in a transition or a move | syntactic sugar | | {numref}`sugar-rewrites` |
| `animation` written inline | core | `(animation ITEM…)`, or `(animation N)` naming one, also as a step | {doc}`time`, {numref}`animation-step` |
| an animation's body of several items | syntactic sugar | one `in-order` | {numref}`sugar-rewrites` |
| `defaults` in an animation, `at-once` or `in-order` | core | a duration and an ease for the moves inside | {doc}`time` |
| `loop` | core | `(loop)` or `(loop N)` | {doc}`time` |
| `at-once`, `in-order` | core | items together, or one after another | {doc}`time` |
| `foreach` in an animation's body | core | puts its moves where it is written | {doc}`time`, {doc}`binding-time` |
| the name of an animation or a transition in a body | core | plays what it names | {doc}`time` |
| `wait` | syntactic sugar | | {numref}`sugar-rewrites` |
| `jump` | syntactic sugar | `(jump V X)`: a move of no duration | {numref}`sugar-rewrites` |
| a use of a choreo | core | the choreo's moves, with the values of its arguments, as one step | {doc}`time`, {numref}`animation-step` |

### Components and their items

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `canvas`, `readout`, `display` | core | the views | {doc}`page-interface`, {doc}`lifecycle` |
| `slider`, `button`, `play`, `stepper`, `toggle` | core | the controls | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove` | core | listeners on a shape or a term, or for `on-pointermove`, on its canvas | {doc}`reaction`, {doc}`concurrency` |
| `on-show`, `on-hide` | core | listeners that play while a canvas starts or stops drawing a shape | {doc}`reaction`, {doc}`lifecycle` |
| `on-view`, `on-ready`, `on-live`, `on-quiet` | core | listeners on their own view | {doc}`lifecycle` |
| `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom` on a canvas | core | the view box and how the {term}`reader` may move it | {doc}`page-interface` |
| `toggle-duration`, `toggle-ease` | core | how a canvas fades its items in and out | {doc}`time`, {doc}`page-interface` |
| a name, a list literal or an expression in a canvas | core | what the canvas draws | {doc}`page-interface` |
| `font` on a readout | core | the readout's font | {doc}`page-interface` |
| `kind` on a display | core | `'block'` or `'inline'` | {doc}`page-interface` |
| `move`, `animation` or a use of a choreo on a control or a listener | core | what the writer plays: one move, a collection of moves, or the moves of a choreo. A writer has at most one of them | {doc}`reaction`, {doc}`time` |
| the move of a slider | core | a `move` or the name of a transition, its first item | {doc}`page-interface`, {doc}`reaction` |
| the target of `toggle`, `on-pointermove` | core | a name | {doc}`reaction` |
| the target of `on-drag` written as a move | core | `(move TARGET (to X))` | {doc}`reaction`, {numref}`drag-group-translate` |
| the target of `on-drag` written as a name | syntactic sugar | the move of the shape's position | {numref}`sugar-rewrites` |
| `label` | core | a control's label | {doc}`page-interface`, {doc}`accessibility` |
| `tex` in a label | core | a label given as LaTeX | {doc}`page-interface` |
| `stops` on a slider | core | the number of positions of its knob. A slider whose target is an `int` and that gives no `stops` stops at each whole number from its `from` to its `to`, and both of these are then known when compiling, or the source is a {term}`compile error` | {doc}`page-interface` |
| `buttons`, `rest`, `labels` on a play | core | its bars, its rest between steps, its step names | {doc}`page-interface`, {doc}`time` |
| `selected` on a button | core | whether it is the current choice | {doc}`page-interface`, {doc}`accessibility` |
| `active` | core | whether the writer acts | {doc}`reaction` |
| `priority` | core | the writer's priority | {doc}`concurrency` |
| `stop-propagation` | core | whether an event goes up the scene tree | {doc}`reaction` |
| `in` | core | the views that a control belongs to | {doc}`page-interface`, {doc}`lifecycle` |
| a condition | core | a bool form that limits what a writer writes | {doc}`reaction` |
| `doc` on a component | core | its docstring | {doc}`compiled-format` |

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
| `formula` | one string, plain or TeX, known when compiling, then terms, `exists-when` and variables ({numref}`formula-terms`) | yes |
| `namespace` | variables, namespaces, palettes | yes |
| `palette` | items `(member color)` | yes |
| `interface` | items `(T attribute constraint…)` | yes |
| `type`, a variable `(T name …)` | {term}`constraints <constraint>`, such as `(>= 0)` | yes |
| `animation`, `choreo`, `at-once`, `in-order` | steps: `move`, `jump`, `wait`, `at-once`, `in-order`, `(animation …)`, the name of an animation or a transition, a use of a choreo | yes |
| `defaults` | items `(attribute value)`, and in an animation, `(duration …)` and `(ease …)` | yes |
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
| `step` | in an animation's body | use `(labels …)` and `(in-order …)` |
| `autoplay` | on a control | use a canvas's `(on-ready …)` |
| `exclusive` | on a writer | use `(priority n)` |
| `when` | on a control or a listener | use `(active bool)` |
| `value` | on a toggle | give the bool its start where it is declared |
| `buttons` | on a stepper | a stepper stops after each step |
| `dash-offset` | as an item | write `(dash [4 2] 1)` |
| `move` | in a canvas | a canvas takes no move |
| `term` | at the top level | a term is given inside its formula |

(core-summary)=
## Summary

| Head | Kind | Rewrite or defining page |
|---|---|---|
| `H@X`, `#'…'`, `[…][X]` | syntactic sugar, made by the parser | {numref}`shorthand-forms` |
| `(H_ …)` | syntactic sugar, made by the parser | {numref}`unnamed-head` |
| `N.A`, `N[X]` | syntactic sugar | {numref}`sugar-rewrites` |
| `when`, `cond`, `and`, `or` | syntactic sugar | {numref}`sugar-rewrites` |
| `(maybe T)`, `colormap` as a type, a name declared by `type` | syntactic sugar | {numref}`sugar-rewrites` |
| `(range X)`, a random function with no `(seed …)`, `roll-dice` with no argument | syntactic sugar | {numref}`sugar-rewrites` |
| `import`, `type`, `palette` | syntactic sugar | {numref}`sugar-rewrites` |
| `like` | syntactic sugar, or core with a `(name …)` | {numref}`sugar-rewrites`, {numref}`names-from-values` |
| `pointer-events` on a container | syntactic sugar | {numref}`sugar-rewrites` |
| `defaults` on a group, a row or a column, and in a formula | syntactic sugar | {numref}`sugar-rewrites` |
| `dash` with one argument, `pos` | syntactic sugar | {numref}`sugar-rewrites` |
| `foreach` with a list of names | syntactic sugar | {numref}`sugar-rewrites` |
| a name as the target of `on-drag` | syntactic sugar | {numref}`sugar-rewrites` |
| `wait`, `jump`, an animation's body of several items | syntactic sugar | {numref}`sugar-rewrites` |
| `interface`, `namespace` | core | {doc}`types`, {doc}`world-model` |
| `colormap` | core | {doc}`evaluation` |
| `scene`, `background`, `transform` in the scene | core | {doc}`world-model` |
| `formula`, `term` and the attributes of a term | core | {doc}`world-model` |
| `motif`, a motif instance, `self`, `defaults` on an instance | core | {doc}`world-model`, {doc}`scope` |
| `variant`, a variant instance | core | {doc}`types`, {doc}`world-model` |
| `func`, `func[T]`, `fn`, calls | core | {doc}`types`, {doc}`evaluation` |
| `transition`, `move` and their parts | core | {doc}`time` |
| `choreo` and its uses | core | {doc}`time`, {numref}`prove-bodies-once` |
| `primitive` | core | {numref}`primitive-form` |
| `animation`, `at-once`, `in-order`, `loop`, `defaults` in an animation | core | {doc}`time`, {numref}`animation-step` |
| `foreach` | core | {numref}`foreach-count`, {numref}`foreach-bounded-length`, {doc}`binding-time` |
| `let` | core | {doc}`scope`, {doc}`binding-time` |
| `(T N …)`, a variable, `font` and its parts | core | {doc}`world-model`, {doc}`reaction` |
| `free` | core | {doc}`reaction`, {doc}`binding-time` |
| the {term}`constraints <constraint>` `>=`, `>`, `<=`, `<`, `length`, `one-of`, `const`, `wrap` | core | {doc}`types` |
| the type notation of "Type notation", but `maybe`, `colormap` and the names declared by `type` | core | {doc}`types` |
| the twelve shapes | core | {doc}`world-model` |
| `row`, `column`, `gap`, `align` | core | {doc}`world-model` |
| the attribute arguments of the shapes, `dash` with two arguments, `clip`, `fixed-size` | core | {doc}`world-model` |
| `exists-when` | core | {doc}`world-model` |
| `.` | core | {numref}`dot-name-part` |
| `name` | core | {doc}`scope`, {numref}`names-from-values` |
| `if`, `as`, `type-of` | core | {doc}`evaluation`, {doc}`types` |
| `doc` | core | {doc}`compiled-format` |
| the views, the controls and their items | core | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| the fourteen listeners | core | {doc}`reaction`, {doc}`concurrency`, {doc}`lifecycle` |
| a move as the target of `on-drag` | core | {doc}`reaction`, {numref}`drag-group-translate` |
| a condition | core | {doc}`reaction` |
| the operators, `not`, `abs`, the `none` functions and the box points | library | {numref}`library-form` |
| the built-in functions and the collections, `map` over an int included, `steps` | library | {doc}`stdlib` |
| the primitives | library | {numref}`primitive-form` |
| the constants and the standard library files | library | {doc}`stdlib` |
