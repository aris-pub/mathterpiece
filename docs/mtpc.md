# The .mtpc format

An `.mtpc` (mtp compiled) file is the static representation of one world model: what the compiler writes and the only thing the runtime reads. It is JSON, checked against `mtpc.schema.json`. This document says what each part means; the schema checks the structure, and this document adds the rules a schema cannot express.

Three rules from the other documents shape everything here:

- **The runtime never guesses a type.** Every variable, every attribute and every expression carries its type, so the runtime can turn each expression into one function specialized to its types when the file loads, and never checks or converts a type while drawing (type system, section 1).
- **The runtime recomputes only what changed.** Every bound variable or attribute lists every variable and attribute it can read (data model, "How reactivity works").
- **Everything known when compiling is already folded.** A variable or an attribute known when compiling holds a plain value, never an expression.

## Top level

    {
      "mtpc": 2,
      "types": [ … ],
      "objects": [ … ],
      "functions": [ … ],
      "names": { "theta": 3, "p": 5, "d1.face": 9, … }
    }

- **`mtpc`**: the format version, 2. (Version 1 was the old JSON format.)
- **`types`**: every type the author declared that the objects use, directly or through other types or functions: named types, motifs and variants. One nothing uses is left out.
- **`objects`**: every object in the world model (variables, shapes, transitions, animations, components). An object's **id** is its position in this list. Objects appear in the order their declarations are reached in the source, depth first: a container comes before its members, a motif instance's members follow the instance, and a transition or animation written inline as an item comes right before the object that holds it.
- **`functions`**: every function the model calls while drawing, declared with `func` or written in place with `fn`, in source order. A function only called where the compiler worked out the result, or never called, is left out. A function's id is its position in this list.
- **`names`**: each named object's name, mapped to its id, as an author or a page refers to it: `theta`, `m0` (group members are named like any scene object), `d1.face` (names inside a motif instance are written through the instance). Unnamed objects (`head_`, or `none` as the name) have no entry. The `"name"` field of an object holds its own name only: `face`, not `d1.face`.

Every reference to an object is resolved to its id. Two things stay names: a parameter or `let` name inside an expression (`["local", …]`), and a declared type (`"of": "dial"`), which is looked up in `types`.

**Same source, same bytes.** The file is UTF-8 JSON written with keys sorted, no whitespace between tokens (`,` and `:` as separators), non-ASCII characters written as themselves, and one newline at the end. Numbers are written in their shortest form that reads back exactly. Lists are in the orders given here.

## Types

Every type is written as JSON:

| Type | Written |
|---|---|
| built-in | `"int"`, `"ratio"`, `"real"`, `"complex"`, `"bool"`, `"string"`, `"color"`, `"font"`, `"point"`, `"transform"`, `"transition"`, `"animation"`, `"none"`, `"scene"` |
| a built-in shape type | `{"shape": "circle"}`, likewise `rect`, `ellipse`, `line`, `triangle`, `text`, `group` |
| a declared type | `{"named": "unit"}`, `{"named": "dial"}`, `{"named": "bar"}`: an entry of `types` |
| a component | `{"component": "slider"}`, likewise for each component |
| an interface | `{"interface": "shape"}`, `{"interface": "positioned"}`, `{"interface": "sequence", "of": T}` |
| a list | `{"list": T}` |
| a function | `{"func": [T1, T2, …], "result": T}` |
| broadened | `{"union": [T, "none"]}` |
| narrowed | `{"refine": T, "constraints": [C, …]}` |

A constraint is an array: `[">=", 0]`, `["<", 1]`, `["length", 3]`, `["one-of", ["left", "right"]]`, `["const"]`. A list's known length is always written as a `length` constraint.

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
| `color` | a string, `"#rrggbbaa"`, always in this form |
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
| `let` | `["let", T, [[name, e], …], body]` |
| `rand` | `["rand", "real", site, lo?, hi?]`, `site` numbering each copy of each `rand` after `foreach` and motif instances are expanded, starting at 0; each site draws its number once, when the page loads |

## Free and bound values

A variable's value, every attribute of a mutable object, and every condition a component reads is written free or bound:

    {"type": T, "free": value}
    {"type": T, "bound": expr, "deps": [[id, attr], …]}

with `"fixed": true` on a variant instance's fixed attributes.

- A **free** one holds its starting value. A writer may change it while drawing, unless its type has a `const` constraint, it is fixed, or its object is a token.
- A **bound** one holds an expression. `deps` lists every variable and attribute it can read: directly, through any function it calls, and through captured names. Where a read depends on a value known only while drawing, such as `g[side].pos`, `deps` lists every one it could read (the `pos` of every member). When any of them changes, this one is recomputed, and nothing else is. `[id, null]` is a variable.
- A variable or an attribute known when compiling is written as free, with a `const` constraint in its type, whether the author wrote it that way or the compiler folded it. One exception: one given a constant (the bare name of a `const` variable or of a built-in constant, or a read of a `const` attribute) is free with no `const` constraint, as if given its value.
- Every attribute of a shape is written, including those left at their default. `pos` is not: it is `x` and `y` read or written together. A line's attributes are its `from` and `to`, a triangle's its corners; their `x` and `y` are computed (the midpoint, the centroid), and a write to them is split into writes to every end or corner.

## Objects

Every object has:

    {"kind": …, "type": T, "access": "scene" | "page", "name": "theta" | null, …}

and then what its kind needs:

| Kind | Further keys |
|---|---|
| `variable` | `"value"`: its value, free or bound; `"token"`: `true` for color and font variables, `false` otherwise. A token is never folded: it effectively acts as a bound variable, bound to the page's value for its CSS property, which is not in the world model, so it is written with its declared value as the fallback. The runtime draws with it through the CSS property `--mtp-<name>` (font variables through their parts: `--mtp-<name>-family` and so on), with its own value as the fallback, so the page's CSS restyles it; colors computed from tokens are passed to the browser as CSS color mixes. A token's own value is what expressions reading its channels or comparing it see. |
| `scene` | `"members"`: the ids of its shapes; `"attrs"`: `background` |
| `circle`, `rect`, `ellipse`, `line`, `triangle`, `text`, `group` | `"attrs"`: every attribute, free or bound, and `exists`, a bool, when an `exists-when` names the shape (while it is false the shape is absent, and so are its members when it is a container, and every read of them is none); `group` also `"members"` |
| a motif instance | kind `instance`; `"of"`: the motif's name; `"members"`; `"attrs"`: its parameters, its bound variables, and `x`, `y`, `translate` and `transform` (its `fill` and the like are its members') |
| a variant instance | the kind of its base shape (`"rect"` for a bar); `"of"`: the variant's name; `"attrs"`: its base's attributes, the fixed ones marked, then its parameters |
| `transition` | `"from"`, `"to"`, `"duration"`, `"ease"`, `"path"` (below) |
| `animation` | `"steps"`: a step (below) |
| `canvas` | `"shows"`: what it shows, in the order written, which is the order it draws them in (later ones on top): each entry the id of a shape, or `[condition, [ids]]` for a `when` item, its condition a bool, free or bound; `"transition"`: an id or `null`; `"attrs"`: the view box, `transform`, `pan` and `zoom` |
| `readout` | `"attrs"`: `value` (the string), `font` |
| `slider`, `button`, `play` | `"animation"`: an id; `"autoplay"` (play only): `null`, `"load"`, or the id of the view or control whose first coming into view starts it; `"conditions"`; `"when"`: a bool, free or bound, or `null`; `"attrs"`: `label`, and `step` (slider: the number of positions its knob stops at), `buttons` (play), and the attributes the reader's actions change: `position` (slider), `playing` and `step` (play: the step now playing) |
| `toggle` | `"target"`: `[id, attr]` or `null`; `"conditions"`; `"when"`: a bool, free or bound, or `null`; `"attrs"`: `label`, `value` |
| `on-drag` | `"shape"`: an id; `"target"`: `[id, attr]`; `"conditions"`; `"when"`: a bool, free or bound, or `null` |
| `on-click`, `on-release`, `on-dragend` | `"shape"`: an id; `"animation"`: an id; `"conditions"`; `"when"`: a bool, free or bound, or `null` |
| `on-view` | `"view"`: the canvas's id; `"animation"`: an id; `"conditions"`; `"when"`: a bool, free or bound, or `null` |

A writer's `"conditions"` is a list of clamps, one per condition, already in the form the reference requires (a comparison of the variable or attribute written with a value not depending on it): `{"target": [id, attr], "op": ">=" | ">" | "<=" | "<", "limit": L}`, `L` free or bound. Before emitting a write to that target, the runtime clamps it to the limit.

Motif and variant instances are written out in full: the runtime never builds an instance itself.

### Steps

    ["move", [id, attr], transitionId, duration, ease]
    ["wait", seconds]
    ["at-once", step, …]
    ["in-order", step, …]
    ["loop", n | null, step]

A move carries its own `duration` and `ease`, resolved from the transition and the nearest enclosing default, so one named transition can be used in animations with different defaults. An animation's `"steps"` is one step; several steps written in a row in the source become one `in-order`. A `(move …)` with a target, or the name of a transition, in an animation's body, is written as a move; a `(move none …)`, as a wait. A slider's move is written as an animation of one move, with duration 1, which the compiler adds. An animation with `(loop n)` or `(loop)` has a `loop` step around its body, `n` being the number of rounds, or `null` for forever; each round starts again from the start of its step, reading every move's ends again.

### Transitions

    {"from": V | null, "to": V | null, "duration": seconds | null,
     "ease": "linear" | "ease-in" | "ease-out" | "ease-in-out" | ["step", n] | ["step-ease", p]
             | {"func": id} | null,
     "path": null | {"func": id}}

A transition is a value: it never changes. Its `from` and `to` (`V`, free or bound) can be bound only so that they can hold expressions; each is read once, when a move along the transition starts, and never followed during the move. `null` for `from` or `to` means the value of what is moved when the move starts. `null` for `duration` or `ease` means the transition gives none of its own: each move along it carries the one resolved from the defaults around it. `path` `null` is the straight line between the ends.

## Functions

    {"params": [P, …], "result": T, "body": expr}

A parameter `P` is as in declared types. A function written in place reads its captured names through `["local", …]`; the `["func", …]` expression that creates it lists them.
