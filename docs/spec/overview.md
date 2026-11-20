# Overview

## How rules are written

Each rule of the spec is stated once, in a numbered box. Rules are numbered by page: Rule 2.1 is
the first rule of page 2. A rule has a label as well as a number, and the spec and the errors of the
{term}`compiler` cite a rule by its label ({numref}`conformance`), so a citation keeps working when
rules are added or moved. For example, the rule with the label `declare-before-use` is
stated in {ref}`scope`, and {numref}`declare-before-use` is a citation of it.

(signatures)=
## How signatures are written

A signature gives a head with everything that it takes, and the type of each. It is how the spec
describes a head, and is not mtp source:

```text
(circle NAME
  (like shape)
  (r:(real (>= 0)) 1)
  (doc:string ''))

(text NAME VALUE:string
  (like shape)
  (halign:(string (one-of 'start' 'middle' 'end')) 'start')
  (valign:(string (one-of 'top' 'middle' 'baseline' 'bottom')) 'baseline')
  (doc:string ''))

(formula NAME TEX:string
  (doc:string '')
  ITEMS)
  ITEMS := (any (either term exists-when variable))
```

- A word in capitals stands for what the form gives in its place: `NAME` for the declared name.
- `X:T` is a {term}`positional argument`, called X in the spec, of type T. The positional arguments
  come in the order of the signature.
- `(A:T D)` is a {term}`named argument <named argument>` `A` of type T, whose default is D. `(A:T)`, with no
  default, is a named argument that the form must give.
- `(like T)` stands for every argument in the signature of T, which is a kind of thing, such as
  `shape`, or a head, such as `rect`.
- `(doc:string '')` is the docstring, which comes after the named arguments ({numref}`docstrings`).
- `ITEMS` is the body. The line under the signature, `ITEMS := …`, says what the body holds, with
  four forms: `(one X)` is exactly one X, `(some X)` is one X or more, `(any X)` is any number of
  X, none included, and `(either A B …)` is one of A, B and so on. The items come in the order
  written, and `EXPR:T` is any expression of type T.

## Terms

Every term the spec defines is in the {doc}`glossary`.

## Examples

Every example in the spec is compiled while the spec's pages are built, and an example that does not
compile stops the build. Each is shown as its source, then live:

```{mtp-example}
; a point on a segment, and a slider and a drag that move it
(scene s
  (real a 1 (>= 0) (<= 4))
  (line track (from [0 0]) (to [4 0]) (stroke #'gray'))
  (circle p (pos [a 0]) (r 0.15) (fill #'crimson')))

(canvas v (x -0.5) (y -0.5) (width 5) (height 1) s
  (on-drag p (move a (to pointer.x))))
(slider push (move a (from 0) (to 4)) (label 'a'))
(readout r f'a = {a:.2f}')
```
