(formulas-page)=
# Formulas

This page defines formulas and their terms.

## Formulas and terms

This rule exists so that every term of a formula is known when compiling.

```{rule} formula-terms
A formula's string is its positional argument, any expression that evaluates to a string known when
compiling. The formula has a term `N` for each `\term{N}{…}` in it, and terms may nest. A string
that marks one name twice is a compile error.
```

So `\term{all}{\frac{\term{top}{a}}{b}}` marks the term `all` and, inside it, the term `top`.

This rule exists to fix the attributes of a term, so that a writer may change how a display shows part of a formula.

````{rule} terms
A term is an object whose attributes are given by its `(term N …)` form, with this signature, and
have their defaults when the formula has no such form for the term:

```mtp-sig
(term N TEX:string?
  (fill:color|none none)
  (opacity:unit 1)
  (background:color|none none)
  (outline:color|none none)
  (outline-width:(real (>= 0)) 1)
  (padding:(real (>= 0)) 0)
  (rounding:(real (>= 0)) 0))
```

`TEX` is the attribute `tex`, which the runtime shows in place of the text that `\term{N}{…}` marks,
and which is that text when it is left out. A `fill` of `none` is the color of the page around the
formula. `background` is a box drawn behind the term, and `outline` a line drawn around it, of width
`outline-width`, each reaching `padding` past the term with corners of radius `rounding`, and
neither moves the text around the term. `outline-width`, `padding` and `rounding` are in screen
pixels. While an `(exists-when N C)` of the formula is false, the runtime shows the formula without
the term N.
````

So with `\term{v}{}` in the string of a formula `f` and `(real q 1)` in its body,
`(term v f'{(* 2 q):.2f}')` shows the value of `2q`, typeset again when `q` changes, and
`(move f.v.background (to #'yellow') (duration 0.2))` fades a box in behind it.

:::{admonition} Code differs
:class: note
The compiler accepts the string of a `(term …)` form anywhere among its items, after its named
arguments too (compiler.py:5338). Bead mtp-ydd4.7.105.
:::

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
