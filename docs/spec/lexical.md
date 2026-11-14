(lexical)=
# Lexical syntax

This part defines the characters of a source and the tokens that the reader makes of them. The
next part, {doc}`grammar`, defines how the reader puts the tokens together into forms. The tokens
of this part and the rules of the next part are one grammar, in the file `docs/spec/mtp.lark`,
written in the notation of the Lark parser. The test `tests/test_grammar.py` reads every source of
the project both with this grammar and with the reader of the compiler, `mathterpiece/parse.py`,
and checks that the two accept the same sources and produce the same forms.

This part describes the reader as it is built today. Where the reader, the older documents and
this part disagree, or where the language has no answer, a box marks an open question.

## How the grammar is written

The grammar is a list of definitions, `name: definition`. A name in capitals is a {term}`token`:
a piece of text that the reader reads whole. A name in small letters is a rule, and
{doc}`grammar` defines the rules. In a definition:

- `"…"` is the text between the quotes.
- `/…/` is a regular expression, in the notation of Python's `re` module. `\s` is a character for
  which Python's `str.isspace()` is true, and `\d` is a decimal digit (Unicode category Nd).
- `a b` is `a` followed by `b`, `a | b` is either one, `a?` is `a` or nothing, `a*` is any number
  of `a`, `a+` is one `a` or more, and `( )` groups.
- `(?!…)` matches no text. It fails when the text that follows matches `…`. A token that is only
  such a check, such as `NOT_TEX`, is used only inside other tokens.
- `INT.2` gives the token `INT` the priority 2. A token with no number has the priority 0.
- The tree of forms does not keep a token whose name starts with `_`.

```{rule} tokens-in-context
At each place in a source, the reader reads only the tokens that the grammar allows at that place.
Where several of them could start there, they are tried from the highest priority down, and the
first that matches is read. A token written in quotes in the grammar, such as `"true"` or `"!="`,
that a token of the same priority also matches whole, such as {token}`mtp:NAME`, is read as the
quoted token where the grammar allows the quoted token, and as the other token elsewhere.
```

This is how Lark reads the grammar with `parser="lalr"` and `lexer="contextual"`, and the test
reads it the same way. So `true` is the token {token}`mtp:TRUE` where a {term}`word` may start,
and `truex` is a {token}`mtp:NAME`.

## Characters

```{rule} source-text
A source is a sequence of Unicode characters. A file is read as UTF-8, with Python's universal
newlines: each `\r\n` and each `\r` alone becomes `\n`. The text has no other change.
```

:::{admonition} Open question Q-lexical-1
:class: warning
A file that starts with a byte order mark (U+FEFF) is an error. `mathterpiece/cli.py:103` reads a
file with `path.read_text(encoding="utf-8")`, which keeps the mark. U+FEFF is not a blank, so
`parse.py:174` raises "expected a form at the top level". The documents have no rule for a byte
order mark. Option A: allow a mark at the very start of a file, and drop it. Option B: keep it an
error, with a message that names it.
:::

```{rule} node-positions
Each node that the reader produces has a position: the line and the column of its first
character, counting from 1. A line feed (U+000A) starts a new line. Every other character, a tab
and a carriage return included, adds 1 to the column. A node that the reader builds from a shorter
spelling has the position given in {numref}`shorthand-forms`.
```

## Blanks and comments

```{mtp-grammar} blank-tokens
```

```{rule} blank
A {term}`blank` is a sequence of whitespace characters and comments. A whitespace character is a
character for which Python's `str.isspace()` is true. A {term}`comment` starts with `;` and runs up
to the next line feed, or to the end of the source. A blank has no meaning: it only separates two
tokens. Inside a string, `;` and whitespace are text.
```

:::{admonition} Open question Q-lexical-2
:class: warning
Every Unicode whitespace character is a blank, such as U+00A0 (no-break space) and U+2028 (line
separator), and so are U+001C to U+001F, for which `str.isspace()` is true. `parse.py:157` uses
`ch.isspace()`. The only rule in `syntax.md` (section 2, "Forms") is that "line breaks and
indentation mean nothing". Option A: keep every Unicode whitespace character. Option B: allow
only space, tab, carriage return and line feed, and make the others errors.
:::

:::{admonition} Open question Q-lexical-3
:class: warning
A comment may stand inside the braces of an interpolated string, as in `$'{x ; note\n}'`, because
`parse.py:501` and `parse.py:510` skip blanks there with `skip_blank`, which also skips comments.
Such a comment runs to the end of the line, so it can hide the closing brace and the closing
quote of the string. The documents have no rule for this case. Option A: allow comments inside
braces. Option B: allow only whitespace there.
:::

## Where tokens end

```{rule} run
A {term}`run` is a longest sequence of characters in which no character is a blank or one of
`( ) [ ] { } " | ;`, and, inside the braces of an interpolated string ({numref}`inside-braces`),
no character is `:`. A {term}`word` is one run read whole: a name, a number, an operator or a
boolean. A run that is none of these is an error. The characters `'`, `$`, `#`, `@`, `.`, `/` and
`^` do not end a run, so `a$'x'` is one run, and it is not a name.
```

Each token of a word matches a whole run. Where a token could match only the start of a run, the
rest of the run would be read as a second word right after it, and {numref}`adjacent-items` does
not allow two words with no blank between them. So the grammar rejects every run that is not one
word, as the reader does.

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
A name part is made of characters that are not blanks and not one of
`( ) [ ] { } " | ; . / $ ^ @ #`. Its first character is not a digit, not `'` and not one of
`+ - * < > =`. Outside the braces of an interpolated string, `:` may be part of a name.
```

So `a?`, `none?`, `a*b`, `x'`, `f''`, `a!b`, `a=b`, `θ`, `x²` and `a:b` are names, and `2x`,
`-x`, `'x` and `a/b` are not.

:::{admonition} Open question Q-lexical-4
:class: warning
The reader allows many more characters in names than the documents list. `syntax.md` (section 2,
"Names") has: "Letters, digits and hyphens are allowed, and some built-in names end in `?`, like
`none?`." `parse.py:27` (`NAME_EXCLUDED`) and `parse.py:82` (`_valid_name_part`) allow every
character but the ones of {numref}`name-characters`. So `!`, `*`, `=`, `<`, `>`, `,`, `&`, `%`,
`~`, `` ` ``, `\`, `:`, `'`, control characters such as U+0000, and U+FEFF may all be part of a
name. Option A: keep the reader's set. Option B: list the allowed characters, for example letters,
digits, `-`, `?`, `!`, `*` and a final `'`, and make the others errors.
:::

```{rule} name-underscore
In a name part, `_` may only be the last character: `x_` is a name part, and `a_b` and `_x` are
not. A word that is `_` alone is an error, unless `.` or `[` follows it: `_.a` and `_[0]` are
names whose first part is `_`. After a `.`, a part may be `_` alone: `a._` is a name.
```

An underscore at the end of the head of a form means that the form has no name
({numref}`unnamed-head`). An underscore has that meaning only at the end of a head.

:::{admonition} Open question Q-lexical-5
:class: warning
In `syntax.md` (section 4, "`none` as a name"), an underscore "is allowed nowhere else, in a name
or on its own". The reader allows `_` at the end of every part of every name, in any place:
`(f x_)`, `a_.b`, `p.x_` and `_.a` are names (`parse.py:86`), and `(circle_ …)` loses its
underscore only because the head is rewritten (`parse.py:91`, `_unnamed`). A lone `_` is an error
(`parse.py:352`), but only when no `[` follows it, because `parse.py:342` reads an index before
that check, so `_[0]` is a name. Option A: make `_` an error everywhere but at the end of the head
of a form. Option B: keep the reader's rule.
:::

```{rule} name-prefixes
At the start of a {term}`node`, a run that starts with `tex'` is a TeX string, a run that starts
with `doc@` is a docstring, and a run that starts with `free@` is a free start
({numref}`prefix-forms`). In other places, such as after `|` in a bar or after a `.` that follows
an index, a run that starts with `tex'` is a name: `a|tex'q'` is the bar of the names `a` and
`tex'q'`.
```

```{mtp-grammar} brace-name-tokens
```

Inside braces the rules for names are the same, but `:` ends the run ({numref}`run`), so the
brace tokens do not allow `:`.

:::{admonition} Open question Q-lexical-6
:class: warning
`'` may be part of a name after its first character, so `f'`, `a'b` and `atex'q'` are names
(`parse.py:88` leaves `'` out of its check). With {numref}`name-prefixes`, this makes `a|tex'q'`
and `xs[0].tex'q'` contain the name `tex'q'`, while `tex'q'` at the start of a node is a TeX
string. `syntax.md` has no rule for `'` in names. Option A: allow `'` only at the end of a name
part, as a prime. Option B: keep the reader's rule. Option C: make `'` in a name an error.
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

A word that only starts with one of these is a name, so `truex`, `true.x`, `none.x` and `!=x` are
names.

:::{admonition} Open question Q-lexical-7
:class: warning
`true`, `false` and `none` may be name parts: `xs[0].true`, `p.none` and `true.x` are names,
because `parse.py:346` compares the whole run with `true`, `false` and `none`. And `none[0]` is a
name, while `true[0]` is an error, because `parse.py:362` checks only `true` and `false` before an
index. Option A: make `true`, `false` and `none` errors as any part of a name. Option B: keep the
reader's rule.
:::

## Reserved words

```{rule} reserved-words
These words are {term}`reserved <reserved word>`: `scene`, `animation`, `transition`, `move`,
`in-order`, `at-once`, `when`, `else`, `true`, `false`, `none`, `const`, `self` and `doc`. A
reserved word is never the name of a declaration, of a member of a namespace, a palette or a
formula, or of the name bound by a `foreach`. The reader does not check this: the compiler does
(`compiler.py:99`, `RESERVED`).
```

:::{admonition} Open question Q-lexical-8
:class: warning
The documents have two lists. The list of `syntax.md` (section 2, "Names") has every word above
but `doc`, while `compiler.py:99` adds `doc`, and `reference.md` ("Docstrings") has the sentence
"`doc` is a reserved word". In `parse.py:26`, the set named `RESERVED` holds the characters
`[ ] { }`, not words. Besides, the names of the special forms of `compiler.py:122` (`if`, `cond`,
`let`, `fn` and the others) are not reserved: a variable may be named `if`, and only a function may
not (`compiler.py:181`). To decide: whether to add `doc` to the list of `syntax.md`, and whether
the names of the special forms are reserved.
:::

```{rule} reserved-characters
Outside a string, `{`, `}` and `"` are errors, and so is a `$` or a `#` that is not followed by
`'`. Strings are written in single quotes only.
```

## Numbers

```{mtp-grammar} number-tokens
```

```{rule} number-literals
A word that matches one of the number tokens is a number, of the kind of the token:

- {token}`mtp:INT` is an {term}`int`, of any size. `007` is 7 and `+4` is 4.
- {token}`mtp:RATIO` is a {term}`ratio`: the exact fraction of two ints, reduced, so `-2/4` is
  `-1/2`. Only the numerator has a sign. A denominator of 0 is an error.
- {token}`mtp:REAL` is a {term}`real`: the double-precision float nearest to the decimal number. A
  real has a decimal point or an exponent: `2.5`, `1.`, `.5`, `1e3`, `1.5E-3`.
- {token}`mtp:IMAG` is a {term}`complex` number whose real part is 0, such as `2i` and `-1.5e3i`.
- {token}`mtp:COMPLEX` is a complex number with both parts, the real part first, such as `1+2i`
  and `-1e+2-3.5i`. Each part is a real, so `1+2i` is `1.0 + 2.0i`.

The priorities of the grammar make a word the first of COMPLEX, IMAG, RATIO, REAL and INT that
matches it whole. This is the same kind as `parse.py:113` (`_number`) returns.
```

So `1-2` is an error, since it is no number, and the difference of 2 and 1 is written `(- 2 1)`.

:::{admonition} Open question Q-lexical-9
:class: warning
Digits are not only ASCII. `parse.py:31` uses `\d`, which matches every decimal digit of Unicode,
so `٣` (ARABIC-INDIC DIGIT THREE) is the int 3. But `parse.py:83` uses `str.isdigit()` for the
first character of a name part, which is also true of characters such as `²`, so `²x` is not a
name, while the grammar here, which uses `\d`, accepts it. And `parse.py:118` checks the value of
the denominator of a ratio, while the grammar checks that one of its digits is not `0`, so `1/٠`
(ARABIC-INDIC DIGIT ZERO) is an error for the reader and a ratio for the grammar. The test lists
these two sources as known differences. Option A: allow only `0` to `9` as digits, everywhere.
Option B: keep Unicode digits, and list which characters are digits.
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

The reader keeps the format spec as written. This part does not give its meaning.

```{rule} inside-braces
The node of a field is read {term}`inside braces`: there, `:` ends a run ({numref}`run`), so
`{x:.2f}` holds the name `x` and the format spec `.2f`. A node nested in that node, in a form or in
a list, is read inside braces too, so `{(f a:b)}` is an error. A field of a string that is nested
in a field is also read inside braces.
```

:::{admonition} Open question Q-lexical-10
:class: warning
The reader leaves the braces too early. `parse.py:505` sets `in_braces = True` when a field
starts, and `parse.py:509` sets it to `False` when the field ends, instead of setting back the
value that it had before. So after a string nested in a field ends, the reader reads the rest of
the outer field as if it were outside braces: `$'{(g $'{a}' b:c)}'` holds the name `b:c`, and
`$'{$'{a}'}'` is an error, because the reader then requires a blank or `)` after the inner string.
The grammar and {numref}`inside-braces` follow the nesting instead, and the test lists these
sources as known differences. Option A: set the value back in the reader. Option B: keep the
reader's rule.
:::
