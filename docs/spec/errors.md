# Errors

This page lists every rule by which the {term}`compiler` rejects a source, with the error for each
case that the rule rejects. The parse step rejects a source with a {term}`syntax error`, and the
rewrite and prove steps with a {term}`compile error` ({numref}`step-rejects-or-passes`). The column
"Step" gives the step that rejects the source ({numref}`compile-steps`).

By {numref}`conformance`, each error carries the label of at least one rule that the source breaks,
and by {numref}`what-is-normative`, its wording is free. So the messages below are the wording of
this spec, and a compiler need not use them. In a message, a word in capitals stands for text of
the source: N for a name, H for a head, A for an attribute, T and U for types, C for a condition, V
for a value, and L:C for the line and the column of a declaration. A row with an empty message has
no message in this spec yet.

## Lexical syntax

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`reserved-characters` | parse | a `"` is outside a string literal | |
| {numref}`reserved-characters` | parse | a `$` outside a string literal is not followed by `'` | "'$' must be followed by a quote" |
| {numref}`reserved-characters` | parse | a `#` outside a string literal is not followed by `'` | "'#' starts a color: #'red'" |
| {numref}`reserved-characters` | parse | a `:` is outside a {term}`format spec` | "':' may only start the format spec in the braces of an interpolated string, as in f'{x:.2f}'" |
| {numref}`word-ends` | parse | the text up to the end of a word is not one word, such as `1x` | "invalid number 'V'" |
| {numref}`no-name-part-after-form` | parse | a `.` or a `[` follows the `)` of a form | |
| {numref}`name-characters` | parse | a `?` does not end a {term}`name part` | "'?' may only end a part of a name: 'N'" |
| {numref}`name-underscore` | parse | an underscore is anywhere but at the end of a head | "an underscore may only end the head of a form, as in (circle_ (r 1))" |
| {numref}`number-literals` | parse | a {term}`ratio` literal has a denominator of 0 | "zero denominator in 'V'" |
| {numref}`string-literals` | parse | a backslash in a string literal starts no escape | "invalid escape 'V'" |
| {numref}`color-literals` | prove | the text of a color, known when compiling, names no color | "'V' is not a color: write a CSS color name or hex digits" |
| {numref}`prefix-forms` | parse | the X of `H@X` is a prefixed form | "a prefixed form cannot follow H@: write (H …)" |
| {numref}`prefix-forms` | parse | an `@` is neither in `H@X` nor in a {term}`name string` | "'@' follows the name of a head, as in r@1" |
| {numref}`interpolated-strings` | parse | an {term}`interpolated string` holds a stray `}` | |
| {numref}`interpolated-strings` | parse | a name string holds no braces | "a name string fills values into a name: with none, write the name itself, or (name 'text')" |

## Grammar

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`forms` | parse | a `(` has no `)` that closes it | "unclosed '('" |
| {numref}`forms` | parse | a `)` closes no `(` | "unexpected ')'" |
| {numref}`top-level-forms` | parse | an item at the top level is not a form | "expected a form at the top level" |
| {numref}`adjacent-items` | parse | two items of a form have nothing between them and neither is a form, such as `'a''b'` | "expected whitespace, '(', ')' or ';' after a string" |
| {numref}`unnamed-head` | prove | a head is `none_` | |
| {numref}`declared-names` | rewrite | the name of a declaration is in quotes | "a name is written bare, not in quotes" |
| {numref}`declared-names` | rewrite | a scene, a formula, a {term}`view` or a {term}`control` has no name | "a H needs a name" |
| {numref}`named-arguments-first` | prove | a {term}`named argument` is in the body | "(H …) is a named argument, so it comes before the canvas's body" |
| {numref}`named-arguments-once` | prove | a named argument is given twice in one form | "'A' is given twice" |
| {numref}`docstrings` | prove | a {term}`docstring` is an interpolated string | "a doc is plain text, known when compiling: doc@'text'" |
| {numref}`contexts` | prove | the body of a form holds an item that its head does not allow, such as a canvas in a scene | "a canvas is declared only at the top level" |
| {numref}`contexts` | prove | the body of a canvas holds nothing that evaluates to a shape, the scene, `none` or a list of shapes | |
| {numref}`contexts` | prove | a movement group holds `step` | "use (labels …) and (in-order …)" |
| {numref}`contexts` | prove | a control holds `autoplay` | "use a canvas's (on-ready …)" |
| {numref}`contexts` | prove | a {term}`writer` holds `exclusive` | "use (priority n)" |
| {numref}`contexts` | prove | a control or a {term}`listener` holds `when` | "use (active bool)" |
| {numref}`contexts` | prove | a toggle holds `value` | "give the bool its start where it is declared" |
| {numref}`contexts` | prove | a stepper holds `buttons` | "a stepper stops after each step" |
| {numref}`contexts` | prove | a body holds `dash-offset` | "write (dash {4 2} 1)" |
| {numref}`contexts` | prove | a canvas holds `move` | "a canvas takes no (move …)" |
| {numref}`contexts` | prove | the top level holds `term` | "a term is given inside its formula" |
| {numref}`contexts` | prove | a group, a row, a column or a shape of a motif holds `pointer-events` | "write (defaults (pointer-events B))" |
| {numref}`body-let-foreach` | prove | a `let` or a `foreach` is in a body that may not hold one, or a `foreach` holds a scene, a motif or a function | |

## Core and derived forms

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`sugar-rewrites` | rewrite | a point `[…]` holds other than two items | "a point is two numbers, [x y]" |
| {numref}`sugar-rewrites` | rewrite | a `when` has other than two arguments | |
| {numref}`sugar-rewrites` | rewrite | a `jump` has other than two arguments | |
| {numref}`sugar-rewrites` | rewrite | an item of a `palette` is not `(M C)` | "a palette's member is (name color)" |
| {numref}`sugar-rewrites` | rewrite | the `F` of a `parametric` is not a `curve`, or its `XS` is not a list of reals | |
| {numref}`sugar-rewrites` | rewrite | the `P` of `(pos P)` holds a call of `rand`, `rand-int`, `choice` or `shuffled` | |
| {numref}`sugar-rewrites` | rewrite | a `foreach` gives one name twice | "foreach gives 'N' twice" |
| {numref}`sugar-rewrites` | rewrite | the `(defaults …)` of an `in-order` or an `at-once` gives a `lag` | |
| {numref}`drag-group-shift` | prove | the target of an `on-drag` is the `pos`, the `x` or the `y` of a group, a row or a column | "a group has no x of its own: drag its shift, as (on-drag g g.shift)" |
| {numref}`foreach-bounded-length` | prove | the prover proves no upper bound below the {term}`number limit` for the length of a `foreach` | "the count of a foreach is known when compiling, or has an upper bound, so the copies can be made then: declare it with (<= …)" |
| {numref}`dot-name-part` | prove | a member of a group is named like an attribute of the group | |
| {numref}`names-from-values` | prove | for some value of `S`, no object named by `S` is declared before `(name S)` | "unknown name 'N'" |

## Data model

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`variables` | rewrite | a variable has no name | |

## World model

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`the-scene` | prove | the source declares two scenes | "a file has exactly one scene" |
| {numref}`collection-defaults` | prove | an `A` of a `(defaults …)` on a collection is not an attribute that a collection may set on its members | |
| {numref}`formula-terms` | prove | the string of a formula is not known when compiling | "a formula's LaTeX is known when compiling" |

## Names and scope

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`name-lookup` | rewrite | a name refers to no declaration, no binding and no built-in | "unknown name 'N'" |
| {numref}`name-lookup` | rewrite | the name is one that the file rand gives | "N comes from the standard library: (import rand N)" |
| {numref}`name-lookup` | rewrite | the name is `rand.N`, for a name N that the file rand gives | "rand.N comes from the standard library: (import rand)" |
| {numref}`declare-before-use` | rewrite | a name is used before its declaration, its binding or its import | "unknown name 'N'" |
| {numref}`one-declaration-per-scope` | rewrite | one scope declares, binds or imports a name twice | "'N' is already declared" |
| {numref}`motif-names-hide-nothing` | rewrite | a shape or a variable in the body of a motif takes a name that the file declares or imports before the motif | "H 'N' would hide the top-level T 'N' (L:C): give it another name" |
| {numref}`declaration-names` | rewrite | a declaration or a binding takes as its name a {term}`keyword`, a {term}`built-in type` or an {term}`operator` | |

## Imports

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`import-form` | rewrite | an `import` is neither `(import F)` nor `(import F N1 N2…)` | "import is (import file name…)" |
| {numref}`import-form` | rewrite | an `Ni` of `(import F N1 N2…)` is not a name of `F.mtp` | "F.mtp has no name 'Ni'" |
| {numref}`import-file-name` | rewrite | no folder holds `F.mtp` | "no F.mtp next to S.mtp or in the standard library" |
| {numref}`import-same-file` | rewrite | two different files of the same name are imported into one source | "two different files named F.mtp are imported" |
| {numref}`import-same-file` | rewrite | a file imports itself, directly or not | "F.mtp imports itself, through the files it imports" |
| {numref}`import-file-holds` | rewrite | the top level of a {term}`file to import` holds a form that it may not hold | |

## Types

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`the-types` | prove | `none` is the declared type of a declaration or of a parameter | |
| {numref}`where-types-are-written` | prove | a type is written where a value is expected | |
| {numref}`where-types-are-written` | prove | a value is written where a type is expected | "expected a type" |
| {numref}`type-forms` | prove | a type other than `list` and `func` has brackets | "T takes no item type" |
| {numref}`type-forms` | prove | `list` has other than one item type | "list takes one item type" |
| {numref}`type-forms` | prove | `list` with no item type is the head of a variable with no value, or is written anywhere else | "a plain list needs a value to take its item type from" |
| {numref}`constraints` | prove | a comparison is a condition of a type that is not a number type | "only numbers can be compared, not T" |
| {numref}`constraints` | prove | a {term}`condition` is not one of the forms of the rule, or is on a type outside its row | |
| {numref}`modular-types` | prove | a value of a modular type is compared with `<`, `>`, `<=` or `>=` | |
| {numref}`type-values` | prove | a variable of a number type has no value, and its type has no default value | "N needs a value: 0 breaks C, and there is no lower bound to use instead" |
| {numref}`type-values` | prove | a parameter with no default, whose type has no default value, is left out | "a T needs a value" |
| {numref}`form-types` | prove | the type of an expression is not a {term}`subtype` of the type expected there, an `(as T X)` included | "expected T, got U" |
| {numref}`form-types` | prove | a `(list-of …)` has no items, or only `none` items, and no list type is expected | "an empty list needs its type: write list[T]" |
| {numref}`none-only-where-allowed` | prove | a value whose type includes `none` is given to a variable whose type does not | "N may be none: give it a default with (or? value default), or declare it T\|none" |
| {numref}`none-only-where-allowed` | prove | a value whose type includes `none` is given to an attribute of a shape that is not declared `T\|none` | "N's A may be none: give it a default with (or? value default), or declare N as T\|none" |
| {numref}`interfaces` | prove | a value whose type is an {term}`interface` is read through an attribute that the interface does not list | "a T has no attribute 'A'" |
| {numref}`motif-and-variant-types` | prove | a `V`, for a variant `V`, sets an attribute that the shape of `V` sets | "a T's A is fixed" |
| {numref}`motif-and-variant-types` | prove | the shape of a variant does not read one of its parameters | |
| {numref}`motif-and-variant-types` | prove | a parameter of a variant is named like an attribute of the type of its shape | "a T already has 'A'" |
| {numref}`function-types` | prove | a variable holds a function, or a function evaluates to a function or to a value that holds one | |
| {numref}`parameters` | prove | the default of a parameter is not known when compiling | "a parameter's default must be known when compiling, or be a function" |
| {numref}`function-result-type` | prove | a function that calls itself declares no result type | |

## Evaluation

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`none-at-known-arguments` | prove | an expression whose arguments are known in the prove step gives `none` | |
| {numref}`none-at-known-arguments` | prove | a `rand` or a `rand-int` has both bounds known and `lo` above `hi` | |
| {numref}`none-never-a-condition` | prove | an expression that can be `none` is the test of an `if`, an `(active …)`, or an item of the list given to `sum`, `count`, `min`, `max`, `any`, `all` or `reduce` | "this value may be none: give it a default with (or? value default)" |
| {numref}`number-limit` | prove | a {term}`literal` is beyond the number limit | "V is beyond ±10^150, the limit of every number" |
| {numref}`default-seed` | prove | a random function has no `(seed …)` in a file with several seeds | "this file declares several seeds: name the one this uses, as (rand 0 1 (seed dots))" |
| {numref}`default-seed` | prove | the {term}`default seed` is declared after a random function that uses it | "the seed N is declared after this: a random value uses a seed declared before it" |
| {numref}`default-seed` | prove | the only variables of type `rand-seed` are const | "N is const, so it is not a seed: a random value uses a seed that is not const" |
| {numref}`default-seed` | prove | the file has no variable of type `rand-seed`, and does not import the file rand | "a random value uses a seed: declare one, (rand-seed dots 0), or import the standard one, (import rand seed)" |
| {numref}`equality-operands` | prove | neither side of `=` or `!=` has a type that is a subtype of the type of the other, and neither side is `none` | "expected T, got U" |
| {numref}`equality-operands` | prove | a side of `=` or `!=` has a type that includes a function, a movement or an animation | |
| {numref}`call-depth-limit` | prove | a call known in the prove step would go deeper than the {term}`call depth limit` when folded | |

## Well-formedness

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`check-bodies-once` | prove | the body of a function, a `foreach`, a motif or an animation is safe for only some of the values of its parameters or variables | "this value may be none: give it a default with (or? value default)" |
| {numref}`no-dependency-cycles` | prove | a bound container reads itself, directly or through other bound containers | |
| {numref}`self-reference` | prove | a variable, a `let` name or a parameter reads itself | "unknown name 'N'" |
| {numref}`self-reference` | prove | a shape in a group reads the whole group in its own form, or the count or the list of a `foreach` in the group reads the group | |
| {numref}`self-reference` | prove | the `clip` or the `(defaults …)` of a collection reads the collection | "N cannot read its own attributes in its own declaration: give the value a name with (let ((name value)) …) around N, and read that name instead" |
| {numref}`writable-targets` | prove | the target of a writer or of a movement is not a name or a qualified name | |
| {numref}`writable-targets` | prove | the target is a bound container | "N is bound: only a free variable or attribute can be written" |
| {numref}`writable-targets` | prove | the target is a const container | |
| {numref}`writable-targets` | prove | the target stands for several containers, and one of them is not free | "N is bound: only a free variable or attribute can be written" |
| {numref}`writable-targets` | prove | the target is an item of a list, or a member of a group, chosen by a position that is not known when compiling | "the position of a member to write must be known when compiling" |
| {numref}`writable-targets` | prove | the target is an attribute of a collection with no members | "N.A cannot be written: the group is empty" |
| {numref}`writer-guards` | prove | a {term}`guard` is not a comparison with `<`, `<=`, `>` or `>=` of a container that the writer writes to | |
| {numref}`writer-guards` | prove | the limit of a guard depends on the container that the guard compares | |
| {numref}`unproved-conditions` | prove | a value known in the prove step breaks a condition of the type expected there | "V breaks C" |
| {numref}`unproved-conditions` | prove | the prover cannot count an argument of a call, or of `(M …)` or `(A …)`, as meeting a condition | "N may break C" |
| {numref}`unproved-conditions` | prove | the prover cannot count the body of a function as meeting a condition of its result type, which does not include `none` | "N's result may break C: constrain what it reads so this can be proved, or declare it T\|none" |
| {numref}`unproved-conditions` | prove | the prover cannot count an item of a list `{X…}` as meeting a condition of the item type of the expected list type | |

## Concurrency model

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`movements-at-once` | prove | two movements of one movement group write to the same container at times that overlap | |

## Controls

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`slider-and-dial` | prove | the `step` or the `ticks` of a slider or a dial is 0 or below | |
| {numref}`select-options` | prove | the value of an option is not of a subtype of the type of the target, or, in a multi-select, of its item type | |

## Built-ins and the standard library

| Rule | Step | The source is rejected when | Message |
|---|---|---|---|
| {numref}`random-calls` | rewrite | a name that refers to a random function is written other than as the head of a call | "N is only called, as (N …)" |

:::{admonition} Code differs
:class: note
The rows below have no message, because today's compiler accepts the source, or rejects it with a
message about another problem, or with a message whose words this spec does not use.

- Accepted today: an empty canvas (bead mtp-ydd4.7.59), a scene, a motif or a function in a
  `foreach` at the top level (mtp-8qeb), a `let` or a `foreach` among the arguments of a form
  (mtp-ydd4.7.9), a random call in `(pos P)` (mtp-ydd4.7.25), a member of a group named like an
  attribute of the group (mtp-g3xb), a variable with no name (mtp-1s8z), a keyword or a built-in
  type as a name (`compiler.py:99`, mtp-ydd4.7.35), a variant parameter that its shape does not read
  (mtp-ydd4.7.61), a function that evaluates to a function (mtp-ydd4.7.43), a recursive function with
  no result type (mtp-127y), `rand-int` with known bounds and `lo` above `hi` (mtp-y7vp), `=` on
  functions (mtp-08wd.4), a call deeper than the call depth limit (mtp-ydd4.7.15), an item of a list
  that may break a condition of its item type, a limit of a guard that reads the target through a
  bound container (mtp-ydd4.7.44), `pointer-events` on a group (mtp-327t), the target `g.x` of an
  `on-drag` on a group (mtp-67wi), and a shape that reads a view, such as `(real a v.x)`.
- No such form today: `jump` (mtp-96um), the `parametric` of the spec (mtp-of7a), `lag`
  (mtp-idcs), modular types (mtp-rk1i), and the slider, the dial and the select of
  {doc}`controls` (mtp-9e62).
- Another problem named: the compiler rejects every read of a shape's own attributes in its own
  declaration (`compiler.py:6596`, mtp-1xob), so a cycle and a read of a whole group get that
  message. `(none_ 1)` gets "expected none, got int", `(none a none)` gets "none is not a none", a
  type as a value gets "unknown name", a target that is not a container and a guard that is not a
  comparison get messages about transitions and choreos (`compiler.py:3136`, `compiler.py:3389`),
  two scenes get "a file has exactly one scene" (`compiler.py:5141`), and a file to import that
  holds a free variable gets a message with a list of forms that differs from
  {numref}`import-file-holds`.
- Words that this spec does not use: the messages for `"`, for a stray `}` and for a part after a
  form (parse.py:274, 615, 372), for `when` and for a variable that holds a function
  (`compiler.py:6758`, `compiler.py:1672`) hold a semicolon. The message for a known argument that
  gives `none` holds the word "undefined" (`compiler.py:2485`). The message for a const target
  holds "it is never written" (`compiler.py:3581`). The message for a `(defaults …)` holds
  "container" for a collection (`compiler.py:5877`), the message for a guard holds "condition"
  (`compiler.py:4773`), the message for an unknown condition holds "constraint" (types.py:448),
  and the message for two movements at once holds "move" for a movement (`compiler.py:3418`).
- The messages for a random function with no `(seed …)` hold the word "follows" where this page
  has "uses".
:::
