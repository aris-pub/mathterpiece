# Writing a world model

A quickstart: how an `.mtp` file is written, from a first complete example to the rule every form follows.

## 1. A first world model

A point on a circle, a slider and a drag that move it, and a number in the prose that follows it:

    ; a point on the unit circle at angle theta
    (scene s
      (real theta 40 (>= 0) (<= 360))
      (circle rim (r 1) (fill none) (stroke 'gray'))
      (circle p (pos (polar 1 theta)) (r 0.08) (fill 'crimson'))
      (line radius (from [0 0]) (to p.pos) (stroke 'crimson')))

    (slider spin (move theta (from 0) (to 360)) (label 'angle'))
    (on-drag p theta)

    (canvas v s)
    (readout r $'θ = {theta:.0f}°')

- `(scene s …)` declares the scene, the mathematical content. Inside it: a variable `theta`, kept between 0 and 360, and three shapes.
- `p`'s position is `(polar 1 theta)`, and `radius` ends at `p.pos`. These are not computed once: they hold at every moment, so when `theta` changes, both follow.
- `spin` is a slider. Moving it plays its animation to that point: `theta` from 0 to 360.
- `(on-drag p …)` lets the reader drag `p`, writing whatever `theta` puts it under the pointer.
- `v` draws the scene and `r` shows `theta` as text; the author places both on the page.

Everything below explains one piece of this file.

## 2. Expressions

Everything in a file is an expression: a literal, a name, or a form. Names may be followed by parts (`p.r`, `xs[0]`, section 7), and types have a notation of their own (`list[color]`, `real|none`, section 10).

### Literals

| Written | Is |
|----|----|
| `3` `-2` | whole numbers |
| `1/3` | an exact fraction |
| `2.5` `1e-3` | reals |
| `2i` | a complex number |
| `'crimson'` | a string, in single quotes |
| `$'θ = {theta:.0f}°'` | an interpolated string: each `{…}` is an expression, with an optional format after the colon |
| `true` `false` | bools |
| `none` | the value that does not exist |
| `[0 1]` `['red' 'gold']` | lists, in square brackets, items separated by spaces |

### Names

A name refers to something declared: `theta`, `p`, `show-tan`. Names are written bare, never in quotes. Letters, digits and hyphens are allowed, and some built-in names end in `?`, like `none?`. These words are reserved and cannot be used as names: `scene`, `animation`, `transition`, `move`, `in-order`, `at-once`, `when`, `else`, `true`, `false`, `none`, `const`, `self`.

### Forms

A form is a head followed by its parts, in parentheses: `(+ theta 10)`, `(circle p (r 0.08))`. The head says what the form is.

One form has a shorter spelling: a docstring, `doc@'text'`, is `(doc 'text')` (reference, "Docstrings"). `@` is allowed nowhere else, in a name or on its own.

A `;` starts a comment, which runs to the end of the line. Line breaks and indentation mean nothing; they are for reading.

## 3. Values and objects

Every expression gives an object. Some objects are **values**, which never change: `3`, `'red'`, `[0 1]`. Others are **mutable objects**, which can: a circle whose position follows `theta`, a variable a slider writes. The data model describes both.

A form either **computes** something, like the function call `(+ theta 10)`, and has no other effect, or it **declares** something, like `(circle p …)`, and its only effect is that a new object exists. Components are declarations too. A few **special forms** do neither in the ordinary way (section 6).

## 4. Declarations

A declaration creates an object and returns it. Its head is usually the type of what it creates (`real`, `circle`, `list[color]`), then its name. A few heads instead say what is being declared: `func`, `type`, `motif`, `variant`, and the components.

    (real theta 40)                       ; a variable holding a real
    (color ink 'navy')
    (circle p (r 0.08))                   ; a circle
    (group marks (circle m0) (circle m1)) ; a group holding two circles
    (func double (real x) (* 2 x))

- **Names** are bare. Each name in the scene is unique, and visible everywhere after its declaration (section 9). A function may call itself.
- **Shapes** are declared only inside the scene, a group, a motif or a variant, never at the top level.
- **`none` as a name** declares something with no name: `(circle none (r 1))`. Any form that takes a name may be written with an underscore after its head instead: `(circle_ (r 1))` is `(circle none (r 1))`, `(line|none_ …)` is `(line|none none …)`, and `(marks.grid_ …)`, a motif of a file imported whole, is `(marks.grid none …)`. An underscore is allowed nowhere else, in a name or on its own. An object with no name has a `name` attribute that is `none`.
- **`(name s)`** builds a name from a string, where it must be computed, as in a loop: `(circle (name $'dot-{i}') …)`. It also refers to such a name: `(name $'dot-{k}')`.
- **Constraints** follow, and narrow what the object may be: `(real theta 40 (>= 0) (<= 360))`.

## 5. Function calls

A call is `(function argument …)`, with the arguments in order. Built-in functions and those declared with `func` are called the same way:

    (+ theta 10)              ; some built-ins take any number of arguments: (+ a b c)
    (polar 1 theta)           ; a point at distance 1 and angle theta
    (dist p q)
    (double 4)                ; a function declared with func

A function is declared with `func`: its name, its parameters, and its body. Every parameter is typed, and may have a default, so a call may leave it out. One parameter is written alone; several, as a list; none, as `()`:

    (func double (real x) (* 2 x))
    (func hyp ((real a) (real b 0)) (sqrt (+ (* a a) (* b b))))

Its result's type is worked out from the body, or written on the head, as a list's item type is, with any constraints:

    (func[point] ahead ((real d)) [d 0])                     ; [d 0] is a point

The `func` entry in the reference, under "Declarations", says what the compiler then proves.

### Functions as arguments

A function can be passed to another, by name or written in place with `fn`, which is `func` without a name. A single parameter of `fn` may leave out its type when the function it is passed to gives that type, as `map`, `where`, `sort` and `count` do:

    (map xs double)                               ; each item doubled
    (map g (fn p (* 2 p.r)))                      ; p is a member of g
    (where g (fn p (> p.r 1)))                    ; the members whose r is over 1
    (sort g (fn p p.r))                           ; the members ordered by r
    (count g (fn p (> p.r 0)))
    (reduce g 0 (fn ((real total) (shape p)) (+ total p.r)))   ; a running value, starting at 0

A function written in place may use the names around it: in `(map g (fn p (* k p.r)))`, the result follows `k` like anything else that reads it.

A collection function's function takes its parameter's type from the items, and, when the list is known when compiling, their range too: in `(map [0 1 2 3] (fn f …))`, `f` is an int from 0 to 3. `map`'s function takes its result's type from the item type expected of the map, so in `(list[point] corners (map [0 1 2 3] (fn k [x y])))` each `[x y]` is a point.

## 6. Special forms

A special form looks like a call but does something a function cannot: it evaluates only some of its parts, binds names, or stands for other expressions. The special forms are `if`, `cond`, `and`, `or`, `let`, `fn` (section 5), `.` (section 7), `name` (section 4), `as`, `foreach` and `type-of`; the reference, "Special forms", says exactly what each evaluates and when. Two of them in use:

    (if (> k 0) 'up' 'down')                      ; evaluates only the branch taken
    (foreach i 5 (circle (name $'dot-{i}') …))    ; five circles, made when compiling

One item is recognized by its head and is not a special form: `(exists-when name c)` in a scene, group, `foreach` or motif body, which says when a shape exists (see the reference, "The scene and shapes"). `(when c x)` is a special form, an expression like `if`. In a control or a listener, `(active c)` is an optional argument.

## 7. Reading parts

A part of an object is read with a dot or with brackets.

    p.r                       ; an attribute
    p.pos.x                   ; a chain: p's pos, then its x
    xs[0]                     ; a list item by position
    xs[-1]                    ; counting from the end
    xs[(+ k 1)]               ; any expression in brackets
    g[0]  g['m1']             ; a group member by position, or by its name given as a string
    g.r                       ; on a group: each member's r

A chain of parts always starts with a name, or with a list written in brackets, which may be followed by positions only: `[a b c][h]` is item `h` of the list. A dot is always followed by an attribute name, or, on a motif instance, the name of one of its members (`d1.face`). Brackets hold a position, a member's name given as a string (used as a key), or any expression that gives one. Group members are read with brackets or by their own name, never with a dot, since a dot after a group reads an attribute of every member (`g.r`). Inside a motif instance a member has no name of its own outside it, so a member of a group inside an instance is read with brackets: in `(motif dial () (group g (circle c)))`, instance `a`'s circle is `a.g['c']`, while a member directly in the motif is `a.c`.

Inside a motif's body, `self` is the instance being built: `self.t` is its parameter `t`, and `self.face.r` its member `face`'s radius. `self` is reserved, and is an error outside a motif's body.

### Parts of what an expression gives

A chain cannot start with a form: `(sort g (fn p p.r))[0]` is not mtp. To read a part of what a form gives, use the form behind both shorthands:

    (. X Y)

`X` is any expression, and `Y` is the part: a name for an attribute, or a position, string or expression as in brackets. Every shorthand above is this form written short:

| Shorthand | Is                |
|-----------|-------------------|
| `p.r`     | `(. p r)`         |
| `xs[0]`   | `(. xs 0)`        |
| `g['m1']` | `(. g 'm1')`      |
| `p.pos.x` | `(. (. p pos) x)` |

So the form is needed only where no shorthand fits, when `X` is itself a form:

    (. (sort g (fn p p.r)) 0)     ; the member with the smallest r
    (. (polar 1 theta) x)         ; the x of a point computed in place
    (. (. (sort g (fn p p.r)) 0) pos)  ; that member's position

## 8. The form template

Every form follows one template:

    (head name? positional… option… body…)

- **The head** says what the form is.
- **The name** comes next, for a form that has one. Some forms have none: listeners (`on-drag`, `on-click`, `on-release`, `on-dragend`, `on-view`, `on-enter`, `on-leave`, `on-pointermove`), an animation written inside a control, and `move`, which writes a transition in place.
- **Positional arguments** come next, recognized by where they are. Each form fixes how many it takes, and some take none. A positional argument may be left out when the form allows it: a variable's value, as in `(real k (>= 0))`.
- **Optional arguments** come next, in any order. Each is a form recognized by its head, such as `(r 1)`, `(fill 'red')` or `(when on)`, and is given at most once.
- **The body** comes last: any number of items, or none. What it holds depends on the form: member declarations, a variable's constraints, the shapes a canvas shows, a writer's conditions, the moves of an animation.

Each form decides whether it has a name, which positional arguments it takes and which of them may be left out, which optional arguments it takes, and what its body holds. An optional argument written after the body is a compile error.

| Form | Name | Positional | Optional arguments | Body |
|----|----|----|----|----|
| `(real theta 40 (>= 0))` | `theta` | `40` | none | `(>= 0)` |
| `(circle p (r 1) (fill 'red'))` | `p` | none | `(r 1)`, `(fill 'red')` | none |
| `(text t 'hi' (pos [0 1]))` | `t` | `'hi'` | `(pos [0 1])` | none |
| `(group marks (defaults (fill 'red')) (circle m0) (circle m1))` | `marks` | none | `(defaults (fill 'red'))` | two member declarations |
| `(func double (real x) (* 2 x))` | `double` | `(real x)`, `(* 2 x)` | none | none |
| `(motif dial ((real t 0.5)) (circle face …) …)` | `dial` | its parameters, `((real t 0.5))` | none | member declarations |
| `(transition slide none (to 5) (duration 1))` | `slide` | the target, here `none` | `(to 5)`, `(duration 1)` | none |
| `(animation grow (defaults (duration 1)) (move theta (like slide)) (wait 0.5))` | `grow` | none | `(defaults (duration 1))` | a move of `theta` along `slide`, then a wait of half a second |
| `(slider spin (move theta (from 0) (to 360)) (label 'angle'))` | `spin` | the move | `(label 'angle')` | none |
| `(canvas v (x -5) a b (when show c))` | `v` | none | `(x -5)` | `a`, `b`, `(when show c)` |
| `(on-drag p theta)` | none | `p`, `theta` | none | none |

Function calls and special forms follow the template too. A call's head is the function, it has no name, and its arguments are positional, some of which may be left out, as in `(round x)` and `(round x 2)`; a function that takes any number of arguments takes them as its body, as in `(+ a b c)`. Each special form has its own positional arguments and body: `(if c a b)` has three positional arguments, and `(cond …)` a body of clauses.

## 9. Putting a file together

A file is a sequence of declarations, read in order: a name must be declared before it is used. The order is only how the file is written; the objects it declares hold all their relations at once. A typical file runs:

- **Types**: `type`, `motif` and `variant`, at the top level.
- **Globals**: functions, transitions, animations, and variables that are not part of the scene, at the top level.
- **The scene**: exactly one `(scene …)`, holding the shapes and the variables they share.
- **Components**: views (`canvas`, `readout`), controls (`slider`, `button`, `play`, `toggle`) and listeners (`on-drag`, `on-click`, `on-release`, `on-dragend`, `on-view`, `on-enter`, `on-leave`, `on-pointermove`), at the top level.

The data model shows how these relate: what reads what, and what writes what.

## 10. Types in brief

A variable's or shape's head is its type: `real`, `int`, `bool`, `string`, `color`, `point`, `list`, a shape such as `circle`, or a type the illustrator declared (section 4 lists the heads that are not types). A function's or motif's parameters always write theirs: `((real t 0.5) (color tint 'red'))`. A type can be written in place: `list[color]` is a list of colors, `real|none` (or `(maybe real)`) a real or `none`, `(real (>= 0))` a real no less than 0.

A literal takes the type expected where it is written: `'red'` is a string, but written as a fill it is a color. The type document covers all of this in full.
