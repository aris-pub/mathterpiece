# Glossary

Each term that the spec defines, with the rule that defines it.

```{glossary}
:sorted:

.mtpc
compiled model
  The JSON file that the compiler writes for one world model, and the only file that passes from
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
  fold and write. Defined in {doc}`compiler-runtime`.

component
  A view or a control: what the author places on a page.
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

writer
  A control or a listener: a page object that writes the model. Defined in {doc}`compiler-runtime`.

page object
  A view, a control or a listener: what the reader sees or acts on in a page. Its type is
  `page-object`. Defined in
  {doc}`compiler-runtime`.

listener
  A page object that is written inside a view and has no page element of its own, and which writes
  the model when the reader acts on a shape or a term, or when its view changes. Defined in
  {doc}`compiler-runtime`.

open page
  A page open in the reader's browser, with the runtime and one live model for each .mtpc that the
  page loads. Defined in {doc}`compiler-runtime`.

live model
  The world model of one .mtpc, as the runtime holds it in memory while a page is open, with the
  current value of every variable and attribute. Defined in {doc}`compiler-runtime`.

parser
  The part of the compiler that does the parse step: it reads the text into forms by the syntax
  alone. Defined in {doc}`compiler-runtime`.

reader
  The person who opens a page and acts on its page objects. Defined in {doc}`compiler-runtime`.

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
  The last items of a form, after its named arguments. What a body may hold depends on the form
  ({numref}`contexts`).

bool
  A value of type `bool`: `true` or `false`. Written as the word `true` or `false`
  ({numref}`the-types`, {numref}`literal-words`).

type
  A named set of values, primitives or objects, known when compiling ({numref}`what-a-type-is`).

built-in type
  One of the types that mtp gives, such as `real`, `point` or `circle`, whose name no declaration
  and no binding takes ({numref}`declaration-names`).

comment
  Text from `;` up to the end of the line ({numref}`whitespace-and-comments`).

complex
  A value of type `complex`: two binary64 numbers, its real part and its imaginary part, within the
  number limit. Written as a number literal with an imaginary part, such as `2i` or `1+2i`
  ({numref}`number-types`, {numref}`number-literals`).

docstring
  `(doc 'text')`, usually written `doc@'text'`: plain text about a declaration or a whole file, for the illustrator
  ({numref}`prefix-forms`, {numref}`docstrings`).

form
  A head and its items in parentheses, such as `(circle p (r 1))` ({numref}`top-level-forms`,
  {numref}`form-template`).

format spec
  The text after `:` in the braces of an interpolated string, such as `.2f` in `{x:.2f}`
  ({numref}`interpolated-strings`).

free starting value
  `(free X)`, also written `free@X`: the start of a free variable or attribute, which holds the
  value of `X` when the page opens and does not update when `X` changes ({numref}`prefix-forms`, {doc}`core`).

head
  The first item of a form. The head of a compound or a declaration is a name, or a form that
  evaluates to a type. Whether a form is a
  compound, a declaration, a clause or a special form depends on its head ({numref}`form-template`,
  {numref}`parser-expressions`).

brackets
  A `[…]` right after a name or after the `}` of a list, with no whitespace between them, such as
  `xs[0]`, `{a b c}[h]` or `func[real real]` ({numref}`lists`, {numref}`name-brackets`).

int
  A value of type `int`: an exact whole number, within the number limit. Written as a number
  literal that is a whole number, such as `3` or `-2` ({numref}`number-types`,
  {numref}`number-literals`).

interpolated string
  `f'…'`: text with expressions in braces, syntactic sugar for a `concat` form that joins the text and
  the values, each written by `fmt` ({numref}`interpolated-strings`, {numref}`parser-sugar`).

letter
  One of the ASCII letters `a` to `z` and `A` to `Z`, as a character of a name
  ({numref}`name-characters`).

point
  A primitive with two real coordinates, `x` and `y`, which are also its attributes `0` and `1`.
  Given by the compound `(point-of X Y)`, which is also written `[X Y]`. The points form a vector
  space ({numref}`values`, {numref}`point-arithmetic`).

list
  A primitive of a list type `list[T]`: items of type T, in order, of any length. Given by the
  compound `(list-of …)`, which is also written with its items in braces, such as `{0 1 2}` ({numref}`the-types`, {numref}`lists`).

literal
  A number, a string, a color, `true`, `false` or `none`, written in the source, such as `2.5` or
  `'crimson'`. A literal evaluates to a primitive ({numref}`literals`).

name
  A word that refers to a type, a variable, an object or a binding, such as `p` or `real`
  ({numref}`name-characters`).

qualified name
  Two or more name parts joined by dots, such as `p.pos.x`. It is syntactic sugar for `(. X K)`
  forms whose `K` is a string: `p.pos.x` is `(. (. p 'pos') 'x')` ({numref}`sugar-rewrites`,
  {numref}`dot-name-part`).

name part
  A piece of a name: the text between two dots, or a pair of brackets, such as `pos` and `[0]` in
  `xs[0].pos` ({numref}`name-characters`, {numref}`name-brackets`).

color string
  `#'…'`, syntactic sugar for `(color-of f'…')`, which evaluates to the color that the text names
  ({numref}`color-literals`).

name string
  `@'…'`: an interpolated string read as a name, which is `(name f'…')`
  ({numref}`interpolated-strings`, {numref}`parser-sugar`).

named argument
  A {term}`clause` after the name and the positional arguments of a form, whose head names one of the
  named arguments that the form allows, such as `(r 1)` in `(circle c (r 1))`
  ({numref}`named-arguments-first`). Like a positional argument, it may be required or left out.

expression
  Anything that the parser produces. After syntactic sugar is rewritten, each expression is a
  literal, a name or a form, and each form is a {term}`compound`, a declaration, a
  {term}`clause` or a {term}`special form` ({numref}`parser-expressions`).

operator
  One of the words `+ - * / ^ < <= > >= = != .`, read as a name with one name part
  ({numref}`literal-words`).

positional argument
  An item of a form that comes right after the name, known by its place ({numref}`form-template`).

ratio
  A value of type `ratio`: an exact fraction, within the number limit. Written as a number literal
  that is an exact fraction, such as `1/3` ({numref}`number-types`, {numref}`number-literals`).

real
  A value of type `real`: a finite binary64 number, within the number limit. Written as a number
  literal with a decimal point or an exponent, such as `2.5` or `1e3` ({numref}`number-types`,
  {numref}`number-literals`).

keyword
  The head of a form of the language, such as `circle`, `if` or `on-drag`, which no declaration
  and no binding takes as its name ({numref}`keywords`, {numref}`declaration-names`).

string
  A value of type `string`: text. Written as text in single quotes, such as `'crimson'`
  ({numref}`the-types`, {numref}`string-literals`).

TeX string
  `$'…'`: a string literal in which only `\'` is an escape, so backslashes are kept as written, as
  LaTeX needs. Its value is an ordinary string ({numref}`tex-strings`).

word
  A name, a number, an operator, a bool literal or `none` ({numref}`word-ends`).

core form
  A form that is not syntactic sugar, such as `(if c a b)` or a call of a function. The
  prover proves core forms, and the runtime runs them. See {numref}`kinds-of-form` and
  {numref}`built-ins`.

built-in
  A function, constant or type that every source has without declaring or importing it, such as
  `+`, `pi` or `real`. A call of a built-in function is a core form. See {numref}`built-ins`.

standard library
  The files that come with mtp, such as `math` and `rand`, which a source imports like any other
  file. See {numref}`built-ins` and {doc}`stdlib`.

prover
  The part of the compiler that does the prove step: it checks types, proves ranges and
  conditions, and checks every invariant of the world model. It is given only core forms. See
  {numref}`compile-steps`.

rewrite
  A pair of mtp fragments: a syntactic sugar form, and the core forms that it means. See
  {numref}`sugar-rewrites`.

syntactic sugar
  A form that can be rewritten into core forms without computing any value and without using
  any type. Also called a derived form. See {numref}`sugar-form`.

evaluation
  Computing the value of an expression, when compiling or while drawing. Evaluation writes no
  variable and no attribute, and creates no variable and no object that a writer can write. Defined in {doc}`evaluation`.

folding
  Computing an expression whose inputs are all known when compiling, and writing its value into
  the .mtpc in place of the expression. Defined in {doc}`evaluation`.

match
  Two values match when they are equal, except that two reals match when they are within about a
  millionth of their size. Matching is not equality, and only the runtime matches values: the step
  of a play or a stepper is read from the scene by matching. Defined in {doc}`evaluation`.

number limit
  ±10¹⁵⁰, the bound on every number. Every result and every write is clamped to it. Defined in
  {doc}`evaluation`.

seed
  A free variable of type `rand-seed`, from which random values are computed. Defined in
  {doc}`evaluation`.

default seed
  The seed that a random function with no `(seed …)` uses: the only seed of the file that holds
  it, or, when that file has no variable of type `rand-seed`, the seed of the file rand of the
  standard library. Defined in {doc}`evaluation`.

site
  The number that each call of a random function has, counted from 0 in the order of the calls in
  the source after the rewrite step. Defined in {doc}`evaluation`.

declaration
  A form that creates a variable, a type or an object, with a name or without one, such as
  `(real a 1)`, `(motif m …)` or `(circle c …)`, or an `import`, which makes the names of another
  file usable ({numref}`declarations-and-bindings`).

binding
  A name that a `let`, a `foreach` or a parameter gives to a value for a part of a source. A binding
  creates nothing ({numref}`declarations-and-bindings`).

scope
  A part of a file in which some names may be used, such as the body of a motif or of a `let`
  ({numref}`scopes`).

file scope
  The scope of a whole file. Its names are the names of its top-level declarations, the names
  that its imports give, and the names of the declarations of its scene at any depth
  ({numref}`scopes`).

file to import
  A `.mtp` file that another file imports with `import`. It holds only the forms that
  {numref}`import-file-holds` allows at its top level. Defined in {doc}`imports`.

value
  A primitive or an object: what a container holds ({doc}`data-model`).

attribute
  A container that belongs to a value, such as `r` of a circle or the item `xs[0]` of a list, whose
  label is its position. Like a variable, it holds one value, and is free, bound or const
  ({numref}`objects`).

function
  An object whose only attribute is `name`, and which the runtime calls. `(func f …)` declares a
  function, and each evaluation of `(fn …)` results in a new function ({numref}`functions`).

movement
  An object that the runtime executes by writing its targets over time. `(move …)`, `(score …)`
  and `(A …)` for an animation `A` each result in a new movement ({numref}`objects`, {doc}`time`).

container
  A variable or an attribute. Each container holds one value, and is free, bound or const
  ({doc}`data-model`).

collection
  A group, a row, a column or a score: an object that holds other objects, its members.

primitive
  A value that never changes and has no identity, such as a number, a string or a list
  ({numref}`values`).

special form
  A `let` or a `foreach` written in a body. It is replaced by its items, which may be of any kind
  that the body holds ({numref}`body-let-foreach`, {doc}`data-model`).

clause
  A form that is part of the form around it and has no result of its own, such as a named
  argument, `exists-when`, or a binding such as `(k 2)` in `(let ((k 2)) …)` ({doc}`data-model`).

compound
  A form that evaluates to a primitive, a type, an object or an attribute,
  and creates nothing that a writer can write, such as `(+ 1 2)` or `(if f a b)` ({doc}`data-model`).

object
  A value that has an identity and attributes, each of which behaves like a variable, such as the
  scene, a shape, a component, a function or a record ({numref}`objects`).

variable
  A named holder of one value, which is free, bound or const ({numref}`variables`).

record
  An object that consists only of the attributes that it is declared with ({numref}`records`).

supertype
  A type B is a supertype of a type A exactly when A is a subtype of B ({numref}`fits`).

subtype
  A type A is a subtype of a type B exactly when A is a subset of B. A value of type A is accepted
  where a value of type B is expected exactly then ({numref}`fits`).

guard
  A compound that evaluates to a bool, in the body of a control or a listener, such as
  `(<= c.x 5)`, that limits what that writer writes ({numref}`writer-guards`).

condition
  A clause that limits the values of the type in the form around it, such as `(>= 0)` or
  `(one-of 'a' 'b')`: `(real (>= 0))` holds the reals that are at least 0 ({numref}`constraints`).

refined type
  A type with conditions, written `(T C…)`, whose values are the values of T that meet every
  condition ({numref}`the-types`, {numref}`constraints`).

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

world model
  Everything that one `.mtp` source file defines, such as its shapes, variables and components.
  The compiler builds it, the .mtpc stores it, and the runtime holds it as the live model. Defined
  in {doc}`world-model`.

move
  A compound `(move T …)` that results in a new movement. When the runtime executes the movement, it
  writes one target, a variable or an attribute, to a new value over a duration. Every control and
  listener that changes the model over time triggers movements.
  Defined in {doc}`time`.

score
  A movement that holds movements, its members, as a group is a shape that holds shapes. Each
  member is placed in time by its own lag, and a score is a collection. `(in-order …)` and `(at-once …)` are scores whose members run one after another, or
  together. Defined in {doc}`time`.

motif
  A shape type, `(motif M PARAMS ITEM…)`. `(M N …)` declares an `M`: the body of the motif with the
  values of its parameters. Defined in {doc}`world-model`.

animation
  A template of movements, `(animation N PARAMS ITEM…)`, as a motif is a template of shapes. With an
  animation `A`, `(A …)` is a compound that results in a new `A`, which is a movement: the body of the
  animation with the values of its parameters. Defined
  in {doc}`time`.
```
