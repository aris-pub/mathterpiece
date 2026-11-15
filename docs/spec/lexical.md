(lexical)=
# Lexical syntax

This part defines the characters of a source and the tokens that the parser makes of them. The
next part, {doc}`grammar`, defines how the parser puts the tokens together into forms. The tokens
of this part and the rules of the next part are one grammar, in the file `docs/spec/mtp.lark`,
written in the notation of the Lark parser. The test `tests/test_grammar.py` reads every source of
the project both with this grammar and with the parser of the compiler, `mathterpiece/parse.py`,
and checks that the two accept the same sources and produce the same forms.

This part states the language as the author has decided it. The parser accepts exactly the text
that this part allows, and rejects everything else. Where the parser does not follow a rule yet, a
note after the rule says what the parser does today and names the bead that will change it. The
test lists each such source as a known difference, with its bead. A box marks each question that
is still open.

## How the grammar is written

The grammar is a list of definitions, `name: definition`. A name in capitals is a {term}`token`:
a piece of text that the parser reads whole. A name in small letters is a rule, and
{doc}`grammar` defines the rules. In a definition:

- `"…"` is the text between the quotes.
- `/…/` is a regular expression, in the notation of Python's `re` module. `[\s\S]` is any
  character.
- `a b` is `a` followed by `b`, `a | b` is either one, `a?` is `a` or nothing, `a*` is any number
  of `a`, `a+` is one `a` or more, and `( )` groups.
- `(?!…)` matches no text. It fails when the text that follows matches `…`. A token that is only
  such a check, such as `NOT_PART`, is used only inside other tokens.
- `INT.2` gives the token `INT` the priority 2. A token with no number has the priority 0.
- The tree of forms does not keep a token whose name starts with `_`.

```{rule} tokens-in-context
At each place in a source, the parser reads only the tokens that the grammar allows at that place.
Where several of them could start there, they are tried from the highest priority down, and the
first that matches is read. A token written in quotes in the grammar, such as `"true"` or `"!="`,
that a token of the same priority also matches whole, such as {token}`mtp:NAME`, is read as the
quoted token where the grammar allows the quoted token, and as the other token elsewhere.
```

This is how Lark reads the grammar with `parser="lalr"` and `lexer="contextual"`, and the test
reads it the same way. So `true` is the token {token}`mtp:TRUE` where a {term}`word` may start,
and `truex` is a {token}`mtp:NAME`. In the same way, `circle_` is the token {token}`mtp:HEAD` only
where a form may have its head ({numref}`name-underscore`).

## Characters

```{mtp-grammar} bom-token
```

```{rule} source-text
A source is a sequence of Unicode characters. A file is read as UTF-8, with Python's universal
newlines: each `\r\n` and each `\r` alone becomes `\n`. A byte order mark (U+FEFF) at the very
start of a source is ignored. The text has no other change.
```

A byte order mark at any other place, outside strings and comments, is an error, because it is no
blank ({numref}`blank`) and no character of a word ({numref}`name-characters`).

:::{admonition} Code differs
:class: note
`mathterpiece/cli.py:103` reads a file with `path.read_text(encoding="utf-8")`, which keeps the
mark, and `parse.py:174` then raises "expected a form at the top level". Bead mtp-ydd4.7.1 makes
the parser drop the mark.
:::

```{rule} node-positions
Each node that the parser produces has a position: the line and the column of its first
character, counting from 1. A byte order mark at the start is not counted. A line feed (U+000A)
starts a new line. Every other character, a tab and a carriage return included, adds 1 to the
column. A node that the parser builds from a shorter spelling has the position given in
{numref}`shorthand-forms`.
```

## Blanks and comments

```{mtp-grammar} blank-tokens
```

```{rule} blank
A {term}`blank` is a sequence of whitespace characters and comments. A whitespace character is one
of space (U+0020), tab (U+0009), line feed (U+000A) and carriage return (U+000D). A
{term}`comment` starts with `;` and runs up to the next line feed, or to the end of the source. A
blank has no meaning: it only separates two tokens. Inside a string, `;` and whitespace are text.
```

So U+00A0 (no-break space), U+2028 (line separator), a form feed and the other characters for
which Python's `str.isspace()` is true are errors outside strings and comments.

:::{admonition} Code differs
:class: note
`parse.py:157` (`skip_blank`) and `parse.py:75` (`_is_delimiter`) use `ch.isspace()`, so every
Unicode whitespace character is a blank. Bead mtp-ydd4.7.2 limits blanks to the four characters
of the rule.
:::

:::{admonition} Open question Q-lexical-3
:class: warning
A comment may stand inside the braces of an interpolated string, as in `$'{x ; note\n}'`, because
`parse.py:501` and `parse.py:510` skip blanks there with `skip_blank`, which also skips comments.
Such a comment runs to the end of the line, so it can hide the closing brace and the closing
quote of the string. The grammar allows it, as the parser does. The decisions do not settle this
case. Option A: allow comments inside braces. Option B: allow only whitespace there.
:::

## Where tokens end

```{rule} run
A {term}`run` is a longest sequence of characters in which no character is a blank or one of
`( ) [ ] { } " | ; :`. A {term}`word` is one run read whole: a name, a number, an operator or a
boolean. A run that is none of these is an error.
```

The characters `'`, `$`, `#`, `@`, `.`, `/` and `^` do not end a run, so `a$'x'` is one run, and it
is not a word. Each token of a word matches a whole run. Where a token could match only the start of
a run, the rest of the run would be read as a second word right after it, and
{numref}`adjacent-items` does not allow two words with no blank between them. So the grammar rejects
every run that is not one word, as the parser does.

:::{admonition} Code differs
:class: note
`parse.py:319` ends a run at `:` only inside the braces of an interpolated string, so `a:b` is one
run, and a name, everywhere else. Bead mtp-ydd4.7.3 changes this, together with the characters of
a name.
:::

```{rule} no-part-after-form
The `)` that closes a form is never followed directly by `.` or `[`: `(sort xs).x` and
`(sort xs)[0]` are errors. The form `(. X Y)` reads a part of the value of a form
({numref}`dot-form`).
```

```{mtp-grammar} closing-token
```

## Names

A {term}`name` is a word that refers to something declared: `theta`, `p.pos`, `show-tan`. It is
one or more {term}`name parts <name part>` joined by dots. `p.pos.x` is the name of the three
parts `p`, `pos` and `x`.

```{mtp-grammar} name-tokens
```

```{rule} name-characters
A name part starts with a {term}`letter`, one of the ASCII letters `a` to `z` and `A` to `Z`. Then
come any number of letters, {term}`digits <digit>` and hyphens (`-`). Last comes `?`, or nothing.
```

So `theta`, `show-tan`, `x2`, `a-`, `none?` and `p.empty?` are names. `2x`, `-x`, `a?b`, `x'`,
`a!b`, `a*b`, `a=b`, `a:b`, `θ` and `x²` are not, and neither is any run that holds a character
that is not ASCII. Since no name holds `'` or `@`, a run that starts with `tex'`, `doc@` or
`free@` is a TeX string, a docstring or a free start at the start of a node
({numref}`tex-strings`, {numref}`prefix-forms`), and an error in every other place, such as after
`|` in a bar or after a `.` that follows an index: `a|tex'q'` and `xs[0].tex'q'` are errors.

:::{admonition} Code differs
:class: note
`parse.py:27` (`NAME_EXCLUDED`) and `parse.py:82` (`_valid_name_part`) allow every character
but `( ) [ ] { } . / ; " $ ^ | @ #` and a few first characters. So the parser reads `a!b`, `a*b`, `a=b`,
`!=x`, `f'`, `a'b`, `a:b`, `θ`, `x²` and names that hold control characters or U+FEFF as names, and
`a|tex'q'` as the bar of the names `a` and `tex'q'`. Bead mtp-ydd4.7.3 makes the parser follow the
rule. The site lexer of `docs/_ext/mtp_sphinx.py` follows it already.
:::

:::{admonition} Open question Q-lexical-4
:class: warning
The decision on names (P7) is "letters, digits and hyphens". Digits and blanks are ASCII by the
same decision, but the decision does not say whether letters are ASCII too. The rule above allows
only ASCII letters, so `θ` and `ünï` are not names. Option A: keep ASCII letters only. Option B:
allow every character for which Python's `str.isalpha()` is true, as `θ`. No source of the
project has a name with a letter that is not ASCII. But the built-in constants `π`, `τ` and `∞`
(`builtins.py:246` to `builtins.py:254`, and {numref}`infinity`) are names
today. With option A, none of the three can be written. With option B, `π` and `τ` can, and `∞`
cannot, since it is not a letter.
:::

```{mtp-grammar} head-token
```

```{rule} name-underscore
An underscore stands only at the very end of the head of a form, right after its last name part:
`(circle_ (r 1))`, `(marks.grid_ …)` and `(line|none_ …)`. Such a head is the token
{token}`mtp:HEAD`.
```

So an underscore in any other place is an error: `x_` as an argument, `a_b`, `_x`, `_` alone,
`a_.b`, `a._`, `_.a` and `_[0]`. An underscore at the end of the head of a form means that the form
has no name ({numref}`unnamed-head`).

:::{admonition} Code differs
:class: note
`parse.py:86` allows `_` at the end of every part of every name, in any place, so the parser reads
`(f x_)`, `a_.b`, `a._` and `_.a` as names, and `_[0]` too, because `parse.py:342` reads an index
before `parse.py:352` rejects a lone `_`. Bead mtp-ydd4.7.3 makes the parser follow the rule.
:::

## Booleans, none and the operators

```{mtp-grammar} keyword-tokens
```

```{rule} literal-words
A word that is `true` or `false` alone is a {term}`boolean`. A word that is `none` alone is the
literal `none`. Each of the words `+ - * / ^ < <= > >= = != .` alone is an {term}`operator`: a name
of one part. A boolean, an operator or a number is never followed directly by `[`: only a name may
have an index. `none` may have one: `none[0]` is a name whose parts are `none` and `0`.
```

A word that only starts with one of these is a name when it follows {numref}`name-characters`, so
`truex`, `true.x` and `none.x` are names. `!=x` is not a word.

:::{admonition} Open question Q-lexical-7
:class: warning
`true`, `false` and `none` may be name parts: `xs[0].true`, `p.none` and `true.x` are names,
because `parse.py:346` compares the whole run with `true`, `false` and `none`. And `none[0]` is a
name, while `true[0]` is an error, because `parse.py:362` checks only `true` and `false` before an
index. The grammar follows the parser here. The decisions do not settle this case. Option A: make
`true`, `false` and `none` errors as any part of a name. Option B: keep the parser's rule.
:::

## Reserved words

```{rule} reserved-words
These words are {term}`reserved <reserved word>`: `scene`, `animation`, `transition`, `move`,
`in-order`, `at-once`, `when`, `else`, `true`, `false`, `none`, `const`, `self` and `doc`. A
reserved word is never the name of a declaration, of a member of a namespace, a palette or a
formula, or of the name bound by a `foreach`.
```

The parser does not check this rule. The compiler does (`compiler.py:99`, `RESERVED`).

:::{admonition} Open question Q-lexical-8
:class: warning
The documents have two lists. The list of `syntax.md` (section 2, "Names") has every word above
but `doc`, while `compiler.py:99` adds `doc`, and `reference.md` ("Docstrings") has the sentence
"`doc` is a reserved word". In `parse.py:26`, the set named `RESERVED` holds the characters
`[ ] { }`, not words. Besides, the names of the special forms of `compiler.py:122` (`if`, `cond`,
`let`, `fn` and the others) are not reserved: a variable may be named `if`, and only a function may
not (`compiler.py:181`). Q-core-26 in {doc}`core` asks the same question about `doc`. The
decisions do not settle this case. To decide: whether `doc` is in the
list, and whether the names of the special forms are reserved.
:::

```{rule} reserved-characters
Outside a string, `{`, `}` and `"` are errors, and so is a `$` or a `#` that is not followed by
`'`. Outside the format spec of a field ({numref}`interpolated-strings`), `:` is an error. Strings
are written in single quotes only.
```

## Numbers

```{mtp-grammar} number-tokens
```

```{rule} number-literals
A {term}`digit` is one of the ASCII digits `0` to `9`. A word that matches one of the number
tokens is a number, of the kind of the token:

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

```{mtp-grammar} string-tokens
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

```{mtp-grammar} prefix-tokens
```

```{rule} prefix-forms
At the start of a node, `doc@` followed directly by a string is a {term}`docstring`, and `free@`
followed directly by a node is a {term}`free start`. No blank may stand between the prefix and the
string or node after it. {numref}`shorthand-forms` gives the form that each one stands for. `@`
may not stand in any other place.
```

## Interpolated strings and name strings

```{mtp-grammar} interpolation-tokens
```

```{rule} interpolated-strings
An {term}`interpolated string` is written `$'…'`, and a {term}`name string` is written `#'…'`.
Their text has the escapes of {numref}`string-literals`, and in it `{{` is `{` and `}}` is `}`. A
`{` that is not doubled opens a {term}`field`. A field is: blanks, one node, blanks, then
optionally a {term}`format spec`, which is `:` followed by any characters but `{`, `}` and `'`,
and last `}`. A `}` that is not doubled and does not close a field is an error. A name string has
at least one field.
```

The parser keeps the format spec as written. This part does not give its meaning. Since `:` ends
a run ({numref}`run`), `{x:.2f}` holds the name `x` and the format spec `.2f`. A `:` in a node
nested in the node of a field is an error, so `{(f a:b)}` is an error.

The grammar has no rule that depends on the depth of a field, so a field is read in the same way
at every depth. When a string nested in the node of a field ends, the node and the rest of the
field go on by the same rules as before the nested string. So `$'{$'{a}'}'` is the interpolated
string whose one field holds the interpolated string `$'{a}'`, and in `$'{#'n-{k}'.x:y}'` the
field holds `#'n-{k}'.x` and the format spec `y`.

:::{admonition} Code differs
:class: note
`parse.py:505` sets `in_braces = True` when a field starts, and `parse.py:509` sets it to `False`
when the field ends, instead of setting back the value that it had before. So after a string
nested in a field ends, the parser reads the rest of the outer field as if it were outside braces:
`$'{$'{a}'}'` is an error, and in `$'{#'n-{k}'.x:y}'` the parser reads `x:y` as one name part.
Bead mtp-kzx2 fixes this.
:::
