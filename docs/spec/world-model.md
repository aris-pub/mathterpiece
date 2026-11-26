# World model

:::{note}
Not drafted yet. This page defines: the objects, their attributes, identity, the tree of collections, primitives and objects, and equality for each type.
:::

## Defaults on a collection and on a shape declared with a motif

This rule exists so that a group, a row or a column can set an attribute once for all its members.

```{rule} collection-defaults
A `(defaults (A V)…)` on a group, a row or a column sets `A` to `V` on each member, at any depth, that a
collection may set `A` on and whose declaration does not set `A`, the nearest collection winning. On a
member declared with a motif, each `(A V)` is added to its own `(defaults …)`. On a shape declared with
a motif, which is not a collection ({doc}`data-model`), it sets `A` on every shape of the motif's body,
at any depth, that has `A` and does not set it. Each `A` must be an attribute that a collection may set
on its members, or it is a {term}`compile error`.
```

## Formulas

This rule exists so that every term of a formula is known when compiling.

```{rule} formula-terms
A formula's string is its positional argument, any expression that evaluates to a string known when
compiling. The formula has a term `N` for each `\term{N}{…}` in it.
```

This rule exists so that a formula can set an attribute once for all its terms.

```{rule} formula-defaults
A `(defaults (A V)…)` in a formula sets `A` to `V` on each term whose `(term …)` form does not set `A`,
or that has no `(term …)` form.
```

The `(defaults …)` of a formula is a named argument, so it must come after the string and before
the body ({numref}`named-arguments-first`). The body may hold `(term …)` forms, `exists-when` forms
and variables. So `(formula f $'\term{a}{x}' (defaults (padding 3)) (term a (fill #'red')))` is
allowed, and the same formula with the string after the `(defaults …)`, or after a `(term …)`, is a
compile error.

:::{admonition} Code differs
:class: note
The compiler rejects a formula string that is not a literal, even when it is known when compiling:
`(int n 2 (const)) (formula f f'x^{n}')` is the error "a formula's LaTeX is known when compiling".
Bead mtp-33l1 makes the compiler follow the rule.
:::
