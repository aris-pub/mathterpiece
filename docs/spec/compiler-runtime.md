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
2. **Rewrite.** Every name is resolved to its declaration ({ref}`scope`), and every {term}`sugar`
   form is rewritten into {term}`core forms <core form>` ({numref}`sugar-form`). No value is
   computed and no type is used.
3. **Prove.** Every expression is given a type, and every type, range, constraint and other
   invariant that the spec requires is proved ({doc}`types`, {doc}`well-formedness`). This step
   proves and does nothing else.
4. **Expand.** Each `foreach` is written out as its copies, and each motif instance as the body of
   its motif with the arguments of the instance. Nothing else is expanded.
5. **Fold and write.** Every expression known when compiling ({doc}`binding-time`) is replaced by
   its value, and the model is written as the .mtpc ({doc}`compiled-format`), with every type that
   the runtime needs.
```

So a check that the parts of a sugar form are known when compiling is made in the prove step, and
every form that is not sugar, other than `foreach` and a motif instance, reaches the prove step as
it is. Which forms are sugar, and the rewrite of each, are defined in {doc}`core`.

```{rule} prove-bodies-once
The prove step proves each body once: the body of a function with each parameter ranging over
every value of its declared type, the body of a `foreach` with its variable ranging over every
value of its range, and the body of a motif with each parameter ranging over every value of its
declared type and constraints. An imported motif is proved once, in the file that declares it.
The copies that a `foreach` makes and the instances of a motif are not proved again, and an error
in such a body is reported at the body as written. A motif body that is safe for only some values
of a parameter is a compile error, unless the parameter declares a constraint that leaves out the
other values.
```

For example, `(motif dot ((real k)) (circle_ (r (/ 1 k))))` is a compile error at `(/ 1 k)`, since
`k` may be 0, whatever the instances give for `k`. With `(real k 1 (>= 1))` as the parameter, the
motif compiles.

```{rule} step-rejects-or-passes
The parse, rewrite and prove steps each either reject the source with exactly one error, the first
that the step finds, or pass their output to the next step. The parse step rejects with a
{term}`syntax error`, and the rewrite and prove steps with a {term}`compile error`
({doc}`errors`). When a step rejects the source, no later step runs. The expand step and the fold
and write step never reject a source that the prove step passed, so the compiler either rejects a
source with one error or writes a .mtpc that is valid by {doc}`compiled-format`, and never both.
```

```{rule} prover-finds-ranges
To prove a range or a constraint, the {term}`prover` works out the range of every number that an
expression can give, from the ranges of its inputs ({numref}`prover-widens-reals`). For an
expression known when compiling, that range holds its value. The prover writes nothing into the
model. Where it cannot prove the constraint of a bound value, it gives the value a type that
includes `none`, and the fold and write step writes the `check` that this type needs
({doc}`compiled-format`).
```

So `(circle c (r (- 1 2)))` is a compile error in the prove step, since the range of `(- 1 2)` is
-1 alone, and so is `(/ 1 0)`, since its divisor is 0 alone ({numref}`undefined-gives-none`).

:::{admonition} Code differs
:class: note
Today the rewrite, prove, expand and fold steps are not separate, and expanding comes before
proving. `_Compiler.run` in mathterpiece/compiler.py, line 586, goes through the top-level forms
once, and each form is rewritten, expanded, checked and folded as it is reached. `foreach` copies
are made one at a time by `_Compiler.expand` (line 828), and the body of a motif is compiled again
for each instance by `_Compiler.instance` (line 4674), so each copy and each instance is proved on
its own. `_Compiler.call` (lines 1962 to 1973) folds a call and then checks its constraint against
the folded value. The new middle of the compiler (mtp-08wd) follows these rules. The order of the
steps and proving each body once are mtp-08wd.1.
:::

## The mtp command

The mtp command runs on the illustrator's machine. It has six subcommands, and each runs the steps
of compiling up to a point.

Building a source is the five steps of compiling, then writing the inventory page. The inventory
page holds the runtime, the .mtpc and the script of the inventory, all inside the page, so that it
works when it is opened as a file. It also holds the opening comment of the source, the lines of
HTML that load the runtime and the .mtpc, every component live with its name and the line of HTML
that places it, every listener with what it does, and every token with its CSS variable and a
control that restyles it. With `?record` at the end of its address, the page holds only the figure,
on a 9:16 page.

```{rule} subcommands
Each subcommand takes the path of one source file, and runs these steps:

| Subcommand | Steps | What it writes |
|---|---|---|
| `mtp parse file` | parse | prints the nodes that the parser reads, and writes no file |
| `mtp check file` | parse, rewrite and prove | prints `file: no errors` when there is no error, and writes no file |
| `mtp compile file` | parse to fold and write | the .mtpc |
| `mtp build file` | parse to fold and write, then the inventory page | the folder `build_name/`, `name` being the file name without `.mtp` |
| `mtp serve file` | as `mtp build`, again each time the file or a file that it imports is saved | as `mtp build`, and serves the inventory page |
| `mtp fmt file` | parse | the file itself, in a house layout |

Every subcommand takes `-v`, given up to three times, which prints more of what the command does:
`-v` information, `-vv` debugging, `-vvv` tracing.
```

```{rule} command-errors
When a step rejects the source, when a file cannot be read or written, or when `mtp serve` cannot
listen on its port, the subcommand writes no file, prints one line to standard error, and exits
with status 1. For
a rejected source, the line is the first error ({numref}`step-rejects-or-passes`), as
`file:line:column: message`. `file` is the path given on the command line, or, for an error in an
imported file, the name written in the `import` form, followed by `.mtp`. The wording of the line
is not normative ({numref}`what-is-normative`).
```

This implementation prints `file: no such file`, `file: cannot be read: it is a folder`,
`file: cannot be read: it is not UTF-8 text`, or `file: cannot be read:` followed by the reason
that the system gives, for a file that cannot be read.

:::{admonition} Code differs
:class: note
`mtp compile` writes with `out.write_text` (mathterpiece/cli.py, line 72) and `mtp build` calls
`build` (line 82), and neither catches `OSError`, so a folder that cannot be written prints a
Python traceback and not one line. `mtp serve` stops in the same way when its port is taken
(`ThreadingHTTPServer` in mathterpiece/serve.py, line 53). Bug mtp-vrzc.
:::

### mtp parse

What `mtp parse` prints is not normative ({numref}`what-is-normative`). This implementation prints
one node per line, in source order, each line indented by two spaces
for each level of depth. A line holds the position of the node as `line:column`, its kind, and
its value, as follows:

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

### mtp check

`mtp check` prints `file: no errors` to standard output. Since no step after prove rejects a source
({numref}`step-rejects-or-passes`), `mtp check` rejects every source that `mtp compile` rejects.

:::{admonition} Code differs
:class: note
`mtp check` runs all of `compile_model`, folding included (mathterpiece/cli.py, line 64), and
skips only writing. mtp-08wd.1.
:::

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
of `index.html`. Other files in the folder are left as they are. The runtime script is the one
that comes with the mtp command, the same for every world model, and building a page needs no
program other than the mtp command. How the mtp command gets its runtime script is not normative.
```

:::{admonition} Code differs
:class: note
The runtime script is built from web/src with `pnpm build` whenever a file in web/src is newer
than the built script in web/dist (`_bundle` in mathterpiece/build.py, lines 29 to 44). Building
it needs Node and pnpm, and fails with "the runtime's source is not in …" when web/src is not
there, so an installed mtp cannot build pages. Bug mtp-crid.
:::

### mtp serve

```{rule} mtp-serve
`mtp serve` builds the source as `mtp build` does, then serves the inventory page at
`http://127.0.0.1:port`, `port` being the number given with `-p` or `--port`, or 8000. It prints
`serving file at` and that address. While it runs:

- It builds the source again whenever the modification time of the source file changes, or that of
  a file that the source imports, directly or through other imports. It checks them every quarter
  of a second.
- It answers a request for `/version` with the number of builds so far, and a request for any
  other path with the page of the last build.
- A script in the page requests `/version` every 400 milliseconds, and reloads the page when the
  number changes.
- When a build fails, it serves a page that holds the error ({numref}`command-errors`) in place of
  the inventory page, until the next save, and goes on running.

It stops when it is interrupted.
```

:::{admonition} Code differs
:class: note
`Server.check` in mathterpiece/serve.py, lines 57 to 66, compares only the modification time of
the source file, so saving a file that the source imports does not build the page again. Bug
mtp-q02m.
:::

### mtp fmt

```{rule} mtp-fmt
`mtp fmt` parses the source, and rejects it when the parse step does. It then rewrites the file in
a house layout, keeping every comment and every line break that the illustrator wrote, so that the
file that it writes has the same meaning as the file that it read. It writes the file only when
the result differs from it. It runs no step after parse. The layout is not normative
({numref}`what-is-normative`).
```

In this implementation, each line is indented as the editor mode editors/mtp-mode.el indents it,
spaces at the end of a line are dropped, at most one empty line is kept in a row, and
`(doc 'text')` is written `doc@'text'` (mathterpiece/fmt.py).

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
library ({ref}`scope`, {doc}`stdlib`).
```

```{rule} compiler-never-acts-while-drawing
The compiler never does what happens only while drawing ({doc}`binding-time`). It never runs a
writer: it never plays an animation, never performs a write that a control or a listener would
perform, and never acts as a reader would. It never reads a page, its CSS or its color scheme, and
so never folds a token: a token is written with its declared value, which the runtime uses where
the page gives none. It never draws a random value ({numref}`random-never-folded`).
```

## What the runtime must do and must never do

```{rule} runtime-loads-mtpc
The runtime loads each .mtpc given by the `src` attribute of an `<mtp-model>` element, once,
from a file that it fetches or from a block in the page ({doc}`page-interface`). When the .mtpc
cannot be fetched or read as JSON, the model fails to load, and the error takes the place of every
component of that model on the page. The runtime reads only the versions of the .mtpc format that
it implements, and refuses a .mtpc that does not match the schema of its version
({doc}`compiled-format`): such a .mtpc fails to load too. For a .mtpc of another version, the
error gives both versions.
```

:::{admonition} Code differs
:class: note
The runtime checks only the version (web/src/elements.ts, lines 100 to 103). A file that breaks the
schema either makes the `Runtime` constructor throw, so that the model fails to load with that
message, or throws later, when a component draws, or draws something wrong with no error. The
schema docs/mtpc.schema.json is checked only by the tests (tests/mtpc_check.py). mtp-ydd4.7.16.
:::

```{rule} runtime-builds-live-model
When a .mtpc loads, the runtime builds its live model, once, before any component draws: it turns
every expression into a function, once, and gives every free variable and attribute its starting
value, reading each `free@` start once ({doc}`compiled-format`, "Free and bound values"). Then it
keeps the live model current as the reader acts: after each write, it computes again only what
depends on what changed, and the views draw again ({doc}`reaction`, {doc}`time`,
{doc}`concurrency`).
```

```{rule} runtime-serves-components
The runtime defines one page element for each kind of view and control, and serves each element
that the page places: in each element, it draws the view or control of the element's model that
the element's `name` attribute gives. A listener has no element: it acts on each element that
draws its shape or term, or, for a listener such as `on-view`, on its own view
({doc}`page-interface`, {doc}`lifecycle`).
```

```{rule} runtime-adds-no-objects
The runtime never adds an object to a live model. A stand-in that a canvas draws for
`on-show` and `on-hide` is not an object of the live model ({doc}`page-interface`).
```

```{rule} runtime-no-type-work-while-drawing
While drawing, the runtime never checks whether a value has its type, and never converts a value
from one type to another. The compiler has proved every type, and every type that the runtime
needs is written in the .mtpc. Bringing a written value into the constraints of what it is written
into, by clamping, rounding, wrapping or holding it ({doc}`types`), is part of what a write does,
and is not a check of a type. How the runtime does this is not normative.
```

## The .mtpc between the compiler and the runtime

```{rule} mtpc-only-boundary
The .mtpc is the only thing that passes from the compiler to the runtime. No other file, no call
and no shared state passes between them. Besides the .mtpc, the runtime reads only the page: its
elements, the values that its CSS gives the tokens, its color scheme, the pointer, the keyboard and
the clock.
```

So the runtime never reads a source file, and every object, every motif instance and every copy
that a `foreach` makes is written out in the .mtpc ({numref}`compile-steps`).

The inventory page holds the opening comment of the source, which is not in the .mtpc
(`about` in mathterpiece/build.py). The mtp command writes that comment into the page, and the
runtime does not read it, so it does not pass from the compiler to the runtime.

```{rule} what-each-may-assume
The runtime may assume that every .mtpc that matches the schema was written by a conforming
compiler: that every reference in it is to an object or function that it holds, that every
expression gives a value of the type written with it, that every `deps` list holds everything that
its expression can read, and that everything known when compiling is folded. The runtime need not
check any of these. This spec does not define what the runtime does with a .mtpc that matches the
schema and breaks one of them. The compiler may assume that a conforming runtime reads every part
of the .mtpc as {doc}`compiled-format` defines it, and nothing else about the runtime.
```

```{rule} format-version
The compiler writes the version of the format that it implements in every .mtpc. Every change to
the format changes its version, so two .mtpc files of the same version are read by the same rules.
```

:::{admonition} Code differs
:class: note
The runtime reads an older form of version 4: a listener with no `in`, or with several views in
`in`, is heard in every view that shows its shape (`heardIn` in web/src/click.ts, line 35, and
docs/mtpc.md, "Objects"). The compiler (mathterpiece/mtpc.py, line 31) and the runtime
(web/src/doc.ts, line 152) both use version 4, so two version 4 files can follow different rules.
mtp-ydd4.7.17.
:::

## Conformance

```{rule} what-is-normative
These are normative, and every conforming implementation gives the same: which sources are
accepted and which are rejected, the meaning of the .mtpc, and what the runtime does. These are
not normative: the wording of error messages, the bytes of the .mtpc, what `mtp parse` prints, and
the layout that `mtp fmt` writes.
```

So two conforming compilers may write different bytes for one source, as long as a runtime builds
the same live model from both. For example, docs/mtpc.md, "Top level", has no rule for which value
`shared` holds when two values of an attribute are equally common, and `_shared` in
mathterpiece/mtpc.py, line 426, picks the one whose JSON text sorts first. Another compiler may
pick the other.

```{rule} conformance
- An implementation of the compiler conforms to this spec when, for every source and the files
  that it imports, it rejects the source if and only if this spec rejects it, with a syntax error
  or a compile error of a rule that the source breaks, and otherwise writes a .mtpc that has the
  meaning that {doc}`compiled-format` defines for the world model of the source. When the source
  breaks several rules, the error may be of any one of them.
- An implementation of the runtime conforms when it loads every valid .mtpc of the versions that
  it implements, and builds and keeps current its live model as the parts from {doc}`world-model`
  to {doc}`accessibility` define.
- An implementation of the mtp command conforms when its compiler conforms, and each of its
  subcommands runs the steps and writes the files that this part gives for it.

Each conforms only when it also obeys every rule of this part about it.
```
