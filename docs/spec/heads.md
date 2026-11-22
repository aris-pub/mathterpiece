(core-inventory)=
# Inventory of heads

This page lists every head of mtp, by the context where it is written. Each table lists the heads of one context. The column "Defined in" gives the page where a core
form's meaning is defined, the rule for a syntactic sugar form, or {doc}`stdlib` for a built-in.

(top-level-heads)=
## Top-level forms

The top level of a source holds only forms whose heads are in these tables, with at most one `scene`.

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

**Imports, `let`, `foreach` and `doc`**

| Head | Kind | Defined in |
|---|---|---|
| `import` | core | {doc}`imports` |
| `let` | core | {doc}`binding-time` |
| `foreach` | core | {doc}`binding-time` |
| `doc` | core | {numref}`docstrings` |

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
| `(T N VALUE C…)` | core | a declaration | {numref}`variables`, {doc}`reaction` |
| `free` | core | a compound | {doc}`reaction`, {doc}`binding-time` |
| `>=`, `>`, `<=`, `<` with one number | core | a clause | {doc}`types` |
| `length` | core | a clause | {doc}`types` |
| `one-of` | core | a clause | {doc}`types` |
| `const` | core | a clause | {numref}`variables` |

## Type notation

| Notation | Kind | What it is | Defined in |
|---|---|---|---|
| `int`, `ratio`, `real`, `complex`, `unit`, `ease`, `curve`, `bool`, `string`, `color`, `point`, `movement`, `none`, `scene` | core | the {term}`built-in types <built-in type>` | {doc}`types` |
| `circle` and the other shape names | core | the shape types | {doc}`types` |
| `shape`, `positioned`, `sequence`: the built-in types and {term}`interfaces <interface>` | core | a name | {doc}`types` |
| `list[T]`, `sequence[T]`, `func[P… R]` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `T1\|T2…`, such as `T\|none` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `T1&T2…`, such as `shape&round` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `type-apply`, `type-union`, `type-intersect` | core | a compound | {numref}`type-forms` |
| `(T C…)`, a refined type | core | a compound | {doc}`types` |
| `colormap` | core | a type | {numref}`the-types` |
| a name declared by `type` | core | the type that it names | {numref}`type-notation` |
| a name declared by `interface`, `motif` or `variant` | core | that type | {doc}`types` |
| `rand-seed` | core | a type | {doc}`types`, {doc}`evaluation` |
| `list` with no item type | core | a type | {doc}`types` |
| `(mod T LO HI)` | core | a compound | {numref}`modular-types` |

## The scene, shapes and collections

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `background` | core | a clause | {doc}`world-model` |
| `shift`, `shift-x`, `shift-y`, `rotate`, `scale-x`, `scale-y` in the scene | core | a clause | {doc}`world-model` |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `bezier`, `arc`, `ring`, `text` | core | a declaration | {doc}`world-model` |
| `group` | core | a declaration | {doc}`world-model` |
| `row`, `column` | core | a declaration | {doc}`world-model` |
| `(M N …)` for a motif `M` | core | a declaration | {doc}`world-model` |
| `(V N …)` for a variant `V` | core | a declaration | {doc}`world-model` |
| `(H\|none N …)` for a shape head `H` | core | a declaration | {doc}`world-model` |
| `exists-when` | core | a clause | {doc}`world-model` |
| `let` in a body | core | a special form | {doc}`binding-time` |
| `foreach` in a body | core | a special form | {doc}`binding-time` |
| a variable in the scene | core | a declaration | {doc}`world-model` |

## Arguments of shapes and collections

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `x`, `y`, `shift`, `shift-x`, `shift-y`, `rotate`, `scale-x`, `scale-y`, `fill`, `stroke`, `stroke-width`, `opacity`, `fill-opacity`, `stroke-opacity`, `line-cap`, `line-join`, `drawn`, `pointer-events` on a shape, `r`, `width`, `height`, `rx`, `ry`, `from`, `to`, `a`, `b`, `c`, `points`, `controls`, `head-start`, `head-end`, `head-size`, `value`, `halign`, `valign`, `face` | core | a clause | {doc}`world-model` |
| `pos` | syntactic sugar | a clause | {numref}`sugar-rewrites` |
| `dash` | core | a clause | {doc}`world-model` |
| `like` | syntactic sugar | a clause | {numref}`like-copies` |
| `defaults` on a group, a row or a column | core | a clause | {numref}`collection-defaults` |
| `clip` | core | a clause | {doc}`world-model` |
| `fixed-size` | core | a clause | {doc}`world-model` |
| `gap`, `align` | core | a clause | {doc}`world-model` |

## Motifs and variants

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a parameter `(T N DEFAULT?)` | core | a clause | {doc}`types` |
| a shape or a bound or const variable in a motif's body | core | a declaration |
| `foreach` or `let` in a motif's body | core | a special form | {doc}`world-model` |
| `exists-when` in a motif's body | core | a clause | {doc}`world-model` |
| `as` in a motif | core | a clause | {doc}`scope` |
| a parameter given to an `M`, for a motif `M`, `(P X)` | core | a clause | {doc}`world-model` |
| `x`, `y`, `shift`, `shift-x`, `shift-y`, `rotate`, `scale-x`, `scale-y` on an `M` | core | a clause | {doc}`world-model` |
| `pos` on an `M` | syntactic sugar | a clause | {numref}`sugar-rewrites` |
| `clip` on an `M` | core | a clause | {doc}`world-model` |
| `defaults` on an `M` | core | a clause | {doc}`world-model` |
| `like` on an `M` or on a `V`, for a variant `V` | syntactic sugar | a clause | {numref}`like-copies` |

The rules about a declaration that reads itself or its collection, such as a default that reads
its own group, are {numref}`self-reference-today` and {numref}`no-dependency-cycles`.

## Records, palettes and interfaces

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a variable in a record | core | a declaration | {doc}`world-model` |
| `record`, `palette` in a record | core, syntactic sugar | a declaration | {doc}`world-model`, {numref}`sugar-rewrites` |
| `(M C)` in a palette | syntactic sugar | a declaration | {numref}`sugar-rewrites` |
| `(T A C…)` in an interface | core | a clause | {doc}`types` |
| `family`, `style`, `weight`, `size` | core | a clause | {doc}`data-model` |
| `like` in a font | syntactic sugar | a clause | {numref}`like-copies` |

## Formulas and terms

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a string known when compiling | core | the positional argument of a formula | {doc}`world-model` |
| `term` | core | a declaration | {doc}`world-model` |
| `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding` in a term | core | a clause | {doc}`world-model` |
| a string in a term | core | the positional argument of a term | {doc}`world-model` |
| `like` in a term | syntactic sugar | a clause | {numref}`like-copies` |
| `defaults` in a formula | core | a clause | {numref}`formula-defaults` |
| `exists-when` in a formula | core | a clause | {doc}`world-model` |
| a variable in a formula | core | a declaration | {doc}`world-model` |

## Literals, names and compounds

The heads of this table that are written as {term}`words <word>`, from `.` to `type-of`, are
{term}`keywords <keyword>` ({numref}`keywords`).

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| a literal | core | an expression | {doc}`lexical`, {doc}`types` |
| a name | core | an expression | {doc}`scope` |
| a name with several name parts, `N.A`, `N[X]` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `.` | core | a compound | {numref}`dot-name-part` |
| `name` | core | a compound | {doc}`scope`, {numref}`names-from-values` |
| `if` | core | a compound | {doc}`evaluation` |
| `when` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `cond`, `and`, `or` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `else` | syntactic sugar | a clause | {numref}`sugar-rewrites` |
| `let` | core | a compound | {doc}`scope`, {doc}`evaluation` |
| `fn` | core | a compound | {doc}`types`, {doc}`evaluation` |
| `rec` | core | a compound | {numref}`records` |
| `list-of` | core | a compound | {numref}`values` |
| `color-of` | core | a compound | {numref}`color-literals` |
| a color string `#'…'` | syntactic sugar | a compound | {numref}`parser-sugar` |
| a list `{X…}` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `point-of` | core | a compound | {numref}`values` |
| a point `[X Y]` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `as` | core | a compound | {doc}`types` |
| `type-of` | core | a compound | {doc}`types` |
| `concat` | core | a compound | {doc}`evaluation` |
| `fmt` | core | a compound | {doc}`evaluation` |
| `free` | core | a compound | {doc}`reaction` |
| `(F A…)` for a declared function `F` | core | a compound | {doc}`evaluation` |
| `(L A…)` for a local function value `L` | core | a compound | {doc}`evaluation` |

## Built-in functions and the standard library

These names are built-in functions and constants, except the random functions, which come from the file rand, and the files of the last row. Each call of a built-in function is a compound and a core form ({numref}`built-ins`).

| Heads | What they are |
|---|---|
| `+`, `-`, `*`, `/`, `^`, `mod`, `=`, `!=`, `<`, `<=`, `>`, `>=` | the operators |
| `not`, `abs`, `or?`, `none?`, `some?`, `somes` | logic, absolute value and `none` |
| `sqrt`, `sign`, `floor`, `ceil`, `exp` | numbers |
| `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, `sind`, `cosd`, `tand`, `secd`, `cscd`, `cotd`, `asin`, `acos`, `atan`, `acot`, `asec`, `acsc`, `asind`, `acosd`, `atand`, `acotd`, `asecd`, `acscd`, `rad`, `turn`, `deg`, `to-rad`, `to-turn` | angles |
| `polar`, `to-polar`, `dist` | points |
| `rgb`, `mix`, `lighten`, `darken`, `light-dark` | colors. `(rgb R G B)` and `(rgb R G B A)` evaluate to the color with the red, green, blue and alpha channels R, G, B and A, each a real from 0 to 1, and A is 1 when it is left out |
| `round`, `log`, `min`, `max`, `lerp` | with a varying number or type of arguments |
| `range` | `(range LO HI (gap G))`: the numbers from `LO`, `G` apart, up to `HI` and not including it. `G` is 1 when the range gives neither `gap` nor `num`. `(range LO HI (num N))`: `N` numbers evenly apart, from `LO` to `HI`, both included. `gap` and `num` are {term}`named arguments <named argument>` of `range` |
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | random values and seeds, which a source names only through the file rand of the standard library ({numref}`rand-module`). `rand`, `rand-int`, `pick` and `shuffle` take the named argument `(seed S)`, and use the {term}`default seed` of the file that holds them when it is left out ({numref}`default-seed`) |
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
| `move` | core | a compound | {doc}`time` |
| `from`, `to`, `duration`, `path` | core | a clause | {doc}`time` |
| `ease` | core | a clause | {doc}`time` |
| `like` in a movement or a move | syntactic sugar | a clause | {numref}`like-copies` |
| an animation's body of several items | syntactic sugar | the body of an animation | {numref}`sugar-rewrites` |
| `defaults` in a score | core | a clause | {doc}`time` |
| `loop` | core | a clause | {doc}`time` |
| `score` | core | a compound | {doc}`time` |
| `lag` | core | a clause | {doc}`time` |
| `in-order`, `at-once` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `foreach` in a score | core | a special form | {doc}`time`, {doc}`binding-time` |
| the name of a movement, or of an animation with no parameters, in a score | core | a body item | {doc}`time` |
| `wait` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `jump` | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `(A …)` for an animation `A` | core | a compound | {doc}`time`, {numref}`animation-step` |

## Page objects and their items

| Head | Kind | What it is | Defined in |
|---|---|---|---|
| `canvas`, `readout`, `display` | core | a declaration | {doc}`page-interface`, {doc}`lifecycle` |
| `slider`, `button`, `play`, `stepper`, `toggle` | core | a declaration | {doc}`page-interface`, {doc}`reaction`, {doc}`concurrency` |
| `on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-pointermove` | core | a declaration | {doc}`reaction`, {doc}`concurrency` |
| `on-show`, `on-hide`, listeners that play while a canvas starts or stops drawing a shape | core | a declaration | {doc}`reaction`, {doc}`lifecycle` |
| `on-view`, `on-ready`, `on-live`, `on-quiet`, listeners on their own view | core | a declaration | {doc}`lifecycle` |
| `x`, `y`, `width`, `height`, `shift`, `shift-x`, `shift-y`, `rotate`, `scale-x`, `scale-y`, `pan`, `zoom` on a canvas | core | a clause | {doc}`page-interface` |
| `toggle-duration`, `toggle-ease` | core | a clause | {doc}`time`, {doc}`page-interface` |
| a name or a compound in a canvas, such as `s`, `{s t}` or `(when c d)` | core | a name or a compound | {doc}`page-interface` |
| `font` on a readout | core | a clause | {doc}`page-interface` |
| `kind` on a display | core | a clause | {doc}`page-interface` |
| a movement on a control or a listener | core | a positional argument of a writer | {doc}`reaction`, {doc}`time` |
| the move of a slider | core | a compound | {doc}`page-interface`, {doc}`reaction` |
| the target of `toggle` | core | a name | {doc}`reaction` |
| `(on-pointermove T)` with a target `T` | syntactic sugar | a declaration | {numref}`sugar-rewrites` |
| `as` on a listener that the pointer triggers | core | a clause | {numref}`pointer-binding` |
| the target of `on-drag` written as a move | core | a compound | {doc}`reaction`, {numref}`drag-group-shift` |
| the target of `on-drag` written as a name | syntactic sugar | a compound | {numref}`sugar-rewrites` |
| `label` | core | a clause | {doc}`page-interface`, {doc}`accessibility` |
| `stops` on a slider | core | a clause | {doc}`page-interface` |
| `buttons`, `rest`, `labels` on a play | core | a clause | {doc}`page-interface`, {doc}`time` |
| `selected` on a button | core | a clause | {doc}`page-interface`, {doc}`accessibility` |
| `active` | core | a clause | {doc}`reaction` |
| `priority` | core | a clause | {doc}`concurrency` |
| `stop-propagation` | core | a clause | {doc}`reaction` |
| `in` | core | a clause | {doc}`page-interface`, {doc}`lifecycle` |
| a guard | core | a compound | {doc}`reaction` |
| `doc` on a component | core | a clause | {doc}`compiled-format` |

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
| `func` | one expression: a literal, a name or a compound | no |
| `scene` | shapes, variables, `exists-when` | yes |
| `group`, `row`, `column` | shapes, `exists-when` | yes |
| `motif` | shapes, variables that are bound or const (never free: free state of each shape is a parameter, which becomes an attribute), `exists-when` | yes |
| `formula` | terms, `exists-when` and variables. The string is its positional argument ({numref}`formula-terms`) | yes |
| `record` | variables, records, palettes | yes |
| `palette` | items `(member color)` | yes |
| `interface` | items `(T attribute condition…)` | yes |
| `type`, a variable `(T name …)` | {term}`conditions <condition>`, such as `(>= 0)` | yes |
| `animation`, `score`, `in-order`, `at-once` | movements: `move`, `jump`, `wait`, a score, the name of a movement, `(A …)` for an animation `A` | yes |
| `defaults` | items `(attribute value)`, and in a score, `(duration …)`, `(ease …)` and `(lag …)` | yes |
| `canvas` | at least one name or compound that evaluates to a shape, the scene, `none` or a list of shapes, such as `s`, `{s t}` or `(when c d)`. Listeners ({numref}`listeners-in-views`) | yes |
| `readout`, `display` | listeners ({numref}`listeners-in-views`) | yes |
| a control, a listener | guards, such as `(>= k 0)` | yes |
| `let`, `foreach` | items of the kinds that the body around them holds | yes |
| `in` | the views that a control belongs to | no |
| `labels` | strings | no |
| a call that takes any number of arguments, such as `(+ a b c)` | its arguments | no |
:::

So `(canvas v)` is an error, because the body of a canvas holds at least one name or compound that evaluates to a shape, the scene, `none` or a list of shapes, and `(canvas v s)`
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
| `dash-offset` | as an item | write `(dash {4 2} 1)` |
| `move` | in a canvas | a canvas takes no move |
| `term` | at the top level | a term is given inside its formula |
| `pointer-events` | on a group, a row, a column or a shape of a motif | write `(defaults (pointer-events B))` |

:::{admonition} Code differs
:class: note
The compiler accepts `(pointer-events B)` on a group, a row, a column or a shape of a motif as a default
for its members (compiler.py:4895-4941, 5395-5443). Bead mtp-327t makes it a compile error.
:::
