# Built-ins and the standard library

This page defines every {term}`built-in` function and constant ({numref}`built-ins`), and every
file of the {term}`standard library`. The built-in types are defined in {doc}`types`.

## How the built-in functions are given

This rule exists so that the prover can give every call of a built-in function a type and a range from this page alone.

```{rule} builtin-tables
Each built-in function is given by its signature ({ref}`signatures`) and by a row of a table of
this page, which gives the value of a call, its result type and its range ({numref}`ranges`). In
the type of an argument or of a result, `T`, `U` and `A` stand for any type, the same type at
every place in one signature. A range given as "its type" is the range of the result type
({numref}`range-rules`), and a call whose result is not a number has no range. A call evaluates to
`none` only at the arguments that {numref}`expressions-that-give-none` lists, and its type includes
`none` only as {numref}`none-only-where-allowed`, {numref}`may-give-none` and
{numref}`none-without-ranges` state.
```

So `(sqrt k)` with `(real k 4 (>= 1) (<= 9))` is a `real` whose range is 1 to 3, by the row of
`sqrt` in {numref}`number-functions`.

This rule exists so that the prover knows which calls of built-in functions give lists of a known length.

```{rule} builtin-known-lengths
A call of `map`, `sorted`, `reversed` or `shuffled` has the {term}`known length` of its list, when
that list has one, and a call of `range` whose arguments are all known in the prove step has the
number of its items. No other call of a built-in function has a known length.
```

## Operators

This rule exists to give the arguments of each {term}`operator`, whose results other rules define.

```{rule} operators
| Operator | Arguments | Its value |
|---|---|---|
| `+`, `*` | one number or more | the sum, the product |
| `-` | one number or more | minus the number, and with several, the first minus the others |
| `/` | two numbers | the first divided by the second |
| `^` | two numbers | the first to the power of the second |
| `mod` | two ints, ratios or reals | A - B × ⌊A / B⌋, which has the sign of B: `(mod -1 360)` is 359 |
| `<`, `<=`, `>`, `>=` | two ints, ratios or reals | `true` when the first is below, at most, above, at least the second |
| `=`, `!=` | two values | {numref}`equality-operands`, {numref}`equality-by-content` |
| `not` | one bool | `true` for `false`, and `false` for `true` |

The result type of an arithmetic operator is given by {numref}`number-result-types`, and its range
by {numref}`range-rules`. `+` and `-` also take points, and `*` and `/` a point and reals
({numref}`point-arithmetic`). `+`, `-` and `*` also take lists of numbers that all have the same
known length, item by item, and `*` takes reals with such a list, each of which multiplies every item.
A comparison and `not` give a `bool`.
```

So `(+ {1 2} {10 20})` is `{11 22}`, and `(* 2 {1 2})` is `{2 4}`. `(< a b c)` is a compile
error, since `<` takes two arguments.

## Numbers

This rule exists to give the built-in functions on numbers, which cannot be written in mtp with results that are correctly rounded ({numref}`correctly-rounded-reals`).

````{rule} number-functions
```mtp-sig
(abs X:int|ratio|real|complex)
(sqrt X:real)
(exp X:real)
(log X:real BASE:real?)
(sign X:real)
(round X:real)
(floor X:real)
(ceil X:real)
(places X:real K:int)
(unwrap X:mod)
(min ITEMS:real|list[real]+)
(max ITEMS:real|list[real]+)
(lerp A:real|point B:real|point T:real)
```

| Call | Its value | Result type | Range |
|---|---|---|---|
| `(abs X)` | the absolute value of X | {numref}`number-result-types` | {numref}`range-rules` |
| `(sqrt X)` | the square root of X | `real` | from the square root of the lower end of X to the square root of its upper end, each end below 0 taken as 0 |
| `(exp X)` | e to the power X | `real` | from e to the power of the lower end of X to e to the power of its upper end |
| `(log X BASE)` | the logarithm of X to the base BASE, and the natural logarithm when BASE is left out | `real` | when the ranges of X and BASE hold no value at which `log` evaluates to `none`, the smallest and the largest of ln x / ln b, for x each end of X and b each end of BASE, b being e when BASE is left out. Otherwise the whole number limit |
| `(sign X)` | -1 when X is below 0, 0 when X is 0, and 1 when X is above 0 | `int` | from the sign of the lower end of X to the sign of its upper end |
| `(round X)`, `(floor X)`, `(ceil X)` | the int nearest X ({numref}`rounding`), the largest int at most X, and the smallest int at least X | `int` | the ends of X, each rounded in the same way |
| `(places X K)` | X rounded to K decimal places ({numref}`rounding`), and to tens, hundreds and so on for K below 0 | `real` | the smallest and the largest of the ends of X, each rounded to each int of the range of K. When the range of K holds more than 21 ints, the whole number limit |
| `(unwrap X)` | for X of type `(mod T lo hi)`, the number of X as a T ({numref}`modular-types`) | T | from lo to hi |
| `(min ITEMS…)`, `(max ITEMS…)` | the smallest and the largest of the items, a list counting as its items | `real` | for `min`, from the smallest lower end to the smallest upper end of the items, and for `max`, from the largest lower end to the largest upper end |
| `(lerp A B T)` | A + (B - A) × T | the type of A | its type |
````

So `(places 2.675 2)` is 2.68, `(places 1234 -2)` is 1200, and `(max g.r)` is the largest radius of
the members of a group `g`. With `(real k 1 (>= 0) (<= 3))`, the range of `(sign (- k 1))` is -1 to
1, and the range of `(floor (* 1.5 k))` is 0 to 4.

## Angles

This rule exists to give the trigonometric functions, in radians and in degrees, and the conversions between the two.

````{rule} angle-functions
```mtp-sig
(sin X:real) (cos X:real) (tan X:real) (sec X:real) (csc X:real) (cot X:real)
(sind X:real|angle) (cosd X:real|angle) (tand X:real|angle)
(secd X:real|angle) (cscd X:real|angle) (cotd X:real|angle)
(asin X:real) (acos X:real) (atan X:real) (acot X:real) (asec X:real) (acsc X:real)
(asind X:real) (acosd X:real) (atand X:real) (acotd X:real) (asecd X:real) (acscd X:real)
(rad X:real) (turn X:real) (deg X:real) (to-rad X:real) (to-turn X:real)
```

| Call | Its value | Result type | Range |
|---|---|---|---|
| `(sin X)` and the others in radians | the function of the angle of X radians | `real` | -1 to 1 for `sin` and `cos`, and its type for the others |
| `(sind X)` and the others in degrees | the function of the angle of X degrees | `real` | -1 to 1 for `sind` and `cosd`, and its type for the others |
| `(asin X)`, `(atan X)`, `(acsc X)` | the inverse function, in radians | `real` | from -π/2 to π/2 |
| `(acos X)`, `(acot X)`, `(asec X)` | the inverse function, in radians | `real` | from 0 to π |
| `(asind X)` and the other inverse functions in degrees | the inverse function, in degrees | `angle` | its type |
| `(rad X)` | X radians in degrees, X × 180 / π | `real` | its type |
| `(turn X)` | X turns in degrees, 360 × X | `real` | its type |
| `(deg X)` | X, a number of degrees | `real` | its type |
| `(to-rad X)` | X degrees in radians, X × π / 180 | `real` | its type |
| `(to-turn X)` | X degrees in turns, X / 360 | `real` | its type |

Each end π/2 and π of a range is the binary64 number nearest to it.
````

So `(asind -0.5)` is the angle 330, since an `angle` lies from 0 up to 360 ({numref}`the-types`),
and `(sind 30)` is exactly 0.5 ({numref}`correctly-rounded-reals`).

## Points

This rule exists to give the built-in functions that make a point from a distance and an angle, and that measure the distance between two points.

````{rule} point-functions
```mtp-sig
(polar R:real A:real|angle)
(dist P:point Q:point)
```

| Call | Its value | Result type | Range |
|---|---|---|---|
| `(polar R A)` | the point at the distance R from `[0 0]`, in the direction of A degrees from the x-axis, counterclockwise: `[R × cos A°, R × sin A°]` | `point` | |
| `(dist P Q)` | the distance between P and Q | `real` | from 0 to the upper end of the number limit |
````

## Points on the box of a shape

This rule exists to give the functions that place one shape against another, by the box of the other.

````{rule} box-points
```mtp-sig
(top S:shape GAP:real?) (bottom S:shape GAP:real?)
(left S:shape GAP:real?) (right S:shape GAP:real?)
(top-left S:shape GAP:real?) (top-right S:shape GAP:real?)
(bottom-left S:shape GAP:real?) (bottom-right S:shape GAP:real?)
```

`(top S)`, `(bottom S)`, `(left S)` and `(right S)` evaluate to the middle of that side of the box
of S ({doc}`world-model`), and `(top-left S)` and the others to that corner of it, the top being
toward the larger y. GAP, 0 when it is left out, moves the point out from the box by GAP on each
side that the name gives. Each result is a `point`, in the frame of the expression that holds the
call, as every read of a position is ({numref}`evaluation-is-pure`).
````

So `(top-right p 0.05)` is 0.05 to the right of the box of `p` and 0.05 above it.

## Colors

This rule exists to give the built-in functions that make colors, which cannot be written in mtp, since only these functions read and set the channels of a color.

````{rule} color-functions
```mtp-sig
(rgb R:unit G:unit B:unit A:unit?)
(mix C:color D:color T:unit)
(tint C:color T:unit)
(shade C:color T:unit)
(light-dark L:color D:color)
```

| Call | Its value |
|---|---|
| `(rgb R G B A)` | the color whose red, green, blue and alpha channels are R, G, B and A, with A 1 when it is left out |
| `(mix C D T)` | the color T of the way from C to D, as CSS `color-mix(in srgb, C, D p%)` computes it with p = 100 × T, with premultiplied alpha, each channel rounded by {numref}`mixed-color-channels` |
| `(tint C T)` | `(mix C #'#ffffff' T)` |
| `(shade C T)` | `(mix C #'#000000' T)` |
| `(light-dark L D)` | the color that is L where the page is light and D where it is dark, by the CSS `color-scheme` of the place where it is drawn. Its light value is the light value of L, and its dark value the dark value of D. When the two values are the same, it is that one color |

Each result is a `color`. `mix`, `tint` and `shade` mix the light values together and the dark
values together.
````

So `(mix ink paper 0.5)` is halfway between the light values of `ink` and `paper` where the page is
light, and halfway between their dark values where it is dark, and `(light-dark #'red' #'#ff0000')`
is the color `#'red'`.

## Lists

This rule exists to give the functions on lists, which take a list of any type, and so cannot be written in mtp.

````{rule} list-functions
```mtp-sig
(map XS:list[T] F:func[T U])
(where XS:list[T] F:func[T bool])
(first XS:list[T] F:func[T bool])
(sorted XS:list[T] F:func[T real])
(reversed XS:list[T])
(reduce XS:list[T] START:A F:func[A T A])
(sum XS:list[int]|list[ratio]|list[real]|list[complex])
(count XS:list[T] F:func[T bool]?)
(any XS:list[bool]) (any XS:list[T] F:func[T bool])
(all XS:list[bool]) (all XS:list[T] F:func[T bool])
(somes XS:list[T|none])
```

| Call | Its value | Result type | Range |
|---|---|---|---|
| `(map XS F)` | the list of `(F x)` for each item x of XS, in order | `list[U]`, with `none` added to U when T includes `none` and the parameter of F does not | of each item, the range of the body of F |
| `(where XS F)` | the items x of XS for which `(F x)` is true, in order | `list[T]` | |
| `(first XS F)` | the first item x of XS for which `(F x)` is true, and `none` when there is none | `T\|none` | the range of the items of XS |
| `(sorted XS F)` | the items of XS by `(F x)`, smallest first, items with equal values of `(F x)` in their order in XS | `list[T]` | |
| `(reversed XS)` | the items of XS in the opposite order | `list[T]` | |
| `(reduce XS START F)` | `(F … (F (F START x₀) x₁) … xₙ₋₁)`, for the items x₀ to xₙ₋₁ of XS, and START when XS is empty | A | its type |
| `(sum XS)` | the sum of the items | the item type of XS | its type |
| `(count XS F)` | the number of items x of XS for which `(F x)` is true, and with F left out, the number of items | `int` | n, when F is left out and XS has the known length n, and otherwise from 0 to the upper end of the number limit |
| `(any XS F)`, `(all XS F)` | `true` when `(F x)` is true for at least one item x, or for every item, and with F left out, when at least one item, or every item, is true | `bool` | |
| `(somes XS)` | the items of XS that are not `none`, in order | `list[T]` | |

In each of these calls, XS may also be a group, which stands for the list of its members, and in a
`map`, an int N, which stands for `(range 0 N)`. The parameter of F that takes an item of XS has the
range of the items of XS: from the smallest to the largest item when XS is known in the prove step,
and otherwise the range of an item of a list ({numref}`range-rules`). The parameter of the F of a
`reduce` that takes the value so far has the range of A.
````

So `(map {1 2 3} (fn k (* 2 k)))` is `{2 4 6}`, a list of known length 3 whose items have the
range 2 to 6, and in `(map xs (fn x (* 2 x)))`, with `xs` a `list[real]`, `x` is a real
({numref}`parameters`). `(first {1 4 9} (fn ((int k)) (> k 3)))` is 4.

This rule exists to give `range`, which makes a list of numbers from its ends.

````{rule} range-function
```mtp-sig
(range LO:real HI:real (gap:real 1))
(range LO:real HI:real (num:int))
```

`(range LO HI (gap G))` is the list of the numbers LO + k × G, for k = 0, 1, 2 and so on, that are
below HI when G is above 0, and above HI when G is below 0. G is 1 when the range gives neither
`gap` nor `num`. `(range LO HI (num N))` is the list of N numbers evenly apart from LO to HI, both
included, and the list of LO alone when N is 1. When every argument is known in the prove step, the
items are ints exactly when they are all whole and LO, HI and G are ints, or with `num`, LO and HI
are ints. Otherwise the list is a `list[int]` when LO, HI and G are ints, and a `list[real]` when
one of them is not or when the range gives `num`. The range of the items is from the smaller of the
lower ends of LO and HI to the larger of their upper ends.
````

So `(range 0 5)` is `{0 1 2 3 4}`, `(range 5 0 (gap -2))` is `{5 3 1}`, and `(range 0 1 (num 5))`
is `{0 0.25 0.5 0.75 1}`.

## Eases

This rule exists to give `steps`, which makes an ease from numbers, and so is a function whose result is a function, which no function written in mtp may be ({numref}`function-types`).

````{rule} steps-ease
```mtp-sig
(steps N:(int (>= 1)) (at:unit 1))
```

`(steps N (at P))` is the ease of N equal jumps, each at the fraction P of its
interval, so that jump k comes at (k - 1 + P) / N. P is known when compiling. The result is an
`ease` ({numref}`the-types`).
````

So `(steps 1 (at P))` is 0 before P and 1 from P on.

## Constants

This rule exists to give the built-in constants.

```{rule} constants
| Constant | Its value | Type |
|---|---|---|
| `pi` | π, the ratio of the circumference of a circle to its diameter | `real` |
| `tau` | 2π | `real` |
| `euler` | e, the base of the natural logarithm | `real` |

Each value is the binary64 number nearest to it.
```

:::{admonition} Code differs
:class: note
- The compiler names `sorted`, `reversed`, `tint` and `shade` `sort`, `reverse`, `lighten` and
  `darken` (mathterpiece/builtins.py, line 347, and compiler.py, line 189). It has no `first`,
  `places`, `unwrap`, `rgb` or `steps`. In their place, `(round X K)` rounds to K places, and
  `(step N)` and `(step-ease P)` are eases ({doc}`heads`).
- The compiler has the built-in functions `to-polar`, `rotate`, `translate`, `scale` and
  `transform`, which the spec does not have (builtins.py, lines 341 to 345, and compiler.py,
  line 2634). Bead mtp-1vyc.
- The inverse functions in degrees evaluate to a `real`, with the range -90 to 90 or 0 to 180
  (builtins.py, lines 325 to 334), and the functions in degrees take only a `real`. Bead mtp-dp9y.
- The range of `(rand lo hi)` and of `(rand-int lo hi)` is the whole number limit unless both
  bounds are known when compiling (compiler.py, lines 2507 to 2523).
- `places` with a negative K gives the whole number limit as its range when an end of X is 10¹⁵ or
  more (compiler.py, line 7166).

Beads mtp-qnfd, mtp-6a4r and mtp-08wd.12 make the compiler follow the rules.
:::

## The files of the standard library

This rule exists to name the files that come with mtp, so that every compiler gives the same names to an import of one of them.

```{rule} library-files
The standard library has the files `style`, `colors`, `eases`, `marks`, `math`, `geometry`,
`text`, `animations` and `rand`, and no others. Each file but rand is a {term}`file to import`
written in mtp, which holds exactly the declarations that its rule below gives, and the file rand
is given by {numref}`rand-module`. A source imports each of them like any other file
({doc}`imports`), and has none of their names without an import ({numref}`import-puts-in`).
```

So `(import math clamped)` makes the name `clamped` usable, and `(import eases)` makes
`eases.cubic-in-out` and the other eases usable.

(stdlib-style)=
### The file style

This rule exists to give the colors and the fonts of the default look of mtp, each with a value for a light page and one for a dark page.

````{rule} style-file
The file `style` holds exactly these declarations:

```mtp
(color red (light-dark #'#ac2e2b' #'#f26b6c'))
(color orange (light-dark #'#c0522b' #'#f79a41'))
(color yellow (light-dark #'#d57a01' #'#ffd31b'))
(color green (light-dark #'#71a05b' #'#98df96'))
(color teal (light-dark #'#158c7f' #'#39cbb5'))
(color blue (light-dark #'#0561b3' #'#6aa2ce'))
(color purple (light-dark #'#8b3be2' #'#a37cff'))
(color pink (light-dark #'#e54393' #'#c16291'))

(color gray-0 (light-dark #'#ffffff' #'#13181b'))
(color gray-50 (light-dark #'#fcfefe' #'#1c242a'))
(color gray-100 (light-dark #'#edf0f2' #'#2a3740'))
(color gray-200 (light-dark #'#dae1e5' #'#38454f'))
(color gray-300 (light-dark #'#c2ccd3' #'#475662'))
(color gray-400 (light-dark #'#b3bfc7' #'#566877'))
(color gray-500 (light-dark #'#a9b7c1' #'#67798a'))
(color gray-600 (light-dark #'#8b9fad' #'#7a8a99'))
(color gray-700 (light-dark #'#5f7186' #'#8c9ba8'))
(color gray-800 (light-dark #'#51636f' #'#a0acb7'))
(color gray-900 (light-dark #'#3c4952' #'#b5bfc8'))
(color gray-950 (light-dark #'#13181b' #'#ced6dc'))
(color gray-1000 (light-dark #'#000000' #'#e8edf0'))

(color paper gray-0 doc@'The page.')
(color ink gray-900 doc@'Text and lines.')
(color soft gray-700 doc@'Guides and helper lines, the lightest gray that passes 3:1 on both pages.')
(color accent blue doc@'The one color for what matters most in a figure.')

(font serif (family '"Source Serif 4", Georgia, serif'))
(font sans (family '"Source Sans 3", system-ui, sans-serif'))
(font mono (family '"Source Code Pro", ui-monospace, monospace'))
(font math (family '"Latin Modern Math", "STIX Two Math", "Cambria Math", math'))

(font text (like sans) (size 16) doc@'Labels and running text.')
(font variable (like serif) (style 'italic') (size 18) doc@'Names of variables, such as x.')
(font number (like mono) (size 14) doc@'Numbers in readouts and on axes.')
(font code (like mono) (size 13) doc@'Source code.')
```
````

The eight hues each have a contrast of at least 3:1 with the paper of their page. The grays go from
`gray-0`, the paper itself, to `gray-1000`, the farthest from it: black on a light page and a
near-white on a dark one.

(stdlib-colors)=
### The file colors

This rule exists to give palettes for telling series and categories apart, and colormaps for showing a number as a color.

````{rule} colors-file
The file `colors` holds exactly these declarations:

```mtp
(palette okabe-ito
  doc@'Okabe and Ito\'s eight colors, made to be told apart from each other under the common kinds of
color blindness, which makes them a good choice for plots. They are not made for contrast with the
page: on a light page, orange, sky-blue and yellow are faint. On a dark page black becomes a
near-white, and the others are as published.'
  (orange #'#e69f00')
  (sky-blue #'#56b4e9')
  (bluish-green #'#009e73')
  (yellow #'#f0e442')
  (blue #'#0072b2')
  (vermillion #'#d55e00')
  (reddish-purple #'#cc79a7')
  (black (light-dark #'#000000' #'#e8edf0')))

(palette tab10
  doc@'Matplotlib\'s ten default colors, made to look distinct to readers with typical color vision,
on both pages. They are not made for color blindness: under protanopia orange and green look the
same. They are not made for contrast with the page either: on a light page, orange, pink, olive
and cyan are faint.'
  (blue #'#1f77b4')
  (orange #'#ff7f0e')
  (green #'#2ca02c')
  (red #'#d62728')
  (purple #'#9467bd')
  (brown #'#8c564b')
  (pink #'#e377c2')
  (gray #'#7f7f7f')
  (olive #'#bcbd22')
  (cyan #'#17becf'))

(colormap viridis
    {#'#440154' #'#48186a' #'#472d7b' #'#424086' #'#3b528b' #'#33638d' #'#2c728e' #'#26828e' #'#21918c'
     #'#1fa088' #'#28ae80' #'#3fbc73' #'#5ec962' #'#84d44b' #'#addc30' #'#d8e219' #'#fde725'}
  doc@'Dark purple through blue and green to yellow, from 0 to 1.')
(colormap magma
    {#'#000004' #'#0a0822' #'#1d1147' #'#36106b' #'#51127c' #'#6a1c81' #'#832681' #'#9c2e7f' #'#b73779'
     #'#d0416f' #'#e75263' #'#f56b5c' #'#fc8961' #'#fea772' #'#fec488' #'#fde2a3' #'#fcfdbf'}
  doc@'Black through purple and red to pale yellow, from 0 to 1.')
(colormap cividis
    {#'#00224e' #'#002e6a' #'#1a386f' #'#32436d' #'#434e6c' #'#535a6d' #'#61656f' #'#6f7073' #'#7d7c78'
     #'#8c8878' #'#9b9476' #'#aba072' #'#bcae6c' #'#cdbb63' #'#dec958' #'#f0d846' #'#fee838'}
  doc@'Blue to yellow, readable with the common kinds of color blindness.')
(colormap blue-white-red
    {#'#053061' #'#2166ac' #'#4393c3' #'#92c5de' #'#d1e5f0' #'#f7f7f7' #'#fddbc7' #'#f4a582' #'#d6604d'
     #'#b2182b' #'#67001f'}
  doc@'For values on either side of a middle: ColorBrewer\'s eleven, blue to white to red.')
```
````

Each palette is a record whose members are named by their hues, so `(var pal tab10 okabe-ito)` may
swap one palette for the other. The colors of `viridis`, `magma` and `cividis` are 17 colors evenly
apart, taken from the colormaps of matplotlib of the same names. A world model gives a colormap
its own numbers, such as `(viridis (/ depth 50))`.

(stdlib-eases)=
### The file eases

This rule exists to give the eases that movements use most.

````{rule} eases-file
The file `eases` holds exactly these declarations:

```mtp
(func linear ((unit t))
  doc@'Moves in a straight line: t itself.'
  t)

(func cubic-in ((unit t))
  doc@'Starts slowly and speeds up: t cubed.'
  (* t t t))
(func cubic-out ((unit t))
  doc@'Starts fast and slows down to a stop.'
  (- 1 (cubic-in (- 1 t))))
(func cubic-in-out ((unit t))
  doc@'Starts slowly, speeds up, and slows down to a stop.'
  (if (< t 0.5) (/ (cubic-in (min 1 (* 2 t))) 2) (/ (+ 1 (cubic-out (max 0 (- (* 2 t) 1)))) 2)))

(func spring-out ((unit t))
  doc@'Like a spring released from rest: past the end once, then settling there.'
  (- 1 (* (^ (- 1 t) 3) (+ (cos (* 8 t)) (* 0.375 (sin (* 8 t)))))))
(func spring-in ((unit t))
  doc@'spring-out turned around: the spring is at the start.'
  (- 1 (spring-out (- 1 t))))
(func spring-in-out ((unit t))
  doc@'spring-in over the first half and spring-out over the second.'
  (if (< t 0.5) (/ (spring-in (min 1 (* 2 t))) 2) (/ (+ 1 (spring-out (max 0 (- (* 2 t) 1)))) 2)))

(func bounce-out ((unit t))
  doc@'Like a ball landing: three bounces, each smaller, before it rests.'
  (cond ((< t (/ 1 2.75)) (* 7.5625 t t))
        ((< t (/ 2 2.75)) (+ (* 7.5625 (- t (/ 1.5 2.75)) (- t (/ 1.5 2.75))) 0.75))
        ((< t (/ 2.5 2.75)) (+ (* 7.5625 (- t (/ 2.25 2.75)) (- t (/ 2.25 2.75))) 0.9375))
        (else (+ (* 7.5625 (- t (/ 2.625 2.75)) (- t (/ 2.625 2.75))) 0.984375))))
(func bounce-in ((unit t))
  doc@'bounce-out turned around: the bounces are at the start.'
  (- 1 (bounce-out (- 1 t))))
(func bounce-in-out ((unit t))
  doc@'bounce-in over the first half and bounce-out over the second.'
  (if (< t 0.5)
      (/ (bounce-in (min 1 (* 2 t))) 2)
    (/ (+ 1 (bounce-out (max 0 (- (* 2 t) 1)))) 2)))

(func elastic-out ((unit t))
  doc@'Like a plucked string: past the end and back, each swing smaller.'
  (cond ((<= t 0) 0)
        ((>= t 1) 1)
        (else (+ 1 (* (^ 2 (* -10 t)) (sin (* (- (* 10 t) 0.75) (/ (* 2 pi) 3))))))))
(func elastic-in ((unit t))
  doc@'elastic-out turned around: the swings are at the start.'
  (- 1 (elastic-out (- 1 t))))
(func elastic-in-out ((unit t))
  doc@'elastic-in over the first half and elastic-out over the second.'
  (if (< t 0.5) (/ (elastic-in (min 1 (* 2 t))) 2) (/ (+ 1 (elastic-out (max 0 (- (* 2 t) 1)))) 2)))

(func back-out ((unit t))
  doc@'Past the end by about 10% and back.'
  (let ((u (- t 1)))
    (+ 1 (* 2.70158 u u u) (* 1.70158 u u))))
(func back-in ((unit t))
  doc@'back-out turned around: back by about 10% before it moves on.'
  (- 1 (back-out (- 1 t))))
(func back-in-out ((unit t))
  doc@'back-in over the first half and back-out over the second.'
  (if (< t 0.5)
      (/ (back-in (min 1 (* 2 t))) 2)
    (/ (+ 1 (back-out (max 0 (- (* 2 t) 1)))) 2)))
```
````

Each ease takes the progress t of a movement, a `unit`, and evaluates to how far along the movement
is: 0 at its start and 1 at its end. An ease whose name ends in `-out` has its effect at the end, the
one that ends in `-in` is the same turned around, `(- 1 (E (- 1 t)))`, and the one that ends in
`-in-out` runs the `-in` ease over the first half and the `-out` ease over the second. The `min` and
the `max` in each `-in-out` ease change no value: they make the range of the argument of each half
lie from 0 to 1 ({numref}`range-rules`), as the parameter of the ease requires. So
`(move k (to 1) (ease cubic-in-out))`, after `(import eases cubic-in-out)`, starts and ends slowly.

(stdlib-marks)=
### The file marks

This rule exists to give the marks that are drawn over a world model most often, each of which draws something with no arguments.

````{rule} marks-file
The file `marks` imports `ink` from the file style, and declares these motifs, whose parameters are
given here as signatures, and the function `tick-gap`:

```mtp-sig
(axes NAME
  (left:real -10) (right:real 10) (bottom:real -10) (top:real 10)
  (ticks:real|none none) (numbers:bool true)
  (stroke:color|none none) (arrows:bool false))
(grid NAME
  (left:real -10) (right:real 10) (bottom:real -10) (top:real 10)
  (step:(real (> 0)) 1)
  (stroke:color|none none) (stroke-opacity:unit 0.25))
(angle-mark NAME
  (from:real 0) (to:real 90) (r:(real (>= 0)) 22) (label:string '')
  (stroke:color|none none))
(measure NAME
  (from:point [0 0]) (to:point [1 0]) (label:string '')
  (stroke:color|none none))
```

| Motif | What it draws |
|---|---|
| `axes` | the x-axis from `left` to `right` and the y-axis from `bottom` to `top`, through `[0 0]`, with a head of kind `'dart'` at the upper end of each when `arrows` is true. With `(ticks s)`, a tick every s along each axis, counted from 0, without one at 0, each with its number beside it when `numbers` is true. Each tick is 8 pixels long, and its number 8 pixels from the axis |
| `grid` | a line across at every multiple of `step` from `bottom` to `top`, and a line up at every multiple of `step` from `left` to `right`, with the stroke opacity `stroke-opacity`. `left`, `right`, `bottom`, `top` and `step` are const |
| `angle-mark` | at its position, an arc of radius `r` from the direction `from` to the direction `to`, counterclockwise, and `label` 12 pixels outside the middle of the arc. When the angle from `from` to `to` is 90 degrees, a square with sides of 0.7 × `r` in place of the arc |
| `measure` | a line from `from` to `to` with a bar at each end, and `label` 6 pixels above the middle of the line |

Each mark draws its lines and its text in `stroke`, and in `ink` when `stroke` is `none`, with a
stroke width of 1 for `axes` and `grid` and 1.5 for the others. The ticks and the numbers of
`axes`, the whole of `angle-mark` and the label of `measure` are in groups of fixed size, so their
lengths are in pixels and keep their size when the reader zooms. `tick-gap` is declared as follows:

```mtp
(func tick-gap ((real span))
  doc@'A round spacing for the ticks of an axis span long: 1, 2 or 5 times a power of ten,
giving about five ticks.'
  (let ((raw (/ span 5))
        (p (^ 10 (floor (log raw 10)))))
    (first {p (* 2 p) (* 5 p) (* 10 p)} (fn ((real s)) (>= s raw)))))
```
````

Each motif also takes the arguments of every shape declared with a motif, such as `x`, `y` and
`defaults` ({doc}`world-model`). So `(axes_ (ticks 1))` and `(grid_ (step 2))` in a scene, after
`(import marks axes grid)`, draw the axes with a tick at every whole number and a grid with a line
every 2.

(stdlib-math)=
### The file math

This rule exists to give the functions on numbers that can be written in mtp.

````{rule} math-file
The file `math` holds exactly these declarations:

```mtp
(func clamped ((real x) (real lo) (real hi))
  doc@'x, kept between lo and hi.'
  (min hi (max lo x)))

(func smoothstep ((real a) (real b) (real x))
  doc@'0 up to a, 1 from b on, and a smooth S between, flat at both ends. none when a is b.'
  (let ((t (clamped (/ (- x a) (- b a)) 0 1)))
    (* t t (- 3 (* 2 t)))))

(func mean ((list[real] xs))
  doc@'The mean of the items of a list, and none for an empty list.'
  (/ (sum xs) (count xs)))

(func sigmoid ((real x))
  doc@'The logistic curve: 1 / (1 + e^−x), from 0 far left to 1 far right, 1/2 at 0.'
  (/ 1 (+ 1 (exp (- x)))))

(func rescaled ((real x) (real a) (real b) (real c) (real d))
  doc@'x moved from the interval a to b onto the interval c to d, in proportion: a gives c and b
gives d. none when a is b.'
  (+ c (* (- d c) (/ (- x a) (- b a)))))

(func[int] factorial ((int n (>= 0)))
  doc@'n! = 1 · 2 · … · n, and 0! = 1.'
  (reduce (range 1 (+ n 1)) 1 (fn ((int p) (int k)) (* p k))))

(func[int] binomial ((int n (>= 0)) (int k (>= 0)))
  doc@'The number of ways to choose k things out of n, n! / (k! (n − k)!), and 0 when k is above n.'
  (if (> k n) 0 (/ (factorial n) (* (factorial k) (factorial (- n k))))))

(func[int] gcd ((int a) (int b))
  doc@'The greatest common divisor of a and b, by Euclid\'s algorithm. (gcd 0 0) is 0.'
  (if (= b 0) (abs a) (gcd b (mod a b))))
```
````

(stdlib-geometry)=
### The file geometry

This rule exists to give the functions on points, segments and circles that figures use most.

````{rule} geometry-file
The file `geometry` holds exactly these declarations:

```mtp
(import math clamped)

(interface segment (point from) (point to))
(interface sized (real width) (real height))

(func dot ((point a) (point b))
  doc@'The dot product of two points read as vectors.'
  (+ (* a.x b.x) (* a.y b.y)))

(func cross ((point a) (point b))
  doc@'The 2D cross product, the signed area of the parallelogram: positive when b turns left of a.'
  (- (* a.x b.y) (* a.y b.x)))

(func normalized ((point p))
  doc@'The point in the same direction as p at distance 1, and none for [0 0].'
  (* p (/ 1 p.mod)))

(func midpoint ((point a) (point b))
  doc@'The point halfway between a and b.'
  (* (+ a b) 0.5))

(func line-meet ((segment a) (segment b))
  doc@'Where the lines through a and b meet, and none when they are parallel.'
  (let ((r (- a.to a.from))
        (s (- b.to b.from)))
    (+ a.from (* (/ (cross (- b.from a.from) s) (cross r s)) r))))

(func line-circle-meet ((segment a) (circle c))
  doc@'Where the line through a meets the circle c: two points, the same point twice when the
line touches it, and none when it misses.'
  (let ((d (- a.to a.from))
        (f (- a.from [c.x c.y]))
        (k (/ (dot f d) (dot d d)))
        (h (sqrt (- (* k k) (/ (- (dot f f) (* c.r c.r)) (dot d d))))))
    (somes {(+ a.from (* (- (- k) h) d))
            (+ a.from (* (+ (- k) h) d))})))

(func circle-meet ((circle c) (circle d))
  doc@'Where the circles c and d meet: two points, the same point twice when they touch, and
none when they do not meet or share a center.'
  (let ((p [c.x c.y])
        (q [d.x d.y])
        (n (dist p q))
        (a (/ (+ (- (* c.r c.r) (* d.r d.r)) (* n n)) (* 2 n)))
        (h (sqrt (- (* c.r c.r) (* a a))))
        (m (+ p (* (/ a n) (- q p))))
        (u (* (/ 1 n) [(- (- q.y p.y)) (- q.x p.x)])))
    (somes {(+ m (* h u)) (- m (* h u))})))

(func projection ((point p) (segment a))
  doc@'The point of the line through a nearest to p, and none when a has no length.'
  (let ((d (- a.to a.from)))
    (+ a.from (* (/ (dot (- p a.from) d) (dot d d)) d))))

(func angle-bisector ((point p) (point vertex) (point q))
  doc@'The segment from vertex that halves the angle from p to q, as long as the shorter arm.'
  (let ((u (- p vertex))
        (v (- q vertex))
        (w (normalized (+ (normalized u) (normalized v)))))
    (rec (point from vertex)
         (point to (+ vertex (* (min u.mod v.mod) w))))))

(func circumcenter ((point p) (point q) (point r))
  doc@'The center of the circle through p, q and r, and none when the three lie on one line.'
  (let ((d (* 2 (+ (* p.x (- q.y r.y)) (* q.x (- r.y p.y)) (* r.x (- p.y q.y)))))
        (sp (dot p p)) (sq (dot q q)) (sr (dot r r)))
    [(/ (+ (* sp (- q.y r.y)) (* sq (- r.y p.y)) (* sr (- p.y q.y))) d)
     (/ (+ (* sp (- r.x q.x)) (* sq (- p.x r.x)) (* sr (- q.x p.x))) d)]))

(func nearest-point-on-segment ((point p) (segment a))
  doc@'The point of the segment a nearest to p: its projection onto the line through a, kept
between the two ends. none when a has no length.'
  (let ((d (- a.to a.from))
        (t (clamped (/ (dot (- p a.from) d) (dot d d)) 0 1)))
    (+ a.from (* t d))))

(func has-point? ((list[point] ps) (point p))
  doc@'Whether p is one of the points of ps, as on a grid: points are equal only when both of their
numbers are.'
  (any (map ps (fn ((point q)) (= q p)))))
```
````

A point has the attributes `x`, `y`, `mod` and `arg`, so the distance of a point `p` from `[0 0]` is
`p.mod` and its angle is `p.arg` ({doc}`data-model`). Each function that divides by a number that
can be 0, such as the cross product of two parallel segments in `line-meet`, evaluates to `none`
there ({numref}`expressions-that-give-none`).

(stdlib-text)=
### The file text

This rule exists to give the functions that write numbers in the subscript and superscript digits of plain text, which is not typeset.

````{rule} text-file
The file `text` holds exactly these declarations:

```mtp
(list[string] subscript-digits {'₀' '₁' '₂' '₃' '₄' '₅' '₆' '₇' '₈' '₉'} (const))

(func[string] subscript ((int n))
  doc@'n written in subscript digits, as the index in C₁₂, with a minus sign before a negative n.'
  (cond ((< n 0) (concat '₋' (subscript (- n))))
        ((< n 10) (or? subscript-digits[n] ''))
        (else (concat (subscript (floor (/ n 10))) (subscript (mod n 10))))))

(list[string] superscript-digits {'⁰' '¹' '²' '³' '⁴' '⁵' '⁶' '⁷' '⁸' '⁹'} (const))

(func[string] superscript ((int n))
  doc@'n written in superscript digits, as the power in x², with a minus sign before a negative n.'
  (cond ((< n 0) (concat '⁻' (superscript (- n))))
        ((< n 10) (or? superscript-digits[n] ''))
        (else (concat (superscript (floor (/ n 10))) (superscript (mod n 10))))))
```
````

So `(subscript 12)` is `'₁₂'`, and `f'x{(superscript 2)}'` is `'x²'`.

(stdlib-animations)=
### The file animations

This rule exists to give the animations that figures use most, each played on a shape.

````{rule} animations-file
The file `animations` holds exactly these declarations:

```mtp
(animation fade-in ((shape s) (real duration 0.4))
  doc@'s comes into view: its opacity goes from 0 to 1.'
  (move s.opacity (from 0) (to 1) (duration duration)))

(animation fade-out ((shape s) (real duration 0.4))
  doc@'s goes out of view: its opacity goes to 0.'
  (move s.opacity (to 0) (duration duration)))

(animation draw-on ((shape s) (real duration 0.8))
  doc@'s is drawn along its outline from its start, as if by a pen.'
  (move s.drawn (from 0) (to 1) (duration duration)))

(animation pulse ((shape s) (real size 1.2) (real duration 0.5))
  doc@'s grows to size and back, once, to draw the eye to it.'
  (in-order
    (at-once (move s.scale-x (to size) (duration (/ duration 2)))
             (move s.scale-y (to size) (duration (/ duration 2))))
    (at-once (move s.scale-x (to 1) (duration (/ duration 2)))
             (move s.scale-y (to 1) (duration (/ duration 2))))))
```
````

So `(button show (fade-in c))`, after `(import animations fade-in)`, plays a movement that makes the
shape `c` come into view over 0.4 seconds.

:::{admonition} Code differs
:class: note
The compiler reads the files of mathterpiece/stdlib: colors, ease, fonts, marks, math, rand and
types, which differ from the files above. It has no files style, eases, geometry, text and
animations. Beads mtp-6kta, mtp-vc5g and mtp-08wd.12.
:::

(stdlib-rand)=
### The file rand

This rule exists because random functions need a seed and a site that the compiler provides, so the file rand cannot be written in mtp.

```{rule} rand-module
The file `rand` of the {term}`standard library` has no .mtp file: the compiler provides its names,
and `(import rand …)` makes them usable in the same way as the names of any other file
({doc}`imports`). The file rand has these names, and only these:

| Name | What it is |
|---|---|
| `rand`, `rand-int`, `choice`, `shuffled`, `next-seed` | the random functions ({numref}`random-signatures`), which the compiler implements |
| `seed` | the {term}`seed` that a file with no seed of its own uses ({numref}`default-seed`), as if declared `(rand-seed seed 0)` |
| `dice-roll` | an animation, as if declared `(animation dice-roll ((rand-seed s)) (jump s (next-seed s)))`: each `dice-roll` writes the next value of the seed `s` to `s` at once. In a `(dice-roll)` with no argument, `s` is the {term}`default seed` of the file that holds the `(dice-roll)` |
```

This rule exists to give the arguments, the result type and the range of each random function.

````{rule} random-signatures
```mtp-sig
(rand LO:real? HI:real? (seed:rand-seed|none none))
(rand-int LO:int HI:int (seed:rand-seed|none none))
(choice XS:list[T] (seed:rand-seed|none none))
(shuffled XS:list[T] (seed:rand-seed|none none))
(next-seed S:rand-seed)
```

| Call | Its value ({numref}`random-values`) | Result type | Range |
|---|---|---|---|
| `(rand LO HI)` | a real from LO up to HI, and from 0 up to 1 when both are left out | `real` | from LO to HI when both are known in the prove step, from 0 to 1 when both are left out, and otherwise the whole number limit |
| `(rand-int LO HI)` | an int from LO to HI, both included | `int` | from LO to HI when both are known in the prove step, and otherwise the whole number limit |
| `(choice XS)` | one item of XS | `T` | the range of the items of XS |
| `(shuffled XS)` | the items of XS in a new order | `list[T]` | |
| `(next-seed S)` | the value that a roll writes to the seed S | `rand-seed` | its type |

`rand` takes either both LO and HI or neither. A call with no `(seed …)` uses the default seed of
its file ({numref}`default-seed`).
````

This rule exists so that each use of a random function is a call with a site of its own.

```{rule} random-calls
A name that refers to a random function may be written only as the head of a call, and anywhere else
is a compile error, "N is only called, as (N …)".
```

Each call of `rand`, `rand-int`, `choice` or `shuffled` has a {term}`site` of its own
({numref}`random-site`), so a random function is never a value. For example, after
`(import rand rand)`, `(map xs rand)` is a compile error.

:::{admonition} Code differs
:class: note
The compiler reads the file rand from `mathterpiece/stdlib/rand.mtp`, in which each random
function is declared with a form `(primitive N)` that only a file of the standard library may hold,
and it names `choice`, `shuffled` and `dice-roll` `pick`, `shuffle` and `roll-dice`. Beads mtp-o3cc
and mtp-ydd4.7.89 make the compiler provide the names, and remove that form.
:::

So `(import rand rand-int dice-roll)` makes the names `rand-int` and `dice-roll` usable, and
`(import rand)` makes `rand.rand-int`, `rand.dice-roll` and the others usable ({doc}`imports`).
`(dice-roll s)` creates a `dice-roll`, which is a movement ({ref}`animation-uses`) of one step: a
write of `(next-seed s)` to the seed `s`.

```mtp
(import rand rand-int dice-roll)
(scene table (circle die (r (rand-int 1 6))))
(canvas v (x -6) (y -6) (width 12) (height 12) table)
(button roll (dice-roll) (label 'roll'))
```

Here the source declares no seed, so `(rand-int 1 6)` uses the seed `seed` of the file rand, which
starts at 0, and the button `roll` writes the next value of that seed to it.
