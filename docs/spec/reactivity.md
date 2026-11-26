# Reactivity

:::{note}
Not drafted yet. This page defines: the state of an open page, its starting state, and what one write does to it.
:::

## Dragging

The signature of `on-drag` ({ref}`signatures`):

```mtp-sig
(on-drag SOURCE:shape|term MOVEMENT:instant
  (as:NAME none)
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 700)
  (doc:string '')
  CONDITIONS:bool*)
```

`SOURCE` is the shape or the term that the reader drags. `MOVEMENT` is the movement that the runtime
executes at each motion of the pointer. Its type is `instant`, the movements whose duration is 0
({numref}`interfaces`), so a `(move …)` whose duration is not 0 is a compile error. `CONDITIONS`
are the guards of the listener ({numref}`writer-guards`).

This rule exists so that a listener can read where the pointer is, in the frame of the shape that it drags.

```{rule} pointer-binding
A listener that the pointer triggers (`on-drag`, `on-pointermove`, `on-click`, `on-release`,
`on-dragstart`, `on-dragend`, `on-enter`, `on-leave`) may hold `(as N)`. `N` is then a {term}`binding` in
its movement: the pointer's position, a point in the frame of the collection that holds the shape or
term, when the movement starts. No other expression reads the pointer's position.
```

So `(on-drag p (as ptr) (move a (to ptr.x)))` writes the x of the pointer to `a` at each motion of
the pointer, and `(on-click board (as pointer) (move marker.pos (to pointer) (duration 0.3)))` moves a marker to
the point where the reader clicked.

:::{admonition} Code differs
:class: note
In the compiler, an `on-drag` holds exactly one `(move …)`, written without a duration, and there is no
interface `instant`. Beads mtp-rk1i and mtp-idcs.
:::

## What a write does to a number

This rule exists so that a container always holds a value that meets the conditions of its type, whatever a writer writes.

```{rule} writes-to-conditions
A write of a number to a {term}`container` brings it into the conditions of its declared type: below a
`(>= c)` it becomes c, above a `(<= c)` it becomes c, into a modular type it wraps by
{numref}`modular-types`, and a number that breaks a `(> c)` or a `(< c)` is not written. A value outside a
`(one-of …)`, and a list whose length breaks a `(length n)`, are not written either. A number written
to an `int` is rounded by {numref}`rounding`. A value not written leaves the container as it was.
```

The {term}`number limit` applies to every write too ({numref}`number-limit`). So with
`(real p 0.5 (>= 0) (<= 1))`, a slider whose `to` is 1.4 stops `p` at exactly 1. Which values
a writer may write at all is defined in {numref}`written-values`.
