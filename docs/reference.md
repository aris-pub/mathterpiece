# Reference

Every form, built-in function and constant in mtp. Each entry says exactly which parts are the name, the positional arguments and the items (see the syntax document, section 8), the types it takes and gives, and where it is undefined.

"Undefined" means: a compile error when the inputs are known when compiling, and `none` while drawing (see the type system document, section 5.c). Constraint names, types and the declaration rule are as in the other documents.

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

A parameter list is one typed parameter `(real t 0.5)` or a list of them `((real t 0.5) (color tint 'red'))`; each may have a default.

### Functions

| Form | Name | Positional | Items |
|---|---|---|---|
| `(func name params body)` | required | the parameter list; the body | none |
| `(fn params body)` | none | the parameter list; the body | none |

`func`'s parameters are always typed. `fn` may give a single parameter as a bare name, typed by its place. Results are never written.

### The scene and shapes

| Form | Name | Positional | Items |
|---|---|---|---|
| `(scene name)` | required | none | shape declarations, variable declarations, `(background color)` |
| `(group name)` | required | none | shape declarations, shape arguments |
| `(circle name)` | required | none | shape arguments, `(r real)` |
| `(rect name)` | required | none | shape arguments, `(width real)`, `(height real)`, `(rx real)`, `(ry real)` (rounded corners) |
| `(ellipse name)` | required | none | shape arguments, `(rx real)`, `(ry real)` |
| `(line name)` | required | none | shape arguments, `(from point)`, `(to point)` |
| `(triangle name)` | required | none | shape arguments, `(a point)`, `(b point)`, `(c point)` |
| `(text name value)` | required | the string | shape arguments, `(font font)`, `(halign …)`, `(valign …)`; fonts are only given as a font token, never as separate size or family arguments |
| `(dial name)`, any motif or variant | required | none | its parameters, and the arguments its base takes |

Shape arguments, taken by every shape: `(pos point)` or `(x real)` `(y real)`; `(fill color|none)`; `(stroke color|none)`; `(stroke-width (real (>= 0)))`; `(opacity unit)`, `(fill-opacity unit)`, `(stroke-opacity unit)`; `(transform transform)`. These mirror SVG on purpose: a color's alpha, `fill-opacity` and `stroke-opacity` multiply, and `opacity` fades the drawn shape as a whole, so a fill does not show through an overlapping stroke.

`halign` is one of `'start' 'middle' 'end'`; `valign` is one of `'top' 'middle' 'bottom'`.

### Tokens

| Form | Name | Positional | Items |
|---|---|---|---|
| `(color name value)` | required | a color | constraints |
| `(font name)` | required | none | `(family string)`, `(style …)`, `(weight (real (>= 1) (<= 1000)))`, `(size real)` |

Color and font variables are tokens: the page may restyle them through CSS custom properties (`--mtp-ink`), and controls cannot write them.

### Transitions and animations

| Form | Name | Positional | Items |
|---|---|---|---|
| `(transition name?)` | optional | none | `(from v)`, `(to v)`, `(duration real)`, `(ease …)`, `(path …)` |
| `(animation name)` | required | none | steps |

Steps: `(place transition)`, which moves a writable place along a transition; `(wait real)`; `(at-once step…)`; `(in-order step…)`. A transition with no `from` starts where the place is; with no `to`, ends there.

Eases: `'linear'`, `'ease-in'`, `'ease-out'`, `'ease-in-out'`, `(step n)` (n equal jumps), or a function `func[real real]` on 0..1. Paths: a straight line between the ends by default, or a function taking the two ends and the progress. A canvas's showing and hiding takes the path `fade`, which is only for that.

### Components

| Form | Name | Positional | Items |
|---|---|---|---|
| `(canvas name)` | required | none | bare names of shapes to show, `(when bool name…)`, `(transition …)` for showing and hiding, `(view-x real)` `(view-y real)` `(view-width real)` `(view-height real)` |
| `(readout name value)` | required | the string | `(font font)`, the only way to set its font |
| `(slider name)` | required | none | `(animation …)`, `(label string)`, `(step int)` (number of places, at least 2) |
| `(button name)` | required | none | `(animation …)`, `(label string)` |
| `(play name)` | required | none | `(animation …)`, `(label string)`, `(buttons bool)` |
| `(toggle name)` | required | none | `(target place)` or none (holds its own bool), `(label string)`, `(value bool)` |
| `(on-drag shape)` | none | the shape | `(target place)` (required), bool conditions, `(when bool)` |
| `(on-click shape)` | none | the shape | `(animation …)`, `(when bool)` |

## Special forms

| Form | Evaluates |
|---|---|
| `(if c a b)` | `c`, then only `a` or `b` |
| `(cond (c1 v1) (c2 v2) … (else v))` | the tests in order, then only the value of the first that holds |
| `(and a b …)` | left to right, stopping at the first false |
| `(or a b …)` | left to right, stopping at the first true |
| `(let ((n1 v1) (n2 v2) …) body)` | each value, in order (each may use the names before it), then the body |
| `(repeat n i decl…)` | when compiling: the declarations, `n` times, with `i` from 0 to n−1; `n` must be known when compiling |

## Operators

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `+` `-` `*` | numbers, any count (`-` with one argument negates); points and lists of numbers of equal known length, item by item | the broadest input type | never |
| `/` | two numbers; an int over an int gives a ratio | number | dividing by 0 |
| `^` | two numbers | number | 0 to a negative power |
| `mod` | two numbers | number | by 0 |
| `abs` | a number | number | never |
| `=` `!=` | any two of one type | bool | never (`(= none none)` is true) |
| `<` `<=` `>` `>=` | two reals | bool | never |
| `not` | a bool | bool | never |

## Functions

### Numbers

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `sqrt` | real | real | negative input |
| `round` `floor` `ceil` | real | int | never |
| `exp` | real | real | never |
| `log` | real, and optionally a base (e if left out) | real | input 0 or below; base 0 or below, or 1 |
| `min` `max` | reals, any count | real | never |
| `lerp` | `a`, `b`, `t` (reals or points) | the same type | never |
| `rand` | none, or `lo hi` | real, drawn once per page load | never |

### Angles

Two full families: the functions ending in `d` take or give degrees, the others radians. `polar` and `rotate` use degrees.

| Radians | Degrees | Takes | Gives | Undefined (degrees; in radians the same angles) |
|---|---|---|---|---|
| `sin` `cos` | `sind` `cosd` | an angle | real | never |
| `tan` | `tand` | an angle | real | at 90 + 180k |
| `sec` | `secd` | an angle | real | at 90 + 180k |
| `csc` `cot` | `cscd` `cotd` | an angle | real | at 180k |
| `asin` `acos` | `asind` `acosd` | real | an angle | outside −1..1 |
| `atan` `acot` | `atand` `acotd` | real | an angle | never |
| `asec` `acsc` | `asecd` `acscd` | real | an angle | strictly between −1 and 1 |

Conversions: `rad` (radians to degrees), `turn` (turns to degrees), `deg` (degrees, unchanged), `to-rad` (degrees to radians), `to-turn` (degrees to turns). None is ever undefined.

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
