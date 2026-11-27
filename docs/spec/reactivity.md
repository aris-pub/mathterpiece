# Reactivity

This page defines the {term}`listeners <listener>` that are triggered when the reader acts on a shape
or a term with the pointer, what limits the writes of every {term}`writer`, and what the runtime
computes again after a write. The listeners that are triggered when a view changes are defined in
{doc}`lifecycle`, the controls in {doc}`controls`, and what happens when two writers write to one
container in {doc}`concurrency`.

## The listeners on shapes and terms

This rule exists to fix the arguments of each listener on a shape or a term, so that the compiler can check every such listener in a source.

````{rule} listener-signatures
```mtp-sig
(on-drag SOURCE:shape|term MOVEMENT:instant
  (as:NAME none)
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 700)
  (doc:string '')
  CONDITIONS:bool*)
(on-pointermove SOURCE:shape? MOVEMENT:instant
  (as:NAME none) (active:bool true) (stop-propagation:bool false)
  (priority:(int (>= 1) (<= 1000)) 700)
  (doc:string '')
  CONDITIONS:bool*)
(on-click SOURCE:shape|term MOVEMENT:movement
  (as:NAME none) (active:bool true) (stop-propagation:bool false)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)
(on-release SOURCE:shape MOVEMENT:movement
  (as:NAME none) (active:bool true) (stop-propagation:bool false)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)
(on-dragstart SOURCE:shape MOVEMENT:movement
  (as:NAME none) (active:bool true) (stop-propagation:bool false)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)
(on-dragend SOURCE:shape MOVEMENT:movement
  (as:NAME none) (active:bool true) (stop-propagation:bool false)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)
(on-enter SOURCE:shape|term MOVEMENT:movement
  (as:NAME none) (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)
(on-leave SOURCE:shape|term MOVEMENT:movement
  (as:NAME none) (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)
```

`SOURCE` is the shape or the term on which the reader acts, and an `on-pointermove` without it is
triggered anywhere over the canvas whose body holds it. `MOVEMENT` is the movement that the runtime
executes each time that the listener is triggered. Its type is `instant` for `on-drag` and
`on-pointermove`, the movements whose duration is 0 ({numref}`interfaces`), so a `(move …)` whose
duration is not 0 is a compile error there. `CONDITIONS` are the guards of the listener
({numref}`writer-guards`).
````

This rule exists so that a listener can read where the pointer is, in the frame of the shape that it drags.

```{rule} pointer-binding
A listener that the pointer triggers (`on-drag`, `on-pointermove`, `on-click`, `on-release`,
`on-dragstart`, `on-dragend`, `on-enter`, `on-leave`) may hold `(as N)`. `N` is then a {term}`binding` in
its movement: the pointer's position, a point in the frame of the collection that holds the shape or
term, or in the frame of the scene for an `on-pointermove` without a source, when the movement
starts. No other expression reads the pointer's position.
```

So `(on-drag p (as ptr) (move a (to ptr.x)))` writes the x of the pointer to `a` at each motion of
the pointer, and `(on-click board (as pointer) (move marker.pos (to pointer) (duration 0.3)))` moves a marker to
the point where the reader clicked.

:::{admonition} Code differs
:class: note
- In the compiler, an `on-drag` holds exactly one `(move …)`, written without a duration, and there
  is no interface `instant`. Beads mtp-rk1i and mtp-idcs.
- The compiler takes the movement of a listener as `(animation …)`, a `(move …)` or a use of a
  choreo, anywhere among its arguments, and a listener with no movement compiles
  (`compiler.py:4006`, `animated`). An `on-pointermove` takes a target, not a movement. No listener
  takes `(as …)`: the move of an `on-drag` reads the name `pointer`, which is the position of the
  shape at the press plus the motion of the pointer since (`compiler.py:4276`, `drag.ts:140`).
  Bead mtp-ydd4.7.100.
:::

This rule exists so that each listener is triggered by the same action of the reader as the event of the DOM that has its name, as authors of web pages expect.

```{rule} listener-triggers
The runtime triggers each listener at the event in the table below, in the view whose body holds it
({numref}`listeners-in-views`). The events follow the pointer events of the DOM in their names, their
order, and the shape or the term on which they happen. The shape hit is the topmost shape under the
pointer that the view draws, and an event on a shape is also on each collection that holds it. A
release triggers the `on-release` listeners first, then the `on-dragend` listeners, then the
`on-click` listeners. One motion of the pointer triggers the `on-leave` listeners first, from the
innermost shape out, then the `on-enter` listeners, from the outermost shape in.

| Listener | The event that triggers it |
|---|---|
| `on-drag` | a press that drags its source ({numref}`dragged-shape`). Its movement is executed at each motion of the pointer from then until the release |
| `on-dragstart` | the first motion of the pointer after a press that drags its source, before the drag writes |
| `on-dragend` | the release that ends a drag of its source in which the pointer moved |
| `on-release` | a release of the pointer over its source |
| `on-click` | a release after a press, on the innermost shape or term that holds both the one pressed and the one released |
| `on-enter` | the pointer coming onto its source, or onto a shape that it holds, from off all of them |
| `on-leave` | the pointer going off its source and off every shape that it holds |
| `on-pointermove` | each motion of the pointer over its source, or anywhere over the canvas for one without a source |
```

This rule exists so that one press drags exactly one shape.

```{rule} dragged-shape
A press drags at most one shape: the first, from the shape hit up through the collections that hold
it, that is the source of an `on-drag` in the view whose `active` holds. Of several such `on-drag` on
one shape, the first written is triggered. A press that drags no shape triggers no `on-drag`,
`on-dragstart` or `on-dragend`.
```

This rule exists so that an event on a shape reaches the listeners on the collections that hold it, as an event of the DOM goes up through the elements that hold its target.

```{rule} event-propagation
An event that triggers `on-click`, `on-release`, `on-dragstart`, `on-dragend` or `on-pointermove`
triggers each listener of that kind whose `active` holds, first on the shape on which the event
happens ({numref}`listener-triggers`), then on each collection that holds it, in order up to the
scene. When a listener that the event triggers has a `stop-propagation` that holds, the event goes
no further than the shape of that listener. An `on-pointermove` without a source is triggered after those on shapes,
unless the event stopped before the scene.
```

So with `(on-click c …)` on a circle `c` in a group `g` and `(on-click g …)`, a click on `c`
triggers both, the one on `c` first, and with `(stop-propagation true)` on the one on `c`, only that one.

This rule exists because a finger has no hover and is never quite still, so the runtime tells a tap from a drag by a distance.

```{rule} touch-events
A tap is a press and a release of a finger that has moved less than 8 CSS pixels between them. A
finger starts a drag only once it has moved 8 CSS pixels from its press. A press of a finger on a
shape triggers the `on-enter` listeners that the pointer coming onto the shape would trigger, and the
`on-leave` listeners of the same shapes are triggered at the next press of a finger elsewhere on the
page.
```

This rule exists so that a reader who cannot drag can make every drag with two taps, as WCAG 2.2 requires in its success criterion 2.5.7.

```{rule} drag-by-taps
A tap on a shape that a press would drag ({numref}`dragged-shape`) selects it, and the runtime draws a
ring around it. The next tap on the same canvas drags it as a drag from the point of the first tap to
the point of the second would: its `on-dragstart`, its movement once and its `on-dragend` are
triggered, and the selection ends. A tap on the selected shape, a press of a finger off the canvas,
and a press that is not a tap end the selection with no drag. The tap that drags the shape triggers
every other listener that a tap there triggers, and selects nothing.
```

## What limits a writer

This rule exists so that the illustrator can turn a writer on and off with a bool, and the movements that the writer has started are not cut short.

```{rule} writer-active
The runtime triggers a writer only when its `active` holds at the moment of the event that would
trigger it, and a control whose `active` does not hold takes no input from the reader. A movement
that a writer has started goes on being executed when the `active` of the writer stops holding.
```

This rule exists so that a writer can keep its writes within limits that hold for that writer alone, while other writers may write past them.

```{rule} guard-limits
Before a writer writes a number to a container A, the runtime brings the number into each guard
`(OP A B)` of that writer ({numref}`writer-guards`), with B evaluated at that moment: a number below B
becomes B when OP is `>` or `>=`, and a number above B becomes B when OP is `<` or `<=`. The guards
limit every write of the writer, those of its movements included, and a guard on the `x` or the `y`
of a shape limits that part of a write to its `pos`. The number is then written by
{numref}`writes-to-conditions`.
```

So with `(on-drag c c.pos (<= c.x 5))`, a drag of `c` past an `x` of 5 holds it at 5, and a
slider with no guard may still write 8 to `c.x`.

:::{admonition} Code differs
:class: note
A guard limits only a number that is written to exactly the container that it names
(`player.ts:327`, `clamped`), so `(<= c.x 5)` does not limit a movement that writes a point to
`c.pos`. Bead mtp-ydd4.7.101.
:::

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

## What the runtime computes again

This rule exists so that the runtime can find, for each write, the bound containers that the write can change.

```{rule} dependencies
A bound container depends on each container that its expression may read: directly, through each
function that it calls, and, where the container read is known only while drawing, as in
`g[side].pos`, on each container that the read may read. A read of a position depends also on the
attributes of each frame through which the runtime converts the value ({doc}`world-model`). When a
bound container A depends on a container B, and B depends on a container C, A depends on C too.
```

So with `(real k 1)`, `(real d (* 2 k))` and `(circle c (r d))`, `c.r` depends on `d` and on `k`,
and no bound container depends on `c.r`.

This rule exists so that after a write, the runtime computes again only what the write can change.

```{rule} stale-containers
Every bound container is stale when the runtime builds the live model. A write that changes the value
of a free container marks as stale every bound container that depends on it
({numref}`dependencies`), and no other. A write of a value that, after
{numref}`writes-to-conditions`, equals the value that the container holds
({numref}`equality-by-content`) changes nothing and marks nothing stale.
```

This rule exists so that the runtime computes each bound container at most once after each write, and only when its value is needed.

```{rule} recompute-on-read
The runtime computes a stale container again the first time that it is read after it became stale,
and the container is then no longer stale. A read of a bound container that is not stale results in
the value that the runtime last computed for it.
```

So after a write, the runtime computes again only the bound containers that depend on the container
written to and that are read, each of them once. By {numref}`evaluation-is-pure`, each of them then
holds the value that its expression evaluates to at that moment.

This rule exists so that every component on the page draws the values that the live model holds.

```{rule} components-draw-again
After each write that changes a container, and before the browser draws its next frame, each
component that reads the container, or a container that the write marked stale, draws again with
the values that the live model holds.
```
