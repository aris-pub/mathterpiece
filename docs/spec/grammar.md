(grammar)=
# Grammar

This page defines how the {term}`parser` puts the {term}`words <word>`, {term}`string`
{term}`literals <literal>` and other pieces of text of {doc}`lexical` together into
{term}`forms <form>`, the {term}`expressions <expression>` that the parser produces, the template
that every form follows, and the kinds of form that may be written in each {term}`body`. The
signatures of the forms, which list the arguments of each {term}`head`, are not part of this page.

This page specifies the language.

## The grammar of the parser

The rules below and the definitions of {doc}`lexical` are one grammar, [mtp.lark](https://github.com/aris-pub/mathterpiece/blob/main/docs/spec/mtp.lark). An
alternative written `a -> free` puts its result in the tree under the name `free`, and `!` before
the name of a rule keeps the quoted text of that rule in the tree.

### Files and forms

```{mtp-grammar} file
```

```{rule} top-level-forms
A source is any number of forms, with or without {term}`whitespace` and
{term}`comments <comment>` between them. Anything else at the top level of a source is an error. A
source may hold no form at all.
```

```{mtp-grammar} forms
```

An expression is one item of a source, of a form, of a {term}`list` literal or of {term}`brackets`:
a form, a list literal, a word, a string literal or a {term}`free starting value`. The first item of
a form may be a head that ends with `_` ({numref}`unnamed-head`).

```{rule} adjacent-items
Among the items of a form, a list literal or brackets, whitespace or a comment separates every two
expressions, except where one of the two is a form. More exactly, an expression that ends with the
`)` of a form, which is a form or a free starting value such as `free@(g)`, may be followed
directly by any expression that does not start with `.` or `[` ({numref}`no-name-part-after-form`),
and every other expression may be followed directly only by a form. So `(f a(b)c)` holds three
expressions after `f`, `(f (a)b)` and `(f 'x'(b))` hold two, and `(f 'a''b')` and `(f [1]x)` are
errors.
```

### Lists and brackets

```{mtp-grammar} lists
```

```{rule} lists
A list literal is written in square brackets, with its items separated as in
{numref}`adjacent-items`: `[]`, `[0 1]`, `[(f x) 'a']`. A `[` right after the `]` of a list literal
starts brackets after the list literal, which hold exactly one expression: `[a b c][h]`.
```

```{rule} name-brackets
A `[` right after a {term}`name`, with no whitespace between them, starts brackets after the name,
which hold one expression or more: `xs[0]`, `xs[(+ k 1)]`, `g['m1']`, `func[real real]`. Several
pairs of brackets may follow each other, and after brackets, `.` and more
{term}`name parts <name part>` may follow: `xs[0].pos.x`, `m[0][1]`, `a[0].b[1]`. A `[` after
whitespace starts a list literal: `xs [0]` is the name `xs` and the list literal `[0]`.
```

### Words

```{mtp-grammar} words
```

```{mtp-grammar} literals
```

```{rule} broadened-types
A {term}`broadened type` is two words or more joined by `|` with no whitespace between them, such
as `real|none`. Its words are names, names followed by brackets, numbers, {term}`bool` literals or
{term}`operators <operator>`. A broadened type is one expression, and the {term}`compiler` reads it as a
type ({doc}`types`).
```

### Heads

```{mtp-grammar} heads
```

A {token}`mtp:head` is the head of a form that has no name: a name that ends with `_`, or a
broadened type whose last word is such a name. {numref}`unnamed-head` gives its meaning.

### Strings

```{mtp-grammar} strings
```

## The expressions that the parser produces

```{rule} parser-expressions
The parser produces the forms of a source as expressions, one for each form, in the order of the
source. Each expression is one of these:

| Expression | Written | Holds |
|---|---|---|
| form | `(…)` | its items, in order |
| list literal | `[…]` | its items, in order |
| name | `p`, `p.pos.x`, `xs[0].y` | its name parts, in order. Each name part is the text of a part between dots, or what a pair of brackets holds: its one expression, or, when it holds more than one, the brackets |
| brackets | `[real real]` in `func[real real]` | its expressions, in order |
| broadened type | `real\|none` | its words, as expressions, in order |
| string literal | `'…'`, `tex'…'` | its text, and whether it is a {term}`TeX string` |
| {term}`interpolated string` | `$'…'` | its pieces: text, the expression of each `{…}` with no {term}`format spec`, and each `{…}` with a format spec |
| `{…}` with a format spec | `{x:.2f}` | the expression and the format spec |
| {term}`int`, {term}`ratio`, {term}`real` or {term}`complex` literal | `3`, `1/3`, `2.5`, `1+2i` | the value ({numref}`number-literals`) |
| bool literal | `true`, `false` | the value |
| none | `none` | nothing |

In an interpolated string, each piece of text is as long as possible, so two pieces of text are
never next to each other.
```

An operator is a name with one name part ({numref}`literal-words`).

```{rule} shorthand-forms
The parser produces each spelling on the left as the form on the right:

| Written | Is the form |
|---|---|
| `doc@'text'` | `(doc 'text')` |
| `free@X` | `(free@ X)`, whose head is the name `free@`, which no source can write as a word |
| `#'dot-{k}'` | `(name $'dot-{k}')` |
| `#'dot-{k}'.a.b` | `(. (. (name $'dot-{k}') a) b)` |
| `#'dot-{k}'[i]` | `(. (name $'dot-{k}') i)` |
| `[a b c][h]` | `(. [a b c] h)` |

The form has the position of the first character of its spelling. A `(. X Y)` that follows a name
string has the position of its `.` or `[`.
```

```{rule} unnamed-head
When the head of a form is a {token}`mtp:head`, the parser removes the `_` and puts `none` in as
the second item: `(circle_ (r 1))` is `(circle none (r 1))`, and `(marks.grid_ …)` is
`(marks.grid none …)`. When the head is a broadened type, this rule applies to its last word, so
`(line|none_ …)` is `(line|none none …)`. The head `none_` becomes the literal `none`:
`(none_ a)` is `(none none a)`.
```

The parser produces a name with several name parts, such as `p.r` or `xs[0].y`, as one name
({numref}`parser-expressions`). The rewrite step rewrites it into `(. X Y)` forms: `p.r` is
`(. p r)`, and `xs[0].y` is `(. (. xs 0) y)` ({numref}`sugar-rewrites`). The meaning of `(. X Y)`
is given in {numref}`dot-name-part`.

## The form template

```{rule} form-template
Every declaration is written `(head name? positional… option… body…)`:

- The head is the first item, and it names the kind of thing declared. It is a name
  (`circle`, `real`, `motif`, `dial`), a name followed by brackets (`list[color]`, `func[real]`), a
  broadened type (`real|none`), or a form that gives a type (`((real (>= 0)) r 1)`).
- The name, for a form that has one, is the second item ({numref}`declared-names`).
- The {term}`positional arguments <positional argument>` come next. Each kind of form has a fixed
  number of them, and some of them may be left out.
- The {term}`optional arguments <optional argument>` come next
  ({numref}`optional-arguments-first`).
- The {term}`docstring`, for a form that has one, comes next ({numref}`docstrings`).
- The body comes last: any number of items, or none. The kinds of item in a body depend on
  the form ({numref}`contexts`).

A call, a special form, a `let`, a `foreach` and an `import` follow the same template: `(+ a b c)`,
`(if c a b)`, `(import math dot)`.
```

```{rule} declared-names
The name of a declaration is a bare name with one name part, `none`, a {term}`name string` such as
`#'dot-{k}'`, or `(name s)`. The string of a name string and of `(name s)` is known when compiling.
`none` as the name means that the declaration has no name, as the head `head_` does
({numref}`unnamed-head`). A name in quotes is an error ("a name is written bare, not in quotes"),
and so is a name that {numref}`declaration-names` does not allow.
```

```{rule} forms-with-no-name
These forms have no name, so their second item is their first positional argument or their first
optional argument: a {term}`listener`, `(move …)`, an `(animation …)` inside a {term}`control` or a
listener, `(foreach …)`, `(let …)`, `(exists-when …)`, `(import …)`, `(term …)`, `(like …)`, every
optional argument, every call and every special form. A {term}`view` and a control always have a
name, because their elements on the page give it, as `<mtp-canvas name="v">`.
```

```{rule} optional-arguments-first
An optional argument is a form, after the name and the positional arguments, whose head names one
of the optional arguments that the form allows, such as `(r 1)` in `(circle c (r 1))`. In every
form, the optional arguments come before the body, in any order, except that a `(like …)` comes
before every other optional argument. An optional argument after the first item of the body is an
error, such as "(x …) is an optional argument, so
it comes before the canvas's body".
```

:::{admonition} Code differs
:class: note
The compiler checks this rule in the bodies of the scene, of groups, rows and columns, of
animations, of `at-once` and `in-order`, of canvases, of controls and of listeners. It allows the
`(defaults …)` of a formula after its other items (`compiler.py:4905`, `formula_decl`), the
`(font f)` of a readout after its listeners, and the `(kind k)` of a display after its listeners.
Bead mtp-ydd4.7.11 makes these errors.
:::

```{rule} optional-arguments-once
Each optional argument appears at most once in a form: a second one is an error, such as "'fill' is
given twice".
```

Since `(pos P)` is `(x …) (y …)` ({numref}`sugar-rewrites`), a form that gives `pos` and also `x`
or `y` gives `x` or `y` twice, and is an error. The forms that allow a `(like …)` are given in
{numref}`sugar-rewrites`.

```{rule} docstrings
Every declaration and every listener may have a docstring, `doc@'text'`, and at most one. The
docstring comes after all the positional arguments and all the optional arguments, and before the
body. In a form that has no body, the docstring is the last item. Its string literal is plain: an
interpolated string is an error.
```

So a docstring comes after the name, the positional arguments, the parameters of a function or a
motif included, and the optional arguments. A variable in the body of a motif may have one, as any
other declaration. `(real k 1 doc@'d' (>= 0))`, `(func f ((real x)) doc@'d' (* 2 x))` and
`(circle c (r 1) doc@'d')` are allowed. `(real k 1 (>= 0) doc@'d')`,
`(func f ((real x)) (* 2 x) doc@'d')`, `(circle c doc@'d' (r 1))` and
`(button b doc@'d' (animation a))` are errors.

:::{admonition} Code differs
:class: note
The compiler removes a docstring from any place after the name (`compiler.py:7322`, `_take_doc`),
so a docstring before an optional argument or after the body compiles. About 22 forms of the
examples have a docstring before an optional argument, such as a button, a play, an `on-ready` or
an `on-click` with a docstring before its `(animation …)`, and three formulas with a docstring
before their `(defaults …)`. Bead mtp-ydd4.7.34 makes these errors and moves those docstrings. A
variable in the body of a motif may not have a docstring: `(motif m () (real k 1 doc@'d') …)` is the error
"unknown constraint 'doc'", because `compiler.py:4822` (`body_variable`) does not remove the
docstring. Bead mtp-qiro fixes this.
:::

## Bodies

```{rule} contexts
Each body holds only the kinds of item that {numref}`contexts-table` gives for it, in the numbers
that it gives, and the `let`
and `foreach` forms that {numref}`body-let-foreach` allows. Any other item in a body is an error.
```

:::{table} The bodies of mtp. "let, foreach" is "yes" for a body that may hold a `let` and a `foreach` ({numref}`body-let-foreach`), and "no body" for a form that has no body.
:name: contexts-table

| Body | Optional arguments | Other items | let, foreach |
|---|---|---|---|
| The top level of a source | none | `import`. Declarations of types (`type`), {term}`interfaces <interface>`, namespaces, palettes, colormaps, functions (`func`, `func[T]`), motifs, variants, choreos, transitions and named animations. At most one `scene`. Formulas. Views (`canvas`, `readout`, `display`) and controls (`slider`, `button`, `play`, `stepper`, `toggle`). Variables of any type, `font` and `rand-seed` included. Not: shapes, listeners, `term`, uses of choreos. A `let` or a `foreach` here holds no `import` | yes |
| The top level of a {term}`file to import` | none | Only `import` and declarations of colors, fonts, functions, motifs, variants, types, interfaces, namespaces, palettes, colormaps, choreos, {term}`seeds <seed>` (`rand-seed`) and variables that are `const`. A `let` or a `foreach` here holds no `import` | yes |
| `(scene name …)` | `(background …)`, `(transform …)` | Shapes: every shape, `group`, `row`, `column`, motif and variant instances. Variables. `exists-when` | yes |
| `(group name …)`, `(row name …)`, `(column name …)` | the optional arguments of a group: `translate`, `transform`, `pointer-events`, `defaults`, `clip`, `fixed-size`, and for a row or a column `gap` and `align` | Shapes. `exists-when`. Not: variables | yes |
| Any other shape, such as `(circle name …)` | the optional arguments of the shape | The string of a text, as a positional argument | no body |
| A motif instance, `(M name …)` | its parameters, and the optional arguments of an instance: `x`, `y`, `pos`, `translate`, `transform`, `pointer-events`, `defaults`, `clip`, `like` | None: "an instance of M takes no members" | no body |
| A variant instance | the optional arguments of its base shape, and the parameters of the variant | None | no body |
| `(motif name params …)` | none | Shapes. Variables that are bound or known when compiling. `exists-when`. Not: `animation` (a choreo is the template of animations), uses of choreos, `motif`, `scene` | yes |
| `(variant name params shape)` | none | Exactly one shape, which is not a group | no |
| `(func name params body)` | none | Exactly one expression | no |
| `(type name base …)` | none | {term}`Constraints <constraint>` | yes |
| `(interface name …)` | none | Items `(T attribute constraint…)` | yes |
| `(namespace name …)` | none | Variables, namespaces, palettes. Not: functions, types, motifs, variants, shapes, {term}`components <component>`, transitions, animations, imports, interfaces, colormaps, choreos | yes |
| `(palette name …)` | none | Items `(member color)`. Not: palettes, namespaces | yes |
| `(formula name …)` | `(defaults …)`, at most once | Exactly one string, plain or TeX, known when compiling. `(term …)`, `exists-when`, variables. A `(term …)` and an `exists-when` of a term come after the string ({numref}`formula-terms`) | yes |
| `(term name …)` | `(like t)` first, then items `(attribute value)`, `(tex …)` among them | None | no body |
| A variable, `(T name value? …)` | none | Constraints, such as `(>= 0)` | yes |
| `(transition name target …)`, `(move target …)` | `like` first, then `from`, `to`, `duration`, `ease`, `path` | None | no body |
| `(animation name …)`, `(animation …)` in a control or a listener, `(choreo name params …)` | `(defaults …)`, `(loop …)` | Steps: `move`, `wait`, `roll-dice`, `at-once`, `in-order`, `(animation …)` ({numref}`animation-step`), the name of an animation or a transition, a use of a choreo | yes |
| `(at-once …)`, `(in-order …)` | `(defaults …)` | The steps of an animation. Not: `loop` | yes |
| `(canvas name …)` | `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom`, `toggle-duration`, `toggle-ease` | Its content, at least one item: names of shapes or of the scene, list literals, and expressions that give a shape, `none` or a list of shapes, such as `(when c d)`. Listeners on its shapes, `on-show`, `on-hide`, `on-view`, `on-ready`, `on-live`, `on-quiet`, `on-pointermove` ({numref}`listeners-in-views`) | yes |
| `(readout name value …)` | `(font f)` | The listeners `on-live` and `on-quiet` ({numref}`listeners-in-views`) | yes |
| `(display name formula …)` | `(kind k)` | Listeners on the terms of its formula (`on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-drag`), `on-live`, `on-quiet` ({numref}`listeners-in-views`) | yes |
| A control, such as `(slider name …)` | its optional arguments, among them `(in view…)` and its animation, written `(animation …)`, `(move …)` or a use of a choreo | Its positional argument: the move of a slider, the target of a toggle. Conditions, such as `(>= k 0)` | yes |
| A listener, inside the body of a view | its optional arguments, its animation among them. Not: `(in …)` | Its positional arguments: the shape or term that it listens to, and for some listeners a target. Conditions | yes |
| `(defaults …)` of a group or an instance | none | Items `(attribute value)` for the members of the container | yes |
| `(defaults …)` of an animation | none | `(duration …)`, `(ease …)` | yes |
| `(defaults …)` of a formula | none | Items `(attribute value)` for the terms | yes |
| `(clip shape)` | none | Exactly one circle, rect, ellipse, triangle, polygon or ring | no |
| `(import file name…)` | none | The file, then the names to import, or no names to import the file whole | no |
:::

So a source need not hold a scene: `(real a 1) (readout r $'{a}')` is a world model with a
variable and a readout, and an empty file is a world model with nothing in it. A source with two
scenes is an error. `(canvas v)` is an error, because a canvas holds at least one item of content,
and `(canvas v s)` and `(canvas v c)` are allowed.

:::{admonition} Code differs
:class: note
The error for a second scene is "a file has exactly one scene" (`compiler.py:4854`), and
`(canvas v)` compiles, to a canvas that draws nothing. Bead mtp-ydd4.7.59.
:::

```{rule} body-let-foreach
`(let ((name value) …) item…)`, `(foreach i n item…)`, `(foreach x list item…)` and
`(foreach ((i n) (x list) …) item…)`, written in a body, are replaced by their items, with their names bound: once
for `let`, and once for each value for `foreach`. A `let` and a `foreach` may be written in every
body that holds declarations or any number of items, the top level of a source and of a file to
import included, and nowhere else. Their items are of the kinds that the body around them holds.
```

The column "let, foreach" of {numref}`contexts-table` follows from this rule. So a `let` and a
`foreach` may never be written among the positional arguments or the optional arguments of a form,
in a form that has no body, or in a body that holds a fixed number of items, such as the body of a
function or a variant. `(let ((k 2)) (real a k))` may be written at the top level, a `let` may be
written among the steps of an animation, and `(circle c (let ((k 2)) (r k)))` is an error, because
`(r k)` is an optional argument of the circle.

:::{admonition} Code differs
:class: note
- `compiler.py:947` (`body_let`) makes a `let` at the top level an error, and a `let` inside a
  `foreach` at the top level too. For a `foreach` at the top level of a file to import, the error
  is "holds a variable that is not const" (`compiler.py:7257`, `_not_importable`), which names the
  wrong form (bead mtp-inhr). Bead mtp-ydd4.7.7 allows both at both top levels.
- A `let` is an error in the body of an animation, a choreo, an `at-once` and an `in-order`
  (`compiler.py:3018`, `steps`), though a `let` inside a `foreach` there compiles. `let` and
  `foreach` are errors in a namespace and a formula, and the body of a canvas, a readout or a
  display allows them only around listeners. Bead mtp-ydd4.7.8 allows them in every body marked
  "yes" in {numref}`contexts-table`.
- `compiler.py:5158` (`shape_here`) expands every item of a shape, so
  `(circle c (let ((k 2)) (r k)))` and `(circle c (foreach i 1 (r 2)))` compile, and give the
  circle a radius of 2. Bead mtp-ydd4.7.9 makes a `let` or a `foreach` among the arguments of a
  form an error.
:::

By {numref}`declare-before-use`, an `exists-when` names a shape, a term or a member that is
declared before it, in every body.

:::{admonition} Code differs
:class: note
In the scene and in the body of a motif, the compiler follows this. In a group,
`compiler.py:5166` (`shape_here`) keeps every `exists-when` until all the members are declared, so
`(group g (exists-when c true) (circle|none c))` compiles. Bead mtp-ydd4.7.10 makes it an error.
:::

```{rule} formula-terms
The string of a formula declares the terms that it marks with `\term{name}{…}`.
```

The `(defaults …)` of a formula is an optional argument, so it comes before the body
({numref}`optional-arguments-first`).
The body holds the string, the terms, the `exists-when` forms and the variables. By
{numref}`declare-before-use`, a `(term name …)` and an `exists-when` of a term come after the
string. So `(formula f (defaults (padding 3)) tex'\term{a}{x}' (term a (fill 'red')))` is allowed,
and the same formula with `(defaults …)` last, or with `(term a …)` before the string, is an error.

:::{admonition} Code differs
:class: note
`compiler.py:4905` (`formula_decl`) looks for the string, the `(defaults …)`, the terms, the
`exists-when` and the variables at every place, so the string may come last, and `(defaults …)`
may come after a `(term …)`. Bead mtp-ydd4.7.11 makes the compiler follow the rule.
:::

```{rule} listeners-in-views
A listener acts only on what happens in the view in whose body it is written. A listener on its
own view leaves out the name of the view: `(on-view (animation …))`, `(on-pointermove target)`.
```

{numref}`contexts-table` gives the view in whose body each listener is written: a listener on a
shape, `on-show`, `on-hide`, `on-view`, `on-ready`, `on-live`, `on-quiet` and `on-pointermove` in a
canvas, a listener on a term of a formula, `on-live` and `on-quiet` in a display, and `on-live` and
`on-quiet` in a readout. A listener is never written at the top level and has no `(in …)`, while a
control is written at the top level and names the views that it belongs to with `(in …)`.

## Imports

Where an `import` may be written is given in {numref}`contexts-table`. Everything else about
imports is in {doc}`imports`.

## An example

This file has each form in a body that allows it: a variable, its docstring and its constraints at
the top level, the optional arguments of the scene before its shapes, a `foreach` of shapes in the
scene, and a canvas and a slider at the top level.

```{mtp-example}
(real k 1 doc@'The radius of the circle.' (>= 0.2) (<= 2))
(scene s
  (background 'white')
  (circle c (r k) (fill 'crimson'))
  (foreach i 3
    (circle #'dot-{i}' (x (+ 3 i)) (r 0.2) (fill 'gray'))))
(canvas v (x -3) (y -3) (width 9) (height 6) s)
(slider size (move k (from 0.2) (to 2)) (label 'radius'))
```
