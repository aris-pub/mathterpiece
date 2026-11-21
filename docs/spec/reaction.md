# State and reaction

:::{note}
Not drafted yet. This page defines: the state of an open page, its starting state, and what one write does to it.
:::

## Dragging

The signature of `on-drag` ({ref}`signatures`):

```text
(on-drag SOURCE:shape|term MOVEMENT:movement&instant
  (at:NAME none)
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 700)
  (doc:string '')
  ITEMS)
  ITEMS := (any EXPR:bool)
```

`SOURCE` is the shape or the term that the reader drags, and `MOVEMENT` is what each motion of the
pointer plays: a movement that takes no time ({numref}`interfaces`), so a move with a duration is a
compile error. The body holds the listener's guards ({numref}`writer-guards`).

```{rule} pointer-binding
A listener that the pointer triggers, `on-drag`, `on-pointermove`, `on-click`, `on-release`,
`on-dragstart`, `on-dragend`, `on-enter` or `on-leave`, may hold the clause `(at N)`, with `N` a
name. `N` is then a {term}`binding` in the listener's movement: the position of the pointer, a point,
in the frame of the collection that holds the shape or the term, when the movement starts. No
other expression reads the position of the pointer.
```

So `(on-drag p (at q) (move a (to q.x)))` writes the x of the pointer into `a` at each motion of
the pointer, and `(on-click board (at q) (move marker.pos (to q) (duration 0.3)))` moves a marker to
the point where the reader clicked.

:::{admonition} Code differs
:class: note
An `on-drag` takes only one move, which gives no duration, and the compiler has no interface
`instant`. Beads mtp-rk1i and mtp-idcs.
:::
