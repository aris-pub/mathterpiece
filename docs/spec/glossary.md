# Glossary

:::{note}
Not drafted yet. Each term the spec defines will be listed here, with a link to where it is defined.
:::

```{glossary}
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

core form
  A form that is not sugar, and which the rewrite step leaves as it is. Defined in
  {doc}`compiler-runtime`, and each one in {doc}`core`.

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

sugar
  A form that can be rewritten into core forms without computing any value. Defined in
  {doc}`compiler-runtime`.

syntax error
  An error by which the parse step rejects a source. Defined in {doc}`compiler-runtime`.

view
  A component through which the reader sees the model: a canvas, a readout or a display. Defined in
  {doc}`compiler-runtime`.
```
