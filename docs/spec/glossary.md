# Glossary

Each term that the spec defines, with the rule that defines it.

```{glossary}
:sorted:

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
```
