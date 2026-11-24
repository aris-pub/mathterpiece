# Controls

A control is a {term}`component` that the reader acts on to write to the world model. This page gives
the signature of each control ({ref}`signatures`) and what each one writes.

:::{admonition} Code differs
:class: note
None of this page is built. The compiler has the slider, the button, the play, the stepper and the
toggle in older forms, and none of the other controls. Bead mtp-9e62.
:::

## What every control takes

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

```{rule} jumpers-and-movers
A control is a `jumper` or a `mover` ({numref}`the-types`). A jumper names one container, its
target, and writes a value to it by a jump each time the reader acts on it: it takes no movement.
A mover takes a movement, its effect, and plays it when the reader acts on it.
```

So a slider writes its number at once, wherever the reader drags its thumb, and a button plays a
movement that may take any time.

## The jumpers

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
  (step:real 1) (buttons:bool true) (typing:bool true)
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

```{rule} slider-and-dial
A slider and a dial are the same control on two kinds of number. The thumb of a slider runs along a
straight track from `from` to `to`. The thumb of a dial runs around a ring, and one full turn covers
the interval of its modular type, so turning past its end wraps around. On both:

- The reader clicks on the track or the ring to move the thumb there, drags the thumb, or steps it
  with the arrow keys.
- With `(step s)`, the thumb stops every s from the start, and an arrow key moves it one step.
  Without it, the thumb of a real target moves smoothly and an arrow key moves it 1/100 of the
  range, and the thumb of an int target stops at each whole number.
- With `(ticks s)`, a tick is drawn every s from the start. Without it, a tick is drawn at each
  step when there is a `(step …)`, and none otherwise.
```

```{rule} range-slider
A range slider has two thumbs on one track and writes to `LOW` and `HIGH`. A thumb that is dragged into
the other stops there, so `LOW` is never above `HIGH`. It takes no `(path …)`: its track is always
straight.
```

```{rule} number-field
A number field shows its target's value. The reader changes it by typing, by the − and + buttons,
by the arrow keys, or by dragging sideways on its label (scrubbing). The buttons and the arrow keys
add or subtract the step, and ten steps with Shift. Scrubbing moves the value one step every few
pixels. The mouse wheel does not change it.

- `(buttons false)` leaves out the − and + buttons, and `(typing false)` turns typing off, so the
  value is shown as plain text. With both, the value is drawn with a dotted underline, to show that
  it can be scrubbed.
- A typed value is written only when the reader commits it: with Enter, with Tab, or by leaving the
  field. Until then the field shows what is typed, and the target does not change.
- A committed value is written by {numref}`writes-to-constraints`. When it is not written, or is
  brought into the range of the target's conditions, the field shows the target's value and its
  box shows a red outline for a moment, and a screen reader is told the same.
```

```{rule} text-field
A text field shows its target's string. A typed string is written only when the reader commits it,
as in a number field. A string that breaks the conditions of the target's type is not written, and
the box shows a red outline for a moment.
```

```{rule} toggle
A toggle shows a checkbox with its target's value and its label. A click writes `(not TARGET)`. A
toggle holds no value of its own: when anything else writes to its target, the checkbox shows the new
value.
```

```{rule} select-options
The options of a select are its body. `(opt V L?)` is one option: the value V and, when it is given,
the label L shown for it, a string or a {term}`TeX string`. An option without a label shows its
value. The type of each V must be a {term}`subtype` of the type of the target, or, in a
multi-select, of the item type of the target. Choosing an option writes it to the target at once.
When the target holds a value that is no option, the select shows no option chosen.
```

```{rule} select-kinds
`kind` chooses how a select is drawn: `'menu'`, a button that shows the chosen option and opens a
list of all of them, `'buttons'`, every option as one of a row of connected buttons, and `'radio'`,
one option per line with a round mark. A multi-select has `'menu'` and `'buttons'` too, and
`'checkbox'`, one checkbox per option.
```

```{rule} multi-select
Choosing an option of a multi-select adds its value to the target list, and choosing it again
removes it. The list holds the chosen values in the order of the options in the source, whatever
the order in which they were chosen. Any number of options may be chosen, none included. A value in
the target list that is no option is shown as nothing chosen, never as an error.
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
