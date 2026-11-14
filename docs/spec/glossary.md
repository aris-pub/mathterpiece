# Glossary

:::{note}
Not drafted yet. Each term the spec defines will be listed here, with a link to where it is defined.
:::

```{glossary}
evaluation
  Computing the value of an expression, when compiling or while drawing. Evaluation changes
  nothing. Defined in {doc}`evaluation`.

folding
  Computing an expression whose inputs are all known when compiling, and writing its value into
  the .mtpc in place of the expression. Defined in {doc}`evaluation`.

match
  Two values match when they are equal, except that two reals match when they are within about a
  millionth of their size. The step of a play or a stepper is read from the scene by matching.
  Defined in {doc}`evaluation`.

number limit
  ±10¹⁵⁰, the bound on every literal and every written number. Defined in {doc}`evaluation`.

seed
  A free variable of type `rand-seed`, from which random values are computed. Defined in
  {doc}`evaluation`.

site
  The number that the compiler gives each place where a random function is written, counted from
  0. Defined in {doc}`evaluation`.

undefined
  An operation is undefined at an input where it has no value, such as `(/ x 0)`. It gives `none`
  while drawing, and is a compile error when its inputs are known when compiling. Defined in
  {doc}`evaluation`.
```
