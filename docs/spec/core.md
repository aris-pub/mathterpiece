(core)=
# Core and derived forms

In this part, every {term}`head` that the compiler accepts is sorted into three kinds:
{term}`core form`, {term}`sugar` and {term}`library`. Each sugar form is given as a
{term}`rewrite` into core forms. Each core form is given with the part of the spec where its
meaning is defined.

The inventory was built from `mathterpiece/compiler.py` and `mathterpiece/parse.py` as they are
on 2026-11-14, and then checked against `docs/reference.md` and `docs/syntax.md`. Citations of
the form `compiler.py:6471` name a file of `mathterpiece/` and a line in it. Where the code, the
documentation and the author's decisions disagree, or where the kind of a form is not clear, what
the code does is stated first, followed by an open question in a box. The author decides each
one.

(core-kinds)=
## Kinds of form

The {term}`head` of a form is its first item: `if` in `(if c a b)`, `circle` in
`(circle p (r 1))`. An item of a form is also called by its head, so `(r 1)` is an `r` item.

```{rule} kinds-of-form
Every head belongs to exactly one of three kinds: core, sugar or library.
```

```{rule} sugar-form
A form is sugar if and only if it can be rewritten into core forms without computing any value.
Looking up a name is not computing a value, since lexical scope is fixed by the text, so a
rewrite may resolve names.
```

```{rule} core-form
A form that is not sugar is core. The prover checks core forms, and the runtime runs them.
```

```{rule} library-form
The library is the built-in functions, which are implemented natively, and the files of the
standard library, which are written in mtp. A call of a library function is a call, which is a
core form. The library holds functions, constants and declarations, and no form of the
language.
```

```{rule} prover-sees-core
The {term}`prover` is given only core forms. Every sugar form is rewritten into core forms
before the prover runs.
```

```{rule} rewrite-keeps-names
A rewrite may move text or copy it. Each name in the moved or copied text refers to the
declaration that it referred to where it was written.
```

```{rule} rewrite-repeats
A rewrite may produce sugar forms. Those are rewritten in turn, until no sugar form is left.
```

```{rule} rewrite-conditions
Each rewrite below has conditions. A sugar form whose conditions do not hold is a compile error.
```

The prover is the part of the compiler that checks types, proves ranges and constraints, and
checks every invariant of the world model and its mathematics (mtp-08wd). The order of the
compiler's steps (parsing, rewriting, expanding what needs values known when compiling, proving,
folding and writing the .mtpc) belongs to {doc}`compiler-runtime`. The compiler of 2026-11-14
does not yet keep these steps apart: most rewrites below are made while the form is being
compiled, in the same functions that check it (mtp-08wd).

### How a rewrite is written

A rewrite is a pair of mtp fragments: the form as written, then the core forms that replace it.
In a fragment, a name in capitals stands for any text of the kind that the rule names: `X` for
an expression, `N` for a name, `ITEMS…` for any number of items. Everything else is written as
it is. After each rule, the line marked "Today" gives the place in `compiler.py` or `parse.py`
where the rewrite is made today, if it is made. These lines describe the code. They are not part
of the rule.

(core-rewrites)=
## Rewrite rules

### Rewrites of the lexical shorthands

These rewrites are made by the reader, `parse.py`, while it reads the source.

````{rule} rewrite-doc
```mtp
doc@'TEXT'
```
is rewritten to
```mtp
(doc 'TEXT')
```
````

Today: parse.py:222-231.

````{rule} rewrite-free
```mtp
free@X
```
is rewritten to
```mtp
(free@ X)
```
The long form cannot be written in a source, since `@` is not allowed in a name.
````

Today: parse.py:210-220. A name holding `@` is a parse error at parse.py:350.

````{rule} rewrite-name-string
```mtp
#'S'
#'S'.N
#'S'[X]
```
are rewritten to
```mtp
(name $'S')
(. (name $'S') N)
(. (name $'S') X)
```
Parts after the first are rewritten in the same way, from left to right. Condition: `S` holds at
least one `{…}`.
````

Today: parse.py:233-262.

````{rule} rewrite-list-part
```mtp
[ITEMS…][X]
```
is rewritten to
```mtp
(. [ITEMS…] X)
```
Further brackets are rewritten in the same way, from left to right.
````

Today: parse.py:285-297.

````{rule} rewrite-unnamed
```mtp
(H_ ITEMS…)
(H|none_ ITEMS…)
(F.H_ ITEMS…)
```
are rewritten to
```mtp
(H none ITEMS…)
(H|none none ITEMS…)
(F.H none ITEMS…)
```
Condition: the underscore ends the head.
````

Today: parse.py:91-103 and parse.py:279-280.

### Rewrites of names with parts

````{rule} rewrite-parts
```mtp
N.A
N[X]
```
are rewritten to
```mtp
(. N A)
(. N X)
```
A chain is rewritten from left to right: `p.pos.x` is `(. (. p pos) x)`, and `g[0].r` is
`(. (. g 0) r)`.
````

Today: neither file makes this rewrite (see Q-core-1).

:::{admonition} Open question Q-core-1
:class: warning
According to the decision of 2026-11-14, `parse.py` rewrites `p.r` to `(. p r)`. It does not.
parse.py:337-358 reads `p.r` as one name with the parts `p` and `r`, and parse.py:360-395 reads
`xs[i]` as a name whose second part is an expression. compiler.py:5953-5960 then reads such a
name part by part. `parse.py` writes a `(. …)` form only after a name string (parse.py:246-260)
and after a list in brackets (parse.py:287-292).

The two spellings also mean different things. In `(. X Y)` with a bare name `Y`, `Y` is an
attribute only when `X` has an attribute of that name, or when `Y` is neither declared nor local
and `X` is an object (compiler.py:6540-6549). Otherwise `Y` is a value, used as a position or a
key. In `X.y`, `y` is always an attribute. So `(let ((r 1)) (. xs r))` is item 1 of `xs`, while
`(let ((r 1)) xs.r)` is the error "a list[real] has no attribute 'r'". In syntax.md, section 7,
`p.r` is given as the same as `(. p r)`.

A writer's target goes the other way: compiler.py:1149-1159 turns `(. X Y)` and `(name s)` back
into a name with parts, and only a name is a target (compiler.py:3229).

Options: (a) `(. X Y)` is core, and `N.A` is rewritten to it as above, so that a local name `A`
changes what `N.A` means. (b) `(. X Y)` is core with two separate cases, one for an attribute
written as a name and one for a position or key given by an expression, and `N.A` is rewritten
to the first. (c) A name with parts is core, and `(. X Y)` is a second core form for parts of a
computed value.
:::

### Rewrites of expressions and types

````{rule} rewrite-when
```mtp
(when C X)
```
is rewritten to
```mtp
(if C X none)
```
Condition: the form has exactly two arguments.
````

Today: compiler.py:6471-6479.

````{rule} rewrite-maybe
```mtp
(maybe T)
```
in type notation is rewritten to
```mtp
T|none
```
````

Today: types.py:342-346.

````{rule} rewrite-colormap-type
The type name `colormap` is rewritten to `func[real color]`.
````

Today: types.py:373-375. The declaration `(colormap …)` is a different form (Q-core-11).

````{rule} rewrite-range
A call of the library function `range` with one argument
```mtp
(range X)
```
is rewritten to
```mtp
(range 0 X (gap 1))
```
Condition: `X` is not a `(gap …)` or `(num …)` item.
````

Today: compiler.py:2361-2365.

### Rewrites of declarations

Each `(like M)` below copies what the declaration of `M` was written with. `M` is a plain name,
declared before the form that holds the `(like …)`. When the declaration of `M` holds a
`(like …)` of its own, that one is rewritten first. A `(like …)` comes first among the items
that are not positional, and a form holds at most one.

````{rule} rewrite-like-shape
```mtp
(K N (like M) ARGS…)
```
where `M` was declared `(K M MARGS…)`, is rewritten to
```mtp
(K N ARGS… COPIED…)
```
`COPIED…` is each item of `MARGS…` whose attribute `ARGS…` does not give. `(pos P)` gives `x`
and `y`. When `MARGS…` gives `(pos P)` and `ARGS…` gives exactly one of `x` and `y`, `COPIED…`
holds the other one, `(x (. P 0))` or `(y (. P 1))`. A text's positional string is copied as an
item. Conditions: `K` is a shape head other than `group`, `row` and `column`, and `M` is a shape
of the same kind.
````

Today: compiler.py:5177-5186 and compiler.py:5239-5243, through `_fill_from` at
compiler.py:7129-7139.

````{rule} rewrite-like-instance
```mtp
(MOTIF N (like M) ARGS…)
```
where `M` is an instance of the same motif, is rewritten to the instance with every argument of
`M` that `ARGS…` does not give, as for a shape, and with the `(defaults …)` of `M` when the form
has no `(defaults …)` of its own.
````

Today: compiler.py:4696-4703 and compiler.py:4743-4749. The `(clip …)` and the
`(pointer-events …)` of `M` are not copied (Q-core-2).

````{rule} rewrite-like-variant
```mtp
(VARIANT N (like M) ARGS…)
```
where `M` is an instance of the same variant, is rewritten to the instance with every parameter
of `M` that `ARGS…` does not give, and every other item of `M` whose head `ARGS…` does not give.
````

Today: compiler.py:4584-4606.

````{rule} rewrite-like-font
```mtp
(font N (like M) PARTS…)
```
where `M` is a font declared before, is rewritten to the font with every part of `M`
(`family`, `style`, `weight`, `size`) that `PARTS…` does not give.
````

Today: compiler.py:4343-4367.

````{rule} rewrite-like-term
```mtp
(term T (like U) ITEMS…)
```
inside a formula, where the `(term U …)` form of the same formula comes before it, is rewritten
to
```mtp
(term T UITEMS… ITEMS…)
```
`UITEMS…` is each item of `U`'s form, after its own `(like …)` was rewritten, whose head
`ITEMS…` does not give.
````

Today: compiler.py:5029-5040.

````{rule} rewrite-like-transition
```mtp
(move TARGET (like T) ARGS…)
(transition N TARGET (like T) ARGS…)
```
where `T` names a transition declared at the top level, are rewritten to the same form with each
of the `from`, `to`, `duration`, `ease` and `path` items of `T` that `ARGS…` does not give.
````

Today: compiler.py:2867-2879. The compiler copies the compiled `duration`, `ease` and `path` of
`T`, and its `from` and `to` as written, each with the scope of `T`.

:::{admonition} Open question Q-core-2
:class: warning
In reference.md, "Copying a declaration", a motif instance copies "its arguments and its
`(defaults …)`". reference.md, "The scene and shapes", lists `(pointer-events bool)` as an
argument of every shape, groups included. The compiler keeps what an instance was written with at
compiler.py:4749, before its `(pointer-events …)` joins its defaults at compiler.py:4759-4762,
and it never keeps its `(clip …)`. So `(like M)` on an instance copies neither. On a shape,
`pointer-events` is an attribute and is copied. Should an instance's `(like …)` copy its
`pointer-events` and its `clip`?
:::

:::{admonition} Open question Q-core-3
:class: warning
`(like X)` compiles `X` as an expression (compiler.py:5329-5341), so `X` may be a name string,
`(like #'dot-{(- i 1)}')`, inside a `foreach`. The argument of a choreo use may be one too. The
string of `(name s)` must be computed (compiler.py:1161-1167), and inside a `foreach` it reads
the foreach's name, which has a value only once the copies are made. So a rewrite that resolves
such a name cannot run before the `foreach` is expanded, and expanding needs values
({numref}`sugar-form`). Options: (a) a sugar form whose name is a `(name …)` form is rewritten
after the expansion, in a second pass. (b) sugar may name only plain names, and `(like (name …))`
is a compile error. (c) `like` given a `(name …)` form is core.
:::

````{rule} rewrite-pointer-events
```mtp
(group N (pointer-events B) ITEMS…)
(MOTIF N (pointer-events B) ITEMS…)
```
are rewritten to the same container with `(pointer-events B)` moved into its `(defaults …)`, a
`(defaults …)` being added when it has none. The same holds for `row` and `column`. Condition:
its `(defaults …)` gives no `pointer-events`.
````

Today: compiler.py:5203-5208 and compiler.py:5247-5250 for a group, compiler.py:4716-4722 and
compiler.py:4759-4762 for an instance. Whether `(defaults …)` is itself sugar is Q-core-15.

````{rule} rewrite-dash
```mtp
(dash L)
```
is rewritten to
```mtp
(dash L 0)
```
````

Today: compiler.py:7376-7391. The offset is the attribute `dash-offset`, which is given only as
the second argument of `dash`. A `(dash-offset …)` item is a compile error.

````{rule} rewrite-foreach-names
```mtp
(foreach ((N1 S1) (N2 S2) MORE…) ITEMS…)
(foreach ((N S)) ITEMS…)
```
are rewritten to
```mtp
(foreach N1 S1 (foreach ((N2 S2) MORE…) ITEMS…))
(foreach N S ITEMS…)
```
Condition: the names are all different.
````

Today: compiler.py:855-900 makes the same copies, in the same order, without rewriting the text.
A check of two sources gave the same .mtpc.

### Rewrites of animations

````{rule} rewrite-wait
```mtp
(wait T)
(wait)
```
in an animation's body are rewritten to
```mtp
(move none (duration T))
(move none)
```
````

Today: compiler.py:3074-3087 compiles `(wait T)` straight to a wait step (Q-core-4).

:::{admonition} Open question Q-core-4
:class: warning
In reference.md, "Transitions and animations", `(wait 1)` is a shorter way to write
`(move none (duration 1))`, and the comment at compiler.py:3075 states the same. The compiler compiles
`(wait T)` to the step `("wait", T)`, with no transition object (compiler.py:3074-3087).
`(move none (duration T))` makes a transition object with no target, and its step is
`("wait", T, id)` (compiler.py:3198). Compiled to the .mtpc, a play of `(wait 1)` and a play of
`(move none (duration 1))` differ by that one transition object. For `a.steps`, the compiler later
makes a transition for each wait (compiler.py:4418-4458). Is the extra object a difference that
the spec allows between a sugar form and its rewrite, or should the two give the same .mtpc?
:::

````{rule} rewrite-roll-dice
```mtp
(roll-dice S)
```
in an animation's body is rewritten to
```mtp
(move S (to (next-seed S)) (duration 0))
```
`(roll-dice)` is `(roll-dice S)`, where `S` is the only seed that the file declares or imports.
Condition: `S` is a `rand-seed`.
````

Today: compiler.py:3070-3073 and compiler.py:3114-3136. A check of two sources gave the same
.mtpc. The compiler plays the move with no ease (compiler.py:3136), so a default ease around it
does not apply. Over a duration of 0, an ease changes nothing.

:::{admonition} Open question Q-core-5
:class: warning
`(roll-dice)`, and a random function written without `(seed …)`, follow the only seed that the
file declares or imports (compiler.py:2299-2314, compiler.py:3125-3126, reference.md, "Random
values and seeds"). The rewrites would be `(roll-dice)` to `(roll-dice S)`, and `(rand …)` to
`(rand … (seed S))`. Finding `S` is a search of every declaration for one whose type is
`rand-seed` (compiler.py:2294-2297), not a lookup of a written name. Is such a search a lookup of a
name in the sense of {numref}`sugar-form`? Options: (a) yes, and both forms are sugar. (b) no,
and the default seed is core, found by the prover.
:::

````{rule} rewrite-animation-item
In a control or a listener whose form has an `(animation …)` item, a single move, or a single use
of a choreo, written in its place
```mtp
(K ITEMS… (move TARGET ARGS…) MORE…)
(K ITEMS… (C ARGS…) MORE…)
```
is rewritten to
```mtp
(K ITEMS… (animation (move TARGET ARGS…)) MORE…)
(K ITEMS… (animation (C ARGS…)) MORE…)
```
Conditions: `K` is a control or a listener that has an animation (not a slider, an `on-drag` or
an `on-pointermove`), `C` names a choreo, and the form has at most one of an `(animation …)`, a
`(move …)` and a use. A `(wait …)`, a `(roll-dice …)`, an `(at-once …)` or an `(in-order …)`
written in the same place is a compile error.
````

Today: compiler.py:3745-3764.

````{rule} rewrite-choreo
Given the declaration
```mtp
(choreo C (P1 … Pn) BODY…)
```
a use
```mtp
(C A1 … Ak)
```
where k is at least the position of the last parameter with no default, is rewritten to the animation
`(animation BODY…)` with each `Pi` replaced by `Ai`, and each `Pi` for i above k by its default.
A use written as an item of an animation's body is rewritten to the step that this animation's
body makes (Q-core-6). Once every use is rewritten, the declaration is removed. Conditions: a
choreo uses only choreos declared before it, so none uses itself, and a use is written only where
an animation is.
````

Today: compiler.py:1669-1729 makes the rewrite on compiled values, not on text: each argument is
compiled, then the body is compiled with the parameters bound to the arguments' values.
compiler.py:1581-1624 checks the declaration.

:::{admonition} Open question Q-core-6
:class: warning
Three parts of a choreo use do not fit a rewrite of text.

1. A use in an animation's body is one step, the step that the choreo's whole body makes as an
   animation's body (compiler.py:1714-1729, through compiler.py:2984-2995). A body of one item
   makes that item, a body of several makes one `in-order`, and a body with `(loop …)` makes a
   loop step. No core form writes a loop step inside an animation's body, and an `(in-order X)` of
   one item is not the same as `X` (Q-core-22). So a choreo with a loop, used in an animation's
   body, has no rewrite into the forms that exist.
2. compiler.py:1702-1708 requires each argument to be known when compiling, or a name, or a
   function (reference.md: "An argument that needs the live model, such as `(* 2 k)`, is a
   compile error"). That check needs values. After a rewrite of text, `(* 2 k)` would stand in
   the body. In a `(duration …)` it would still be an error, but in a `(to …)` it would be
   allowed.
3. A choreo whose parameters all have defaults is compiled once with no use, so that errors in
   its body are reported (compiler.py:1619-1637). After the rewrite, no source text holds that use.

Options: for 1, a core form for an animation written as a step of another animation's body, or
a rule that a choreo used as a step has no loop. For 2, a binding-time rule on the rewritten body
({doc}`binding-time`), or no rule. For 3, the rewriter makes a use with every default, and the
prover checks it and drops it.
:::

### Rewrites of library calls

:::{admonition} Open question Q-core-7
:class: warning
In reference.md, "Collections", an int `n` in `(map n f)` "stands for `(range n)`". At
compiler.py:2661-2663, `(map n f)` and `(map xs f)` are told apart by the type of the first
argument. A type is known only to the prover, so this cannot be a rewrite made before the prover. It is part
of the typing rule of the library function `map`. Is that the intended reading? The same holds
for reference.md, "Special forms", where `(foreach i n …)` is given as
`(foreach i (range n) …)` (Q-core-27).
:::

(core-inventory)=
## Inventory of heads

Each table lists the heads of one context. The column "Defined in" gives the part where a core
form's meaning is defined, the rule for a sugar form, or {doc}`stdlib` for the library. An
open question about a candidate for sugar follows the table that lists it.

### Top-level declarations

compiler.py:1032-1075 dispatches the top-level forms, and compiler.py:828-853 expands each
`foreach`. A `let` at the top level is a compile error (compiler.py:949-954).

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `import` | core (Q-core-8) | `(import F)` or `(import F N…)`: the names of another file | {doc}`scope` |
| `type` | core (Q-core-9) | `(type N BASE C…)`: a named type | {doc}`types` |
| `interface` | core | `(interface N (T A C…)…)`: typed attributes that an object must have | {doc}`types` |
| `namespace` | core | `(namespace N MEMBER…)`: a mutable object that is not drawn | {doc}`world-model` |
| `palette` | core (Q-core-10) | `(palette N (M C)…)`: a namespace of colors | {doc}`world-model` |
| `colormap` | core (Q-core-11) | `(colormap N [C…] ITEM…)`: a function from a real to a color | {doc}`evaluation` |
| `scene` | core | `(scene N ITEM…)`: the one scene | {doc}`world-model` |
| `formula` | core | `(formula N ITEM…)`: typeset math with terms | {doc}`world-model` |
| `motif` | core | `(motif N PARAMS ITEM…)`: a template of shapes | {doc}`world-model` |
| `variant` | core (Q-core-12) | `(variant N PARAMS SHAPE)`: a new type of shape | {doc}`types` |
| `func`, `func[T]` | core | `(func N PARAMS BODY)`: a named function | {doc}`types`, {doc}`evaluation` |
| `transition` | core | `(transition N TARGET ITEM…)`: a named trajectory | {doc}`time` |
| `animation` | core | `(animation N ITEM…)`: a named animation | {doc}`time` |
| `choreo` | sugar | `(choreo N PARAMS ITEM…)`: a template of animations | {numref}`rewrite-choreo` |
| `foreach` | core | copies of its declarations, made when compiling | {doc}`binding-time` |
| `(T N …)` for a type `T` | core | a variable, among them `color` and `font` tokens and `rand-seed` seeds | {doc}`world-model`, {doc}`reaction` |
| components | core | views and controls (see "Components and their items") | {doc}`page-interface` |
| `doc` | core | a docstring, kept in the .mtpc | {doc}`compiled-format` |

:::{admonition} Open question Q-core-8
:class: warning
An import reads another file and makes its names known (compiler.py:745-826). The .mtpc holds no
import: what the source uses is written into it, each under its key, `house.ink` (reference.md,
"Imports"). An import could be read as a rewrite: put the declarations of `F.mtp` into the file,
each under the key `F.N`, and rename each use, as compiler.py:7280-7299 already renames `F.N` for
a file imported whole. That reads a file but computes no value. Options: (a) sugar, rewritten as
above. (b) core, defined in {doc}`scope`.
:::

:::{admonition} Open question Q-core-9
:class: warning
`(type N BASE C…)` names a refined type (compiler.py:1245-1256). Whether a value fits a type is
decided by base and constraints alone (types.py:160-228), so a named type behaves as the type
expression `(BASE C…)` wherever it is written. A rewrite would replace each use of `N` by
`(BASE C…)`. Three things still depend on the name: the .mtpc keeps the name in its table of types
(a check of `(type unit real (>= 0) (<= 1)) (unit k 0.5)` against `((real (>= 0) (<= 1)) k 0.5)`
gave a different .mtpc), the compiler finds seeds by the type name `rand-seed`
(compiler.py:7001-7003), and error messages name the type. Options: (a) sugar, with the name kept
for messages and the .mtpc only. (b) core.
:::

:::{admonition} Open question Q-core-10
:class: warning
compiler.py:1426-1455 rewrites `(palette N (M C)…)` to `(namespace N (color M C)…)` and then sets
the namespace's type to `palette`. A namespace of colors declared with `namespace` has the type
`namespace`: a check of the two gave a .mtpc that differs only in that type. The type `palette`
cannot be written in a type: `(func f ((palette q)) 1)` is the error "unknown type 'palette'"
(types.py:329-384), and neither can `namespace`. Options: (a) sugar into a core `namespace` form
that carries a mark for its type. (b) core, as today. (c) every namespace whose members are all
colors has the type `palette`, so that the type is decided by the prover and `palette` is sugar.
:::

:::{admonition} Open question Q-core-11
:class: warning
compiler.py:1731-1855 rewrites a colormap into a `func` of a real, whose body is built from
`let`, `cond`, `mix`, `min` and `max`. The rewrite computes values: each position must be known
when compiling (compiler.py:1768-1772), positions given as a start and an end are spread out by
arithmetic (compiler.py:1795-1796), and the steps of a discrete map are worked out
(compiler.py:1810-1813). It also checks that the positions do not decrease and that `wrap-at`
comes after the last. The function made is marked inline (compiler.py:1855), which a declared
`func` is not. A rewrite that computes nothing would write each position as an expression,
`(+ START (* (- END START) (/ K (- COUNT 1))))`, with `COUNT` the number of colors in the literal
list, and leave the checks to the prover. Options: (a) sugar, rewritten that way. (b) core.
:::

### Variables and constraints

A variable is `(T N VALUE? C…)` (compiler.py:1468-1558). Its head is a type.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `(T N VALUE C…)` | core | a variable of type `T`, free or bound | {doc}`world-model`, {doc}`reaction` |
| `list` with no item type | core | a list whose item type is the type of its value | {doc}`types` |
| `font` | core | `(font N PART…)`: a font token, given by its parts | {doc}`world-model` |
| `family`, `style`, `weight`, `size` | core | the parts of a font | {doc}`world-model` |
| `like` in a font | sugar | copies the parts of another font | {numref}`rewrite-like-font` |
| `free@` | core | a free value that starts at a computed value, only as a variable's value or an attribute's | {doc}`reaction`, {doc}`binding-time` |
| `>=`, `>`, `<=`, `<` with one number | core | a bound | {doc}`types` |
| `length` | core | the length of a list | {doc}`types` |
| `one-of` | core | the choices of a string | {doc}`types` |
| `const` | core | a value that no writer may write | {doc}`types` |
| `wrap` | core | an interval that a number wraps into | {doc}`types` |

### Type notation

compiler.py reads type notation through types.py:329-451.

| Notation | Kind | What it is | Defined in |
|---|---|---|---|
| `int`, `ratio`, `real`, `complex`, `bool`, `string`, `color`, `font`, `point`, `transform`, `transition`, `animation`, `none`, `scene` | core | the built-in types | {doc}`types` |
| `circle` and the other shape names | core | the shape types | {doc}`types` |
| `shape`, `positioned`, `sequence`, `sequence[T]` | core | the built-in interfaces | {doc}`types` |
| `list[T]` | core | lists | {doc}`types` |
| `func[P… R]` | core | function types | {doc}`types` |
| `T\|none` | core | a type that allows `none` | {doc}`types` |
| `(T C…)` | core | a refined type | {doc}`types` |
| `(maybe T)` | sugar | `T\|none` | {numref}`rewrite-maybe` |
| `colormap` | sugar | `func[real color]` | {numref}`rewrite-colormap-type` |
| a name declared by `type`, `interface`, `motif` or `variant` | core | that type | {doc}`types` |
| `rand-seed` | core | the type of seeds, an int of at least 0 | {doc}`types`, {doc}`evaluation` |

### The scene, shapes and containers

compiler.py:4864-4903 reads the items of the scene, and compiler.py:5109-5327 a shape.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `background` | core | the scene's background | {doc}`world-model` |
| `transform` in the scene | core | how the scene's coordinates are drawn | {doc}`world-model` |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text` | core | the shapes | {doc}`world-model` |
| `group` | core | a container | {doc}`world-model` |
| `row`, `column` | core (Q-core-13) | a group that places its members one after another | {doc}`world-model` |
| `(M N …)` for a motif `M` | core | an instance, an object of kind `instance` | {doc}`world-model` |
| `(V N …)` for a variant `V` | core (Q-core-12) | an instance of a variant | {doc}`world-model` |
| `(H\|none N …)` for a shape head `H` | core | a shape that may not exist | {doc}`world-model` |
| `exists-when` | core (Q-core-16) | `(exists-when N C)`: when a shape exists | {doc}`world-model` |
| `let` in a body | core (Q-core-17) | values worked out once, where the `let` is written | {doc}`binding-time` |
| `foreach` in a body | core | copies of declarations | {doc}`binding-time` |
| a variable in the scene | core | as at the top level | {doc}`world-model` |

### Arguments of shapes and containers

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `x`, `y`, `translate`, `transform`, `fill`, `stroke`, `stroke-width`, `opacity`, `fill-opacity`, `stroke-opacity`, `line-cap`, `line-join`, `drawn`, `pointer-events` on a shape, `r`, `width`, `height`, `rx`, `ry`, `from`, `to`, `a`, `b`, `c`, `points`, `controls`, `head-start`, `head-end`, `head-size`, `value`, `halign`, `valign`, `font` | core | an attribute of the shape, by the table at compiler.py:268-328 | {doc}`world-model` |
| `pos` | core (Q-core-14) | `x` and `y` given as one point | {doc}`world-model` |
| `dash` with two arguments | core | the dash lengths and `dash-offset` | {doc}`world-model` |
| `dash` with one argument | sugar | an offset of 0 | {numref}`rewrite-dash` |
| `like` | sugar | copies another shape's arguments | {numref}`rewrite-like-shape` |
| `defaults` | core (Q-core-15) | what a container gives its members | {doc}`world-model` |
| `clip` | core | a shape that the members are drawn inside | {doc}`world-model` |
| `fixed-size` | core | a group whose members are measured in screen pixels | {doc}`world-model` |
| `pointer-events` on a group or an instance | sugar | a default for the members | {numref}`rewrite-pointer-events` |
| `gap`, `align` | core | the spacing and alignment of a row or a column | {doc}`world-model` |

:::{admonition} Open question Q-core-12
:class: warning
An instance of a variant is compiled as its base shape, with the variant's body items and the
instance's own items, the variant's parameters added as attributes, some attributes marked fixed,
and the variant's type in place of the base type (compiler.py:4566-4636). A rewrite of
`(V N ARGS…)` to `(BASE N BODYITEMS… ARGS…)` would lose three things: the parameters as
attributes (a parameter `p` of `n` is read as `n.p`), the fixed marks (no writer may write a fixed attribute), and the type
`V`, a subtype of the base, which parameters and variables may be declared with. Options: (a)
core. (b) sugar into a core shape form that may carry extra attributes, fixed marks and a type.
:::

:::{admonition} Open question Q-core-13
:class: warning
A row or a column is a group with a layout (compiler.py:5401-5408): the runtime moves each member
so that its box starts a gap after the box of the member before. A rewrite into a plain group
would give each member a translate built from the box points of the members before it, `(right
…)` and `(left …)`, which are library functions. But a member's box depends on its own
translate, so its translate would read the member itself, unless each member is put inside a
group of its own. A member that does not exist is given no space, so each translate would also test
whether the members before it exist. Options: (a) core, as today. (b) sugar, rewritten into
nested groups as above.
:::

:::{admonition} Open question Q-core-14
:class: warning
`(pos P)` on a shape compiles `P` once and splits it into `x` and `y` (compiler.py:5594-5611).
A rewrite to `(x (. P 0)) (y (. P 1))` copies `P`, which changes two things. A random call in `P`
is a place of its own each time it is written (compiler.py:2255), so `x` and `y` would be drawn
from two places. And a check of `(pos [a 2])` against `(x (. [a 2] 0)) (y (. [a 2] 1))` gave
different .mtpc files: in the first, `y` is free, so a writer may write it, and in the second it
is `const`, since `(. [a 2] 1)` is not a literal (compiler.py:5656-5657). `(pos free@P)` would
need its own rewrite too. Options: (a) core, as today. (b) sugar, with those differences.
:::

:::{admonition} Open question Q-core-15
:class: warning
`(defaults (A V)…)` on a group or an instance gives its members each attribute that they do not
give themselves, at any depth, the nearest container winning (compiler.py:5543-5576,
compiler.py:5251-5276, compiler.py:4723-4762). A rewrite would copy each `(A V)` into each member
that has the attribute and does not give it. It would skip a text for what only a stroke uses,
give heads only to the shapes with ends and a text's settings only to texts, give `fixed-size`
only to member groups and no further, and for an instance member, add `(A V)` to the instance's
own `(defaults …)`, since a motif's body is expanded for each instance later. A check of one group
and its rewrite gave the same .mtpc. One thing differs. A default is compiled in the container's
scope, where a read of the container is an error (compiler.py:394-397, compiler.py:6329), while a
member that reads its container whole has the container compiled twice (compiler.py:1205-1243),
so `(dial d (defaults (stroke d.tint)))`, an error today, would become a member reading `d`.
Options: (a) sugar, rewritten as above. (b) core, as today.
:::

:::{admonition} Open question Q-core-16
:class: warning
`(exists-when N C)` sets the `exists` attribute of the shape `N`, declared before it as
`T|none` (compiler.py:5506-5541). A rewrite would move `C` into the declaration of `N` as an
argument, but `exists-when` comes after the shape and may read what is declared between the two,
and a name is visible only after its declaration. No `(exists …)` argument exists in the source
either. In a formula, `(exists-when T C)` sets a term's `exists` (compiler.py:5058-5066). Options:
(a) core, as today. (b) sugar into a core `(exists C)` argument, with a rule under which it may
read what is declared after the shape.
:::

:::{admonition} Open question Q-core-17
:class: warning
A `let` in a scene, group, `foreach` or motif body works out each value once, where it is
written (compiler.py:947-983). A value known only while drawing becomes a variable object of its
own (compiler.py:969-983). A rewrite that put the value in place of each use of the name would
compute it once for each use, and each random call in it would be a place of its own. A rewrite
into a variable declaration needs the value's type, which is found only by the prover. The `let` of an
expression (compiler.py:6663-6698) also shares one computation among its uses. Both look core.
Is that the intended reading?
:::

### Motifs and variants

compiler.py:1560-1579 reads a motif, compiler.py:4674-4820 an instance, compiler.py:4516-4549 a
variant and compiler.py:4566-4636 an instance of one.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a parameter `(T N DEFAULT?)` | core | a parameter of a motif, variant, function or choreo | {doc}`types` |
| a shape, a bound variable, `foreach`, `let` or `exists-when` in a motif's body | core | the members and values of each instance | {doc}`world-model` |
| `self` | core | the instance being built, inside a motif's body | {doc}`scope` |
| a parameter given to an instance, `(P X)` | core | the parameter's value | {doc}`world-model` |
| `x`, `y`, `pos`, `translate`, `transform` on an instance | core | the instance's frame | {doc}`world-model` |
| `clip`, `defaults` on an instance | as on a group | | |
| `pointer-events` on an instance | sugar | | {numref}`rewrite-pointer-events` |
| `like` on an instance | sugar | | {numref}`rewrite-like-instance` |
| `like` on a variant instance | sugar | | {numref}`rewrite-like-variant` |

A motif instance is core: it is an object of kind `instance` in the .mtpc. Making the members of
each instance from the motif's body needs values known when compiling (the parameters' values),
so it is an expansion, as a `foreach` is, and not a rewrite (mtp-08wd). A motif is also compiled
once with no instance, so that errors in its body are reported (compiler.py:4495-4514). That is a check,
not a form. Within the motif machinery, the rewrites are `(like …)` and `(pointer-events …)` on
an instance. Whether an instance's `(defaults …)` is a rewrite is Q-core-15.

### Namespaces, palettes and interfaces

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a variable in a namespace | core | a member, kept as `N.M` | {doc}`world-model` |
| `namespace`, `palette` in a namespace | core | a namespace inside a namespace | {doc}`world-model` |
| `(M C)` in a palette | core (Q-core-10) | a color member | {doc}`world-model` |
| `(T A C…)` in an interface | core | an attribute that an object must have | {doc}`types` |

### Formulas and terms

compiler.py:4905-4969 reads a formula.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a TeX string | core | the formula's LaTeX, which marks its terms | {doc}`world-model` |
| `term` | core | `(term T ITEM…)`: a term's attributes | {doc}`world-model` |
| `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding`, `tex` in a term | core | a term's attributes | {doc}`world-model` |
| `like` in a term | sugar | copies another term's form | {numref}`rewrite-like-term` |
| `defaults` in a formula | core (Q-core-18) | attributes for every term | {doc}`world-model` |
| `exists-when` in a formula | core (Q-core-16) | when a term exists | {doc}`world-model` |
| a variable in a formula | core | a member, kept as `F.M` | {doc}`world-model` |

:::{admonition} Open question Q-core-18
:class: warning
`(defaults (A V)…)` in a formula gives every term each attribute, each term its own copy, and a
term's own `(term …)` form wins (compiler.py:4985-5016). A rewrite would add `(A V)` to the
`(term T …)` form of each term `T` that does not give `A`, or add a form `(term T (A V)…)` where
there is none. The terms are read from the TeX literal (compiler.py:7339-7366), which is text and
not a computed value. Two things differ. The defaults are compiled before any of the formula's
variables (compiler.py:4939), while a term form may read the variables declared before it. And a
`(like U)` copies `U`'s form as written: it is not settled whether the copy would include the
moved defaults. Options: (a) sugar, rewritten as above. (b) core, as today.
:::

### Special forms and other expressions

compiler.py:6430-6578 reads a form in an expression. The special forms are the set at
compiler.py:122. No declared function may have the name of one (compiler.py:181-185).

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a literal | core | a number, string, TeX string, interpolated string, bool, `none` or list | {doc}`lexical`, {doc}`types` |
| a name | core | what the name refers to | {doc}`scope` |
| a name with parts, `N.A`, `N[X]` | sugar | | {numref}`rewrite-parts` |
| `.` | core (Q-core-1) | `(. X Y)`: an attribute, item or member of `X` | {doc}`world-model`, {doc}`types` |
| `name` | core | `(name S)`: the name whose text is `S`, known when compiling | {doc}`scope`, {doc}`binding-time` |
| `if` | core | `(if C A B)` | {doc}`evaluation` |
| `when` | sugar | `(when C X)` | {numref}`rewrite-when` |
| `cond`, `else` | core (Q-core-19) | `(cond (C V)… (else V))` | {doc}`evaluation` |
| `and`, `or` | core (Q-core-19) | left to right, stopping early | {doc}`evaluation` |
| `let` | core | `(let ((N V)…) BODY)` | {doc}`scope`, {doc}`evaluation` |
| `fn` | core | `(fn PARAMS BODY)`: a function written in place | {doc}`types`, {doc}`evaluation` |
| `as` | core | `(as T LITERAL)`: a literal given a type | {doc}`types` |
| `type-of` | core | `(type-of X)`: the type of `X`, as a string | {doc}`types` |
| `free@` | core | see "Variables and constraints". In an expression it is a compile error | {doc}`reaction` |
| `(F A…)` for a declared function `F` | core | a call | {doc}`evaluation` |
| `(L A…)` for a local function value `L` | core | a call of a function held by a parameter or a `let` name | {doc}`evaluation` |

:::{admonition} Open question Q-core-19
:class: warning
`cond` is compiled to nested `if`s (compiler.py:6608-6661):
`(cond (C1 V1) MORE… (else V))` is `(if C1 V1 (cond MORE… (else V)))`, and `(cond (else V))` is
`V`. A check of one `cond` and its nested `if`s gave the same .mtpc. One difference: with no type
expected from outside, a literal list among the values is given the type of the values that are not
literal lists, over all the clauses at once (compiler.py:6629-6641), while an `if` gives a literal
list in one branch the type of the other branch only (compiler.py:6494-6504).

`and` and `or` could be rewritten too: `(and A MORE…)` to `(if A (and MORE…) false)`, `(and A)`
to `A`, `(and)` to `true`, and `(or A MORE…)` to `(if A true (or MORE…))`, `(or A)` to `A`,
`(or)` to `false`. A check of `(and a b)` against `(if a b false)` gave .mtpc files that differ
only in the operation written, `and` or `if`. Options: (a) `cond`, `and` and `or` are sugar,
rewritten as above. (b) they stay core.
:::

### Library functions

These heads name functions of the library. Each call is a core call ({numref}`library-form`).
A declared function may have the name of a library function, and from its declaration on, a call
of that name is a call of the declared function (reference.md, "Functions").

| Heads | What they are | Where the compiler reads them |
|---|---|---|
| `+`, `-`, `*`, `/`, `^`, `mod`, `=`, `!=`, `<`, `<=`, `>`, `>=` | the operators | compiler.py:6441-6447 |
| `not`, `abs`, `or?`, `none?`, `some?`, `somes` | logic, absolute value and `none` | compiler.py:6532-6572 |
| `sqrt`, `sign`, `floor`, `ceil`, `exp` | numbers | builtins.py:180-188 |
| `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, `sind`, `cosd`, `tand`, `secd`, `cscd`, `cotd`, `asin`, `acos`, `atan`, `acot`, `asec`, `acsc`, `asind`, `acosd`, `atand`, `acotd`, `asecd`, `acscd`, `rad`, `turn`, `deg`, `to-rad`, `to-turn` | angles | builtins.py:189-227 |
| `polar`, `to-polar`, `dist` | points | builtins.py:228-232 |
| `rotate`, `translate`, `scale`, `transform` | transforms | builtins.py:233-234, compiler.py:2345-2355 |
| `mix`, `lighten`, `darken`, `light-dark` | colors | builtins.py:235-238 |
| `round`, `log`, `min`, `max`, `lerp`, `range` | with a varying number or type of arguments | compiler.py:2316-2444 |
| `gap`, `num` | the third argument of `range` | compiler.py:2357-2407 |
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | random values and seeds | compiler.py:2236-2314 |
| `seed` | the last argument of a random function, `(seed S)` | compiler.py:2245-2252 |
| `map`, `where`, `sort`, `reverse`, `reduce`, `sum`, `count`, `any`, `all` | collections | compiler.py:2652-2795 |
| `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right` | points on a shape's box | compiler.py:5420-5440 |
| `pi`, `π`, `tau`, `τ`, `euler`, `infty`, `∞` | constants | builtins.py:246-254 |
| the files `colors`, `ease`, `fonts`, `marks`, `math`, `rand`, `types` | the standard library, written in mtp | `mathterpiece/stdlib/` |

:::{admonition} Open question Q-core-20
:class: warning
In reference.md, "Functions", a function may have the name of a built-in function, "such as
`sind` or `map`", and not the name of a special form, a type or a constant. The operators are not
mentioned. compiler.py:6430-6440 calls a declared function in place of any head that is not a
special form, and the operators are not among the names refused (compiler.py:181-185). So
`(func + ((real a) (real b)) 7)` compiles, and after it `(+ 1 2)` is 7. The same holds for `not`,
`abs`, `or?`, `none?`, `some?`, `somes` and the eight box points, which compiler.py reads itself
and builtins.py does not list. If the operators are library, as this part lists them, replacing
them is allowed. Is that intended?
:::

### Transitions and animations

compiler.py:2835-2897 reads a transition, compiler.py:2970-3104 an animation and its body.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `move` | core | `(move TARGET ITEM…)`: a transition written in place | {doc}`time` |
| `from`, `to`, `duration`, `path` | core | the parts of a transition | {doc}`time` |
| `ease` | core | a function from 0 to 1, or one of the two forms below | {doc}`time` |
| `step` as an ease | core | `(step N)`: N equal jumps | {doc}`time` |
| `step-ease` | core | `(step-ease P)`: 0 before P and 1 from P on | {doc}`time` |
| `like` in a transition or a move | sugar | | {numref}`rewrite-like-transition` |
| `animation` written inline | core | `(animation ITEM…)`, or `(animation N)` naming one | {doc}`time` |
| `defaults` in an animation, `at-once` or `in-order` | core (Q-core-21) | a duration and an ease for the moves inside | {doc}`time` |
| `loop` | core | `(loop)` or `(loop N)` | {doc}`time` |
| `at-once`, `in-order` | core | items together, or one after another | {doc}`time` |
| `foreach` in an animation's body | core | puts its moves where it is written | {doc}`time`, {doc}`binding-time` |
| the name of an animation or a transition in a body | core | plays what it names | {doc}`time` |
| `wait` | sugar | | {numref}`rewrite-wait` |
| `roll-dice` | sugar | | {numref}`rewrite-roll-dice` |
| a use of a choreo | sugar | | {numref}`rewrite-choreo` |

:::{admonition} Open question Q-core-21
:class: warning
`(defaults (duration D) (ease E))` in an animation, `at-once` or `in-order` gives each move inside
that has no duration or ease of its own the nearest default (compiler.py:3018-3033,
compiler.py:3184-3227). A rewrite would add `(duration D)` and `(ease E)` to each such move and
each `(wait)`. Three things differ. A check of
`(animation (defaults (duration 2)) (move k (to 1)) …)` against the same moves with
`(duration 2)` written in gave different .mtpc files: today the default is put on the step only,
and the move's transition object has no duration, which `a.steps[0].duration` reads. A default
also applies to the name of a transition in the body, and to the moves of a choreo used there,
and a name cannot be given a duration in text without `(move T (like N) (duration D))`, which
makes a new transition object. And a default ease does not apply to a move of a bool, a string or
a choice (compiler.py:3204-3226), so the rewrite of `(ease E)` needs the type of each target,
which is found only by the prover. Options: (a) the duration default is sugar and the ease
default core. (b) both core, as today.
:::

:::{admonition} Open question Q-core-22
:class: warning
An animation's body of two or more items is one `in-order` (compiler.py:6986-6988), so
`(animation A B MORE…)` is `(animation (in-order A B MORE…))`. A check of the two gave the same
.mtpc. A choreo's body is read the same way. An `(in-order X)` of one item stays an `in-order` of
one item (compiler.py:3088-3093), and as an animation's whole body it is one step, where `X`'s
own items would be several: a play of `(animation (in-order (in-order a b)))` has one step, and a
play of `(animation (in-order a b))` has two. Options: (a) a body of several items is sugar,
rewritten to one `in-order`, and an `in-order` of one item stays core. (b) an `in-order` or
`at-once` of one item is also rewritten to its item, which changes the steps of such a play.
:::

### Components and their items

compiler.py:3324-3411 reads a view, a control or a listener, and the `build_` functions at
compiler.py:3810-4329 read each kind.

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `canvas`, `readout`, `display` | core | the views | {doc}`page-interface`, {doc}`lifecycle` |
| `slider`, `button`, `play`, `stepper`, `toggle` | core | the controls | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove` | core | listeners on a shape or a term, or for `on-pointermove`, on its canvas | {doc}`reaction`, {doc}`concurrency` |
| `on-show`, `on-hide` | core | listeners that play while a canvas starts or stops drawing a shape | {doc}`reaction`, {doc}`lifecycle` |
| `on-view`, `on-ready`, `on-live`, `on-quiet` | core | listeners on their own view | {doc}`lifecycle` |
| `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom` on a canvas | core | the view box and how the reader may move it | {doc}`page-interface` |
| `toggle-duration`, `toggle-ease` | core | how a canvas fades its items in and out, kept as a `(move none …)` (compiler.py:4216-4223) | {doc}`time`, {doc}`page-interface` |
| a name, a list or an expression in a canvas | core | what the canvas draws | {doc}`page-interface` |
| `font` on a readout | core | the readout's font | {doc}`page-interface` |
| `kind` on a display | core | `'block'` or `'inline'` | {doc}`page-interface` |
| `animation` on a control or a listener | core | its animation | {doc}`reaction` |
| `move`, or a use of a choreo, in place of `animation` | sugar | | {numref}`rewrite-animation-item` |
| the move of a slider | core | a `move` or the name of a transition, its first item | {doc}`page-interface`, {doc}`reaction` |
| the target of `on-drag`, `toggle`, `on-pointermove` | core (Q-core-23) | a name, or for `on-drag` a `(move TARGET (to X))` | {doc}`reaction` |
| `label` | core | a control's label | {doc}`page-interface`, {doc}`accessibility` |
| `tex` in a label | core | a label given as LaTeX | {doc}`page-interface` |
| `step` on a slider | core | the number of positions of its knob | {doc}`page-interface` |
| `buttons`, `rest`, `labels` on a play | core | its bars, its rest between steps, its step names | {doc}`page-interface`, {doc}`time` |
| `selected` on a button | core | whether it is the current choice | {doc}`page-interface`, {doc}`accessibility` |
| `active` | core | whether the writer acts | {doc}`reaction` |
| `priority` | core | the writer's priority | {doc}`concurrency` |
| `stop-propagation` | core | whether an event goes up the scene tree | {doc}`reaction` |
| `in` | core | the views that a control belongs to | {doc}`page-interface`, {doc}`lifecycle` |
| a condition | core | a bool form that limits what a writer writes | {doc}`reaction` |
| `doc` on a component | core | its docstring | {doc}`compiled-format` |

:::{admonition} Open question Q-core-23
:class: warning
reference.md, "Dragging", has the sentence "`(on-drag p p.pos)` is short for
`(on-drag p (move p.pos (to pointer)))`, and `p.x` and `p.y` likewise." The compiler keeps the
two apart (compiler.py:3951-4022): only the second has a map. The runtime treats them differently
for a group (web/src/drag.ts:99-120). The bare target moves each member by the pointer's motion,
while the move writes the pointer's point to the group's `pos`, which puts every member at that
one point. For `p.x`, `(to pointer)` is a type error, since the target is a real and the pointer
a point, so "likewise" would need `(to pointer.x)`. Options: (a) the bare target is sugar, and
the rewrite is fixed so that it holds for groups. (b) the bare target is core, and the reference
is changed.
:::

### Heads that are compile errors with a message

These heads were once part of the language, or belong in another context. Each is a compile
error, with a message about what to write in its place. They are not forms of the language.

| Head | Where | The message, in short | Code |
|---|---|---|---|
| `step` | in an animation's body | use `(labels …)` and `(in-order …)` | compiler.py:3047-3052 |
| `autoplay` | on a control | use a canvas's `(on-ready …)` | compiler.py:3695-3701 |
| `exclusive` | on a writer | use `(priority n)` | compiler.py:3784-3786 |
| `when` | on a control or a listener | use `(active bool)` | compiler.py:3769-3772 |
| `value` | on a toggle | give the bool its start where it is declared | compiler.py:3926-3932 |
| `buttons` | on a stepper | a stepper stops after each step | compiler.py:3897-3902 |
| `dash-offset` | as an item | write `(dash [4 2] 1)` | compiler.py:7378-7382 |
| `term` | at the top level | a term is given inside its formula | compiler.py:1050-1051 |
| `let` | at the top level | write it in a scene, group, `foreach` or motif body | compiler.py:949-954 |

(core-docs-check)=
## Differences between the code and the documentation

The inventory above was checked against reference.md and syntax.md. Every head in the tables is
described in at least one of the two, except `exclusive` and `value` on a toggle, which appear
only in the code, as compile errors. `(maybe T)` is in syntax.md, section 10, and not in
reference.md. The differences below are questions for the author.

:::{admonition} Open question Q-core-24
:class: warning
In reference.md, "Transitions and animations", `(move target)` is "written only inside an
animation, a slider or a canvas". reference.md, "Components", has "A canvas takes no `move`",
and compiler.py:4240-4245 makes a move in a canvas a compile error. Which is right?
:::

:::{admonition} Open question Q-core-25
:class: warning
reference.md, "Writes and conditions", has the sentence "`(when bool)` is different: it decides
whether the writer is active". syntax.md, section 8, gives `(when on)` as an example of an optional argument.
compiler.py:3769-3772 makes a `when` item on a control or a listener a compile error, "(active
bool) says when it acts", and reference.md, "Components", lists `(active bool)`. Should the two
documents drop `(when bool)` on writers?
:::

:::{admonition} Open question Q-core-26
:class: warning
syntax.md, "Names", lists the reserved words and leaves out `doc`. compiler.py:99-102 reserves
`doc`, and in reference.md, "Docstrings", `doc` is a reserved word. Should syntax.md add
`doc`?
:::

:::{admonition} Open question Q-core-27
:class: warning
In reference.md, "Special forms", `(foreach i n …)` is given as `(foreach i (range n) …)`. They
differ for a count known only while drawing. With an upper bound, `(foreach i n …)` makes as many
copies as `n` can be at most (compiler.py:902-915), while `(range n)` then has no length known
when compiling, which is the error "the length of the list a foreach goes through must be known
when compiling" (compiler.py:930-934). Should the reference be changed, or should the two be made the
same?
:::

(core-summary)=
## Summary

| Head | Kind | Rewrite or defining part |
|---|---|---|
| `doc@'…'` | sugar | {numref}`rewrite-doc` |
| `free@X` | sugar | {numref}`rewrite-free` |
| `#'…'` | sugar | {numref}`rewrite-name-string` |
| `[…][X]` | sugar | {numref}`rewrite-list-part` |
| `(H_ …)` | sugar | {numref}`rewrite-unnamed` |
| `N.A`, `N[X]` | sugar | {numref}`rewrite-parts` |
| `when` | sugar | {numref}`rewrite-when` |
| `(maybe T)` | sugar | {numref}`rewrite-maybe` |
| `colormap` as a type | sugar | {numref}`rewrite-colormap-type` |
| `(range X)` | sugar | {numref}`rewrite-range` |
| `like` on a shape | sugar | {numref}`rewrite-like-shape` |
| `like` on an instance | sugar | {numref}`rewrite-like-instance` |
| `like` on a variant instance | sugar | {numref}`rewrite-like-variant` |
| `like` on a font | sugar | {numref}`rewrite-like-font` |
| `like` on a term | sugar | {numref}`rewrite-like-term` |
| `like` on a transition or a move | sugar | {numref}`rewrite-like-transition` |
| `pointer-events` on a container | sugar | {numref}`rewrite-pointer-events` |
| `dash` with one argument | sugar | {numref}`rewrite-dash` |
| `foreach` with a list of names | sugar | {numref}`rewrite-foreach-names` |
| `wait` | sugar | {numref}`rewrite-wait` |
| `roll-dice` | sugar | {numref}`rewrite-roll-dice` |
| `move` or a use in place of `animation` | sugar | {numref}`rewrite-animation-item` |
| `choreo` and its uses | sugar | {numref}`rewrite-choreo` |
| `import` | core (Q-core-8) | {doc}`scope` |
| `type` | core (Q-core-9) | {doc}`types` |
| `interface` | core | {doc}`types` |
| `namespace` | core | {doc}`world-model` |
| `palette` | core (Q-core-10) | {doc}`world-model` |
| `colormap` | core (Q-core-11) | {doc}`evaluation` |
| `scene`, `background`, `transform` in the scene | core | {doc}`world-model` |
| `formula`, `term` and the attributes of a term | core | {doc}`world-model` |
| `defaults` in a formula | core (Q-core-18) | {doc}`world-model` |
| `motif`, a motif instance, `self` | core | {doc}`world-model`, {doc}`scope` |
| `variant`, a variant instance | core (Q-core-12) | {doc}`types`, {doc}`world-model` |
| `func`, `func[T]`, `fn`, calls | core | {doc}`types`, {doc}`evaluation` |
| `transition`, `move` and their parts, `step`, `step-ease` | core | {doc}`time` |
| `animation`, `at-once`, `in-order`, `loop` | core (Q-core-22) | {doc}`time` |
| `defaults` in an animation | core (Q-core-21) | {doc}`time` |
| `foreach` | core | {doc}`binding-time` |
| `let` | core (Q-core-17) | {doc}`scope`, {doc}`binding-time` |
| `(T N …)`, a variable, `font` and its parts | core | {doc}`world-model`, {doc}`reaction` |
| `free@` | core | {doc}`reaction`, {doc}`binding-time` |
| the constraints `>=`, `>`, `<=`, `<`, `length`, `one-of`, `const`, `wrap` | core | {doc}`types` |
| the type notation of "Type notation", but `maybe` and `colormap` | core | {doc}`types` |
| the twelve shapes | core | {doc}`world-model` |
| `row`, `column`, `gap`, `align` | core (Q-core-13) | {doc}`world-model` |
| the attribute arguments of the shapes | core | {doc}`world-model` |
| `pos` | core (Q-core-14) | {doc}`world-model` |
| `dash` with two arguments | core | {doc}`world-model` |
| `defaults` on a container | core (Q-core-15) | {doc}`world-model` |
| `clip`, `fixed-size` | core | {doc}`world-model` |
| `exists-when` | core (Q-core-16) | {doc}`world-model` |
| `.` | core (Q-core-1) | {doc}`world-model`, {doc}`types` |
| `name` | core | {doc}`scope`, {doc}`binding-time` |
| `if` | core | {doc}`evaluation` |
| `cond`, `else`, `and`, `or` | core (Q-core-19) | {doc}`evaluation` |
| `as`, `type-of` | core | {doc}`types` |
| `doc` | core | {doc}`compiled-format` |
| the views `canvas`, `readout`, `display` and their items | core | {doc}`page-interface`, {doc}`lifecycle` |
| the controls `slider`, `button`, `play`, `stepper`, `toggle` and their items | core | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| the fourteen listeners | core | {doc}`reaction`, {doc}`concurrency`, {doc}`lifecycle` |
| the target of `on-drag` | core (Q-core-23) | {doc}`reaction` |
| a condition | core | {doc}`reaction` |
| the operators, `not`, `abs` and the `none` functions | library (Q-core-20) | {doc}`stdlib` |
| the built-in functions of builtins.py, the collections and the box points | library | {doc}`stdlib` |
| `(map N F)` with an int `N` | library (Q-core-7) | {doc}`stdlib` |
| a random function with no `(seed …)` | library (Q-core-5) | {doc}`stdlib` |
| the constants | library | {doc}`stdlib` |
| the standard library files | library | {doc}`stdlib` |

## Open questions in this part

- Q-core-1: `parse.py` does not rewrite `p.r`, and `p.r` and `(. p r)` mean different things.
- Q-core-2: an instance's `(like …)` copies neither its `pointer-events` nor its `clip`.
- Q-core-3: a sugar form that names a `(name …)` form needs the foreach's values.
- Q-core-4: `(wait T)` and `(move none (duration T))` give different .mtpc files.
- Q-core-5: whether finding the only seed is a lookup of a name.
- Q-core-6: a choreo use with a loop, the rule on its arguments, and its trial compile.
- Q-core-7: `(map n f)` with an int is told apart by a type.
- Q-core-8: whether `import` is sugar.
- Q-core-9: whether `type` is sugar.
- Q-core-10: the type `palette`.
- Q-core-11: `colormap` computes its positions.
- Q-core-12: whether a variant instance is sugar.
- Q-core-13: whether `row` and `column` are sugar.
- Q-core-14: whether `pos` is sugar.
- Q-core-15: whether a container's `defaults` is sugar.
- Q-core-16: whether `exists-when` is sugar.
- Q-core-17: `let` is core.
- Q-core-18: whether a formula's `defaults` is sugar.
- Q-core-19: whether `cond`, `and` and `or` are sugar.
- Q-core-20: a declared function may replace an operator.
- Q-core-21: whether an animation's `defaults` is sugar.
- Q-core-22: an animation's body of several items, and an `in-order` of one item.
- Q-core-23: `on-drag`'s bare target is not the same as its move.
- Q-core-24: the reference contradicts itself on a move in a canvas.
- Q-core-25: the documents still give `(when bool)` on writers.
- Q-core-26: syntax.md leaves `doc` out of the reserved words.
- Q-core-27: `(foreach i n …)` is not `(foreach i (range n) …)`.
