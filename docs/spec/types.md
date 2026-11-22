(types)=
# Types

This page defines the types of mtp, how a type is written, which {term}`values <value>` each type
holds, when a value of one type is accepted where another type is expected, and the type of each
expression. The prove step works out every type ({numref}`compile-steps`), and the {term}`runtime`
never checks one ({numref}`runtime-no-type-work-while-drawing`).

## What a type is

```{rule} what-a-type-is
A type is a set of {term}`values <value>`. A value may belong to many types. Every container,
parameter and expression has one type, known when compiling: for a container, its declared type,
conditions included. Every value that it holds or evaluates to belongs to that type.
```

So `bool` is the set `{true, false}`, `circle` is the set of all circles, and `(real (>= 0))` is
the set of the reals that are not below 0. The types are combined as sets:

| Type | As a set |
|---|---|
| `T1\|T2` | the union of T1 and T2 |
| `T1&T2` | the intersection of T1 and T2 |
| `(T C…)` | the subset of T whose values meet every condition C ({numref}`constraints`). `((T C…) D…)` is `(T C… D…)`, and the conditions of a union with `none` apply to its other types: `(real\|none (>= 0))` is `(real (>= 0))\|none` |
| `(interface N (T A)…)` | the set of the values that have each attribute A, of type T ({numref}`interfaces`) |
| `list[T]` | the set of the lists whose items all belong to T |
| `func[P1 … Pn R]` | the set of the functions of n parameters, of types P1 to Pn, whose result belongs to R |
| `(mod int lo hi)`, `(mod real lo hi)` | the set of the numbers from lo up to hi, hi left out, with arithmetic that wraps ({numref}`modular-types`) |

A type that is a subset of another is a {term}`subtype` of it ({numref}`fits`).

```{rule} membership
`(is X T)` evaluates to `true` when the value of X is in the type T, and to `false` otherwise.
Where the type of X lies wholly inside T, or wholly outside it, the result is known when compiling.
Otherwise the runtime works it out while drawing. In the branch of an `if` that runs when `(is X T)` is true, X has the type T as
well as its own, and in the other branch X is known not to be in T.
```

So in `(func size ((point|circle p)) (if (is p circle) p.r 0))`, `p.r` is read only when `p` is a
circle, and `(is 3 real)` is `true` when compiling.

## The types

```{rule} the-types
These are the built-in types of mtp, and the types that a source declares. Every other type is built
from these, as {numref}`what-a-type-is` lists:

| Type | Its values | Notes |
|---|---|---|
| `int`, `ratio`, `real`, `complex` | the numbers of each kind | {numref}`number-types` |
| `unit` | the reals from 0 to 1 | the same type as `(real (>= 0) (<= 1))` |
| `angle` | the angles in degrees, from 0 up to 360 | the same type as `(mod real 0 360)` ({numref}`modular-types`). The trigonometric functions in degrees take an angle, and their inverses evaluate to one |
| `bool` | `true` and `false` | |
| `string` | the {term}`strings <string>` | the strings of formulas among them |
| `color` | the colors | {numref}`color-literals` |
| `point` | the points | two reals, `x` and `y` ({numref}`values`) |
| `none` | `none` alone | never the declared type of a declaration or of a parameter, only of an expression and of a `let` name bound to one |
| `func` | every function | |
| `ease` | the eases of a movement | the same type as `func[unit real]` ({doc}`time`) |
| `curve` | the curves of the plane | the same type as `func[real point]` |
| `colormap` | the functions from a real to a color | the same type as `func[real color]` |
| `rand-seed` | the ints | a free variable of this type is a {term}`seed` ({numref}`seed-variable`) |
| `shape` | every shape | the union of every shape type, motif type and variant type |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `bezier`, `arc`, `ring`, `text`, `group` | the shapes of that kind | a row and a column are of type `group` |
| `M`, for a motif `M` | every `M` | {numref}`motif-and-variant-types` |
| `V`, for a variant `V` | every `V` | {numref}`motif-and-variant-types` |
| `scene` | the scene | |
| `formula`, `term` | the formulas, and the terms | |
| `record`, `font` | the records, and the fonts | a font is a record with a family, a style, a weight and a size |
| `movement` | every movement | the moves, the scores and every `A` |
| `A`, for an animation `A` | every `A` | {doc}`time` |
| `page-object`, `component`, `view`, `control`, `listener`, `writer` | the page objects, the components, the views, the controls, the listeners, and the writers | a page object is a view, a control or a listener, a component is a view or a control, and a writer is a control or a listener |
| `canvas`, `readout`, `display`, `slider`, `button`, `play`, `stepper`, `toggle`, and each listener head | the components of that kind | |
| `palette` | the records whose attributes are all colors, whatever their names and number | a record made by `(palette …)` is one ({numref}`sugar-rewrites`). An attribute M of a palette may be read by its label, and has the type `color|none`: it is `none` when the palette has no attribute M |
| `positioned`, `instant`, and each declared interface | the values that have the attributes that it lists | an {term}`interface` ({numref}`interfaces`) |

```

```{diagram} builtin-types
:file: diagrams/builtin-types.svg
:max-width: 48rem

The built-in types as sets, each box inside the boxes of the types that hold it. `unit` overlaps `int`
and `ratio`, and `writer` overlaps `component`. `angle` is a modular type, which is a subtype only of itself, so it
is not inside `real`. `palette` is drawn inside `record`, and the interface `instant` inside `movement`. `positioned` is not
drawn, since it holds values from several boxes: the points and most shapes.
```

:::{admonition} Code differs
:class: note
- `unit` is not a built-in type: the file types of the standard library declares it, and a source
  imports it with `(import types unit)`. Bead mtp-vc5g makes it a built-in type and removes that
  file.
- `ease` is not a type, and the file of eases of the standard library is named ease.mtp. Bead
  mtp-6kta makes `ease` a built-in type and renames the file eases.mtp.
- The compiler has the type `transform`, which the spec does not have: a shape's frame is a set of
  its attributes ({doc}`data-model`). Bead mtp-1vyc.
- `record`, `formula`, `term`, `component`, `view`, `control`, `listener`, `func` and the
  component types are not types that a source can write: `(func f ((canvas c)) 1)` is the error
  "unknown type 'canvas'". `shape` is an interface, the type of a parameter only. `movement` and the
  animation types are named `transition` and `animation`. Bead mtp-rk1i.
- The shape `bezier` is named `curve`, and `curve` is not a type. Bead mtp-qnws renames the shape
  and makes `curve` a built-in type.
:::

Which of these are primitives and which are objects is defined in {doc}`data-model`. A free
variable of type `rand-seed` is a {term}`seed` ({numref}`seed-variable`).

:::{admonition} Code differs
:class: note
The compiler gives `rand-seed` the constraint `(>= 0)` (`types.py:143`, `RAND_SEED`), so an
{term}`int` below 0 does not belong to it. Bead mtp-ydd4.7.30.
:::

```{rule} type-notation
Types are not values: no container holds a type, and no expression that evaluates to a value may
stand for one. These expressions evaluate to types:

- the name of a built-in type ({numref}`the-types`), or of a type that `type`, `interface`, `motif`,
  `variant` or `animation` declares
- `(type-apply …)`, `(type-union …)` and `(type-intersect …)` ({numref}`type-forms`)
- `(mod T lo hi)` ({numref}`modular-types`) and `(T C…)` ({numref}`constraints`)

These places expect a type, and only an expression that evaluates to a type may be written there:

- the head of a declaration of a variable or of an object, such as `real` in `(real a 1)` or `circle`
  in `(circle c …)`, and the `TYPE` of `(var NAME TYPE DEFAULT)`
- the type of a parameter, `(T N DEFAULT?)`, and of an interface item, `(T A C…)`
- the `T` of `(type N T C…)`, the result type `R` of `(func[R] …)`, and the `T` of `(is X T)` and of
  `(as T X)`
- every item of `(type-apply …)`, `(type-union …)` and `(type-intersect …)`, the `T` of `(mod T lo
  hi)`, and the `T` of `(T C…)`

An expression that evaluates to a type, written anywhere else, is a {term}`compile error`, and so is
an expression that evaluates to a value, written where a type is expected.
```

```{rule} type-forms
`(type-union T1 T2 …)` is the union of the types T1, T2 and so on, `(type-intersect T1 T2 …)` is
their intersection, and `(type-apply T X…)` is the type T with the types X… in its brackets: `(type-apply
list int)` is `list[int]`. In `(type-apply T X…)`, `T` is `list` or `func`. With `list`,
`X…` is exactly one type, the type of the items. With `func`, `X…` is one type or
more: the last is the result type, and the others are the types of the parameters, in order. `list`
with no item type may be written only as the head of a variable whose value is given, and the type
of the variable is then the type of its value. A source writes them as `T1|T2…`, `T1&T2…` and `T[X…]`
({numref}`sugar-rewrites`).
```

So `real[int]` is a compile error, `real|real` is `real`, and `point|circle` is the set of the
points and the circles.

## Subtypes

```{rule} fits
A type A is a {term}`subtype` of a type B, and B is a {term}`supertype` of A, exactly when A is a
subset of B. A value of type A is accepted where a value of type B is expected exactly when A is a
subtype of B.
```

So `real` is a subtype of `real|none`, a list of ints of a list of reals, and `func[real real]` of
`func[unit real]`, since a function on every real is also a function on the reals from 0 to 1. For
refined types, the conditions are compared as sets: `(real (>= 0))` is a subtype of `(real (>= -1))`, and
`(int (> 0))` is a subtype of `(int (>= 1))`, since both are the ints from 1 up. A modular type such as
`(mod real 0 360)` is not a subset of `real`, so it is a subtype only of itself. A value whose type is not a
subtype of the expected type may still be accepted when the prover proves that it meets the conditions ({numref}`constraint-proof`).

## Conditions

```{rule} constraints
A condition is a clause that limits the values of the type in the form around it: `(T C…)` holds the
values of T that meet every condition C. A condition has no meaning outside that form. A condition is one of these forms, each on the
types of its row only, and its values are known when compiling:

| Condition | On | The values that meet it | Written with |
|---|---|---|---|
| `(>= c)`, `(> c)`, `(<= c)`, `(< c)` | `int`, `ratio`, `real` | the numbers at least c, above c, at most c, below c | one number |
| `(length n)` | `list[T]`, `string` | the lists or the strings of n items | one int, 0 or more |
| `(one-of v1 … vk)` | the numbers, `bool`, `string`, `color`, `point`, `list[T]` | the values v1 to vk | one value or more |

Any other form in the place of a condition, and a condition on a type outside its row, is a compile
error. A type of objects may not have a condition: an intersection with an interface limits it instead.
```

`(const)` is not a condition: a variable or an attribute is free, bound or const
({numref}`variables`).

:::{admonition} Code differs
:class: note
The compiler reads `(const)` and `(wrap lo hi)` as constraints, takes `(one-of …)` only on strings,
and `(length n)` only on lists. Bead mtp-rk1i.
:::

## Modular types

```{rule} modular-types
`(mod T lo hi)`, with `T` either `int` or `real` and lo below hi, is the set of the numbers from lo
up to hi, hi left out, with no order. A number v that a container, a parameter or a function result
of the type receives is never refused: it is replaced by lo + ((v - lo) `mod` (hi - lo)). Adding a
number to a value of the type, or subtracting one from it, results in a value of the type. A value of
the type may not be compared with `<`, `>`, `<=` or `>=`. `(unwrap X)`, with X of the type, evaluates
to the number of X as an ordinary T.
```

So `((mod real 0 360) theta 400)` holds 40, `(+ theta 330)` is 10, and `(< theta 90)` is a compile
error. With `(type hour (mod int 0 12))` and `(func[hour] later ((hour h) (int n)) (+ h n))`,
`(later 9 5)` is 2, and `(real a (unwrap theta))` holds `theta` as an ordinary real.

:::{admonition} Code differs
:class: note
The compiler has no modular types. It has the constraint `(wrap lo hi)` on `int`, `ratio` and
`real`, whose arithmetic gives an ordinary number, so `(+ theta 30)` may be 380. Bead mtp-rk1i.
:::

## Default values

```{rule} type-values
A variable declared with no value, and a parameter with no default that is left out, hold the
default value of their type, given by the first row of this table that matches the type:

| Type | Its default value |
|---|---|
| a {term}`choice type` | its first choice that meets its other conditions |
| `int`, `ratio`, `real`, `complex` | 0 |
| a modular type | 0 brought into the interval ({numref}`modular-types`) |
| a refined number type whose conditions 0 breaks | c, when the type holds `(>= c)`. Otherwise c, when the type holds `(<= c)`. Otherwise none |
| `bool` | `false` |
| `string` | `''` |
| `color` | black, `#'#000000'` |
| `font` | the font of the defaults of a font ({doc}`world-model`) |
| `point` | `[0 0]` |
| `list[T]` | `{}`, and with `(length n)`, n items, each the value of T |
| a union with `none` | `none` |
| every other type | none: the variable or the parameter must be given a value |

Leaving out the value of a type that has no default value is a compile error.
```

So `(real k (>= 1))` holds 1, `(real k (<= -1))` holds -1, and `(real k (> 1))` is a compile error,
since its type holds neither a `(>= c)` nor a `(<= c)`, so it has no default value. A parameter whose type is a shape type or an interface has no default
value, so it must be given wherever it has no default of its own. No variable and no parameter is
ever left without a value.

## Conversions

```{rule} conversions
No value is converted from one type to another unless a form asks for it, such as `round`,
`color-of` or `unwrap`.
```

So `(string s 'red')` followed by `(circle d (fill s))` is a compile error, while
`(circle d (fill (color-of s)))` is allowed. An int is accepted where a real is expected because
`int` is a subtype of `real` ({numref}`fits`), not because it is converted.

## Known lengths

```{rule} known-lengths
The length of a list is {term}`known <known length>` when its type holds `(length n)`. These lists
have that condition in their types, with these lengths:

- `(list-of X…)` with n items: n
- a list known when compiling: its length
- a variable, an attribute, a parameter or a declared result whose declared type holds
  `(length n)`: n
- a bound container whose expression has a known length: that length
- `(if C A B)` whose branches have the same known length: that length
- a call of a function declared with `func` whose {term}`body` has a known length: that length
- a spread `g.A` of a group, and `g.members`: the number of members of the group
- a call of a {term}`built-in` function: the length that {doc}`stdlib` states

The items of a list have a known item length m when every item is a list of known length m. Such a
list has `(length m)` in its item type.
```

So the length of `(list xs {side 0 1})` is known, 3, even when `side` is known only while
drawing. A free list variable has a known length
only when it is declared with `(length n)`, and its items never have a known item length, since a
writer may write lists of another length into them.

## none

```{rule} none-only-where-allowed
A type includes `none` when it is `none` or a union with `none`. A value of such a type may be written
where the expected type does not include `none` only in these two places:

- as an argument of a call: the call then evaluates to `none` whenever that argument is `none`, and
  the type of the call includes `none`
- as an attribute of a shape declared `T|none`: the shape is then `none` whenever that attribute is
  `none`, and is not drawn ({numref}`none-propagates`)

A few built-in functions treat `none` in their own way ({numref}`none-never-a-condition`,
{numref}`none-propagates`).
```

In the first example, `s` is `none`, so the call `(* 2 s)` is `none` too, and its type is
`real|none`. `d` may hold it, since its type includes `none`, but `e` may not:

```mtp
(real theta 90)
(real|none s (secd theta))
(real|none d (* 2 s))
(real e (* 2 s))          ; compile error: the type of e does not include none
```

In the second example, `r` is `none`, so the circle `c`, declared `circle|none`, is `none` and is
not drawn. The circle `k` is not declared with `none`, so its `r` may not be `none`:

```mtp
(real|none r none)
(scene s
  (circle|none c (pos [0 0]) (r r))
  (circle k (pos [0 0]) (r r)))   ; compile error: k is not declared circle|none
```

In the third example, the line tangent to the unit circle at the angle `theta` meets the x-axis at
x = sec θ. At 90° the tangent line is parallel to the x-axis and never meets it, so `(secd theta)` is
`none`. By the first case, the call `(point-of (secd theta) 0)`, written `[(secd theta) 0]`, is
`none` too. By the second case, the segment `tangent` and the point `q`, declared `line|none` and
`circle|none`, are then `none`, and are not drawn. `theta` is an int, so the slider stops at every
degree, and the two are gone at 90 only:

```{mtp-example}
(int theta 60 (>= 20) (<= 160))
(scene s
  (line axis (from [-4 0]) (to [4 0]) (stroke #'gray'))
  (circle rim (pos [0 0]) (r 1) (fill none) (stroke #'gray'))
  (line radius (from [0 0]) (to (polar 1 theta)) (stroke #'gray'))
  (line|none tangent (from (polar 1 theta)) (to [(secd theta) 0]) (stroke #'crimson') (stroke-width 3))
  (circle|none q (pos [(secd theta) 0]) (r 0.08) (fill #'crimson')))
(canvas v (x -4) (y -1.5) (width 8) (height 3) s)
(slider turn (move theta (from 20) (to 160)) (label 'θ'))
(readout r f'θ = {theta}°')
```

## Choice types

```{rule} choice-types
A {term}`choice type` is a refined type whose conditions include a `(one-of v1 …)`. Its values are
the choices v1 … that meet its other conditions.
```

So with `(type side string (one-of 'left' 'right'))`, a `side` is a string, and a string is a
`side` only when the prover proves that it is among the choices ({numref}`constraint-proof`):
`(side s 'left')` is allowed, `(side s 'up')` is a compile error, and so is `(side s q)` for a free
string variable `q`, since a writer may write any string into `q`. A write of a string that is not
among the choices into a `side` has no effect ({numref}`writes-into-constraints`). The alignments
of a text, the caps and joins of a stroke, the heads of a line and the style of a font are choice
types ({doc}`world-model`).

:::{admonition} Code differs
:class: note
The compiler checks the choices only of a value known when compiling (`compiler.py:5823`,
`checked`), so `(string q 'up')` followed by `(side s q)` compiles. Bead mtp-ydd4.7.42.
:::

## Interfaces

```{rule} interfaces
An interface `(interface N (T1 A1 C1…) …)` is the set of the values that have each attribute Ai, of
a subtype of `(Ti Ci…)`. A value whose type is an interface may be read only through the attributes
Ai. These interfaces are built in:

| Interface | Definition |
|---|---|
| `positioned` | `(interface positioned (real x) (real y))` |
| `instant` | `(interface instant (real duration (one-of 0)))` |
```

:::{admonition} Code differs
:class: note
The compiler has no interface `palette`: `(func f ((palette q)) 1)` is the error "unknown type
'palette'" (`types.py:150`, `PALETTE`, is a type that a palette has as its own). Bead mtp-rdk2.
:::

So `(func label-at ((positioned o) (string s)) …)` may be given points, which are primitives, and
shapes, which are objects. `(func area ((shape o)) (* pi o.r o.r))` is a compile error, since not
every shape has an `r`. A record whose `r` is a plain `real` is not a subtype of
`(interface round (real r (>= 0)))`, since `real` is not a subtype of `(real (>= 0))`.

:::{admonition} Code differs
:class: note
The compiler joins a type only with `none`: `(func f ((point|circle p)) 1)` is the error "a type can
be broadened only by none for now". An interface is the type of a parameter only, and a variable
declared with one is a compile error. Bead mtp-mo3r.
:::

```{mtp-example}
; the parameter colors of the motif disc takes either namespace, since both are subtypes of inky
(interface inky (color ink) (color paper))
(namespace day (color ink #'#1f2a44') (color paper #'#f6f1e7'))
(namespace night (color ink #'#e8e4d8') (color paper #'#14161c'))
(bool dark false)
(motif disc ((inky colors)) (circle face (r 1) (fill colors.paper) (stroke colors.ink) (stroke-width 0.2)))
(scene s (disc d (colors (if dark night day))))
(canvas v (x -2) (y -2) (width 4) (height 4) s)
(toggle mode dark (label 'dark'))
```

## Common type

```{rule} common-type
The common type of two types A and B is the smallest type that holds both, found this way:

- When A is a subtype of B, it is B, and when B is a subtype of A, it is A.
- When one is `none`, it is the union of the other and `none`.
- When one includes `none`, it is the union of `none` and the common type of the two without `none`.
- For two number types, it is the later of the two, without conditions, in the order `int`, `ratio`,
  `real`, `complex`.
- For two list types, it is the list type of the common type of their item types.
- Otherwise there is none, and the source is a compile error.

The type of the branches of an `if` and of the items of a `(list-of …)` is their common type, except
that the type of the branches of an `if` is the expected type when it is a declared interface that
both are subtypes of. The type of the members of a group is found otherwise: their type when all have the
same type, else `positioned` when all are subtypes of it, else `shape`, with `none` added when the type of
one of them includes `none`.
```

So the common type of the branches of `(if on 1 2.5)` is `real`, and `g[k]` on a group of circles and rects is
`positioned`, so `g[k].x` may be read.

## Motifs and variants

```{rule} motif-and-variant-types
`(motif M PARAMS …)` declares the shape type M, and `(M N …)` declares an M. The motif may hold
the clause `(as N)` after its parameters, such as `(as me)`, which binds `N` in its body to the shape being declared
({numref}`declarations-and-bindings`).
`(variant V PARAMS S)` declares the type V, whose base type is the type of S: a shape type, a motif
type, a movement type, an animation type, a component type, or another variant type. V is a subtype
of its base, while a new motif or a new animation is a type of its own, disjoint from every other. A V has the attributes of its base and the parameters of V. Every attribute that S sets, a
{term}`positional argument` included, and `x` and `y` when S sets `pos`, is fixed by V: a V that
sets it is a compile error. A parameter of V never has the name of an attribute of its
base, and every parameter of V is read by an attribute that S sets: a parameter that no attribute
of S reads is a compile error. When `S` has `(defaults …)` and a V has `(defaults …)` too, the V
has both, and where both set the same attribute, the default of `S` wins.
```

So by {numref}`fits`, a `bar` declared `(variant bar ((real p 0)) (rect_ (width 0.8) (height (* 5 p))))`
is accepted wherever a `rect` is, and `(bar b2 (width 2))` is a compile error. A writer never
writes a fixed attribute ({numref}`writable-targets`). The parameters of a variant describe the
shapes of its base that it keeps: a square is a rect described by one number,
`(variant square ((real side 1)) (rect_ (width side) (height side)))`. A parameter that no attribute
reads, such as `q` in `(variant bar ((real p 0) (real q 1)) (rect_ (width 0.8) (height (* 5 p))))`,
would add an input that changes nothing in the shape, and is a compile error.

:::{admonition} Code differs
:class: note
The compiler accepts a variant parameter that no attribute of its shape reads. mtp-ydd4.7.61.
:::

## Functions

```{rule} function-types
The values of a function type are the functions declared with `func`, the functions written with
`fn`, the colormaps, the built-in functions, and the functions that calls of built-in functions result in,
such as the ease that `(steps N)` evaluates to. A type that is a function type, or holds one, as
`list[func[real real]]` does, is the type only of a parameter, a `let` name, an expression, and an
attribute whose type is a function type in {doc}`world-model`, such as the `ease` of a movement. A
variable and the declared result of a function may not have such a type: a declaration that
declares one with it is a compile error.
```

`=` on such a value is a compile error ({numref}`equality-operands`).

:::{admonition} Code differs
:class: note
The compiler refuses a variable whose type is a function type (`compiler.py:1484`,
`variable_here`), but accepts `(list fs [sind cosd])`, a variable of type `list[func[real real]]`,
and `(func g () sind)`, whose result is a function. Bead mtp-ydd4.7.43.
:::

```{rule} parameters
A parameter `(T N DEFAULT?)` of a function, a motif, a variant or an animation has the type T, which is
always written, with its conditions. Its default, when it has one, is of a subtype of T and is known when
compiling, or is a function declared with `func` or a built-in function. When a call, or a declaration whose head is a motif, leaves out a parameter, the parameter takes its
default, and when it has none, the value of T ({numref}`type-values`). A call of a function declared
with `func` may have at most as many arguments as the function has parameters, and may leave out only
the last ones. A call of a function value, such as a parameter, must have exactly as many arguments
as its type has parameters.
```

A parameter of `fn` may be written as a bare name when the function is given where its type is
expected, as for the function of `map` ({doc}`stdlib`): `(map xs (fn x (* 2 x)))`. Its type is then
the expected type.

```{rule} function-result-type
The result type of `(func[R] N PARAMS BODY)` is R. The result type of `(func N PARAMS BODY)` is
worked out from BODY, in which each call of N has a result type of its own:

1. T0 is the type of BODY when each call of N in BODY meets every type at that type
   ({numref}`common-type`), so that `(if (<= m 0) 0 (+ 1 (N …)))` has type `int`.
2. T(k + 1) is the type of BODY when each call of N in BODY has the type Tk.
3. The result type is the first Tk that equals T(k + 1).

When every branch of BODY calls N, or when T5 does not equal T6, the function is a compile error.
```

The type of a function declared with `func` is `func[P1 … Pn R]`, with the types of its
parameters and its result type. The type of `(fn PARAMS BODY)` is the same, with the type of BODY
as R.

## The type of each expression

```{rule} form-types
Each expression except a clause and a special form has this type:

| Expression | Its type |
|---|---|
| a literal | `int`, `ratio`, `real` or `complex` for a number, by how it is written ({numref}`number-literals`), `string` for a string literal or a {term}`TeX string`, `bool` for `true` and `false`, and `none` for `none` |
| a name | the type of what it refers to ({numref}`name-lookup`): the declared type of a variable, its value's type when the variable is a plain `list`, the type of a shape, the type of a parameter, the type of the value of a `let` name, `int` for the name of a `foreach` over a count, the item type for a `foreach` over a list, the common type of the members for a `foreach` over a group, and the function type of a function |
| `(. X K)` | the type of the attribute or the member that K chooses ({numref}`dot-name-part`). An item of a list: the item type. A coordinate of a point: `real`. A member of a group chosen while drawing: the common type of the members. Each with `none` added as {numref}`may-give-none` states |
| `(list-of X…)` | a list of the common type of its items ({numref}`common-type`). With no items, or only `none` items, a compile error, unless `list[T]` is expected: each item then has T expected |
| `(color-of S)` | `color` when S is known when compiling, `color\|none` otherwise ({numref}`color-literals`) |
| `(point-of X Y)` | `point`, each of X and Y with `real` expected. With `none` added when the type of X or of Y includes `none` ({numref}`none-propagates`) |
| `(as T X)` | T. X may be any expression whose type is a subtype of T: `as` states the type of X and never changes its value. So `(as list[real] {})` and `(as func[real real] (fn x (* 2 x)))` are allowed, and `(as int 2.5)` is a compile error |
| a spread `g.A` | `list[U]`, U the common type of the A of the members, with the number of members as its length. A member that has no A contributes `none`, and `none` is then added to U |
| `(if C A B)` | C has type `bool`. The type is the common type of A and B ({numref}`common-type`). When C is known in the prove step, the type of the branch taken ({numref}`known-condition-takes-one-branch`). When one branch never runs by {numref}`if-narrowing`, the type of the other branch |
| `(or? X D)` | the common type of the type of X without `none` and the type of D. When the type of X does not include `none`, the type of X |
| `(let (…) B)` | the type of B |
| `(fn PARAMS B)` | {numref}`function-result-type` |
| a call `(F A…)` of a function | the result type of F, with `none` added as {numref}`none-only-where-allowed` states |
| a call of a built-in function or an operator | the result type in {doc}`stdlib`, {numref}`number-result-types` for arithmetic, with `none` added as {numref}`none-only-where-allowed` and {numref}`may-give-none` state |
| `(= A B)`, `(!= A B)` | `bool` ({numref}`equality-operands`) |
| an {term}`interpolated string` | `string`, with `none` added when the type of one of its expressions includes `none` ({numref}`none-propagates`) |
| `(name S)` | the type of the declaration that it names ({numref}`names-from-values`) |
| `(type-of X)` | `string`. X is compiled for its type only |
| a declaration | the type of what it declares |
| `(free X)` | the type of X |

The type of each expression that is given where a type is expected must be a subtype of that type ({numref}`fits`), after
the conversions of {numref}`conversions`, or meet its conditions by {numref}`constraint-proof`.
```

So `(int m (if on 1 2.5))` is a compile error, since the common type of the branches is `real`, and
with an int `n`, `(real k n)` holds the value of `n` as a real.
