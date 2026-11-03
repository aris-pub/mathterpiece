# The type system

What types are for in mtp, which types there are, and how to use them, declare new ones, narrow them and broaden them.

## 1. What types are for

Every object in a world model has a type, and the compiler knows every type before the page loads (see the data model's account of objects and binding time). mtp is statically and strongly typed: a value of one type is never quietly treated as another, and anything that does not fit is a compile error.

This buys two things. Mistakes are caught when compiling, at the line that made them, instead of showing up as a broken drawing in a reader's browser. And the runtime does no type work while drawing: it never checks, converts or guesses a type, so every frame of a drag or an animation is spent on the mathematics alone. Neither depends on the author writing types everywhere; the compiler works most of them out. A type is written where it says something the compiler cannot guess.

mtp has no classes, no methods attached to types, and no inheritance. It has **refinement**: a type can be narrowed to some of its objects, and the narrower type is accepted wherever the wider one is.

## 2. The types

Objects are values, which never change, or mutable objects, which can. A type that refines another accepts only some of its objects: every `unit`, a real between 0 and 1 (section 5.b), is a real. Every circle satisfies the interface `shape` (section 6).

- **object**
  - **value** (never changes)
    - numbers: `int`, `ratio`, `real`, `complex`
    - `bool`, `string`, `color`, `font`
    - `point` (two reals, `x` and `y`)
    - `list[T]`, `transform`
    - functions (eases, paths), `transition`, `animation`
    - `name`
    - `none`
  - **mutable object** (can change)
    - **`shape`** (an interface): `circle`, `rect`, `ellipse`, `line`, `triangle`, `text`, `group`, motif instances (`dial`, …), variants; each satisfies `shape`
    - **`scene`**: holds the shapes
    - **component**
      - view: `canvas`, `readout`
      - control: `slider`, `button`, `play`, `toggle`
      - listener: `on-drag`, `on-click`

- **A name** holds a variable or an attribute without evaluating it: `k`, `p.r`, `g[1].r`, `d.c.pos`. A name is declared once and never changes, so it is always known when compiling. A transition's target is a `name|none`.
- **Numbers** come in four types: `int`, `ratio` (exact fractions such as `1/3`), `real` and `complex`.
- **A point** is its own type: two reals, read as `x` and `y` or by position, `p[0]`. **A list**, `list[T]`, holds items of one type T; like a Python tuple, the list itself never changes, though the objects it holds may.
- **Functions, transitions and animations** are values too: an ease is a function from 0..1 to a real, `func[real real]`; a path is a function of the two ends and the progress, `func[T T real T]`; a transition is a trajectory. A transition's ends may be expressions: the transition itself never changes, and its ends are read once, when a move along it starts. A function's type lists its inputs, then its result: `func[real real]` takes a real and gives a real. Its result is never written in its declaration; the compiler works it out from the body.
- **`none`** is the value that stands for one that does not exist (section 5.c).
- **Types are objects themselves**: declaring a motif or a named type creates one. They cannot yet be passed or held in a variable.

## 3. Conversions

Only two conversions ever happen without being asked for. (A list written in brackets, even of expressions such as `[k 0]`, is a literal, and takes the type expected where it is written: it is a point where a point is expected.) Separately, a narrower type is accepted where a wider one is expected without any conversion: a refinement where its base is (a `unit` where a `real` is), and any `T` where `T|none` is.

- **Numbers broaden**, never narrow: an `int` is accepted where a `ratio`, `real` or `complex` is expected, a `ratio` where a `real` or `complex` is, and a `real` where a `complex` is. Going the other way takes a function, such as `round`. (The one exception is a write while drawing into an int, which is rounded: section 5.b.)
- **A literal takes the type expected where it is written.** `'red'` is a string, but written where a color is expected it is a color; `'middle'` written as a text's alignment is one of the allowed alignments. Where nothing gives a literal its type, such as a branch of a function's `cond`, `(as color 'red')` gives it one.

&nbsp;

    (real k 1)                  ; the int 1 broadens to a real
    (circle c (fill 'red'))     ; 'red' is a color here
    (string s 'red')            ; and a string here
    (circle d (fill s))         ; an error: s is a string, and only a literal converts

## 4. Using types

A variable is declared with its type, its name, its value, then any constraints. A parameter is declared the same way, with its default as its value. (A font variable is the one exception: it is declared with items instead of a value; see the reference.)

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
    (func area (circle o) (* pi o.r o.r))            ; circles, and any variant of circle (section 5.e)

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

A constraint narrows a type to some of its values. Constraints are written after a declaration's value, or inside a narrowed type expression. A constraint is always one of: a comparison with one argument, `(length n)`, `(const)` or `(one-of …)`. None of these is a valid value, so the compiler can always tell a constraint from a value, even when the value is left out: `(real k (>= 0))` is a real with no value and a constraint.

- **Comparisons** with the value left out: `(>= 0)`, `(< 1)`. A range is two of them: `(real p 0.5 (>= 0) (<= 1))`.
- **`(length n)`** fixes a list's length.
- **`(one-of …)`** narrows a string to a few values, a choice type (section 5.d).
- **`(const)`** forbids every write, so the variable is known when compiling and costs nothing while drawing.

A value known when compiling that breaks a constraint is a compile error. A bound value that breaks one while drawing is `none` (section 5.c), so unless the compiler can prove the expression stays within the constraint, the value may be `none` and must be handled like any other `none`: the variable declared `T|none`, or the expression given a default with `or?`. A write while drawing (from a slider, a drag or an animation) is brought into the constraint: a range is **clamped** to its nearest end (a strict bound such as `(> 0)` has no nearest allowed value, so a write that breaks it is skipped), an `int` is **rounded** (after clamping, to the nearest int inside the range), and a fixed choice **holds** its last valid value. An argument passed to a constrained parameter, and an item of a list with constrained items, follow the rule for bound values: unless the compiler can prove they fit, it is a compile error. A write that changes nothing is skipped, so nothing downstream is recomputed.

    (real p 0.5 (>= 0) (<= 1))
    (slider s (move p (from 0) (to 1.4)))   ; p stops at exactly 1
    (int n 8 (const))                                   ; known when compiling: usable as a repeat count

### 5.c Broadening (none, more later)

`none` stands for a value that does not exist. For now it is the only way to broaden a type: `real|none`, or `(maybe real)`, is a real or none.

**Where it comes from.** A function where it is undefined: `(/ x 0)`, `(secd 90)`, `(tand 90)`, `(asin 2)`, `(log 0)`, `(sqrt -1)`. When the inputs are known when compiling this is a compile error; while drawing it gives `none`, never an error and never infinity. A lookup by a key known only while drawing, `g[side]`, may also give none. And an author may write `none` on purpose.

**How it behaves.** Anything computed from `none` is `none`: a function's result, a part of `none` (if `g[k]` is `none`, so is `g[k].pos`), and an interpolated string with a part that is `none` (`$'sec θ = {crossing:.3f}'` is `none` when `crossing` is). The exceptions are the forms that deal with `none` (below), equality (`(= none none)` is true, `(= none 3)` is false), and a function whose parameter is declared `T|none`: it receives `none` and runs its body. A parameter that does not accept `none` makes the call `none`. Conditions (`if`, `cond`, `and`, `or`, and the `when` item of a canvas or listener) cannot decide anything with `none`, so they must always receive a value that cannot be `none`. Of the list operations, `sum`, `count`, `min`, `max`, `any`, `all` and `reduce` must not receive items that may be `none`; `map`, `reverse` and reading a position pass them through.

**Handling it.** Everywhere a value reaches the reader must handle a `none` that may arrive there, whatever its source: a shape, a readout, a condition, an interpolated string, a list operation, a write. Handling means giving it a default with `or?`, filtering it out of a list with `somes`, or, for a shape, declaring the shape itself `T|none`. A transition whose end may be `none` is a write and must be handled too, except into a `color|none` variable or attribute, where `none` is mixed as transparent. Declaring a variable `T|none` is the author's choice that the variable may hold `none`; it does not exempt what reads it. A `none` arrives unasked when it comes from a partial function or a lookup, or anything computed from them; an unasked `none` may not even pass silently into a variable declared plain `T`. Until every `none` is handled, the compiler stops. The forms:

    (or? x d)                ; x, or d when x is none
    (none? x)  (some? x)     ; is x none, is it not
    (somes xs)               ; the items of xs that are not none
    (where g f)              ; the members of g for which the function f holds

**Shapes.** A plain shape type must always be drawable. Every attribute of a built-in shape is drawing-essential except `fill` and `stroke`. If any drawing-essential attribute may be `none`, compilation stops. Declaring the shape itself as `T|none` says it may be absent: then it is not drawn, and the shape is `none`, so whatever reads it must handle that in turn. An attribute accepts `none` only if its type says so: for built-in shapes, that is `fill` and `stroke`, typed `color|none`, where `none` means no paint. So the rule above applies to drawing-essential attributes only: `(circle c (fill x))` with `x : color|none` is a plain circle, drawn without paint when `x` is `none`.

    (real|none crossing (secd theta))
    (line tan (from p.pos) (to [crossing 0]))           ; an error: the end may be none
    (line|none tan (from p.pos) (to [crossing 0]))      ; at 90° the line is absent
    (line tan2 (from p.pos) (to [(or? crossing 0) 0]))  ; or: a stand-in end
    (readout r (or? $'sec θ = {crossing:.3f}' 'sec θ is undefined'))
    (circle ring (r 1) (fill none) (stroke 'navy'))     ; fill accepts none: an outline

    (list[real|none] radii (map g (fn p (sqrt p.k))))        ; some square roots fail
    (real mean (/ (sum (somes radii)) (count (somes radii))))

**Constraints.** A bound value that would break its constraint while drawing is `none`, like an undefined value: `(circle|none c (r (secd theta)))` is absent at 90° and wherever `secd` is negative. Constraints also let the compiler prove a value is defined: with `(real k 1 (>= 1))`, `(/ 1 k)` can never be `none`.

**What the compiler proves.** It reasons only with ranges, never anything cleverer, so every implementation accepts the same programs. A variable's range comes from its constraints (`(real k 1 (>= 0) (<= 10))` is 0 to 10). **Every number lies within ±10¹⁵⁰:** a literal beyond it is a compile error, a write beyond it is clamped to it, and a value with no limit of its own has the range −10¹⁵⁰ to 10¹⁵⁰. A computed result may go beyond that bound; only one beyond the largest real (about 1.8 × 10³⁰⁸) overflows, and an overflow is undefined, so it gives `none`. With these limits, `(* 2 k)` or `(* 360 t)` can never overflow, while a product of several unlimited values may. Each operation has a range rule. Only `+`, `-`, `*`, `/`, `^`, `abs`, `min`, `max` and `sqrt` compute their range from their inputs' ranges; every other function is taken to give its whole range whatever its input, which is its mathematical range (`sind` −1 to 1, `exp` above 0, `floor` and `round` all ints, `mod` from 0 up to its divisor, `dist` 0 and above, and so on). `if`, `cond` and `or?` give the union of their branches' ranges; a list built from expressions, and the result of `map`, give their item type the range all their items share, so `(map g (fn p (dist o p)))` is a `list[(real (>= 0))]`; a parameter, an attribute read and a recursive call give their type's range. Ends are closed unless the function never reaches them (`exp` is never 0). There is no narrowing after a test: `(if (some? x) (* 2 x) 0)` still sees `x` as possibly `none`; `(or? x 0)` is the way to handle it. This is deliberately simple, so every implementation agrees; it can be refined later. A partial function is safe when its input's range avoids every point where it is undefined (for the radian trigonometric functions, only where their result is not a number: `csc` and `cot` at exactly 0, the inverse functions outside their domain): `(/ 1 k)` when `k`'s range excludes 0, `(secd a)` when `a`'s range contains no 90 + 180n. A bound value is safe when its range lies inside its constraint. Anything else may be `none`. So `(circle c (r (* 2 k)))` with a plain `(real k 1)` is an error, because `r` may break its `(>= 0)`; declaring `k` with `(>= 0)` makes it compile. Constraints on a type that allows `none` apply to its other values; `none` itself is always allowed.

### 5.d Choice types

A choice type is a string narrowed to a fixed set of values, like an enumeration in other languages. It is declared like any other narrowing:

    (type side string (one-of 'left' 'right'))
    (type align string (one-of 'start' 'middle' 'end'))

    (side s 'left')                          ; a variable of a choice type
    (motif arrow ((side towards 'left')) ...)
    (side t 'up')                            ; an error: 'up' is not a side

A value of a choice type is still a string, so it can be shown in a readout or used in an interpolated string as is. Text alignment (`halign`, `valign`) and font style are built-in choice types. A write while drawing that is not one of the choices holds the last valid value.

Where members of different types meet (a group of circles and rects, the branches of an `if`, `g[k]`), their common type is the most specific interface all of them satisfy: for circles and rects, `positioned`, so `p.x` may be read.

**Known lengths.** A list's length is known when compiling when it comes from a literal list, a group (its `length`, the member count, which never changes: no member is ever removed, and an absent `T|none` member stays where it is as `none`), a spread such as `g.r`, `map`, `sort` or `reverse` of a list whose length is known, or a variable bound to any of these, which always equals it; a free list variable may be replaced by a move, so its length is known only with a `(length n)` constraint; `where` and `somes` give a list whose length is not known. Reading a fixed position on a list of known length is checked when compiling: it never gives `none`, and a position out of range is a compile error. A position only known while drawing never gives `none` either when its range lies within the list's positions (from -n to n - 1 on a list of length n), such as an `(int f 0 (>= 0) (<= 3))` on a list of four. Any other position known only while drawing, or a position on a list of unknown length, may give `none`.

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
      (rect_ (width 0.8) (y 0) (height (* 5 p))))
    (bar b1 (x 2) (p 0.4))
    b1.x  b1.height  b1.p                    ; all read directly
    (bar b2 (width 2))                       ; an error: a bar's width is fixed

    (variant big-dial ((real level 0.8))
      (dial_ (t level) (tint 'gold')))      ; a variant of a motif

Motifs and variants are declared at the top level, once, like named types.

## 6. Interfaces

An interface names what several types have in common. A type satisfies an interface by having what it lists, without declaring anything: this is checked by structure, as in Go, TypeScript or Python's protocols. mtp has three, built in:

| Interface | Means | Satisfied by |
|----|----|----|
| `positioned` | has real `x` and `y` | points, every shape except groups (on a group, `x` is a list) |
| `sequence[T]` | items by position, a `length` | lists, points, groups |
| `shape` | has its own `translate` and `transform` | circle, rect, …, groups, motif instances, variants |

An interface cannot be instantiated: no shape is created whose type is only `shape`. An interface can type a parameter, as in `(shape o)`, or a variable that holds an existing shape: `(shape sel p)` declares `sel`, holding the shape `p`, and `(shape sel (circle c …))` declares the circle `c` and a variable holding it. A parameter typed with an interface may read only what the interface lists, and is checked once, at the definition, like any other parameter.

    (func label-at ((positioned o) (string s)) …)   ; accepts points and shapes alike
    (func area (circle o) (* pi o.r o.r))                   ; circles, and any variant of circle
    (func area (shape o) (* pi o.r o.r))                    ; an error: not every shape has an r

Reading an attribute of a group, `g.r`, gives each member's `r`, and is allowed when every member's type has one. Authors cannot declare interfaces of their own yet.

## 7. Not yet

- Unions of types other than `none`, such as a fill that is a color or a gradient.
- Vectors: fixed-length numbers with arithmetic, separate from lists.
- Container types an author defines, such as `pair[T]`.
- Interfaces an author declares, and extra attributes on new types (which would let `point` become a refinement of `list[real]` instead of a type of its own).
- Variables that hold functions.
- Types passed or held as values.
- Maps from keys to values.
- Units and dimensional analysis, where a value with a unit would be a quantity.

## 8. Appendix: attributes by type

Every declared object has a `name` attribute, a string, or `none` for one declared with no name, `(circle none …)` or `(circle_ …)`. Other attributes, read with a dot (`c.r`) or the part form:

| Type | Attributes |
|----|----|
| complex | `re`, `im` |
| color | `r`, `g`, `b`, `a`, each from 0 to 1 |
| string | `length` |
| list | `length`; items by position, `xs[0]` |
| point | `x`, `y` |
| transition | `duration`, `from`, `to`, `ease`, `path` |
| animation | `duration` (except for one that loops forever), `steps` |
| shapes | the arguments they take (a circle's `r`, `fill`, …) and their position, `pos`, `x`, `y` |
| group | `length` (its member count), `members`; members by position or name, `g[0]`, `g['disk-3']`; any member attribute, spread over the members, `g.r` |
| scene | `background`, `length` (its member count), `members` (its shapes, not its variables); members by position or name; no spreading (`s.r` is an error) |
| motif instances | their parameters and bound variables, `a.t`, `disk.area`; their members, `a.tip`; their shape arguments, `a.x`, `a.fill`, … |
| variant instances | their parameters, and every attribute of their base, `b1.p`, `b1.x` |
| font | `family`, `style`, `weight`, `size` |
| slider | `label`, `position` (0 to 1), `step` (the number of positions its knob stops at, if given) |
| play | `label`, `step` (which item of its animation's body is now playing), `playing`, `buttons` |
| button, toggle | `label`; a toggle's `value` |
| readout | `value` (its string), `font` |
| canvas | `view-x`, `view-y`, `view-width`, `view-height`, `pan`, `zoom` |

Attributes of controls change as the reader acts. Only components and globals may read them; the scene may not.
