# The .mtpc format

A {term}`.mtpc` file holds one {term}`world model`. It is JSON, and it must match the schema `mtpc.schema.json`. The schema checks the structure of the file. This page defines what each part of the file means, and the rules that a schema cannot express.

Three rules of other pages determine much of the format:

- **The runtime never checks a type.** In the file, every variable, every attribute and every expression has its type, so that the runtime can turn each expression into one function for its types when the file loads, and never checks or converts a type while drawing ({numref}`runtime-no-type-work-while-drawing`).
- **The runtime computes again only what depends on a change.** Every bound variable or attribute lists every variable and attribute that it can read ({numref}`runtime-builds-live-model`).
- **Every value known when compiling is folded.** A variable or an attribute whose value is known when compiling holds a value in the file, never an expression ({term}`folding`).

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

- **`mtpc`**: the version, 4 ({numref}`spec-version`).
- **`types`**: every type that the source declares and that the objects use, directly or through other types or functions: named types, motifs and variants. A declared type that nothing uses is left out.
- **`objects`**: every variable and every object of the world model: variables, shapes, `transition` and `animation` objects, and components. In this format a variable is an entry of `objects` too, so on this page "object" also means a variable. An object's **id** is its position in this list. The objects are in the order in which their declarations come in the source, depth first: a collection comes before its members, the members of a shape declared with a motif come right after that shape, and a `transition` or an `animation` written as an item in the form of another object comes right before that object.
- **`functions`**: every function that the runtime may call while drawing, declared with `func` or written with `fn`, in the order of the source. A function that is called only where the compiler folded the call, or never called, is left out. A function's id is its position in this list. A function declared with a {term}`docstring` also has the key `"doc"`.
- **`shared`**, present only when it is not empty: for each kind of shape and each attribute of that kind, the most common value of the attribute among the shapes of that kind, when at least two of them have it. The value is written here once and left out of the shapes that have it. A shape with another value has its own value written in it. A kind is a shape's `kind`, such as `circle`, or `instance:` followed by the motif's name for the shapes declared with a motif, since their attributes differ from one motif to another. A kind with one shape shares nothing. Before it reads the rest of the file, a program that reads the file must copy each value back into every shape of its kind that has no value of its own for that attribute. After that, the file is read as if every attribute were written in each shape.
- **`type-table`**, present only when it is not empty: each structured type that the file uses, written once. A structured type is a type that is not a plain name such as `"real"`. Where a structured type is the whole value of one of these keys (an object's `type`, an attribute's, the second item of an expression, a parameter's, a function's `result`, a declared type's `type` or a variant's `base`), it is written as its position in this list. A type inside another type is written out in full. A program that reads the file must put each type back in its place before it reads the rest of the file, and before it puts back the values of `shared`.
- **`names`**: the name of each named object, mapped to its id, written as an author writes it in a page: `theta`, `m0` (a member of a group is named like any other object of the scene), `d1.face` (a name in the body of a motif is written after the name of the shape declared with the motif). An object with no name (declared with a head such as `circle_`, or with `none` as its name) has no entry. The key `"name"` of an object holds its own name only: `face`, not `d1.face`.

Every reference to an object is written as the object's id. Two kinds of reference are written as names: a parameter or a `let` binding inside an expression (`["local", …]`), and a declared type (`"of": "dial"`), which is looked up in `types`.

**Same source, same bytes.** The file is UTF-8 JSON written with keys sorted, no whitespace between tokens (`,` and `:` as separators), non-ASCII characters written as themselves, and one newline at the end. Numbers are written in their shortest form that reads back exactly. Arrays are in the orders that this page states.

## Types

Every type is written as JSON:

| Type | Written |
|---|---|
| built-in | `"int"`, `"ratio"`, `"real"`, `"complex"`, `"bool"`, `"string"`, `"color"`, `"font"`, `"point"`, `"transform"`, `"transition"`, `"animation"`, `"none"`, `"scene"`, `"namespace"` (every namespace, as every circle is `{"shape": "circle"}`), `"palette"` (every palette: a namespace whose members are colors, and whose object is of kind `namespace`), `"formula"` and `"term"` (every formula and every term of a formula) |
| a built-in shape type | `{"shape": "circle"}`, and in the same way `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text`, `group` |
| a declared type | `{"named": "unit"}`, `{"named": "dial"}`, `{"named": "bar"}`: an entry of `types` |
| a component | `{"component": "slider"}`, and in the same way for each component |
| an interface | `{"interface": "shape"}`, `{"interface": "positioned"}`, `{"interface": "sequence", "of": T}` |
| a list | `{"list": T}` |
| a function | `{"func": [T1, T2, …], "result": T}` |
| a union with `none` | `{"union": [T, "none"]}` |
| a refined type | `{"refine": T, "constraints": [C, …]}` |

A constraint is an array: `[">=", 0]`, `["<", 1]`, `["length", 3]`, `["one-of", ["left", "right"]]`, `["const"]`, `["wrap", 0, 360]`. A {term}`known length` of a list is always written as a `length` constraint.

### Declared types

    {"name": "unit", "kind": "type", "type": T}
    {"name": "dial", "kind": "motif", "params": [P, …]}
    {"name": "bar", "kind": "variant", "params": [P, …], "base": T, "fixed": ["width", "y", …]}

A parameter `P` is `{"name": …, "type": T}`, with `"default": value` when it has a default. With no `"default"` key, the parameter has no default, and `"default": null` means that the default is `none`. A variant's `base` is the shape type that the variant refines, and `fixed` lists the attributes that the body of the variant sets. A shape declared with the variant may not set them, and a writer may not write them.

## Values

A value is written as plain JSON, and is read by its type, which is always written with it:

| Type | Written |
|---|---|
| `int`, `real` | a number |
| `ratio` | `[numerator, denominator]`, in lowest terms |
| `complex` | `[re, im]` |
| `bool` | `true`, `false` |
| `string`, a choice type | a string |
| `color` | a string, `"#rrggbbaa"`, always in this form. A color with a different value in dark mode ({doc}`world-model`) is the CSS `"light-dark(#rrggbbaa, #rrggbbaa)"`, always in this form, with one space after the comma, and only when the two values differ. The runtime passes it to the browser as written, so the browser chooses one of the two values by the `color-scheme` of the place where the color is drawn. In a mix of such colors, the light values and the dark values are mixed separately |
| `font` | `{"family": …, "style": …, "weight": …, "size": …}`, with `family` `null` for the font of the page |
| `point` | `[x, y]` |
| `list[T]` | an array of values of type T |
| `transform` | `[a, b, c, d, e, f]`, the affine matrix |
| `none` | `null` |
| an object (a shape, a transition, an animation, …) | `{"ref": id}` |
| a function | `{"func": id}` for one in `functions`, `{"builtin": "sqrt"}` for a built-in |

## Expressions

An expression is written as an array: its operation first, then its type, then its parts. The `frame` of a read is the id of the innermost collection, or shape declared with a motif, that holds the expression (`null` at the top level and directly in the scene), or `"caller"` inside the body of a function. With `"caller"`, the frame is the frame of the expression that calls the function, and the runtime passes it with each call. The runtime converts the value that it reads through every `translate` and `transform` that applies to the shape that is read but not to that frame ({doc}`data-model`), and the `deps` include those `translate` and `transform` attributes. The types written here are the types that the compiler proved: a result that may be `none` has a type `{"union": [T, "none"]}`, and the runtime checks for `none` nowhere else.

| Expression | Written |
|---|---|
| a literal | `["lit", T, value]` |
| a list or a point made from expressions | `["list", T, e…]` |
| an interpolated string | `["format", T, part…]`, with `T` either `"string"`, or `{"union": ["string", "none"]}` when a part may be `none`. Each part is a string, or `[e, spec]`, with `spec` the {term}`format spec` (`""` when there is none) |
| a variable | `["read", T, id, null, frame]` |
| an attribute | `["read", T, id, attr, frame]` |
| an object itself (a group passed to `map`, a shape read as a value) | `["obj", T, id]` |
| a value brought into an interval | `["wrap", T, e, lo, hi]`: the value of `e` brought into [`lo`, `hi`), or `none` when `e` evaluates to `none`. The compiler writes it wherever a value that may lie outside the interval is written into a type with a `wrap` constraint |
| a value checked against constraints | `["check", T, e, [C, …]]`: the value of `e`, or `none` when that value does not meet one of the constraints. The compiler writes it wherever it cannot prove the constraint of a bound value ({numref}`constraint-proof`), so `T` always includes `none` |
| a parameter or a `let` binding | `["local", T, name]` |
| a built-in function or an operator | `["builtin", T, name, arg…]`, with `name` its name in {doc}`stdlib`: `"sind"`, `"+"`, `"or?"`, … |
| a function from `functions` | `["call", T, functionId, arg…]`, always with every argument: the compiler fills in the defaults |
| a call through a function value | `["apply", T, e, arg…]` |
| a function as a value | `["func", T, functionId, [captured name…]]` for one in `functions`, or `["builtinfunc", T, name]`. For a function written with `fn`, the captured names are the names from around the function that its body reads |
| a part | `["part", T, e, key]`, with `key` an attribute name (a string) or an expression for a position or for the name of a member |
| an attribute of every member of a group | `["spread", T, e, attr]`, which evaluates to a list |
| `if` | `["if", T, c, a, b]` |
| `cond` | `["cond", T, [[c, v], …], else]` |
| `and`, `or` | `["and", "bool", e…]`, `["or", "bool", e…]` |
| `let` | `["let", T, [[name, e], …], body]`: the runtime evaluates each `e` once, in order, then the body. The compiler writes a `let` only for values that are known only while drawing and are not shapes, and adds a `#` and a number to each name, so that no two `let` names in one expression are the same |
| a point on a shape's box | `["anchor", T, side, e, gap, frame]`, with `side` one of the eight names (`"top"`, `"top-right"`, …), `e` the shape, `gap` an expression, and `frame` as in a read |
| `rand`, `rand-int`, `pick`, `shuffle` | `[op, T, site, seed, arg…]`: `site` is the {term}`site` of the call ({numref}`random-site`), and `seed` is the expression of the seed that the call uses, a read of a variable of type `rand-seed`. The arguments are `lo` and `hi` (optional for `rand`, and required for `rand-int`) or the list (`pick`, `shuffle`). The runtime computes the value from the value of the seed, the site and, for `shuffle`, the position of each item, by {numref}`random-values`. `next-seed` is written as a built-in, `["builtin", T, "next-seed", seed]` |

## Free and bound containers

A variable, each attribute of an object, and each value that a component reads (such as its `"active"` and the limit of a guard) are written in one of these forms:

    {"type": T, "free": value}
    {"type": T, "bound": expr, "deps": [[id, attr], …]}
    {"type": T, "start": expr, "deps": [[id, attr], …]}

An attribute that a variant fixes has `"fixed": true` in each shape of that variant. An attribute of a shape declared with a motif that comes from a variable of the motif's body has `"doc"`, a string, when that variable has a docstring.

- A **free** one holds its starting value. A writer may write it while drawing, unless its type has a `const` constraint, it is fixed, or it is a token.
- A **started** one, written `free@expr` or `(free expr)` in the source, is free, and its starting value is the value of `expr`, which the runtime evaluates once, when it builds the {term}`live model`, and never again. `deps` lists what `expr` reads, as for a bound one. After that, it is free like any other.
- A **bound** one holds an expression. `deps` lists every variable and attribute that the expression can read: directly, through any function that it calls, and through captured names. Where a read depends on a value known only while drawing, such as `g[side].pos`, `deps` lists every container that the read may read (the `pos` of every member). The runtime computes a bound container again only when a container in its `deps` changes. `[id, null]` in `deps` is a variable.
- A variable or an attribute whose value is known when compiling is written as free, with a `const` constraint in its type, whether the source declares it const or the compiler folded its expression. The one exception is a variable or an attribute whose expression is the name of a `const` variable or of a built-in constant, or a read of a `const` attribute: it is written as free with no `const` constraint, as if its expression were its value.
- Every attribute of a shape is written, also when it has its default value, in the shape or, when the value is the most common one among the shapes of its kind, once in `shared` (see "Top level"). `pos` is not written: it is `x` and `y`, read or written together. The attributes of a line are its `from` and `to`, of a triangle its corners, of a polyline and of a polygon its `points`, and of a curve its `from`, `to` and `controls`. Their `x` and `y` are computed (the midpoint, the centroid, the mean of the points, the mean of a curve's ends and controls), and a write to them becomes writes to every end or corner, or moves every point.

## Objects

Every object has these keys:

    {"kind": …, "type": T, "access": "scene" | "page", "name": "theta" | null, …}

It also has `"doc"`, a string, when its declaration has a docstring ({numref}`docstrings`), and the keys of its kind:

| Kind | Further keys |
|---|---|
| `variable` | `"value"`: its value, free, started or bound. `"token"`: `true` for color and font variables, `false` otherwise. A token is never folded: the file holds its declared value, which the runtime uses where the CSS of the page sets none ({numref}`compiler-never-acts-while-drawing`). `"let"`, a string, on a variable that the compiler makes to hold the value of a binding of a `let` whose body holds declarations: the name of that binding. Every attribute that reads the name reads this variable, so the runtime computes the value once each time a container that it reads changes. Such a variable has no name (`"name"` is `null`), and the source does not declare it, so it is not listed among the variables of the world model |
| `scene` | `"members"`: the ids of its shapes. `"attrs"`: `background`, and `transform`, which sets how the runtime draws the coordinates of the scene |
| a row or a column | kind `group`, with `"layout"`: `{"axis": "row" or "column", "gap": a real, "align": a string}`, each free or bound. The runtime places each member after the box of the member before it |
| `namespace` | `"members"`: the ids of its members, variables and namespaces, in the order in which they are declared. Each member is an object of its own, named through the namespace: `theme.ink`, `colors.tab10.blue` |
| `formula` | `"tex"`: its LaTeX, as written, with `\term{name}{…}` around each term. `"members"`: the ids of its terms, in the order of the LaTeX. Its variables are objects of their own, named through the formula, as `bounds.lit` |
| `term` | `"term"`: its name in the LaTeX, `gap` for `\term{gap}{…}`. `"formula"`: the id of its formula. `"attrs"`: `fill`, `opacity`, `background`, `outline`, `outline-width`, `padding`, `rounding`, `exists`, each free or bound, and `tex`, its content, when its `(term …)` form has one |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `polyline`, `polygon`, `curve`, `arc`, `ring`, `text`, `group` | `"attrs"`: every attribute, free or bound, and `exists`, a bool, when an `exists-when` holds the name of the shape. While `exists` is false, the shape is absent, and so are its members when it is a group, and every read of them evaluates to `none`. A `group` also has `"members"`, `"clip"`, the id of its clip shape when it has one (that shape is an object of its own, in the group's frame, and not one of the members), and `"fixed-size": true` when its members are measured in screen pixels (a group with `(fixed-size false)` or with no `fixed-size` has no such key) |
| a shape declared with a motif | kind `instance`. `"of"`: the motif's name. `"members"`. `"attrs"`: its parameters, its bound variables, and `x`, `y`, `translate` and `transform` (attributes such as `fill` belong to its members). `"clip"`, as for a group |
| a shape declared with a variant | the kind of its base shape (`"rect"` for a bar). `"of"`: the variant's name. `"attrs"`: the attributes of its base, with the fixed ones marked, then its parameters |
| `transition` | `"from"`, `"to"`, `"duration"`, `"ease"`, `"path"` (see "Transitions" below) |
| `animation` | `"steps"`: one step (see "Steps" below) |
| `canvas` | `"shows"`: the items of its body, in the order written, which is the order in which the runtime draws them (later ones on top). Each entry is the id of a shape, or an attribute, free or bound, for an item that evaluates to a shape, `none` or a list of shapes, such as `(when show d)`. `"transition"`: an id or `null`. `"attrs"`: `x`, `y`, `width`, `height`, `transform`, `pan` and `zoom`. A canvas with none of `x`, `y`, `width` and `height` ({numref}`canvas-view-box`) has `"fit": true` ({numref}`canvas-fit`), and no `x`, `y`, `width` or `height` in its `"attrs"`, nor in `shared` for its kind. A canvas with all four has no `"fit"` key |
| `readout` | `"attrs"`: `value` (the string), `font` |
| `display` | `"formula"`: the id of its formula. `"as"`: `"block"` or `"inline"` |
| `slider`, `button`, `play`, `stepper` | `"animation"`: an id. `"labels"` (play only, and only when it has labels): one string for each step of its animation, that is, for each item of its body (inside a loop around the whole body, if there is one). `"rest"` (play only, and only when it has one): the seconds of the pause between two steps, which the runtime adds as a wait after every step of the play's animation except the last. `"conditions"`. `"active"`: a bool, free or bound, or `null`. `"label-tex"`: `true` when the label is a {term}`TeX string`, `(label $'…')`, and left out otherwise. `"canvases"`, only when there are some: the ids of the canvases that the control belongs to, which are the canvases that draw a shape that depends on a value that the control writes. Each of them must be ready before the reader may use the control ({doc}`lifecycle`). `"attrs"`: `label`, and `stops` (slider: the number of positions at which its knob stops), `buttons` (play), `selected` (button, only when it has one), and the attributes that the reader's actions write: `position` (slider), `playing` and `step` (play and stepper: the step that is playing or paused, or else the highest step whose state the scene is in, counted from 1, and 0 in explore mode) |
| `toggle` | `"target"`: `[id, attr]`, the bool variable or attribute that it writes. `"animation"`: the id of the animation that the runtime plays after each flip, or `null`. `"conditions"`. `"active"`: a bool, free or bound, or `null`. `"label-tex"`: as for a button. `"canvases"`: as for a button. `"attrs"`: `label`, `value` |
| `on-drag` | `"shape"`: an id. `"target"`: `[id, attr]`. `"map"`, when the drag is written with a move: the `to` of the move, free or bound, which reads the local name `pointer`, a point. `"conditions"`. `"active"`: a bool, free or bound, or `null` |
| `on-pointermove` | `"shape"`: an id or `null`. `"view"`: the id of the canvas, or `null`. Exactly one of the two is not `null`. `"target"`: `[id, attr]`. `"conditions"`. `"active"`: a bool, free or bound, or `null`. `"stop-propagation"`: a bool, free or bound, or `null` |
| `on-click`, `on-release`, `on-dragstart`, `on-dragend` | `"shape"`: an id, of a shape or, for `on-click`, of a term. `"animation"`: an id. `"conditions"`. `"active"`: a bool, free or bound, or `null`. `"stop-propagation"`: a bool, free or bound, or `null` |
| `on-enter`, `on-leave` | `"shape"`: an id, of a shape or of a term. `"animation"`: an id. `"conditions"`. `"active"`: a bool, free or bound, or `null` |
| `on-show`, `on-hide` | `"shape"`: the id of a shape, of a group or of a shape declared with a motif. For a group or a shape declared with a motif, the runtime plays the listener for each of its shapes that has no listener of the same kind of its own. `"animation"`: an id. Its moves write only the stand-in of the shape, which the runtime draws in the canvas of `"in"` ({numref}`runtime-adds-no-objects`). No `"active"`, `"conditions"` or `"priority"` |
| `on-view`, `on-ready` | `"view"`: the id of the canvas. `"animation"`: an id. `"conditions"`. `"active"`: a bool, free or bound, or `null` ({doc}`lifecycle`) |
| `on-live`, `on-quiet` | `"view"`: the id of the canvas, readout or display. `"animation"`: an id, or `null` when the listener has no movement. `"conditions"`. `"active"`: a bool, free or bound, or `null`. A view with an `on-live` has a quiet mode ({doc}`lifecycle`). The view of every `on-quiet` also has an `on-live` |

A listener on a shape or a term has `"in"`: the id of the view whose body holds the listener ({numref}`listeners-in-views`). The runtime triggers the listener only for what the reader does in that view, and not at all while that view is quiet. A listener on its own view (`on-view`, `on-ready`, `on-live`, `on-quiet`, and an `on-pointermove` on a canvas) has no `"in"` key: its `"view"` is the id of that view. A control whose source has `(in V…)` has `"in"`: the ids of those views, in the order written, at least one. The control belongs to those views. A control with no `(in …)` belongs to no view and has no `"in"` key. The runtime hides a control while all of its views are quiet. An older file may have a listener on a shape with several views in `"in"`, or with no `"in"`. The runtime then triggers the listener in every view that draws its shape.

A control or a listener whose source has `(priority n)` has `"priority": n`, an int from 1 to 1000. One with no `(priority …)` has no `"priority"` key, and the runtime uses the priority of its kind: 1000 for `on-view`, 300 for `on-ready`, 700 for a gesture (`on-drag`, a slider's knob held, `on-pointermove`) and 500 for the rest ({doc}`concurrency`). Whether the reader started a writer is not written in the file: the runtime finds this out from what started the writer.

The `"conditions"` of a writer is a list of clamps, one for each guard of the writer, each in the form that {numref}`writer-guards` requires (a comparison of the variable or attribute that the writer writes with a limit that does not depend on it): `{"target": [id, attr], "op": ">=" | ">" | "<=" | "<", "limit": L}`, with `L` free or bound. Before the runtime makes a write to that target, it clamps the value to the limit.

Shapes declared with a motif or a variant are written out in full: the runtime never builds such a shape itself.

### Steps

    ["move", [id, attr], transitionId, duration, ease]
    ["wait", seconds]
    ["at-once", step, …]
    ["in-order", step, …]
    ["loop", n | null, step]

A move has its own `duration` and `ease`, which the compiler works out from the `transition` and the nearest default around the move, so one named `transition` may be used in animations with different defaults. The `"steps"` of an animation is one step. Several steps written one after another in the source are written as one `in-order`. The steps of a play are the items of the top-level `in-order` (inside a `loop` around the whole body, if there is one), or the one step when there is no such `in-order`. A `(move …)` with a target, or the name of a `transition`, in the body of an animation is written as a move, and a `(move none …)` as a wait. The move of a slider is written as an animation of one move, with duration 1, which the compiler adds. An animation with `(loop n)` or `(loop)` has a `loop` step around its body, with `n` the number of rounds, or `null` for no end. Each round starts again from the start of its step, and the runtime reads the ends of every move again.

### Transitions

    {"from": V | null, "to": V | null, "duration": seconds | null,
     "ease": "linear" | ["step", n] | ["step-ease", p]
             | {"func": id} | null,
     "path": null | {"func": id}}

A `transition` is a value: it never changes. Its `from` and `to` (`V`, free or bound) may be bound only so that they can hold expressions. The runtime reads each of them once, when a move along the `transition` starts, and does not update it during the move. `null` for `from` or `to` means the value of the moved container when the move starts. `"linear"` is the ease of a move that has no ease of its own, and every other ease is a step or a function. `null` for `duration` or `ease` means that the `transition` has none of its own: each move along it has the one that the compiler works out from the defaults around it. A `path` of `null` is the straight line between the ends.

## Functions

    {"params": [P, …], "result": T, "body": expr}

A parameter `P` is written as in declared types. A function written with `fn` reads its captured names through `["local", …]`, and the `["func", …]` expression that creates it lists them.
