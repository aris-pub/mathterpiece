# Page interface of views and controls

Status: approved by the author, 2026-11-13. Not built yet.

## Rules

1. **Reading.** Each element (`mtp-model`, every view and every control) shows its own page
   state on itself as `data-mtp-…` attributes: present or absent for a yes/no state, a value
   otherwise. Every change of its page state fires one `mtp-state` event on that element.
2. **Scene values** are not page state. They are never shown as attributes. A script reads them
   from `<mtp-model>` and never writes them.
3. **Driving.** A script acts on an element only through its inputs, as a reader does. Each piece
   of an element the reader presses, clicks or drags is an input and carries
   `data-mtp-input="name"`, the name unique within its element. No element has methods that
   change it. To start again, a script reloads the page.
4. **Names.** Every attribute carries the `data-mtp-` prefix.

## What follows for each kind

| Element | Attributes (each `data-mtp-…`) | Inputs (`data-mtp-input=…`) |
|---|---|---|
| `mtp-model` (the page) | `ready` | none |
| canvas, display, readout | `ready`, `seen`, `mode` (`quiet` or `live`) | `switch` (the hand) |
| button | `inactive` | `button` |
| toggle | `inactive` | `box` |
| slider | `inactive`, `held` | `track` |
| play | `inactive`, `step`, `playing`, `exploring` | `button`, `bar-1` to `bar-N` |
| stepper | `inactive`, `step`, `playing`, `exploring` | `back`, `next`, `dot-1` to `dot-N` |

`inactive` is present while a control's `(active bool)` does not hold. `step` is 0 in explore
mode, and `exploring` is present then.

## Events

`mtp-state` on each element replaces `mtp-mode` and `mtp-rest`. On `<mtp-model>`, `mtp-change`
stays, and the old `mtp-ready` (the model has loaded) is renamed `mtp-loaded`: both are about
the model and the scene, not page state.

During `mtp-state` on a play or a stepper, its `step` and `playing` values read from
`<mtp-model>` already match its attributes, or for copies, the attributes of the copy that moved
the scene last.

## The view box of a canvas

```{rule} canvas-view-box
A canvas gives all four of `x`, `y`, `width` and `height`, or none of them. A canvas that gives
one, two or three of them is an error, and the error names the ones that the canvas leaves out.
With all four, the canvas shows the box whose lower-left corner is the point (`x`, `y`) and whose
size is `width` by `height`, in the scene's own coordinates. A canvas that gives none of them has
no attributes `x`, `y`, `width` and `height`, so reading or writing any of them is an error.
```

So `(canvas v (x -3) (y -2) (width 6) (height 4) s)` shows the box from -3 to 3 across and from -2
to 2 up, `(canvas v s)` shows the box of the shapes of `s`, and `(canvas v (x -3) (width 6) s)` is an
error that names `y` and `height`.

```{rule} canvas-fit
A canvas that gives none of `x`, `y`, `width` and `height` shows the box around its shapes, with a
margin on each side of 5% of the larger of the box's width and height. The runtime works the box
out for each copy of the canvas on the page, from the shapes that the canvas draws the first time
that the runtime draws that copy at a size on screen, and then keeps it. The box stays the same
when the shapes move, appear or disappear later, and when the copy changes size on screen.
```

The box is made as follows.

- **Which shapes count.** The shapes that count are those that the items of the canvas give at the
  moment when the runtime works the box out, and that exist at that moment. A container counts by
  its members that exist, cut to the box of its clip when it has one. A shape that the canvas
  draws with no paint, or fully transparent, still counts. A shape whose `on-show` or `on-hide`
  plays at that moment counts as the scene gives it, not as its stand-in.
- **How a shape counts.** A shape counts by the smallest rectangle, with sides along the axes,
  around its geometry after every transform on the way to the scene. Strokes and heads are left
  out, since their sizes are in screen pixels. A group with `(fixed-size true)` counts by its
  position, since its members have no size in scene units.
- **Texts.** A text counts by the box that its letters take up as the runtime draws them. A text's
  size on screen is fixed, so its size in the scene depends on the box that the copy shows. The
  box is therefore the smallest box that holds every text at the size that this box gives it.
  When no box can hold the texts, because they are wider than the copy on screen, each text
  counts by its position alone, and the texts can reach past the edges of the canvas.
- **The margin.** The margin on each side is 5% of the larger of the box's width and height, so a
  line along an axis gets a margin across it too. A line from `[0 0]` to `[10 0]` gives the view
  from -0.5 to 10.5 across and from -0.5 to 0.5 up.
- **A box of no size.** When the shapes that count give a box with no width and no height, as a
  circle of radius 0 does, the canvas shows the square of side 20 whose center is that point, with
  no margin. When no shape counts, because every item gives `none` or nothing exists at that
  moment, the canvas shows the box from -10 to 10 on both axes. A box with a width and no height,
  or a height and no width, gets its margin as any other box does.
- **Frame, pan and zoom.** The canvas's frame, its `shift-x`, `shift-y`, `rotate`, `scale-x` and
  `scale-y`, applies about the center of the box, as a shape's frame does ({doc}`data-model`). The
  box is worked out from the shapes before the frame applies, so a frame can move shapes out of
  the view, as it can on a canvas that gives its own box. The reader pans and zooms from this box
  as from a box that the canvas gives, and a double click goes back to it.
- **Before a copy has a size.** The runtime can measure a text only in a copy that has a size on
  screen. A copy has no size, for example, while it is in a part of the page that is hidden, and
  then the page shows nothing of it. Until the copy has a size, the runtime draws it with the box
  of the shapes that the canvas draws the first time that the runtime draws the copy, with each
  text counted by its position.
- **Copies.** A text has the same size on screen in every copy, so two copies of one canvas that
  draw a text and have different widths on screen can show different boxes.
