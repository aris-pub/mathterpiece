# Lifecycle

This page defines what happens to a view from the moment when the page opens: the states of a canvas
before the reader acts on it, the moment when it becomes ready, the quiet and live modes of a view,
and what a canvas draws while it starts or stops drawing a shape. Each element of the page that
places a view is a copy of the view ({doc}`page-interface`), and the rules of this page apply to each
copy on its own, except where a rule states otherwise. The listeners on this page are triggered
when a view or what it draws changes, and not by the pointer ({doc}`reactivity`).

## The listeners on views

This rule exists to fix the arguments of each listener on a view, so that the compiler can check every such listener in a source.

````{rule} view-listener-signatures
```mtp-sig
(on-view MOVEMENT:movement
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 1000)
  (doc:string '')
  CONDITIONS:bool*)

(on-ready MOVEMENT:movement
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 300)
  (doc:string '')
  CONDITIONS:bool*)

(on-live MOVEMENT:movement
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)

(on-quiet MOVEMENT:movement
  (active:bool true)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)

(on-show SOURCE:shape MOVEMENT:movement
  (doc:string ''))

(on-hide SOURCE:shape MOVEMENT:movement
  (doc:string ''))
```

`MOVEMENT` is the movement that the runtime executes when the listener is triggered. `SOURCE` is a
shape that the canvas may draw. `CONDITIONS` are the guards of the listener ({numref}`writer-guards`).
````

## From page load to ready

This rule exists to name the values from which a canvas starts, before and after its `on-view`.

```{rule} start-states
A state is a value for each free container of the live model. State -1 of a canvas is the state
when the page opens, and exists only when the canvas has an `on-view`. State 0 of a canvas with an
`on-view` is the state after the movement of the `on-view` has been executed from state -1, and
state 0 of a canvas with no `on-view` is the state when the page opens.
```

This rule exists so that an `on-view` is executed the first time that the reader can see its canvas, and never over values that a writer has changed before.

```{rule} on-view-trigger
The runtime triggers the `on-view` of a copy of a canvas when the copy first comes into view, if the
canvas is not ready yet and every free container that the movement of the `on-view` writes to still
matches ({numref}`matching`) its value in state -1. Otherwise it never triggers that `on-view` in
that copy. A copy comes into view when part of it is on the screen and neither it nor an element
that holds it is fully transparent, hidden or not displayed, whether the copy is quiet or live.
```

So a page that keeps its content at opacity 0 while it loads delays every `on-view` until the content
is shown.

This rule exists so that the compiler can work out state 0, and so that every `on-view` ends.

```{rule} on-view-movement
The movement of an `on-view` may not loop without end, and no `(move …)` in it may have a `to` that
reads its target or a container that depends on its target ({numref}`dependencies`). Either is a
compile error.
```

This rule exists so that every copy of a canvas becomes ready at the same moment, and as soon as one copy has reached state 0.

```{rule} canvas-ready
A canvas becomes ready in every copy at once, at the first moment when the `on-view` of one of its
copies ends. A canvas with no `on-view` is ready when the page opens, and a canvas with a copy that
comes into view without triggering its `on-view` ({numref}`on-view-trigger`) is ready from that
moment. Once ready, a canvas stays ready. A display and a readout are ready when the page opens, and
the page is ready once every view on it is ready.
```

:::{admonition} Code differs
:class: note
The runtime makes a canvas ready only once no `on-view` of any of its copies is executed
(`lifecycle.ts:78`), so a canvas is not ready while the `on-view` of a second copy is executed,
although the `on-view` of the first copy has ended. Bead mtp-ydd4.7.102.
:::

This rule exists so that the reader acts on a canvas only once it has reached state 0.

```{rule} before-ready
Until a canvas is ready, the listeners in its body that the pointer triggers ({numref}`listener-triggers`)
are not triggered in it, and the reader cannot make it live ({numref}`quiet-and-live`). Until then, a
control takes no input when it writes to a container on which a shape that the canvas may draw
depends, and the canvas has a copy on the page.
```

This rule exists so that a canvas can start a movement once, when the reader can first act on it.

```{rule} on-ready-trigger
The runtime triggers the `on-ready` of a canvas when the canvas becomes ready, once for the canvas
and not once for each copy.
```

So a loop that is to run while the reader uses the canvas is written in its `on-ready`, since an
`on-view` may not loop ({numref}`on-view-movement`).

## Quiet and live

This rule exists so that a view can rest on the page until the reader chooses to use it.

```{rule} quiet-and-live
A view that holds an `on-live` is quiet or live, and every other view is always live. Each copy of
such a view is quiet when the page opens. A press on the button that the runtime draws in the top
right corner of a quiet copy, or Enter or Space while that button has the focus, makes the copy live,
and the runtime then triggers each `on-live` of the view. A press on the same button, or Escape while
the focus is in the copy, makes it quiet again, and the runtime then triggers each `on-quiet` of the
view. An `on-quiet` in a view with no `on-live` is a compile error.
```

So when a copy becomes quiet, every container that its `on-quiet` does not write to keeps its value.

:::{admonition} Code differs
:class: note
The runtime keeps one mode for each view, shared by all its copies (`runtime.ts:169`, and `setLive`
in `elements.ts:220`), so a press on the button of one copy makes every copy live. Bead
mtp-ydd4.7.103.
:::

This rule exists so that a quiet view takes no input from the pointer, and a reader who scrolls past it on a phone is not caught by it.

```{rule} while-quiet
While a copy is quiet, the listeners in its body that the pointer triggers
({numref}`listener-triggers`) are not triggered in it, and a quiet copy of a canvas neither pans nor
zooms, so a finger on it scrolls the page. When a copy of a canvas becomes quiet, it drops what the
reader panned and zoomed. A control whose `(in …)` names views is hidden while every copy of each of
those views is quiet.
```

## Showing and hiding a shape

This rule exists so that a canvas can move a shape on the screen as it starts or stops drawing it, without any change to the live model.

```{rule} show-and-hide
Once a canvas is ready, the runtime triggers the `on-show` of a shape in a copy when the copy starts
drawing the shape, and its `on-hide` when the copy stops drawing it, such as when an item of the
canvas starts or stops evaluating to the shape. The copy stops drawing the shape only when the movement
of the `on-hide` ends. Before the canvas is ready, a copy starts and stops drawing a shape at once,
with no `on-show` or `on-hide`. An `on-show` or an `on-hide` on a collection is triggered for each
shape that the collection holds, at any depth, unless the shape or a collection nearer to it has its
own of the same kind.
```

This rule exists because a shape that a canvas does not draw is hidden, with `drawn` 0 and `opacity` 0, so the movement of an `on-show` and that of an `on-hide` must both write to these two attributes.

```{rule} show-and-hide-movements
The movement of an `on-show` or an `on-hide` must write to the `drawn` and the `opacity` of its source
and of every shape that the source holds, at any depth, directly or through a collection that holds
the shape. A movement of an `on-show` or an `on-hide` that leaves one of them unwritten, or that
writes to anything other than its source and the shapes that it holds, is a compile error, and so
are two listeners of one kind on one shape in one canvas.
```

This rule exists so that an `on-show` or an `on-hide` moves the shape on the screen while the shape in the live model keeps every attribute ({numref}`runtime-adds-no-objects`).

```{rule} stand-ins
While the movement of an `on-show` or an `on-hide` is executed in a copy, the copy draws a stand-in in
place of the shape, and the movement writes to the stand-in. Each attribute of the stand-in holds the
value of the same attribute of the shape, plus an offset for each attribute that the movement writes
to. A move turns its `from` and its `to` into offsets from the value of the shape when the move
starts, and writes only the offset, so a move with no `to` ends on the value of the shape. For a
color, the stand-in blends from the value of the move to the color of the shape instead, and `drawn`
is written with no offset. The pointer passes through a stand-in, and the copy drops the stand-in
when the movement ends.
```

So with an `on-show` that writes to `name.y` from -6, a text `name` whose `y` is -4 rises from -6 to
-4, and when a writer writes -3 to `name.y` meanwhile, the stand-in ends on -3.

This rule exists so that a shape that the reader shows and hides again in quick succession turns back from where it is drawn, with no jump.

```{rule} show-and-hide-reversed
When a copy starts drawing a shape again while its `on-hide` is executed, or stops drawing it while
its `on-show` is executed, the movement being executed ends, and the other one starts from the
stand-in as it is drawn at that moment. A shape that stops existing while a copy draws it is hidden by
its `on-hide` on a stand-in that keeps the last values of the shape.
```

This rule exists so that a state set by a play or a stepper looks the same however the reader reached it.

```{rule} states-drawn-at-once
While a play or a stepper sets a state ({doc}`time`), each copy starts and stops drawing shapes at
once, with no `on-show` or `on-hide`, and each `on-show` and `on-hide` being executed ends at once,
with its stand-in where its movement would end.
```
