(scope)=
# Names and scope

This page defines {term}`declarations <declaration>` and {term}`bindings <binding>`, the part of a
source in which each {term}`name` may be used, and the declaration or binding to which each use of
a name refers. Which characters a name holds is defined in {numref}`name-characters`.
Which {term}`expressions <expression>` may read the scene, a formula or the page is defined in
{doc}`binding-time`.

The rewrite step finds what each name refers to ({numref}`compile-steps`), so a source
that breaks a rule of this page is rejected in the rewrite step. A name that is built from a value,
`(name S)` with `S` reading a `foreach` name or a motif parameter, is resolved in the prove step
instead ({numref}`names-from-values`). This page specifies the language.

## Declarations and bindings

```{rule} declarations-and-bindings
A declaration is a {term}`form` that creates a new thing that can be addressed: an object of the
world model, a function, a type or a choreo. The thing exists whether or not the source gives it a
name, so `(circle_ (r 1))` creates a circle that has no name. A binding gives a name to a value
for a part of a source, and creates nothing: the names of a `let` and of a `foreach`, and the
parameters of a function, a motif, a variant or a choreo, are bindings. The language makes two
bindings of its own: the move of a drag binds `pointer` to the position of the pointer, and the
body of a motif binds `self` to the instance being built. An `import` creates
nothing either: it gives names to the things that the declarations of another file create
({doc}`imports`).
```

So `(real a 1)`, `(circle c (r a))`, `(canvas v s)`, `(func twice ((real x)) (* 2 x))` and
`(type unit real (>= 0) (<= 1))` are declarations, and so is a listener written in a
canvas, such as `(on-click c (move a (to 0) (duration 1)))`, which creates a listener with no name. In
`(let ((k 2)) (circle c (r k)))`, the circle `c` is a declaration and `k` is a binding.

## Scopes

```{rule} scopes
A {term}`scope` is a part of a file in which some names may be used. These are the scopes of mtp,
and the names of each one:

| Scope | Covers | Names |
|---|---|---|
| the {term}`file scope` of a source or of a {term}`file to import` | the whole file | every declaration at the top level, every name that an `import` gives ({numref}`import-declares-names`), and every declaration in the scene and in its groups, rows and columns, at any depth |
| the {term}`body` of a motif | the motif's body | the parameters of the motif, `self`, and every shape and variable declared in the body, at any depth |
| a function `(func N PARAMS BODY)`, a function `(fn PARAMS BODY)`, a variant and a choreo | the body | the parameters |
| `(let ((N1 V1) … (Nk Vk)) …)`, in an expression or in a body | each value after `Vi`, and the body or the items of the `let` | `N1` to `Nk`, each `Ni` from `V(i+1)` on |
| `foreach` | each source after the source of a name, and the items of the `foreach` | the names that it binds, each from the next source on |
| a namespace or a palette | the items after each member | its members |
| a formula | the items of the formula | its variables, from the item after each, and its terms ({numref}`formula-terms`) |
| the move of an `on-drag` | the move | `pointer` |

The scope of a body is inside the scope of the form around it, and every scope is inside the file
scope. A group, a row, a column and the scene make no scope of their own. The names that are
declared in the items of a `let` or of a `foreach` written in a body belong to the scope of that
body: only the names that the `let` or the `foreach` binds belong to its own scope.
```

So the shapes of the scene, at any depth in its groups, are names of the file scope: a canvas, a
{term}`listener` and a readout name them. A copy that a `foreach` in the scene makes, such as
`#'dot-{k}'`, is a name of the file scope too, while `k` is used only inside the `foreach`. A
parameter is used only in its body, and so a default of a parameter never reads another parameter.
A member of a namespace, a palette or a formula is used by its bare name only inside that
declaration, and elsewhere through it, as `theme.ink`, by {numref}`dot-name-part`. In the same way,
a member of a motif's body is used from outside the body only through an instance, as `d1.face`.

```{rule} declare-before-use
A use of a name refers only to a declaration or a binding that comes before the use, in every
scope, with no exceptions, and a name that an import gives is used only after the import. The
order is the order of the source after the rewrite step, with each `foreach` read as its copies, in
the order of the copy index. A declaration, a binding or an import comes before a use when its
form starts before the use. A use of a name inside the form that declares or binds it is allowed
only as {numref}`self-reference-today` allows.
```

So two functions never call each other, since one of them would name the other before its
declaration, and a function calls itself only by {numref}`self-reference-today`. A canvas comes
after the scene that it draws, a {term}`control` comes after the {term}`views <view>` that its
`(in …)` names, and an `exists-when` comes after the shape that it names. Copy k of a `foreach` may
name copy k - 1, which comes before it, and never copy k + 1. By {numref}`import-declares-names`, a
name that an import gives is used only after the import.

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

```{rule} name-lookup
A use of a bare name, and the first {term}`name part` of a name with several name parts, refers to
what these steps find, in order:

1. Among the scopes around the use, from the innermost outwards to the file scope, the first that
   has the name among its names before the use ({numref}`declare-before-use`). The use refers to
   the declaration or the binding of the name in that scope, or, for a name that an import gives,
   to the declaration in the imported file.
2. A built-in function or a built-in constant of that name ({doc}`stdlib`).

When neither step finds the name, the source is a {term}`compile error`. When the file rand of the
standard library gives a name of that text ({ref}`stdlib-rand`), the message is "N comes from the
standard library: (import rand N)", with `N` the name. When the name is `rand` and has a second
name part `N` that the file rand gives, the message is "rand.N comes from the standard library:
(import rand)".
```

So a source that calls `(rand-int 1 6)` and imports no `rand-int` is a compile error, "rand-int
comes from the standard library: (import rand rand-int)", since the random functions, `seed` and
`roll-dice` are not built in ({numref}`primitive-form`).

So an inner name hides an outer name of the same text inside its scope: a parameter, a `let`
name and a `foreach` name hide a name of the file scope, and a member of a namespace hides a
top-level name inside the namespace. A declaration in the file scope, and a name that an import
gives, hide a built-in function or constant from that declaration or import on
({numref}`declaration-names`). The name parts of a name after its first are not looked up in any
scope: `p.r` is `(. p r)` ({numref}`sugar-rewrites`),
and what `r` is in it is defined in {numref}`dot-name-part`. `pointer` is found only in the move of
an `on-drag`, and is a compile error everywhere else, since no declaration and no binding takes
it as its name.

In this example, the parameter `x` hides the variable `x` inside `tenfold`, so `(tenfold 2)` is
20 whatever the slider gives the variable:

```{mtp-example}
; the parameter x hides the variable x inside tenfold
(real x 1 (>= 0) (<= 4))
(func tenfold ((real x)) (* 10 x))
(readout r f'x = {x:.1f}, (tenfold 2) = {(tenfold 2)}, (tenfold x) = {(tenfold x):.0f}')
(slider change (move x (from 0) (to 4)) (label 'x'))
```

```{rule} one-declaration-per-scope
In one scope, a name is declared or bound at most once, whatever the kinds of the declarations
and the bindings. A variable, a shape, a function, a type, an {term}`interface`, a motif, a
variant, a choreo, a {term}`component` and every other declaration share the names of their
scope, and so do the bindings and the names that imports give. In the same way, the parameters of
one form, the names of one `let` and the names of one `foreach` are all different. A second
declaration, binding or import of a name in the same scope is a compile error.
```

So `(type unit real (>= 0) (<= 1))` followed by `(real unit 1)` is a compile error, and so is a
shape of the scene that has the name of a top-level function. Since the scene makes no scope, two
shapes in two groups of the scene never have the same name. Two copies of a `foreach` declare
different names, as `#'dot-{k}'` does.

:::{admonition} Code differs
:class: note
The compiler does not check that the names of one `let` are all different (`compiler.py:6670`,
`let`, and `compiler.py:959`, `body_let`), so `(let ((a 1) (a 2)) a)` compiles, and is 2. Bead
mtp-ydd4.7.41.
:::

```{rule} motif-names-hide-nothing
A shape or a variable declared in the body of a motif never takes a name that the file declares at
its top level, or that an `(import F N…)` gives, before the motif. Such a declaration is a compile
error.
```

So inside a motif's body, a name declared at the top level always means the top-level
declaration, unless a parameter, a `let` name or a `foreach` name hides it. A shape of the scene is
not declared at the top level, so two motifs and the scene may each have a member `c`. A file
imported whole gives only its own name ({numref}`import-puts-in`), so a member `ink` does not hide
`house.ink`. A motif in an imported file follows the rule against that file's own top-level names.

## Imports

The file scope of an imported file, and the names that an import gives, are defined in
{doc}`imports`.

## Names that no declaration or binding takes

```{rule} declaration-names
No declaration and no binding takes as its name a {term}`keyword` ({numref}`keywords`) or a
{term}`built-in type`. This holds for every kind of declaration and binding: a variable, a shape, a
function, a parameter, a name of a `let` or a `foreach`, a member of a namespace, a palette or a
formula, a motif, a font, and every other. The built-in types are `int`, `ratio`, `real`,
`complex`, `bool`, `string`, `color`, `font`, `point`, `transform`, `transition`, `animation`,
`scene`, `func`, `rand-seed`, `list`, the shape types, and the
interfaces `shape`, `positioned`, `sequence` and `palette`. Nor does it take the name of an
{term}`operator`. A declaration or a binding may take the name of any other built-in function, or
of a built-in constant (`pi`, `tau` and `euler`): from that declaration or binding on, the name refers to what it declares or binds
({numref}`name-lookup`).
```

So `(real if 1)` and `(circle line …)` are compile errors, and
`(func max ((real a) (real b)) a)` and `(real pi 3)` are allowed. `scene`, `transition`,
`animation` and `func` are both built-in types and keywords. `true`, `false` and `none` are values,
never names ({numref}`name-characters`). The built-in functions and constants are found only by the
second step of {numref}`name-lookup`. The names of the {term}`standard library` are not built-ins:
they are ordinary declarations of its files ({doc}`stdlib`), which a source brings in with
`import`, and are found as any other imported name.

A variable may be named `pointer` or `self`. Inside the move of a drag, the binding `pointer` hides
a declaration named `pointer`, and inside the body of a motif, the binding `self` hides a
declaration named `self` ({numref}`name-lookup`). A member of a motif's body named `self` is a
compile error by {numref}`one-declaration-per-scope`, since the body binds `self`.

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

:::{admonition} Open question Q-scope-1 (parked)
:class: warning
Every rule about a declaration that reads itself or its container is to be redesigned around
`self`, so that a declaration, a shape for example, refers to itself through `self`. Today `self`
is bound only in the body of a motif ({numref}`declarations-and-bindings`). The redesign is parked,
and the rules of today about a declaration that reads itself are in
{numref}`self-reference-today`.
:::
