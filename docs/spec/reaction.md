# State and reaction

:::{note}
Not drafted yet. This page defines: the state of an open page, its starting state, and what one write does to it.
:::

## Dragging

The signature of `on-drag` ({ref}`signatures`):

```text
(on-drag SOURCE:shape|term MOVEMENT:instant
  (as:NAME none)
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 700)
  (doc:string '')
  ITEMS)
  ITEMS := (any EXPR:bool)
```

`SOURCE` is the shape or the term that the reader drags. `MOVEMENT` is the movement that the runtime
executes at each motion of the pointer. Its type is `instant`, the movements whose duration is 0
({numref}`interfaces`), so a move whose duration is not 0 is a compile error. The items of the body
are the guards of the listener ({numref}`writer-guards`).

```{rule} pointer-binding
A listener that the pointer triggers, `on-drag`, `on-pointermove`, `on-click`, `on-release`,
`on-dragstart`, `on-dragend`, `on-enter` or `on-leave`, may hold the optional clause `(as N)`, with `N` a
name. `N` is then a {term}`binding` in the listener's movement: the position of the pointer, a point,
in the frame of the collection that holds the shape or the term, when the movement starts. No
other expression reads the position of the pointer.
```

So `(on-drag p (as ptr) (move a (to ptr.x)))` writes the x of the pointer into `a` at each motion of
the pointer, and `(on-click board (as pointer) (move marker.pos (to pointer) (duration 0.3)))` moves a marker to
the point where the reader clicked.

:::{admonition} Code differs
:class: note
In the compiler, an `on-drag` holds exactly one move, written without a duration, and there is no
interface `instant`. Beads mtp-rk1i and mtp-idcs.
:::

## What a write does to a number

```{rule} writes-into-constraints
A write of a number into a {term}`container` brings it into the conditions of its declared type: below a `(>= c)` it becomes c, above a `(<= c)` it becomes c, it is brought into a modular
type by {numref}`modular-types`, and when it breaks a `(> c)` or a `(< c)` it is not written. A write of a value that is not among the values of a `(one-of …)` is not
written. A number written into an `int` is rounded as {numref}`rounding` states. A value that is
not written leaves the container as it was.
```

The {term}`number limit` applies to every write too ({numref}`number-limit`). So with
`(real p 0.5 (>= 0) (<= 1))`, a slider whose `to` is 1.4 stops `p` at exactly 1. Which values
a writer may write at all is defined in {numref}`written-values`.
