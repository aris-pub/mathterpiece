# State and reaction

:::{note}
Not drafted yet. This page defines: the state of an open page, its starting state, and what one write does to it.
:::

## Dragging

The signature of `on-drag` ({ref}`signatures`):

```text
(on-drag SOURCE:shape|term MOVEMENT:movement&instant
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 700)
  (doc:string '')
  ITEMS)
  ITEMS := (any EXPR:bool)
```

`SOURCE` is the shape or the term that the listener hears, and `MOVEMENT` is what each motion of the
pointer plays: a movement that takes no time ({numref}`interfaces`), so a move with a duration is a
compile error. The body holds the listener's guards ({numref}`writer-guards`).

:::{admonition} Code differs
:class: note
An `on-drag` takes only one move, which gives no duration, and the compiler has no interface
`instant`. Beads mtp-rk1i and mtp-idcs.
:::
