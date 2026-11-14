(grammar)=
# Grammar

This part defines how the parser puts the tokens of {doc}`lexical` together into forms, the nodes
that the parser produces, the template that every form follows, and the kinds of form that may
stand in each body. The signatures of the forms, which list the arguments of each head, are not
part of this part.

As in {doc}`lexical`, this part states the language as the author has decided it. Where the parser
or the compiler does not follow a rule yet, a note after the rule says what the code does today
and names the bead that will change it. A box marks each question that is still open.

## The grammar of the parser

The rules below and the tokens of {doc}`lexical` are one grammar, `docs/spec/mtp.lark`. An
alternative written `a -> free` builds a node named `free`, and `!` before the name of a rule keeps
its quoted tokens in the tree.

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
between them. The first chunk of a form may start with a head that ends with `_`
({numref}`unnamed-head`).

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
`syntax.md` (section 2, "Forms") is that "line breaks and indentation mean nothing". The parser
allows a form to touch its neighbors, as in {numref}`adjacent-items`: a run ends at `(` and `)`
(`parse.py:74`), and after a `)`, `parse.py:276` checks only for `.` and `[`. The grammar follows
the parser here. The decisions do not settle this case. Option A: keep this rule. Option B: require
a blank between every two nodes, as in `(f a (b) c)`.
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

```{mtp-grammar} literals
```

```{rule} bars
A {term}`bar` is two words or more joined by `|` with no blank, such as `real|none`. Its words are
names, names with indexes, numbers, booleans or operators. A bar is one node, and the compiler
reads it as a type ({doc}`types`).
```

### Heads

```{mtp-grammar} heads
```

A {token}`mtp:head` is the first item of a form that has no name: a name that ends with `_`, or a
bar whose last word is such a name. {numref}`unnamed-head` gives its meaning.

### Strings

```{mtp-grammar} strings
```

## The nodes that the parser produces

```{rule} parser-nodes
The parser produces the forms of a source as a sequence of nodes, in the order of the source.
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
When the first item of a form is a {token}`mtp:head`, the parser removes the `_` and puts `none`
in as the second item: `(circle_ (r 1))` is `(circle none (r 1))`, and `(marks.grid_ …)` is
`(marks.grid none …)`. When the head is a bar, this rule applies to its last word, so
`(line|none_ …)` is `(line|none none …)`. The head `none_` becomes the literal `none`:
`(none_ a)` is `(none none a)`.
```

```{rule} dot-form
`(. X Y)` reads the part `Y` of the value of `X`, where `X` is any node. A name of several parts
that stands for a value is a shorter spelling of `(. X Y)` forms, and means exactly what they
mean: `p.r` means `(. p r)`, `p.r.s` means `(. (. p r) s)`, and `xs[0].y` means
`(. (. xs 0) y)`.
```

The parser still produces such a name as one name node ({numref}`parser-nodes`). {doc}`core`
gives the meaning of `(. X Y)`.

:::{admonition} Code differs
:class: note
The compiler reads the two spellings differently when `r` is also a declared name. In `p.r`, the
part `r` is always the attribute named `r` (`compiler.py:5958`). In `(. p r)`, a bare name `r` is
an attribute only when `p` has an attribute by that name, or when `r` is not declared and `p` is
an object. Otherwise the value of `r` is the part (`compiler.py:6540`). So with `(int r 0)`
declared and `p` a list, `(. p r)` is `p[r]`, while `p.r` is an error. Bead mtp-ydd4.7.5 makes
`p.r` mean exactly `(. p r)`.
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
every special form. A view and a control always have a name, because their elements on the page
give it, as `<mtp-canvas name="v">`.
```

```{rule} options-first
An option is a form among the items after the name and the positional arguments, whose head is
one of the options of the form. In every form, the options come before the body, in any order. An
option after the first item of the body is an error, such as "(x …) is an optional argument, so
it comes before the canvas's body" (`compiler.py:3599`).
```

:::{admonition} Code differs
:class: note
The compiler checks this rule in the bodies of the scene, of groups, rows and columns, of
animations, of `at-once` and `in-order`, of canvases, of controls and of listeners. It allows the
`(defaults …)` of a formula after its other items (`compiler.py:4905`, `formula_decl`), the
`(font f)` of a readout after its listeners, and the `(kind k)` of a display after its listeners.
Bead mtp-ydd4.7.11 makes these errors.
:::

```{rule} options-once
Each option appears at most once in a form: a second one is an error, such as "'fill' is given
twice". `(pos p)` gives both `x` and `y`, so it does not appear together with either of them.
`(like x)`, in the forms that allow it (a shape, a motif or variant instance, a transition, a
move, a term and a font), comes before every other option.
```

```{rule} docstrings
Every declaration and every listener may have a docstring, `doc@'text'`, and at most one. The
docstring stands among the options ({numref}`options-first`), but it is not one of them. Its
string is plain: an interpolated string is an error.
```

So a docstring comes after the name and the positional arguments, the parameters of a function or a
motif included, and before the body. A variable in the body of a motif may have one, as any other
declaration. `(real k 1 doc@'d' (>= 0))` and `(func f ((real x)) doc@'d' (* 2 x))` are allowed, and
`(real k 1 (>= 0) doc@'d')` and `(func f ((real x)) (* 2 x) doc@'d')` are errors.

:::{admonition} Code differs
:class: note
The compiler removes a docstring from any place after the name (`compiler.py:7322`, `_take_doc`),
so a docstring after the body compiles. Bead mtp-ydd4.7.6 makes it an error. A variable in the
body of a motif may not have a docstring: `(motif m () (real k 1 doc@'d') …)` is the error
"unknown constraint 'doc'", because `compiler.py:4822` (`body_variable`) does not remove the
docstring. Bead mtp-qiro fixes this.
:::

## Bodies

```{rule} contexts
Each body holds only the kinds of item that {numref}`contexts-table` gives for it, and the `let`
and `foreach` forms that {numref}`body-let-foreach` allows. Any other item in a body is an error.
```

:::{table} The bodies of mtp. "let, foreach" is "yes" for a body that may hold a `let` and a `foreach` ({numref}`body-let-foreach`), and "no body" for a form that has no body.
:name: contexts-table

| Body | Options | Other items | let, foreach | Compiler |
|---|---|---|---|---|
| The top level of a source | none | `import`. Declarations of types (`type`), interfaces, namespaces, palettes, colormaps, functions (`func`, `func[T]`), motifs, variants, choreos, transitions and named animations. One `scene`. Formulas. Views (`canvas`, `readout`, `display`) and controls (`slider`, `button`, `play`, `stepper`, `toggle`). Variables of any type, `font` and `rand-seed` included. Not: shapes, listeners, `term`, uses of choreos. A `let` or a `foreach` here holds no `import` | yes | `top_here`, `expand` |
| The top level of a file to import | none | Only `import` and declarations of colors, fonts, functions, motifs, variants, types, interfaces, namespaces, palettes, colormaps, choreos, seeds (`rand-seed`) and variables that are `const`. A `let` or a `foreach` here holds no `import` | yes | `_not_importable` |
| `(scene name …)` | `(background …)`, `(transform …)` | Shapes: every shape, `group`, `row`, `column`, motif and variant instances. Variables. `exists-when` | yes | `scene_items` |
| `(group name …)`, `(row name …)`, `(column name …)` | the options of a group: `translate`, `transform`, `pointer-events`, `defaults`, `clip`, `fixed-size`, and for a row or a column `gap` and `align` | Shapes. `exists-when`. Not: variables | yes | `shape_here` |
| Any other shape, such as `(circle name …)` | the options of the shape | The string of a text, as a positional argument | no body | `shape_here` |
| A motif instance, `(M name …)` | its parameters, and the options of an instance: `x`, `y`, `pos`, `translate`, `transform`, `pointer-events`, `defaults`, `clip`, `like` | None: "an instance of M takes no members" | no body | `instance` |
| A variant instance | the options of its base shape, and the parameters of the variant | None | no body | `variant_instance` |
| `(motif name params …)` | none | Shapes. Variables that are bound or known when compiling. `exists-when`. Not: `animation` (a choreo is the template of animations), uses of choreos, `motif`, `scene` | yes | `instance` |
| `(variant name params shape)` | none | Exactly one shape, which is not a group | no | `variant_decl` |
| `(func name params body)` | none | Exactly one expression | no | `func_decl` |
| `(type name base …)` | none | Constraints | yes | `type_decl` |
| `(interface name …)` | none | Items `(T attribute constraint…)` | yes | `interface_decl` |
| `(namespace name …)` | none | Variables, namespaces, palettes. Not: functions, types, motifs, variants, shapes, components, transitions, animations, imports, interfaces, colormaps, choreos | yes | `namespace_decl` |
| `(palette name …)` | none | Items `(member color)`. Not: palettes, namespaces | yes | `palette_decl` |
| `(formula name …)` | `(defaults …)`, at most once | Exactly one string, plain or TeX, known when compiling. `(term …)`, `exists-when`, variables. In the order of {numref}`formula-terms` | yes | `formula_decl` |
| `(term name …)` | `(like t)` first, then items `(attribute value)`, `(tex …)` among them | None | no body | `term_form` |
| A variable, `(T name value? …)` | none | Constraints, such as `(>= 0)` | yes | `declared` |
| `(transition name target …)`, `(move target …)` | `like` first, then `from`, `to`, `duration`, `ease`, `path` | None | no body | `transition` |
| `(animation name …)`, `(animation …)` in a control or a listener, `(choreo name params …)` | `(defaults …)`, `(loop …)` | Steps: `move`, `wait`, `roll-dice`, `at-once`, `in-order`, the name of an animation or a transition, a use of a choreo | yes | `anim_body`, `steps` |
| `(at-once …)`, `(in-order …)` | `(defaults …)` | The steps of an animation. Not: `loop` | yes | `steps` |
| `(canvas name …)` | `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom`, `toggle-duration`, `toggle-ease` | Its content: names of shapes or of the scene, lists, and expressions that give a shape, `none` or a list of shapes, such as `(when c d)`. Listeners | yes | `component`, `build_canvas` |
| `(readout name value …)` | `(font f)` | The listeners `on-live` and `on-quiet` | yes | `component`, `build_readout` |
| `(display name formula …)` | `(kind k)` | Listeners on the terms of its formula (`on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-drag`), `on-live`, `on-quiet` | yes | `component`, `listened` |
| A control, such as `(slider name …)` | its options, among them `(in view…)` and its animation, written `(animation …)`, `(move …)` or a use of a choreo | Its positional argument: the move of a slider, the target of a toggle. Conditions, such as `(>= k 0)` | yes | `component`, `writer` |
| A listener, inside the body of a view | its options, its animation among them. Not: `(in …)` | Its positional arguments: the shape or term that it listens to, and for some listeners a target. Conditions | yes | `component`, `listened`, `writer` |
| `(defaults …)` of a group or an instance | none | Items `(attribute value)` for the members of the container | yes | `group_defaults` |
| `(defaults …)` of an animation | none | `(duration …)`, `(ease …)` | yes | `steps` |
| `(defaults …)` of a formula | none | Items `(attribute value)` for the terms | yes | `formula_defaults` |
| `(clip shape)` | none | Exactly one circle, rect, ellipse, triangle, polygon or ring | no | `clip` |
| `(import file name…)` | none | The file, then the names to import, or no names to import the file whole | no | `imports` |
:::

```{rule} body-let-foreach
`(let ((name value) …) item…)`, `(foreach i n item…)`, `(foreach x list item…)` and
`(foreach ((i n) (x list) …) item…)` stand in a body for their items, with their names bound: once
for `let`, and once for each value for `foreach`. A `let` and a `foreach` may stand in every body
that holds declarations or any number of items, the top level of a source and of a file to import
included, and nowhere else. Their items are of the kinds that the body around them holds.
```

The column "let, foreach" of {numref}`contexts-table` follows from this rule. So a `let` and a
`foreach` never stand among the positional arguments or the options of a form, in a form that has no
body, or in a body that holds a fixed number of items, such as the body of a function or a variant.
`(let ((k 2)) (real a k))` may stand at the top level, a `let` may stand among the steps of an
animation, and `(circle c (let ((k 2)) (r k)))` is an error, because `(r k)` is an option of the
circle.

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

The `(defaults …)` of a formula is an option, so it comes before the body ({numref}`options-first`).
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

:::{admonition} Open question Q-grammar-10
:class: warning
Whether a listener on its own view names that view, as in `(on-view v (animation …))`, or leaves
the name out, as in `(on-view (animation …))` today. The comment at `compiler.py:178`
(`OWN_VIEW_NAMED = False`) points to bead mtp-6k7f, which holds this question.
:::

## Imports

```{rule} import-declares-names
An `(import …)` declares the names that it gives at its place in the file.
```

By {numref}`declare-before-use`, a name that an import gives is then used only after the import.
An import need not come before the forms that do not use its names. So
`(scene s (circle c (fill colors.tab10-named.red))) (import colors)` is an error, and the same
two forms in the other order are allowed.

:::{admonition} Code differs
:class: note
`compiler.py:745` (`imports`) reads every import of a file before any other form, so an import may
come after the forms that use its names. Bead mtp-ydd4.7.12 makes such a use an error.
:::

## An example

This file has each form in a body that allows it: a variable, its docstring and its constraints at
the top level, the options of the scene before its shapes, a `foreach` of shapes in the scene, and
a canvas and a slider at the top level.

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
