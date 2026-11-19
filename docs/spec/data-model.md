(data-model)=
# Data model

This page defines the things that the compiler builds from a source and that the runtime holds:
values, variables, objects and namespaces. What the parser reads, {term}`literals <literal>`
among it, is defined in {doc}`grammar`. This page specifies the language.

<figure class="mtp-diagram">
<svg viewBox="0 0 480 412" role="img" aria-labelledby="mtp-dm-title"><title id="mtp-dm-title">A literal is source text, which the compiler reads as a value. A variable holds one value. An object has attributes, and each attribute behaves like a variable. A shape is an object that the runtime also draws. A namespace is an object with only the attributes it is declared with.</title><defs><marker id="mtp-dm-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="mtp-d-headpath" d="M0 0 L10 5 L0 10 z"/></marker></defs><rect class="mtp-d-file" x="15" y="16" width="150" height="76" rx="6"/><text class="mtp-d-name" x="90" y="40" text-anchor="middle">literal</text><text class="mtp-d-code" x="90" y="62" text-anchor="middle">3  'hi'  [1 2]</text><text class="mtp-d-sub" x="90" y="81" text-anchor="middle">text in the source</text><line class="mtp-d-arrow" x1="165" y1="54" x2="313" y2="54" marker-end="url(#mtp-dm-head)"/><text class="mtp-d-label" x="239" y="46" text-anchor="middle">the compiler reads</text><rect class="mtp-d-part" x="315" y="16" width="150" height="76" rx="6"/><text class="mtp-d-name" x="390" y="40" text-anchor="middle">value</text><text class="mtp-d-sub" x="390" y="62" text-anchor="middle">never changes,</text><text class="mtp-d-sub" x="390" y="78" text-anchor="middle">has no identity</text><rect class="mtp-d-part" x="315" y="134" width="150" height="76" rx="6"/><text class="mtp-d-name" x="390" y="158" text-anchor="middle">variable</text><text class="mtp-d-code" x="390" y="180" text-anchor="middle">(real a 1)</text><text class="mtp-d-sub" x="390" y="199" text-anchor="middle">free, bound or const</text><line class="mtp-d-arrow" x1="390" y1="134" x2="390" y2="94" marker-end="url(#mtp-dm-head)"/><text class="mtp-d-label" x="398" y="118" text-anchor="start">holds one</text><line class="mtp-d-arrow" x1="390" y1="210" x2="390" y2="282" marker-start="url(#mtp-dm-head)"/><text class="mtp-d-label" x="382" y="236" text-anchor="end">each attribute</text><text class="mtp-d-label" x="382" y="250" text-anchor="end">behaves like a variable</text><rect class="mtp-d-live" x="15" y="256" width="450" height="146" rx="10"/><text class="mtp-d-livename" x="31" y="277">objects: an identity, and attributes</text><rect class="mtp-d-part" x="35" y="284" width="190" height="102" rx="6"/><text class="mtp-d-name" x="130" y="308" text-anchor="middle">a shape</text><text class="mtp-d-code" x="130" y="330" text-anchor="middle">(circle c …)</text><text class="mtp-d-sub" x="130" y="352" text-anchor="middle">attributes r, x, y, fill, …</text><text class="mtp-d-sub" x="130" y="370" text-anchor="middle">and the runtime draws it</text><rect class="mtp-d-part" x="255" y="284" width="190" height="102" rx="6"/><text class="mtp-d-name" x="350" y="308" text-anchor="middle">a namespace</text><text class="mtp-d-code" x="350" y="330" text-anchor="middle">(namespace style …)</text><text class="mtp-d-sub" x="350" y="352" text-anchor="middle">the attributes it is</text><text class="mtp-d-sub" x="350" y="370" text-anchor="middle">declared with, nothing else</text></svg>
</figure>

## Values

```{rule} values
A value is a piece of data that never changes and has no identity: two values that are equal are
the same value. The values are the numbers, the bools, the strings, the colors, the fonts, the
points, the transforms, the lists, the functions and `none`. A value comes from a literal
({numref}`literal-types`) or from another expression.
```

Each of these gives a value:

| Written | The value | Its type |
|---|---|---|
| `3` | the number 3 | `int` |
| `(+ 1 2)` | the number 3, the same value as `3` | `int` |
| `2.5` | the number 2.5 | `real` |
| `'hi'` | the string hi | `string` |
| `true` | true | `bool` |
| `[1 2 3]` | the list of 1, 2 and 3 | `list[int]` |
| `[0 1]`, where a point is expected | the point at x 0 and y 1 | `point` |
| `none` | `none` | `none` |
| `(fn ((real x)) (* 2 x))` | the function that doubles a real | `func[real real]` |
| `(rotate 30)` | the rotation by 30 degrees | `transform` |

Every value but a function and a transform can be written as a literal. Since a value never
changes, nothing writes a value: a writer writes a variable or an attribute, which then holds a
different value. A slider that writes `(real a 1)` puts 2 into `a`, and 1 is still 1.

## Variables

```{rule} variables
A variable is a named holder of one value. It is free, bound or const. A free variable holds its
value until a writer writes a new one. A bound variable holds the value of its expression at all
times. A const variable rejects every attempted write. A variable with no name is a
{term}`compile error`.
```

For example:

| Declared | What the variable is |
|---|---|
| `(real a 1)` | free: it holds 1 when the page opens, and a slider or an animation may write it |
| `(real b (* 2 a))` | bound: it always holds twice the value of `a`, and follows `a` when `a` changes |
| `(real c 3 (const))` | const: it holds 3, and a slider that writes it is a compile error |
| `(real_ 1)` | a compile error: a variable has a name |

A variable is not an object: it has no attributes, only its one value.

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
transitions, the animations and the namespaces. For example, in

```mtp
(real a 1 (>= 0) (<= 2))
(scene sc
  (circle c (r 1) (x (* 2 a)))
  (circle d (r 1) (x (* 2 a)))
  (circle_ (r 3)))
```

- `c` is an object with the attributes `r`, `x`, `y`, `fill` and the others of a circle. Its `r`
  is free, so a slider may write `c.r`, and its `x` is bound to `(* 2 a)`.
- `c` and `d` are two objects, though they are declared with the same attributes. Writing `c.r`
  leaves `d.r` as it is.
- The third circle has no name, and is an object all the same.
- `a` is a variable, not an object.

## Namespaces

```{rule} namespaces
A namespace is an object that consists only of the attributes that it is declared with.
```

For example, `(namespace style (real width 2 (>= 0) (<= 5)) (color ink 'navy'))` is an object with
the two attributes `width` and `ink`, read as `style.width` and `style.ink`. Like any attribute,
`style.width` may be written: `(slider s (move style.width (from 0) (to 5)))` writes it. Unlike a
shape, a namespace is not drawn, and the compiler does nothing with it beyond holding its
attributes.
