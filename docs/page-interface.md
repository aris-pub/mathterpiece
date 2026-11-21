# Page interface of views and controls

Status: approved by the author, 2026-11-13. Not built yet.

## Rules

1. **Reading.** The runtime sets the page state of each element (`mtp-model`, every view and every
   control) as `data-mtp-…` attributes on that element: an attribute is present or absent for a
   yes or no state, and holds a value otherwise. At every change of the page state of an element,
   the runtime fires one `mtp-state` event on that element.
2. **Values of the scene.** The values of the scene are not page state, and the runtime never sets
   them as attributes. A script may read them from `<mtp-model>`, and may not write them.
3. **Driving.** A script may act on an element only through its inputs, as a reader does. Each
   part of an element that the reader presses, clicks or drags is an input, and has the attribute
   `data-mtp-input="name"`, with a name that is unique within its element. No element has methods
   that change it. To start again, a script must reload the page.
4. **Names.** The name of every attribute starts with `data-mtp-`.

## Attributes and inputs of each kind of element

| Element | Attributes (each `data-mtp-…`) | Inputs (`data-mtp-input=…`) |
|---|---|---|
| `mtp-model` (the page) | `ready` | none |
| canvas, display, readout | `ready`, `seen`, `mode` (`quiet` or `live`) | `switch` (the hand) |
| button | `inactive` | `button` |
| toggle | `inactive` | `box` |
| slider | `inactive`, `held` | `track` |
| play | `inactive`, `step`, `playing`, `exploring` | `button`, `bar-1` to `bar-N` |
| stepper | `inactive`, `step`, `playing`, `exploring` | `back`, `next`, `dot-1` to `dot-N` |

`inactive` is present while the `active` of a control is false. `step` is 0 in explore mode, and
`exploring` is present then.

## Events

The event `mtp-state` of each element replaces the events `mtp-mode` and `mtp-rest`. The runtime
still fires `mtp-change` on `<mtp-model>`, and the old event `mtp-ready`, which the runtime fires
when the model has loaded, is renamed `mtp-loaded`. Both events are about the model and the scene,
not about page state.

When the runtime fires `mtp-state` on a play or a stepper, the values of `step` and `playing` that a
script reads from `<mtp-model>` already match the attributes of that element. For a control with
several copies on the page, they match the attributes of the copy that changed the scene last.

## The view box of a canvas

```{rule} canvas-view-box
A canvas must have all four of the named arguments `x`, `y`, `width` and `height`, or none of them.
A canvas that has one, two or three of them is a compile error, and the message of the error holds
the names of the missing ones. In a canvas with all four, the runtime draws the box whose
lower-left corner is the point [`x` `y`] and whose size is `width` by `height`, in the coordinates
of the scene. A canvas with none of them has no attributes `x`, `y`, `width` and `height`, so an
expression that reads one of them, or a writer that writes one, is a compile error.
```

So in `(canvas v (x -3) (y -2) (width 6) (height 4) s)`, the runtime draws the box from -3 to 3
across and from -2 to 2 up, in `(canvas v s)` the box around the shapes of `s`, and
`(canvas v (x -3) (width 6) s)` is a compile error whose message holds the names `y` and `height`.

```{rule} canvas-fit
In a canvas with none of `x`, `y`, `width` and `height`, the runtime draws the box around the shapes
of the canvas, with a margin on each side of 5% of the larger of the box's width and height. The
runtime works the box out for each copy of the canvas on the page, from the shapes of the canvas at
the first time that it draws that copy at a size on screen, and then keeps it. The box stays the
same when the shapes move, appear or disappear later, and when the copy changes size on screen.
```

The runtime works the box out as follows.

- **Which shapes count.** The shapes that count are the shapes to which the items of the canvas
  evaluate at the moment when the runtime works the box out, and that exist at that moment. A
  group, a row or a column counts by its members that exist, cut to the box of its clip when it has
  one. A shape with no paint, or a fully transparent one, still counts. A shape whose `on-show` or
  `on-hide` is playing at that moment counts with the attributes that it has in the scene, not as
  its stand-in.
- **How a shape counts.** A shape counts by the smallest rectangle, with sides along the axes,
  around its geometry after the frames of the shape and of every collection that holds it. Strokes
  and heads are left out, since their sizes are in screen pixels. A group with `(fixed-size true)`
  counts by its position, since its members have no size in the units of the scene.
- **Texts.** A text counts by the box that its letters take up when the runtime draws them. The
  size of a text on screen is fixed, so its size in the scene depends on the box that the runtime
  draws in the copy. The box is therefore the smallest box that holds every text at the size that
  the text has in this box. When no box can hold the texts, because they are wider than the copy
  on screen, each text counts by its position alone, and the texts can reach past the edges of the
  canvas.
- **The margin.** The margin on each side is 5% of the larger of the box's width and height, so a
  line along an axis has a margin across it too. For a line from `[0 0]` to `[10 0]`, the runtime
  draws the box from -0.5 to 10.5 across and from -0.5 to 0.5 up.
- **A box of no size.** When the box around the shapes that count has no width and no height, as
  for a circle of radius 0, the runtime draws the square of side 20 whose center is that point,
  with no margin. When no shape counts, because every item evaluates to `none` or nothing exists at
  that moment, the runtime draws the box from -10 to 10 on both axes.
- **Frame, pan and zoom.** The frame of the canvas, its `shift-x`, `shift-y`, `rotate`, `scale-x`
  and `scale-y`, applies about the center of the box, as the frame of a shape does
  ({doc}`data-model`). The runtime works the box out before it applies the frame, so a frame can
  move shapes out of the box, as it can in a canvas with `x`, `y`, `width` and `height`. The reader
  may pan and zoom from this box as from a box set by `x`, `y`, `width` and `height`, and on a
  double click the runtime draws this box again.
- **Before a copy has a size.** The runtime can measure a text only in a copy that has a size on
  screen. A copy has no size, for example, while it is in a part of the page that is hidden, and
  then no part of the copy is visible. Until the copy has a size, the runtime draws it with the box
  around the shapes of the canvas at the first time that the runtime draws the copy, with each text
  counted by its position.
- **Copies.** A text has the same size on screen in every copy, so the runtime can draw different
  boxes in two copies of one canvas that hold a text and have different widths on screen.
