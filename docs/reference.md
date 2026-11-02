# Reference

Every form, built-in function and constant in mtp. Each entry says exactly which parts are the name, the positional arguments and the items (see the syntax document, section 8), the types it takes and gives, and where it is undefined.

"Undefined" means: a compile error when the inputs are known when compiling, and `none` while drawing (see the type system document, section 5.c). Constraint names, types and the declaration rule are as in the other documents.

## Coordinates

- **y points up** and x to the right, as in mathematics.
- **Angles** are counterclockwise from the positive x axis. `(polar 1 90)` is straight up; `rotate` turns counterclockwise.
- **A canvas's view box** is given by its lower-left corner (`view-x`, `view-y`) and its size (`view-width`, `view-height`), in scene units. The default is −10 to 10 in both directions. The whole view box is shown, scaled to fit the element and centered in it. A canvas's `transform` applies about the center of its view box. The reader may pan and zoom what the view box shows (see "Panning and zooming"), which changes only what the canvas shows, never the view box's attributes.
- **Stroke widths and font sizes are in screen units** (CSS pixels): a line keeps the same thickness on screen, and text the same size, whatever the view box and however the figure is scaled.
- **Every shape has its own frame of reference.** It starts identical to the scene's; then the shape's `translate` and then its `transform` are applied (`translate` is the translation that comes first; `transform` is everything else, and may include further translations), and they apply to the shape and to everything below it in the scene tree. Both act about the origin of the container's frame, so `(rotate 30)` turns a shape around that origin, not around its own position; to turn a shape in place, put its offset inside the transform, after the rotation: `(transform (transform (rotate 30) (translate 6 -6)))`. A group's `translate` and `transform` are its own: they move its members, and are not spread over them.
- **A position is written before the transforms of the shape's containers are applied.** `(group g (translate [5 0]) (circle p (x 1)))` places `p` at x = 1, then the group's translation moves it: it is drawn at 6. The author never converts anything by hand: what is written is where the shape sits before its containers move it.
- **Reading an attribute converts it through every transform that applies to the shape read but not to the expression reading it.** Inside `g`, a sibling reads `p.x` as 1, so `(circle q (x p.x))` sits exactly on `p`; outside `g`, `p.x` reads 6, where `p` is drawn. The runtime stores the 1. A shape's own `translate` and `transform` count too: `(circle p (x 1) (translate [2 0]))` is drawn at 3, and a sibling reads `p.x` as 3. Inside a function, a read uses the frame of the expression that called it. A drag's write converts the other way: it writes the value that, after every transform, lands under the pointer. Writes from animations and toggles are in the target's own frame and are not converted.

## Declarations

### Values and variables

| Form | Name | Positional | Items |
|---|---|---|---|
| `(T name value)` for any type `T` | required | the value | constraints |

`T` is any type or type expression: `(real k 1)`, `(color ink 'navy')`, `(list[color] palette ['red' 'gold'])`, `(real|none crossing (secd theta))`, `((real (>= 0)) r 1)`. A plain `list` infers its item type from the value.

### Types

| Form | Name | Positional | Items |
|---|---|---|---|
| `(type name base)` | required | the base type | constraints |
| `(motif name params)` | required | the parameter list | member declarations, bound variable declarations |
| `(variant name params shape)` | required | the parameter list; one shape declaration | none |

A parameter list is one typed parameter `(real t 0.5)`, a list of them `((real t 0.5) (color tint 'red'))`, or `()` for none; each may have a default. `()` is also an empty list of `let` bindings, and is never a value.

### Functions

| Form | Name | Positional | Items |
|---|---|---|---|
| `(func name params body)` | required | the parameter list; the body | none |

`func`'s parameters are always typed. Results are never written. A function may call itself. `fn`, a function written in place, is a special form (below).

### The scene and shapes

| Form | Name | Positional | Items |
|---|---|---|---|
| `(scene name)` | required | none | shape declarations, variable declarations, `repeat`, `(background color)` |
| `(group name)` | required | none | shape declarations, shape arguments |
| `(circle name)` | required | none | shape arguments, `(r (real (>= 0)))` |
| `(rect name)` | required | none | shape arguments, `(width real)`, `(height real)`, `(rx real)`, `(ry real)` (rounded corners) |
| `(ellipse name)` | required | none | shape arguments, `(rx real)`, `(ry real)` |
| `(line name)` | required | none | shape arguments, `(from point)`, `(to point)` |
| `(triangle name)` | required | none | shape arguments, `(a point)`, `(b point)`, `(c point)` |
| `(text name value)` | required | the string | shape arguments, `(font font)`, `(halign …)`, `(valign …)`; its font is only given as a declared font variable, never as separate size or family arguments |
| `(dial name)`, any motif or variant | required | none | its parameters, and the arguments its base takes |

Shape arguments, taken by every shape except groups: `(x real)` `(y real)`, or `(pos point)`, which writes `x` and `y` together, as one point (`c.pos` is `[c.x c.y]`; `pos` is not kept apart from them). Taken by every shape, groups included: `(translate point)`, the translation part of its transform, and `(transform transform)`. Taken by every shape except groups: `(fill color|none)`; `(stroke color|none)`; `(stroke-width (real (>= 0)))`; `(opacity (real (>= 0) (<= 1)))`, `(fill-opacity (real (>= 0) (<= 1)))`, `(stroke-opacity (real (>= 0) (<= 1)))`. On a group, any of these, and `x`, `y` and `pos`, are read and written on each member (they spread). Given in a group's declaration, they are defaults for its members: a member that gives its own value keeps it, as a transition's own `ease` wins over the `default-ease` around it, and the nearest group's value wins over one further out. A text takes no `stroke` or `stroke-width` from a group, since a stroke would outline its letters; it keeps its own. A motif instance takes them too: its `x` and `y` move its frame, and so its members, before its `translate` and `transform`; its paint arguments are defaults for its members, as on a group, except `opacity`, which fades the instance as a whole and multiplies with its members' own. These mirror SVG on purpose: a color's alpha, `fill-opacity` and `stroke-opacity` multiply, and `opacity` fades the drawn shape as a whole, so a fill does not show through an overlapping stroke.

`halign` is one of `'start' 'middle' 'end'`; `valign` is one of `'top' 'middle' 'baseline' 'bottom'`, where `'baseline'` is the line the letters sit on and `'bottom'` is the bottom of the lowest letters.

Where each shape is placed by its position: a circle's and an ellipse's center, a rect's center, a text's anchor point (chosen by `halign` and `valign`). A line's position is its midpoint and a triangle's its centroid. They are computed from the ends or corners, so a line or triangle is declared by its ends or corners and never given `x`, `y` or `pos`; a writer that writes its position moves every end or corner together, and may only do so when they are all free.

### Tokens

| Form | Name | Positional | Items |
|---|---|---|---|
| `(color name value)` | required | a color | constraints |
| `(font name)` | required | none | `(family string)`, `(style …)`, `(weight (real (>= 1) (<= 1000)))`, `(size real)` |

Color and font variables are tokens: the page may restyle them through CSS custom properties (`--mtp-ink`), and no writer (control or listener) can write them.

### Transitions and animations

| Form | Name | Positional | Items |
|---|---|---|---|
| `(transition name?)` | optional: a transition written inline as an item has none | none | `(from v)`, `(to v)`, `(duration real)`, `(ease …)`, `(path …)` |
| `(animation name)` | required, except when written inline as an item of a control or listener | none | steps |

Steps: `(target transition)`, which moves `target`, a variable or an attribute a writer may change, along a transition; `(wait real)`; `(at-once step…)`; `(in-order step…)`; or the name of an animation, which runs its steps there. An animation, `at-once` and `in-order` also take the items `(default-duration real)` and `(default-ease …)`, so that the transitions inside them need not each give their own: a transition's own `duration` or `ease` wins, and otherwise the nearest enclosing default applies. A transition with no `from` starts from the value of what it moves; with no `to`, ends there.

Eases: `'linear'`, `'ease-in'`, `'ease-out'`, `'ease-in-out'`, `(step n)` (n equal jumps, each at the start of its interval: a 1 s `(step 4)` move from 0 to 4 shows 1 at once and reaches 4 at 0.75 s), or a function `func[real real]` on 0..1. A bool, a string or a choice (section 5.d of the type system) cannot change smoothly, so its ease must be piecewise constant and take only the values 0 and 1: where it is 0 what moves holds its start value, where it is 1 its end value. Such eases come only from the standard library, which for now has one: `(step-ease p)`, with `p` from 0 to 1 known when compiling, which is 0 before progress `p` and 1 from `p` on (`(step-ease 0)` changes at the start, `(step-ease 1)` at the end). An author cannot write one, since the compiler could not check it. By default a bool, a string or a choice changes at the start of its move and holds its new value for the rest of the duration, so a move that is cancelled never leaves it in between. An enclosing `default-ease` that is not such an ease does not apply to it. Paths: a straight line between the ends by default, or a function taking the two ends and the progress. A canvas's showing and hiding takes the path `fade`, which is only for that.

### Components

| Form | Name | Positional | Items |
|---|---|---|---|
| `(canvas name)` | required | none | bare names of shapes to show (the scene's name shows the whole scene), `(when bool name…)`, drawn in the order written, each on top of those before it; `(transition …)` for showing and hiding, `(view-x real)` `(view-y real)` `(view-width real)` `(view-height real)`, `(transform transform)`, `(pan bool)`, `(zoom bool)` |
| `(readout name value)` | required | the string (a number is shown by interpolating it: `$'{k:.2f}'`) | `(font font)`, a declared font variable, the only way to set its font |
| `(slider name)` | required | none | `(animation …)`, `(label string)`, `(step int)` (the number of positions its knob stops at, at least 2), conditions |
| `(button name)` | required | none | `(animation …)`, `(label string)`, conditions |
| `(play name)` | required | none | `(animation …)`, `(label string)`, `(buttons bool)`, conditions |
| `(toggle name)` | required | none | `(target t)` or none (holds its own bool), `(label string)`, `(value bool)`, conditions |
| `(on-drag shape)` | none | the shape | `(target t)` (required), conditions, `(when bool)` |
| `(on-click shape)` | none | the shape | `(animation …)`, conditions, `(when bool)` |

## Defaults

What an attribute is when the author leaves it out:

| What | Default |
|---|---|
| `x`, `y`, `translate` | 0, so `[0 0]` |
| `transform` | the identity |
| `fill` | black, `'#000000'` |
| `stroke` | `none` |
| `stroke-width` | 1 (a screen pixel) |
| `opacity`, `fill-opacity`, `stroke-opacity` | 1 |
| circle `r` | 1 |
| rect `width`, `height` | 1; corners `rx`, `ry` 0 |
| ellipse `rx`, `ry` | 1 |
| line | from `[0 0]` to `[1 0]` |
| triangle | corners `[0 0]`, `[1 0]`, `[0 1]` |
| text | `halign` `'start'`, `valign` `'baseline'` |
| a font's parts | family: the page's font; style `'normal'`; weight 400; size 16 (screen pixels) |
| scene `background` | `none` |
| canvas view box | −10 to 10 in both directions |
| transition `ease` | `'linear'` |
| transition `duration` | none: a transition with no duration takes the `default-duration` of the nearest animation, `at-once` or `in-order` around it, and is a compile error if there is none |
| control `label` | the control's name |
| toggle `value` | `false` |
| slider `step` | none: the slider moves continuously |
| play `buttons` | `false` |
| canvas `pan`, `zoom` | `true`: the reader may pan and zoom it |

Every type has a value used when no value or default is given: in a variable declared without one, `(real k)`, and in a parameter without a default that an instance or call leaves out.

| Type | Its value |
|---|---|
| `int`, `ratio`, `real`, `complex` | 0 |
| `bool` | `false` |
| `string` | `''` |
| a choice type | its first choice |
| `color` | black |
| `font` | the font defaults above |
| `point` | `[0 0]` |
| `list[T]` | `[]`; with a `(length n)` constraint, n items each with T's value |
| `transform` | the identity |
| `T\|none` | `none` |
| a narrowed number whose 0 breaks its constraints | its lower bound if that bound is allowed (`(>= 1)` gives 1); otherwise there is none, and leaving a value out is a compile error |
| shapes, functions, transitions, animations | none: leaving one out is a compile error |

## Writes and conditions

Every control and listener emits writes to its target (or, through its animation, to the variables and attributes the animation moves).

- **Conditions** are items of a control or listener: any bool expression, recognized as an item because its head is a comparison or another function giving a bool, such as `(>= theta 0)` or `(<= u.x 5)`. They belong to that writer only. Before a write is emitted it is brought into every condition: a condition that compares the variable or attribute written with a value not depending on it, `(>= theta 0)`, `(< theta (* 2 k))`, clamps the write to that limit. Any other condition is a compile error: the compiler must see a direct limit on what is written, and never searches for a value. `(when bool)` is different: it decides whether the writer is active at all.
- **Constraints on the target** (on its type) then apply to every write it receives, from any writer: a range clamps, an int rounds, a choice holds its last valid value. A write that changes nothing is skipped.

### Dragging

- **The press** hits the topmost shape under the pointer, then goes up the scene tree to the nearest shape with an `on-drag` whose `when` holds. That shape is dragged.
- **A target that is the shape's own `x`, `y` or `pos`** follows the pointer's motion, keeping the offset the pointer had from the shape at the press: the shape does not jump to center itself under the pointer. A target of `x` alone or `y` alone follows the pointer along that axis only.
- **A target that is a number the shape's position depends on** (`theta` in `(polar 1 theta)`) takes the value that brings the shape closest to where the pointer has moved it. The search starts from the current value and stays near it, so the shape never jumps to another position equally close (the far side of a circle). When no value reaches the pointer exactly, the closest is taken.
- **A group** moves every member by the pointer's motion.
- **A target** is the shape's own position or a number its position depends on.

### Panning and zooming

- **Pan:** dragging where no draggable shape is moves what the canvas shows with the pointer.
- **Zoom:** a pinch, on a trackpad or with two fingers, or the wheel with ctrl or cmd held, zooms about the pointer. A plain wheel scrolls the page.
- **A double click** goes back to the view box the author gave.
- **Neither writes anything:** they are the canvas's own state, like its fades, so stroke widths and font sizes stay the same on screen. `(pan false)` or `(zoom false)` turns either off.

### Controls

- **Slider:** its knob runs from 0 to 1, its `position`. Moving it does not play the animation over time; it sets how far along the animation is, each part taking a share of the track equal to its duration. With `(step n)` the knob stops at n evenly spaced positions. A move with no `from` starts from where its target was when the reader began moving the knob.
- **A slider follows its target:** when another writer changes the variable or attribute its animation moves, the knob goes to the position whose value is closest to its new value. This holds when the animation moves exactly one variable or attribute; otherwise the knob stays put. Its starting position is found the same way.
- **Button:** a press plays its animation from the start, over time; a press while it runs starts it again.
- **Play:** a press plays the animation, and its label reads "pause" while it runs. A press while it runs pauses it, and the next resumes it; after the end, a press plays it again from the start. With `(buttons true)` it also shows one button per top-level step, lit while that step holds: clicking one, whatever the state, first cancels every writer moving any variable or attribute the play moves (the play itself included), then runs that step alone, over time, from wherever things are. The play then stops at the step's end; its next press plays from the start.
- **Toggle:** a checkbox writing its target bool, or holding its own value when it has no target; `(value bool)` sets that own value's start, and is an error with a target. On a group's attribute it writes every member, reads true only when every member's is true, and shows a mixed state when the members differ; a click on a mixed toggle sets every member to true. A toggle is read through its value, `show.value`, like any other attribute.
- **On-click:** a click on the shape plays its animation, as a button does.
- **Two writers on one target:** a writer that starts moving a variable or an attribute cancels any other writer moving it. The newest wins, whatever its kind.

## Rounding

One rule, the same in the compiler and the runtime, wherever a number is rounded: `round`, a write into an int, and a format spec such as `{x:.2f}`. **Halves round away from zero:** 2.5 gives 3, −2.5 gives −3, and 0.125 to two decimal places gives 0.13. Rounding works on the number's shortest exact decimal form, not its binary value, so 2.675 to two decimal places gives 2.68.

## Special forms

| Form | Evaluates |
|---|---|
| `(if c a b)` | `c`, then only `a` or `b` |
| `(cond (c1 v1) (c2 v2) … (else v))` | the tests in order, then only the value of the first that holds |
| `(and a b …)` | left to right, stopping at the first false |
| `(or a b …)` | left to right, stopping at the first true |
| `(let ((n1 v1) (n2 v2) …) body)` | each value, in order (each may use the names before it), then the body, a single expression |
| `(fn params body)` | nothing until called; binds its parameters in its body. A single parameter may be a bare name, typed by where the function is used; several must all be typed |
| `(. X Y)` | `X`, and `Y` unless it is an attribute name |
| `(name s)` | `s`, a string, which becomes a name |
| `(as T literal)` | nothing: the literal, with the type `T`; anything but a literal is a compile error |
| `(repeat n i decl…)` | when compiling: the declarations, `n` times, with `i` from 0 to n−1; `n` must be known when compiling |

## Operators

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `+` `-` `*` | numbers, any count (`-` with one argument negates); points and lists of numbers of equal known length, item by item | the broadest input type | a result too large for a real |
| `/` | two numbers | an int over an int gives a ratio; otherwise the broadest input type | dividing by 0 |
| `^` | two numbers | an int to a non-negative int power gives an int, to a negative int power a ratio; a complex input gives a complex; otherwise a real | 0 to a negative power; a negative base to a power that is not an int; a result too large for a real |
| `mod` | two numbers | number, with the sign of the divisor: `(mod -1 360)` is 359 | by 0 |
| `abs` | a number | the same type; a complex gives a real | never |
| `=` `!=` | any two of one type | bool | never (`(= none none)` is true) |
| `<` `<=` `>` `>=` | two reals | bool | never |
| `not` | a bool | bool | never |

## Functions

### Numbers

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `sqrt` | real | real | negative input |
| `round` | real, and optionally a number of decimal places `n` (an int; negative rounds to tens, hundreds, …) | int without `n`, real with it | never |
| `floor` `ceil` | real | int | never |
| `exp` | real | real | a result too large for a real |
| `log` | real, and optionally a base (e if left out) | real | input 0 or below; base 0 or below, or 1 |
| `min` `max` | reals, any count | real | never |
| `lerp` | `a`, `b`, `t` (reals or points) | the same type | never |
| `rand` | none (0 to 1), or `lo hi` | real, drawn once per page load and never again; each copy of a `rand` (in each `repeat` copy, each motif instance) draws its own; a `rand` inside a function is a compile error for now | never |

### Angles

Two full families: the trigonometric functions whose names end in `d` (`sind`, `asind`, …) take or give degrees; the others take or give radians. `polar`, `to-polar` and `rotate` use degrees.

| Radians | Degrees | Takes | Gives | Undefined (in degrees; the radian versions compute numerically and give `none` only where the result is not a number, since π/2 cannot be hit exactly) |
|---|---|---|---|---|
| `sin` `cos` | `sind` `cosd` | an angle | real | never |
| `tan` | `tand` | an angle | real | at 90 + 180k |
| `sec` | `secd` | an angle | real | at 90 + 180k |
| `csc` `cot` | `cscd` `cotd` | an angle | real | at 180k |
| `asin` `acos` | `asind` `acosd` | real | an angle | outside −1..1 |
| `atan` `acot` | `atand` `acotd` | real | an angle | never |
| `asec` `acsc` | `asecd` `acscd` | real | an angle | strictly between −1 and 1 |

Conversions: `rad` (radians to degrees), `turn` (turns to degrees), `deg` (degrees, unchanged), `to-rad` (degrees to radians), `to-turn` (degrees to turns). No conversion is ever undefined.

### Points

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `polar` | radius, angle | point | never |
| `to-polar` | point | `[radius angle]` | the angle at the origin |
| `dist` | two points | real | never |

### Transforms

| Function | Takes | Gives |
|---|---|---|
| `rotate` | degrees | transform |
| `scale` | one factor, or `sx sy` | transform |
| `translate` | `dx dy` | transform |
| `transform` | transforms, any count | their composition |

### Colors

| Function | Takes | Gives |
|---|---|---|
| `mix` | two colors, `t` in 0..1 | color |
| `lighten` `darken` | a color, `t` in 0..1 | color |

A color literal is any CSS color: a name (`'crimson'`), `'#rrggbb'`, `'#rrggbbaa'`.

### Collections

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `map` | a collection, `func[T U]` | `list[U]` | never |
| `where` | a collection, `func[T bool]` | the members for which it holds | never |
| `sort` | a collection, `func[T real]` | the members, by key, smallest first | never |
| `reverse` | a list | the list reversed | never |
| `reduce` | a collection, a start, `func[A T A]` | `A` | never |
| `sum` | a list of numbers | number | never |
| `count` | a collection, optionally `func[T bool]` | int | never |
| `any` `all` | a list of bools, or a collection and `func[T bool]` | bool | never |
| `somes` | `list[T\|none]` | `list[T]` | never |
| `xs[i]`, `g[k]` | a position or key | an item | a position out of range, a missing key |

### none

| Function | Takes | Gives |
|---|---|---|
| `or?` | `x`, `d` | `x`, or `d` when `x` is none |
| `none?` `some?` | any value | bool |

## Constants

| Name | Value |
|---|---|
| `pi`, `π` | 3.14159… |
| `tau`, `τ` | 6.28318… |

## Interpolated strings

`$'…{expr}…'` shows each `{expr}`, optionally followed by a format after a colon, using Python's format mini-language: `{x:.2f}` (2 decimals), `{x:+.3f}`, `{p:.0%}` (percent), `{n:d}`, `{x:e}`, `{x:g}`, with fill, alignment and width (`{x:>8.2f}`).
