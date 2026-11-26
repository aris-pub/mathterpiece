# Compiler and runtime

Two programs implement mtp. The {term}`compiler` turns a source file into a {term}`.mtpc`, and
the {term}`runtime` turns a .mtpc into a {term}`live model` in a browser. This page defines what
each program must do and must never do, the .mtpc as the only file that passes between the two programs, and what an implementation of either
program must do to conform to this spec.
The format of the .mtpc is defined in {doc}`compiled-format`, and is not repeated here.

## People and artifacts

Three people take part. The {term}`illustrator` writes a {term}`world model` as an `.mtp` source file.
The {term}`author` writes a page and places {term}`components <component>` of the world model in
it. The {term}`reader` opens the page and acts on its {term}`page objects <page object>`. One person may be both the
illustrator and the author. The illustrator runs the compiler on their own machine, and the runtime
runs in the reader's browser. mtp requires no particular tool for making the page: the author may
use any software for making web pages, an AI assistant included, and is encouraged to use the
tools that they already prefer.

A page object is a view, a control or a listener. A component is a view or a control: the author
places each one on the page. A control and a listener are {term}`writers <writer>`. A {term}`view` is where the runtime draws part of the world
model for the reader: shapes in a canvas, a line of text in a readout and a formula in a display. A
{term}`control` is a slider, a button, a play, a stepper or a toggle, and the reader presses, drags
or clicks it to write to a variable or an attribute of the world model. A {term}`listener` is written inside a view and
has no element of its own on the page: it writes to a variable or an attribute of the world model when the reader acts
on a shape or a term of that view, or when the view changes, for example when it comes into
sight. The illustrator declares every component, and the author places each view and control on
the page with an element of its own.

```{diagram} people-and-programs
:file: diagrams/people-and-programs.svg

The illustrator, the author and the reader, the files that each one makes or uses, and the two programs: the compiler, which makes the .mtpc, and the runtime, which runs in the reader's browser.
```

| Artifact | Made by | What it is |
|---|---|---|
| the `.mtp` | the illustrator | the source of one world model |
| the `.mtpc` | the compiler | the {term}`compiled model` of one world model |
| the {term}`runtime script`, `mathterpiece.js` | the implementation of mtp, the same for every world model | the runtime, and the page elements that it defines |
| the page | the author, with any tool for making web pages | the text, the elements that load .mtpc files, and the elements that place components |
| the {term}`open page` | the reader's browser, from the page | the page with the runtime running in it, and one live model for each .mtpc that the page loads |

The smallest world model that has something to draw has a scene with one circle and a canvas that
draws the scene. This is the source smallest.mtp, 34 bytes:

```{literalinclude} pages/smallest/smallest.mtp
:language: mtp
```

```{mtpc-of} pages/smallest/smallest.mtp
```

The smallest page that places the canvas, smallest.html, is the following, placed next to
smallest.mtpc and mathterpiece.js:

```{literalinclude} pages/smallest/smallest.html
:language: html
```

```{raw} html
<p><a href="pages/smallest/smallest.html">Open smallest.html</a>.</p>
```

An empty file is a world model too ({numref}`top-level-forms`), but it has nothing to draw.

## The steps of compiling

This rule exists so that every compiler does the same work in the same order, and so that later rules can name the step in which they apply.

```{rule} compile-steps
The compiler turns a source into a .mtpc in six steps, in this order:

1. **Parse.** The {term}`parser` reads the text into {term}`forms <form>`, by the syntax alone
   ({doc}`lexical`, {doc}`grammar`).
2. **Rewrite.** Each {term}`name` is resolved to its declaration ({ref}`scope`), and each
   {term}`syntactic sugar` form is rewritten into {term}`core forms <core form>` ({numref}`sugar-form`).
3. **Prove.** Each {term}`expression` except a {term}`clause` gets a type, each clause is checked against
   the form around it, and each {term}`condition` and {term}`range` is proved ({doc}`types`, {doc}`well-formedness`).
4. **Expand.** The forms that need a type or a value to be rewritten are rewritten, and each
   `foreach`, motif and animation is written out as its copies, with the names built from values
   replaced ({numref}`names-from-values`).
5. **Fold.** Each expression known when compiling is replaced by its value ({doc}`binding-time`).
6. **Write.** The model is written as the .mtpc ({doc}`compiled-format`).
```

So a check that the parts of a syntactic sugar form are known when compiling is made in the prove step, and
every core form other than `foreach`, `(M …)` for a motif `M` and `(A …)` for an animation `A` reaches the fold step
as it is. Which forms are syntactic sugar, and the {term}`rewrite` of each, are defined in {doc}`core`.

This rule exists so that a body that compiles works for every call and every copy of it, including calls added later, and so that compiling takes no longer as calls and copies are added.

```{rule} check-bodies-once
The prove step checks the body of each function, `foreach`, motif and animation once, with each
parameter or variable ranging over every value that it can take. Its copies and calls are not
checked again, and an imported body is checked in its own file. A body that is safe for only some
of those values is a {term}`compile error`. An expression is known in the prove step when it is known
when compiling ({doc}`binding-time`) and reads no parameter or variable of a body around it.
```

So an error in such a body is about the body as written, and not about a copy or about one `dot`. For
example,
`(motif dot ((real k)) (circle_ (r (/ 1 k))))` is a compile error at `(/ 1 k)`, since
`k` may be 0, whatever each `dot` gives for `k`. With `(real k 1 (>= 1))` as the parameter, the
motif compiles.

This rule exists so that compiling a source gives either one error from one step or a complete .mtpc, and never a partial .mtpc.

```{rule} step-rejects-or-passes
Each of the parse, rewrite and prove steps either rejects the source, the parse step with a
{term}`syntax error` and the others with a compile error ({doc}`errors`), or passes it on. No step runs
after a rejection, and the later steps never reject. So the compiler either rejects a source or
writes a valid .mtpc ({doc}`compiled-format`).
```

What the error of a rejected source holds is given in {numref}`conformance`.

This rule exists to specify what the compiler does when it cannot prove a condition of a bound container, instead of rejecting the source.

```{rule} prover-finds-ranges
The {term}`prover` proves conditions by working out ranges ({numref}`ranges`). Where the range of a bound
container does not lie inside its conditions, the type of the container includes `none`, and the
.mtpc holds the `check` for it ({doc}`compiled-format`).
```

So `(circle c (r (- 1 2)))` is a compile error in the prove step, since the range of `(- 1 2)` is
-1 alone, and so is `(/ 1 0)`, since its divisor is 0 alone ({numref}`none-at-known-arguments`).

:::{admonition} Code differs
:class: note
Today the rewrite, prove, expand and fold steps are not separate, and expanding comes before
proving. `_Compiler.run` in mathterpiece/compiler.py, line 586, loops once over the top-level forms,
and rewrites, expands, checks and {term}`folds <folding>` each form in turn.
`foreach` copies are made one at a time by `_Compiler.expand` (line 828), and the body of a motif is
compiled again for each shape of the motif by `_Compiler.instance` (line 4674), so each copy and each such
shape is checked on its own. `_Compiler.call` (lines 1962 to 1973) folds a call and then checks its
constraint against the folded value. The new middle of the compiler (mtp-08wd) follows these rules.
Bead mtp-08wd.1 changes the compiler to use this order of steps and to check each body once.
:::

## Running the compiler

This rule exists to fix what the compiler is given and what it produces.

```{rule} compiler-input-output
The compiler is given one source file, and either rejects it with an error ({numref}`conformance`) or
writes one .mtpc for it.
```

How the compiler is run, such as the name of a command, its options, where it writes the .mtpc and
what it prints, is not part of this spec ({numref}`what-is-normative`). An implementation may offer
other tools with the compiler, such as a formatter for sources or a page on which every component
of a world model is placed, and these are not part of this spec either.

## What the compiler must do and must never do

The compiler resolves every name, gives every expression except a clause a type and proves it, and either rejects
the source or writes a valid .mtpc, by {numref}`compile-steps` and {numref}`step-rejects-or-passes`.

This rule exists because the reader waits for the runtime, and not for the compiler.

```{rule} compiler-decides-early
Everything that can be decided when compiling is decided when compiling, even when that makes
compiling slower.
```

This rule exists so that a .mtpc can be rebuilt, compared and cached by its bytes.

```{rule} compiler-same-bytes
The same source and the same imported files always give the same .mtpc, byte for byte
({doc}`compiled-format`).
```

This rule exists so that the files that the compiler reads, and so the .mtpc that it writes, follow from the source alone.

```{rule} compiler-reads-files
The compiler reads only the source and the files that it imports, directly or not. An import is
looked for next to the file that imports it, then in the {term}`standard library` ({doc}`stdlib`).
```

This rule exists because what happens while drawing depends on the reader and on the page, and neither is there when compiling.

```{rule} compiler-never-acts-while-drawing
The compiler never does what happens only while drawing ({doc}`binding-time`): it never runs a
writer and never reads a page. So it never folds a font: a font is written with its declared value,
which the runtime uses where the page sets none.
```

So the compiler never draws a random value, since a random value is known only while drawing
({numref}`random-never-folded`).

## From the .mtpc to the open page

In this section, one world model is taken from its source to an open page. This section has no
rules: the rules are in the sections after it and in {doc}`page-interface`.

The illustrator writes the source dial.mtp:

```{literalinclude} pages/dial/dial.mtp
:language: mtp
```

The compiler compiles dial.mtp into dial.mtpc, and the author writes the page dial.html:

```{literalinclude} pages/dial/dial.html
:language: html
```

Below is that page, served from a folder that holds dial.html, dial.mtpc and mathterpiece.js, as
the author would serve it.

```{raw} html
<iframe class="mtp-page" src="pages/dial/dial.html" title="The page dial.html, open"></iframe>
<p><a href="pages/dial/dial.html">Open dial.html on its own</a>.</p>
```

When the reader opens the page, the browser and the runtime do the following, in this order:

1. The browser reads the page. The `<script>` element loads the runtime script, which defines
   the page elements `<mtp-model>`, `<mtp-canvas>`, `<mtp-slider>`, `<mtp-readout>` and the
   others ({numref}`runtime-serves-components`). The `<link>` element loads the stylesheet that
   draws the controls, and the `<style>` element holds the author's own CSS, which sets the width
   of the canvas.
2. For the `<mtp-model>` element, the runtime fetches the file that its `src` attribute names,
   dial.mtpc, and checks it ({numref}`runtime-loads-mtpc`). The `src` attribute may instead name a
   block `<script type="application/json">` of the page that holds the .mtpc, as in
   `src="#dial-data"` ({doc}`page-interface`).
3. The runtime builds the live model of dial.mtpc, once: the free variable `a` is given its
   starting value 0.6, and every bound variable and attribute is computed from it
   ({numref}`runtime-builds-live-model`). The page refers to this live model by the `id` attribute
   of the element, `dial`.
4. In each element whose `model` attribute is `dial`, the runtime draws the component of
   that live model that the element's `name` attribute gives: the canvas `v`, the slider `turn` and
   the readout `now` ({numref}`runtime-serves-components`). The author may place these elements
   anywhere in the page, inside a sentence too.
5. When the reader drags the slider, the slider writes to `a`. The position of `dot` and the text of
   `now` are computed again, and the canvas and the readout draw again
   ({numref}`runtime-builds-live-model`).

Nothing else is needed in the page: it holds no script of its own and calls no function of the runtime.

## What the runtime must do and must never do

This rule exists to specify how the runtime gets each .mtpc, and what it does when it cannot.

```{rule} runtime-loads-mtpc
The runtime loads each .mtpc that an `<mtp-model>` element names, once ({doc}`page-interface`). It
refuses a .mtpc that it cannot fetch or read, one of a version that it does not implement, one that
does not match its schema, and a {term}`corrupt <corrupt .mtpc>` one ({numref}`corrupt-mtpc`). Which versions it
implements is not normative. It runs no part of a refused .mtpc, and shows the error in place of
each component of its model, with both versions when they differ.
```

:::{admonition} Code differs
:class: note
The runtime checks the version and the schema (web/src/elements.ts, web/src/schema.ts), but it
does not look for corrupt files. A corrupt .mtpc either makes the `Runtime` constructor throw, so
that the model fails to load with that message, or throws later, when a component draws, or draws
something wrong with no error. mtp-ydd4.7.27.
:::

This rule exists because a reader cannot fix an error.

```{rule} no-errors-after-loading
Once a .mtpc has loaded, nothing that the reader does and nothing that the runtime computes makes
the page show an error.
```

This rule follows from a principle of the design of mtp: a state that breaks a rule of the spec
cannot be represented. No source can hold such a state, since the compiler checks every type
and condition before the page opens. No reader can reach one, since a computation that has no
value gives the value `none` instead of failing, and a written value is brought into the conditions of
the container that it is written to. For example, a line declared `line|none` is not drawn while it is `none`
({numref}`expressions-that-give-none`, {doc}`evaluation`), and a write of -1 to a variable
declared with `(>= 0)` writes 0 ({numref}`writes-to-conditions`). The principle is a goal of
the design: where the spec still allows a state that breaks a rule, the spec has a gap, and the
gap is closed by changing the language, never by showing an error to the reader.

This rule exists to specify when the runtime does its work, so that it does each piece of work once and not on every frame.

```{rule} runtime-builds-live-model
When a .mtpc loads, before it draws anything, the runtime builds the live model once: it turns each
expression into a function and sets each free container to its starting value. After each write,
it computes again only what depends on what changed ({doc}`reactivity`).
```

This rule exists to specify how the elements of a page are tied to the views and controls of a model.

```{rule} runtime-serves-components
The runtime defines a page element for each kind of view and control, and in each one draws the
view or control that its `name` attribute names ({doc}`page-interface`). A listener has no element:
it acts in each element that draws its shape or term, or, for `on-view`, in its view
({doc}`lifecycle`).
```

This rule exists so that a world model holds exactly what its source declares, whatever the runtime draws.

```{rule} runtime-adds-no-objects
The objects of a live model are exactly those that its source creates ({doc}`data-model`). What the
runtime draws beyond them, such as a stand-in, only changes how a component looks: nothing reads it,
and it writes to nothing.
```

For example, while an `on-show` or an `on-hide` plays, the runtime draws a stand-in in the canvas in place of the
shape: a copy of the shape that only this canvas has, which the movement writes to. The shape in the
live model keeps every attribute as it was, and when the movement ends, the runtime drops the
stand-in.

This rule exists because the compiler has already checked every type, so checking types again while drawing would only slow the runtime.

```{rule} runtime-no-type-work-while-drawing
While drawing, the runtime never checks or converts a type, since the compiler has checked every
type. Bringing a written value into the conditions of its target is part of the write
({numref}`writes-to-conditions`), and not a type check.
```

## The .mtpc between the compiler and the runtime

This rule exists so that a compiler and a runtime can be written separately and still work together.

```{rule} any-compiler-any-runtime
Every conforming runtime runs every .mtpc of a version that it implements, whichever conforming
compiler wrote it, and makes the same page from any two .mtpc files of one source.
```

So an implementation of the compiler and an implementation of the runtime can be built apart, by
different people and in different languages, and the format of the .mtpc is all that the builders of each need to
know about the other. This is why the format of the .mtpc is defined in full in {doc}`compiled-format`.

This rule exists so that what the runtime does is determined by the .mtpc and the page alone.

```{rule} mtpc-only-boundary
The .mtpc is all that passes from the compiler to the runtime. Besides it, the runtime reads only
the page: its elements, the fonts that its CSS sets, its color scheme, the pointer, the keyboard and
the clock.
```

So the runtime never reads a source file, and every object, every shape of a motif and every copy
that a `foreach` makes is written out in the .mtpc ({numref}`compile-steps`).

This rule exists to name the .mtpc files that the runtime may refuse, even though they match the schema.

```{rule} corrupt-mtpc
A .mtpc that matches its schema but breaks a rule of this spec is corrupt, such as one that refers
to an object that it does not hold, or that leaves an expression known when compiling unfolded. A
conforming compiler never writes one.
```

This rule exists so that a runtime can catch as many corrupt files as possible with the schema alone.

```{rule} schema-strength
The schema of each version holds every rule of {doc}`compiled-format` that a JSON schema can express.
```

So the runtime refuses a corrupt .mtpc ({numref}`runtime-loads-mtpc`), although it matches the
schema. How the runtime finds that a .mtpc is corrupt is not part of this spec.

This rule exists so that the version of this spec that applies to a .mtpc can be read from the .mtpc alone.

```{rule} spec-version
The versions of this spec are numbered 1, 2, 3 and so on, in the order in which they are published,
and a draft states the number that it will have. Every .mtpc states, in its member `mtpc`, the
version that its compiler implements.
```

## Conformance

This rule exists to separate what every implementation must give the same from what each may choose.

```{rule} what-is-normative
Every conforming implementation gives the same: which sources are accepted, the meaning of each
.mtpc, and what the runtime does. Nothing else is normative, such as the wording of an error, the
bytes of a .mtpc, or how the compiler is run.
```

So two conforming compilers may write different bytes for one source, as long as a runtime builds
the same live model from both. For example, the members of a JSON object may be written in any
order, so one compiler may write `{"r": 1, "x": 0}` where another writes `{"x": 0, "r": 1}`.

This rule exists to define when an implementation of the compiler or of the runtime conforms to this spec.

```{rule} conformance
- A compiler conforms when it rejects exactly the sources that break a rule of this spec, and
  otherwise writes a .mtpc with the meaning that {doc}`compiled-format` defines. Each error carries
  the label of at least one broken rule checked in the step that rejects the source, such as
  `declare-before-use`.
- A runtime conforms when it loads every valid .mtpc of the versions that it implements, and keeps
  its live model as this spec defines.

Each conforms only when it also follows every rule of this page about it.
```

:::{admonition} Code differs
:class: note
An error carries no label of a rule. `CompileError` (mathterpiece/compiler.py, line 402) and
`ParseError` (mathterpiece/parse.py, line 39) hold only a message and a position. Bug
mtp-ydd4.7.53.
:::
