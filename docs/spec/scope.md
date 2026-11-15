(scope)=
# Names and scope

This page defines the {term}`forms <form>` that declare {term}`names <name>`, the part of a source
in which each name may be used, and the declaration to which each use of a name refers. Which
characters a name holds is defined in {numref}`name-characters`, and which names a declaration may
take in {numref}`keywords` and {numref}`declaration-names`. Which {term}`expressions <expression>`
may read the scene, a formula or the page is defined in {doc}`binding-time`.

The rewrite step resolves every name to its declaration ({numref}`compile-steps`), so a source
that breaks a rule of this page is rejected in the rewrite step. A name that is built from a value,
`(name S)` with `S` reading a `foreach` name or a motif parameter, is resolved in the prove step
instead ({numref}`names-from-values`). This page specifies the language. Where the {term}`compiler`
does not follow a rule yet, a box marked "Code differs" gives what the code does and the bead that
will change it.

## Scopes

```{rule} scopes
A {term}`scope` is a part of a file in which some names may be used. These are the scopes of mtp,
and the names that each one declares:

| Scope | Covers | Declares |
|---|---|---|
| the {term}`file scope` of a source or of a {term}`file to import` | the whole file | every declaration at the top level, every name that an `import` gives ({numref}`import-declares-names`), and every declaration in the scene and in its groups, rows and columns, at any depth |
| the {term}`body` of a motif | the motif's body | the parameters of the motif, and every shape and variable that the body declares, at any depth |
| a function `(func N PARAMS BODY)`, a function `(fn PARAMS BODY)`, a variant and a choreo | the body | the parameters |
| `(let ((N1 V1) … (Nk Vk)) …)`, in an expression or in a body | each value after `Vi`, and the body or the items of the `let` | `N1` to `Nk`, each `Ni` from `V(i+1)` on |
| `foreach` | each source after the source of a name, and the items of the `foreach` | the names that it binds, each from the next source on |
| a namespace or a palette | the items after each member | its members |
| a formula | the items of the formula | its variables, from the item after each, and its terms ({numref}`formula-terms`) |
| the move of an `on-drag` | the move | `pointer` |

The scope of a body is inside the scope of the form around it, and every scope is inside the file
scope. A group, a row, a column and the scene make no scope of their own. The names that the
items of a `let` or of a `foreach` written in a body declare belong to the scope of that body:
only the names that the `let` or the `foreach` binds belong to its own scope.
```

So the shapes of the scene, at any depth in its groups, are names of the file scope: a canvas, a
{term}`listener` and a readout name them. A copy that a `foreach` in the scene makes, such as
`#'dot-{k}'`, is a name of the file scope too, while `k` is used only inside the `foreach`. A
parameter is used only in its body, and so a default of a parameter never reads another parameter.
A member of a namespace, a palette or a formula is used by its bare name only inside that
declaration, and elsewhere through it, as `theme.ink`, by {numref}`dot-name-part`. In the same way,
a member of a motif's body is used from outside the body only through an instance, as `d1.face`.

```{rule} declare-before-use
A use of a name refers only to a declaration that comes before the use, in every scope, imports
included, with no exceptions. The order is the order of the source after the rewrite step, with
each `foreach` read as its copies, in the order of the copy index. A declaration comes before a
use when its form starts before the use. A use of a name inside the form that declares it is
allowed only as {numref}`self-reference-today` allows.
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

## Which declaration a name refers to

```{rule} name-lookup
A use of a bare name, and the first {term}`name part` of a name with several name parts, refers to
the declaration that these steps find, in order:

1. Among the scopes around the use, from the innermost outwards to the file scope, the first that
   declares the name before the use ({numref}`declare-before-use`).
2. A built-in function or a built-in constant of that name ({doc}`stdlib`).

When neither step finds a declaration, the source is a {term}`compile error`.
```

So an inner name hides an outer name of the same text inside its scope: a parameter, a `let`
name and a `foreach` name hide a name of the file scope, and a member of a namespace hides a
top-level name inside the namespace, as the palette member `yellow` of examples/colormaps.mtp does
while the file also imports a color `yellow`. A declaration in the file scope hides a built-in
function or constant from that declaration on ({numref}`declaration-names`). The name parts of a
name after its first are not looked up in any scope: `p.r` is `(. p r)` ({numref}`sugar-rewrites`),
and what `r` is in it is defined in {numref}`dot-name-part`. `pointer` is found only in the move of
an `on-drag`, and is a compile error everywhere else, since no declaration takes it as its name.

In this example, the parameter `x` hides the variable `x` inside `tenfold`, so `(tenfold 2)` is
20 whatever the slider gives the variable:

```{mtp-example}
; the parameter x hides the variable x inside tenfold
(real x 1 (>= 0) (<= 4))
(func tenfold ((real x)) (* 10 x))
(readout r $'x = {x:.1f}, (tenfold 2) = {(tenfold 2)}, (tenfold x) = {(tenfold x):.0f}')
(slider change (move x (from 0) (to 4)) (label 'x'))
```

```{rule} one-declaration-per-scope
In one scope, a name is declared at most once, whatever the kinds of the declarations. A
variable, a shape, a function, a type, an {term}`interface`, a motif, a variant, a choreo, a
{term}`component` and every other declaration share the names of their scope, and so do the names
that imports give. In the same way, the parameters of one form, the names of one `let` and the names
of one `foreach` are all different. A second declaration of a name in the same scope is a compile
error.
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
imported whole gives only its own name ({numref}`sugar-rewrites`), so a member `ink` does not hide
`house.ink`. A motif in an imported file follows the rule against that file's own top-level names.

## Imports

The file scope of an imported file, and the names that an import gives, are defined in
{doc}`imports`.

## The keywords, the built-in names and `self`

No declaration takes a {term}`keyword`, a {term}`built-in type`, `pointer` or `self` as its name
({numref}`keywords`, {numref}`declaration-names`), and `true`, `false` and `none` are values and
never names ({numref}`name-characters`). The built-in functions and constants are found only by
the second step of {numref}`name-lookup`. The names of the standard {term}`library` are ordinary
declarations of its files, which a source brings in with `import`, and are found as any other
imported name.

:::{admonition} Open question Q-scope-1 (parked)
:class: warning
What `self` means, and every rule about a declaration that reads itself or its container, are to
be redesigned around `self` (bead mtp-9b4m). The redesign is parked, and this spec
does not define `self`. Today the compiler reads `self` in the body of a motif as the instance
being built, and gives an error for `self` outside a motif's body (`compiler.py:6036` to
`compiler.py:6043`, `lookup`). The rules of today about a declaration that reads itself are in
{numref}`self-reference-today`.
:::
