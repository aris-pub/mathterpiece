# Open questions

The first drafts of five pages raised 67 open questions. Most of them are cases of a few missing
principles. This page groups them by principle. Each group proposes one principle, lists the
questions that it settles, and gives the options. The questions themselves are in the warning
boxes of each part.

| Part | Questions |
|---|---|
| {doc}`compiler-runtime` | Q-compiler-runtime-1 to 10 |
| {doc}`lexical` | Q-lexical-1 to 10 |
| {doc}`grammar` | Q-grammar-1 to 11 |
| {doc}`core` | Q-core-1 to 27 |
| {doc}`evaluation` | Q-evaluation-1 to 13 |

The drafts of {doc}`scope` and {doc}`well-formedness` raised three more: Q-scope-1, decided on 2026-11-21 (a declaration may read its own
attributes, by its name or through `self`, as long as no-dependency-cycles holds), and Q-well-formedness-1 and Q-well-formedness-2, which are
decided under P1 and P4.

## P1. When bodies are checked: once, or once per copy

**Today.** The compiler expands each `foreach` into its copies and each motif into its instances,
and then checks every copy and every instance on its own, with the actual values of `i` or of the
parameters. Checking and folding are interleaved, because a copy can only be checked once its
values are known.

**The question.** The prover must be as small as possible. Two designs are possible:

- **Check, then expand.** A `foreach` body is checked once, with `i` ranging over its known range,
  and a motif body is checked once, with each parameter ranging over its declared type and
  constraints. Expanding then needs no check. Errors point at the body as written. An imported
  motif is checked once. A body that is safe only for some values of a parameter is rejected,
  unless the parameter declares a constraint that makes it safe.
- **Expand, then check** (as today). Each copy is checked with its actual values, which accepts more
  programs. The prover runs once per copy, and an error in a motif body is reported for one
  instance.

**Settles:** Q-compiler-runtime-1, Q-compiler-runtime-2, Q-core-3, Q-core-6, and the order of
the steps in {doc}`compiler-runtime`.

**Decided:** check, then expand: each `foreach` body and each motif body is checked once, and the
copies and instances are not checked again ({numref}`check-bodies-once`). In {doc}`core`, a form
whose rewrite would need the value of a `foreach` name or a motif parameter is core
({numref}`names-from-values`).

**Decided (2026-11-15):** a branch of an `if` is checked only for the values for which it runs. The
spec lists exactly which conditions narrow the range of a name: a comparison with `=`, `!=`, `<`,
`<=`, `>` or `>=` of the name with a number known in the prove step, and `cond`, `when`, `and` and
`or` through their rewrites into `if`. No other condition narrows ({numref}`if-narrowing`)
(Q-well-formedness-1). So examples/spiral-of-copies.mtp, which reads `dot-{(- k 1)}` only where
`k` is not 0, compiles once the body of a `foreach` is checked once.

## P2. Syntactic sugar means exactly its rewrite

**Proposed principle.** Every syntactic sugar form means exactly the core forms that it rewrites into. Where
the compiler gives a syntactic sugar form a different meaning today, the compiler is wrong, and
is changed to match the rewrite. A form that cannot be given a rewrite without computing a value or knowing
a type is core.

**Settles:** `p.r` and `(. p r)` (Q-grammar-2, Q-core-1), `(wait t)` and `(move none (duration t))`
(Q-core-4), `cond`, `and` and `or` as `if` (Q-core-19, Q-evaluation-1), an `in-order` of one item
(Q-core-22), `(on-drag p p.pos)` (Q-core-23), `(foreach i n …)` and `(range n)` (Q-core-27),
`like` (Q-core-2), and the defaults of collections, animations and formulas (Q-core-15, 18, 21).
Using a type to choose a rewrite makes the form core (Q-core-7, `map` over an int).

**Decided:** syntactic sugar means exactly its rewrite, and where the code gives it another meaning,
the code is changed. A form that needs a value or a type to be rewritten is core
({numref}`sugar-form`, {numref}`sugar-rewrites`).

**Decided (2026-11-15):** `(on-drag p p.pos)` is syntactic sugar for `(on-drag p (move p.pos (to pointer)))`,
and `p.x` and `p.y` likewise, and the two spellings mean the same at all times. Dragging a group, a
row or a column, fixed-size or not, writes its `translate`, for both spellings
({numref}`sugar-rewrites`, {numref}`drag-group-shift`) (Q-core-23). `(foreach k n …)` means
exactly `(foreach k (range 0 n) …)`. A `foreach` over a count, or over a list whose length is known
only while drawing and has an upper bound, makes as many copies as the bound, and copy k exists
only while k is below the count or the length ({numref}`foreach-count`,
{numref}`foreach-bounded-length`) (Q-core-27). Since an int and a list are told apart by their
type, `(foreach k n …)` stays core by {numref}`sugar-form`.

**Decided (2026-11-19):** a form that leaves out an argument that has a default is core, and the
default is given where its head is defined: `(dash L)`, a random function with no `(seed …)` and
`(roll-dice)` are not rewrites. `(range X)` is removed: `(range LO HI)` with neither `gap` nor `num`
has a gap of 1, so `(range 0 n)` replaces `(range n)` (mtp-z8i1).

## P3. Which forms are core

Under P2, these forms need a decision of their own: `import` (Q-core-8), `type` (Q-core-9),
`palette` (Q-core-10), `colormap` (Q-core-11), variants (Q-core-12), rows and columns
(Q-core-13), `pos` as `x` and `y` (Q-core-14), `exists-when` (Q-core-16), `let` (Q-core-17), the
search for the only seed (Q-core-5), and a function that takes the name of an operator
(Q-core-20). Each is listed in {doc}`core` with the rewrite that it would have.

**Decided:** P2 is applied form by form, and only the cases where that changes an existing figure
are brought to the author. Syntactic sugar: `import`, `type`, `palette`, `pos`, the defaults of groups,
rows, columns and formulas, and the search for the only seed. Core: `colormap`, variant
instances, rows and columns, `exists-when`, `let`, the defaults of instances and of animations,
and an `in-order` of one item. The operators are built-in functions ({numref}`built-ins`),
which a declared function may replace ({numref}`declaration-names`). The list is in {doc}`core`,
"Summary".

The two cases that changed existing figures, Q-core-23 and Q-core-27, are decided under P2.

## P4. One meaning for every expression, at both times

**Proposed principle.** An expression has one value for given inputs, whether the compiler folds
it or the runtime computes it. The compiler folds only what it can compute exactly as the runtime
does.

**Settles:** exact ratios when folding and floats while drawing (Q-evaluation-2), `infty` as an
input while drawing (Q-evaluation-4), rounding of colours (Q-evaluation-5), the last bits of trig,
`exp`, `log` and `mod` (Q-evaluation-9), and the ±10¹⁵⁰ limit (Q-evaluation-3).

The open choice is what numbers are: IEEE doubles at both times, with `1/3` only a way to write a
real, or exact ratios at both times, which the runtime would then implement.

**Decided:** ints and ratios are exact at both times, and a folded value is final
({numref}`same-value-at-both-times`). The first decision let reals differ in their last digits,
and the decisions of 2026-11-15 below replace it.

**Decided (2026-11-15):** ints and ratios are exact at both times ({numref}`number-types`). Every
function on reals gives the correctly rounded binary64 result of its exact value, at both times,
so folding and drawing never differ, and the prover does not widen ranges
({numref}`correctly-rounded-reals`, {numref}`same-value-at-both-times`) (Q-evaluation-9,
Q-evaluation-12). Infinity is removed from the language: `infty` is not a name, a real is finite,
and an overflow gives `none` ({numref}`number-types`, {numref}`operations-that-give-none`)
(Q-evaluation-4, Q-evaluation-10, Q-evaluation-11). The ±10¹⁵⁰ limit applies to every starting
value known when compiling ({numref}`number-limit`). The channels of a mixed color round halves up
at both times, as CSS `color-mix()` does (Q-evaluation-5, {numref}`mixed-color-channels`).

A type `real|infty`, with `real` finite, may be added later, when a figure needs it.

**Decided (2026-11-16):** an animation that loops forever has no duration, so its `duration` is
`none`, and its type is `real|none`. `(real d a.duration)` is then a compile error by the rules on
`none`, and `(real|none d a.duration)` gives `none`. An animation that ends has a duration that is
a real. The rule goes on the time page.

**Decided (2026-11-15):** arithmetic saturates at the number limit. Every number, int, ratio or
real, lies within -10¹⁵⁰ to 10¹⁵⁰. Every result of an operation or a built-in function is its exact
value, correctly rounded for a real, and then clamped to the number limit, at both times, as a
write already is. So no operation overflows, and no operation gives `none` because of the size of
its result. Ints and ratios stay exact inside the limit. A literal beyond the limit is still a
compile error ({numref}`number-limit`). This replaces "an overflow gives `none`" and the limit on
starting values above. Every range of the prover lies within the number limit, and a division
whose divisor has a range that holds 0 has the range of the whole number limit
({numref}`range-rules`), so Q-well-formedness-2 goes away.

## P5. Equality for each type

**Today.** `=` compares numbers exactly, points and lists item by item, and everything else by
identity, so `(= f f)` is false while drawing for a function `f`. A second, tolerant comparison
matches a play's steps and a canvas's rest.

**Proposed principle.** Primitives compare by content: numbers exactly, points, lists and colours
item by item, strings and choices exactly. Objects, such as shapes, compare by identity.
Functions, transitions and animations cannot be compared, and comparing them is a compile error.
The tolerant comparison is not equality: it gets its own name and is used only by the runtime.

**Settles:** Q-evaluation-7.

**Decided:** as proposed, primitives compare by content, objects by identity, `=` on
functions, transitions and animations is a compile error, and the tolerant comparison is called
matching and is used only by the runtime ({numref}`equality-by-content`,
{numref}`equality-operands`, {numref}`matching`).

## P6. Termination

**Today.** A function may call itself, and nothing makes a call end. The compiler stops folding at
a depth of about 80 and leaves the call to the runtime. The runtime has no limit, and a stack
overflow replaces the component with an error. Three examples use recursion: `best-in` in
bourgain-densities.mtp, `koch` in koch-snowflake.mtp and `has-divisor` in ulam-spiral.mtp.

**Options.**
- **A depth limit.** A call nested deeper than a fixed limit gives `none`,
  the same limit at both times. Every expression then has a value. The prover proves nothing new.
- **No recursion.** A function may not call itself, directly or through others. Every
  expression ends. The three examples are rewritten with `map`, `reduce` and `range`.
- **Proved termination.** A call to itself must make an int argument smaller, with a lower bound
  that the prover can show. This adds a proof to the prover.

**Settles:** Q-evaluation-8.

**Decided:** a depth limit, the same at both times ({numref}`call-depth-limit`).

**Decided (2026-11-15):** `max-call-depth` is 256 (Q-evaluation-8). A call known when compiling
that passes it when folded is a compile error, and a call of a recursive function does not get a type that includes
`none` ({numref}`call-depth-limit`). Since no error may appear after loading (P11), what happens
to a call past the limit while drawing is open: Q-evaluation-13 in {doc}`evaluation`.

## P7. What a name may contain, and what text the parser accepts

**Proposed principle.** The parser accepts exactly the text that the spec allows, and rejects
everything else. The spec allows what the docs describe: names of letters, digits and hyphens,
with an optional `?` at the end and `_` only after a head, ASCII whitespace, ASCII digits, and a
byte order mark at the start.

**Settles:** Q-lexical-1 to 9, and the lexer of the site (mtp-phpx).

**Decided:** the parser accepts exactly what the spec allows: names of letters, digits and hyphens
with an optional `?` at the end and `_` only right after a head, ASCII whitespace and digits, and a
byte order mark at the start of a file ignored.

**Decided (2026-11-15):**

- Letters in names are ASCII only, so `π`, `τ` and `∞` are not names ({numref}`name-characters`)
  (Q-lexical-4).
- `?` may end each name part of a name, as in `found?.x` ({numref}`name-characters`).
- `true`, `false` and `none` may be part of a name, as in `the-true-value`, but never a whole
  name or a whole name part between dots, so `p.true` is an error ({numref}`name-characters`)
  (Q-lexical-7).
- Whitespace is space, tab, carriage return and line feed ({numref}`whitespace-and-comments`).
- No comment may be written in the braces of an interpolated string, around the expression
  ({numref}`interpolated-strings`) (Q-lexical-3).
- A form may touch its neighbors with no whitespace between them ({numref}`adjacent-items`)
  (Q-grammar-1).
- No declaration of any kind takes a keyword as its name: the head of a declaration, a shape, an
  expression form, a step, a component or a listener, or `term`, `doc`, `exists-when` or `import`
  ({numref}`keywords`). The heads of named arguments are not keywords. No declaration takes the
  name of a built-in type, `pointer` or `self`. A declaration may take the name of a built-in
  function or constant, and from it on the name means the declared thing. `true`, `false` and
  `none` are values, never names. The names of the standard library are ordinary declarations
  brought in with `import` ({numref}`declaration-names`) (Q-lexical-8, Q-core-26).
- The coined words "token", "run", "chunk", "sequence" and "field" are not used: the spec writes
  out what they mean. A piece of a name is a "name part" ({numref}`name-characters`).

## P8. Declare before use, everywhere

**Proposed principle.** A name is used only after its declaration, in every scope, with no
exceptions, imports included. Named arguments come before the body, in any order.

**Settles:** `exists-when` that names a later member (Q-grammar-8), `import` after the forms that
use it (Q-grammar-11), the items of a formula in any order (Q-grammar-9), and where a docstring
may be written (Q-grammar-3).

**Decided:** a name is used only after its declaration in every scope, imports included, and
named arguments come before the body, in any order.

**Decided (2026-11-15):** a docstring comes after all the positional arguments and all the optional
arguments, and before the body. A form that has no body has its docstring last
({numref}`docstrings`).

## P9. `let` and `foreach` may be written wherever declarations may be written

**Proposed principle.** `let` and `foreach` may be written in every body that holds declarations
or items, and nowhere else: not among the named arguments of a shape.

**Settles:** Q-grammar-4 to 7. Q-grammar-10 (whether a listener on its own view names that view)
was a separate question, filed as mtp-6k7f.

**Decided:** `let` and `foreach` may be written in every body that holds declarations or items, the
top level included, and never among the arguments of a form. This includes the constraints of a
variable or a type, the conditions of a writer, every `(defaults …)`, and the items of a palette
and of an interface ({numref}`body-let-foreach`, {numref}`bodies-table`).

**Decided (2026-11-11, mtp-6k7f):** every listener is written in the body of its view, acts only on
what happens in that view, and has no `(in …)`. A listener on its own view leaves out the name of
the view. Controls stay at the top level, with `(in …)` ({numref}`listeners-in-views`)
(Q-grammar-10).

## P10. What a conforming implementation must match

**Proposed principle.** These are normative: which world models are accepted and which are
rejected, the meaning of the .mtpc, and what the runtime does. These are not: the wording of
errors, the bytes of the .mtpc, the output of `mtp parse` and `mtp fmt`. Every change to the
format of the .mtpc changes its version. A runtime refuses a .mtpc that does not match the schema.

**Settles:** Q-compiler-runtime-3, 5, 6, 7, 8, 9 and 10, Q-lexical-10 (a bug), and the doc
contradictions Q-core-24 to 26 and Q-evaluation-6.

**Decided:** as proposed, and a runtime refuses a .mtpc that does not match the schema
({numref}`what-is-normative`, {numref}`spec-version`, {numref}`runtime-loads-mtpc`).

**Decided (2026-11-15):** nothing is left to the implementation: every source and every .mtpc has
a behavior that the spec states. A rejected source gets an error that points to at least one rule
that the source breaks, and may point to any or all of them. An error points to a rule when it
carries the label of the rule. Nothing else about an error is prescribed ({numref}`conformance`). A .mtpc that matches the schema and breaks the spec is
corrupt. The compiler never writes one, the schema is made as strong as possible, and the runtime
refuses every corrupt .mtpc and runs no part of it ({numref}`corrupt-mtpc`,
{numref}`schema-strength`, {numref}`runtime-loads-mtpc`). An operation that has no value gives
`none`, and the words "gives `none`" are used for it, never "undefined"
({numref}`operations-that-give-none`). `rand` and `rand-int` with `lo` above `hi` give `none`, and
are a compile error when both bounds are known when compiling ({numref}`none-at-known-inputs`).
Any int is a seed, and two seeds that are equal modulo 2³² draw the same values
({numref}`seed-variable`, {numref}`random-hash`) (Q-evaluation-6).

## P11. No figure breaks in front of the reader

**Principle (the author, 2026-11-15).** We do not break figures in front of the reader's face.

**Decided (2026-11-15):** once a model has loaded, nothing that a reader does and nothing that the
runtime computes makes a figure or a component fail or show an error. Every case that could fail
is rejected when compiling, or when the .mtpc is loaded ({numref}`no-errors-after-loading`). So a
call past `max-call-depth` while drawing may not be an error, and Q-evaluation-13 asks what the
language does in its place.
