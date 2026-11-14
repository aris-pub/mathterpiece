# Open questions

The first drafts of five parts raised 67 open questions. Most of them are cases of a few missing
principles. This page groups them by principle. Each group proposes one principle, lists the
questions that it settles, and gives the options. The questions themselves are in the warning
boxes of each part.

| Part | Questions |
|---|---|
| {doc}`compiler-runtime` | Q-compiler-runtime-1 to 10 |
| {doc}`lexical` | Q-lexical-1 to 10 |
| {doc}`grammar` | Q-grammar-1 to 11 |
| {doc}`core` | Q-core-1 to 27 |
| {doc}`evaluation` | Q-evaluation-1 to 9 |

## P1. When bodies are proved: once, or once per copy

**Today.** The compiler expands each `foreach` into its copies and each motif into its instances,
and then proves every copy and every instance on its own, with the actual values of `i` or of the
parameters. Proving and folding are interleaved, because a copy can only be proved once its
values are known.

**The question.** The prover must be as small as possible. Two designs are possible:

- **Prove, then expand.** A `foreach` body is proved once, with `i` ranging over its known range,
  and a motif body is proved once, with each parameter ranging over its declared type and
  constraints. Expanding then needs no proof. Errors point at the body as written. An imported
  motif is proved once. A body that is safe only for some values of a parameter is rejected,
  unless the parameter declares a constraint that makes it safe.
- **Expand, then prove** (as today). Each copy is proved with its actual values, which proves more
  programs. The prover runs once per copy, and an error in a motif body is reported for one
  instance.

**Settles:** Q-compiler-runtime-1, Q-compiler-runtime-2, Q-core-3, Q-core-6, and the order of
the steps in {doc}`compiler-runtime`.

## P2. A shorthand means exactly its rewrite

**Proposed principle.** Every sugar form means exactly the core forms that it rewrites into. Where
the compiler gives a shorthand a different meaning today, the shorthand is wrong, and is changed
to match its rewrite. A form that cannot be given a rewrite without computing a value or knowing
a type is core.

**Settles:** `p.r` and `(. p r)` (Q-grammar-2, Q-core-1), `(wait t)` and `(move none (duration t))`
(Q-core-4), `cond`, `and` and `or` as `if` (Q-core-19, Q-evaluation-1), an `in-order` of one item
(Q-core-22), `(on-drag p p.pos)` (Q-core-23), `(foreach i n …)` and `(range n)` (Q-core-27),
`like` (Q-core-2), and the defaults of containers, animations and formulas (Q-core-15, 18, 21).
Using a type to choose a rewrite makes the form core (Q-core-7, `map` over an int).

## P3. Which forms are core

Under P2, these forms need a decision of their own: `import` (Q-core-8), `type` (Q-core-9),
`palette` (Q-core-10), `colormap` (Q-core-11), variants (Q-core-12), rows and columns
(Q-core-13), `pos` as `x` and `y` (Q-core-14), `exists-when` (Q-core-16), `let` (Q-core-17), the
search for the only seed (Q-core-5), and a function that takes the name of an operator
(Q-core-20). Each is listed in {doc}`core` with the rewrite that it would have.

## P4. One meaning for every expression, at both times

**Proposed principle.** An expression has one value for given inputs, whether the compiler folds
it or the runtime computes it. The compiler folds only what it can compute exactly as the runtime
does.

**Settles:** exact ratios when folding and floats while drawing (Q-evaluation-2), `infty` as an
input while drawing (Q-evaluation-4), rounding of colours (Q-evaluation-5), the last bits of trig,
`exp`, `log` and `mod` (Q-evaluation-9), and the ±10¹⁵⁰ limit (Q-evaluation-3).

The open choice is what numbers are: IEEE doubles at both times, with `1/3` only a way to write a
real, or exact ratios at both times, which the runtime would then implement.

## P5. Equality for each type

**Today.** `=` compares numbers exactly, points and lists item by item, and everything else by
identity, so `(= f f)` is false while drawing for a function `f`. A second, tolerant comparison
matches a play's steps and a canvas's rest.

**Proposed principle.** Values compare by content: numbers exactly, points, lists and colours
item by item, strings and choices exactly. Mutable objects, such as shapes, compare by identity.
Functions, transitions and animations cannot be compared, and comparing them is a compile error.
The tolerant comparison is not equality: it gets its own name and is used only by the runtime.

**Settles:** Q-evaluation-7.

## P6. Termination

**Today.** A function may call itself, and nothing makes a call end. The compiler stops folding at
a depth of about 80 and leaves the call to the runtime. The runtime has no limit, and a stack
overflow replaces the component with an error. Three examples use recursion: `best-in` in
bourgain-densities.mtp, `koch` in koch-snowflake.mtp and `has-divisor` in ulam-spiral.mtp.

**Options.**
- **A depth limit.** A call nested deeper than a fixed limit is undefined, so it gives `none`,
  the same limit at both times. Every expression then has a value. The prover proves nothing new.
- **No recursion.** A function may not call itself, directly or through others. Every
  expression ends. The three examples are rewritten with `map`, `reduce` and `range`.
- **Proved termination.** A call to itself must make an int argument smaller, with a lower bound
  that the prover can show. This adds a proof to the prover.

**Settles:** Q-evaluation-8.

## P7. What a name may contain, and what text the reader accepts

**Proposed principle.** The reader accepts exactly the text that the spec allows, and rejects
everything else. The spec allows what the docs describe: names of letters, digits and hyphens,
with an optional `?` at the end and `_` only after a head, ASCII blanks, ASCII digits, and a
byte order mark at the start.

**Settles:** Q-lexical-1 to 9, and the lexer of the site (mtp-phpx).

**Decided:** the parser accepts exactly what the spec allows: names of letters, digits and hyphens
with an optional `?` at the end and `_` only right after a head, ASCII blanks and digits, and a
byte order mark at the start of a file ignored.

## P8. Declare before use, everywhere

**Proposed principle.** A name is used only after its declaration, in every scope, with no
exceptions, imports included. Optional arguments come before the body, in any order.

**Settles:** `exists-when` that names a later member (Q-grammar-8), `import` after the forms that
use it (Q-grammar-11), the items of a formula in any order (Q-grammar-9), and where a docstring
may stand (Q-grammar-3).

**Decided:** a name is used only after its declaration in every scope, imports included, and
optional arguments come before the body, in any order.

## P9. `let` and `foreach` stand wherever declarations stand

**Proposed principle.** `let` and `foreach` may stand in every body that holds declarations or
items, and nowhere else: not among the options of a shape.

**Settles:** Q-grammar-4 to 7. Q-grammar-10 (whether a listener on its own view names that view)
is a separate question, already filed as mtp-6k7f.

**Decided:** `let` and `foreach` may stand in every body that holds declarations or items, the top
level included, and never among the arguments of a form.

## P10. What a conforming implementation must match

**Proposed principle.** These are normative: which world models are accepted and which are
rejected, the meaning of the .mtpc, and what the runtime does. These are not: the wording of
errors, the bytes of the .mtpc, the output of `mtp parse` and `mtp fmt`. Every change to the
format of the .mtpc changes its version. A runtime refuses a .mtpc that does not match the schema.

**Settles:** Q-compiler-runtime-3, 5, 6, 7, 8, 9 and 10, Q-lexical-10 (a bug), and the doc
contradictions Q-core-24 to 26 and Q-evaluation-6.
