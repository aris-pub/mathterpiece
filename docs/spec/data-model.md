(data-model)=
# Data model

This page defines the things that the compiler builds from a source and that the runtime holds:
values, variables, objects and namespaces. What the parser reads, {term}`literals <literal>`
among it, is defined in {doc}`grammar`. This page specifies the language.

<figure class="mtp-diagram" style="max-width: 35rem">
<svg viewBox="0 0 560 392" role="img" aria-labelledby="mtp-dm-title"><title id="mtp-dm-title">Three columns. In the source: a literal and other expressions give values; declarations and some expressions give objects. A value never changes and has no identity. An object has an identity and attributes, each like a variable. A variable holds one value or one object, and is free, bound or const.</title><defs><marker id="mtp-dm-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="mtp-d-headpath" d="M0 0 L10 5 L0 10 z"/></marker></defs><text class="mtp-d-label" x="90" y="20" text-anchor="middle">in the source</text><text class="mtp-d-label" x="280" y="20" text-anchor="middle">what it gives</text><text class="mtp-d-label" x="470" y="20" text-anchor="middle">what holds it</text><rect class="mtp-d-file" x="15" y="34" width="150" height="70" rx="6"/><text class="mtp-d-name" x="90" y="58" text-anchor="middle">literal</text><text class="mtp-d-code" x="90" y="80" text-anchor="middle">3  'hi'  [1 2]</text><line class="mtp-d-arrow" x1="165" y1="69" x2="213" y2="69" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="118" width="150" height="70" rx="6"/><text class="mtp-d-name" x="90" y="142" text-anchor="middle">expressions</text><text class="mtp-d-code" x="90" y="164" text-anchor="middle">(+ 1 2)  (sqrt 2)</text><line class="mtp-d-arrow" x1="165" y1="153" x2="213" y2="153" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="222" width="150" height="70" rx="6"/><text class="mtp-d-name" x="90" y="246" text-anchor="middle">declarations</text><text class="mtp-d-code" x="90" y="268" text-anchor="middle">(circle c …)</text><text class="mtp-d-code" x="90" y="284" text-anchor="middle">(func f …)</text><line class="mtp-d-arrow" x1="165" y1="257" x2="213" y2="257" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="306" width="150" height="70" rx="6"/><text class="mtp-d-name" x="90" y="330" text-anchor="middle">expressions</text><text class="mtp-d-code" x="90" y="352" text-anchor="middle">(if f a b)  g[0]</text><text class="mtp-d-code" x="90" y="368" text-anchor="middle">(fn …)  (ns …)</text><line class="mtp-d-arrow" x1="165" y1="341" x2="213" y2="341" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-part" x="215" y="34" width="130" height="154" rx="6"/><text class="mtp-d-name" x="280" y="96" text-anchor="middle">value</text><text class="mtp-d-sub" x="280" y="118" text-anchor="middle">never changes,</text><text class="mtp-d-sub" x="280" y="134" text-anchor="middle">has no identity</text><rect class="mtp-d-part" x="215" y="222" width="130" height="154" rx="6"/><text class="mtp-d-name" x="280" y="276" text-anchor="middle">object</text><text class="mtp-d-sub" x="280" y="298" text-anchor="middle">has an identity</text><text class="mtp-d-sub" x="280" y="314" text-anchor="middle">and attributes, each</text><text class="mtp-d-sub" x="280" y="330" text-anchor="middle">like a variable</text><rect class="mtp-d-part" x="395" y="160" width="150" height="90" rx="6"/><text class="mtp-d-name" x="470" y="184" text-anchor="middle">variable</text><text class="mtp-d-code" x="470" y="206" text-anchor="middle">(real a 1)</text><text class="mtp-d-sub" x="470" y="226" text-anchor="middle">free, bound or const</text><line class="mtp-d-arrow" x1="395" y1="182" x2="347" y2="140" marker-end="url(#mtp-dm-head)"/><line class="mtp-d-arrow" x1="395" y1="228" x2="347" y2="270" marker-end="url(#mtp-dm-head)"/><text class="mtp-d-label" x="470" y="150" text-anchor="middle">holds one</text></svg>
</figure>

## Values

```{rule} values
A value is a piece of data that never changes and has no identity: two values that are equal are
the same value. The values are the numbers, the bools, the strings, the colors, the fonts, the
points, the transforms, the lists and `none`. A value comes from a literal
({numref}`literal-types`) or from another expression.
```

Each of these gives a value:

| Written | The value | Its type |
|---|---|---|
| `3` | the number 3 | `int` |
| `(+ 1 2)` | the number 3, the same value as `3` | `int` |
| `2.5` | the number 2.5 | `real` |
| `'hi'` | the string hi | `string` |
| `true` | true | `bool` |
| `[1 2 3]` | the list of 1, 2 and 3 | `list[int]` |
| `[0 1]`, where a point is expected | the point at x 0 and y 1 | `point` |
| `none` | `none` | `none` |
| `(rotate 30)` | the rotation by 30 degrees | `transform` |

Every value but a font and a transform can be written as a literal. A font comes from a `font`
declaration, and a transform from a call such as `(rotate 30)`. Since a value never
changes, nothing writes a value: a writer writes a variable or an attribute, which then holds a
different value. A slider that writes `(real a 1)` puts 2 into `a`, and 1 is still 1.

## Variables

```{rule} variables
A variable is a named holder of one value or one object. It is free, bound or const. A free variable holds its
value until a writer writes a new one. A bound variable holds the value of its expression at all
times. A const variable rejects every attempted write. A variable with no name is a
{term}`compile error`.
```

For example:

| Declared | What the variable is |
|---|---|
| `(real a 1)` | free: it holds 1 when the page opens, and a slider or a transition may write it |
| `(real b (* 2 a))` | bound: it always holds twice the value of `a`, and follows `a` when `a` changes |
| `(real c 3 (const))` | const: it holds 3, and a slider that writes it is a compile error |
| `(real_ 1)` | a compile error: a variable has a name |

A variable is not an object: it has no attributes, only what it holds.

:::{admonition} Code differs
:class: note
No variable holds an object: there is no form to declare one. Bead mtp-wppk adds it.
:::

:::{admonition} Code differs
:class: note
`(real_ 1)` compiles, and nothing can read the variable that it makes. Bead mtp-1s8z makes it a
compile error.
:::

## Objects

```{rule} objects
An object is a thing that has an identity and attributes. Each attribute behaves like a variable:
it holds one value, and it is free, bound or const. An object stays the same object while the
values of its attributes change. Every object has the const attribute `name`: the string of its
name, or `none` when it has none. The behavior of an object is what the compiler and the runtime
do with it beyond holding its attributes, and it depends on the kind of object:

| Object | Behavior |
|---|---|
| the scene and its shapes | drawn |
| formulas and their terms | typeset |
| views | laid out on the page |
| controls and listeners | trigger transitions, when the reader acts |
| transitions | executed: the runtime writes their targets over time |
| functions | called |
| namespaces | none |
```

:::{admonition} Code differs
:class: note
Only shapes have the attribute `name` (`c.name` is `'c'`): `f.name` of a function `f` is the error
"a func[real real] has no attribute 'name'". Bead mtp-teu1 gives every object `name`.
:::

<figure class="mtp-diagram">
<svg viewBox="0 0 480 410" role="img" aria-labelledby="mtp-dm2-title"><title id="mtp-dm2-title">The kinds of object: the scene, which holds shapes and groups, some of a motif or variant type, and is drawn; formulas, which hold terms and are typeset; transitions, which are moves, animations, or of a choreo type, and are executed when triggered; namespaces, which have only attributes; components, which are views, controls and listeners on the page; and functions, which are called.</title><rect class="mtp-d-part" x="15" y="16" width="250" height="156" rx="6"/><text class="mtp-d-name" x="140" y="38" text-anchor="middle">the scene</text><rect class="mtp-d-file" x="30" y="50" width="220" height="84" rx="6"/><text class="mtp-d-name" x="140" y="72" text-anchor="middle">shapes and groups</text><rect class="mtp-d-part" x="45" y="86" width="190" height="36" rx="6"/><text class="mtp-d-sub" x="140" y="109" text-anchor="middle">of a motif or variant type</text><text class="mtp-d-sub" x="140" y="156" text-anchor="middle">drawn</text><rect class="mtp-d-part" x="280" y="16" width="185" height="156" rx="6"/><text class="mtp-d-name" x="372" y="38" text-anchor="middle">a formula</text><rect class="mtp-d-file" x="300" y="50" width="145" height="44" rx="6"/><text class="mtp-d-name" x="372" y="77" text-anchor="middle">terms</text><text class="mtp-d-sub" x="372" y="156" text-anchor="middle">typeset</text><rect class="mtp-d-part" x="15" y="188" width="250" height="112" rx="6"/><text class="mtp-d-name" x="140" y="210" text-anchor="middle">transitions</text><rect class="mtp-d-file" x="30" y="222" width="220" height="48" rx="6"/><text class="mtp-d-sub" x="140" y="242" text-anchor="middle">moves, animations,</text><text class="mtp-d-sub" x="140" y="259" text-anchor="middle">or of a choreo type</text><text class="mtp-d-sub" x="140" y="288" text-anchor="middle">executed when triggered</text><rect class="mtp-d-part" x="280" y="188" width="185" height="112" rx="6"/><text class="mtp-d-name" x="372" y="210" text-anchor="middle">namespaces</text><text class="mtp-d-sub" x="372" y="240" text-anchor="middle">attributes only</text><rect class="mtp-d-part" x="15" y="316" width="300" height="80" rx="6"/><text class="mtp-d-name" x="165" y="340" text-anchor="middle">components</text><text class="mtp-d-sub" x="165" y="362" text-anchor="middle">views, controls and listeners, on the page:</text><text class="mtp-d-sub" x="165" y="380" text-anchor="middle">controls and listeners trigger transitions</text><rect class="mtp-d-part" x="330" y="316" width="135" height="80" rx="6"/><text class="mtp-d-name" x="397" y="340" text-anchor="middle">functions</text><text class="mtp-d-sub" x="397" y="366" text-anchor="middle">called</text></svg>
</figure>

The objects are the scene and its shapes, the transitions, the formulas and
their terms, the components (views, controls and listeners), the functions and the namespaces. A shape whose
type is a motif or a variant is a shape like any other: only its type differs. For example, in

```mtp
(real a 1 (>= 0) (<= 2))
(scene sc
  (circle c (r 1) (x (* 2 a)))
  (circle d (r 1) (x (* 2 a)))
  (circle_ (r 3)))
```

- `c` is an object with the attributes `r`, `x`, `y`, `fill` and the others of a circle. Its `r`
  is free, so a slider may write `c.r`, and its `x` is bound to `(* 2 a)`.
- `c` and `d` are two objects, though they are declared with the same attributes. Writing `c.r`
  leaves `d.r` as it is.
- The third circle has no name, and is an object all the same.
- `a` is a variable, not an object.
- `c.name` is the string `'c'`, and the `name` of the third circle is `none`.

## Functions

```{rule} functions
A function is an object whose only attribute is `name`, and whose behavior is to be called.
`(func f …)` declares a function, and `(fn …)` gives a new function each time that it is evaluated.
```

So `(func twice ((real x)) (* 2 x))` declares the function `twice`, whose `name` is `'twice'`, and
`(map xs (fn ((real x)) (* 2 x)))` passes a function with no name to `map`. A variable holds a
function as it holds any object: `(var f twice)`. Since a function has no attribute that a writer
may write, a new function made each time that `(fn …)` is evaluated loses nothing.

:::{admonition} Code differs
:class: note
The compiler treats functions as values: no variable may hold one (bead mtp-wppk), and `(= f g)`
on two functions compiles, with no result given by the spec.
:::

## Namespaces

```{rule} namespaces
A namespace is an object that consists only of the attributes that it is declared with.
`(namespace n …)` declares a namespace, and `(ns …)` gives a new namespace each time that it is
evaluated. Every attribute of a namespace that `(ns …)` gives is bound or const.
```

For example, `(namespace style (real width 2 (>= 0) (<= 5)) (color ink 'navy'))` is an object with
the two attributes `width` and `ink`, read as `style.width` and `style.ink`. Like any attribute,
`style.width` may be written: `(slider s (move style.width (from 0) (to 5)))` writes it. Unlike a
shape, a namespace is not drawn, and the compiler does nothing with it beyond holding its
attributes.

`(ns …)` is to `(namespace …)` as `(fn …)` is to `(func …)`. Since every attribute of a namespace
that `(ns …)` gives is bound or const, no writer writes it, and a new namespace made each time that
`(ns …)` is evaluated loses nothing. So `(var s (ns (real height k)))` holds a namespace whose
`height` follows `k`, and `(var s (ns (real width 1)))` is a compile error, since `width` is free.

:::{admonition} Code differs
:class: note
No expression gives a namespace. Bead mtp-h732 adds `(ns …)`.
:::
