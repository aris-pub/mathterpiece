# Accessibility

This page defines what the {term}`runtime` gives a screen reader and the keyboard for each
{term}`component`, and what it does when the reader asks the browser for reduced motion. The roles,
names and states below are those of WAI-ARIA 1.2. The inputs of each element are named in
{numref}`input-names`, and what each control writes is defined in {doc}`controls`.

## Names

This rule exists so that a screen reader names each control as the page shows it.

```{rule} control-names
A screen reader reads the label of a control ({numref}`control-arguments`) as the name of the
control, and the label of an option of a select or a multi-select as the name of the option
({numref}`select-options`). Each label is read as the text of its string, so a label that
holds LaTeX is read as that LaTeX. An option with no label is read as its value, written as
`(fmt V)` writes it.
```

So with `(label $'\frac{a+b}{2}')`, the page shows the formula, and a screen reader reads
`\frac{a+b}{2}`. The names of the inputs that have no label of their own are given in
{numref}`jumper-roles`, {numref}`mover-roles` and {numref}`view-reading`.

## What a screen reader gets

This rule exists to fix what a screen reader gets for each input of a jumper.

```{rule} jumper-roles
Each input of a jumper has the role, the name and the state of its row. A value is written as
`(fmt V)` writes it.

| Input | Role | Name, and state |
|---|---|---|
| the `box` of a toggle | `checkbox` | the label, and checked while its target is true. When the target stands for several containers ({numref}`writable-targets`), mixed while some of them are true and the others false |
| the `thumb` of a slider and of a dial, and the `low` and `high` of a range slider | `slider` | the label of the control, followed by `, low` and `, high` on a range slider. Its value is its target's value, its least and greatest values are the smaller and the larger of `from` and `to`, or the ends of the modular type of a dial ({numref}`modular-types`), and its value text is the value of its target written |
| the `box` or the `value` of a number field | `spinbutton` | the label. Its value is its target's value, and its value text the value written |
| the `minus` and the `plus` of a number field | `button` | `decrease` and `increase` |
| the `box` of a text field | `textbox` | the label |
| the `menu` of a select or a multi-select | `button`, which opens a `listbox` | the label and the options chosen. Each option in the list has the role `option`, and is selected while it is chosen |
| an option of a select of kind `'buttons'` | `radio`, in a `radiogroup` | checked while it is chosen |
| an option of a multi-select of kind `'buttons'` | `button`, in a `group` | pressed while it is chosen |
| an option of a select of kind `'radio'`, or of a multi-select of kind `'checkbox'` | `radio` in a `radiogroup`, or `checkbox` in a `group` | checked while it is chosen |
```

The `track` of a slider and the `ring` of a dial have no role, and the thumb holds the value of the
target. The ticks of a slider and of a dial, and the value in the middle of a dial, are
hidden from a screen reader, since the value text of the thumb holds the value.

This rule exists to fix what a screen reader gets for each input of a mover.

```{rule} mover-roles
Each input of a mover has the role, the name and the state of its row. k is the step of the play or
the stepper, and N its number of steps ({doc}`time`).

| Input | Role | Name, and state |
|---|---|---|
| the `button` of a button | `button` | the label |
| the `button` of a play | `button` | the label, and `pause` while the play plays |
| the row of the bars of a play | `slider` | the label. Its value is k, from 0 to N, and its value text is `k / N`, followed by ` · L` when step k has the label L of `(labels …)`, or in explore mode `N steps`, or `1 step` when N is 1 |
| the `back` and the `next` of a stepper | `button` | `previous step` and `next step` |
| `dot-1` to `dot-N` of a stepper | `button`, in a `group` | `step 1` to `step N`, and the dot of step k is marked as the current step. The group is named by the label followed by `: step k of N`, or in explore mode by `: N steps`, or `: 1 step` when N is 1 |
```

The step count beside a play and a stepper, and the pill that reads `Exploring`, are hidden from
a screen reader, since the value text of the row of bars and the name of the group of dots hold
the same.

This rule exists to fix what a screen reader gets for each view.

```{rule} view-reading
A readout is its text in the line of the page, which a screen reader reads as any text of the page.
The runtime gives a canvas no role, no name and no description, and gives the formula of a display
the role `img`, with no name. The `switch` of a view with a quiet mode is a button named
`Interactive figure: open it` while the view is quiet, and `Back to the plain figure` while it is
live.
```

This rule exists so that a screen reader hears what the red outline of a refused commit shows.

```{rule} refused-commit-message
When the runtime refuses a committed value of a number field or a text field, or brings it into the
conditions of the target ({numref}`number-field`, {numref}`text-field`), it puts a message in a part
of the control that a screen reader reads when it changes, and that the page does not show. With T the typed text
and V the value that the field shows after the commit, the message of a number field is
`T is not allowed. The value is V.`, and that of a text field is `“T” is not allowed.`.
```

This rule exists so that a screen reader and the keyboard treat an input that the reader may not use as turned off.

```{rule} inputs-turned-off
While a control is inactive ({numref}`page-state-attributes`), or belongs to a canvas on the page
that is not ready ({doc}`lifecycle`), each of its inputs is turned off: a press on it does nothing,
the keyboard cannot give it the focus, except the row of the bars of a play, and a screen reader
reads it as turned off. A `back` at step 0 and a `next` at the last step of a stepper are turned off
too.
```

## The keyboard

This rule exists to fix which inputs the keyboard reaches, and in which order.

```{rule} focus-order
The Tab key moves the focus through the inputs that are not turned off, in the order of the page,
and reaches these:

- every input of a view, a button, a toggle, a slider, a range slider, a dial, a text field and a
  stepper, except the `track` and the `ring`
- the `box` or the `value` of a number field, and not its `scrub`, `minus` and `plus`
- the `menu` of a select or a multi-select of kind `'menu'`. While the list of options is open, the
  list has the focus
- the chosen option of a select of kind `'buttons'` or `'radio'`, or its first option when none is
  chosen, and every option of a multi-select of kind `'buttons'` or `'checkbox'`
- the `button` of a play and the row of its bars.
```

A press on the `track` of a slider moves the focus to the thumb that it moves, and a press on the
`ring` of a dial to its thumb.

This rule exists to fix what each key does on each control.

```{rule} control-keys
With the focus on an input of a control, these keys act as the table lists. On a thumb and a number
field, no arrow key acts while Alt, Control or Meta is held. On a play and a stepper, no key of the
table acts then, nor a key that repeats because it is held down. Enter and Space press a button, and
the browser's own keys act on a checkbox and a radio button.

| Control | Keys |
|---|---|
| a slider, a range slider, a dial | the right and up arrows add one step to the target of the thumb, and the left and down arrows subtract one ({numref}`slider-and-dial`). On a slider and a range slider, Home moves the thumb to `from`, and End to `to`, or to the last step before `to` when there is a step |
| a number field, a text field | the keys of {numref}`number-field` and {numref}`text-field` |
| a select or a multi-select of kind `'menu'` | on the `menu`, the down and up arrows, Enter and Space open the list, with the chosen option active, or the first option when none is chosen. In the list, the down and up arrows make the next and the previous option active, Home and End the first and the last, Enter and Space choose the active option, Escape closes the list and gives the focus to the `menu`, and Tab closes the list. A select closes its list once an option is chosen, and a multi-select keeps it open |
| a select of kind `'buttons'` | the right and down arrows choose the next option and give it the focus, and the left and up arrows the previous one, the last option being followed by the first |
| a play | Space acts as a press of `button`. With `(buttons true)`, at step k, the right arrow acts as a press of `bar-(k+1)` while k is below N, and the left arrow as a press of `bar-k` while k is above 0, or of `bar-(k-1)` when pressed less than 300 milliseconds after step k started and k is above 1 |
| a stepper | the right arrow acts as a press of `next`, and the left arrow of `back` |
```

On a page that holds exactly one element of a play or a stepper, its keys act also with the focus
anywhere on the page, except while the focus is on an `input`, `textarea`, `select` or `button`
element, on editable text, on an element whose role is `slider`, `spinbutton` or `listbox`, or in
another control. So on a page with one play and no other control, the reader may step through the
play with the arrow keys while reading.

This rule exists to fix what the keyboard does to a view.

```{rule} view-keys
The `switch` of a view is a button. With the focus in a live view, Escape acts as a press of its
`switch`. No key drags a shape, clicks a shape or a term, pans a canvas or zooms it: the reader does
these only with the pointer.
```

:::{admonition} Code differs
:class: note
The runtime draws the older slider ({numref}`input-names`) as a native range input inside a label,
which a screen reader reads by the label and the browser moves with its own keys
(web/src/elements.ts:1236-1330). Bead mtp-9e62.
:::

## Reduced motion

This rule exists to fix what the runtime does when the reader asks the browser for reduced motion.

```{rule} reduced-motion
While the browser of the reader matches the CSS media query `(prefers-reduced-motion: reduce)`, the
runtime folds and unfolds a control at once ({numref}`control-folding`), and draws each change of
the look of a button, a box or a thumb of a control at once, with no CSS transition. It plays every
movement as it does otherwise.
```

So an `on-view` or an `on-ready` plays its movement over its duration whatever the setting of the
reader.
