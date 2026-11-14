# Compiler and runtime

Two programs implement mtp. The {term}`compiler` runs on the illustrator's machine and turns a
source file into a {term}`.mtpc`. The {term}`runtime` runs in the reader's browser and turns a
.mtpc into a {term}`live model`. This part defines what each program must do and must never do,
the {term}`mtp command` that runs the compiler, the .mtpc as the only thing that passes between
the two programs, and what an implementation of either program must do to conform to this spec.
The format of the .mtpc is defined in {doc}`compiled-format`, and is not repeated here.

## People and artifacts

Three people take part. The {term}`illustrator` writes a world model as an `.mtp` source file.
The {term}`author` writes a page and places {term}`components <component>` of the world model in
it. The {term}`reader` opens the page and acts on the components. One person may be both the
illustrator and the author.

| Artifact | Made by | What it is |
|---|---|---|
| the `.mtp` | the illustrator | the source of one world model |
| the `.mtpc` | the mtp command | the compiled model of one world model |
| the {term}`runtime script`, `mathterpiece.js` | mtp, the same for every world model | the runtime, and the page elements that it defines |
| the page | the author, usually through a tool such as a Markdown converter | the text, the elements that load .mtpc files, and the elements that place components |
| the {term}`live figure` | the reader's browser, from the page | the runtime and the page together, with one live model for each .mtpc that the page loads |

The {term}`inventory page`, which `mtp build` writes, is outside this table. The illustrator uses
it to see the live figure while working, and the author uses it to learn which components a world
model has and how to place each one.

## The steps of compiling

```{rule} compile-steps
The compiler turns a source into a .mtpc in five steps, in this order:

1. **Parse.** The {term}`parser` reads the text into forms, by the syntax alone ({doc}`lexical`,
   {doc}`grammar`). It looks up no name.
2. **Rewrite.** Every {term}`sugar` form is rewritten into {term}`core forms <core form>`
   ({doc}`core`). Names may be looked up. No value is computed.
3. **Expand.** Every form that needs values computed when compiling is written out: each copy that
   a `foreach` makes, and the body of a motif, once for each instance.
4. **Prove.** Every type, range, constraint and other invariant that the spec requires is proved
   ({doc}`types`, {doc}`well-formedness`).
5. **Fold and write.** Every expression known when compiling ({doc}`binding-time`) is replaced by
   its value, and the model is written as the .mtpc ({doc}`compiled-format`).
```

```{rule} step-rejects-or-passes
Each step either rejects the source with an error or passes its output to the next step. The parse
step rejects with a {term}`syntax error`, and every later step with a {term}`compile error`
({doc}`errors`). A step that rejects the source stops at its first error, and no later step runs.
```

```{rule} sugar-definition
A form is sugar if and only if it can be rewritten into core forms without computing any value.
The rewrite may look up names. Every form that is not sugar is a core form, or needs the expand
step.
```

For example, `(wait t)` is sugar for `(move none (duration t))`, `(range n)` for
`(range 0 n (gap 1))`, and `(roll-dice s)` for `(move s (to (next-seed s)) (duration 0))`. A
`foreach` is not sugar: the number of copies that it makes is a value, computed when compiling.

```{rule} prove-step-only-proves
The prove step proves, and does nothing else. Rewriting, expanding and folding are done by the
other steps.
```

:::{note}
**How the current compiler does these steps.** The parse step is separate: `parse` in
mathterpiece/parse.py reads the whole text before anything else runs. Writing is separate:
`write` in mathterpiece/mtpc.py turns the finished model into JSON. The writer also leaves out
every function and declared type that no object reaches (`_only_used`), and writes the values
that shapes of one kind share once (`_shared`).

The rewrite, expand, prove and fold steps are not separate. `_Compiler.run` in
mathterpiece/compiler.py goes through the top-level forms once, and each form is rewritten,
expanded, checked and folded as it is reached:

- Sugar is rewritten where the form is compiled, as `(wait t)` in `_Compiler.steps`, `(range n)`
  in `_Compiler.range_list`, `(map n f)` in `_Compiler.collection` and `(roll-dice s)` in
  `_Compiler.roll`.
- `foreach` copies are made by `_Compiler.expand`, one at a time, each just before it is compiled.
  The number of copies is computed by compiling the count as an expression (`bounded_count`,
  `each_of`).
- The body of a motif is compiled again for each instance, where the instance is compiled
  (`_Compiler.instance`).
- Types, ranges and constraints are checked, and known values folded, in the same functions that
  compile each expression (for example `_Compiler.call`, `_Compiler.apply_builtin`,
  `_Compiler.fold_call`).
- Imported files are read and compiled in the same pass (`_Compiler.imports`, `_Compiler.load`).
- A few checks run once every top-level form is compiled: the trial uses of choreos
  (`choreo_trial`), `check_quiet` and `check_states`. After them, `mark_canvases` works out the
  canvases of each control.
:::

:::{admonition} Open question Q-compiler-runtime-1
:class: warning
The prove step needs values that the model above computes only in the fold step. Two examples:

- In docs/data-model.md, line 66, the compile errors include "a constraint, or a range a value must
  stay in, that cannot be proved, such as a radius that might be negative" and "a value known when
  compiling that is undefined there, such as `(/ 1 0)`". Proving `(circle c (r (- 1 2)))` wrong,
  or finding `(/ 1 0)` undefined, needs the value of the expression.
- In docs/mtpc.md ("Expressions", the row `check`), the compiler writes a `check`
  expression "wherever a bound value's constraint cannot be proved". That adds to the model where a
  proof fails, which {numref}`prove-step-only-proves` does not allow in the prove step.

Today both happen in one pass (mathterpiece/compiler.py, `_Compiler.call`, lines 1962 to 1973,
fold a call and then check its constraint against the folded value). The options:

- (a) The expand step also computes every value known when compiling, and the fold step only
  writes them in place.
- (b) The prove step evaluates known expressions itself, which makes it larger.
- (c) Folding comes before proving.

A related question: which steps `mtp check` runs. Today it runs all of
`compile_model`, folding included (mathterpiece/cli.py, line 64), and skips only writing.
:::

:::{admonition} Open question Q-compiler-runtime-2
:class: warning
In the comments of the code, some forms are called sugar, or are written as standing for other
forms, but these forms need values computed when compiling, so by {numref}`sugar-definition` they
are not sugar:

- `colormap`: its docstring in mathterpiece/compiler.py, line 1732, has "sugar for one function of
  a real", but lines 1768 to 1789 reject a colormap whose `positions`, `discrete` or `wrap-at` is
  not known when compiling, and one whose positions decrease.
- A use of a choreo: `_Compiler.choreo_use` (lines 1669 to 1712) puts the arguments in place of
  the parameters, which needs no value, but rejects an argument that is not known when compiling
  (line 1705, "the arguments of a choreo are known when compiling").

The options for each:

- (a) It is expanded in the expand step, as a motif body is.
- (b) It is sugar, and the check that its parts are known moves to the prove step.

The same question applies to a `let` whose body holds declarations, which `_Compiler.body_let`
(line 947) handles in `_Compiler.expand`.
:::

## The mtp command

The mtp command runs on the illustrator's machine. It has six subcommands, and each runs the steps
of compiling up to a point.

```{rule} building
Building a source is the five steps of compiling, then a sixth step: writing the inventory page.
```

The inventory page holds the runtime, the .mtpc and the script of the inventory, all inside the
page, so that it works when it is opened as a file. It also holds the opening comment of the source,
the lines of HTML that load the runtime and the .mtpc, every component live with its name and the
line of HTML that places it, every listener with what it does, and every token with its CSS
variable and a control that restyles it. With `?record` at the end of its address, the page holds
only the figure, on a 9:16 page.

```{rule} subcommands
Each subcommand takes the path of one source file, and runs these steps:

| Subcommand | Steps | What it writes |
|---|---|---|
| `mtp parse file` | parse | prints the forms, and writes no file |
| `mtp check file` | parse to prove | prints `file: no errors` when there is no error, and writes no file |
| `mtp compile file` | parse to fold and write | the .mtpc |
| `mtp build file` | parse to fold and write, then the inventory page | the folder `build_name/`, `name` being the file name without `.mtp` |
| `mtp serve file` | as `mtp build`, again each time the file is saved | as `mtp build`, and serves the inventory page |
| `mtp fmt file` | parse | the file itself, in the house layout |

Every subcommand takes `-v`, given up to three times, which prints more of what the command does:
`-v` information, `-vv` debugging, `-vvv` tracing.
```

```{rule} command-errors
When a step rejects the source, or a file cannot be read, the subcommand prints one line to
standard error and exits with status 1. For a rejected source, the line is the first error
({numref}`step-rejects-or-passes`), as `file:line:column: message`. `file` is the path given on
the command line, or, for an error in an imported file, the name written in the `import` form,
followed by `.mtp`. A file that cannot be
read is an error too: `file: no such file`, `file: cannot be read: it is a folder`,
`file: cannot be read: it is not UTF-8 text`, or `file: cannot be read:` followed by the reason
that the system gives.
```

```{rule} nothing-written-on-error
A subcommand that ends with an error writes no file.
```

### mtp parse

```{rule} mtp-parse
`mtp parse` prints every node that the parser reads, one per line, in source order, each line
indented by two spaces for each level of depth. A line holds the position of the node as
`line:column`, its kind, and its value, as follows:

- `form`, `list`, `brackets` or `bar`, for a node that holds others. The nodes that it holds
  follow on the next lines.
- `name` and the name, its parts joined by `.`, with `[…]` for each part that is an expression.
  The nodes of those parts follow on the next lines.
- `string with values`, for a string with values in it. Each part follows on the next lines:
  `text` and the text, or the node of the value.
- `value` and, after a colon, its format, for a value inside a string.
- `string` or `tex string`, and the string.
- `none`, or `bool` and `true` or `false`.
- `int`, `ratio`, `real` or `complex`, and the number.
```

### mtp check

```{rule} mtp-check
`mtp check` runs the steps up to and including prove, and stops there. It prints
`file: no errors` to standard output when no step rejects the source.
```

### mtp compile

```{rule} mtp-compile
`mtp compile` writes the .mtpc to the path given with `-o` or `--output`, or else next to the
source, with the same name and the extension `.mtpc`. It makes the folder of that path when the
folder does not exist. It prints nothing unless `-v` is given.
```

### mtp build

```{rule} mtp-build
`mtp build` writes the folder `build_name/` next to the source, making it when it does not exist,
and writes three files into it: the .mtpc as `name.mtpc`, the runtime script as
`mathterpiece.js`, and the inventory page as `index.html`. It then prints `wrote` and the path
of `index.html`. Other files in the folder are left as they are.
```

:::{note}
The runtime script is built from web/src with `pnpm build` whenever a file in web/src is newer
than the built script in web/dist (`_bundle` in mathterpiece/build.py). Building it needs Node and
pnpm, and fails with an error without them.
:::

:::{admonition} Open question Q-compiler-runtime-3
:class: warning
Whether building the runtime script is a step of the mtp command. mathterpiece/build.py, lines 29
to 44, builds it from the TypeScript source in web/src during `mtp build` and `mtp serve`, and
fails with "the runtime's source is not in …" when web/src is not there (line 34). In
docs/data-model.md, line 15, the runtime script is made by "mtp itself, the same for every world
model", which can be read as made once, when mtp is released. The options:

- (a) The mtp command ships with a built runtime script and only copies it.
- (b) Building it from source is part of the command, as today.
:::

### mtp serve

```{rule} mtp-serve
`mtp serve` builds the source as `mtp build` does, then serves the inventory page at
`http://127.0.0.1:port`, `port` being the number given with `-p` or `--port`, or 8000. It prints
`serving file at` and that address. While it runs:

- It builds the source again whenever the modification time of the source file changes, checking
  it every quarter of a second.
- It answers a request for `/version` with the number of builds so far, and a request for any
  other path with the page of the last build.
- A script in the page requests `/version` every 400 milliseconds, and reloads the page when the
  number changes.
- When a build fails, it serves a page that holds the error ({numref}`command-errors`) in place of
  the inventory page, until the next save, and goes on running.

It stops when it is interrupted.
```

:::{admonition} Open question Q-compiler-runtime-4
:class: warning
`mtp serve` builds again only when the source file itself changes. `Server.check` in
mathterpiece/serve.py, lines 57 to 66, compares only the modification time of `self.path`, so
saving a file that the source imports does not rebuild the page. docs/data-model.md, line 63, has
"builds again and reloads the page whenever the source file is saved", which matches the code, but
the behavior looks unintended for an illustrator who edits an imported file. The options:

- (a) Watch every file that the source imports, directly or through other imports.
- (b) Keep watching the source file alone.
:::

### mtp fmt

```{rule} mtp-fmt
`mtp fmt` parses the source, and rejects it when the parse step does. It then rewrites the file in
the house layout, line by line, keeping every comment and every line break that the illustrator
wrote: each line is indented as the editor mode editors/mtp-mode.el indents it, spaces at the end
of a line are dropped, at most one empty line is kept in a row, and `(doc 'text')` is written
`doc@'text'`. Nothing else changes. It writes the file only when the result differs from it. It
runs no step after parse.
```

:::{admonition} Open question Q-compiler-runtime-5
:class: warning
Which outputs of the command are part of the spec, so that another implementation must give the
same text: the lines of `mtp parse` ({numref}`mtp-parse`, mathterpiece/cli.py, `_tree`, lines 121
to 160), the line `file: no errors` of `mtp check` (cli.py, line 68), the messages for a file that
cannot be read (cli.py, lines 101 to 111), the text of every compile error, and the house layout
of `mtp fmt` (mathterpiece/fmt.py, which follows editors/mtp-mode.el). This part states them as the
code gives them. The options:

- (a) All are normative.
- (b) Only the position `file:line:column` and the exit status are normative, and the text of a
  message is not.
- (c) Some other division.
:::

## What the compiler must do

```{rule} compiler-resolves-names
The compiler resolves every name in the source to its declaration ({ref}`scope`), or rejects the
source.
```

```{rule} compiler-proves-every-type
The compiler gives every expression a type and proves it, and writes every type that the runtime
needs into the .mtpc ({doc}`types`, {doc}`compiled-format`).
```

```{rule} compiler-decides-early
Everything that can be decided when compiling is decided when compiling, even when that makes
compiling slower. Nothing that the compiler could have decided is left for the runtime to decide
while the reader waits.
```

```{rule} compiler-rejects-or-writes
For every source, the compiler either rejects it with exactly one error, the first error
({numref}`step-rejects-or-passes`), or writes a .mtpc that is valid by {doc}`compiled-format`.
It never writes a .mtpc for a source that it rejects.
```

```{rule} compiler-same-bytes
The compiler is deterministic: the same source and the same imported files always give the same
bytes ({doc}`compiled-format`, "Same source, same bytes").
```

```{rule} compiler-reads-files
The compiler reads only the source file and the files that it imports, directly or through other
imports. An import is looked for in the folder of the file that imports it, then in the standard
library ({ref}`scope`, {doc}`stdlib`).
```

## What the compiler must never do

```{rule} compiler-never-runs-writers
The compiler never runs a writer: it never plays an animation, never performs a write that a
control or a listener would perform, and never acts as a reader would.
```

```{rule} compiler-never-reads-page
The compiler never reads a page, its CSS or its color scheme. It never folds a token: a token is
written with its declared value, which the runtime uses where the page gives none.
```

```{rule} compiler-never-draws-random
The compiler never draws a random value. A random function is known only while drawing
({doc}`binding-time`), and its value is drawn by the runtime from its seed.
```

## What the runtime must do

```{rule} runtime-loads-mtpc
The runtime loads each .mtpc given by the `src` attribute of an `<mtp-model>` element, once,
from a file that it fetches or from a block in the page ({doc}`page-interface`). When the .mtpc
cannot be fetched or read as JSON, the model fails to load, and the error takes the place of every
component of that model on the page.
```

```{rule} runtime-checks-version
The runtime reads only the versions of the .mtpc format that it implements. A .mtpc of another
version fails to load, with an error that gives both versions.
```

```{rule} runtime-builds-live-model
When a .mtpc loads, the runtime builds its live model, once, before any component draws: it turns
every expression into a function, once, and gives every free variable and attribute its starting
value, reading each `free@` start once ({doc}`compiled-format`, "Free and bound values").
```

```{rule} runtime-keeps-model-current
The runtime keeps the live model current as the reader acts: after each write, it computes again
only what depends on what changed, and the views draw again ({doc}`reaction`, {doc}`time`,
{doc}`concurrency`).
```

```{rule} runtime-serves-components
The runtime defines one page element for each kind of view and control, and serves each element
that the page places: in each element, it draws the view or control of the element's model that
the element's `name` attribute gives. A listener has no element: it acts on each element that
draws its shape or term, or, for a listener such as `on-view`, on its own view
({doc}`page-interface`, {doc}`lifecycle`).
```

## What the runtime must never do

```{rule} runtime-never-reads-source
The runtime never reads a source file. Everything that it holds of a world model comes from the
.mtpc.
```

```{rule} runtime-adds-no-objects
The runtime never adds an object to a live model. Every object, every motif instance and every
copy that a `foreach` makes is written out in the .mtpc. A stand-in that a canvas draws for
`on-show` and `on-hide` is not an object of the live model ({doc}`page-interface`).
```

```{rule} runtime-no-type-work-while-drawing
The runtime never checks or converts a type while drawing. The compiler has proved every type, and
every type that the runtime needs is written in the .mtpc.
```

:::{admonition} Open question Q-compiler-runtime-6
:class: warning
The runtime walks types and their constraints on every write. docs/mtpc.md, line 7, has
"the runtime can turn each expression into one function specialized to its types when the file
loads, and never checks or converts a type while drawing", and web/src/runtime.ts, line 4, has
"nothing here checks or converts one". But `Runtime.constrain` (web/src/runtime.ts, lines 756 to
779), which runs on every write of a free value, resolves the type of the slot (`this.core(t)`)
and its constraints (`this.constraints(t)`) each time, rounds a write into an int, clamps it into
a range, wraps it, and holds a choice at its last valid value. docs/data-model.md, line 192, has "a
write that breaks a constraint is brought into it (clamped, rounded or held)". The options:

- (a) Bringing a write into its type is an exception to
  {numref}`runtime-no-type-work-while-drawing`, stated in the rule.
- (b) The runtime turns the constraints of each slot into one function when the file loads, so
  that no type is walked while drawing, and the rule stands as written.
:::

## The .mtpc between the compiler and the runtime

```{rule} mtpc-only-boundary
The .mtpc is the only thing that passes from the compiler to the runtime. No other file, no call
and no shared state passes between them. Besides the .mtpc, the runtime reads only the page: its
elements, the values that its CSS gives the tokens, its color scheme, the pointer, the keyboard and
the clock.
```

The inventory page holds the opening comment of the source, which is not in the .mtpc
(`about` in mathterpiece/build.py). The mtp command writes that comment into the page, and the
runtime does not read it, so it does not pass from the compiler to the runtime.

```{rule} runtime-may-assume
The runtime may assume that every .mtpc that it reads was written by a conforming compiler: that
it is valid by {doc}`compiled-format`, that every reference in it is to an object or function that
it holds, that every expression gives a value of the type written with it, that every `deps` list
holds everything that its expression can read, and that everything known when compiling is folded.
The runtime need not check any of these.
```

```{rule} compiler-may-assume
The compiler may assume that a conforming runtime reads every part of the .mtpc as
{doc}`compiled-format` defines it. It may assume nothing else about the runtime.
```

```{rule} format-version
The compiler writes the version of the format that it implements in every .mtpc. Two .mtpc files
of the same version are read by the same rules.
```

:::{admonition} Open question Q-compiler-runtime-7
:class: warning
What the runtime does with a .mtpc that is not valid. The runtime checks only the version
(web/src/elements.ts, lines 100 to 103) and nothing else, as {numref}`runtime-may-assume`
allows. A file that breaks the format either makes the `Runtime`
constructor throw, and the model fails to load with that message (for example "unknown expression
…", web/src/runtime.ts, line 1104), or throws later, when a component draws, and the error takes
the place of that component (`MtpPart.guard`, web/src/elements.ts, lines 324 to 333), or draws
something wrong with no error. The schema docs/mtpc.schema.json is checked only by the tests
(tests/mtpc_check.py). The options:

- (a) The spec does not define the behavior.
- (b) The runtime must reject a file that the schema rejects, with an error at load.
- (c) The runtime must reject some named kinds of fault at load, and need not find the others.
:::

:::{admonition} Open question Q-compiler-runtime-8
:class: warning
Whether every change to the format changes its version. docs/mtpc.md ("Objects", the
paragraph after the table) has "An older file may have a listener on a shape with several views
in `"in"`, or with no `"in"`, which the runtime reads as heard in every view that shows its
shape", and `heardIn` in web/src/click.ts, line 35, returns true in every view for a listener
with no `in`. Both the compiler (mathterpiece/mtpc.py, line 31) and the runtime (web/src/doc.ts,
line 152) use version 4,
and the runtime refuses every other version (web/src/elements.ts, line 100), so that older file is
version 4 too, and two version 4 files can follow different rules. That breaks
{numref}`format-version` as written. The options:

- (a) Every change to the format changes the version, and the runtime stops reading the older
  form.
- (b) A change that a runtime can read in both forms keeps the version, and
  {numref}`format-version` is changed to allow it.
:::

## Conformance

```{rule} conforming-compiler
An implementation of the compiler conforms to this spec when, for every source and the files that
it imports:

- It rejects the source if and only if this spec rejects it, with a syntax error or a compile error
  of a rule that the source breaks.
- Otherwise it writes the .mtpc that {doc}`compiled-format` defines for the world model of the
  source.
- It obeys every rule of this part about the compiler.
```

```{rule} conforming-runtime
An implementation of the runtime conforms to this spec when it loads every valid .mtpc of the
versions that it implements, builds and keeps current its live model as the parts from
{doc}`world-model` to {doc}`accessibility` define, and obeys every rule of this part about the
runtime.
```

```{rule} conforming-command
An implementation of the mtp command conforms to this spec when its compiler conforms, and each of
its subcommands runs the steps and writes the files that this part gives for it.
```

:::{admonition} Open question Q-compiler-runtime-9
:class: warning
How close another compiler must come to this one. Three points have no answer:

- (a) Whether it must write the same bytes as mathterpiece/compiler.py and mathterpiece/mtpc.py
  for every source, or only a .mtpc that a runtime reads to the same live model. For example,
  docs/mtpc.md, "Top level", has no rule for which value `shared` holds when two values of an
  attribute are equally common, and `_shared` in mtpc.py, line 426, picks the one whose JSON text
  sorts first.
- (b) When a source breaks several rules, whether it must report the same first error as this
  compiler. That error depends on the order in which this compiler checks things.
- (c) Whether the text of an error message must match (see Q-compiler-runtime-5).
:::

:::{admonition} Open question Q-compiler-runtime-10
:class: warning
An error that the system gives while writing is not reported as {numref}`command-errors`
requires. In mathterpiece/cli.py, `mtp compile` writes with `out.write_text` (line 72) and
`mtp build` calls `build` (line 82), and neither catches `OSError`, so a folder that cannot be
written prints a Python traceback and not one line. `mtp serve` stops in the same way when its port
is taken (`ThreadingHTTPServer` in mathterpiece/serve.py, line 53). The options:

- (a) Every such error is an error of the command, printed as one line with exit status 1.
- (b) Errors of the system are outside the spec.
:::
