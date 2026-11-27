# Compiled format

This page defines version 1 of the format of the {term}`.mtpc`: the parts of the file, and what each
part means. The schema of version 1 is the file
[mtpc.schema.json](https://github.com/aris-pub/mathterpiece/blob/main/docs/spec/mtpc.schema.json),
which is part of this spec, and which holds every rule of this page that a JSON schema can express
({numref}`schema-strength`). The .mtpc of the smallest world model is given in {doc}`compiler-runtime`.

Every expression in the file has its type, so that the runtime never checks a type
({numref}`runtime-no-type-work-while-drawing`). Every bound container lists the containers that it
reads, so that the runtime computes again only what depends on a change
({numref}`runtime-builds-live-model`). Every container whose value is known when compiling holds its
value, and not an expression ({term}`folding`).

:::{admonition} Code differs
:class: note
Version 1 holds what the compiler writes today, which differs from the other pages of the spec in
these ways:

- It has the type and the value `transform`, and the attributes `translate` and `transform`, where
  the spec has the frame attributes `shift`, `rotate`, `scale-x` and so on. Bead mtp-1vyc.
- It has `transition` objects and `animation` objects with steps, where the spec has movements,
  movement groups with lags, and animations as templates. Beads mtp-kir3, mtp-cg47 and mtp-idcs.
- It has the types `namespace` and `palette`, and writes a font as a value, where the spec has
  records, and a font is a record. Beads mtp-h732 and mtp-1vyc.
- It writes a shape declared with a motif with members, where the spec makes such a shape one shape
  whose body's shapes are its attributes. Bead mtp-ar1u.
- The `map` of an `on-drag` reads the name `pointer`, where the spec binds a name with `(as N)`. Bead
  mtp-t8in.
- It can write only some of the types of the spec. Bead mtp-uhak.
:::

## The file

This rule exists so that a program can read a .mtpc with any reader of JSON, and check it against one schema.

```{rule} mtpc-json
A .mtpc is a JSON text in UTF-8 whose value is an object. A .mtpc of version 1 matches the schema of
version 1, and its object has these members:

| Member | What it holds |
|---|---|
| `mtpc` | 1, the version of this spec that its compiler implements ({numref}`spec-version`) |
| `types` | the declared types ({numref}`mtpc-declared-types`) |
| `objects` | the entries: every variable and every object of the world model ({numref}`mtpc-objects`) |
| `functions` | the functions that the runtime may call ({numref}`mtpc-functions`) |
| `names` | the id of each entry that has a name ({numref}`mtpc-names`) |
| `shared`, only when it is not empty | the values that shapes of one kind share ({numref}`mtpc-shared`) |
| `type-table`, only when it is not empty | the structured types, each written once ({numref}`mtpc-type-table`) |
```

## Entries and ids

This rule exists so that every part of the file can refer to a variable or an object by a number.

```{rule} mtpc-objects
`objects` lists every variable and every object of the world model, each as an entry: the
variables, the shapes, the `transition` and `animation` objects, and the components. The id of an
entry is its position in `objects`, counted from 0. The entries come in the order of their
declarations in the source, depth first: a collection comes before its members, the members of a
shape declared with a motif come right after that shape, and a `transition` or an `animation` written
as an item in the form of another entry comes right before that entry.
```

This rule exists so that a reference to an entry is never ambiguous, whatever names the source uses.

```{rule} mtpc-references
Every reference to an entry is its id, with two exceptions, which are names: a parameter or a `let`
binding in an expression is written `["local", T, name]` ({numref}`mtpc-expressions`), and a declared
type is written by its name, which is the name of an entry of `types`, as in `"of": "dial"`.
```

This rule exists so that the author can place a component of the model by the name that the source gives it.

```{rule} mtpc-names
`names` maps the name of each entry that has a name to its id. The name is the one that the author
writes in a page: `theta`, `m0` for a member of a group, and `d1.face` for the shape `face` in the
body of the motif of the shape `d1`. An entry declared with no name ({numref}`unnamed-head`) has no
member in `names`. The member `"name"` of an entry holds its own name only, such as `face`, and is
`null` for an entry with no name.
```

So `<mtp-canvas model="dial" name="v">` places the canvas whose id is `names.v` ({doc}`page-interface`).

This rule exists so that a .mtpc holds no more than its page can use.

```{rule} mtpc-imported-declarations
Of the declarations that a source imports ({numref}`import-puts-in`), a .mtpc holds only those that
the source uses, directly or through other declarations.
```

## Shared values and the type table

This rule exists so that a value that many shapes have is written once, which keeps the file small.

```{rule} mtpc-shared
For each kind of shape and each attribute of that kind, `shared` may hold one value, which every
shape of that kind with no value of its own for that attribute has. The kind is the `kind` of the
shape, such as `circle`, or `instance:` followed by the name of the motif for a shape declared with a
motif. A program that reads the .mtpc copies each value of `shared` into every shape of its kind that
has no value of its own for that attribute, before it reads anything else but the type table, and
then reads the file as if every attribute were written in each shape.
```

So with three circles of radius 1 and one of radius 2, `shared` may hold `{"circle": {"r": …}}` for
the radius 1, and only the fourth circle then has an `r` of its own.

This rule exists so that a type that many entries have is written once, which keeps the file small.

```{rule} mtpc-type-table
`type-table` lists structured types, each once: the types that are not a plain name such as
`"real"`. Where a structured type is the whole value of the `type` of an entry or of an attribute,
the second item of an expression, the type of a parameter, the `result` of a function, the `type` of a
declared type or the `base` of a variant, it may be written as its position in `type-table`. A type
inside another type is written in full. A program that reads the .mtpc puts each type back in its
place before it reads anything else, and before it copies the values of `shared`.
```

## Types

This rule exists so that the runtime can read every type that the prover worked out.

```{rule} mtpc-types
A type is written as JSON:

| Type | Written |
|---|---|
| a built-in type | `"int"`, `"ratio"`, `"real"`, `"complex"`, `"bool"`, `"string"`, `"color"`, `"font"`, `"point"`, `"transform"`, `"transition"`, `"animation"`, `"none"`, `"scene"`, `"namespace"`, `"palette"` (a namespace whose members are colors), `"formula"` and `"term"` |
| a shape type | `{"shape": "circle"}`, and in the same way for `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text` and `group` |
| a declared type | `{"named": N}`, with N the name of an entry of `types`, such as `{"named": "dial"}` |
| a component | `{"component": "slider"}`, and in the same way for each component |
| an interface | `{"interface": "shape"}`, `{"interface": "positioned"}`, and `{"interface": "sequence", "of": T}` |
| `list[T]` | `{"list": T}` |
| `func[T1 … Tn R]` | `{"func": [T1, …, Tn], "result": R}` |
| `T\|none` | `{"union": [T, "none"]}` |
| a refined type `(T C…)` | `{"refine": T, "constraints": [C, …]}` |
```

This rule exists so that the runtime can read every condition of a type, and the length of every list whose length is known.

```{rule} mtpc-constraints
A condition is written as an array: `[">=", c]`, `[">", c]`, `["<=", c]`, `["<", c]`,
`["length", n]`, `["one-of", [v, …]]`, `["const"]` for a const container, and `["wrap", lo, hi]`
for a number brought into the interval from lo up to hi. A {term}`known length` is always written as
a `["length", n]`.
```

This rule exists so that the runtime knows each type that the source declares and that the world model uses.

```{rule} mtpc-declared-types
`types` lists each type that the source declares with `type`, `motif` or `variant` and that an entry
uses, directly or through other types or functions, each as one of these:

    {"name": "unit", "kind": "type", "type": T}
    {"name": "dial", "kind": "motif", "params": [P, …]}
    {"name": "bar", "kind": "variant", "params": [P, …], "base": T, "fixed": [attr, …]}

A parameter `P` is `{"name": N, "type": T}`, with `"default": V` when it has a default, and
`"default": null` when its default is `none`. The `base` of a variant is the shape type that the
variant refines, and `fixed` lists the attributes that the body of the variant sets, which a shape
declared with the variant may not set and a writer may not write to.
```

## Values

This rule exists so that every value has one way of being written, which its type tells the runtime how to read.

```{rule} mtpc-values
A value is written as JSON and read by its type, which is always written with it:

| Type | Written |
|---|---|
| `int`, `real` | a number |
| `ratio` | `[numerator, denominator]`, in lowest terms |
| `complex` | `[re, im]` |
| `bool` | `true`, `false` |
| `string`, a choice type | a string |
| `color` | the string `"#rrggbbaa"`. A color whose value is not the same on a light page and on a dark page is the string `"light-dark(#rrggbbaa, #rrggbbaa)"`, with one space after the comma, and the runtime passes it to the browser as written ({numref}`color-functions`) |
| `font` | `{"family": F, "style": S, "weight": W, "size": Z}`, with F `null` for the font of the page |
| `point` | `[x, y]` |
| `list[T]` | an array of values of type T |
| `transform` | `[a, b, c, d, e, f]`, the matrix of the affine map that takes `[x y]` to `[ax + cy + e, bx + dy + f]` |
| `none` | `null` |
| an object, such as a shape, a `transition` or an `animation` | `{"ref": id}` |
| a function | `{"func": id}` for an entry of `functions`, and `{"builtin": N}` for the built-in function N |
```

## Expressions

This rule exists so that the runtime can turn each expression into a function once, when the .mtpc loads.

```{rule} mtpc-expressions
An expression is written as an array: a string that gives its kind, its type, then its parts. Its type
is the type that the prover worked out, so the type of an expression that may evaluate to `none` is a
`{"union": [T, "none"]}`, and the runtime tests for `none` only there.

| Expression | Written |
|---|---|
| a literal | `["lit", T, value]` |
| a list or a point made from expressions | `["list", T, e…]` |
| an interpolated string | `["format", T, part…]`, with T `"string"`, or `{"union": ["string", "none"]}` when a part may be `none`. Each part is a string, or `[e, spec]`, with spec the {term}`format spec`, `""` when it has none |
| a read of a variable | `["read", T, id, null, frame]` ({numref}`mtpc-frames`) |
| a read of an attribute | `["read", T, id, attr, frame]` |
| an entry as a value, such as a group given to `map` | `["obj", T, id]` |
| a number brought into an interval | `["wrap", T, e, lo, hi]`: the value of e brought into the interval from lo up to hi ({numref}`modular-types`), and `none` when e evaluates to `none`. It is written wherever a value that may lie outside the interval goes into a type with a `wrap` condition |
| a value checked against conditions | `["check", T, e, [C, …]]`: the value of e, and `none` when it breaks one of the conditions C. It is written wherever the prover cannot prove a condition of a bound value ({numref}`unproved-conditions`), so T includes `none` |
| a parameter or a `let` binding | `["local", T, name]` |
| a call of a built-in function or an operator | `["builtin", T, name, arg…]`, with name its name in {doc}`stdlib`, such as `"sind"`, `"+"` or `"or?"` |
| a call of an entry of `functions` | `["call", T, id, arg…]`, with every argument, the defaults included |
| a call of a function value | `["apply", T, e, arg…]` |
| a function as a value | `["func", T, id, [name…]]` for an entry of `functions`, with the names from around a function written with `fn` that its body reads, and `["builtinfunc", T, name]` for a built-in function |
| a part, `(. X K)` | `["part", T, e, key]`, with key the label of an attribute, a string, or an expression for a position or for the name of a member |
| an attribute of every member of a group, `g.A` | `["spread", T, e, attr]`, a list |
| `if` | `["if", T, c, a, b]` |
| `cond` | `["cond", T, [[c, v], …], else]` |
| `and`, `or` | `["and", "bool", e…]`, `["or", "bool", e…]` |
| `let` | `["let", T, [[name, e], …], body]`. Each e is evaluated once, in order, and then the body. Each name ends in `#` and a number, so that no two `let` names in one expression are the same. A `let` is written only for values that are known only while drawing and are not shapes |
| a point on the box of a shape | `["anchor", T, side, e, gap, frame]`, with side one of the eight names of {numref}`box-points`, e the shape, gap an expression, and frame as in a read |
| a random value | {numref}`mtpc-random-values` |
```

This rule exists so that the runtime reads each position in the frame of the expression that reads it.

```{rule} mtpc-frames
The frame of a read is the id of the innermost collection, or shape declared with a motif, that holds
the expression, `null` at the top level and directly in the scene, and `"caller"` in the body of a
function. With `"caller"`, the frame is the frame of the expression that calls the function, which
the runtime passes with each call. The runtime converts the value that it reads through every
`translate` and `transform` that applies to the entry that is read and not to the frame, and the
`deps` of the expression include those attributes ({numref}`mtpc-deps`).
```

This rule exists so that every runtime computes each random value from the same seed and site.

```{rule} mtpc-random-values
A call of `rand`, `rand-int`, `choice` or `shuffled` is written `[N, T, site, seed, arg…]`, with N
`"rand"`, `"rand-int"`, `"pick"` or `"shuffle"`, site the {term}`site` of the call
({numref}`random-site`), and seed the expression of the {term}`seed` that the call uses, a read of a
variable of type `rand-seed`. The arguments are `lo` and `hi`, which a `rand` may leave out, or the
list. The runtime computes the value from the value of the seed, the site and, for `shuffle`, the
position of each item, by {numref}`random-values`. A call of `next-seed` is written
`["builtin", T, "next-seed", seed]`.
```

## Containers

This rule exists so that the runtime knows, for each container, whether a writer may write to it and how its value is computed.

```{rule} mtpc-containers
A variable, an attribute of an entry, and each value that a component reads, such as its `active` and
the limit of a guard, is written in one of these forms:

    {"type": T, "free": V}
    {"type": T, "start": e, "deps": [[id, attr], …]}
    {"type": T, "bound": e, "deps": [[id, attr], …]}

A free one holds its starting value V. A started one is free, and its starting value is the value of
e, which the runtime evaluates once, when it builds the {term}`live model` ({term}`free starting value`). A bound one holds the expression e. A writer may write to a free or a started one, unless
its type has a `["const"]` condition, it is fixed, or it is a token ({numref}`mtpc-variable-entries`).
```

An attribute that a variant fixes has `"fixed": true` in each shape of that variant. An attribute of a
shape declared with a motif that comes from a variable of the body of the motif has `"doc"`, a
string, when that variable has a {term}`docstring`.

This rule exists so that the runtime computes a bound container again only when a container that it can read changes.

```{rule} mtpc-deps
The `deps` of a bound or a started container list every container that its expression can read:
directly, through every function that it calls, and through the names that its functions read
from around them. Where a read depends on a value known only while drawing, such as `g[side].pos`,
`deps` lists every container that the read may read, here the `pos` of every member. `[id, null]` is
the variable whose id is `id`.
```

This rule exists so that the runtime never computes a value that the compiler has already computed.

```{rule} mtpc-folded
A variable or an attribute whose value is known when compiling is written as free, with a `["const"]`
condition in its type, whether the source declares it const or the compiler folded its expression.
The exception is a variable or an attribute whose expression is the name of a const variable or of a
built-in constant, or a read of a const attribute: it is written as free, with no `["const"]`
condition.
```

So `(real a (* 2 pi))` is written `{"type": {"refine": "real", "constraints": [["const"]]}, "free": 6.283185307179586}`,
and `(real b pi)` is written `{"type": "real", "free": 3.141592653589793}`.

This rule exists so that the runtime reads every attribute of every shape from the file, and never from defaults of its own.

```{rule} mtpc-shape-attributes
Every attribute of a shape is written, also when it has its default value, in the shape or in
`shared`. `pos` is not written, since it is `x` and `y`. The attributes of a line are its `from` and
its `to`, of a triangle its corners, of a polyline and of a polygon its `points`, and of a curve its
`from`, its `to` and its `controls`. The runtime computes their `x` and `y`: the midpoint, the
centroid, the mean of the points, and the mean of the ends and the controls. A write to that `x` or
`y` becomes writes to every end, corner or point, which moves each of them by the same amount.
```

## Entries

This rule exists so that the runtime can tell what each entry is from its members alone.

```{rule} mtpc-entry-keys
Every entry has these members, and the members of its kind:

    {"kind": K, "type": T, "access": "scene" | "page", "name": N | null}

`access` is `"page"` for a view, a control, a listener, and an entry that reads one, and `"scene"` for
every other entry ({numref}`what-reads-what`). An entry whose declaration has a docstring
({numref}`docstrings`) also has `"doc"`, its text.
```

This rule exists to give the members of a variable, and to mark the variables that a page may restyle.

```{rule} mtpc-variable-entries
An entry of kind `variable` has `"value"`, its value, free, started or bound ({numref}`mtpc-containers`),
and `"token"`, which is `true` for a variable of type `color` or `font` and `false` otherwise. A token
holds its declared value, which the runtime uses where the CSS of the page sets none
({numref}`compiler-never-acts-while-drawing`). A variable that holds the value of a binding of a `let`
whose body holds declarations has `"let"`, the name of that binding, and `"name": null`. Every
attribute that reads that binding reads this variable, so the runtime computes the value once each
time a container that it reads changes.
```

This rule exists to give the members of the scene, of the shapes and of the other entries of the world model that are not components.

```{rule} mtpc-model-entries
| Kind | Its other members |
|---|---|
| `scene` | `"members"`: the ids of its shapes. `"attrs"`: `background`, and `transform`, which sets how the runtime draws the coordinates of the scene |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text`, `group` | `"attrs"`: every attribute, free, started or bound, and `exists`, a bool, when an `exists-when` holds the name of the shape. While `exists` is false, the shape is `none`, and so are its members when it is a group. A `group` also has `"members"`, `"clip"`, the id of its clip shape when it has one, which is an entry in the frame of the group and not a member, and `"fixed-size": true` when its members are measured in pixels |
| `group`, for a row or a column | `"layout"`: `{"axis": "row" \| "column", "gap": G, "align": A}`, each free, started or bound. The runtime places each member after the box of the member before it |
| `instance`, a shape declared with a motif | `"of"`: the name of the motif. `"members"`. `"attrs"`: its parameters, its bound variables, and `x`, `y`, `translate` and `transform`. `"clip"`, as for a group |
| the kind of its base, for a shape declared with a variant | `"of"`: the name of the variant. `"attrs"`: the attributes of its base, the fixed ones marked, then its parameters |
| `namespace` | `"members"`: the ids of its variables and namespaces, in the order of their declarations. Each member is an entry, named through the namespace, as `theme.ink` |
| `formula` | `"tex"`: its LaTeX as written, with `\term{name}{…}` around each term. `"members"`: the ids of its terms, in the order of the LaTeX. Its variables are entries, named through the formula, as `bounds.lit` |
| `term` | `"term"`: its name in the LaTeX, `gap` for `\term{gap}{…}`. `"formula"`: the id of its formula. `"attrs"`: `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding`, `exists`, and `tex`, its content, when its `(term …)` has one |

Every shape declared with a motif or a variant is written in full, so the runtime never builds a
shape from a motif or a variant.
```

This rule exists to give the members of each view.

```{rule} mtpc-view-entries
| Kind | Its other members |
|---|---|
| `canvas` | `"shows"`: the items of its body, in the order written, which is the order in which the runtime draws them, the later ones on top. Each is the id of a shape, or a container for an item that evaluates to a shape, `none` or a list of shapes, such as `(when show d)`. `"transition"`: an id or `null`. `"attrs"`: `x`, `y`, `width`, `height`, `transform`, `pan` and `zoom`. A canvas that gives none of `x`, `y`, `width` and `height` has `"fit": true`, and no `x`, `y`, `width` or `height` in its `"attrs"` or in `shared`. A canvas that gives all four has no `"fit"` |
| `readout` | `"attrs"`: `value`, its string, and `font` |
| `display` | `"formula"`: the id of its formula. `"as"`: `"block"` or `"inline"` |
```

This rule exists to give the members of each control.

```{rule} mtpc-control-entries
Every control has `"conditions"` ({numref}`mtpc-writer-conditions`), `"active"`, a bool, free,
started or bound, or `null`, `"label-tex": true` when its label is a {term}`TeX string`, and, when
there are some, `"canvases"`: the ids of the canvases that draw a shape that depends on a value that
the control writes to, each of which must be ready before the reader may use the control
({doc}`lifecycle`).

| Kind | Its other members |
|---|---|
| `button`, `play`, `stepper`, and `slider` with an `"animation"` | `"animation"`: an id. A play has `"labels"`, when it has labels: one string for each step of its animation, which is each item of its body, inside a `loop` around the whole body if there is one. A play has `"rest"`, when it has one: the seconds of a wait that the runtime adds after every step of its animation but the last. `"attrs"`: `label`, `stops` for a slider, the number of positions at which its knob stops, `buttons` for a play, and the attributes that the reader's actions write to: `position` for a slider, and `playing` and `step` for a play and a stepper. `step` is the step that is playing or paused, or else the highest step whose state the scene is in, counted from 1, and 0 in explore mode |
| `toggle` | `"target"`: `[id, attr]`, the bool that it writes to. `"animation"`: the id of the animation that the runtime plays after each flip, or `null`. `"attrs"`: `label`, `value` |
| `slider` with a `"target"` | `"target"`: `[id, attr]`, the number that it writes to. `"attrs"`: `label`, `from`, `to`, `step` and `ticks`. `step` and `ticks` are of type `{"union": ["real", "none"]}`, and are `null` when the source gives none |
| `range-slider` | `"low"` and `"high"`: each `[id, attr]`, the numbers `LOW` and `HIGH` that it writes to. `"attrs"`: as for a slider with a `"target"` |
| `dial` | `"target"`: `[id, attr]`, a number whose type has a `wrap` condition, which gives the interval of one turn. `"attrs"`: `label`, `step` and `ticks`, as for a slider |
| `number-field` | `"target"`: `[id, attr]`. `"attrs"`: `label`, `step`, 1 when the source gives none, and `buttons` and `typing`, `true` when the source gives none |
| `text-field` | `"target"`: `[id, attr]`, the string that it writes to. `"attrs"`: `label` |
| `select`, `multi-select` | `"target"`: `[id, attr]`, a list for a multi-select. `"as"`: its `kind`, `"menu"` when the source gives none. `"options"`: one member for each `(opt V L)` of its body, in the order of the source, at least one: `{"value": V, "label": L, "label-tex": true}`, with V and L free, started or bound, `"label"` only when the option has a label, and `"label-tex"` only when that label is a TeX string. `"attrs"`: `label` |
```

This rule exists to give the members of each listener.

```{rule} mtpc-listener-entries
Every listener has `"conditions"` ({numref}`mtpc-writer-conditions`), except `on-show` and `on-hide`,
and every listener that has `"active"` holds in it a bool, free, started or bound, or `null`.

| Kind | Its other members |
|---|---|
| `on-drag` | `"shape"`: an id. `"target"`: `[id, attr]`. `"map"`, when the drag is written with a movement: the `to` of the movement, free, started or bound, which reads the name `pointer`, a point. `"active"` |
| `on-pointermove` | `"shape"`: an id or `null`. `"view"`: the id of a canvas or `null`, exactly one of the two not `null`. `"target"`: `[id, attr]`. `"active"`. `"stop-propagation"`: a bool, free, started or bound, or `null` |
| `on-click`, `on-release`, `on-dragstart`, `on-dragend` | `"shape"`: the id of a shape, or for `on-click`, of a term. `"animation"`: an id. `"active"`. `"stop-propagation"`, as for `on-pointermove` |
| `on-enter`, `on-leave` | `"shape"`: the id of a shape or of a term. `"animation"`: an id. `"active"` |
| `on-show`, `on-hide` | `"shape"`: the id of a shape, a group or a shape declared with a motif, and for each of the last two, the runtime plays the listener for each of its shapes that has no listener of the same kind of its own. `"animation"`: an id, whose movements write only to the stand-in of the shape, which the runtime draws in the canvas of `"in"` ({numref}`runtime-adds-no-objects`). No `"active"` and no `"priority"` |
| `on-view`, `on-ready` | `"view"`: the id of a canvas. `"animation"`: an id. `"active"` |
| `on-live`, `on-quiet` | `"view"`: the id of a canvas, a readout or a display. `"animation"`: an id, or `null` when the listener has no movement. `"active"`. A view with an `on-live` has a quiet mode, and the view of every `on-quiet` also has an `on-live` ({doc}`lifecycle`) |
```

This rule exists so that the runtime triggers each writer only in the views that it belongs to.

```{rule} mtpc-in
A listener on a shape or a term has `"in"`: the id of the view whose body holds it
({numref}`listeners-in-views`), and the runtime triggers it only for what the reader does in that
view, and not while that view is quiet. A listener on its own view has no `"in"`. A control whose
source has `(in V…)` has `"in"`: the ids of those views, in the order written, at least one, and a
control with no `(in …)` has no `"in"`. The runtime hides a control while all of its views are quiet.
```

This rule exists so that the runtime knows the priority of each writer ({doc}`concurrency`).

```{rule} mtpc-priority
A control or a listener whose source has `(priority n)` has `"priority": n`, an int from 1 to 1000.
One with no `(priority …)` has no `"priority"`, and the runtime uses the priority of its kind: 1000
for `on-view`, 300 for `on-ready`, 700 for a gesture, and 500 for every other. The gestures are
`on-drag`, `on-pointermove`, and the reader holding the knob or the thumb of a slider, the thumb of a
range slider or of a dial, or the label of a number field.
```

This rule exists so that the runtime can clamp each write of a writer to its guards.

```{rule} mtpc-writer-conditions
The `"conditions"` of a writer is a list of clamps, one for each of its guards ({numref}`writer-guards`):
`{"target": [id, attr], "op": ">=" | ">" | "<=" | "<", "limit": L}`, with L free, started or bound.
Before the runtime makes a write to that target, it clamps the value to the limit.
```

## Animations and transitions

This rule exists so that the runtime can play an animation as a tree of steps.

```{rule} mtpc-steps
An entry of kind `animation` has `"steps"`, one step, which is one of these:

    ["move", [id, attr], transitionId, duration, ease]
    ["wait", seconds]
    ["at-once", step, …]
    ["in-order", step, …]
    ["loop", n | null, step]

A `move` has its own `duration` and `ease`, which the compiler works out from the `transition` and
from the nearest default around the movement. Several steps written one after another are one
`in-order`. A `(move …)` with a target, or the name of a `transition`, is a `move`, and a
`(move none …)` is a `wait`. The movement of a slider is an animation of one `move`, of duration 1.
An animation with `(loop n)` or `(loop)` has a `loop` around its body, with n the number of rounds,
or `null` for no end, and each round starts again from the start of its step, reading the ends of
every `move` again.
```

The steps of a play are the items of the `in-order` at the top of its animation, inside a `loop`
around the whole body if there is one, or the one step when there is no such `in-order`.

This rule exists so that the runtime knows the ends, the duration, the ease and the path of each `move`.

```{rule} mtpc-transitions
An entry of kind `transition` has these members:

    {"from": V | null, "to": V | null, "duration": seconds | null,
     "ease": "linear" | ["step", n] | ["step-ease", p] | {"func": id} | null,
     "path": null | {"func": id}}

A `transition` never changes. The runtime reads each of its `from` and `to`, V free, started or
bound, once, when a `move` along it starts. `null` for `from` or `to` is the value of the target when
the `move` starts. `"linear"` is the ease of a movement that has no ease of its own, and `null` for
`duration` or `ease` means that each `move` along it has the one that the compiler works out from
the defaults around it. A `path` of `null` is the straight line between the ends.
```

## Functions

This rule exists so that the runtime can call each function that the compiler could not fold.

```{rule} mtpc-functions
`functions` lists every function, declared with `func` or written with `fn`, that the runtime may call
while drawing, in the order of the source, and leaves out every function that is called only where
the compiler folded the call, or never. The id of a function is its position in `functions`. Each is
written `{"params": [P, …], "result": T, "body": e}`, with each P as in {numref}`mtpc-declared-types`,
and `"doc"` when the function has a docstring. The body of a function written with `fn` reads the
names from around it through `["local", …]`, and the `["func", …]` expression that creates it lists
those names ({numref}`mtpc-expressions`).
```
