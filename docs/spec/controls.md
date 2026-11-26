# Controls

A control is a {term}`component` that the reader acts on to write to the world model. This page gives
the signature of each control ({ref}`signatures`) and what each one writes.

:::{admonition} Code differs
:class: note
None of this page is built. The compiler has the slider, the button, the play, the stepper and the
toggle in older forms, and none of the other controls. Bead mtp-9e62.
:::

## What every control takes

This rule exists so that every control takes the same common arguments, which the signatures below then need not repeat.

````{rule} control-arguments
Every control takes these arguments, which the signatures below write as `(like control)`:

```mtp-sig
(control
  (label:string '')
  (active:bool true)
  (in VIEWS:view*)
  (priority:(int (>= 1) (<= 1000)) 500)
  (doc:string '')
  CONDITIONS:bool*)
```

`label` is the text shown with the control, a string or a {term}`TeX string`. `VIEWS` are the views
that the control belongs to ({numref}`listeners-in-views`). `CONDITIONS` are the guards of the
control ({numref}`writer-guards`).
````

## Jumpers and movers

This rule exists to separate the controls that write to a container directly from those that play a movement, since the runtime handles the two kinds differently.

```{rule} jumpers-and-movers
A control is a `jumper` or a `mover` ({numref}`the-types`). A jumper names one container, its target,
and writes a value to it by a jump each time the reader acts on it, with no movement. A mover takes a
movement, its effect, and plays it when the reader acts on it.
```

So a slider writes its number at once, wherever the reader drags its thumb, and a button plays a
movement that may take any time.

## The jumpers

This rule exists to fix the arguments of each jumper, so that the compiler can check every control in a source.

````{rule} jumper-signatures
```mtp-sig
(slider NAME TARGET:real
  (from:real) (to:real)
  (step:real none) (ticks:real none)
  (like control))
(range-slider NAME LOW:real HIGH:real
  (from:real) (to:real)
  (step:real none) (ticks:real none)
  (like control))
(dial NAME TARGET:mod
  (step:real none) (ticks:real none)
  (like control))
(number-field NAME TARGET:real
  (step:(real (> 0)) 1) (buttons:bool true) (typing:bool true)
  (like control))
(text-field NAME TARGET:string (like control))
(toggle NAME TARGET:bool (like control))
(select NAME TARGET
  (kind:(string (one-of 'menu' 'buttons' 'radio')) 'menu')
  (like control)
  OPTIONS:opt+)
(multi-select NAME TARGET
  (kind:(string (one-of 'menu' 'buttons' 'checkbox')) 'menu')
  (like control)
  OPTIONS:opt+)
```

`TARGET:mod` is a target whose type is a modular type, written with the head `mod`. In a select,
`TARGET` is a container of any type, and in a multi-select a container whose type is a list.
````

This rule exists so that the runtime draws and handles a slider and a dial the same way, apart from wrapping.

```{rule} slider-and-dial
A slider and a dial are one control on two kinds of number. A slider's thumb runs along a straight
track from `from` to `to`. A dial's thumb runs around a ring, one full turn covering its modular type's
interval, so it wraps. On both:

- The reader clicks on the track or ring to move the thumb there, drags the thumb, or steps it with the
  arrow keys.
- A `step` or a `ticks` that is 0 or below is a compile error.
- With `(step s)`, the thumb stops every s from the start, and an arrow key moves one step. Without it,
  a real target moves smoothly, an arrow key moving 1/100 of the range, and an int target stops at each
  whole number.
- With `(ticks s)`, a tick is drawn every s from the start. Without it, there is a tick at each step,
  and none when there is no step.
```

This rule exists to specify how the runtime keeps the two values of a range slider in order.

```{rule} range-slider
A range slider has two thumbs on one straight track and writes to `LOW` and `HIGH`. A thumb dragged into
the other stops there, so `LOW` is never above `HIGH`. A press on the track away from both thumbs
moves the nearer one there.
```

This rule exists to specify every way in which the reader changes a number field, and when the runtime writes the value.

```{rule} number-field
A number field shows its target's value. The reader changes it by typing, by the − and + buttons, by
the up and down arrow keys, which add or subtract the step, or ten steps with Shift, or by dragging sideways on
its label (scrubbing), one step every few pixels. The mouse wheel does not change it.

- `(buttons false)` leaves out the buttons, and `(typing false)` turns typing off and shows the value as
  plain text. With both, the value has a dotted underline, to show that it can be scrubbed.
- A typed value is written only when the reader commits it, with Enter, with Tab or by leaving the
  field. Until then the target does not change.
- A committed value is written by {numref}`writes-to-conditions`. When it is refused or brought into
  range, the field shows the target's value, its box shows a red outline for a moment, and a screen
  reader is told the same.
```

This rule exists to specify when the runtime writes the text of a text field, and what it shows when the text is refused.

```{rule} text-field
A text field shows its target's string. A typed string is written only when committed, as in a number
field, and a string that breaks the target's conditions is not written, with a red outline on the box
for a moment. In a number field and a text field, while typed text is not committed, the arrow keys
move the text cursor as in any text box, and Escape drops the typed text and shows the target's value
again.
```

This rule exists to specify what a toggle writes, and that it always shows the current value of its target.

```{rule} toggle
A toggle shows a checkbox with its target's value and its label, and a click writes `(not TARGET)`. It
holds no value of its own, so it always shows the target's current value.
```

This rule exists to specify how the options of a select are written, and how the compiler checks their values.

```{rule} select-options
A select's body is its options. `(opt V L?)` is the value V with an optional label L, a string, and an
option without one shows its value. Each V must be of a {term}`subtype` of the target's type, or, in a
multi-select, of its item type. Choosing an option writes it to the target at once. When the target
holds no option's value, no option is shown chosen.
```

This rule exists to fix the ways in which the runtime may draw a select.

```{rule} select-kinds
`kind` sets how a select is drawn: `'menu'`, a button showing the chosen option, or the control's label when none is
chosen, that opens the list of all of them, `'buttons'`, a row of connected buttons, or `'radio'`, one option per line with a round mark.
A multi-select has `'menu'`, `'buttons'` and `'checkbox'`, one checkbox per option.
```

This rule exists so that the list that a multi-select writes has one order, whatever order the reader chose in.

```{rule} multi-select
Choosing an option of a multi-select adds its value to the target list, and choosing it again removes it.
The list keeps the options' order in the source, and may hold any number of them, none included. A value
in the list that is no option, which another writer may have put there, is shown as nothing chosen,
never as an error, and stays in the list after the chosen options.
```

For example:

```mtp
(string mean 'arithmetic')
(select means mean (label 'mean') (kind 'buttons')
  (opt 'arithmetic' $'\frac{a+b}{2}')
  (opt 'geometric' $'\sqrt{ab}')
  (opt 'harmonic'))

(list[string] curves {'circle'})
(multi-select shown curves (label 'curves') (kind 'checkbox')
  (opt 'circle') (opt 'ellipse') (opt 'parabola') (opt 'hyperbola'))

(slider size k (from 0) (to 1) (label 'k'))
(dial turn theta (step 15))
(number-field sides n (label 'sides'))
```

## The movers

This rule exists to fix the arguments of each mover, so that the compiler can check every control in a source.

````{rule} mover-signatures
```mtp-sig
(button NAME EFFECT:movement (like control))
(play NAME EFFECT:movement
  (buttons:bool false) (rest:(real (>= 0)) 0)
  (labels LABELS:string*)
  (like control))
(stepper NAME EFFECT:movement (like control))
```

`EFFECT` is required. A press of a button plays its effect from the start. A play plays its effect
and lets the reader scrub it, and a stepper goes through its steps one at a time
({doc}`time`).
````

```mtp
(button b (move k (to 1) (duration 2)) (label 'go'))
```
