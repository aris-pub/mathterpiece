# World model

:::{note}
Not drafted yet. This page defines: the objects, their attributes, identity, the tree of collections, primitives and objects, and equality for each type.
:::

## Defaults of a collection

```{rule} collection-defaults
A `(defaults (A V)…)` on a group, a row or a column gives each `(A V)` to each of its members, at
any depth, that takes `A` from a collection and does not give `A` itself. When several collections
give `A`, the nearest one wins. A member that is an instance gets `(A V)` in its own
`(defaults …)`. Each `A` is one that a collection gives its members, and any other is a
{term}`compile error`.
```

## Formulas

```{rule} formula-terms
The string of a formula is its positional argument, right after its name: any string expression whose
value is known when compiling. It declares the terms that it marks with `\term{name}{…}`.
```

```{rule} formula-defaults
A `(defaults (A V)…)` in a formula gives each `(A V)` to each term of the formula whose `(term …)`
form does not give `A`, and to each term that has no `(term …)` form. The terms are those that the
formula's string marks.
```

The `(defaults …)` of a formula is a named argument, so it comes after the string and before the
body ({numref}`named-arguments-first`). The body holds the terms, the `exists-when` forms and the
variables. So `(formula f $'\term{a}{x}' (defaults (padding 3)) (term a (fill #'red')))` is allowed,
as a text is written `(text t 'hi' …)`, and the same formula with the string after the
`(defaults …)`, or after a `(term …)`, is an error.

:::{admonition} Code differs
:class: note
The compiler rejects a formula string that is not a literal, even when it is known when compiling:
`(int n 2 (const)) (formula f f'x^{n}')` is the error "a formula's LaTeX is known when compiling".
Bead mtp-33l1 makes the compiler follow the rule.
:::
