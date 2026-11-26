(scope)=
# Names and scope

This page defines {term}`declarations <declaration>` and {term}`bindings <binding>`, the part of a
source in which each {term}`name` may be used, and the declaration or binding to which each use of
a name refers. Which characters a name holds is defined in {numref}`name-characters`.
Which {term}`expressions <expression>` may read the scene, a formula or the page is defined in
{doc}`binding-time`.

The rewrite step finds what each name refers to ({numref}`compile-steps`), so a source
that breaks a rule of this page is rejected in the rewrite step. A name built from a string,
`(name S)`, is resolved in the prove step instead ({numref}`names-from-values`).

## Declarations and bindings

This rule exists to separate the forms that create something from the forms that only name a value.

```{rule} declarations-and-bindings
A declaration is a {term}`form` that creates a variable, a type or an object, or, for an `import`, makes
the names of another file usable ({doc}`data-model`). What it creates exists whether or not it has a
name: `(circle_ (r 1))` creates a circle with no name. A binding names a value for part of a source and
creates nothing. The bindings are the names of a `let` and a `foreach`, the parameters of a function,
a motif, a variant or an animation, and the `N` of an `(as N)`, which is the shape being declared in a
motif and the pointer's position in a listener ({numref}`pointer-binding`). The language binds no name of
its own.
```

So `(real a 1)`, `(circle c (r a))`, `(canvas v s)`, `(func twice ((real x)) (* 2 x))` and
`(type unit real (>= 0) (<= 1))` are declarations, and so is a listener written in a
canvas, such as `(on-click c (move a (to 0) (duration 1)))`, which creates a listener with no name. In
`(let ((k 2)) (circle c (r k)))`, the circle `c` is a declaration and `k` is a binding.

In a pointer listener, `(as N)` is used like this:

```mtp
(real a 1 (>= 0) (<= 4))
(scene s (circle p (pos [a 0]) (r 0.2)))
(canvas v s
  (on-drag p (as pointer) (move a (to pointer.x))))
```

In the movement of the `on-drag`, `pointer` is the position of the pointer, so dragging `p` writes the x
of the pointer to `a`, and `p` moves with it.

In a motif, `(as N)` is used like this:

```mtp
(motif dot ((real size 1)) (as self)
  (circle c (r size))
  (text_ self.name (pos (top c 0.2)) (halign 'middle') (valign 'bottom')))
(scene s
  (dot d1)
  (dot d2 (size 0.5)))
```

In the body of `dot`, `self` is the shape being declared, so each `dot` shows its own name above
its circle: `'d1'` above the circle of `d1`, and `'d2'` above the circle of `d2`.

Inside the body, the parameters, the shapes and the variables of the body are names already:
`size` is `self.size`, and `c` is `self.c`. So `(as N)` is needed only for the parts of the shape that
have no name in the body: its `name`, the attributes that it has from its kind, such as `x`, `y`,
`rotate` or `opacity`, which are given where the shape is declared, and the shape as a whole, as in
`(f self)` or `(= self picked)`. Every read through `self` is limited by
{numref}`no-dependency-cycles`: a text in the body may read `self.x`, since the position of the
shape does not depend on the text, but `(pos (top self 0.2))` in the body is a compile error, since
the box of the shape depends on the shapes in its body.

## Scopes

This rule exists to determine, at each place in a source, which names may be used there.

```{rule} scopes
A {term}`scope` is a part of a source in which some names may be used. These are the scopes of mtp,
and the names of each one:

| Scope | Covers | Names |
|---|---|---|
| the {term}`file scope` | the whole source | every declaration at the top level, every name that an `import` makes usable ({numref}`import-declares-names`), and every declaration in the scene, at any depth |
| the {term}`body` of a motif, a variant, an animation, a function, a record or a formula | the body | the parameters of the form, the name of its `(as N)`, and every declaration in the body, at any depth |
| a `let` | for each name, the expressions given to the names after it, and the items of the `let` | the names that it binds |
| a `foreach` | the items of the `foreach` | the name that it binds |
| a listener with `(as N)` | its movement | `N` |

The scope of a body is inside the scope of the form around it, and every scope is inside the file
scope. A group, a row, a column and the scene make no scope of their own. The names that are
declared in the items of a `let` or of a `foreach` written in a body belong to the scope of that
body: only the names that the `let` or the `foreach` binds belong to its own scope.
```

A source holds at most one scene ({numref}`top-level-forms`), so the shapes of the scene can be names
of the file scope without two scenes declaring the same name, and a canvas or a listener may use them
with no prefix, as `frame` or `triangles`. A source may hold several formulas, and two of them may
each have a term `a`, so each formula makes a scope of its own, and its terms may be used outside
it only through the formula, as `pythagoras.c2`.

So the shapes of the scene, at any depth in its groups, are names of the file scope: the body of a canvas, a
{term}`listener` and a readout may use their names. A copy that a `foreach` in the scene makes, such as
`@'dot-{k}'`, is a name of the file scope too, while `k` may be used only inside the `foreach`. A
parameter may be used only in its body, and so a default of a parameter never reads another parameter.
An attribute of a record, and a member of a formula, may be used by its name only inside
that declaration, and elsewhere through it, as `theme.ink`, by {numref}`dot-name-part`. In the same way,
a shape or a variable declared in a motif's body may be used outside the body only as an attribute
of a shape of that motif, as `d1.face` ({doc}`data-model`).

This rule exists so that the compiler can resolve every name in one pass, and so that no value can depend on a value declared after it.

```{rule} declare-before-use
A use of a name refers only to a declaration, a binding or an import that comes before it, in every
scope, with no exceptions. The order is that of the source after the rewrite step, each `foreach`
read as its copies in order, and something comes before a use when its form starts before it. A use
inside the form that declares or binds the name is allowed only as {numref}`self-reference` allows.
```

So two functions may not call each other, since one of them would use the name of the other before
its declaration, and a function may call itself only by {numref}`self-reference`. A canvas must come
after the scene in its body, a {term}`control` must come after the {term}`views <view>` named in its
`(in …)`, and an `exists-when` must come after the shape named in it. Copy k of a `foreach` may
use the name of copy k - 1, which comes before it, and may never use the name of copy k + 1. By {numref}`import-declares-names`, a
name that an import makes usable may be used only after the import.

:::{admonition} Code differs
:class: note
The compiler reads every import of a file before any other form (`compiler.py:745`, `imports`),
so a name that an import gives may be used above the import. Bead mtp-ydd4.7.12.
:::

:::{admonition} Code differs
:class: note
In the scene and in the body of a motif, the compiler follows this. In a group,
`compiler.py:5166` (`shape_here`) keeps every `exists-when` until all the members are declared, so
`(group g (exists-when c true) (circle|none c))` compiles. Bead mtp-ydd4.7.10 makes it an error.
:::

## What a name refers to

This rule exists so that every compiler resolves each name to the same declaration.

```{rule} name-lookup
A use of a name, and the first {term}`name part` of a {term}`qualified name`, refers to the first of:

1. The declaration or binding of the name in the innermost scope around the use that has the name
   before the use ({numref}`declare-before-use`), or, for an imported name, its declaration in the
   imported file.
2. A built-in function or constant of that name ({doc}`stdlib`).

When neither finds the name, the source is a {term}`compile error`. When the file rand gives a name of
that text ({ref}`stdlib-rand`), the message is "N comes from the standard library: (import rand N)",
and for `rand.N` it is "rand.N comes from the standard library: (import rand)".
```

So a source that calls `(rand-int 1 6)` and imports no `rand-int` is a compile error, "rand-int
comes from the standard library: (import rand rand-int)", since the random functions, `seed` and
`roll-dice` are not built in ({numref}`rand-module`).

So an inner name hides an outer name of the same text inside its scope: a parameter, a `let`
name and a `foreach` name hide a name of the file scope, and an attribute of a record hides a
top-level name inside the record. A declaration in the file scope, and a name that an import
gives, hide a built-in function or constant from that declaration or import on
({numref}`declaration-names`). The name parts of a name after its first are not looked up in any
scope: `p.r` is `(. p 'r')` ({numref}`sugar-rewrites`), where `'r'` is a label and not a name,
and what it chooses is defined in {numref}`dot-name-part`.

In this example, the parameter `x` hides the variable `x` inside `tenfold`, so `(tenfold 2)` is
20 whatever value the slider writes to the variable:

```{mtp-example}
; the parameter x hides the variable x inside tenfold
(real x 1 (>= 0) (<= 4))
(func tenfold ((real x)) (* 10 x))
(readout r f'x = {x:.1f}, (tenfold 2) = {(tenfold 2)}, (tenfold x) = {(tenfold x):.0f}')
(slider change (animation (move x (from 0) (to 4) (duration 0))) (label 'x'))
```

This rule exists so that every name in a scope refers to exactly one thing.

```{rule} one-declaration-per-scope
In one scope, a name is declared, bound or imported at most once, whatever the kinds involved: every
declaration, binding and imported name of a scope shares one set of names. The parameters of one
form, and the names of one `let` or one `foreach`, are also all different. A second one is a
compile error.
```

So `(type unit real (>= 0) (<= 1))` followed by `(real unit 1)` is a compile error, and so is a
shape of the scene that has the name of a top-level function. Since the scene makes no scope, two
shapes in two groups of the scene never have the same name. Two copies of a `foreach` declare
different names, as `@'dot-{k}'` does.

:::{admonition} Code differs
:class: note
The compiler does not check that the names of one `let` are all different (`compiler.py:6670`,
`let`, and `compiler.py:959`, `body_let`), so `(let ((a 1) (a 2)) a)` compiles, and is 2. Bead
mtp-ydd4.7.41.
:::

This rule exists so that a name inside a motif never means something other than the same name at the top level of its file.

```{rule} motif-names-hide-nothing
A shape or a variable declared in the body of a motif may not take a name that its file declares at
the top level, or that an `(import F N…)` gives, before the motif. Such a declaration is a compile
error.
```

So inside a motif's body, a name declared at the top level always means the top-level
declaration, unless a parameter, a `let` name or a `foreach` name hides it. A shape of the scene is
not declared at the top level, so two motifs and the scene may each have a member `c`. A file
imported whole makes only its own name usable ({numref}`import-puts-in`), so a member `ink` does not hide
`house.ink`. The same rule holds for a motif in an imported file, with that file's own top-level names.

## Imports

The file scope of an imported file, and the names that an import gives, are defined in
{doc}`imports`.

## Names that no declaration or binding takes

This rule exists so that a keyword or a built-in type always means the same thing wherever it is written.

```{rule} declaration-names
No declaration or binding, of any kind, may take as its name a {term}`keyword` ({numref}`keywords`), a
{term}`built-in type` ({numref}`the-types`) or an {term}`operator`. It may take the name of any other
built-in function or constant, such as `pi`, and from there on the name refers to what it declares or
binds ({numref}`name-lookup`).
```

So `(real if 1)` and `(circle line …)` are compile errors, and
`(func max ((real a) (real b)) a)` and `(real pi 3)` are allowed. `scene`, `movement`,
`animation` and `func` are both built-in types and keywords. `true`, `false` and `none` are literals,
never names ({numref}`name-characters`). The built-in functions and constants are found only by the
second step of {numref}`name-lookup`. The names of the {term}`standard library` are not built-ins:
they are ordinary declarations of its files ({doc}`stdlib`), which a source brings in with
`import`, and are found as any other imported name.



:::{admonition} Code differs
:class: note
`compiler.py:99` (`RESERVED`) forbids only the names `scene`, `animation`, `transition`, `move`,
`in-order`, `at-once`, `when`, `else`, `true`, `false`, `none`, `const`, `self`, `doc`, `free`, `set`
and `primitive`, so the name `self` is refused everywhere. The special forms of `compiler.py:122` (`SPECIAL`) and the types
are forbidden only as the name of a function (`compiler.py:181`, `NOT_FUNCTION_NAMES`), so a
variable may be named `if`, and a function may not take the name of a constant. A name bound by
`let` is checked against neither (`_Compiler.let`, `compiler.py:6663`). Bead mtp-ydd4.7.35 makes
the compiler follow the rule.
:::
