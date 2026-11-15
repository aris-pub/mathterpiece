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
  The program that turns a source file into a .mtpc, in the steps parse, rewrite, prove, expand,
  and fold and write. Defined in {doc}`compiler-runtime`.

component
  A view, a control or a listener: what the illustrator declares and the author places on a page.
  Defined in {doc}`compiler-runtime`.

corrupt .mtpc
  A .mtpc that matches the schema of its version and breaks a rule of this spec. The compiler
  never writes one, and the runtime refuses every one. Defined in {doc}`compiler-runtime`.

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

broadened type
  Two words or more joined by `|` with no whitespace between them, such as `real|none`
  ({numref}`broadened-types`).

whitespace
  The characters space, tab, line feed and carriage return. Whitespace and comments have no
  meaning ({numref}`whitespace-and-comments`).

digit
  One of the ASCII digits `0` to `9` ({numref}`number-literals`).

body
  The last items of a form, after its optional arguments. What a body may hold depends on the form
  ({numref}`contexts`).

bool
  The word `true` or `false` ({numref}`literal-words`).

built-in type
  One of the types that mtp gives, such as `real`, `point` or `circle`, whose name no declaration
  takes ({numref}`declaration-names`).

comment
  Text from `;` up to the end of the line ({numref}`whitespace-and-comments`).

complex
  A number literal with an imaginary part, such as `2i` or `1+2i` ({numref}`number-literals`).

docstring
  `doc@'text'`, which is `(doc 'text')`: plain text about a declaration, for the illustrator
  ({numref}`prefix-forms`, {numref}`docstrings`).

form
  A head and its items in parentheses, such as `(circle p (r 1))` ({numref}`top-level-forms`,
  {numref}`form-template`).

format spec
  The text after `:` in the braces of an interpolated string, such as `.2f` in `{x:.2f}`
  ({numref}`interpolated-strings`).

free starting value
  `free@X`, which is `(free@ X)` ({numref}`prefix-forms`).

head
  The first item of a form ({numref}`form-template`).

brackets
  A `[…]` right after a name or a list, which reads a part of it ({numref}`lists`,
  {numref}`name-brackets`).

int
  A number literal that is a whole number, such as `3` or `-2` ({numref}`number-literals`).

interpolated string
  `$'…'`: a string with expressions in braces, whose values are filled in
  ({numref}`interpolated-strings`).

letter
  One of the ASCII letters `a` to `z` and `A` to `Z`, as a character of a name
  ({numref}`name-characters`).

list
  Expressions in square brackets, such as `[0 1]` ({numref}`lists`).

name
  A word that refers to something declared: parts joined by dots, such as `p.pos.x`
  ({numref}`name-characters`).

part
  A piece of a name: the text between two dots, or a pair of brackets, such as `pos` and `[0]` in
  `xs[0].pos` ({numref}`name-characters`, {numref}`name-brackets`).

name string
  `#'…'`: an interpolated string read as a name, which is `(name $'…')`
  ({numref}`interpolated-strings`, {numref}`shorthand-forms`).

expression
  One item of a source as the parser produces it: a form, a list, a word, a string or a free
  starting value ({numref}`parser-expressions`).

operator
  One of the words `+ - * / ^ < <= > >= = != .`, read as a name of one part
  ({numref}`literal-words`).

optional argument
  A form after the name and the positional arguments of a form, whose head names one of the
  optional arguments that the form allows, such as `(r 1)` in `(circle c (r 1))`
  ({numref}`optional-arguments-first`).

positional argument
  An item of a form that comes right after the name, known by its place ({numref}`form-template`).

ratio
  A number literal that is an exact fraction, such as `1/3` ({numref}`number-literals`).

real
  A number literal with a decimal point or an exponent, such as `2.5` or `1e3`
  ({numref}`number-literals`).

keyword
  The head of a form of the language, such as `circle`, `if` or `on-drag`, which no declaration
  takes as its name ({numref}`keywords`, {numref}`declaration-names`).

string
  Text in single quotes, such as `'crimson'` ({numref}`string-literals`).

TeX string
  `tex'…'`: a string of LaTeX, in which only `\'` is an escape ({numref}`tex-strings`).

word
  A name, a number, an operator, a bool or `none` ({numref}`word-ends`).

core form
  A form that is not sugar, such as a form whose head is core or a call of a library function. The
  prover proves core forms, and the runtime runs them. See {numref}`kinds-of-form` and
  {numref}`library-form`.

library
  The built-in functions and the files of the standard library. A call of a library function is
  a core form. See {numref}`library-form`.

prover
  The part of the compiler that does the prove step: it checks types, proves ranges and
  constraints, and checks every invariant of the world model. It is given only core forms. See
  {numref}`compile-steps`.

rewrite
  A pair of mtp fragments: a sugar form, and the core forms that it means. See
  {numref}`sugar-rewrites`.

sugar
  A form that can be rewritten into core forms without computing any value and without using
  any type. Also called a derived form. See {numref}`sugar-form`.

evaluation
  Computing the value of an expression, when compiling or while drawing. Evaluation changes
  nothing. Defined in {doc}`evaluation`.

folding
  Computing an expression whose inputs are all known when compiling, and writing its value into
  the .mtpc in place of the expression. Defined in {doc}`evaluation`.

match
  Two values match when they are equal, except that two reals match when they are within about a
  millionth of their size. Matching is not equality, and only the runtime matches values: the step
  of a play or a stepper is read from the scene by matching. Defined in {doc}`evaluation`.

number limit
  ±10¹⁵⁰, the bound on every literal and every written number. Defined in {doc}`evaluation`.

seed
  A free variable of type `rand-seed`, from which random values are computed. Defined in
  {doc}`evaluation`.

site
  The number that each call of a random function has, counted from 0 in the order of the calls in
  the source after the rewrite step. Defined in {doc}`evaluation`.

scope
  A part of a file in which some names may be used, such as the body of a motif or of a `let`
  ({numref}`scopes`).

file scope
  The scope of a whole file: its top-level declarations, its imports, and the declarations of its
  scene at any depth ({numref}`scopes`).

fit
  A type A fits a type B when a value of type A is accepted where a value of type B is expected
  ({numref}`fits`).

constraint
  A form that refines a type to some of its values, such as `(>= 0)` or `(one-of 'a' 'b')`
  ({numref}`constraints`).

refined type
  A type with constraints, written `(T C…)`, whose values are the values of T that meet every
  constraint ({numref}`the-types`, {numref}`constraints`).

choice type
  A string type refined by `(one-of …)` to a few strings ({numref}`choice-types`).

interface
  A type that no object has as its own type, which every type with what it lists satisfies, such
  as `shape` or a type declared with `interface` ({numref}`interfaces`).

known length
  The length of a list when it is known when compiling, as a `(length n)` in its type
  ({numref}`known-lengths`).

range
  The closed interval of reals that holds every value of an expression, which the prover works
  out ({numref}`ranges`, {numref}`range-rules`).

call depth limit
  The constant `max-call-depth`, which is 256: a call known when compiling that, when folded, would
  nest calls of functions deeper than it is a compile error. Defined in {doc}`evaluation`.
```
