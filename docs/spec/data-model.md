(data-model)=
# Data model

This page defines the things that the compiler builds from a source and that the runtime holds:
values, variables, objects and namespaces. What the parser reads, {term}`literals <literal>`
among it, is defined in {doc}`grammar`. This page specifies the language.

## Values

```{rule} values
A value is a piece of data that never changes and has no identity: two values that are equal are
the same value. The values are the numbers, the bools, the strings, the colors, the fonts, the
points, the transforms, the lists, the functions and `none`. A value comes from a literal
({numref}`literal-types`) or from another expression.
```

So `(+ 1 2)` and `3` give the same value. Every value but a function and a transform can be written
as a literal. A function is written with `fn` or declared with `func`, and a transform is given by a
call such as `(rotate 30)`.

## Variables

```{rule} variables
A variable is a named holder of one value. It is free, bound or const. A free variable holds its
value until a writer writes a new one. A bound variable holds the value of its expression at all
times. A const variable rejects every attempted write. A variable with no name is a
{term}`compile error`.
```

So `(real a 1)` is a free variable whose value is 1 when the page opens, `(real b (* 2 a))` is a
bound variable whose value is always twice that of `a`, and `(real_ 1)` is an error. A variable is
not an object.

:::{admonition} Code differs
:class: note
`(real_ 1)` compiles, and nothing can read the variable that it makes. Bead mtp-1s8z makes it a
compile error.
:::

## Objects

```{rule} objects
An object is a thing that has an identity and attributes. Each attribute behaves like a variable:
it holds one value, and it is free, bound or const. An object stays the same object while the
values of its attributes change. The compiler knows what to do with some of the built-in objects,
such as shapes, which it draws.
```

The objects are the scene, the shapes, the instances of motifs and variants, the components, the
transitions, the animations and the namespaces. An object usually has a name, but it has an
identity without one: `(circle_ (r 1))` is a circle with no name. Two circles declared with the
same attributes are two objects.

## Namespaces

```{rule} namespaces
A namespace is an object that consists only of the attributes that it is declared with.
```

So `(namespace style (real width 2) (color ink 'navy'))` is an object with the two attributes
`width` and `ink`, read as `style.width` and `style.ink`. The compiler does nothing with a
namespace beyond holding its attributes.
