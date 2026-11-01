# The type system

What types are for in mtp, which types there are, and how to use them, declare new ones, narrow them and broaden them.

## 1. What types are for

Every object in a world model has a type, and the compiler knows every type before the page loads (see the data model's account of objects and binding time). mtp is statically and strongly typed: a value of one type is never quietly treated as another, and anything that does not fit is a compile error.

This buys two things. Mistakes are caught when compiling, at the line that made them, instead of showing up as a broken drawing in a reader's browser. And the runtime does no type work while drawing: it never checks, converts or guesses a type, so every frame of a drag or an animation is spent on the mathematics alone. Neither depends on the author writing types everywhere; the compiler works most of them out. A type is written where it says something the compiler cannot guess.

mtp has no classes, no objects with methods, and no inheritance. It has **refinement**: a type can be narrowed to some of its objects, and the narrower type is accepted wherever the wider one is.

## 2. The types

Objects are values, which never change, or mutable objects, which can. A type that refines another accepts only some of its objects: every circle is a shape.

- **object**
  - **value** (never changes)
    - numbers: `int`, `ratio`, `real`, `complex`
    - `bool`, `string`, `color`, `font`
    - `point` (a list of two reals)
    - `list[T]`, `transform`
    - functions (eases, paths), `transition`, `animation`
    - `none`
  - **mutable object** (can change)
    - **`shape`** (an interface): `circle`, `rect`, `ellipse`, `line`, `triangle`, `text`, `group`, motif instances (`dial`, …), variants; each refines `shape`
    - **`scene`**: holds the shapes
    - **component**
      - view: `canvas`, `readout`
      - control: `slider`, `button`, `play`, `toggle`
      - listener: `on-drag`, `on-click`

- **Numbers** come in four types: `int`, `ratio` (exact fractions such as `1/3`), `real` and `complex`.
- **A point** is a list of two reals. **A list**, `list[T]`, holds items of one type T; like a Python tuple, the list itself never changes, though the objects it holds may.
- **Functions, transitions and animations** are values too: an ease is a function from 0..1 to a real; a transition is a trajectory. A function's type lists its inputs, then its result: `func[real real]` takes a real and gives a real. Its result is never written in its declaration; the compiler works it out from the body.
- **`none`** is the value that stands for one that does not exist (section 5.c).
- **Types are objects themselves**: declaring a motif or a named type creates one. They cannot yet be passed or held in a variable.

## 3. Conversions

Only two conversions ever happen without being asked for.

- **Numbers broaden**, never narrow: an `int` is accepted where a `ratio`, `real` or `complex` is expected, a `ratio` where a `real` or `complex` is, and a `real` where a `complex` is. Going the other way takes a function, such as `round`.
- **A literal takes the type of its place.** `'red'` is a string, but written where a color is expected it is a color; `'middle'` written as a text's alignment is one of the allowed alignments.

&nbsp;

    (real k 1)                  ; the int 1 broadens to a real
    (circle c (fill 'red'))     ; 'red' is a color here
    (string s 'red')            ; and a string here
    (circle d (fill s))         ; an error: s is a string, and only a literal converts

## 4. Using types

Every declaration has the same shape: the type, the name, the value, then any constraints. A variable and a parameter are declared alike.

    (real theta 40)                         ; a real variable
    (color ink 'navy')                      ; a color variable
    (bool show-tan false)
    (list xs [1 2 3])                       ; the item type is worked out: list[int]
    (list palette ['red' 'gold'])           ; list[string]: these are strings
    (list[color] palette ['red' 'gold'])    ; list[color]: the literals become colors
    (list[real] samples [])                 ; an empty list: say what it will hold
    (circle c (r 1))                        ; creates an object of type circle

Parameters of functions and motifs always write their type, and may give a default:

    (func double (real x) (* 2 x))
    (motif dial ((real t 0.5) (color tint 'red'))
      (circle face (r 1) (fill tint)))
    (func area (circle o) (* pi o.r o.r))            ; circles, and any variant of circle (section 6)

A small, complete use: a bar chart whose bars are declared with typed parameters.

    (type prob real (>= 0) (<= 1))
    (list[prob] probs [0.2 0.5 0.3] (length 3))
    (motif bar ((prob p 0.0) (int k 0))
      (rect col (pos [k 0]) (width 0.8) (height (* 5 p)))
      (text label $'{p:.0%}' (pos [k (+ (* 5 p) 0.3)])))

## 5. Declaring new types

### 5.a Basic examples

There are three ways to make a type out of others: narrow it with constraints, broaden it with `none`, or build a container around it. Any of them can be named with `type`. Shapes have their own forms for the same three (section 5.e).

    (type unit real (>= 0) (<= 1))          ; narrowing: reals from 0 to 1
    (type crossing real|none)               ; broadening: a real, or none
    (type units list[unit])                 ; a container of a named type

    (unit progress 0.3)                     ; a named type heads a declaration like any other
    (motif dial ((unit t 0.5)) ...)  ; a motif declares the shape type dial

A type can also be written in place, as a **type expression**, anywhere a type goes:

    list[real]                              ; a container
    list[list[real]]
    (real (>= 0) (<= 1))                    ; a narrowed type
    real|none                               ; a broadened type, with the bar
    (maybe real)                            ; the same, as a form
    list[(real (>= 0) (<= 1))]              ; narrowed items
    list[real|none]                         ; items that may be none
    list[real]|none                         ; a whole list, or none
    func[real real]                         ; a function from a real to a real
    func[real shape real]                   ; two inputs; the last type is the result

A function type is written only for a parameter that takes a function:

    (func twice ((func[real real] f) (real x)) (f (f x)))
    (twice double 3)                        ; 12

### 5.b Narrowing (constraints)

A constraint narrows a type to some of its values. Constraints are written after a declaration's value, or inside a narrowed type expression.

- **Comparisons** with the value left out: `(>= 0)`, `(< 1)`. A range is two of them: `(real p 0.5 (>= 0) (<= 1))`.
- **`(length n)`** fixes a list's length.
- **`(one-of …)`** narrows a string to a few values, a choice type (section 5.d).
- **`(const)`** forbids every write, so the variable is known when compiling and costs nothing while drawing.

A value known when compiling that breaks a constraint is a compile error, and a bound value that breaks one while drawing is `none` (section 5.c). A write while drawing (from a slider, a drag or an animation) is brought into the constraint: a range is **clamped** to its nearest end, an `int` is **rounded**, and a fixed choice **holds** its last valid value. A write that changes nothing is skipped, so nothing downstream is recomputed.

    (real p 0.5 (>= 0) (<= 1))
    (slider s (animation (p (transition (to 1.4)))))   ; p stops at exactly 1
    (int n 8 (const))                                   ; known when compiling: usable as a repeat count

### 5.c Broadening (none, more later)

`none` stands for a value that does not exist. For now it is the only way to broaden a type: `real|none`, or `(maybe real)`, is a real or none.

**Where it comes from.** A function where it is undefined: `(/ x 0)`, `(sec 90)`, `(tan 90)`, `(asin 2)`, `(log 0)`, `(sqrt -1)` on a real. When the inputs are known when compiling this is a compile error; while drawing it gives `none`, never an error and never infinity. A lookup by a key known only while drawing, `g[side]`, may also give none. And an author may write `none` on purpose.

**How it behaves.** Anything computed from `none` is `none`. `(= none none)` is true; so is a part of `none`: if `g[k]` is `none`, so is `g[k].pos`.

**Handling it.** A `none` that can arrive unasked must be handled wherever it reaches the reader: a shape, a readout, a condition, a list operation, a write. Until it is, the compiler stops. The forms:

    (or? x d)                ; x, or d when x is none
    (none? x)  (some? x)     ; is x none, is it not
    (somes xs)               ; the items of xs that are not none
    (where g f)              ; the members of g for which the function f holds

**Shapes.** A plain shape type must always be drawable. If any of its drawing-essential attributes may be `none`, compilation stops. Declaring the shape itself as `T|none` says it may be absent: then it is not drawn, and the shape is `none`, so whatever reads it must handle that in turn. An attribute accepts `none` only if its type says so: for built-in shapes, that is `fill` and `stroke`, typed `color|none`, where `none` means no paint.

    (real|none crossing (sec theta))
    (line tan (from p.pos) (to [crossing 0]))           ; an error: the end may be none
    (line|none tan (from p.pos) (to [crossing 0]))      ; at 90° the line is absent
    (line tan2 (from p.pos) (to [(or? crossing 0) 0]))  ; or: a stand-in end
    (readout r (or? $'sec θ = {crossing:.3f}' 'sec θ is undefined'))
    (circle ring (r 1) (fill none) (stroke 'navy'))     ; fill accepts none: an outline

    (list[real|none] radii (map g (fn p (sqrt p.k))))        ; some square roots fail
    (real mean (/ (sum (somes radii)) (count (somes radii))))

**Constraints.** A bound value that would break its constraint while drawing is `none`, like an undefined value: `(circle|none c (r (sec theta)))` is absent at 90° and wherever `sec` is negative. Constraints also let the compiler prove a value is defined: with `(real k 1 (>= 1))`, `(/ 1 k)` can never be `none`. Constraints on a type that allows `none` apply to its other values; `none` itself is always allowed.

### 5.d Choice types

A choice type is a string narrowed to a fixed set of values, like an enumeration in other languages. It is declared like any other narrowing:

    (type side string (one-of 'left' 'right'))
    (type align string (one-of 'start' 'middle' 'end'))

    (side s 'left')                          ; a variable of a choice type
    (motif arrow ((side towards 'left')) ...)
    (side t 'up')                            ; an error: 'up' is not a side

A value of a choice type is still a string, so it can be shown in a readout or used in an interpolated string as is. Text alignment and font style are built-in choice types. A write while drawing that is not one of the choices holds the last valid value.

Choices also make lookups safe: when every choice is a key of a group, a lookup with a value of that type can never miss, so it is never `none`.

    (group arms (line left ...) (line right ...))
    arms[s].pos                              ; s is a side, and every side is a key

### 5.e New types of shape

Shapes get the same three mechanisms as values, with forms of their own.

|  | Values | Shapes |
|----|----|----|
| Containers | `list[T]` | `group` (one container), `motif` (a type of container) |
| Refinement | constraints | `variant` |
| Broadening | `T\|none` | `circle\|none`, the same rule |

**A group** is a single shape that holds other shapes. It declares no new type: each group is written out once, where it is.

    (group marks (circle m0 (pos [0 0])) (circle m1 (pos [1 0])))
    marks[0]  marks['m1']  marks.r            ; members by position or key; marks.r spreads over them

**A motif** declares a type of shape made of several shapes, with parameters each instance sets, so the same container can be created many times. Its members are reached through the instance.

    (motif dial ((real t 0.5) (color tint 'red'))
      (circle face (r 1) (fill tint))
      (line hand (to (polar 1 (* 360 t)))))
    (dial d1 (t 0.2))
    d1.t  d1.face.r

**A variant** declares a type of shape that refines exactly one existing shape type: a built-in shape, a motif or another variant. Its body is a single shape of that type with some attributes set. Those are fixed: an instance cannot change them, which is what makes every bar a rect of width 0.8 and not just any rect. The rest are set by the instance. The base's attributes pass through, so a bar is read like a rect, and a bar is accepted wherever a rect is.

    (variant bar ((prob p 0))
      (rect _ (width 0.8) (y 0) (height (* 5 p))))
    (bar b1 (x 2) (p 0.4))
    b1.x  b1.height  b1.p                    ; all read directly
    (bar b2 (width 2))                       ; an error: a bar's width is fixed

    (variant big-dial ((real level 0.8))
      (dial _ (t level) (tint 'gold')))      ; a variant of a motif

Motifs and variants are declared at the top level, once, like named types.

## 6. Interfaces

An interface names what several types have in common. A type satisfies an interface by having what it lists, without declaring anything: this is checked by structure, as in Go, TypeScript or Python's protocols. mtp has three, built in:

| Interface | Means | Satisfied by |
|----|----|----|
| `positioned` | has real `x` and `y` | points, every shape |
| `sequence[T]` | items by position, a `length` | lists, points, groups |
| `shape` | positioned, and drawable by the backend | circle, rect, …, groups, motif instances, variants |

There is no `(shape s …)`: an interface has no instances of its own, only types that satisfy it. A parameter typed with an interface may read only what the interface lists, and is checked once, at the definition, like any other parameter.

    (func label-at ((positioned o) (string s)) …)   ; accepts points and shapes alike
    (func area (circle o) (* pi o.r o.r))                   ; circles, and any variant of circle
    (func area (shape o) (* pi o.r o.r))                    ; an error: not every shape has an r

Reading an attribute of a group, `g.r`, gives each member's `r`, and is allowed when every member's type has one. Authors cannot declare interfaces of their own yet.

## 7. Not yet

- Unions of types other than `none`, such as a fill that is a color or a gradient.
- Vectors: fixed-length numbers with arithmetic, separate from lists.
- Container types an author defines, such as `pair[T]`.
- Interfaces an author declares, and extra attributes on new types (which would let a point be a list with `x` and `y`).
- Variables that hold functions.
- Types passed or held as values.
- Maps from keys to values.
- Units and dimensional analysis, where a value with a unit would be a quantity.

## 8. Appendix: attributes by type

Every object has a `name`. Other attributes, read with a dot (`c.r`) or the part form:

| Type | Attributes |
|----|----|
| complex | `re`, `im` |
| color | `r`, `g`, `b`, `a`, each from 0 to 1 |
| string | `length` |
| list | `length`; items by position, `xs[0]` |
| point | `x`, `y` |
| transition | `duration`, `from`, `to` |
| animation | `duration`, `steps` |
| shapes | their parameters (a circle's `r`, `fill`, …) and their position, `pos`, `x`, `y` |
| group, scene | `count`, `members`; members by position or key, `g[0]`, `g['disk-3']`; any member attribute, spread over the members, `g.r` |
| motif instances | their parameters and bound variables, `a.t`, `disk.area`; their members, `a.tip` |
| font | `family`, `style`, `weight`, `size` |
| slider | `label`, `position` (0 to 1) |
| play | `label`, `step`, `playing` |
| button, toggle | `label`; a toggle's `value` |
| canvas | its view box |

Attributes of controls change as the reader acts. Only the page may read them; the scene may not.
