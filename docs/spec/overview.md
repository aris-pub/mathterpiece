# Overview

:::{note}
The skeleton of this part: how the spec is written. The rest of the part is not drafted yet.
:::

## How rules are written

Each rule of the spec is stated once, in a box like the one below. Rules are numbered by part:
Rule 1.1 is the first rule of part 1. A rule has a label as well as a number, and the spec, the
tests, the compiler's errors and the documentation cite a rule by its label, so a citation keeps
working when rules are added or moved. The label of the rule below is `declare-before-use`, and
{numref}`declare-before-use` is a citation of it.

```{rule} declare-before-use
A name is declared before it is used. This box shows how a rule looks: the rule itself will be
stated in {ref}`scope`.
```

## Terms

Every term the spec defines is in the {doc}`glossary`.

## Examples

Every example in the spec is compiled while the site is built, and an example that does not
compile stops the build. Each is shown as its source, then live:

```{mtp-example}
; a point on a segment, and a slider and a drag that move it
(scene s
  (real a 1 (>= 0) (<= 4))
  (line track (from [0 0]) (to [4 0]) (stroke 'gray'))
  (circle p (pos [a 0]) (r 0.15) (fill 'crimson')))

(canvas v (x -0.5) (y -0.5) (width 5) (height 1) s
  (on-drag p (move a (to pointer.x))))
(slider push (move a (from 0) (to 4)) (label 'a'))
(readout r $'a = {a:.2f}')
```
