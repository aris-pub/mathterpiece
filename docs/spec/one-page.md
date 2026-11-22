# mtp in one page

This page lists the main terms of mtp, with their meanings, diagrams and one example. It holds no
rules: each word links to the page that defines it.

## What mtp is

mtp is a language for interactive mathematical illustrations. In a source, the illustrator declares shapes, formulas
and the variables that they depend on. A reader changes the variables with sliders, buttons,
drags and clicks, and everything that depends on them updates.

## People

| Person | What they do |
|---|---|
| {term}`illustrator` | writes a {term}`world model` as an `.mtp` source file |
| {term}`author` | writes a web page and places components of the world model in it |
| {term}`reader` | opens the page and acts on the components |

One person may be both the illustrator and the author.

## Programs and files

The {term}`compiler` turns an `.mtp` source into a `.mtpc` file, on the illustrator's machine. The
{term}`runtime`, `mathterpiece.js`, runs in the reader's browser. It reads the `.mtpc` and keeps
one {term}`live model` for it, and it draws the components that the author places in the page
({doc}`compiler-runtime`).

```{diagram} one-page-people-and-programs
:file: diagrams/people-and-programs.svg

The people, the files and the two programs ({numref}`people-and-programs`).
```

## An example

```{mtp-example}
; a point on a segment, and a slider and a drag that move it
(scene s
  (real a 1 (>= 0) (<= 4))
  (line track (from [0 0]) (to [4 0]) (stroke #'gray'))
  (circle p (pos [a 0]) (r 0.15) (fill #'crimson')))

(canvas v (x -0.5) (y -0.5) (width 5) (height 1) s
  (on-drag p (move a (to pointer.x))))
(slider push (move a (from 0) (to 4)) (label 'a'))
(readout r f'a = {a:.2f}')
```

:::{admonition} Code differs
:class: note
In the spec, the drag is written `(on-drag p (as ptr) (move a (to ptr.x)))`. The compiler does not have
`(as …)` yet. Bead mtp-t8in.
:::

- `a` is a free variable: it holds 1 when the page opens, and a writer may change it.
- The circle `p` is a shape. Its `pos` is bound to `[a 0]`, so the circle moves whenever `a`
  changes.
- The canvas `v` is a view: the runtime draws the scene `s` in it. The slider `push` is a control, and
  `on-drag` is a listener. Both write `a` with a movement, `(move a …)`.
- The readout `r` is a view: the runtime writes `a` in it as text.

## Expressions

A source is any number of forms. Before anything else, every piece of syntactic sugar is
rewritten into the form that it is sugar for, for example:

| Written | Means |
|---|---|
| `[0 1]` | `(point-of 0 1)` |
| `{0 1 2}` | `(list-of 0 1 2)` |
| `p.pos.x` | `(. (. p 'pos') 'x')` |
| `real\|none` | `(type-union real none)` |
| `list[int]` | `(type-apply list int)` |
| `r@1` | `(r 1)` |
| `@'dot-{k}'` | `(name f'dot-{k}')` |
| `#'red'` | `(color-of f'red')` |

After that, each expression is a {term}`literal`, a {term}`name` or a {term}`form`. A form is
written in parentheses, and its first item is its {term}`head`. Whether the form is a {term}`compound`, a declaration, a {term}`clause` or a {term}`special form`
depends on its head ({doc}`grammar`, {doc}`heads`).

```{diagram} one-page-kinds-of-expression
:file: diagrams/kinds-of-expression.svg
:max-width: 35rem

The five kinds of expression after syntactic sugar is rewritten ({numref}`kinds-of-expression`).
```

## Values, containers and types

A {term}`value` is a {term}`primitive` or an {term}`object`. A primitive, such as the number `3`, the string `'hi'`, the point `[0 1]` or
the list `{0 1 2}`, never changes and has no identity. An object, such as a circle, has an identity and
attributes.

A {term}`container` is a variable or an attribute, and holds one value. Each container is one of
these:

| Kind | Example | What it holds |
|---|---|---|
| free | `(real a 1)` | 1 when the page opens, until a writer writes a new value |
| bound | `(real b (* 2 a))` | the value of its expression at all times, so `b` updates when `a` changes |
| const | `(real c 3 (const))` | 3, always. A writer of `c` is a compile error |

A {term}`type` is a set of values, known when compiling, such as `real`, `(real (>= 0))`,
`circle` or `real|none` ({doc}`types`).

```{diagram} one-page-values-containers-types
:file: diagrams/values-containers-types.svg
:max-width: 44rem

Primitives, objects and containers ({numref}`values-containers-types`).
```

## Objects

| Object | What the runtime does with it |
|---|---|
| the scene and its shapes | draws them |
| formulas and their terms | typesets them |
| views: canvas, readout, display | lays them out on the page |
| controls: slider, button, play, stepper, toggle | starts their movements when the reader acts on them |
| listeners, such as `on-drag` and `on-click` | starts their movements when the reader acts on a shape or a term |
| movements: `move`, `score`, `(A …)` for an animation `A` | writes their targets over time |
| functions | calls them |
| records | holds their attributes |

A {term}`collection` holds other objects, its members: a group, a row or a column holds shapes,
and a score holds movements. A motif is a type of shape that the illustrator declares, and an
animation is a type of movement ({doc}`data-model`).
