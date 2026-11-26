(lexical)=
# Lexical syntax

This page defines the characters of a source, and the {term}`names <name>`, numbers,
{term}`string` {term}`literals <literal>` and other pieces of text that the {term}`parser` reads
whole. The next page, {doc}`grammar`, defines how the parser puts these pieces together into
{term}`expressions <expression>`, forms among them. The definitions of this
page and the rules of the next page are one grammar, written in the notation of the Lark parser and
shown in pieces on the two pages. The whole grammar is also one file, [mtp.lark](https://github.com/aris-pub/mathterpiece/blob/main/docs/spec/mtp.lark).

The parser accepts exactly the text
that this page allows, and rejects everything else.

## How the grammar is written

The grammar is a list of definitions, `name: definition`. A definition whose name is in capitals
gives a piece of text that the parser reads whole, such as a name, a number or a string literal,
with no {term}`whitespace` or {term}`comment` inside it. A definition whose name is in small letters
is a rule of {doc}`grammar`. In a definition:

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

This rule exists so that the parser reads the same text the same way wherever two definitions of the grammar could both match.

```{rule} grammar-in-context
The parser reads, at each place, only what the grammar allows there. Where several definitions
in capitals match, it reads the one of the highest priority, and among those, the longest match.
```

This is how Lark reads the grammar with `parser="lalr"` and `lexer="contextual"`. So `truex` is a {token}`mtp:NAME`, and not {token}`mtp:TRUE` followed by
`x`. In the same way, `circle_` matches {token}`mtp:HEAD` only where a form may have its
{term}`head` ({numref}`name-underscore`).

## Characters

```{mtp-grammar} bom
```

This rule exists so that the parser reads the same characters whatever system wrote the file.

```{rule} source-text
A source is a sequence of Unicode characters, read from a UTF-8 file. Each `\r\n` and each lone `\r`
becomes `\n`, and a byte order mark (U+FEFF) at the very start is dropped. Nothing else changes.
```

A byte order mark at any other place, outside string literals and comments, is an error, because it
is not whitespace ({numref}`whitespace-and-comments`) and not a character of a {term}`word`
({numref}`word-ends`).

This rule exists so that every compiler gives an error the same line and column.

```{rule} expression-positions
Each expression has a position: the line and column of its first character, both counted from 1.
A newline starts a new line, and every other character, a tab included, adds 1 to the column. An
expression built from a shorter spelling has the position given in {numref}`parser-sugar`.
```

## Whitespace and comments

```{mtp-grammar} whitespace-and-comments
```

This rule exists to specify what the parser skips between expressions.

```{rule} whitespace-and-comments
Whitespace is space, tab and newline. A comment runs from `;` to the next newline or the end of the
source. Neither has any meaning, except inside a string literal, where both are text.
```

A source holds no carriage return, since {numref}`source-text` turns each one into a newline. So
U+00A0 (no-break space), U+2028 (line separator), a form feed, a vertical tab and the other
characters whose Unicode general category is Zs, or whose bidirectional class is WS, B or S, are
errors outside string literals and comments. {doc}`grammar` gives the places where whitespace and comments may be written, and
{numref}`interpolated-strings` the places inside an {term}`interpolated string`.

## Where words end

This rule exists so that the parser splits text into words the same way in every compiler.

```{rule} word-ends
A word is a name, a number, an {term}`operator`, a {term}`bool` literal or `none`. A word runs from its
first character up to whitespace, the end of the source, or one of `( ) [ ] { } " | ; :`, and that
text must be exactly one word.
```

The characters `'`, `$`, `#`, `@`, `.`, `/` and `^` do not end a word, so `a$'x'`, `1x` and `a'b`
are errors: none of them is one word. The grammar rejects them, as the parser does, because by
{numref}`adjacent-items` only a form may follow a word with no whitespace between them.

This rule exists to keep the syntax uniform and easy to read and to parse: only a name is followed by `.` or `[`.

```{rule} no-name-part-after-form
The `)` that closes a form is never followed directly by `.` or `[`: `(sort xs).x` is an error.
```

A part of the value of a form is read with the form `(. X Y)` ({numref}`dot-name-part`), as
`(. (sort xs) 0)`.

```{mtp-grammar} closing-parenthesis
```

## Names

A name is a word that refers to a type, a variable, an object or a binding: `theta`, `show-tan`.
A {term}`qualified name` is two or more {term}`name parts <name part>` joined by dots, such as
`p.pos`: `p.pos.x` is the qualified name of the three name parts `p`, `pos` and `x`. After syntactic
sugar is rewritten, a qualified name is a `(. X K)` form whose `K` is a string: `p.pos` is
`(. p 'pos')` ({numref}`sugar-rewrites`). A name part after a dot is not a name: it is the label of an
attribute or the name of a member, and means nothing on its own.

```{mtp-grammar} names
```

This rule exists to specify which text the parser reads as a name.

```{rule} name-characters
A name part is an ASCII {term}`letter`, then any number of letters, {term}`digits <digit>` and hyphens,
then `?` or nothing. A name part is never `true`, `false` or `none`.
```

So `theta`, `show-tan`, `x2`, `a-`, `none?`, `the-true-value`, `truex`, `p.empty?`, `found?.x` and
`ball.on-floor?` are names or qualified names. `2x`, `-x`, `a?b`, `x'`, `a!b`, `a*b`, `a=b`, `a:b`, `θ`, `π` and `x²`
are not, and neither is any word that holds a character that is not ASCII. `true.x`, `p.true`,
`none.x`, `xs[0].none` and `none[0]` are errors, since one of their name parts is `true` or `none`.
Since no name holds `'` or `@`, text that starts with `f'` is an {term}`interpolated string`, and a
name followed by `@` starts a prefixed form, at the start of an expression
({numref}`interpolated-strings`, {numref}`prefix-forms`). Both are errors in every other place,
such as after `|` in a {term}`broadened type` or after a `.` that follows {term}`brackets`:
`a|f'q'`, `xs[0].f'q'` and `a|r@1` are errors.

```{mtp-grammar} heads-with-no-name
```

This rule exists so that the parser can tell a head with no name from a name that holds an underscore.

```{rule} name-underscore
An underscore may end the head of a form, right after its last name part, as in `(circle_ (r 1))`,
and may appear nowhere else. Such a head matches {token}`mtp:HEAD`.
```

So an underscore in any other place is an error: `x_` as an argument, `a_b`, `_x`, `_` alone,
`a_.b`, `a._`, `_.a` and `_[0]`. An underscore at the end of the head of a form means that the form
has no name ({numref}`unnamed-head`).

## Bools, none and the operators

```{mtp-grammar} bools-and-none
```

This rule exists to specify which words the parser reads as bools, as `none` and as operators, and not as names.

```{rule} literal-words
`true` and `false` are the bool literals, and `none` is the literal `none`. `+ - * / ^ < <= > >= =
!= .` are the operators, names of one name part that are never followed directly by `[`.
```

So `+[0]` is an error. `true[0]`, `none[0]` and `3[0]` are errors too, since by
{numref}`adjacent-items` only a form may follow a bool literal, `none` or a number directly. `!=x`
is not a word.

## Keywords

This rule exists to fix the words that a source may not use as names.

```{rule} keywords
A {term}`keyword` is a word of {numref}`keywords-table`.
```

Each keyword is the head of a form of the language.

:::{table} The keywords, from the inventory of heads in {doc}`heads`.
:name: keywords-table

| Heads of | Keywords |
|---|---|
| Declarations of objects | `scene`, `formula`, `record`, `palette`, `movement` |
| Declarations of shapes and collections | `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `bezier`, `arc`, `ring`, `text`, `group`, `row`, `column`, `parametric` |
| Declarations of {term}`components <component>` | `canvas`, `readout`, `display`, `slider`, `button`, `play`, `stepper`, `toggle` |
| Declarations of {term}`listeners <listener>` | `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove`, `on-show`, `on-hide`, `on-view`, `on-ready`, `on-live`, `on-quiet` |
| Declarations of functions, types and animations | `func`, `colormap`, `type`, `interface`, `motif`, `variant`, `animation` |
| Other items of {term}`bodies <body>` | `import`, `let`, `foreach`, `exists-when`, `term`, `doc` |
| Compounds | `.`, `name`, `if`, `when`, `cond`, `and`, `or`, `fn`, `rec`, `type-of`, `as`, `free`, `concat`, `fmt` |
| Movements and their collections | `move`, `wait`, `jump`, `score`, `lag`, `at-once`, `in-order` |
:::

The heads of {term}`named arguments <named argument>`, such as `x`, `r`, `size`, `gap`,
`step`, `fill`, `duration`, `like`, `defaults` and `loop`, are not keywords, and neither are the
heads of {term}`conditions <condition>`, such as `length` and `one-of`, and `const`.

Which names no declaration and no binding may take is defined in {numref}`declaration-names`.

This rule exists so that names stay plain text, and so that these characters are never mistaken for part of other syntax.

```{rule} reserved-characters
Outside a string literal, `"` is an error, and so is a `$` or a `#` not followed by `'`. Outside a
{term}`format spec` ({numref}`interpolated-strings`), `:` is an error. `{` and `}` start and end a list
({numref}`lists`). String literals take single quotes only.
```

## Numbers

```{mtp-grammar} numbers
```

This rule exists so that the parser reads every number to the same value and the same kind in every compiler.

```{rule} number-literals
A digit is an ASCII digit `0` to `9`. A word that matches a number definition is a number of that
kind, the first of COMPLEX, IMAG, RATIO, REAL and INT that matches it whole:

- {token}`mtp:INT` is an {term}`int`, of any size: `007` is 7 and `+4` is 4.
- {token}`mtp:RATIO` is a {term}`ratio`, an exact fraction reduced, with the sign on the numerator only:
  `-2/4` is `-1/2`. A denominator of 0 is an error.
- {token}`mtp:REAL` is a {term}`real`, the binary64 number nearest to the decimal, with a decimal point or
  an exponent: `2.5`, `1.`, `.5`, `1e3`.
- {token}`mtp:IMAG` is a {term}`complex` with real part 0, such as `2i`.
- {token}`mtp:COMPLEX` is a complex with both parts, real first, each read as a real: `1+2i`.
```

So `٣` (ARABIC-INDIC DIGIT THREE) and `²` are not digits. `1-2` is an error, since it is no
number, and the difference of 2 and 1 is written `(- 2 1)`.

## Strings

```{mtp-grammar} string-literals
```

This rule exists to specify which text the parser reads as a string, and what each escape stands for.

```{rule} string-literals
A string literal is in single quotes. Inside it, `\'` is a quote, `\\` a backslash and `\n` a line
feed. Any other backslash is an error, and every other character, a line feed included, is itself.
```

This rule exists so that TeX can be written with its backslashes as they are, without an escape for each one.

```{rule} tex-strings
A TeX string is written `$'…'`. Inside it, `\'` is a quote and every other character is itself, so
`\frac` and `\\` stay as written. A backslash and the next character are read as a pair, so in
`$'a\\'` the last quote closes the string. Its value is an ordinary string.
```

This rule exists to specify which text the compiler reads as a color.

```{rule} color-literals
A color is written `#'…'`, syntactic sugar for `(color-of f'…')`. `(color-of S)` is the color that `S`
names: a CSS color name, `transparent`, or 3, 4, 6 or 8 hex digits, with or without `#`, in either
case. Any other text is a {term}`compile error` when `S` is known when compiling, and otherwise gives
`none`, so the type is then `color|none`. A string is read as a color only through `color-of`.
```

So `#'red'`, `#'#ff0000'` and `#'ff0000'` are the same color, and `#'#f00'` is too, and
`#'#{h}'` is the color whose hex digits are the string `h`. No CSS color
name is made only of hex digits, so a name and a hex color are never confused. `(fill 'red')` is a compile error, since `'red'` is a string.

:::{admonition} Code differs
:class: note
The compiler reads `#'…'` as a color literal, whose text holds no braces, and has no `color-of` and
no `rgb`. Bead mtp-ivdt.
:::

## Prefixes

```{mtp-grammar} prefixes
```

This rule exists to specify how the parser reads `H@X`, a short way of writing a form of one name and one expression.

```{rule} prefix-forms
`H@X`, written with nothing between its parts, is `(H X)`, where H is a name that is neither an
operator nor ends with `_`, and X is any expression that is not itself a prefixed form. Besides a
name string `@'…'` ({numref}`interpolated-strings`), `@` appears nowhere else.
```

So `doc@'The dot.'` is the {term}`docstring` `(doc 'The dot.')`, `free@green` is the
{term}`free starting value` `(free green)`, `r@1` is `(r 1)`, and `(circle c r@1 fill@#'red')` is
`(circle c (r 1) (fill #'red'))`. `free@(mix a b)` is `(free (mix a b))`, `r@(* 2 k)` is
`(r (* 2 k))` and `pos@[1 2]` is `(pos [1 2])`. `fill@free@green`, `+@1`, `circle_@c`, `r@ 1` and
`r @1` are errors. The form `(H X)` must be allowed where it is written, by the same
rules as when it is written with parentheses: `if@c` is `(if c)`, which is an error.

## Interpolated strings and name strings

```{mtp-grammar} interpolated-strings
```

This rule exists to specify how the parser reads a string with expressions inside it, and what each part becomes.

```{rule} interpolated-strings
An interpolated string is `f'…'`, a {term}`name string` `@'…'`, and a color string `#'…'`
({numref}`color-literals`). Their text has the escapes of {numref}`string-literals`, and `{{` and `}}`
stand for `{` and `}`. A single `{` opens braces holding one expression, then an optional format spec,
then `}`, with no comment inside. A format spec is `:` followed by any characters but `{`, `}` and
`'`. A stray `}` is an error, and a name string holds braces at least once. A list written first in
the braces needs whitespace before it: `f'{ {a b} }'`.
```

The parser keeps the format spec as written. This page does not give its meaning. Since `:` ends
a word ({numref}`word-ends`), `{x:.2f}` holds the name `x` and the format spec `.2f`. A `:` in an
expression nested in the expression in braces is an error, so `{(f a:b)}` is an error. A comment
inside a form in the braces is allowed, since it is inside the form and not around the
expression: `f'{(f ; c\n x)}'` holds the form `(f x)`. `f'{x ; c\n}'` is an error.

The grammar has no rule that depends on how deep braces are nested, so braces are read in the
same way at every depth. When a string literal nested in the expression in braces ends, the
expression and the rest of the braces go on by the same rules as before the nested string literal.
So `f'{f'{a}'}'` is the interpolated string whose braces hold the interpolated string `f'{a}'`, and
in `f'{@'n-{k}'.x:y}'` the braces hold `@'n-{k}'.x` and the format spec `y`.
