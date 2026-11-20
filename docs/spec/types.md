(types)=
# Types

This page defines the types of mtp, how a type is written, which {term}`values <value>` and
{term}`objects <object>` each type holds, when a value of one type is accepted where another type is expected, and the type of each
{term}`form`. Every {term}`expression` has a type, which the prove step works out
({numref}`compile-steps`), and the {term}`runtime` never checks a type
({numref}`runtime-no-type-work-while-drawing`). How a value is held and computed is defined in
{doc}`evaluation`, which objects there are and what their attributes are in {doc}`world-model`, and
the types of the built-in functions in {doc}`stdlib`. What the {term}`prover` proves about
{term}`ranges <range>`, {term}`conditions <condition>` and `none` is defined in
{doc}`well-formedness`.

This page specifies the language.

## What a type is

```{rule} what-a-type-is
A type is a named set of {term}`values <value>`, primitive values or objects, known when compiling: a set that
a source can write. Every variable, attribute,
parameter and expression has a type, and what it holds or gives is always in that set.

A value has no one type: its types are all the sets that it belongs to. A variable or an attribute
has one type, its declared type, written where it is declared, conditions included. Every write
into it and every read of it follows its declared type.
```

So `bool` is the set of the values `true` and `false`, `(real (>= 0))` is the set of the reals that
are not below 0, `real|none` is the set of the reals with `none` added, and `circle` is the set of
the circles. A type that {term}`fits <fit>` another is a subset of it.

A source makes new types from named ones in four ways, which differ only in how they are written:
a union, `point|circle`, joins sets; an intersection, `shape&round`, keeps the values that are in
both; a condition, `(real (>= 0))`, keeps the values of a set that meet it; and an interface,
`(interface inky (color ink))`, is the set of the values that have the attributes that it lists. `list[T]` and `func[P… R]` name the sets of the lists and the functions
whose items, parameters and result are of the types in the brackets.

```{rule} membership
`(is X T)` gives `true` when the value X is in the type T, and `false` otherwise. Where the type of
X lies wholly inside T, or wholly outside it, the answer is known when compiling. Otherwise the
runtime gives it. In the branch of an `if` that runs when `(is X T)` is true, X has the type T as
well as its own, and in the other branch X is known not to be in T.
```

So in `(func size ((point|circle p)) (if (is p circle) p.r 0))`, `p.r` is read only when `p` is a
circle, and `(is 3 real)` is `true` when compiling.

## The types

```{rule} the-types
These are the types of mtp:

| Type | Written | Its values or objects |
|---|---|---|
| `int`, `ratio`, `real`, `complex` | as named | the numbers of {numref}`number-types` |
| `unit` | `unit` | the same type as `(real (>= 0) (<= 1))`: the reals from 0 to 1 |
| `ease` | `ease` | the same type as `func[unit real]`: the eases of a movement ({doc}`time`) |
| `curve` | `curve` | the same type as `func[real point]`: the curves of the plane, such as the one that `parametric` draws |
| `bool` | `bool` | `true` and `false` |
| `string` | `string` | the {term}`strings <string>`, TeX strings among them |
| `color` | `color` | the colors ({doc}`world-model`) |
| `font` | `font` | the fonts: the records with a family, a style, a weight and a size |
| `point` | `point` | the pairs of {term}`reals <real>`, `x` and `y` |
| a {term}`list` type | `list[T]` | the lists of any length whose items are of type T |
| `function` | `function` | every function |
| a function type | `func[P1 … Pn R]` | the functions of n parameters, of types P1 to Pn, whose result is of type R |
| `movement` | `movement` | every movement: the moves, the scores and the movements of every animation type ({doc}`time`) |
| an animation type | the name of the animation | the movements that its uses make |
| `none` | `none` | the value `none` alone |
| a {term}`broadened type` | `T\|none` | the values of T, and `none` |
| a {term}`refined type` | `(T C…)` | the values of T that meet every condition C ({numref}`constraints`) |
| a union | `T1\|T2\|…` | the values of each of the types |
| an intersection | `T1&T2&…` | the values that are in every one of the types |
| a modular type | `(mod int lo hi)`, `(mod real lo hi)` | the numbers from lo up to hi, hi left out, with arithmetic that wraps ({numref}`modular-types`) |
| `shape` | `shape` | every shape: the shapes of every shape type, motif type and variant type |
| a shape type | `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `bezier`, `arc`, `ring`, `text`, `group` | the shapes of that kind. A row and a column are of type `group` |
| a motif type | the {term}`name` of the motif | its instances ({numref}`motif-and-variant-types`) |
| a variant type | the name of the variant | its instances ({numref}`motif-and-variant-types`) |
| `scene` | `scene` | the scene |
| `record`, `formula`, `term` | as named | the records, palettes and fonts among them, the formulas, and the terms |
| `component`, `view`, `control`, `listener` | as named | the components, the views, the controls and the listeners |
| a {term}`component` type | `canvas`, `readout`, `display`, `slider`, `button`, `play`, `stepper`, `toggle`, and the name of each listener | the components of that kind |
| an {term}`interface` | `positioned`, `sequence`, `sequence[T]`, `instant`, or the name of a declared interface | no object of its own: the objects whose types satisfy it ({numref}`interfaces`) |
| `rand-seed` | `rand-seed` | the values of `int` ({numref}`seed-variable`) |
| `colormap` | `colormap` | the same type as `func[real color]`: the functions from a real to a color |

There are no other types.
```

Each kind of object is a type: a named set of objects, as `shape` is the set of every shape. A type
of one kind of object is a subset of the type of its kind: `circle` is a subset of `shape`, `canvas` of
`view`, and `view` of `component`.

:::{admonition} Code differs
:class: note
- `unit` is not a built-in type: the file types of the standard library declares it, and a source
  imports it with `(import types unit)`. Bead mtp-vc5g makes it a built-in type and removes that
  file.
- `ease` is not a type, and the file of eases of the standard library is named ease.mtp. Bead
  mtp-6kta makes `ease` a built-in type and renames the file eases.mtp.
- The compiler has the type `transform`, which the spec does not have: a shape's frame is a set of
  its attributes ({doc}`data-model`). Bead mtp-1vyc.
- `record`, `formula`, `term`, `component`, `view`, `control`, `listener`, `function` and the
  component types are not types that a source can write: `(func f ((canvas c)) 1)` is the error
  "unknown type 'canvas'". `shape` is an interface, the type of a parameter only. `movement` and the
  animation types are named `transition` and `animation`. Bead mtp-rk1i.
- The shape `bezier` is named `curve`, and `curve` is not a type. Bead mtp-qnws renames the shape
  and makes `curve` a built-in type.
:::

Which of these are values and which are mutable objects is defined in {doc}`world-model`. A free
variable of type `rand-seed` is a {term}`seed` ({numref}`seed-variable`).

:::{admonition} Code differs
:class: note
The compiler gives `rand-seed` the constraint `(>= 0)` (`types.py:143`, `RAND_SEED`), so an
{term}`int` below 0 does not {term}`fit` it. Bead mtp-ydd4.7.30.
:::

```{rule} type-notation
Where a type is expected, the {term}`compiler` reads these expressions as types, and every other
expression there is a {term}`compile error`:

- The name of a {term}`built-in type` of {numref}`the-types`, or a name declared by `interface`,
  `motif` or `variant`, is that type, and a name declared by `(type N T C…)` is the
  refined type `(T C…)`.
- `list[T]` is a list type, with exactly one type in its {term}`brackets`. `list` with no brackets
  is allowed only as the {term}`head` of a variable whose value is given, and the type of the
  variable is then the type of its value.
- `sequence` with no brackets, and `sequence[T]` with exactly one type in its brackets, are
  interfaces.
- `func[T1 … Tn R]` is a function type, with one type or more in its brackets: the last is the
  result type, and the others are the types of the parameters, in order.
- No other name is followed by brackets in a type.
- `T1|T2|…` is a union: the set of the values of each of the types `T1`, `T2` and so on. Each is a
  name, or a name followed by brackets. `T|none` is the union of `T` and `none`, a broadened type.
- `T1&T2&…` is an intersection: the set of the values that are in each of the types. Each is a
  name, or a name followed by brackets.
- `(mod T lo hi)` is a modular type, with `T` either `int` or `real` ({numref}`modular-types`).
- `(T C…)` is a refined type: `T` is a type and each `C` is a condition. `((T C…) D…)` is
  `(T C… D…)`, and `(T|none C…)` is `(T C…)|none`.
- `none` is the type `none`. It is never written as the type of a declaration or of a parameter:
  it is the type only of an expression, and of a name that a `let` binds to such an expression.
```

So `real[int]` is a compile error, `real|real` is `real`, and `point|circle` is the set of the
points and the circles. A broadened type of a refined
type is written as `(real|none (>= 0))`, since a broadened type holds no form.

## Fitting

```{rule} fits
A type A fits a type B, and a value of type A is accepted where a value of type B is
expected, exactly when one of these holds:

1. A and B are the same type.
2. B is a union, and A fits one of its types; or A is a union, and each of its types fits B.
   `T|none` is one such union.
3. A is a variant type, and its base type fits B ({numref}`motif-and-variant-types`).
4. A or B is a refined type, A without its conditions fits B without its conditions, and the
   conditions of A imply each condition of B ({numref}`constraint-implication`).
10. B is an intersection, and A fits each of its types; or A is an intersection, and one of its
    types fits B.
5. A and B are number types, and A comes no later than B in the order `int`, `ratio`, `real`,
   `complex`.
6. A is `list[S]`, B is `list[U]`, and S fits U.
7. A is `func[P1 … Pn R]`, B is `func[Q1 … Qn S]`, with the same n, each Qi fits Pi, and R fits S.
8. B is an interface, and A satisfies it ({numref}`interfaces`).
9. A and B are `int` and `rand-seed`, in either order.

No other type fits another. A modular type fits only itself.
```

So a broadened type fits only a broadened type, a list of ints fits a list of reals, and a
function on every real fits where a function on the reals from 0 to 1 is expected:
`func[real real]` fits `func[(real (>= 0) (<= 1)) real]`. A `(real (>= 0) (<= 1))` fits `real`
and `(real (>= -1))`, and a `real` fits neither `(real (>= 0) (<= 1))` nor `(real (>= -1))`. Whether a value whose type does
not fit is still accepted, because the prover proves that its value meets the conditions, is
defined in {numref}`constraint-proof`.

```{rule} constraint-implication
A list of conditions implies a condition C exactly in these cases:

| C | The list holds one of these |
|---|---|
| `(>= c)` | `(>= a)` or `(> a)`, with a at least c |
| `(> c)` | `(> a)` with a at least c, or `(>= a)` with a above c |
| `(<= c)` | `(<= a)` or `(< a)` with a at most c |
| `(< c)` | `(< a)` with a at most c, or `(<= a)` with a below c |
| `(length n)` | `(length n)` |
| `(one-of s…)` | a `(one-of t…)` whose values are all among `s…` |
```

## Conditions

```{rule} constraints
A condition is a type written as the values that meet it, and `(T C…)` is the intersection of T with
each condition C. A condition is one of these forms, each on the types of its row only, and its
values are {term}`literals <literal>`:

| Condition | On | The values that meet it | Written with |
|---|---|---|---|
| `(>= c)`, `(> c)`, `(<= c)`, `(< c)` | `int`, `ratio`, `real` | the numbers at least c, above c, at most c, below c | one number |
| `(length n)` | `list[T]`, `string` | the lists or the strings of n items | one int, 0 or more |
| `(one-of v1 … vk)` | every type whose values are written as literals: the numbers, `bool`, `string`, `color`, `point`, `list[T]` | the values v1 to vk | one literal or more |

Any other form in the place of a condition, and a condition on a type outside its row, is a compile
error. A type of objects takes no condition: an intersection with an interface does that job.
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
up to hi, hi left out, with no order. A number that enters it is brought into its interval, and is
never refused: it is replaced by lo + ((v - lo) `mod` (hi - lo)), with `mod` as {doc}`stdlib`
defines it. A number enters it when it is the value of a variable or an attribute of the type, an
argument for a parameter of the type, the result of a function declared with the type, or a write
into a variable or an attribute of the type. Adding or subtracting a number to a value of the type
gives a value of the type. A value of the type takes no comparison, and `(as T X)` gives it as an
ordinary number.
```

So `((mod real 0 360) theta 400)` holds 40, `(+ theta 330)` is 10, and `(< theta 90)` is a compile
error. With `(type hour (mod int 0 12))` and `(func[hour] later ((hour h) (int n)) (+ h n))`,
`(later 9 5)` is 2.

:::{admonition} Code differs
:class: note
The compiler has no modular types. It has the constraint `(wrap lo hi)` on `int`, `ratio` and
`real`, whose arithmetic gives an ordinary number, so `(+ theta 30)` may be 380. Bead mtp-rk1i.
:::

```{rule} writes-into-constraints
A write of a number into a variable or an attribute brings it into the conditions of its declared
type: below a `(>= c)` it becomes c, above a `(<= c)` it becomes c, it is brought into a modular
type by {numref}`modular-types`, and when it breaks a `(> c)` or a `(< c)` it is not written. A write of a value that is not among the values of a `(one-of …)` is not
written. A number written into an `int` is rounded as {numref}`rounding` gives. A value that is
not written leaves the variable or the attribute as it was.
```

The {term}`number limit` applies to every write too ({numref}`number-limit`). So with
`(real p 0.5 (>= 0) (<= 1))`, a slider whose move goes to 1.4 stops `p` at exactly 1. Which values
a writer may write at all is defined in {numref}`written-values`.

```{rule} type-values
A variable declared with no value, and a parameter that a call or an instance leaves out and that
has no default, hold the value of their type:

| Type | Its value |
|---|---|
| `int`, `ratio`, `real`, `complex` | 0 |
| a modular type | 0 brought into the interval ({numref}`modular-types`) |
| a refined number type whose conditions 0 breaks | c, when the type holds `(>= c)`. With no `(>= c)`, the type has no value |
| `bool` | `false` |
| `string` | `''` |
| a refined string type with `(one-of s1 …)` | s1 |
| `color` | black, `#'#000000'` |
| `font` | the font of the defaults of a font ({doc}`world-model`) |
| `point` | `[0 0]` |
| `list[T]` | `[]`, and with `(length n)`, n items, each the value of T |
| `T\|none` | `none` |
| every other type | no value |

Leaving out the value of a type that has no value is a compile error.
```

So `(real k (>= 1))` holds 1, `(real k (> 1))` is a compile error, and a motif's parameter whose
type is an interface or a shape type is given in every instance.

## Literals and conversions

```{rule} literal-types
A literal has the type that is expected where it is written. Where no type is expected, it has its
own type.

| Literal | Own type | Where a type is expected |
|---|---|---|
| a number | its kind ({numref}`number-literals`) | its kind must fit the expected type, without its conditions: `1` where a real is expected is a real, and `2.5` where an int is expected is a compile error |
| a string literal or a {term}`TeX string` | `string` | where a refined string type is expected, it must be among its choices. It is never a color |
| a color literal, `#'…'` | `color` | as its own type ({numref}`color-literals`) |
| `true`, `false` | `bool` | as its own type |
| `none` | `none` | it must be a broadened type |
| `[X…]` | a list of the meeting of the types of its items ({numref}`common-type`). With no items, or only `none` items, it has no own type, and is a compile error | where a point is expected, it must have two items, each a number, or a value whose type is a number type with `none`, and it is a point. Where `list[T]` is expected, each item has T expected |
| `(as T X)` | T | X has T expected. X must be a literal |

A literal is checked against the conditions of the expected type by {numref}`constraint-proof`.
```

So `(circle c (fill #'red'))` gives a color, `(string s 'red')` a string, and
`(list[color] swatches [#'red' #'gold'])` a list of colors. A list literal may have expressions
as items, such as `[k 0]`. A point whose coordinate is `none` is `none`
({numref}`none-propagates`), so `[x y]` is of type `point|none` when the type of `x` includes
`none`.

```{rule} conversions
Only these change the type of a value where no form asks for it:

1. A number is accepted where a later number type is expected ({numref}`fits`), and is then a
   value of that type, as {numref}`number-result-types` gives.
2. Where a point is expected, a list of numbers whose length is known to be 2
   ({numref}`known-lengths`), and whose type does not include `none`, is a point. Where a list of
   points is expected, a list whose items are such lists, of a known item length 2, is a list of
   points. Where a function whose result is a point is expected, a function whose result is such a
   list is accepted.
3. A literal has the type that is expected where it is written ({numref}`literal-types`).

Nothing else converts. A string is never a color, a real is never an int, and a point is never a
list.
```

So `(string s 'red')` followed by `(circle d (fill s))` is a compile error, and a real becomes an
int only through a function such as `round`, `floor` or `ceil`, or through a write into an int
({numref}`writes-into-constraints`). A free list variable with no `(length n)` is never a point,
since a writer may give it another length.

```{rule} known-lengths
The length of a list is {term}`known <known length>` when its type holds `(length n)`. These lists
have that condition in their types, with these lengths:

- a list literal, of n items: n
- a list known when compiling: its length
- a variable, an attribute, a parameter or a declared result whose declared type holds
  `(length n)`: n
- a bound variable or attribute whose expression has a known length: that length
- `(if C A B)` whose branches have the same known length: that length
- a call of a function declared with `func` whose {term}`body` has a known length: that length
- a spread `g.A` of a group, and `g.members`: the number of members of the group
- a list that a {term}`built-in` function gives: the length that {doc}`stdlib` gives

The items of a list have a known item length m when every item is a list of known length m. Such a
list has `(length m)` in its item type.
```

So the length of `(list corners [[side 0] [0 0]])` is known, and its items have length 2 at every
position, even when `side` is known only while drawing. A free list variable has a known length
only when it is declared with `(length n)`, and its items never have a known item length, since a
write may give them another one.

## none and broadened types

```{rule} none-only-where-allowed
A type includes `none` when it is `none` or a broadened type. An expression whose type includes
`none` may be given only where the expected type includes `none`, with these exceptions:

- an argument of a call, whose parameter's type does not include `none`: the type of the call
  then includes `none`
- an argument of a built-in function or an {term}`operator`, other than those of
  {numref}`none-never-a-condition`: the type of the result then includes `none`, except for the
  functions that {numref}`none-propagates` names

Everywhere else, such an expression is a compile error.
```

So a shape attribute that may be `none` is a compile error unless the type of the attribute
includes `none`, as the types of `fill` and `stroke` do ({doc}`world-model`), or the shape is
declared `T|none`. Every attribute of a shape declared `T|none` has a type that includes `none`,
and so does every member of a collection declared `T|none` and every read of such a shape or its
attributes outside its own body. `(or? x d)`, `somes` and a shape declared `T|none` are the ways to
handle `none` ({doc}`stdlib`).

```{mtp-example}
; at 90° the secant has no value: the line is declared line|none and is not drawn there
(real theta 60 (>= 0) (<= 180))
(scene s
  (line|none tangent (from [0 0]) (to [(secd theta) 0]) (stroke #'crimson') (stroke-width 3))
  (circle p (pos (polar 1 theta)) (r 0.08)))
(canvas v (x -3) (y -1.5) (width 6) (height 3) s)
(slider turn (move theta (from 0) (to 180)) (label 'θ'))
```

## Choice types

```{rule} choice-types
A {term}`choice type` is a refined type `(string (one-of s…))`. A value of a choice type is a
string, so it fits `string`.
```

By {numref}`constraint-proof`, a value whose type does not fit a choice type meets its
`(one-of …)` only when it is known in the prove step and is among its choices. So with `(type side string (one-of 'left' 'right'))`, `(side s 'up')` is a compile error, and a
string variable that a writer may change never becomes a `side`. The alignments of a text, the caps
and joins of a stroke, the heads of a line and the style of a font are choice types
({doc}`world-model`). A write of a string that is not a choice is not written
({numref}`writes-into-constraints`).

:::{admonition} Code differs
:class: note
The compiler checks the choices only of a value known when compiling (`compiler.py:5823`,
`checked`), so `(string q 'up')` followed by `(side s q)` compiles. Bead mtp-ydd4.7.42.
:::

## Interfaces

```{rule} interfaces
An interface is a type given by attributes: the set of the values that have the attributes that it
lists, of the types that it gives them. It is a type like any other, and may be the type of a
variable, an attribute or a parameter. A type satisfies an interface as follows:

| Interface | Satisfied by |
|---|---|
| `shape` | every shape type, motif type and variant type |
| `positioned` | `point`, and every shape type, motif type and variant type but `group` |
| `sequence` | every list type, `point` and `group` |
| `instant` | every movement whose `duration` is 0: a jump, and a score of jumps. It is `(interface instant ((real (one-of 0)) duration))` |
| `sequence[T]` | `list[S]` when S fits T, `point` when `real` fits T, and `group`, when the common type of the members of the group ({numref}`common-type`) fits T |
| `palette` | every record whose members are all colors, whatever their names and number. A palette made by `(palette …)` is one ({numref}`sugar-rewrites`) |
| a declared interface, `(interface N (T1 A1 C1…) …)` | a type whose objects all have each attribute Ai, of a type that fits `(Ti C1…)`, or that satisfies Ti when Ti is a declared interface. For a record, the attributes are its members, and each record that a value may be satisfies the interface on its own |

A value whose type is an interface is read only for what the interface gives: the attributes of
the frame for `shape`, `x`, `y` and `pos` for `positioned`, its items by position and its
`length` for a `sequence`, and the attributes Ai for a declared interface. A member M of a value
whose type is `palette` is read by its name and has the type `color|none`: it is `none` when the
record has no member M.
```

:::{admonition} Code differs
:class: note
The compiler has no interface `palette`: `(func f ((palette q)) 1)` is the error "unknown type
'palette'" (`types.py:150`, `PALETTE`, is a type that a palette has as its own). Bead mtp-rdk2.
:::

So `(func label-at ((positioned o) (string s)) …)` may be given points and shapes alike, and
`(func area ((shape o)) (* pi o.r o.r))` is a compile error, since not every shape has an `r`. A
condition of a declared interface is met only when the type of the attribute implies it: a
record whose `r` is a plain `real` does not satisfy `(interface round (real r (>= 0)))`.

The named types form a hierarchy: every value is a primitive value or an object, and every object is of one
kind, a shape, a movement, a record and so on. An interface cuts across it: `positioned` holds
points, which are values, and shapes, which are objects.

:::{admonition} Code differs
:class: note
The compiler joins a type only with `none`: `(func f ((point|circle p)) 1)` is the error "a type can
be broadened only by none for now". An interface is the type of a parameter only, and a variable
declared with one is a compile error. Bead mtp-mo3r.
:::

```{mtp-example}
; the parameter colors of the motif disc takes either namespace, since both fit inky
(interface inky (color ink) (color paper))
(namespace day (color ink #'#1f2a44') (color paper #'#f6f1e7'))
(namespace night (color ink #'#e8e4d8') (color paper #'#14161c'))
(bool dark false)
(motif disc ((inky colors)) (circle face (r 1) (fill colors.paper) (stroke colors.ink) (stroke-width 0.2)))
(scene s (disc d (colors (if dark night day))))
(canvas v (x -2) (y -2) (width 4) (height 4) s)
(toggle mode dark (label 'dark'))
```

```{rule} common-type
Where the types of several values meet in one type, the type is the narrowest type that each of
them fits, found this way for two types A and B:

- When A fits B, it is B, and when B fits A, it is A.
- When one is `none`, it is the other, broadened.
- When one includes `none`, it is the meeting of the two without `none`, broadened.
- Two number types meet at the later of the two, without conditions, in the order `int`,
  `ratio`, `real`, `complex`.
- Two list types meet at the list type of the meeting of their item types.
- Otherwise there is no meeting, and the source is a compile error.

The branches of an `if` and the items of a list literal meet this way, except that the
branches of an `if` meet at the expected type when it is a declared interface that both satisfy.
The members of a group meet otherwise: at their type when all have the same type, else at
`positioned` when all satisfy it, else at `shape`, and broadened when the type of one of them
includes `none`.
```

So the branches of `(if on 1 2.5)` meet at `real`, and `g[k]` on a group of circles and rects is
`positioned`, so `g[k].x` may be read.

## Motifs and variants

```{rule} motif-and-variant-types
`(motif M PARAMS …)` declares the shape type M, whose objects are the instances of M.
`(variant V PARAMS S)` declares the type V, whose base type is the type of S: a shape type, a motif
type, a movement type, an animation type, a component type, or another variant type. V is a subtype
of its base, while a new motif or a new animation is a type of its own, disjoint from every other. An instance of
V has the attributes of its base and the parameters of V. Every attribute that S gives, a
{term}`positional argument` included, and `x` and `y` when S gives `pos`, is fixed by V: an instance
of V that gives it is a compile error. A parameter of V never has the name of an attribute of its
base, and every parameter of V is read by an attribute that S gives: a parameter that no attribute
of S reads is a compile error.
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
`fn`, the colormaps, the built-in functions, and the functions that a built-in function gives, such
as the ease that `(steps N)` gives. A type that is a function type, or holds one, as
`list[func[real real]]` does, is the type only of a parameter, a `let` name, an expression, and an
attribute that {doc}`world-model` gives a function type, such as the `ease` of a movement. A
variable and the declared result of a function never have such a type, and a declaration that
gives them one is a compile error.
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
always written, with its conditions. Its default, when it has one, fits T and is known when
compiling, or is a function declared with `func` or a built-in function. A call or an instance that
leaves out a parameter gives it its default, and when it has none, the value of T
({numref}`type-values`). A call of a function declared with `func` gives at most as many arguments
as it has parameters, and leaves out only the last ones. A call of a function value, such as a
parameter, gives exactly as many arguments as its type has parameters.
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

## The type of each form

```{rule} form-types
Each form has this type:

| Form | Its type |
|---|---|
| a literal | {numref}`literal-types` |
| a name | the type of what it refers to ({numref}`name-lookup`): the declared type of a variable, its value's type when the variable is a plain `list`, the type of a shape or an instance, the type of a parameter, the type of the value of a `let` name, `int` for the name of a `foreach` over a count, the item type for a `foreach` over a list, the common type of the members for a `foreach` over a group, and the function type of a function |
| `(. X Y)` | the type of the attribute or the member Y of X ({numref}`dot-name-part`). An item of a list or a point: the item type. A member of a group by a key known only while drawing: the common type of the members. Each broadened as {numref}`may-give-none` gives |
| a spread `g.A` | `list[U]`, U the meeting of the types of A of the members, with the number of members as its length |
| `(if C A B)` | C has type `bool`. The type is the meeting of A and B ({numref}`common-type`). When C is known in the prove step, the type of the branch taken ({numref}`known-condition-takes-one-branch`). When one branch never runs by {numref}`if-narrowing`, the type of the other branch |
| `(or? X D)` | the meeting of the type of X without `none` and the type of D. When the type of X does not include `none`, the type of X |
| `(let (…) B)` | the type of B |
| `(fn PARAMS B)` | {numref}`function-result-type` |
| a call `(F A…)` of a function | the result type of F, broadened as {numref}`none-only-where-allowed` gives |
| a call of a built-in function or an operator | the type that {doc}`stdlib` gives, {numref}`number-result-types` for arithmetic, broadened as {numref}`none-only-where-allowed` and {numref}`may-give-none` give |
| `(= A B)`, `(!= A B)` | `bool` ({numref}`equality-operands`) |
| an {term}`interpolated string` | `string`, broadened when the type of one of its expressions includes `none` ({numref}`none-propagates`) |
| `(name S)` | the type of the declaration that it names ({numref}`names-from-values`) |
| `(type-of X)` | `string`. X is compiled for its type only |
| a declaration | the type that its head gives, as in {numref}`form-template` |
| `(free X)` | the type of X |

Each expression that is given where a type is expected must fit that type ({numref}`fits`), after
the conversions of {numref}`conversions`, or meet its conditions by {numref}`constraint-proof`.
```

So `(int m (if on 1 2.5))` is a compile error, since the branches meet at `real`, and
`(real k n)` with an int `n` gives `k` the value of `n` as a real.
