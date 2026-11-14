(grammar)=
# Grammar

This part defines how the reader puts the tokens of {doc}`lexical` together into forms, the nodes
that the reader produces, the template that every form follows, and the kinds of form that may
stand in each body. The signatures of the forms, which list the arguments of each head, are not
part of this part.

## The reader grammar

The rules below and the tokens of {doc}`lexical` are one grammar, `docs/spec/mtp.lark`. A rule
written with `{w}`, such as `form{w}`, is written once for two places, which differ only in their
words. Outside the braces of an interpolated string, `w` is {token}`mtp:word`. Inside them, `w` is
{token}`mtp:bword`, whose tokens end a run at `:` ({numref}`inside-braces`). An alternative
written `a -> free` builds a node named `free`, and `!` before the name of a rule keeps its quoted
tokens in the tree.

### Files and sequences

```{mtp-grammar} file
```

```{rule} top-level-forms
A source is a sequence of {term}`forms <form>`, with or without blanks between them. Anything
else at the top level of a source is an error. A source may hold no form at all.
```

```{mtp-grammar} sequences
```

A {term}`node` is one item of a form, a list or an index: a form, a list, a word, a string or a
free start. A sequence is the nodes of a form or a list. A chunk is a run of nodes with no blank
between them.

```{rule} adjacent-items
In a sequence, a blank separates every two nodes, except where one of the two is a form. More
exactly, a node that ends with the `)` of a form, which is a form or a free start of a form, may
be followed directly by any node, and every other node may be followed directly only by a form.
So `(f a(b)c)`, `(f (a)b)` and `(f 'x'(b))` hold three nodes after `f`, and `(f 'a''b')` and
`(f [1]x)` are errors.
```

:::{admonition} Open question Q-grammar-1
:class: warning
The documents have no rule for when a blank is needed between two nodes. The only rule in
`syntax.md` (section 2, "Forms") is that "line breaks and indentation mean nothing". The reader
allows a form to touch its neighbors, as in {numref}`adjacent-items`: a run ends at `(` and `)`
(`parse.py:74`), and after a `)`, `parse.py:276` checks only for `.` and `[`. Option A: keep this
rule. Option B: require a blank between every two nodes, as in `(f a (b) c)`.
:::

### Lists and parts

```{mtp-grammar} lists
```

```{rule} lists
A {term}`list` is written in square brackets, with its items separated as in
{numref}`adjacent-items`: `[]`, `[0 1]`, `[(f x) 'a']`. A `[` right after the `]` of a list is an
{term}`index` of the list, and it holds exactly one node: `[a b c][h]`.
```

```{rule} name-index
A `[` right after a name, with no blank between them, is an index of the name. It holds one node
or more: `xs[0]`, `xs[(+ k 1)]`, `g['m1']`, `func[real real]`. Several indexes may follow each
other, and after an index, `.` and more name parts may follow: `xs[0].pos.x`, `m[0][1]`,
`a[0].b[1]`. A `[` after a blank starts a list: `xs [0]` is the name `xs` and the list `[0]`.
```

### Words

```{mtp-grammar} words
```

```{mtp-grammar} brace-words
```

```{mtp-grammar} literals
```

```{rule} bars
A {term}`bar` is two words or more joined by `|` with no blank, such as `real|none`. Its words are
names, names with indexes, numbers, booleans or operators. A bar is one node, and the compiler
reads it as a type ({doc}`types`).
```

### Strings

```{mtp-grammar} strings
```

## The nodes that the reader produces

```{rule} reader-nodes
The reader produces the forms of a source as a sequence of nodes, in the order of the source.
Each node is one of these:

| Node | Written | Holds |
|---|---|---|
| form | `(…)` | its items, in order |
| list | `[…]` | its items, in order |
| name | `p`, `p.pos.x`, `xs[0].y` | its parts, in order. Each part is the text of a name part, or the node of an index. An index of more than one node is a bracket node |
| bracket node | the index of `func[real real]` | its nodes, in order |
| bar | `real\|none` | its words, as nodes, in order |
| string | `'…'`, `tex'…'` | its text, and whether it is a TeX string |
| interpolated string | `$'…'` | its pieces: text, the node of each field without a format spec, and a field node for each field with one |
| field node | `{x:.2f}` | the node and the format spec |
| int, ratio, real, complex | `3`, `1/3`, `2.5`, `1+2i` | the value ({numref}`number-literals`) |
| boolean | `true`, `false` | the value |
| none | `none` | nothing |

An operator is a name of one part. In an interpolated string, each piece of text is as long as
possible, so two pieces of text are never next to each other.
```

```{rule} shorthand-forms
The reader produces each spelling on the left as the form on the right:

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
When the first item of a form is a name whose last part ends with `_` and has more than one
character, the reader removes the `_` and puts `none` in as the second item: `(circle_ (r 1))` is
`(circle none (r 1))`, and `(marks.grid_ …)` is `(marks.grid none …)`. When the first item is a
bar, this rule applies to the last word of the bar, so `(line|none_ …)` is `(line|none none …)`.
The head `none_` becomes the literal `none`: `(none_ a)` is `(none none a)`. No other `_` in a
source has a meaning.
```

```{rule} dot-form
`(. X Y)` reads the part `Y` of the value of `X`, where `X` is any node. The reader produces a
name of several parts, such as `p.r` or `xs[0]`, as one name node, and a part that follows a list
or a name string as a `(. X Y)` form ({numref}`shorthand-forms`). A part of the value of a form is
written only with `(. X Y)` ({numref}`no-part-after-form`).
```

:::{admonition} Open question Q-grammar-2
:class: warning
In `syntax.md` (section 7, "Parts of what an expression gives"), `p.r` is `(. p r)`. The compiler
reads the two differently when `r` is also a declared name. In `p.r`, the part `r` is always the
attribute named `r` (`compiler.py:5958`). In `(. p r)`, a bare name `r` is an attribute only when
`p` has an attribute by that name, or when `r` is not declared and `p` is an object. Otherwise the
value of `r` is the part (`compiler.py:6540`). So with `(int r 0)` declared and `p` a list,
`(. p r)` is `p[r]`, while `p.r` is an error. Option A: make `(. p r)` always read the attribute
`r`, as `p.r` does. Option B: keep the compiler's rule, and change `syntax.md`.
:::

## The form template

```{rule} form-template
Every declaration is written `(head name? positional… option… body…)`:

- The {term}`head` is the first item, and it names the kind of thing declared. It is a name
  (`circle`, `real`, `motif`, `dial`), a name with an index (`list[color]`, `func[real]`), a bar
  (`real|none`), or a form that gives a type (`((real (>= 0)) r 1)`).
- The name, for a form that has one, is the second item ({numref}`declared-names`).
- The {term}`positional arguments <positional argument>` come next. Each kind of form has a fixed
  number of them, and some of them may be left out.
- The {term}`options <option>` come next, in any order ({numref}`options-first`).
- The {term}`body` comes last: any number of items, or none. The kinds of item in a body depend on
  the form ({numref}`contexts`).

A call and a special form follow the same template, with no name: `(+ a b c)`, `(if c a b)`.
```

```{rule} declared-names
The name of a declaration is a bare name of one part, `none`, a name string such as `#'dot-{k}'`,
or `(name s)`. The string of a name string and of `(name s)` is known when compiling. `none` as the
name means that the declaration has no name, as the head `head_` does ({numref}`unnamed-head`). A
name in quotes is an error ("a name is written bare, not in quotes"), and so is a reserved word
({numref}`reserved-words`).
```

```{rule} forms-with-no-name
These forms have no name, so their second item is their first positional argument or their first
option: a listener, `(move …)`, an `(animation …)` inside a control or a listener, `(foreach …)`,
`(let …)`, `(exists-when …)`, `(import …)`, `(term …)`, `(like …)`, every option, every call and
every special form. A view and a control always have a name, because their elements on the page give it, as `<mtp-canvas name="v">`.
```

```{rule} options-first
An option is a form among the items after the name and the positional arguments, whose head is
one of the options of the form. In the bodies marked "yes" under "Options first" in
{numref}`contexts-table`, an option after the first other item is an error, such as "(x …) is an
optional argument, so it comes before the canvas's body" (`compiler.py:3599`).
```

```{rule} options-once
Each option appears at most once in a form: a second one is an error, such as "'fill' is given
twice". `(pos p)` gives both `x` and `y`, so it does not appear together with either of them.
`(like x)`, in the forms that allow it (a shape, a motif or variant instance, a transition, a
move, a term and a font), comes before every other option.
```

```{rule} docstrings
A docstring, `doc@'text'`, may stand anywhere among the items of a declaration after its name, or,
for a listener, after its head. A declaration has at most one docstring. Its string is plain: an
interpolated string is an error. The compiler removes the docstring from the form before it reads
the other items, so a docstring is not one of the positional arguments, the options or the body.
```

:::{admonition} Open question Q-grammar-3
:class: warning
In `reference.md` ("Docstrings"), a docstring "goes with the declaration's other optional
arguments, and in a function or a motif after the parameters and before the body". The compiler
removes it from any place after the name (`compiler.py:7322`, `_take_doc`), so
`(circle c (r 1) doc@'x')` and `(func f ((real x)) (* 2 x) doc@'d')`, with the docstring after the
body, compile. Option A: require the place of `reference.md`. Option B: allow any place after the
name.
:::

:::{admonition} Open question Q-grammar-4
:class: warning
A variable in the body of a motif may not have a docstring: `(motif m () (real k 1 doc@'d') …)` is
the error "unknown constraint 'doc'", because `compiler.py:4822` (`body_variable`) does not remove
the docstring. A variable in the scene, at the top level or in a namespace may have one
(`compiler.py:1468`). In `reference.md` ("Docstrings"), every declaration may have a docstring.
Option A: allow a docstring on a variable of a motif, as on any other. Option B: make it an error
with a message about the docstring.
:::

## Bodies

```{rule} contexts
Each body holds only the kinds of item that {numref}`contexts-table` gives for it, in the order of
the table. A `let` or a `foreach` in a body holds the kinds of item that the body holds, and it
stands for its items, with its names bound ({numref}`body-let-foreach`). Any other item in a body
is an error.
```

:::{table} The bodies of mtp. "Options first" is "yes" for a body whose options come before its other items ({numref}`options-first`), and "no body" for a form that has no body.
:name: contexts-table

| Body | Options | Other items | Options first | Compiler |
|---|---|---|---|---|
| The top level of a source | none | `import`. Declarations of types (`type`), interfaces, namespaces, palettes, colormaps, functions (`func`, `func[T]`), motifs, variants, choreos, transitions and named animations. One `scene`. Formulas. Views (`canvas`, `readout`, `display`) and controls (`slider`, `button`, `play`, `stepper`, `toggle`). Variables of any type, `font` and `rand-seed` included. A `foreach` of any of these but `import`. Not: `let`, shapes, listeners, `term`, uses of choreos | no | `top_here`, `expand` |
| The top level of a file to import | none | Only `import` and declarations of colors, fonts, functions, motifs, variants, types, interfaces, namespaces, palettes, colormaps, choreos, seeds (`rand-seed`) and variables that are `const` | no | `_not_importable` |
| `(scene name …)` | `(background …)`, `(transform …)` | Shapes: every shape, `group`, `row`, `column`, motif and variant instances. Variables. `exists-when`, `let`, `foreach` | yes | `scene_items` |
| `(group name …)`, `(row name …)`, `(column name …)` | the options of a group: `translate`, `transform`, `pointer-events`, `defaults`, `clip`, `fixed-size`, and for a row or a column `gap` and `align` | Shapes. `exists-when`, `let`, `foreach`. Not: variables | yes | `shape_here` |
| Any other shape, such as `(circle name …)` | the options of the shape | The string of a text, as a positional argument | no body | `shape_here` |
| A motif instance, `(M name …)` | its parameters, and the options of an instance: `x`, `y`, `pos`, `translate`, `transform`, `pointer-events`, `defaults`, `clip`, `like` | None: "an instance of M takes no members" | no body | `instance` |
| A variant instance | the options of its base shape, and the parameters of the variant | None | no body | `variant_instance` |
| `(motif name params …)` | none | Shapes. Variables that are bound or known when compiling. `exists-when`, `let`, `foreach`. Not: `animation` (a choreo is the template of animations), uses of choreos, `motif`, `scene` | no | `instance` |
| `(variant name params shape)` | none | Exactly one shape, which is not a group | no | `variant_decl` |
| `(func name params body)` | none | Exactly one expression | no | `func_decl` |
| `(type name base …)` | none | Constraints | no | `type_decl` |
| `(interface name …)` | none | Items `(T attribute constraint…)` | no | `interface_decl` |
| `(namespace name …)` | none | Variables, namespaces, palettes. Not: `let`, `foreach`, functions, types, motifs, variants, shapes, components, transitions, animations, imports, interfaces, colormaps, choreos | no | `namespace_decl` |
| `(palette name …)` | none | Items `(member color)`. Not: palettes, namespaces | no | `palette_decl` |
| `(formula name …)` | `(defaults …)`, at most once | Exactly one string, plain or TeX, known when compiling. `(term …)`, `exists-when`, variables. In any order. Not: `let`, `foreach` | no | `formula_decl` |
| `(term name …)` | `(like t)` first, then items `(attribute value)`, `(tex …)` among them | None | no body | `term_form` |
| A variable, `(T name value? …)` | none | Constraints, such as `(>= 0)` | no | `declared` |
| `(transition name target …)`, `(move target …)` | `like` first, then `from`, `to`, `duration`, `ease`, `path` | None | no body | `transition` |
| `(animation name …)`, `(animation …)` in a control or a listener, `(choreo name params …)` | `(defaults …)`, `(loop …)` | Steps: `move`, `wait`, `roll-dice`, `at-once`, `in-order`, the name of an animation or a transition, a use of a choreo, a `foreach` of steps. Not: `let` | yes | `anim_body`, `steps` |
| `(at-once …)`, `(in-order …)` | `(defaults …)` | The steps of an animation. Not: `loop`, `let` | yes | `steps` |
| `(canvas name …)` | `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom`, `toggle-duration`, `toggle-ease` | Its content: names of shapes or of the scene, lists, and expressions that give a shape, `none` or a list of shapes, such as `(when c d)`. Listeners. A `foreach` or a `let` of listeners only | yes | `component`, `build_canvas` |
| `(readout name value …)` | `(font f)` | The listeners `on-live` and `on-quiet`. A `foreach` or a `let` of those only | no | `component`, `build_readout` |
| `(display name formula …)` | `(kind k)` | Listeners on the terms of its formula (`on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-drag`), `on-live`, `on-quiet`. A `foreach` or a `let` of those only | no | `component`, `listened` |
| A control, such as `(slider name …)` | its options, among them `(in view…)` and its animation, written `(animation …)`, `(move …)` or a use of a choreo | Its positional argument: the move of a slider, the target of a toggle. Conditions, such as `(>= k 0)` | yes | `component`, `writer` |
| A listener, inside the body of a view | its options, its animation among them. Not: `(in …)` | Its positional arguments: the shape or term that it listens to, and for some listeners a target. Conditions | yes | `component`, `listened`, `writer` |
| `(defaults …)` of a group or an instance | none | Items `(attribute value)` for the members of the container | no | `group_defaults` |
| `(defaults …)` of an animation | none | `(duration …)`, `(ease …)` | no | `steps` |
| `(defaults …)` of a formula | none | Items `(attribute value)` for the terms | no | `formula_defaults` |
| `(clip shape)` | none | Exactly one circle, rect, ellipse, triangle, polygon or ring | no | `clip` |
| `(import file name…)` | none | The file, then the names to import, or no names to import the file whole | no | `imports` |
:::

```{rule} body-let-foreach
`(let ((name value) …) item…)`, `(foreach i n item…)`, `(foreach x list item…)` and
`(foreach ((i n) (x list) …) item…)` stand in a body for their items, with their names bound: once
for `let`, and once for each value for `foreach`. Their items are of the kinds that the body
around them holds. A `let` of declarations never stands at the top level, and neither does a `let`
inside a `foreach` at the top level.
```

:::{admonition} Open question Q-grammar-5
:class: warning
The top level allows a `foreach` but not a `let`. The compiler expands the top level with
`compiler.py:828` (`expand`) and `top=True`, which makes the copies of a `foreach` there, so
`(foreach i 3 (real #'k-{i}' i))` and a `foreach` of sliders compile, while `compiler.py:947`
(`body_let`) makes a `let` at the top level an error, and a `let` inside such a `foreach` too.
`reference.md` does not list `foreach` among the forms of the top level. And for a file to import
with a `foreach` at its top level, the error is "holds a variable that is not const"
(`compiler.py:7257`, `_not_importable`), which names the wrong form. Option A: allow both
`foreach` and `let` at the top level. Option B: allow neither. In both cases, a decision is also
needed on which of them a file to import may hold.
:::

:::{admonition} Open question Q-grammar-6
:class: warning
`let` and `foreach` may stand among the options of a shape that has no body. `compiler.py:5158`
(`shape_here`) expands every item of a shape with `expand`, so `(circle c (let ((k 2)) (r k)))`
and `(circle c (foreach i 1 (r 2)))` compile, and give the circle a radius of 2. In
`reference.md` ("The scene and shapes"), such shapes have no body, and the error message of
`compiler.py:950` gives a `let` declarations to hold. Option A: make `let` and `foreach` among the
options of a shape an error. Option B: allow them, and add them to the rules.
:::

:::{admonition} Open question Q-grammar-7
:class: warning
The body of an animation does not allow `let`, but a `foreach` in it may hold one.
`compiler.py:3018` (`steps`) expands only a `foreach`, and a `let` is the error "an animation holds
moves, waits, …". But `expand` makes the copies of the `foreach`, and `expand` also expands a `let`
inside them, so `(animation an (foreach i 1 (let ((k 1)) (move a (to k) (duration 1)))))`
compiles. Option A: allow `let` in the body of an animation. Option B: make it an error inside a
`foreach` there too.
:::

:::{admonition} Open question Q-grammar-8
:class: warning
In the scene and in the body of a motif, an `exists-when` names a shape declared before it, as in
`reference.md` ("The scene and shapes"): "It is written after the shape it names". In a group,
`compiler.py:5166` (`shape_here`) keeps every `exists-when` until all the members are declared, so
`(group g (exists-when c true) (circle|none c))` compiles. Option A: require the shape first in a
group too. Option B: allow any order in every body.
:::

:::{admonition} Open question Q-grammar-9
:class: warning
The items of a formula may come in any order. `compiler.py:4905` (`formula_decl`) looks for the
string, the `(defaults …)`, the terms, the `exists-when` and the variables at every place, so the
string may come last, and `(defaults …)` may come after a `(term …)`. `reference.md` ("Formulas")
gives no order, and in every other body with options, the options come first
({numref}`options-first`). Option A: keep any order. Option B: require the string first, then
`(defaults …)`, then the other items.
:::

:::{admonition} Open question Q-grammar-10
:class: warning
A listener on its own view does not name that view: `(on-view (animation …))` inside a canvas, and
`(on-pointermove target)` with one name for the canvas, but two for a shape and its target. The
comment at `compiler.py:178` (`OWN_VIEW_NAMED = False`) is "Not decided by the author yet
(mtp-6k7f)". Option A: leave the name of the view out. Option B: write it, as in
`(on-view v (animation …))`.
:::

:::{admonition} Open question Q-grammar-11
:class: warning
An `(import …)` may stand anywhere at the top level, after the forms that use the names that it
gives, because `compiler.py:745` (`imports`) reads every import of a file before any other form.
So `(scene s (circle c (fill colors.tab10-named.red))) (import colors)` compiles. This breaks the
rule that a name is declared before it is used ({numref}`declare-before-use`). Option A: require
every import before the first form that is not an import. Option B: allow an import anywhere.
:::

## An example

This file has each form in a body that allows it: a variable and its constraints at the top
level, the options of the scene before its shapes, a `foreach` of shapes in the scene, and a
canvas and a slider at the top level.

```{mtp-example}
(real k 1 (>= 0.2) (<= 2) doc@'The radius of the circle.')
(scene s
  (background 'white')
  (circle c (r k) (fill 'crimson'))
  (foreach i 3
    (circle #'dot-{i}' (x (+ 3 i)) (r 0.2) (fill 'gray'))))
(canvas v (x -3) (y -3) (width 9) (height 6) s)
(slider size (move k (from 0.2) (to 2)) (label 'radius'))
```
