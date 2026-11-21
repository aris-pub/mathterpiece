(data-model)=
# Data model

This page defines the things that the compiler builds from a source and that the runtime holds in
memory and manipulates: values, variables and attributes. A {term}`value` is a
{term}`primitive` or an {term}`object`. Variables and attributes are
{term}`containers <container>`: each holds one value.
What the parser reads, {term}`literals <literal>` among it, is defined in {doc}`grammar`. This page
specifies the language.

<figure class="mtp-diagram" style="max-width: 37rem">
<svg viewBox="0 0 590 508" role="img" aria-labelledby="mtp-dm-title"><title id="mtp-dm-title">Three columns: text in the source, values in the compiler or runtime, and containers in the compiler or runtime. Literals and some compounds give primitives. Declarations and other compounds give objects. Type declarations and names of types give types, which are held in the compiler only. A primitive never changes and has no identity. An object has an identity and attributes, each a container. A type is a set of values, known when compiling. A container is a variable or an attribute, holds one value, and is free, bound or const.</title><defs><marker id="mtp-dm-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="mtp-d-headpath" d="M0 0 L10 5 L0 10 z"/></marker></defs><text class="mtp-d-label" x="105" y="16" text-anchor="middle">text in the source</text><text class="mtp-d-label" x="315" y="16" text-anchor="middle">values in the</text><text class="mtp-d-label" x="315" y="30" text-anchor="middle">compiler or runtime</text><text class="mtp-d-label" x="500" y="16" text-anchor="middle">containers in the</text><text class="mtp-d-label" x="500" y="30" text-anchor="middle">compiler or runtime</text><g transform="translate(0,16)"><rect class="mtp-d-file" x="15" y="34" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="58" text-anchor="middle">literals</text><text class="mtp-d-code" x="105" y="80" text-anchor="middle">3  'hi'  [1 2]</text><line class="mtp-d-arrow" x1="195" y1="69" x2="243" y2="69" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="118" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="142" text-anchor="middle">compounds</text><text class="mtp-d-code" x="105" y="164" text-anchor="middle">(+ 1 2)  (sqrt 2)</text><line class="mtp-d-arrow" x1="195" y1="153" x2="243" y2="153" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="222" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="246" text-anchor="middle">declarations</text><text class="mtp-d-code" x="105" y="268" text-anchor="middle">(circle c …)</text><text class="mtp-d-code" x="105" y="284" text-anchor="middle">(func f …)</text><line class="mtp-d-arrow" x1="195" y1="257" x2="243" y2="257" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="306" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="330" text-anchor="middle">compounds</text><text class="mtp-d-code" x="105" y="352" text-anchor="middle">(if f a b)</text><text class="mtp-d-code" x="105" y="368" text-anchor="middle">(fn …)  (rec …)</text><line class="mtp-d-arrow" x1="195" y1="341" x2="243" y2="341" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="410" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="434" text-anchor="middle">types</text><text class="mtp-d-code" x="105" y="456" text-anchor="middle">(type t …)</text><text class="mtp-d-code" x="105" y="472" text-anchor="middle">real|none</text><line class="mtp-d-arrow" x1="195" y1="445" x2="243" y2="445" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-part" x="245" y="34" width="140" height="154" rx="6"/><text class="mtp-d-name" x="315" y="96" text-anchor="middle">primitive</text><text class="mtp-d-sub" x="315" y="118" text-anchor="middle">never changes,</text><text class="mtp-d-sub" x="315" y="134" text-anchor="middle">has no identity</text><rect class="mtp-d-part" x="245" y="222" width="140" height="154" rx="6"/><text class="mtp-d-name" x="315" y="276" text-anchor="middle">object</text><text class="mtp-d-sub" x="315" y="298" text-anchor="middle">has an identity</text><text class="mtp-d-sub" x="315" y="314" text-anchor="middle">and attributes,</text><text class="mtp-d-sub" x="315" y="330" text-anchor="middle">each a container</text><text class="mtp-d-label" x="315" y="402" text-anchor="middle">types in the compiler</text><rect class="mtp-d-part" x="245" y="410" width="140" height="70" rx="6"/><text class="mtp-d-name" x="315" y="434" text-anchor="middle">type</text><text class="mtp-d-sub" x="315" y="454" text-anchor="middle">a set of values,</text><text class="mtp-d-sub" x="315" y="470" text-anchor="middle">known when compiling</text><rect class="mtp-d-part" x="425" y="155" width="150" height="104" rx="6"/><text class="mtp-d-name" x="500" y="179" text-anchor="middle">container</text><text class="mtp-d-sub" x="500" y="199" text-anchor="middle">a variable or</text><text class="mtp-d-sub" x="500" y="215" text-anchor="middle">an attribute</text><text class="mtp-d-sub" x="500" y="242" text-anchor="middle">free, bound or const</text><line class="mtp-d-arrow" x1="425" y1="182" x2="387" y2="140" marker-end="url(#mtp-dm-head)"/><line class="mtp-d-arrow" x1="425" y1="228" x2="387" y2="270" marker-end="url(#mtp-dm-head)"/><text class="mtp-d-label" x="500" y="145" text-anchor="middle">holds one</text></g></svg>
</figure>

An {term}`expression` is a literal, a name or a {term}`form`. A form is a head and its items in
parentheses, and each form is a {term}`compound`, a declaration or a {term}`clause`.

A literal evaluates to a primitive. A name refers to a type, a variable, an object or an attribute,
and evaluates to what it refers to. A {term}`broadened type`, such as `real|none`, is a name of a
type.

A compound evaluates to a primitive, a type, an object or an attribute. An object or attribute that
it gives already exists, except with the heads `fn`, `rec` and `move`: each of these gives a new
object, and every attribute of that object is const or bound, never free, so no writer can write it
({numref}`functions`, {numref}`records`). So evaluating a compound never writes a variable or an
attribute, and never creates a variable or an object that a writer can write.

A declaration creates something new in the model: a variable, a type or an object.

A clause, such as a named argument, the guard of a control, or `exists-when` in a scene or a
formula, is part of the form around it and has no result of its own.

The arguments of a form are literals, names or compounds, and the items of a body are
declarations. A `let` is a compound where it holds a literal, a name or a compound, and a
declaration where it holds declarations. A `foreach` holds declarations and is always a
declaration. An `import` declares the names that it brings in.

## Primitives

```{rule} values
A primitive is a value that never changes and has no identity: two primitives that are
equal are the same value. The primitives are the numbers, the bools, the strings, the colors,
the points, the lists and `none`. A primitive comes from a literal
({numref}`literal-types`) or from another expression.
```

Each of these gives a primitive:

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

Every primitive can be written as a literal. Since a primitive never
changes, nothing writes one: a writer writes a variable or an attribute, which then holds a
different value. A slider that writes `(real a 1)` puts 2 into `a`, and 1 is still 1.

## Variables

```{rule} variables
A variable is a named holder of one value. It is free, bound or const. A free variable holds its
value until a writer writes a new one. A bound variable holds the value of its expression at all
times. A const variable rejects every attempted write. A variable with no name is a
{term}`compile error`.
```

For example:

| Declared | What the variable is |
|---|---|
| `(real a 1)` | free: it holds 1 when the page opens, and a slider or a movement may write it |
| `(real b (* 2 a))` | bound: it always holds twice the value of `a`, and follows `a` when `a` changes |
| `(real c 3 (const))` | const: it holds 3, and a slider that writes it is a compile error |
| `(real_ 1)` | a compile error: a variable has a name |

`(var NAME TYPE DEFAULT)` declares a variable that holds an object, with its declared type after its
name: `(var sel shape c)` holds a shape, at first the circle `c`. A variable is not an object: it
has no attributes, only what it holds.

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
An object is a value that has an identity and attributes. Each attribute behaves like a variable:
it holds one value, and it is free, bound or const. An object stays the same object while the
values of its attributes change. Every object has the const attribute `name`: the string of its
name, or `none` when it has none. The behavior of an object is what the compiler and the runtime
do with it beyond holding its attributes, and it depends on the kind of object:

| Object | Behavior |
|---|---|
| the scene and its shapes | drawn |
| formulas and their terms | typeset |
| views | laid out on the page |
| controls and listeners | trigger movements, when the reader acts |
| movements | executed: the runtime writes their targets over time |
| functions | called |
| records | none |
```

:::{admonition} Code differs
:class: note
The compiler calls a movement a transition, declared with `(transition t TARGET …)`. Bead mtp-kir3
renames it. The compiler calls the template of movements a choreo, declared with
`(choreo …)`, its `(animation …)` is a collection of moves, and `(in-order …)` and `(at-once …)` are
only items inside an animation. Bead mtp-cg47. There is no `score` and no `lag`: bead mtp-idcs.
:::

:::{admonition} Code differs
:class: note
Only shapes have the attribute `name` (`c.name` is `'c'`): `f.name` of a function `f` is the error
"a func[real real] has no attribute 'name'". Bead mtp-teu1 gives every object `name`.
:::

<figure class="mtp-diagram">
<svg viewBox="0 0 480 410" role="img" aria-labelledby="mtp-dm2-title"><title id="mtp-dm2-title">The kinds of object: the scene, which holds shapes and groups, some of a motif or variant type, and is drawn; formulas, which hold terms and are typeset; movements, which are moves, scores, or of an animation type, and are executed when triggered; records, which have only attributes; components, which are views, controls and listeners on the page; and functions, which are called.</title><rect class="mtp-d-part" x="15" y="16" width="250" height="156" rx="6"/><text class="mtp-d-name" x="140" y="38" text-anchor="middle">the scene</text><rect class="mtp-d-file" x="30" y="50" width="220" height="84" rx="6"/><text class="mtp-d-name" x="140" y="72" text-anchor="middle">shapes and groups</text><rect class="mtp-d-part" x="45" y="86" width="190" height="36" rx="6"/><text class="mtp-d-sub" x="140" y="109" text-anchor="middle">of a motif or variant type</text><text class="mtp-d-sub" x="140" y="156" text-anchor="middle">drawn</text><rect class="mtp-d-part" x="280" y="16" width="185" height="156" rx="6"/><text class="mtp-d-name" x="372" y="38" text-anchor="middle">a formula</text><rect class="mtp-d-file" x="300" y="50" width="145" height="44" rx="6"/><text class="mtp-d-name" x="372" y="77" text-anchor="middle">terms</text><text class="mtp-d-sub" x="372" y="156" text-anchor="middle">typeset</text><rect class="mtp-d-part" x="15" y="188" width="250" height="112" rx="6"/><text class="mtp-d-name" x="140" y="210" text-anchor="middle">movements</text><rect class="mtp-d-file" x="30" y="222" width="220" height="48" rx="6"/><text class="mtp-d-sub" x="140" y="242" text-anchor="middle">moves, scores,</text><text class="mtp-d-sub" x="140" y="259" text-anchor="middle">or of an animation type</text><text class="mtp-d-sub" x="140" y="288" text-anchor="middle">executed when triggered</text><rect class="mtp-d-part" x="280" y="188" width="185" height="112" rx="6"/><text class="mtp-d-name" x="372" y="210" text-anchor="middle">records</text><text class="mtp-d-sub" x="372" y="240" text-anchor="middle">attributes only</text><rect class="mtp-d-part" x="15" y="316" width="300" height="80" rx="6"/><text class="mtp-d-name" x="165" y="340" text-anchor="middle">components</text><text class="mtp-d-sub" x="165" y="362" text-anchor="middle">views, controls and listeners, on the page:</text><text class="mtp-d-sub" x="165" y="380" text-anchor="middle">controls and listeners trigger movements</text><rect class="mtp-d-part" x="330" y="316" width="135" height="80" rx="6"/><text class="mtp-d-name" x="397" y="340" text-anchor="middle">functions</text><text class="mtp-d-sub" x="397" y="366" text-anchor="middle">called</text></svg>
</figure>

The objects are the scene and its shapes, the movements, the formulas and
their terms, the components (views, controls and listeners), the functions and the records. A shape whose
type is a motif or a variant is a shape like any other: only its type differs. A score is a
movement that holds movements, as a group is a shape that holds shapes: each member places itself
in time by its own `lag`, the fraction of the member before it that has run when it starts, as each
member of a group places itself in space by its own position. `(in-order …)` is a score whose
members have the lag 1, so each starts when the one before it ends, and `(at-once …)` is one whose
members have the lag 0, so all start together. An animation is a template of movements, as
a motif is a template of shapes: each use of an animation is a movement of the animation's type. For example, in

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

A shape's frame, which places it in its collection, is not a value of its own: it is a set of the
shape's attributes with a joint meaning, `shift-x`, `shift-y`, `rotate`, `scale-x` and `scale-y`,
as `pos` is the joint meaning of `x` and `y`; `shift` is the joint meaning of `shift-x` and
`shift-y` in the same way. Each is free, bound or const on its own, so a slider
may write `c.rotate` while `c.shift-x` follows an expression. There is no transform value. A frame
is reused through a group, whose frame applies to every member, through `(defaults …)`, or through
`(like …)`.

:::{admonition} Code differs
:class: note
The compiler has a type `transform`, whose values come from calls such as `(rotate 30)`, and a
shape gives its frame with `(translate …)` and `(transform …)`. Bead mtp-1vyc makes the frame a set
of attributes.
:::

## Identity

```{rule} identity
Two primitives are the same value exactly when they are equal. An object is the same object only as
itself: each declaration, each copy that a `foreach` makes of a declaration, and each evaluation of
`(fn …)`, `(rec …)` or `(move …)` creates an object of its own, and two objects created apart are
two objects, however alike their attributes.
```

So `[1 2]` written twice is one primitive, while `(circle c (r 1))` and `(circle d (r 1))` are two
objects, and so are the copies `c-0` and `c-1` of `(foreach k 2 (circle @'c-{k}' (r 1)))`.

A source usually works with an object through its attributes, as `c.r` or `style.width`, and with a
primitive by itself, as `3` or `'hi'`. A primitive may have attributes too: a point has `x` and `y`, a
color its channels `r`, `g`, `b` and `a`, a list and a string a `length`, and a complex number `re`
and `im`. Reading an attribute of a primitive gives a primitive. Writing one puts a new value into the
variable or the attribute that holds it, and the old value does not change.

## Functions

```{rule} functions
A function is an object whose only attribute is `name`, and whose behavior is to be called.
`(func f …)` declares a function, and `(fn …)` gives a new function each time that it is evaluated.
```

So `(func twice ((real x)) (* 2 x))` declares the function `twice`, whose `name` is `'twice'`, and
`(map xs (fn ((real x)) (* 2 x)))` passes a function with no name to `map`. A variable holds a
function as it holds any object: `(var f function twice)`. Since a function has no attribute that a writer
may write, a new function made each time that `(fn …)` is evaluated loses nothing.

:::{admonition} Code differs
:class: note
The compiler treats functions as primitives: no variable may hold one (bead mtp-wppk), and `(= f g)`
on two functions compiles, with no result given by the spec.
:::

## Records

```{rule} records
A record is an object that consists only of the attributes that it is declared with.
`(record n …)` declares a record, and `(rec …)` gives a new record each time that it is
evaluated. Every attribute of a record that `(rec …)` gives is bound or const.
```

A font is a record: `(font serif (family 'serif') (style 'normal') (weight 400) (size 12))`
declares a record with the four attributes `family`, `style`, `weight` and `size`. A text applies
it with `(face serif)`, and writing `serif.size` changes the size of every text that applies
`serif`.

:::{admonition} Code differs
:class: note
The compiler treats a font as a primitive: its parts can be read, as `f.size`, but not written, and a
text applies one with `(font f)`. Bead mtp-1vyc makes fonts namespaces.
:::

For example, `(record style (real width 2 (>= 0) (<= 5)) (color ink #'navy'))` is an object with
the two attributes `width` and `ink`, read as `style.width` and `style.ink`. Like any attribute,
`style.width` may be written: `(slider s (move style.width (from 0) (to 5)))` writes it. Unlike a
shape, a record is not drawn, and the compiler does nothing with it beyond holding its
attributes.

`(rec …)` is to `(record …)` as `(fn …)` is to `(func …)`. Since every attribute of a record
that `(rec …)` gives is bound or const, no writer writes it, and a new record made each time that
`(rec …)` is evaluated loses nothing. So `(var s record (rec (real height k)))` holds a record
whose `height` follows `k`, and `(var s record (rec (real width 1)))` is a compile error, since
`width` is free.

:::{admonition} Code differs
:class: note
The compiler calls a record a namespace, declared with `(namespace n …)`, and no expression gives
one. Bead mtp-h732 renames it and adds `(rec …)`.
:::
