# World model

:::{note}
Not drafted yet. This page defines: the objects, their attributes, identity, the tree of containers, values and mutable objects, and equality for each type.
:::

## Defaults of a container

```{rule} container-defaults
A `(defaults (A V)…)` on a group, a row or a column gives each `(A V)` to each of its members, at
any depth, that takes `A` from a container and does not give `A` itself. When several containers
give `A`, the nearest one wins. A member that is an instance gets `(A V)` in its own
`(defaults …)`. Each `A` is one that a container gives its members, and any other is a
{term}`compile error`.
```

## Formulas

```{rule} formula-terms
The string of a formula is any string expression whose value is known when compiling. It declares
the terms that it marks with `\term{name}{…}`.
```

```{rule} formula-defaults
A `(defaults (A V)…)` in a formula gives each `(A V)` to each term of the formula whose `(term …)`
form does not give `A`, and to each term that has no `(term …)` form. The terms are those that the
formula's string marks.
```

The `(defaults …)` of a formula is a named argument, so it comes before the body
({numref}`named-arguments-first`).
The body holds the string, the terms, the `exists-when` forms and the variables. By
{numref}`declare-before-use`, a `(term name …)` and an `exists-when` of a term come after the
string. So `(formula f (defaults (padding 3)) $'\term{a}{x}' (term a (fill 'red')))` is allowed,
and the same formula with `(defaults …)` last, or with `(term a …)` before the string, is an error.

:::{admonition} Code differs
:class: note
`compiler.py:4905` (`formula_decl`) looks for the string, the `(defaults …)`, the terms, the
`exists-when` and the variables at every place, so the string may come last, and `(defaults …)`
may come after a `(term …)`. Bead mtp-ydd4.7.11 makes the compiler follow the rule.
:::

:::{admonition} Code differs
:class: note
The compiler rejects a formula string that is not a literal, even when it is known when compiling:
`(int n 2 (const)) (formula f f'x^{n}')` is the error "a formula's LaTeX is known when compiling".
Bead mtp-33l1 makes the compiler follow the rule.
:::
