# Page interface

This page defines how a page places the {term}`components <component>` of a {term}`world model`,
the attributes and events that the {term}`runtime` puts in the page for each of them, the inputs of
each view and control, and the CSS custom properties that a page may set. What each control writes
is defined in {doc}`controls`, and what the runtime gives a screen reader and the keyboard in
{doc}`accessibility`.

## The elements of a page

This rule exists to specify how a page loads a .mtpc and names its {term}`live model`.

```{rule} model-element
A page loads the {term}`runtime script` with a `<script type="module">` element. Each
`<mtp-model>` element loads one .mtpc ({numref}`runtime-loads-mtpc`), and its `id` attribute names
the live model of that .mtpc in the page. Its `src` attribute is the address of the .mtpc, or `#`
followed by the `id` of a `<script type="application/json">` element of the page that holds the
.mtpc, before or after the `<mtp-model>`. In such a script element, every `</` of the .mtpc must be
written `<\/`. A page may hold several `<mtp-model>` elements, and each has a live model of its own.
```

So `<mtp-model id="dial" src="dial.mtpc"></mtp-model>` loads the file dial.mtpc, which the page
fetches from where it is served, and `<mtp-model id="dial" src="#dial-data"></mtp-model>` reads the
.mtpc from `<script type="application/json" id="dial-data">`, which may stand anywhere in the page.
A component of one live model never reads or writes to another live model.

This rule exists to specify how a page places each view and control, and what the runtime shows when it cannot draw one.

```{rule} component-elements
A page places a view or a control with an element whose tag is `mtp-` followed by the head of its
declaration, such as `<mtp-canvas>` or `<mtp-number-field>`. The `model` attribute of the element
is the `id` of an `<mtp-model>`, and its `name` attribute is the name of the component. The element
may stand anywhere in the page, inside a paragraph too, and may be added to the page at any time.
A component may be placed in several elements, its copies, and every copy shows the same live
model. When the .mtpc was refused, or declares no component of that name and kind, the runtime
shows a `<pre class="mtp-error">` that holds the error in place of the content of the element.
```

So `<mtp-slider model="dial" name="turn"></mtp-slider>` places the slider `turn` of the live model
`dial`, and two `<mtp-canvas model="dial" name="v">` elements show the same scene, each with its own
page state ({numref}`page-state`). A listener has no element ({numref}`runtime-serves-components`).

## Page state

This rule exists so that the CSS and the scripts of a page can read the state of each element without calling the runtime.

```{rule} page-state
The page state of an element is a set of attributes whose names start with `data-mtp-`, which the
runtime sets on `<mtp-model>` and on each copy of a view and a control. An attribute for a state
that holds or does not hold is present, with no value, while the state holds, and absent otherwise.
Every other attribute holds a value. At each change of the page state of an element, the runtime
fires one `mtp-state` event, which bubbles, on that element.
```

This rule exists to list the page state of each kind of element.

```{rule} page-state-attributes
The page state of each element is made of the attributes of its row:

| Element | Its attributes, each written here without `data-mtp-` |
|---|---|
| `mtp-model` | `ready`: every copy of every view of its model on the page is ready ({doc}`lifecycle`) |
| a canvas, a display, a readout | `ready`: the view is ready ({doc}`lifecycle`). `seen`: this copy has come into view ({doc}`lifecycle`). `mode`: `quiet` or `live`, only on a view with a quiet mode ({doc}`lifecycle`) |
| a slider, a range slider, a dial, a number field | `inactive`, and `held`: from a press on the `track`, the `ring`, a thumb, or the `scrub` or underlined `value` of a number field ({numref}`input-names`), until its release |
| a button, a toggle, a text field, a select, a multi-select | `inactive` |
| a play, a stepper | `inactive`, and `step`, `playing` and `exploring`: its step, 0 in explore mode, whether it plays, and whether it is in explore mode ({doc}`time`) |

`inactive` holds while the `active` of the control is false ({numref}`control-arguments`).
```

So a page may show a question once a play reaches its second step, with the CSS
`.fig:has(mtp-play[data-mtp-step="2"]) .q2 { display: block }`, and a script may wait for the
event `mtp-state` on `<mtp-model>` until it has `data-mtp-ready`.

This rule exists to specify how a control that belongs to views is shown while the reader does not use those views.

```{rule} control-folding
A control that belongs to views ({numref}`control-arguments`) is folded while every one of those
views is quiet, and only then: the page does not show it. When it folds or unfolds, the runtime
changes its height and its opacity over 300 milliseconds, or at once by {numref}`reduced-motion`. Each copy of the control has `data-mtp-folded` while it is folded, and
`data-mtp-folding` while its height changes. These two attributes are not page state, so the
runtime fires no `mtp-state` when they change.
```

A view with no quiet mode is never quiet ({doc}`lifecycle`), so a control that belongs to no view,
or to one view with no quiet mode, is never folded.

## Events

This rule exists so that a script of a page can act when a model has loaded and when its values change.

```{rule} model-events
The runtime fires these events on an `<mtp-model>`, each of which bubbles: `mtp-loaded`, once, when
its .mtpc has loaded or has been refused ({numref}`runtime-loads-mtpc`), and `mtp-change` after each
change of a value of its live model.
```

This rule exists so that a script that hears `mtp-state` on a play or a stepper reads values that match the attributes of the element.

```{rule} step-before-state
When the runtime fires `mtp-state` on a copy of a play or a stepper, its attributes `step` and
`playing` in the live model already hold the values of `data-mtp-step` and `data-mtp-playing` of
that copy. When the control has several copies, these attributes follow the copy that the reader
used last, or every copy alike before the reader has used one. The runtime fires this `mtp-state`
before the `mtp-change` of the same change.
```

## Values and inputs

This rule exists so that a script of a page can read the live model and never change it in a way that the reader could not.

```{rule} script-reads-values
The values of a live model are not page state, and the runtime never shows them as attributes. A
script of the page may read them from the `<mtp-model>` element, and may not write to them.
```

This rule exists so that a script can drive a page as the reader does, which is all that a test or a recording needs.

```{rule} inputs
An input is a part of an element that the reader presses, clicks, drags or types into. Each input
has the attribute `data-mtp-input`, whose value is its name, unique within its element. A script of
the page may act on an element only through its inputs, as the reader does: no element has a method
that changes it. To bring a page back to its starting state, a script must load the page again.
```

This rule exists to name the inputs of each kind of element.

```{rule} input-names
Each element has the inputs of its row, and only those. N is the number of options of a select or
a multi-select, of steps of a stepper, and of bars of a play: one per step with `(buttons true)`,
and one without.

| Element | Its inputs |
|---|---|
| a canvas, a display or a readout that has a quiet mode | `switch`, the button that makes the view live and quiet again ({doc}`lifecycle`). A view with no quiet mode has no input |
| a button | `button` |
| a toggle | `box`, its checkbox |
| a slider | `track` and `thumb` |
| a range slider | `track`, and `low` and `high`, the thumbs of `LOW` and `HIGH` |
| a dial | `ring` and `thumb` |
| a number field | `scrub`, its label. With `(typing true)`, `box`, the box that the reader types into, and with `(typing false)`, `value`, the text of the value. With `(buttons true)`, `minus` and `plus` |
| a text field | `box` |
| a select, a multi-select | `option-1` to `option-N`, its options in the order of the source, and with `(kind 'menu')`, `menu`, the button that opens the list of options |
| a play | `button`, and `bar-1` to `bar-N` |
| a stepper | `back`, `next`, and `dot-1` to `dot-N` |
```

So a script presses the plus of a number field with
`field.querySelector('[data-mtp-input="plus"]').click()`. What each input does is defined in
{doc}`controls` for the jumpers and in {doc}`time` for the play and the stepper.

:::{admonition} Code differs
:class: note
The compiler writes the slider, the button, the play, the stepper and the toggle only in their older
forms (bead mtp-9e62). The runtime draws the older slider, `(slider s (animation …))`, as one native
range input whose name is `track`, with no `thumb` (web/src/elements.ts:1236-1330).
:::

## CSS custom properties

This rule exists to name the CSS custom properties through which a page sets the colors of the controls and the fonts of a world model.

```{rule} page-custom-properties
A page may set these CSS custom properties, and the runtime draws each element with the values that
it inherits:

- `--mtp-control-rest` and `--mtp-control-active`, two CSS colors: the color of every control at
  rest, and while the reader presses it, holds it or gives it the focus from the keyboard, or while
  a play or a stepper plays. Where the page sets neither, both are the color `--primary-700`, or
  `--primary-600` for a toggle.
- For each font whose name is N, `--mtp-N-family`, `--mtp-N-style` and `--mtp-N-weight`. In N,
  each dot of a {term}`qualified name` is written `-`, and a name declared in another file has the
  name of that file first. The runtime draws with the declared value where the page sets none.
```

A variable of type `color` is an ordinary variable, and the page sets no color of a world model.

:::{admonition} Code differs
:class: note
The runtime also reads `--mtp-N` for each variable of type `color` and each attribute of type `color`
of a record whose name is N, and draws with the value that the page sets. The author decided on
2026-11-24 that the page sets no color variable.
:::

So with `(color ink #'navy')`, the CSS `mtp-canvas { --mtp-ink: crimson }` draws in crimson every
shape whose fill is `ink`, and `ink` from the file `house.mtp` is `--mtp-house-ink`. An expression
that reads `ink`, such as `(= ink #'navy')`, reads its value in the live model, not the value that
the page sets ({doc}`evaluation`). The runtime adds its own stylesheet for the controls to the page,
once. That stylesheet also reads the custom properties `--surface-page`, `--surface-hover`,
`--border-primary`, `--border-action`, `--radius-lg`, `--text-body`, `--text-subtle`,
`--text-error`, `--primary-200`, `--primary-300`, `--primary-600`, `--primary-700`, `--gray-100`,
`--ring` and `--ring-color`, which the page sets with a stylesheet of its own.

:::{admonition} Code differs
:class: note
Only a color computed by a read, an `if`, a `cond`, `mix`, `light-dark`, or the older names
`lighten` and `darken` of `tint` and `shade`, is drawn from the values that the page sets. A color
that a function declared with `func` evaluates to, or that is taken from a list, is drawn with its
value in the live model (web/src/runtime.ts:830, `compileCss`). Beads mtp-dliq and mtp-m1hb.
:::

## Listeners in views

This rule exists so that a listener acts only in the view where the reader can see what it acts on.

```{rule} listeners-in-views
The runtime triggers a listener only for events in the view whose body holds it. A listener on that
view itself is written without the view's name: `(on-view (move …))`.
```

A listener may be written only in the body of a view, and only in these views:

- in a canvas: a listener on a shape, `on-show`, `on-hide`, `on-view`, `on-ready`, `on-live`,
  `on-quiet` and `on-pointermove`
- in a display: a listener on a term of its formula, `on-live` and `on-quiet`
- in a readout: `on-live` and `on-quiet`.

A listener may not be written at the top level, and has no `(in …)`. A control is written at the
top level, and may hold `(in …)` with the names of the views that it belongs to.

## The view box of a canvas

This rule exists so that the runtime always has a whole box to draw, never part of one.

```{rule} canvas-view-box
A canvas has all four of the named arguments `x`, `y`, `width` and `height`, or none. One, two or three of
them is a compile error whose message names the missing ones. With all four, the runtime draws the box
of size `width` by `height` whose lower-left corner is [`x` `y`], in the scene's coordinates. With none,
the canvas has no attributes `x`, `y`, `width` and `height`, so reading or writing to one is a compile
error.
```

So in `(canvas v (x -3) (y -2) (width 6) (height 4) s)`, the runtime draws the box from -3 to 3
across and from -2 to 2 up, in `(canvas v s)` the box around the shapes of `s`, and
`(canvas v (x -3) (width 6) s)` is a compile error whose message holds the names `y` and `height`.

This rule exists so that a canvas with no box given still shows all of its shapes.

```{rule} canvas-fit
In a canvas with none of `x`, `y`, `width` and `height`, the runtime draws the box around the canvas's
shapes, with a margin on each side of 5% of the box's larger side. It works the box out for each copy
of the canvas on the page, from the shapes when it first draws that copy at a size on screen, and
then keeps it, whatever the shapes or the copy's size do later.
```

The runtime works the box out as follows.

- **Which shapes count.** The shapes that count are the shapes to which the items of the canvas
  evaluate at the moment when the runtime works the box out, and that exist at that moment. A
  group counts by its members that exist, cut to the box of its clip when it has
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
