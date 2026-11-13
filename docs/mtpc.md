# The .mtpc format

An `.mtpc` (mtp compiled) file is the static representation of one world model: what the compiler writes and the only thing the runtime reads. It is JSON, checked against `mtpc.schema.json`. This document says what each part means; the schema checks the structure, and this document adds the rules a schema cannot express.

Three rules from the other documents shape everything here:

- **The runtime never guesses a type.** Every variable, every attribute and every expression carries its type, so the runtime can turn each expression into one function specialized to its types when the file loads, and never checks or converts a type while drawing (type system, section 1).
- **The runtime recomputes only what changed.** Every bound variable or attribute lists every variable and attribute it can read (data model, "How reactivity works").
- **Everything known when compiling is already folded.** A variable or an attribute known when compiling holds a plain value, never an expression.

## Top level

    {
      "mtpc": 4,
      "types": [ … ],
      "objects": [ … ],
      "functions": [ … ],
      "names": { "theta": 3, "p": 5, "d1.face": 9, … },
      "shared": { "circle": { "r": { … }, … }, "instance:dial": { … } },
      "type-table": [ {"refine": "string", "constraints": [ … ]}, … ]
    }

- **`mtpc`**: the format version, 4.
- **`types`**: every type the illustrator declared that the objects use, directly or through other types or functions: named types, motifs and variants. One nothing uses is left out.
- **`objects`**: every object in the world model (variables, shapes, transitions, animations, components). An object's **id** is its position in this list. Objects appear in the order their declarations are reached in the source, depth first: a container comes before its members, a motif instance's members follow the instance, and a transition or animation written inline as an item comes right before the object that holds it.
- **`functions`**: every function the model calls while drawing, declared with `func` or written in place with `fn`, in source order. A function only called where the compiler worked out the result, or never called, is left out. A function's id is its position in this list. A function declared with a docstring, `doc@'text'`, has its `"doc"` too.
- **`shared`**, only when there is something in it: for each attribute that every shape of one kind has, its most common value among them, when at least two share it, written here once and left out of the shapes that have it; a shape with another value keeps its own. A kind is a shape's `kind`, such as `circle`, or `instance:` and the motif's name for motif instances, since their attributes differ by motif. A kind with one shape shares nothing. A reader puts each value back in every shape of its kind that does not give it, as a copy, before reading the file; after that, the file is read as if every attribute were written in each shape.
- **`type-table`**, only when there is something in it: each structured type the file uses, every type that is not a plain name such as `"real"`, written once. Where the file writes a type at the top of something (an object's `type`, an attribute's, the second item of an expression, a parameter's, a function's `result`, a declared type's `type` or a variant's `base`), it writes a structured type as its position in this list; a type inside another type is written out in full. A reader puts each back in its place, before reading the file and before putting back `shared` values.
- **`names`**: each named object's name, mapped to its id, as an author or a page refers to it: `theta`, `m0` (group members are named like any scene object), `d1.face` (names inside a motif instance are written through the instance). Unnamed objects (`head_`, or `none` as the name) have no entry. The `"name"` field of an object holds its own name only: `face`, not `d1.face`.

Every reference to an object is resolved to its id. Two things stay names: a parameter or `let` name inside an expression (`["local", …]`), and a declared type (`"of": "dial"`), which is looked up in `types`.

**Same source, same bytes.** The file is UTF-8 JSON written with keys sorted, no whitespace between tokens (`,` and `:` as separators), non-ASCII characters written as themselves, and one newline at the end. Numbers are written in their shortest form that reads back exactly. Lists are in the orders given here.

## Types

Every type is written as JSON:

| Type | Written |
|---|---|
| built-in | `"int"`, `"ratio"`, `"real"`, `"complex"`, `"bool"`, `"string"`, `"color"`, `"font"`, `"point"`, `"transform"`, `"transition"`, `"animation"`, `"none"`, `"scene"`, `"namespace"` (every namespace, as every circle is `{"shape": "circle"}`), `"palette"` (every palette, a namespace whose members are colors; its object is of kind `namespace`), `"formula"` and `"term"` (every formula and every term of one) |
| a built-in shape type | `{"shape": "circle"}`, likewise `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text`, `group` |
| a declared type | `{"named": "unit"}`, `{"named": "dial"}`, `{"named": "bar"}`: an entry of `types` |
| a component | `{"component": "slider"}`, likewise for each component |
| an interface | `{"interface": "shape"}`, `{"interface": "positioned"}`, `{"interface": "sequence", "of": T}` |
| a list | `{"list": T}` |
| a function | `{"func": [T1, T2, …], "result": T}` |
| broadened | `{"union": [T, "none"]}` |
| narrowed | `{"refine": T, "constraints": [C, …]}` |

A constraint is an array: `[">=", 0]`, `["<", 1]`, `["length", 3]`, `["one-of", ["left", "right"]]`, `["const"]`, `["wrap", 0, 360]`. A list's known length is always written as a `length` constraint.

### Declared types

    {"name": "unit", "kind": "type", "type": T}
    {"name": "dial", "kind": "motif", "params": [P, …]}
    {"name": "bar", "kind": "variant", "params": [P, …], "base": T, "fixed": ["width", "y", …]}

A parameter `P` is `{"name": …, "type": T}`, with `"default": value` when it has one (no `"default"` key means no default; `"default": null` means the default is `none`). A variant's `base` is the shape type it refines, and `fixed` lists the attributes its body sets, which no instance and no writer may change.

## Values

A value is plain JSON, read according to the type that always accompanies it:

| Type | Written |
|---|---|
| `int`, `real` | a number; a real that is infinite, `"infty"` or `"-infty"`, since JSON has no infinity |
| `ratio` | `[numerator, denominator]`, in lowest terms |
| `complex` | `[re, im]` |
| `bool` | `true`, `false` |
| `string`, a choice | a string |
| `color` | a string, `"#rrggbbaa"`, always in this form; a color with a dark value of its own (reference, "Colors"), the CSS that picks between the two, `"light-dark(#rrggbbaa, #rrggbbaa)"`, always in this form, with one space after the comma, and only when the two differ. The runtime paints it as written, so the browser picks by the `color-scheme` where it is drawn, and mixes the two modes apart |
| `font` | `{"family": …, "style": …, "weight": …, "size": …}`, `family` `null` for the page's font |
| `point` | `[x, y]` |
| `list[T]` | an array of values of type T |
| `transform` | `[a, b, c, d, e, f]`, the affine matrix |
| `none` | `null` |
| an object (a shape, a transition, an animation, …) | `{"ref": id}` |
| a function | `{"func": id}` for one in `functions`, `{"builtin": "sqrt"}` for a built-in |

## Expressions

An expression is an array: its operation first, then its type, then its parts. `frame` in a read is the id of the container the reading expression sits in (`null` at the top level and directly in the scene), or `"caller"` inside a function body, where the frame is that of the expression making the call, passed along with each call. The runtime converts the value read through every `translate` and `transform` that applies to the shape read but not to that container (reference, "Coordinates"), and `deps` include those `translate` and `transform` attributes. Types written here are what the compiler proved: a result that may be `none` has a `{"union": [T, "none"]}` type, and the runtime never checks for `none` anywhere else.

| Expression | Written |
|---|---|
| a literal | `["lit", T, value]` |
| a list or point built from expressions | `["list", T, e…]` |
| an interpolated string | `["format", T, part…]`, `T` being `"string"`, or `{"union": ["string", "none"]}` when a part may be `none`; each part a string, or `[e, spec]` with `spec` the format after the colon (`""` if none) |
| a variable | `["read", T, id, null, frame]` |
| an attribute | `["read", T, id, attr, frame]` |
| an object itself (a group passed to `map`, a shape read as a value) | `["obj", T, id]` |
| a value brought into an interval | `["wrap", T, e, lo, hi]`: `e` brought into [`lo`, `hi`), `none` when `e` is; written wherever a value that may lie outside enters a type with a `wrap` constraint |
| a value checked against constraints | `["check", T, e, [C, …]]`: `e`, or `none` when it breaks one of the constraints; written by the compiler wherever a bound value's constraint cannot be proved (type system, "What the compiler proves"), so `T` always includes `none` |
| a parameter or `let` name | `["local", T, name]` |
| a built-in function or operator | `["builtin", T, name, arg…]`, `name` being its name in the reference: `"sind"`, `"+"`, `"or?"`, … |
| a function from `functions` | `["call", T, functionId, arg…]`, always with every argument: the compiler fills in defaults |
| a call through a function value | `["apply", T, e, arg…]` |
| a function as a value | `["func", T, functionId, [captured name…]]` for one in `functions` (the captured names are those it reads from around it, if it was written in place), or `["builtinfunc", T, name]` |
| a part | `["part", T, e, key]`, `key` being an attribute name (a string) or an expression for a position or member name |
| an attribute of every member of a group | `["spread", T, e, attr]`, giving a list |
| `if` | `["if", T, c, a, b]` |
| `cond` | `["cond", T, [[c, v], …], else]` |
| `and`, `or` | `["and", "bool", e…]`, `["or", "bool", e…]` |
| `let` | `["let", T, [[name, e], …], body]`: each `e` in order, once, then the body. The compiler writes one only for values known while drawing that are not shapes, and gives each name a `#` and a number, so no two `let` names in one expression are the same |
| a point on a shape's box | `["anchor", T, side, e, gap, frame]`, `side` being one of the eight names (`"top"`, `"top-right"`, …), `e` the shape, `gap` an expression, and `frame` as in a read (reference, "Placing") |
| `rand`, `rand-int`, `pick`, `shuffle` | `[op, T, site, seed, arg…]`: `site` numbers each place a random function is written, after `foreach` and motif instances are expanded, starting at 0; `seed` is the expression of the seed it follows, a read of a `rand-seed` variable; the args are `lo` and `hi` (`rand`, optional, and `rand-int`) or the list (`pick`, `shuffle`). The value is computed from the seed's value, the site and, for a shuffle, each item's position, by the runtime's hash (web/src/random.ts), so the same seed always gives the same values; a new seed gives new ones. `next-seed` is a built-in, `["builtin", T, "next-seed", seed]`. |

## Free and bound values

A variable's value, every attribute of a mutable object, and every condition a component reads is written free or bound:

    {"type": T, "free": value}
    {"type": T, "bound": expr, "deps": [[id, attr], …]}
    {"type": T, "start": expr, "deps": [[id, attr], …]}

with `"fixed": true` on a variant instance's fixed attributes.

- A **free** one holds its starting value. A writer may change it while drawing, unless its type has a `const` constraint, it is fixed, or its object is a token.
- A **started** one, written `free@expr` in the source, is free, and its starting value is `expr`'s value, which the runtime reads once, when it builds the live model, and never again; `deps` lists what it reads, as for a bound one. From then on it is free like any other.
- A **bound** one holds an expression. `deps` lists every variable and attribute it can read: directly, through any function it calls, and through captured names. Where a read depends on a value known only while drawing, such as `g[side].pos`, `deps` lists every one it could read (the `pos` of every member). When any of them changes, this one is recomputed, and nothing else is. `[id, null]` is a variable.
- A variable or an attribute known when compiling is written as free, with a `const` constraint in its type, whether the illustrator wrote it that way or the compiler folded it. One exception: one given a constant (the bare name of a `const` variable or of a built-in constant, or a read of a `const` attribute) is free with no `const` constraint, as if given its value.
- Every attribute of a shape is written, including those left at their default, in the shape or, when it is the value most shapes of its kind share, once in `shared` (see "Top level"). `pos` is not: it is `x` and `y` read or written together. A line's attributes are its `from` and `to`, a triangle's its corners, a polyline's and a polygon's its `points`, a curve's its `from`, `to` and `controls`; their `x` and `y` are computed (the midpoint, the centroid, the mean of the points, the mean of a curve's ends and controls), and a write to them is split into writes to every end or corner, or moves every point.

## Objects

Every object has:

    {"kind": …, "type": T, "access": "scene" | "page", "name": "theta" | null, …}

and `"doc"`, a string, when its declaration gives a docstring, `doc@'text'` (reference, "Docstrings"); then what its kind needs:

| Kind | Further keys |
|---|---|
| `variable` | `"value"`: its value, free or bound; `"token"`: `true` for color and font variables, `false` otherwise. A token is never folded: it is written with its declared value, which the runtime draws with where the page's CSS gives none (data model, "On the page"). `"let"`, a string, on a variable the compiler made to hold a value of a `let` whose body holds declarations: the name the `let` gives it. Every attribute that reads the name reads this variable, so the value is worked out once each time what it reads changes. Such a variable is never named (`"name"` is `null`) and is not one the figure declares, so a page does not list it among the variables. |
| `scene` | `"members"`: the ids of its shapes; `"attrs"`: `background`, and `transform`, how the scene's own coordinates are drawn |
| a row or a column | kind `group`, with `"layout"`: `{"axis": "row" or "column", "gap": a real, "align": a string}`, each free or bound; the runtime moves each member after the box of the one before (reference, "Placing") |
| `namespace` | `"members"`: the ids of its members, variables and namespaces, in the order declared. Each member is an object of its own, named by the namespace: `theme.ink`, `colors.tab10.blue` |
| `formula` | `"tex"`: its LaTeX, as written, `\term{name}{…}` marking each term; `"members"`: the ids of its terms, in the order the LaTeX marks them. Its variables are objects of their own, named by the formula, as `bounds.lit` |
| `term` | `"term"`: its name in the LaTeX, `gap` for `\term{gap}{…}`; `"formula"`: its formula's id; `"attrs"`: `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding`, `exists`, each free or bound, and `tex`, its content, when its `(term …)` form gives one |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text`, `group` | `"attrs"`: every attribute, free or bound, and `exists`, a bool, when an `exists-when` names the shape (while it is false the shape is absent, and so are its members when it is a container, and every read of them is none); `group` also `"members"`, `"clip"`, the id of its clip shape, when it has one (that shape is an object of its own, in the group's frame, and not among the members), and `"fixed-size": true` when its members are measured in screen pixels (a group given `(fixed-size false)` or nothing has no such key) |
| a motif instance | kind `instance`; `"of"`: the motif's name; `"members"`; `"attrs"`: its parameters, its bound variables, and `x`, `y`, `translate` and `transform` (its `fill` and the like are its members'); `"clip"`, as for a group |
| a variant instance | the kind of its base shape (`"rect"` for a bar); `"of"`: the variant's name; `"attrs"`: its base's attributes, the fixed ones marked, then its parameters |
| `transition` | `"from"`, `"to"`, `"duration"`, `"ease"`, `"path"` (below) |
| `animation` | `"steps"`: a step (below) |
| `canvas` | `"shows"`: what it shows, in the order written, which is the order it draws them in (later ones on top): each entry the id of a shape, or an attribute, free or bound, for an item that gives a shape, none or a list of them, such as `(when show d)`; `"transition"`: an id or `null`; `"attrs"`: the view box, `transform`, `pan` and `zoom` |
| `readout` | `"attrs"`: `value` (the string), `font` |
| `display` | `"formula"`: the id of the formula it shows; `"as"`: `"block"` or `"inline"` |
| `slider`, `button`, `play`, `stepper` | `"animation"`: an id; `"labels"` (play only, and only when it has them): one string per step of its animation, the items of its body (inside a loop around the whole of it); `"rest"` (play only, and only when it has one): the seconds it pauses between each pair of steps, which the runtime adds as a wait after every step of the play's animation but the last; `"conditions"`; `"active"`: a bool, free or bound, or `null`; `"label-tex"`: `true` when the label is LaTeX, given as `(label (tex …))`, and left out otherwise; `"attrs"`: `label`, and `step` (slider: the number of positions its knob stops at), `buttons` (play), `selected` (button, only when it has one), and the attributes the reader's actions change: `position` (slider), `playing` and `step` (play and stepper: the step playing or paused, or else the highest step whose state the scene is in, from 1, and 0 in explore mode, as written) |
| `toggle` | `"target"`: `[id, attr]`, the bool variable or attribute it writes; `"animation"`: the id of the animation each flip plays after writing, or `null`; `"conditions"`; `"active"`: a bool, free or bound, or `null`; `"label-tex"`: as for a button; `"attrs"`: `label`, `value` |
| `on-drag` | `"shape"`: an id; `"target"`: `[id, attr]`; `"map"`, when the drag is written as a move: its `to`, free or bound, reading the local `pointer`, a point; `"conditions"`; `"active"`: a bool, free or bound, or `null` |
| `on-pointermove` | `"shape"`: an id or `null`; `"view"`: the canvas's id or `null`, one of the two; `"target"`: `[id, attr]`; `"conditions"`; `"active"`: a bool, free or bound, or `null`; `"stop-propagation"`: a bool, free or bound, or `null` |
| `on-click`, `on-release`, `on-dragstart`, `on-dragend` | `"shape"`: an id, of a shape or, for `on-click`, of a term; `"animation"`: an id; `"conditions"`; `"active"`: a bool, free or bound, or `null`; `"stop-propagation"`: a bool, free or bound, or `null` |
| `on-enter`, `on-leave` | `"shape"`: an id, of a shape or of a term; `"animation"`: an id; `"conditions"`; `"active"`: a bool, free or bound, or `null` |
| `on-view`, `on-rest` | `"view"`: the canvas's id; `"animation"`: an id; `"conditions"`; `"active"`: a bool, free or bound, or `null` (docs/canvas-lifecycle.md) |
| `on-live`, `on-quiet` | `"view"`: the id of the canvas, readout or display; `"animation"`: an id, or `null` when it gives none; `"conditions"`; `"active"`: a bool, free or bound, or `null`. A view with an `on-live` has a quiet mode (reference, "Quiet and live views"); every `on-quiet`'s view has an `on-live` |

A listener on a shape or a term has `"in"`: one id, that of the view whose body holds it (reference, "Listeners and controls in views"). It hears the pointer only in that view, and nothing in it while that view is quiet. A listener on its own view (`on-view`, `on-rest`, `on-live`, `on-quiet`, and an `on-pointermove` on a canvas) has no `"in"` key: its `"view"` names that view. A control whose source gives `(in view…)` has `"in"`: the ids of those views, in the order written, at least one. It belongs to those views, and one without it to none, with no `"in"` key: the runtime hides a control while all its views are quiet. An older file may have a listener on a shape with several views in `"in"`, or with no `"in"`, which the runtime reads as heard in every view that shows its shape.

A control or a listener whose source gives `(priority n)` has `"priority": n`, an int from 1 to 1000, and one without it has no `"priority"` key: the runtime gives it its kind's priority, 300 for `on-view` and `on-rest`, 700 for a gesture (`on-drag`, a slider's knob held, `on-pointermove`) and 500 for the rest (reference, "Concurrency"). Whether the reader set a writer off is not in the file: the runtime knows it from what started the writer.

A writer's `"conditions"` is a list of clamps, one per condition, already in the form the reference requires (a comparison of the variable or attribute written with a value not depending on it): `{"target": [id, attr], "op": ">=" | ">" | "<=" | "<", "limit": L}`, `L` free or bound. Before emitting a write to that target, the runtime clamps it to the limit.

Motif and variant instances are written out in full: the runtime never builds an instance itself.

### Steps

    ["move", [id, attr], transitionId, duration, ease]
    ["wait", seconds]
    ["at-once", step, …]
    ["in-order", step, …]
    ["loop", n | null, step]

A move carries its own `duration` and `ease`, resolved from the transition and the nearest enclosing default, so one named transition can be used in animations with different defaults. An animation's `"steps"` is one step; several steps written in a row in the source become one `in-order`. A `(step …)` is written as an `in-order` of its items, or as its one item when it holds one; a body that is one `(step …)` alone is an `in-order` holding that one, so that the play's steps are always the items of the top-level `in-order`, or the one step when there is none. A `(move …)` with a target, or the name of a transition, in an animation's body, is written as a move; a `(move none …)`, as a wait. A slider's move is written as an animation of one move, with duration 1, which the compiler adds. An animation with `(loop n)` or `(loop)` has a `loop` step around its body, `n` being the number of rounds, or `null` for forever; each round starts again from the start of its step, reading every move's ends again.

### Transitions

    {"from": V | null, "to": V | null, "duration": seconds | null,
     "ease": "linear" | ["step", n] | ["step-ease", p]
             | {"func": id} | null,
     "path": null | {"func": id}}

A transition is a value: it never changes. Its `from` and `to` (`V`, free or bound) can be bound only so that they can hold expressions; each is read once, when a move along the transition starts, and never followed during the move. `null` for `from` or `to` means the value of what is moved when the move starts. `"linear"` is the straight line a move with no ease takes; every other ease is a step or a function. `null` for `duration` or `ease` means the transition gives none of its own: each move along it carries the one resolved from the defaults around it. `path` `null` is the straight line between the ends.

## Functions

    {"params": [P, …], "result": T, "body": expr}

A parameter `P` is as in declared types. A function written in place reads its captured names through `["local", …]`; the `["func", …]` expression that creates it lists them.
