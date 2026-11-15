# Compiler and runtime

Two programs implement mtp. The {term}`compiler` turns a source file into a {term}`.mtpc`, and
the {term}`runtime` turns a .mtpc into a {term}`live model` in a browser. This page defines what
each program must do and must never do, the .mtpc as the only thing that passes between the two programs, and what an implementation of either
program must do to conform to this spec.
The format of the .mtpc is defined in {doc}`compiled-format`, and is not repeated here.

## People and artifacts

Three people take part. The {term}`illustrator` writes a {term}`world model` as an `.mtp` source file.
The {term}`author` writes a page and places {term}`components <component>` of the world model in
it. The {term}`reader` opens the page and acts on the components. One person may be both the
illustrator and the author. The illustrator runs the compiler on their own machine, and the runtime
runs in the reader's browser. mtp requires no particular tool for making the page: the author may
use any software for making web pages, an AI assistant included, and is encouraged to use the
tools that they already prefer.

A component is a view, a control or a listener. A {term}`view` shows the world model to the
reader: a canvas draws shapes, a readout shows a line of text, and a display shows a formula. A
{term}`control` is a slider, a button, a play, a stepper or a toggle, and the reader presses, drags
or clicks it to change a value of the world model. A {term}`listener` is written inside a view and
has no element of its own on the page: it changes a value of the world model when the reader acts
on a shape or a term of that view, or when the view changes, for example when it comes into
sight. The illustrator declares every component, and the author places each view and control on
the page with an element of its own.

<figure class="mtp-diagram">
<svg viewBox="0 0 480 480" role="img" aria-labelledby="mtp-d-title"><title id="mtp-d-title">The illustrator writes the .mtp, which the compiler compiles into the .mtpc. The author writes the page. The .mtpc, the runtime script and the page make the open page in the reader’s browser, where the runtime holds one live model for each .mtpc and serves the components, which the reader sees and acts on.</title><defs><marker id="mtp-d-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="mtp-d-headpath" d="M0 0 L10 5 L0 10 z"/></marker></defs><rect class="mtp-d-person" x="15.0" y="16" width="140" height="36" rx="18.0"/><text class="mtp-d-name" x="85.0" y="39.0" text-anchor="middle">illustrator</text><rect class="mtp-d-person" x="325.0" y="16" width="140" height="36" rx="18.0"/><text class="mtp-d-name" x="395.0" y="39.0" text-anchor="middle">author</text><line class="mtp-d-arrow" x1="85" y1="52" x2="85" y2="94" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="93" y="78" text-anchor="start">writes</text><line class="mtp-d-arrow" x1="395" y1="52" x2="395" y2="94" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="403" y="78" text-anchor="start">writes</text><rect class="mtp-d-file" x="15.0" y="96" width="140" height="36" rx="6"/><text class="mtp-d-code" x="85.0" y="119.0" text-anchor="middle">.mtp</text><rect class="mtp-d-file" x="325.0" y="96" width="140" height="36" rx="6"/><text class="mtp-d-name" x="395.0" y="119.0" text-anchor="middle">page</text><line class="mtp-d-arrow" x1="85" y1="132" x2="85" y2="178" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="93" y="152" text-anchor="start">the compiler</text><text class="mtp-d-label" x="93" y="166" text-anchor="start">compiles it</text><rect class="mtp-d-file" x="15.0" y="180" width="140" height="48" rx="6"/><text class="mtp-d-code" x="85.0" y="209.0" text-anchor="middle">.mtpc</text><rect class="mtp-d-file" x="175.0" y="180" width="140" height="48" rx="6"/><text class="mtp-d-name" x="245.0" y="200.5" text-anchor="middle">runtime script</text><text class="mtp-d-code" x="245.0" y="217.5" text-anchor="middle">mathterpiece.js</text><line class="mtp-d-arrow" x1="85" y1="228" x2="85" y2="268" marker-end="url(#mtp-d-head)"/><line class="mtp-d-arrow" x1="245" y1="228" x2="245" y2="268" marker-end="url(#mtp-d-head)"/><line class="mtp-d-arrow" x1="395" y1="132" x2="395" y2="268" marker-end="url(#mtp-d-head)"/><rect class="mtp-d-live" x="15" y="270" width="450" height="112" rx="10"/><text class="mtp-d-livename" x="31" y="292">open page, in the reader’s browser</text><rect class="mtp-d-part" x="35" y="306" width="190" height="58" rx="6"/><text class="mtp-d-name" x="130.0" y="331.5" text-anchor="middle">runtime</text><text class="mtp-d-sub" x="130.0" y="348.5" text-anchor="middle">one live model for each .mtpc</text><rect class="mtp-d-part" x="255" y="306" width="190" height="58" rx="6"/><text class="mtp-d-name" x="350.0" y="331.5" text-anchor="middle">components</text><text class="mtp-d-sub" x="350.0" y="348.5" text-anchor="middle">views, controls, listeners</text><line class="mtp-d-arrow" x1="225" y1="335" x2="253" y2="335" marker-end="url(#mtp-d-head)"/><line class="mtp-d-arrow" x1="350" y1="364" x2="350" y2="428" marker-start="url(#mtp-d-head)" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="358" y="402" text-anchor="start">sees, acts on</text><rect class="mtp-d-person" x="280.0" y="430" width="140" height="36" rx="18.0"/><text class="mtp-d-name" x="350.0" y="453.0" text-anchor="middle">reader</text></svg>
</figure>

| Artifact | Made by | What it is |
|---|---|---|
| the `.mtp` | the illustrator | the source of one world model |
| the `.mtpc` | the compiler | the {term}`compiled model` of one world model |
| the {term}`runtime script`, `mathterpiece.js` | the implementation of mtp, the same for every world model | the runtime, and the page elements that it defines |
| the page | the author, with any tool for making web pages | the text, the elements that load .mtpc files, and the elements that place components |
| the {term}`open page` | the reader's browser, from the page | the page with the runtime running in it, and one live model for each .mtpc that the page loads |

The smallest world model that draws something has a scene with one circle and a canvas that
draws the scene. This is the source smallest.mtp, 34 bytes:

```{literalinclude} pages/smallest/smallest.mtp
:language: mtp
```

```{mtpc-of} pages/smallest/smallest.mtp
```

The smallest page that shows the canvas, smallest.html, is the following, placed next to
smallest.mtpc and mathterpiece.js:

```{literalinclude} pages/smallest/smallest.html
:language: html
```

```{raw} html
<p><a href="pages/smallest/smallest.html">Open smallest.html</a>.</p>
```

An empty file is a world model too ({numref}`contexts-table`), but it has nothing to draw.

## The steps of compiling

```{rule} compile-steps
The compiler turns a source into a .mtpc in six steps, in this order:

1. **Parse.** The {term}`parser` reads the text into {term}`forms <form>`, by the syntax alone
   ({doc}`lexical`, {doc}`grammar`). It looks up no {term}`name`.
2. **Rewrite.** Every name is resolved to its declaration ({ref}`scope`), and every {term}`sugar`
   form is rewritten into {term}`core forms <core form>` ({numref}`sugar-form`). For example, `(pos [1 2])`
   becomes `(x 1) (y 2)`. No value is computed and no type is used.
3. **Prove.** Every {term}`expression` is given a type, and every type, {term}`range`,
   {term}`constraint` and other invariant that the spec requires is proved ({doc}`types`,
   {doc}`well-formedness`). This step proves and does nothing else.
4. **Expand.** Each `foreach` is written out as its copies, each motif instance as the
   {term}`body` of its motif with the arguments of the instance, and each use of a choreo as the
   body of its choreo with the arguments of the use. In the copies, the instances and the uses,
   the names built from values are replaced ({numref}`names-from-values`).
5. **Fold.** Every expression known when compiling ({doc}`binding-time`) is replaced by its
   value.
6. **Write.** The model is written as the .mtpc ({doc}`compiled-format`), with every type that the
   runtime needs.
```

So a check that the parts of a sugar form are known when compiling is made in the prove step, and
every core form other than `foreach`, a motif instance and a use of a choreo reaches the fold step
as it is. Which forms are sugar, and the {term}`rewrite` of each, are defined in {doc}`core`.

```{rule} prove-bodies-once
The prove step proves each body once: the body of a function with each parameter ranging over
every value of its declared type, the body of a `foreach` with its variable ranging over every
value of its range, and the body of a motif or a choreo with each parameter ranging over every
value of its declared type and constraints. An imported motif or choreo is proved once, in the file
that declares it. The copies that a `foreach` makes, the instances of a motif and the uses of a
choreo are not proved again. A motif or choreo body that is safe for only some values of a
parameter is a {term}`compile error`, unless the parameter declares a constraint that leaves out
the other values. An expression is known in the prove step when it is known when compiling
({doc}`binding-time`) and does not read, inside the body of a `foreach`, a function, a motif or a
choreo, the variable of that `foreach` or a parameter of that function, motif or choreo.
```

So an error in such a body is about the body as written, and not about a copy or an instance. For
example,
`(motif dot ((real k)) (circle_ (r (/ 1 k))))` is a compile error at `(/ 1 k)`, since
`k` may be 0, whatever the instances give for `k`. With `(real k 1 (>= 1))` as the parameter, the
motif compiles.

```{rule} step-rejects-or-passes
The parse, rewrite and prove steps each either reject the source or pass their output to the next
step. The parse step rejects with a {term}`syntax error`, and the rewrite and prove steps with a
compile error ({doc}`errors`). When a step rejects the source, no later step runs. The
expand, fold and write steps never reject a source that the prove step passed, so the
compiler either rejects a source or writes a .mtpc that is valid by {doc}`compiled-format`, and
never both.
```

What the error of a rejected source holds is given in {numref}`conformance`.

```{rule} prover-finds-ranges
To prove a range or a constraint, the {term}`prover` works out ranges ({numref}`ranges`,
{numref}`range-rules`). The prover writes nothing into the model. Where the range of a bound
value does not lie inside the constraint of the value, the prover gives the value a type that includes `none`, and the write step writes the `check`
that this type needs ({doc}`compiled-format`).
```

So `(circle c (r (- 1 2)))` is a compile error in the prove step, since the range of `(- 1 2)` is
-1 alone, and so is `(/ 1 0)`, since its divisor is 0 alone ({numref}`none-at-known-inputs`).

:::{admonition} Code differs
:class: note
Today the rewrite, prove, expand and fold steps are not separate, and expanding comes before
proving. `_Compiler.run` in mathterpiece/compiler.py, line 586, goes through the top-level forms
once, and each form is rewritten, expanded, checked and {term}`folded <folding>` as it is reached.
`foreach` copies are made one at a time by `_Compiler.expand` (line 828), and the body of a motif is
compiled again for each instance by `_Compiler.instance` (line 4674), so each copy and each instance
is proved on its own. `_Compiler.call` (lines 1962 to 1973) folds a call and then checks its
constraint against the folded value. The new middle of the compiler (mtp-08wd) follows these rules.
The order of the steps and proving each body once are mtp-08wd.1.
:::

## Running the compiler

```{rule} compiler-input-output
The compiler is given one source file. It reads that file and the files that it imports
({numref}`compiler-reads-files`), and then either rejects the source with an error
({numref}`conformance`) and writes no .mtpc, or writes one .mtpc for it.
```

How the compiler is run, such as the name of a command, its options, where it writes the .mtpc and
what it prints, is not part of this spec ({numref}`what-is-normative`). An implementation may offer
other tools with the compiler, such as a formatter for sources or a page that shows every component
of a world model, and these are not part of this spec either.

## What the compiler must do and must never do

The compiler resolves every name, gives every expression a type and proves it, and either rejects
the source or writes a valid .mtpc, by {numref}`compile-steps` and {numref}`step-rejects-or-passes`.

```{rule} compiler-decides-early
Everything that can be decided when compiling is decided when compiling, even when that makes
compiling slower. Nothing that the compiler could have decided is left for the runtime to decide
while the reader waits.
```

```{rule} compiler-same-bytes
The compiler is deterministic: the same source and the same imported files always give the same
bytes ({doc}`compiled-format`, "Same source, same bytes").
```

```{rule} compiler-reads-files
The compiler reads only the source file and the files that it imports, directly or through other
imports. An import is looked for in the folder of the file that imports it, then in the standard
{term}`library` ({ref}`scope`, {doc}`stdlib`).
```

```{rule} compiler-never-acts-while-drawing
The compiler never does what happens only while drawing ({doc}`binding-time`). It never runs a
writer: it never plays an animation, never performs a write that a control or a listener
would perform, and never acts as a reader would. It never reads a page, its CSS or its color scheme,
and so never folds a token: a token is written with its declared value, which the runtime uses where
the page gives none.
```

So the compiler never draws a random value, since a random value is known only while drawing
({numref}`random-never-folded`).

## From the .mtpc to the open page

This section follows one world model from its source to an open page. It states no rule: the
rules are in the sections after it and in {doc}`page-interface`.

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
3. The runtime builds the live model of dial.mtpc, once: the free variable `a` takes its
   starting value 0.6, and every bound value is computed from it
   ({numref}`runtime-builds-live-model`). The page refers to this live model by the `id` attribute
   of the element, `dial`.
4. In each element whose `model` attribute is `dial`, the runtime draws the component of
   that live model that the element's `name` attribute gives: the canvas `v`, the slider `turn` and
   the readout `now` ({numref}`runtime-serves-components`). The author may place these elements
   anywhere in the page, inside a sentence too.
5. When the reader drags the slider, the slider writes `a`. The position of `dot` and the text of
   `now` are computed again, and the canvas and the readout draw again
   ({numref}`runtime-builds-live-model`).

The page needs nothing else: it holds no script of its own, and calls no function of the runtime.

## What the runtime must do and must never do

```{rule} runtime-loads-mtpc
The runtime loads each .mtpc given by the `src` attribute of an `<mtp-model>` element, once,
from a file that it fetches or from a block in the page ({doc}`page-interface`). When the .mtpc
cannot be fetched or read as JSON, the model fails to load, and the error takes the place of every
component of that model on the page. The runtime reads only .mtpc files that state a version of
this spec that it implements, and which versions those are is not normative. It refuses a .mtpc of
another version, a .mtpc that does not match the schema of
its version ({doc}`compiled-format`), and every {term}`corrupt <corrupt .mtpc>` .mtpc
({numref}`corrupt-mtpc`). A .mtpc that the runtime refuses fails to load too, and the runtime runs
no part of it. For a .mtpc of another version, the error gives both versions.
```

:::{admonition} Code differs
:class: note
The runtime checks the version and the schema (web/src/elements.ts, web/src/schema.ts), but it
does not look for corrupt files. A corrupt .mtpc either makes the `Runtime` constructor throw, so
that the model fails to load with that message, or throws later, when a component draws, or draws
something wrong with no error. mtp-ydd4.7.27.
:::

```{rule} no-errors-after-loading
Once a .mtpc has loaded, nothing that a reader does and nothing that the runtime computes makes a
component or the page fail or show an error. A source in which something could fail after loading
is rejected when compiling, and a .mtpc in which something could fail is refused when it is
loaded ({numref}`runtime-loads-mtpc`).
```

This rule follows from a principle of the design of mtp: a state that breaks a rule of the spec
cannot be represented. No source can declare such a state, since the compiler proves every type
and constraint before the page opens. No reader can reach one, since a computation that has no
value gives the value `none` instead of failing, and a write is brought into the constraints of
what it is written into. For example, a line declared `line|none` is not drawn while it is `none`
({numref}`operations-that-give-none`, {doc}`evaluation`), and a write of -1 into a variable
declared with `(>= 0)` writes 0 ({numref}`writes-into-constraints`). The principle is a goal of
the design: where the spec still allows a state that breaks a rule, the spec has a gap, and the
gap is closed by changing the language, never by showing an error to the reader.

```{rule} runtime-builds-live-model
When a .mtpc loads, the runtime builds its live model, once, before any component draws: it turns
every expression into a function, once, and gives every free variable and attribute its starting
value, reading each `free@` start once ({doc}`compiled-format`, "Free and bound values"). Then it
keeps the live model current as the reader acts: after each write, it computes again only what
depends on what changed, and the views draw again ({doc}`reaction`, {doc}`time`,
{doc}`concurrency`).
```

```{rule} runtime-serves-components
The runtime defines one page element for each kind of view and control, and
serves each element that the page places: in each element, it draws the view or control of the
element's model that the element's `name` attribute gives. A listener has no element: it
acts on each element that draws its shape or term, or, for a listener such as `on-view`, on its
own view ({doc}`page-interface`, {doc}`lifecycle`).
```

```{rule} runtime-adds-no-objects
What a world model holds is decided by the illustrator alone: the objects of a live model are
those that the source declares, and the runtime never adds an object to a live model or removes
one. What the runtime draws beyond the objects of the live model changes only how a component
looks. It is not an object of the live model, no expression and no writer of the world model reads
it, and it never changes a value of the live model.
```

For example, while an `on-show` or an `on-hide` plays, a canvas draws a stand-in in place of the
shape: a copy of the shape that only this canvas has, which the animation moves. The shape in the
live model keeps every attribute as it was, and when the animation ends, the canvas drops the
stand-in ({doc}`page-interface`).

```{rule} runtime-no-type-work-while-drawing
While drawing, the runtime never checks whether a value has its type, and never converts a value
from one type to another. The compiler has proved every type, and every type that the runtime
needs is written in the .mtpc. Bringing a written value into the constraints of what it is written
into, by clamping, rounding, wrapping or holding it ({doc}`types`), is part of what a write does,
and is not a check of a type. How the runtime does this is not normative.
```

## The .mtpc between the compiler and the runtime

```{rule} any-compiler-any-runtime
Every conforming compiler works with every conforming runtime. Every conforming runtime that
implements the version of this spec that a .mtpc states runs it, whichever conforming compiler wrote it.
Two conforming compilers may write different bytes for one source ({numref}`what-is-normative`),
and every conforming runtime makes the same open page from both files.
```

So an implementation of the compiler and an implementation of the runtime can be built apart, by
different people and in different languages, and the .mtpc is the only thing that each needs to
know of the other. This is why the format of the .mtpc is defined in full in {doc}`compiled-format`.

```{rule} mtpc-only-boundary
The .mtpc is the only thing that passes from the compiler to the runtime. No other file, no call
and no shared state passes between them. Besides the .mtpc, the runtime reads only the page: its
elements, the values that its CSS gives the tokens, its color scheme, the pointer, the keyboard and
the clock.
```

So the runtime never reads a source file, and every object, every motif instance and every copy
that a `foreach` makes is written out in the .mtpc ({numref}`compile-steps`).

```{rule} corrupt-mtpc
A .mtpc that matches the schema of its version and breaks a rule of this spec is
corrupt. Among the corrupt files are a .mtpc with a reference to an
object or a function that it does not hold, one with an expression that can give a value of
another type than the type written with it, one with a `deps` list that leaves out something that
its expression can read, and one with an expression known when compiling that is not folded. A
conforming compiler never writes a corrupt .mtpc.
```

```{rule} schema-strength
The schema of each version of this spec holds every rule of {doc}`compiled-format` that a JSON
schema can express, so that as few corrupt files as possible match it.
```

So the runtime refuses a corrupt .mtpc ({numref}`runtime-loads-mtpc`), although it matches the
schema. How the runtime finds that a .mtpc is corrupt is not part of this spec.

```{rule} spec-version
The versions of this spec are numbered 1, 2, 3 and so on. A version gets the next number when it
is published, and the draft of a version states the number that it will have. Every .mtpc states,
as the whole number in its member `mtpc`, the version of this spec that its compiler implements.
The format of the .mtpc and its schema are part of this spec, so two .mtpc files that state the
same version are read by the same rules.
```

:::{admonition} Code differs
:class: note
The .mtpc states a version of its format, 4, and this spec has no version yet. Bead mtp-ydd4.7.60.
The runtime also reads an older form of version 4: a listener with no `in`, or with several views in
`in`, is heard in every view that shows its shape (`heardIn` in web/src/click.ts, line 35). The compiler (mathterpiece/mtpc.py, line 31) and the runtime
(web/src/doc.ts, line 152) both use version 4, so two version 4 files can follow different rules.
mtp-ydd4.7.17.
:::

## Conformance

```{rule} what-is-normative
These are normative, and every conforming implementation gives the same: which sources are
accepted and which are rejected, the meaning of the .mtpc, and what the runtime does. These are
not normative: everything about an error beyond what {numref}`conformance` requires, such as its
wording and the position that it gives, the bytes of the .mtpc, and how the compiler is run
({numref}`compiler-input-output`).
```

So two conforming compilers may write different bytes for one source, as long as a runtime builds
the same live model from both. For example, the members of a JSON object may be written in any
order, so one compiler may write `{"r": 1, "x": 0}` where another writes `{"x": 0, "r": 1}`.

```{rule} conformance
- An implementation of the compiler conforms to this spec when, for every source and the files
  that it imports, it rejects the source if and only if this spec rejects it, and otherwise writes
  a .mtpc that has the meaning that {doc}`compiled-format` defines for the world model of the
  source. Every error that rejects a source carries the label of at least one rule that the source
  breaks, among the rules checked in the step that rejects the source
  ({numref}`step-rejects-or-passes`). The label of a rule is the name that this spec gives it, such
  as `declare-before-use`. When the source breaks several of these rules, the error carries the
  label of any one of them, of several, or of all.
- An implementation of the runtime conforms when it loads every valid .mtpc of the versions that
  it implements, and builds and keeps current its live model as the pages from {doc}`world-model`
  to {doc}`accessibility` define.

Each conforms only when it also obeys every rule of this page about it.
```

:::{admonition} Code differs
:class: note
An error carries no label of a rule. `CompileError` (mathterpiece/compiler.py, line 402) and
`ParseError` (mathterpiece/parse.py, line 39) hold only a message and a position. Bug
mtp-ydd4.7.53.
:::
