(core-inventory)=
# Inventory of heads

This page lists every head of mtp, by the context where it is written. Each table lists the heads of one context. The column "Defined in" gives the page where a core
form's meaning is defined, the rule for a syntactic sugar form, or {doc}`stdlib` for a built-in.

(top-level-heads)=
## Top-level forms

The top level of a source holds only the heads of these tables, with at most one `scene`.

**Declarations of types**

| Head | Kind | Defined in |
|---|---|---|
| `type` | core | {numref}`type-notation` |
| `interface` | core | {doc}`types` |
| `motif` | core | {doc}`world-model` |
| `variant` | core | {doc}`types` |
| `animation` | core | {doc}`time` |

**Declarations of objects**

| Head | Kind | Defined in |
|---|---|---|
| `scene` | core | {doc}`world-model` |
| `formula` | core | {doc}`world-model` |
| `record` | core | {doc}`world-model` |
| `font` | core | {doc}`data-model` |
| `palette` | syntactic sugar | {numref}`sugar-rewrites` |
| `parametric` | syntactic sugar | {numref}`sugar-rewrites` |
| `movement` | core | {doc}`time` |

**Declarations of components**

| Head | Kind | Defined in |
|---|---|---|
| `canvas` | core | {doc}`page-interface`, {doc}`lifecycle` |
| `readout` | core | {doc}`page-interface` |
| `display` | core | {doc}`page-interface` |
| `slider` | core | {doc}`page-interface`, {doc}`reaction` |
| `button` | core | {doc}`page-interface`, {doc}`reaction` |
| `play` | core | {doc}`page-interface`, {doc}`time` |
| `stepper` | core | {doc}`page-interface`, {doc}`time` |
| `toggle` | core | {doc}`page-interface`, {doc}`reaction` |

The listeners are declared in the body of a view, not at the top level ({numref}`listeners-in-views`).

**Declarations of functions**

| Head | Kind | Defined in |
|---|---|---|
| `func`, `func[T]` | core | {doc}`types`, {doc}`evaluation` |
| `colormap` | core | {doc}`evaluation` |

**Declarations of variables**

| Head | Kind | Defined in |
|---|---|---|
| `(T N …)` for a type `T` | core | {doc}`data-model`, {doc}`reaction` |
| `var` | core | {doc}`data-model` |

**Forms around declarations**

| Head | Kind | Defined in |
|---|---|---|
| `import` | core | {doc}`imports` |
| `let` | core | {doc}`binding-time` |
| `foreach` | core | {doc}`binding-time` |
| `doc` | core | {doc}`compiled-format` |

So a source need not hold a scene: `(real a 1) (readout r f'{a}')` is a world model with a
variable and a readout, and an empty file is a world model with nothing in it. A source with two
scenes is an error.

:::{admonition} Code differs
:class: note
The error for a second scene is "a file has exactly one scene" (`compiler.py:4854`). Bead
mtp-ydd4.7.59.
:::

## Variables and conditions

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `(T N VALUE C…)` | core | a variable declaration | {numref}`variables`, {doc}`reaction` |
| `free` | core | an expression | {doc}`reaction`, {doc}`binding-time` |
| `>=`, `>`, `<=`, `<` with one number | core | conditions | {doc}`types` |
| `length` | core | a condition | {doc}`types` |
| `one-of` | core | a condition | {doc}`types` |
| `const` | core | a named argument of a variable or an attribute | {numref}`variables` |

## Type notation

| Notation | Kind | What it is | Defined in |
|---|---|---|---|
| `int`, `ratio`, `real`, `complex`, `unit`, `ease`, `curve`, `bool`, `string`, `color`, `font`, `point`, `transform`, `movement`, `none`, `scene` | core | the {term}`built-in types <built-in type>` | {doc}`types` |
| `circle` and the other shape names | core | the shape types | {doc}`types` |
| `shape`, `positioned`, `sequence`, `sequence[T]` | core | built-in types and {term}`interfaces <interface>` | {doc}`types` |
| `list[T]` | core | a list type | {doc}`types` |
| `func[P… R]` | core | a function type | {doc}`types` |
| `T\|none` | core | a union with `none` | {doc}`types` |
| `(T C…)` | core | a refined type | {doc}`types` |
| `colormap` | core | a type | {numref}`the-types` |
| a name declared by `type` | core | the type that it names | {numref}`type-notation` |
| a name declared by `interface`, `motif` or `variant` | core | that type | {doc}`types` |
| `rand-seed` | core | a type | {doc}`types`, {doc}`evaluation` |
| `list` with no item type | core | a type | {doc}`types` |
| `mod` | core | a type | {numref}`modular-types` |

## The scene, shapes and collections

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `background` | core | a named argument of the scene | {doc}`world-model` |
| `transform` in the scene | core | a named argument of the scene | {doc}`world-model` |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `bezier`, `arc`, `ring`, `text` | core | shape declarations | {doc}`world-model` |
| `group` | core | a group declaration | {doc}`world-model` |
| `row`, `column` | core | group declarations | {doc}`world-model` |
| `(M N …)` for a motif `M` | core | a declaration of a shape whose type is the motif | {doc}`world-model` |
| `(V N …)` for a variant `V` | core | a declaration of an object whose type is the variant | {doc}`world-model` |
| `(H\|none N …)` for a shape head `H` | core | a declaration of a shape that may be `none` | {doc}`world-model` |
| `exists-when` | core | a body item | {doc}`world-model` |
| `let` in a body | core | a let | {doc}`binding-time` |
| `foreach` in a body | core | a foreach | {doc}`binding-time` |
| a variable in the scene | core | a variable declaration | {doc}`world-model` |

## Arguments of shapes and collections

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `x`, `y`, `translate`, `transform`, `fill`, `stroke`, `stroke-width`, `opacity`, `fill-opacity`, `stroke-opacity`, `line-cap`, `line-join`, `drawn`, `pointer-events` on a shape, `r`, `width`, `height`, `rx`, `ry`, `from`, `to`, `a`, `b`, `c`, `points`, `controls`, `head-start`, `head-end`, `head-size`, `value`, `halign`, `valign`, `font` | core | named arguments of a shape | {doc}`world-model` |
| `pos` | syntactic sugar | a named argument | {numref}`sugar-rewrites` |
| `dash` | core | a named argument | {doc}`world-model` |
| `like` | syntactic sugar | a named argument | {numref}`like-copies` |
| `defaults` on a group, a row or a column | core | a named argument | {numref}`collection-defaults` |
| `clip` | core | a named argument | {doc}`world-model` |
| `fixed-size` | core | a named argument | {doc}`world-model` |
| `gap`, `align` | core | named arguments of a row or a column | {doc}`world-model` |

## Motifs and variants

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a parameter `(T N DEFAULT?)` | core | a parameter | {doc}`types` |
| a shape, a bound or const variable, `foreach`, `let` or `exists-when` in a motif's body | core | body items of a motif | {doc}`world-model` |
| `self` | core | a name | {doc}`scope` |
| a parameter given to an instance, `(P X)` | core | a named argument of a shape of a motif type | {doc}`world-model` |
| `x`, `y`, `translate`, `transform` on an instance | core | named arguments of a shape of a motif type | {doc}`world-model` |
| `pos` on an instance | syntactic sugar | a named argument | {numref}`sugar-rewrites` |
| `clip` on an instance | core | a named argument | {doc}`world-model` |
| `defaults` on an instance | core | a named argument | {doc}`world-model` |
| `like` on an instance or a variant instance | syntactic sugar | a named argument | {numref}`like-copies` |

The rules about a declaration that reads itself or its collection, such as a default that reads
its own group, are to be redesigned around `self`. Until then, the rules of today hold
({numref}`self-reference-today`).

## Records, palettes and interfaces

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a variable in a record | core | a body item | {doc}`world-model` |
| `record`, `palette` in a record | core, syntactic sugar | a body item | {doc}`world-model`, {numref}`sugar-rewrites` |
| `(M C)` in a palette | syntactic sugar | a body item | {numref}`sugar-rewrites` |
| `(T A C…)` in an interface | core | a body item | {doc}`types` |
| `family`, `style`, `weight`, `size` | core | named arguments of a font | {doc}`data-model` |
| `like` in a font | syntactic sugar | a named argument of a font | {numref}`like-copies` |

## Formulas and terms

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a string known when compiling | core | the positional argument of a formula | {doc}`world-model` |
| `term` | core | a body item of a formula | {doc}`world-model` |
| `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding` in a term | core | named arguments of a term | {doc}`world-model` |
| a string in a term | core | the positional argument of a term | {doc}`world-model` |
| `like` in a term | syntactic sugar | a named argument | {numref}`like-copies` |
| `defaults` in a formula | core | a named argument | {numref}`formula-defaults` |
| `exists-when` in a formula | core | a body item | {doc}`world-model` |
| a variable in a formula | core | a body item | {doc}`world-model` |

## Special forms and other expressions

The heads of this table that are written as {term}`words <word>`, from `.` to `type-of`, are
{term}`keywords <keyword>` ({numref}`keywords`).

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a literal | core | an expression | {doc}`lexical`, {doc}`types` |
| a name | core | an expression | {doc}`scope` |
| a name with several name parts, `N.A`, `N[X]` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| `.` | core | an expression | {numref}`dot-name-part` |
| `name` | core | an expression | {doc}`scope`, {numref}`names-from-values` |
| `if` | core | an expression | {doc}`evaluation` |
| `when` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| `cond`, `and`, `or` | syntactic sugar | expressions | {numref}`sugar-rewrites` |
| `else` | syntactic sugar | a clause of `cond` | {numref}`sugar-rewrites` |
| `let` | core | an expression | {doc}`scope`, {doc}`evaluation` |
| `fn` | core | an expression | {doc}`types`, {doc}`evaluation` |
| `as` | core | an expression | {doc}`types` |
| `type-of` | core | an expression | {doc}`types` |
| `concat` | core | an expression | {doc}`evaluation` |
| `fmt` | core | an expression | {doc}`evaluation` |
| `free` | core | an expression | {doc}`reaction` |
| `(F A…)` for a declared function `F` | core | an expression | {doc}`evaluation` |
| `(L A…)` for a local function value `L` | core | an expression | {doc}`evaluation` |

## Built-in functions and the standard library

These heads name built-in functions, except the random functions, which the file rand gives. Each call is a core call ({numref}`built-ins`).

| Heads | What they are |
|---|---|
| `+`, `-`, `*`, `/`, `^`, `mod`, `=`, `!=`, `<`, `<=`, `>`, `>=` | the operators |
| `not`, `abs`, `or?`, `none?`, `some?`, `somes` | logic, absolute value and `none` |
| `sqrt`, `sign`, `floor`, `ceil`, `exp` | numbers |
| `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, `sind`, `cosd`, `tand`, `secd`, `cscd`, `cotd`, `asin`, `acos`, `atan`, `acot`, `asec`, `acsc`, `asind`, `acosd`, `atand`, `acotd`, `asecd`, `acscd`, `rad`, `turn`, `deg`, `to-rad`, `to-turn` | angles |
| `polar`, `to-polar`, `dist` | points |
| `rotate`, `translate`, `scale`, `transform` | transforms |
| `mix`, `lighten`, `darken`, `light-dark` | colors |
| `round`, `log`, `min`, `max`, `lerp` | with a varying number or type of arguments |
| `range` | `(range LO HI (gap G))`: the numbers from `LO`, `G` apart, up to `HI` and not including it. `G` is 1 when the range gives neither `gap` nor `num`. `(range LO HI (num N))`: `N` numbers evenly apart, from `LO` to `HI`, both included. `gap` and `num` are {term}`named arguments <named argument>` of `range` |
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | random values and seeds, which a source names only through the file rand of the standard library ({numref}`rand-module`). `rand`, `rand-int`, `pick` and `shuffle` take the named argument `(seed S)`, and follow the {term}`default seed` of the file that holds them when it is left out ({numref}`default-seed`) |
| `steps` | an ease: `(steps N (at P))` gives the ease of N equal jumps, each at the fraction P of its interval, so jump k comes at (k − 1 + P)/N. P is from 0 to 1 and known when compiling, and is 1 when `(at …)` is left out. So `(steps 1 (at P))` is 0 before P and 1 from P on |
| `map`, `where`, `sort`, `reverse`, `reduce`, `sum`, `count`, `any`, `all` | lists |
| `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right` | points on a shape's box |
| `pi`, `tau`, `euler` | constants |
| the files `colors`, `eases`, `fonts`, `marks`, `math`, `rand` | the standard library: files written in mtp, and the file `rand`, which the compiler gives ({ref}`stdlib-rand`) |

:::{admonition} Code differs
:class: note
The compiler accepts `(range n)` as `(range 0 n (gap 1))`, and rejects a `range` that gives
neither `gap` nor `num`, such as `(range 0 n)`, with "range is (range n), (range start stop (gap g))
or (range start stop (num n))". Bead mtp-z8i1 makes the compiler follow the rule.
:::

A call of `steps` gives an ease, which is a function, so `steps` is a built-in function and not a
keyword. By {numref}`declaration-names`, a declaration or a binding named `steps` takes the place
of the built-in function from that declaration or binding on.

:::{admonition} Code differs
:class: note
The compiler has `(step N)`, whose jumps come at the start of each interval, and `(step-ease P)`,
with one jump at P, in place of `steps` (compiler.py:3092-3107, web/src/transitions.ts:22). It reads
them only as the whole value of an `ease`, and not as calls. So after `(real step 3)`,
`(ease (step 2))` still compiles as the ease of two jumps, and `(step 2)` in any other place is the
error "unknown function". Beads mtp-ydd4.7.40 and mtp-6a4r make the compiler follow the rule.
:::

## Movements

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `move` | core | an expression | {doc}`time` |
| `from`, `to`, `duration`, `path` | core | named arguments of a movement | {doc}`time` |
| `ease` | core | a named argument of a movement | {doc}`time` |
| `like` in a movement or a move | syntactic sugar | a named argument | {numref}`like-copies` |
| an animation's body of several items | syntactic sugar | the body of an animation | {numref}`sugar-rewrites` |
| `defaults` in a score | core | a named argument | {doc}`time` |
| `loop` | core | a named argument of a score | {doc}`time` |
| `score` | core | an expression | {doc}`time` |
| `lag` | core | a named argument of a movement | {doc}`time` |
| `in-order`, `at-once` | syntactic sugar | expressions | {numref}`sugar-rewrites` |
| `foreach` in a score | core | a body item | {doc}`time`, {doc}`binding-time` |
| the name of a movement, or of an animation with no parameters, in a score | core | a body item | {doc}`time` |
| `wait` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| `jump` | syntactic sugar | an expression | {numref}`sugar-rewrites` |
| a use of an animation | core | an expression | {doc}`time`, {numref}`animation-step` |

## Components and their items

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `canvas`, `readout`, `display` | core | view declarations | {doc}`page-interface`, {doc}`lifecycle` |
| `slider`, `button`, `play`, `stepper`, `toggle` | core | control declarations | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove` | core | listeners | {doc}`reaction`, {doc}`concurrency` |
| `on-show`, `on-hide` | core | listeners that play while a canvas starts or stops drawing a shape | {doc}`reaction`, {doc}`lifecycle` |
| `on-view`, `on-ready`, `on-live`, `on-quiet` | core | listeners on their own view | {doc}`lifecycle` |
| `x`, `y`, `width`, `height`, `transform`, `pan`, `zoom` on a canvas | core | named arguments of a canvas | {doc}`page-interface` |
| `toggle-duration`, `toggle-ease` | core | named arguments of a canvas | {doc}`time`, {doc}`page-interface` |
| a name, a list literal or an expression in a canvas | core | body items of a canvas | {doc}`page-interface` |
| `font` on a readout | core | a named argument of a readout | {doc}`page-interface` |
| `kind` on a display | core | a named argument of a display | {doc}`page-interface` |
| a movement on a control or a listener | core | a positional argument of a writer | {doc}`reaction`, {doc}`time` |
| the move of a slider | core | the positional argument of a slider | {doc}`page-interface`, {doc}`reaction` |
| the target of `toggle`, `on-pointermove` | core | a positional argument | {doc}`reaction` |
| the target of `on-drag` written as a move | core | the positional argument of an `on-drag` | {doc}`reaction`, {numref}`drag-group-shift` |
| the target of `on-drag` written as a name | syntactic sugar | the positional argument of an `on-drag` | {numref}`sugar-rewrites` |
| `label` | core | a named argument of a control | {doc}`page-interface`, {doc}`accessibility` |
| `stops` on a slider | core | a named argument of a slider | {doc}`page-interface` |
| `buttons`, `rest`, `labels` on a play | core | named arguments of a play | {doc}`page-interface`, {doc}`time` |
| `selected` on a button | core | a named argument of a button | {doc}`page-interface`, {doc}`accessibility` |
| `active` | core | a named argument of a writer | {doc}`reaction` |
| `priority` | core | a named argument of a writer | {doc}`concurrency` |
| `stop-propagation` | core | a named argument of a listener | {doc}`reaction` |
| `in` | core | a named argument of a control | {doc}`page-interface`, {doc}`lifecycle` |
| a guard | core | a body item of a writer | {doc}`reaction` |
| `doc` on a component | core | its docstring | {doc}`compiled-format` |

:::{admonition} Code differs
:class: note
The compiler shows a label written `(label $'…')` as typeset LaTeX, and any other label as plain
text, so the spelling of a string changes its meaning. Bead mtp-z8x5 makes the compiler follow the rule.
:::

:::{admonition} Code differs
:class: note
A canvas without `(zoom …)` zooms from 1 to 10 times, `(zoom B)` turns zooming on or off, and a
canvas without `(pan …)` pans (compiler.py:3790-3815, 4386-4391). Bead mtp-ff0r makes the compiler
follow the rule.
:::

## Bodies

:::{table} The bodies of mtp ({numref}`contexts`). A head that the table does not list has no body. "let, foreach" says whether the body may hold a `let` and a `foreach` ({numref}`body-let-foreach`).
:name: bodies-table

| Head | Its body | let, foreach |
|---|---|---|
| the top level of a source | the heads of {ref}`top-level-heads` | yes |
| the top level of a {term}`file to import` | the forms of {numref}`import-file-holds` | yes |
| `import` | the names to import, or none to import the whole file | no |
| `scene` | shapes, variables, `exists-when` | yes |
| `group`, `row`, `column` | shapes, `exists-when` | yes |
| `motif` | shapes, variables that are bound or const (never free: free state of each shape is a parameter, which becomes an attribute), `exists-when` | yes |
| `formula` | terms, `exists-when` and variables. The string is its positional argument ({numref}`formula-terms`) | yes |
| `record` | variables, records, palettes | yes |
| `palette` | items `(member color)` | yes |
| `interface` | items `(T attribute constraint…)` | yes |
| `type`, a variable `(T name …)` | {term}`conditions <condition>`, such as `(>= 0)` | yes |
| `animation`, `score`, `in-order`, `at-once` | movements: `move`, `jump`, `wait`, a score, the name of a movement, a use of an animation | yes |
| `defaults` | items `(attribute value)`, and in a score, `(duration …)`, `(ease …)` and `(lag …)` | yes |
| `canvas` | at least one thing to draw: a name of a shape or of the scene, a list literal, or an expression that gives a shape, `none` or a list of shapes, such as `(when c d)`. Listeners ({numref}`listeners-in-views`) | yes |
| `readout`, `display` | listeners ({numref}`listeners-in-views`) | yes |
| a control, a listener | guards, such as `(>= k 0)` | yes |
| `let`, `foreach` | items of the kinds that the body around them holds | yes |
| `in` | the views that a control belongs to | no |
| `labels` | strings | no |
| `transform` | transforms, such as `(rotate 90)` | no |
| a call that takes any number of arguments, such as `(+ a b c)` | its arguments | no |
:::

So `(canvas v)` is an error, because a canvas holds at least one thing to draw, and `(canvas v s)`
and `(canvas v c)` are allowed.

:::{admonition} Code differs
:class: note
`(canvas v)` compiles, to a canvas that draws nothing. Bead mtp-ydd4.7.59.
:::

## Heads that are errors

These heads were once part of the language, or belong in another context. No body holds them, so
each is a compile error ({numref}`contexts`). The compiler gives a message about what to write in
their place. They are not forms of the language.

| Head | Where | The message, in short |
|---|---|---|
| `step` | in a score | use `(labels …)` and `(in-order …)` |
| `autoplay` | on a control | use a canvas's `(on-ready …)` |
| `exclusive` | on a writer | use `(priority n)` |
| `when` | on a control or a listener | use `(active bool)` |
| `value` | on a toggle | give the bool its start where it is declared |
| `buttons` | on a stepper | a stepper stops after each step |
| `dash-offset` | as an item | write `(dash [4 2] 1)` |
| `move` | in a canvas | a canvas takes no move |
| `term` | at the top level | a term is given inside its formula |
| `pointer-events` | on a group, a row, a column or an instance | write `(defaults (pointer-events B))` |

:::{admonition} Code differs
:class: note
The compiler accepts `(pointer-events B)` on a group, a row, a column or an instance as a default
for its members (compiler.py:4895-4941, 5395-5443). Bead mtp-327t makes it a compile error.
:::
