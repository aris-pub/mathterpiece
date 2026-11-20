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

### Forms and sources

```{mtp-grammar} forms
```

```{rule} forms
A form is a `(`, then any number of expressions, its items, then a `)`. An
expression is a form, a {term}`list` literal, a word, a {term}`broadened type`, a
string literal or an {term}`interpolated string`. The first item of a form is its head, and it may be a head
that ends with `_` ({numref}`unnamed-head`). The form `()` has no items and no head.
```

So `(circle c (r 1))` is a form with three items, whose head is `circle` and whose third item is
the form `(r 1)`, and `(motif m () …)` holds the form `()`, an empty list of parameters.

```{mtp-grammar} file
```

```{rule} top-level-forms
A source is any number of forms, with or without {term}`whitespace` and
{term}`comments <comment>` between them. Anything else at the top level of a source is an error. A
source may hold no form at all.
```

```{rule} adjacent-items
Among the items of a form, a list literal or brackets, whitespace or a comment separates every two
expressions, except where one of the two is a form. More exactly, an expression that ends with the
`)` of a form, which is a form or a prefixed form such as `free@(g)`, may be followed
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
A broadened type is two words or more joined by `|` with no whitespace between them, such
as `real|none`. Its words are names, names followed by brackets, numbers, {term}`bool` literals or
{term}`operators <operator>`. A broadened type is one expression, and the {term}`compiler` reads it as a
type ({doc}`types`).
```

### Heads

```{mtp-grammar} heads
```

A {token}`mtp:head` is the head of a form that has no name: a name that ends with `_`, or a
broadened type whose last word is such a name. The `_` at the end of a head stands for the missing
name. {numref}`unnamed-head` gives its meaning.

### Strings

```{mtp-grammar} strings
```

A {token}`mtp:string` is a plain string or a {term}`TeX string`. An {term}`interpolated string`
and a {term}`name string` hold text and expressions in braces, each expression with an optional
{term}`format spec` after a colon, and a name string holds at least one expression.
{numref}`string-literals` and {numref}`interpolated-strings` give the characters and the escapes
inside each kind.

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
| string literal | `'…'`, `$'…'` | its text |
| color literal | `#'…'` | the color ({numref}`color-literals`) |
| {term}`int`, {term}`ratio`, {term}`real` or {term}`complex` literal | `3`, `1/3`, `2.5`, `1+2i` | the value ({numref}`number-literals`) |
| bool literal | `true`, `false` | the value |
| none | `none` | nothing |
```

An operator is a name with one name part ({numref}`literal-words`).

```{rule} literals
A literal is a piece of source text that writes a value directly: a number literal, a string
literal, a color literal, `true`, `false`, `none`, or a list literal whose items are literals.
```

What value a literal gives, and of what type, is defined in {numref}`literal-types`. Values are
defined in {doc}`data-model`.

```{rule} parser-sugar
The parser produces each spelling on the left as the form on the right:

| Written | Is the form |
|---|---|
| `H@X`, such as `r@1` | `(H X)`, such as `(r 1)` ({numref}`prefix-forms`) |
| `@'dot-{k}'` | `(name f'dot-{k}')` |
| `@'dot-{k}'.a.b` | `(. (. (name f'dot-{k}') a) b)` |
| `@'dot-{k}'[i]` | `(. (name f'dot-{k}') i)` |
| `[a b c][h]` | `(. [a b c] h)` |
| `f'x = {x:.2f}!'` | `(concat 'x = ' (fmt x '.2f') '!')`. Each piece of text, as long as possible, is a string literal, each `{X}` is `(fmt X)`, and each `{X:S}` is `(fmt X 'S')`, in the order of the text |

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
Every form is written `(head name? positional… named… docstring? body…)`. The signature of each
head says which of these it has ({ref}`signatures`).

- The head determines which of these the form has: whether it has a name, which positional and
  named arguments it takes and which of them it requires, whether it may have a docstring, and
  what its body may hold.
- The name, for a declaration, if it takes one, is the second item ({numref}`declared-names`).
- The {term}`positional arguments <positional argument>` come next, in the order that the head
  specifies. A head takes a fixed number of them. One that the head does not require may be left
  out only together with every positional argument after it.
- The {term}`named arguments <named argument>` come next, in any order, each at most once
  ({numref}`named-arguments-first`, {numref}`named-arguments-once`). Each is a form whose head has
  a meaning only inside the form that holds it, as `r` has only inside a circle, and whose items
  are specified by the head that holds it: at most two positional arguments, and a body, but
  never a named argument. So `(defaults (fill red) (stroke blue))` has only a body, whose items
  are the attributes and values that it gives.
- The {term}`docstring`, for a declaration, comes next ({numref}`docstrings`).
- The body comes last: any number of items, or none, of the kinds that the form specifies
  ({numref}`contexts`). Whatever a form takes in a varying number goes in its body: no positional
  argument and no named argument stands for several items. Whether the order of the items in the
  body matters is specified by the head.

So a call `(+ a b c)`, a special form `(if c a b)` and an import `(import math dot)` follow the
template, with no name.
```

Some forms, taken apart by the template:

```{table}
:class: form-parts

| Form | Head | Name | Positional | Named | Docstring | Body |
|---|---|---|---|---|---|---|
| `(circle c (r 1) (fill 'crimson'))` | `circle` | `c` |  | `(r 1)`, `(fill 'crimson')` |  | no |
| `(real k 1 (>= 0) (<= 3))` | `real` | `k` | `1` |  |  | yes |
| `(real k 1 doc@'the count' (>= 0))` | `real` | `k` | `1` |  | `doc@'the count'` | yes |
| `(list[color] cs ['red' 'blue'])` | `list[color]` | `cs` | `['red' 'blue']` |  |  | no |
| `((real (>= 0)) r 1)` | `(real (>= 0))` | `r` | `1` |  |  | no |
| `(line\|none l (from a) (to b))` | `line\|none` | `l` |  | `(from a)`, `(to b)` |  | no |
| `(func f ((real x)) (* 2 x))` | `func` | `f` | `((real x))` |  |  | yes |
| `(group g (defaults (fill 'red')) (circle_ (r 1)))` | `group` | `g` |  | `(defaults (fill 'red'))` |  | yes |
| `(canvas v (x -2) (width 4) s)` | `canvas` | `v` |  | `(x -2)`, `(width 4)` |  | yes |
| `(slider s (move k (from 0) (to 1)) (label 'k'))` | `slider` | `s` | `(move k (from 0) (to 1))` | `(label 'k')` |  | no |
| `(if c a b)` | `if` |  | `c`, `a`, `b` |  |  | no |
```

```{rule} declared-names
Almost every declaration has a name slot, its second item. The exceptions are rare: a
{term}`listener` is a declaration with no name slot ({numref}`forms-with-no-name`). The name of a
declaration is a bare name with one name part, `none`, or `(name s)`, whose string `s` is known
when compiling ({numref}`names-from-values`).
`none` as the name means that the declaration has no name, as the head `head_` does
({numref}`unnamed-head`). A scene, a formula, a {term}`view` and a {term}`control` must have a name,
and `none` is an error for them. Every other declaration may have the name `none`. A name in quotes
is an error ("a name is written bare, not in quotes"), and so is a name that
{numref}`declaration-names` does not allow.
```

A scene is named because a canvas shows it by its name, a formula because a display shows it by its
name, and a view and a control because the page places them by their names, as
`<mtp-canvas name="v">`. Inside the compiler and the runtime, a declaration with no name is still a
thing of its own, so nothing else needs a name.

So `(circle c (r 1))` has the name `c`, and `(circle none (r 1))` and `(circle_ (r 1))` have no
name. Inside `(foreach k 3 …)`, `(circle @'dot-{k}' (r 1))` declares the circles `dot-0`, `dot-1`
and `dot-2`, and `(circle (name s) (r 1))` takes its name from the string `s`, which is known when
compiling. `(real none 1)`, `(animation_ (move k (to 2)))` and `(func_ ((real x)) (* 2 x))` are
allowed, and nothing can refer to them. `(canvas none s)`, `(slider_ (move k (from 0) (to 1)))`,
`(scene_ (circle c (r 1)))` and `(formula none $'x')` are errors, since those must have a name.
`(circle 'c' (r 1))` is an error, since the name is in quotes, and so is `(circle p.r (r 1))`, since
its name has two name parts.

```{rule} forms-with-no-name
These forms have no name, so their second item is their first positional argument or their first
named argument: a {term}`listener`, `(move …)`, `(jump …)`, an `(animation …)` inside a
{term}`control` or a listener, `(foreach …)`, `(let …)`, `(exists-when …)`, `(import …)`,
`(term …)`, `(like …)`, every named argument, every call and every special form.
```

So the second item of each of these is not a name:

- `(on-drag p (move k (to pointer)))`: `p`, the shape that the listener hears.
- `(move k (to 1) (duration 0.5))`: `k`, the target that the move writes.
- `(foreach k 3 (circle_ (r k)))`: `k`, the name that the foreach binds, and then `3`.
- `(let ((h (/ w 2))) (rect_ (width h)))`: `((h (/ w 2)))`, the bindings.
- `(import math clamp)`: `math`, the file that the import reads.
- `(term a (fill #'crimson'))`: `a`, the term that the form gives attributes to.
- `(r 1)`, a named argument: `1`, its value.


```{rule} named-arguments-first
A named argument is a form, after the name and the positional arguments, whose head names one
of the named arguments that the form allows, such as `(r 1)` in `(circle c (r 1))`. In every
form, the named arguments come before the body, in any order, except that a `(like …)` comes
before every other named argument. A named argument after the first item of the body is an
error, such as "(x …) is a named argument, so
it comes before the canvas's body".
```

So `(circle c (r 1) (fill #'red'))` and `(circle c (fill #'red') (r 1))` are the same form, and
`(circle d (like c) (r 2))` is allowed. `(circle d (r 2) (like c))` is an error, since its
`(like …)` is not first. `(canvas v s (x 0))` and `(group g (circle_ (r 1)) (defaults (fill #'red')))`
are errors, since a named argument comes after the first item of the body.

```{rule} named-arguments-once
Each named argument appears at most once in a form: a second one is an error, such as "'fill' is
given twice".
```

So `(circle c (fill #'red') (fill #'blue'))` and `(circle c (r 1) (r 2))` are errors, and
`(circle c (x 1) (y 2))` is allowed.

Since `(pos P)` is `(x …) (y …)` ({numref}`sugar-rewrites`), a form that gives `pos` and also `x`
or `y` gives `x` or `y` twice, and is an error. The forms that allow a `(like …)` are given in
{numref}`sugar-rewrites`.

```{rule} docstrings
Every declaration may have a docstring, `doc@'text'`, and at most one. The
docstring comes after all the positional arguments and all the named arguments, and before the
body. In a form that has no body, the docstring is the last item. Its string literal is plain: an
interpolated string is an error.
```

So a docstring comes after the name, the positional arguments, the parameters of a function or a
motif included, and the named arguments. A variable in the body of a motif may have one, as any
other declaration. `(real k 1 doc@'d' (>= 0))`, `(func f ((real x)) doc@'d' (* 2 x))` and
`(circle c (r 1) doc@'d')` are allowed. `(real k 1 (>= 0) doc@'d')`,
`(func f ((real x)) (* 2 x) doc@'d')`, `(circle c doc@'d' (r 1))` and
`(button b doc@'d' (animation a))` are errors.
`(button b (animation a) doc@'d')` and `(on-click p (animation a) doc@'d')` are allowed, and so is
`(motif m ((real k 1)) doc@'d' (circle_ (r k)))`, whose docstring comes after its parameters and
before its body. A second docstring, as in `(circle c doc@'d' doc@'e')`, is an error, and so is
`(circle c doc@f'r = {r}')`, whose string is interpolated.

## Bodies

```{rule} contexts
The head specifies what the body of a form may hold, and {numref}`bodies-table` gives it for each
head that has a body. A head that the table does not list has no body. An item that the head does
not allow in the body is an error.
```

```{rule} body-let-foreach
`(let ((name value) …) item…)`, `(foreach i n item…)`, `(foreach x list item…)` and
`(foreach ((i n) (x list) …) item…)`, written in a body, are replaced by their items, with their names bound: once
for `let`, and once for each value for `foreach`. A `let` and a `foreach` may be written in every
body that {numref}`bodies-table` marks "yes", the top level of a source and of a file to import
included, and nowhere else. Their items are of the kinds that the body around them holds.
```

So a `let` and a `foreach` may never be written among the positional arguments or the named
arguments of a form, or in a form that has no body, such as a function, whose expression is a
positional argument. `(let ((k 2)) (real a k))` may be written at the top level, a `let` may be
written among the steps of an animation, and `(circle c (let ((k 2)) (r k)))` is an error, because
`(r k)` is a named argument of the circle.

:::{admonition} Code differs
:class: note
- A `let` is an error in the body of an animation, a choreo, an `at-once` and an `in-order`
  (`compiler.py:3018`, `steps`), though a `let` inside a `foreach` there compiles. `let` and
  `foreach` are errors in a namespace and a formula, and the body of a canvas, a readout or a
  display allows them only around listeners. Bead mtp-ydd4.7.8 allows them in every body marked
  "yes" in {numref}`bodies-table`.
- `compiler.py:5158` (`shape_here`) expands every item of a shape, so
  `(circle c (let ((k 2)) (r k)))` and `(circle c (foreach i 1 (r 2)))` compile, and give the
  circle a radius of 2. Bead mtp-ydd4.7.9 makes a `let` or a `foreach` among the arguments of a
  form an error.
:::

## Imports

An `import` is written only at the top level of a source or of a file to import, and never inside
a `let` or a `foreach`. Everything else about imports is in {doc}`imports`.

## An example

This file has each form in a body that allows it: a variable, its docstring and its conditions at
the top level, the named arguments of the scene before its shapes, a `foreach` of shapes in the
scene, and a canvas and a slider at the top level.

```{mtp-example}
(real k 1 doc@'The radius of the circle.' (>= 0.2) (<= 2))
(scene s
  (background (light-dark #'#ffffff' #'#13181b'))
  (circle c (r k) (fill #'crimson'))
  (foreach i 3
    (circle @'dot-{i}' (x (+ 3 i)) (r 0.2) (fill #'gray'))))
(canvas v (x -3) (y -3) (width 9) (height 6) s)
(slider size (move k (from 0.2) (to 2)) (label 'radius'))
```
