(lexical)=
# Lexical syntax

This page defines the characters of a source, and the names, numbers, strings and other pieces of
text that the parser reads whole. The next page, {doc}`grammar`, defines how the parser puts these
pieces together into forms. The definitions of this page and the rules of the next page are one
grammar, in the file `docs/spec/mtp.lark`, written in the notation of the Lark parser. The test
`tests/test_grammar.py` reads every source of the project both with this grammar and with the
parser of the compiler, `mathterpiece/parse.py`, and checks that the two accept the same sources
and produce the same forms.

This page specifies the language. The parser accepts exactly the text
that this page allows, and rejects everything else. Where the parser does not follow a rule yet, a
note after the rule says what the parser does today and names the bead that will change it. The
test lists each such source as a known difference, with its bead.

## How the grammar is written

The grammar is a list of definitions, `name: definition`. A definition whose name is in capitals
gives a piece of text that the parser reads whole, such as a name, a number or a string, with no
whitespace or comment inside it. A definition whose name is in small letters is a rule of
{doc}`grammar`. In a definition:

- `"…"` is the text between the quotes.
- `/…/` is a regular expression, in the notation of Python's `re` module. `[\s\S]` is any
  character.
- `a b` is `a` followed by `b`, `a | b` is either one, `a?` is `a` or nothing, `a*` is any number
  of `a`, `a+` is one `a` or more, and `( )` groups.
- `(?!…)` matches no text. It fails when the text that follows matches `…`. A definition that is
  only such a check, such as `NOT_PART`, is used only inside other definitions.
- `INT.2` gives the definition `INT` the priority 2. A definition with no number has the priority
  0.
- The tree of forms does not keep the text of a definition whose name starts with `_`.

```{rule} grammar-in-context
At each place in a source, the parser reads only the text that the grammar allows at that place.
Where several definitions in capitals could match there, the parser reads the one of the highest
priority, and among those of the same priority, the one that matches the longest text.
```

This is how Lark reads the grammar with `parser="lalr"` and `lexer="contextual"`, and the test
reads it the same way. So `truex` is a {token}`mtp:NAME`, and not {token}`mtp:TRUE` followed by
`x`. In the same way, `circle_` matches {token}`mtp:HEAD` only where a form may have its head
({numref}`name-underscore`).

## Characters

```{mtp-grammar} bom
```

```{rule} source-text
A source is a sequence of Unicode characters. A file is read as UTF-8, with Python's universal
newlines: each `\r\n` and each `\r` alone becomes `\n`. A byte order mark (U+FEFF) at the very
start of a source is ignored. The text has no other change.
```

A byte order mark at any other place, outside strings and comments, is an error, because it is
not whitespace ({numref}`whitespace-and-comments`) and not a character of a word
({numref}`word-ends`).

:::{admonition} Code differs
:class: note
`mathterpiece/cli.py:103` reads a file with `path.read_text(encoding="utf-8")`, which keeps the
mark, and `parse.py:174` then raises "expected a form at the top level". Bead mtp-ydd4.7.1 makes
the parser drop the mark.
:::

```{rule} expression-positions
Each expression that the parser produces has a position: the line and the column of its first
character, counting from 1. A byte order mark at the start is not counted. A line feed (U+000A)
starts a new line. Every other character, a tab and a carriage return included, adds 1 to the
column. An expression that the parser builds from a shorter spelling has the position given in
{numref}`shorthand-forms`.
```

## Whitespace and comments

```{mtp-grammar} whitespace-and-comments
```

```{rule} whitespace-and-comments
{term}`Whitespace <whitespace>` is the four characters space (U+0020), tab (U+0009), line feed
(U+000A) and carriage return (U+000D). A {term}`comment` starts with `;` and runs up to the next
line feed, or to the end of the source. Whitespace and comments have no meaning. Inside a string,
`;` and whitespace are text.
```

So U+00A0 (no-break space), U+2028 (line separator), a form feed, a vertical tab and the other
characters for which Python's `str.isspace()` is true are errors outside strings and comments.
{doc}`grammar` gives the places where whitespace and comments may be written, and
{numref}`interpolated-strings` the places inside an interpolated string.

:::{admonition} Code differs
:class: note
`parse.py:157` (`skip_blank`) and `parse.py:75` (`_is_delimiter`) use `ch.isspace()`, so the
parser reads every character for which `str.isspace()` is true as whitespace. Bead mtp-ydd4.7.2
limits whitespace to the four characters of the rule.
:::

## Where words end

```{rule} word-ends
A {term}`word` is a name, a number, an operator, a bool or `none`. From the first character of a word up
to the next whitespace, the end of the source, or the next of the characters
`( ) [ ] { } " | ; :`, the text is exactly one word. Text that starts where a word may start and is
not one word up to there is an error.
```

The characters `'`, `$`, `#`, `@`, `.`, `/` and `^` do not end a word, so `a$'x'`, `1x` and `a'b`
are errors: none of them is one word. The grammar rejects them, as the parser does, because by
{numref}`adjacent-items` only a form may follow a word with no whitespace between them.

:::{admonition} Code differs
:class: note
`parse.py:319` ends a word at `:` only inside the braces of an interpolated string, so `a:b` is
one word, and a name, everywhere else. Bead mtp-ydd4.7.3 changes this, together with the
characters of a name.
:::

```{rule} no-part-after-form
The `)` that closes a form is never followed directly by `.` or `[`: `(sort xs).x` and
`(sort xs)[0]` are errors.
```

A part of the value of a form is read with the form `(. X Y)` ({numref}`dot-part`), as
`(. (sort xs) 0)`.

```{mtp-grammar} closing-parenthesis
```

## Names

A {term}`name` is a word that refers to something declared: `theta`, `p.pos`, `show-tan`. It is
one or more {term}`parts <part>` joined by dots. `p.pos.x` is the name of the three parts `p`,
`pos` and `x`.

```{mtp-grammar} names
```

```{rule} name-characters
Each part of a name starts with a {term}`letter`, one of the ASCII letters `a` to `z` and `A` to
`Z`. Then come any number of letters, {term}`digits <digit>` and hyphens (`-`). Last comes `?`, or
nothing. A part is never exactly `true`, `false` or `none`.
```

So `theta`, `show-tan`, `x2`, `a-`, `none?`, `the-true-value`, `truex`, `p.empty?`, `found?.x` and
`ball.on-floor?` are names. `2x`, `-x`, `a?b`, `x'`, `a!b`, `a*b`, `a=b`, `a:b`, `θ`, `π` and `x²`
are not, and neither is any word that holds a character that is not ASCII. `true.x`, `p.true`,
`none.x`, `xs[0].none` and `none[0]` are errors, since one of their parts is `true` or `none`.
Since no name holds `'` or `@`, text that starts with `tex'`, `doc@` or `free@` is a TeX string, a
docstring or a free starting value at the start of an expression ({numref}`tex-strings`,
{numref}`prefix-forms`), and an error in every other place, such as after `|` in a broadened type
or after a `.` that follows brackets: `a|tex'q'` and `xs[0].tex'q'` are errors.

:::{admonition} Code differs
:class: note
- `parse.py:27` (`NAME_EXCLUDED`) and `parse.py:82` (`_valid_name_part`) allow every character
  but `( ) [ ] { } . / ; " $ ^ | @ #` and a few first characters. So the parser reads `a!b`, `a*b`,
  `a=b`, `!=x`, `f'`, `a'b`, `a:b`, `θ`, `x²` and names that hold control characters or U+FEFF as
  names, and `a|tex'q'` as the broadened type of the names `a` and `tex'q'`. Bead mtp-ydd4.7.3
  makes the parser follow the rule. The site lexer of `docs/_ext/mtp_sphinx.py` follows it
  already.
- `parse.py:346` compares only the whole word with `true`, `false` and `none`, and `parse.py:362`
  checks only `true` and `false` before brackets, so the parser reads `true.x`, `p.true`, `none.x`
  and `none[0]` as names. Bead mtp-ydd4.7.32 makes these errors.
- `builtins.py:246` to `builtins.py:254` declare the constants `π`, `τ` and `∞`, which no source
  can write by this rule. Bead mtp-ydd4.7.33 removes them, together with `infty`.
:::

```{mtp-grammar} heads-with-no-name
```

```{rule} name-underscore
An underscore may be written only at the very end of the head of a form, right after its last
part: `(circle_ (r 1))`, `(marks.grid_ …)`, `(line|none_ …)` and `(none_ a)`. Such a head matches
{token}`mtp:HEAD`.
```

So an underscore in any other place is an error: `x_` as an argument, `a_b`, `_x`, `_` alone,
`a_.b`, `a._`, `_.a` and `_[0]`. An underscore at the end of the head of a form means that the form
has no name ({numref}`unnamed-head`).

:::{admonition} Code differs
:class: note
`parse.py:86` allows `_` at the end of every part of every name, in any place, so the parser reads
`(f x_)`, `a_.b`, `a._` and `_.a` as names, and `_[0]` too, because `parse.py:342` reads the
brackets before `parse.py:352` rejects a lone `_`. Bead mtp-ydd4.7.3 makes the parser follow the
rule.
:::

## Bools, none and the operators

```{mtp-grammar} bools-and-none
```

```{rule} literal-words
The word `true` or `false` is a {term}`bool`. The word `none` is the literal `none`. Each of the
words `+ - * / ^ < <= > >= = != .` is an {term}`operator`: a name of one part, which is never
followed directly by `[`.
```

So `+[0]` is an error. `true[0]`, `none[0]` and `3[0]` are errors too, since by
{numref}`adjacent-items` only a form may follow a bool, `none` or a number directly. `!=x` is not a
word.

## Keywords and built-in names

```{rule} keywords
A {term}`keyword` is one of the words of {numref}`keywords-table`, and no other word.
```

Each keyword is the head of a form of the language.

:::{table} The keywords, from the inventory of heads in {doc}`core`.
:name: keywords-table

| Heads of | Keywords |
|---|---|
| Declarations | `import`, `type`, `interface`, `namespace`, `palette`, `colormap`, `scene`, `formula`, `motif`, `variant`, `func`, `transition`, `animation`, `choreo` |
| Shapes and containers | `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text`, `group`, `row`, `column` |
| Items of bodies | `let`, `foreach`, `exists-when`, `term`, `doc` |
| Expression forms | `.`, `name`, `if`, `when`, `cond`, `else`, `and`, `or`, `fn`, `type-of`, `as` |
| Steps of an animation | `move`, `wait`, `roll-dice`, `at-once`, `in-order` |
| Components | `canvas`, `readout`, `display`, `slider`, `button`, `play`, `stepper`, `toggle` |
| Listeners | `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove`, `on-show`, `on-hide`, `on-view`, `on-ready`, `on-live`, `on-quiet` |
:::

The heads of optional arguments, such as `x`, `r`, `size`, `gap`, `step`, `fill`, `duration`,
`like`, `defaults` and `loop`, are not keywords, and neither are the heads of constraints, such as
`const`, `length` and `wrap`. A word that is the head of an optional argument and also a keyword,
such as `animation` or `move`, is a keyword.

```{rule} declaration-names
No declaration takes as its name a keyword, a {term}`built-in type`, `pointer` or `self`. This
holds for every kind of declaration: a variable, a shape, a function, a parameter, a name bound by
`let` or `foreach`, a member of a namespace, a palette or a formula, a motif, a font, and every
other. The built-in types are `int`, `ratio`, `real`, `complex`, `bool`, `string`, `color`, `font`,
`point`, `transform`, `transition`, `animation`, `scene`, `func`, `rand-seed`, `list`, `maybe`, the
shape types, and the interfaces `shape`, `positioned` and `sequence`. `pointer` is the name bound in
the move of a drag, and `self` the instance being built in the body of a motif. A declaration may
take the name of a built-in function, an operator included, or of a built-in constant (`pi`, `tau`
and `euler`): from that declaration on, the name refers to the declared thing
({numref}`name-lookup`).
```

So `(real if 1)`, `(circle line …)` and `(let ((self 2)) …)` are compile errors, and
`(func max ((real a) (real b)) a)` and `(real pi 3)` are allowed. `scene`, `transition`,
`animation` and `func` are both built-in types and keywords. `true`, `false` and `none` are values,
never names ({numref}`name-characters`). The names of the standard library are not built-in: they
are ordinary declarations of the files of `mathterpiece/stdlib/`, which a source brings in with
`import` ({numref}`sugar-rewrites`). The parser does not check this rule, and the compiler checks it.

:::{admonition} Code differs
:class: note
`compiler.py:99` (`RESERVED`) forbids only the names `scene`, `animation`, `transition`, `move`,
`in-order`, `at-once`, `when`, `else`, `true`, `false`, `none`, `const`, `self` and `doc`. The
special forms of `compiler.py:122` (`SPECIAL`) and the types are forbidden only as the name of a
function (`compiler.py:181`, `NOT_FUNCTION_NAMES`), so a variable may be named `if`, and a
function may not take the name of a constant. A name bound by `let` is checked against neither
(`_Compiler.let`, `compiler.py:6663`), so `(real v (let ((self 2)) self))` compiles, and `v` is 2.
docs/reference.md, "Functions" (line 124), has the same rule for constants, and is wrong. Bead
mtp-ydd4.7.35 makes the compiler and the documents follow the rule.
:::

```{rule} reserved-characters
Outside a string, `{`, `}` and `"` are errors, and so is a `$` or a `#` that is not followed by
`'`. Outside the format spec of an interpolated string ({numref}`interpolated-strings`), `:` is an
error. Strings are written in single quotes only.
```

## Numbers

```{mtp-grammar} numbers
```

```{rule} number-literals
A {term}`digit` is one of the ASCII digits `0` to `9`. A word that matches one of the number
definitions is a number, of the kind of the definition:

- {token}`mtp:INT` is an {term}`int`, of any size. `007` is 7 and `+4` is 4.
- {token}`mtp:RATIO` is a {term}`ratio`: the exact fraction of two ints, reduced, so `-2/4` is
  `-1/2`. Only the numerator has a sign. A denominator of 0 is an error.
- {token}`mtp:REAL` is a {term}`real`: the double-precision float nearest to the decimal number. A
  real has a decimal point or an exponent: `2.5`, `1.`, `.5`, `1e3`, `1.5E-3`.
- {token}`mtp:IMAG` is a {term}`complex` number whose real part is 0, such as `2i` and `-1.5e3i`.
- {token}`mtp:COMPLEX` is a complex number with both parts, the real part first, such as `1+2i`
  and `-1e+2-3.5i`. Each part is a real, so `1+2i` is `1.0 + 2.0i`.

The priorities of the grammar make a word the first of COMPLEX, IMAG, RATIO, REAL and INT that
matches it whole.
```

So `٣` (ARABIC-INDIC DIGIT THREE) and `²` are not digits. `parse.py:113` (`_number`) returns the
same kind as these priorities give. `1-2` is an error, since it is no number, and the difference
of 2 and 1 is written `(- 2 1)`.

:::{admonition} Code differs
:class: note
`parse.py:30` to `parse.py:36` use `\d`, which matches every decimal digit of Unicode, so the
parser reads `٣` as the int 3 and `1/٣` as a ratio. Bead mtp-ydd4.7.4 limits digits to `0` to `9`.
:::

## Strings

```{mtp-grammar} string-literals
```

```{rule} string-literals
A {term}`string` is written in single quotes. Inside it, `\'` is a quote, `\\` is a backslash and
`\n` is a line feed. A backslash followed by any other character is an error. Every other
character, a line feed included, is itself.
```

```{rule} tex-strings
A {term}`TeX string` is written `tex'…'`. Inside it, `\'` is a quote, and every other character is
itself: `\frac`, `\\` and `\q` stay as written. A backslash and the character after it are read
together, so in `tex'a\\'` the string is `a\\` and the last quote closes it.
```

## Prefixes

```{mtp-grammar} prefixes
```

```{rule} prefix-forms
At the start of an expression, `doc@` followed directly by a string is a {term}`docstring`, and
`free@` followed directly by an expression is a {term}`free starting value`. No whitespace or
comment may be written between the prefix and the string or expression after it.
{numref}`shorthand-forms` gives the form that each one is short for. `@` may not be written in
any other place.
```

## Interpolated strings and name strings

```{mtp-grammar} interpolated-strings
```

```{rule} interpolated-strings
An {term}`interpolated string` is written `$'…'`, and a {term}`name string` is written `#'…'`. Their
text has the escapes of {numref}`string-literals`, and in it `{{` is `{` and `}}` is `}`. A `{` that
is not doubled opens braces, which hold one expression, with whitespace or nothing before and
after it, then a {term}`format spec` or nothing, and last `}`. No comment may be written in the
braces, around the expression. A format spec is `:` followed by any characters but `{`, `}` and
`'`. A `}` that is not doubled and does not close braces is an error. A name string holds braces
at least once.
```

The parser keeps the format spec as written. This page does not give its meaning. Since `:` ends
a word ({numref}`word-ends`), `{x:.2f}` holds the name `x` and the format spec `.2f`. A `:` in an
expression nested in the expression in braces is an error, so `{(f a:b)}` is an error. A comment
inside a form in the braces is allowed, since it is inside the form and not around the
expression: `$'{(f ; c\n x)}'` holds the form `(f x)`. `$'{x ; c\n}'` is an error.

The grammar has no rule that depends on how deep braces are nested, so braces are read in the
same way at every depth. When a string nested in the expression in braces ends, the expression
and the rest of the braces go on by the same rules as before the nested string. So `$'{$'{a}'}'`
is the interpolated string whose braces hold the interpolated string `$'{a}'`, and in
`$'{#'n-{k}'.x:y}'` the braces hold `#'n-{k}'.x` and the format spec `y`.

:::{admonition} Code differs
:class: note
- `parse.py:505` sets `in_braces = True` when braces open, and `parse.py:509` sets it to `False`
  when they close, instead of setting back the value that it had before. So after a string nested
  in braces ends, the parser reads the rest of the outer braces as if it were outside braces:
  `$'{$'{a}'}'` is an error, and in `$'{#'n-{k}'.x:y}'` the parser reads `x:y` as one part. Bead
  mtp-kzx2 fixes this.
- `parse.py:501` and `parse.py:510` skip whitespace around the expression with `skip_blank`,
  which also skips comments, so the parser reads `$'{x ; c\n}'` as `$'{x}'`. Such a comment runs
  to the end of the line, so it can hide the closing brace and the closing quote of the string.
  Bead mtp-ydd4.7.31 makes it an error.
:::
