# Glossary

Each term that the spec defines, with the rule that defines it.

```{glossary}
:sorted:

.mtpc
compiled model
  The JSON file that the compiler writes for one world model, and the only thing that passes from
  the compiler to the runtime. Defined in {doc}`compiler-runtime`, and its format in
  {doc}`compiled-format`.

author
  The person who writes a page and places components of world models in it. Defined in
  {doc}`compiler-runtime`.

compile error
  An error by which a step of compiling after the parse step rejects a source. Defined in
  {doc}`compiler-runtime`, and each one in {doc}`errors`.

compiler
  The program that turns a source file into a .mtpc, in the steps parse, rewrite, expand, prove,
  and fold and write. Defined in {doc}`compiler-runtime`.

component
  A view, a control or a listener: what the illustrator declares and the author places on a page.
  Defined in {doc}`compiler-runtime`.

control
  A component that the reader presses, drags or clicks, and which writes the model: a slider, a
  button, a play, a stepper or a toggle. Defined in {doc}`compiler-runtime`.

illustrator
  The person who writes a world model as an `.mtp` source file. Defined in
  {doc}`compiler-runtime`.

inventory page
  The page that `mtp build` writes, which holds the runtime and the .mtpc, and every
  component live with the HTML that places it. Defined in {doc}`compiler-runtime`.

listener
  A component that is written inside a view and has no page element of its own, and which writes
  the model when the reader acts on a shape or a term, or when its view changes. Defined in
  {doc}`compiler-runtime`.

live figure
  The runtime and a page together, with one live model for each .mtpc that the page loads.
  Defined in {doc}`compiler-runtime`.

live model
  The world model of one .mtpc, as the runtime holds it in memory while a page is open, with the
  current value of every variable and attribute. Defined in {doc}`compiler-runtime`.

mtp command
  The command that runs the compiler on the illustrator's machine, with the subcommands `parse`,
  `check`, `compile`, `build`, `serve` and `fmt`. Defined in {doc}`compiler-runtime`.

parser
  The part of the compiler that does the parse step: it reads the text into forms by the syntax
  alone. Defined in {doc}`compiler-runtime`.

reader
  The person who opens a page and acts on its components. Defined in {doc}`compiler-runtime`.

runtime
  The program that runs in the reader's browser, loads each .mtpc that a page names, builds its
  live model, keeps it current, and serves the components that the page places. Defined in
  {doc}`compiler-runtime`.

runtime script
  The file `mathterpiece.js`, which holds the runtime and defines the page elements. It is the
  same for every world model. Defined in {doc}`compiler-runtime`.

syntax error
  An error by which the parse step rejects a source. Defined in {doc}`compiler-runtime`.

view
  A component through which the reader sees the model: a canvas, a readout or a display. Defined in
  {doc}`compiler-runtime`.

bar
  Two words or more joined by `|` with no blank, such as `real|none` ({numref}`bars`).

blank
  A sequence of whitespace characters and comments, which only separates tokens
  ({numref}`blank`).

body
  The last items of a form, after its options. What a body may hold depends on the form
  ({numref}`contexts`).

boolean
  The word `true` or `false` ({numref}`literal-words`).

comment
  Text from `;` up to the end of the line ({numref}`blank`).

complex
  A number literal with an imaginary part, such as `2i` or `1+2i` ({numref}`number-literals`).

docstring
  `doc@'text'`, which is `(doc 'text')`: plain text about a declaration, for the illustrator
  ({numref}`prefix-forms`, {numref}`docstrings`).

field
  `{…}` in an interpolated string or a name string: a node, and optionally a format spec
  ({numref}`interpolated-strings`).

form
  A head and its items in parentheses, such as `(circle p (r 1))` ({numref}`top-level-forms`,
  {numref}`form-template`).

format spec
  The text after `:` in a field, such as `.2f` in `{x:.2f}` ({numref}`interpolated-strings`).

free start
  `free@X`, which is `(free@ X)` ({numref}`prefix-forms`).

head
  The first item of a form ({numref}`form-template`).

index
  A `[…]` right after a name or a list, which reads a part of it ({numref}`lists`,
  {numref}`name-index`).

inside braces
  Read as the node of a field, where `:` ends a run ({numref}`inside-braces`).

int
  A number literal that is a whole number, such as `3` or `-2` ({numref}`number-literals`).

interpolated string
  `$'…'`: a string with fields, whose values are filled in ({numref}`interpolated-strings`).

list
  Nodes in square brackets, such as `[0 1]` ({numref}`lists`).

name
  A word that refers to something declared: name parts joined by dots, such as `p.pos.x`
  ({numref}`name-characters`).

name part
  One of the pieces of a name that dots separate ({numref}`name-characters`).

name string
  `#'…'`: an interpolated string read as a name, which is `(name $'…')`
  ({numref}`interpolated-strings`, {numref}`shorthand-forms`).

node
  One item of a source as the reader produces it: a form, a list, a word, a string or a free start
  ({numref}`reader-nodes`).

operator
  One of the words `+ - * / ^ < <= > >= = != .`, read as a name of one part
  ({numref}`literal-words`).

option
  A form among the items of a declaration whose head is one of the options of the declaration,
  such as `(r 1)` ({numref}`options-first`).

positional argument
  An item of a form that comes right after the name, known by its place ({numref}`form-template`).

ratio
  A number literal that is an exact fraction, such as `1/3` ({numref}`number-literals`).

real
  A number literal with a decimal point or an exponent, such as `2.5` or `1e3`
  ({numref}`number-literals`).

reserved word
  A word that is never the name of a declaration ({numref}`reserved-words`).

run
  A longest sequence of characters with no blank and none of `( ) [ ] { } " | ;` ({numref}`run`).

string
  Text in single quotes, such as `'crimson'` ({numref}`string-literals`).

TeX string
  `tex'…'`: a string of LaTeX, in which only `\'` is an escape ({numref}`tex-strings`).

token
  A piece of text that the reader reads whole, such as a name or a string
  ({numref}`tokens-in-context`).

word
  One run read whole: a name, a number, an operator or a boolean ({numref}`run`).

core form
  A form that the prover checks and the runtime runs: every form that is not sugar. See
  {numref}`core-form`.

library
  The built-in functions and the files of the standard library. A call of a library function is
  a core form. See {numref}`library-form`.

prover
  The part of the compiler that checks types, proves ranges and constraints, and checks every
  invariant of the world model. It sees only core forms. See {numref}`prover-sees-core`.

rewrite
  A rule that replaces a sugar form by core forms, as a pair of mtp fragments. See
  {ref}`core-rewrites`.

sugar
  A form that can be rewritten into core forms without computing any value. Also called a
  derived form. See {numref}`sugar-form`.
```
