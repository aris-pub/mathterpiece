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

    (slider spin (label 'angle')
      (animation (theta (transition (from 0) (to 360)))))
    (on-drag p (target theta))

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

A name refers to something declared: `theta`, `p`, `show-tan`. Names are written bare, never in quotes. Letters, digits and hyphens are allowed, and some built-in names end in `?`, like `none?`. These words are reserved and cannot be used as names: `scene`, `animation`, `transition`, `wait`, `in-order`, `at-once`, `when`, `else`, `true`, `false`, `none`, `const`, `self`.

### Forms

A form is a head followed by its parts, in parentheses: `(+ theta 10)`, `(circle p (r 0.08))`. The head says what the form is.

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
- **`_`** declares something with no name: `(circle _ (r 1))`.
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

### Functions as arguments

A function can be passed to another, by name or written in place with `fn`, which is `func` without a name. A single parameter of `fn` may leave out its type when the place gives it:

    (map xs double)                               ; each item doubled
    (map g (fn p (* 2 p.r)))                      ; p is a member of g
    (where g (fn p (> p.r 1)))                    ; the members whose r is over 1
    (sort g (fn p p.r))                           ; the members ordered by r
    (count g (fn p (> p.r 0)))
    (reduce g 0 (fn ((real total) (shape p)) (+ total p.r)))   ; a running value, starting at 0

A function written in place may use the names around it: in `(map g (fn p (* k p.r)))`, the result follows `k` like anything else that reads it.

## 6. Special forms

A special form looks like a call but does something a function cannot: it evaluates only some of its parts, binds names, or stands for other expressions. Each is its own exception, documented with exactly what it evaluates and when.

| Form | What is special |
|----|----|
| `(if c a b)` | evaluates only the branch taken |
| `(cond (c1 a) (c2 b) (else d))` | takes clauses, each a test and a value; evaluates only the first clause whose test holds |
| `(and …)` `(or …)` | stop at the first part that decides the answer |
| `(let ((h (* 2 k))) (+ h 1))` | names values for use inside its body, a single expression, and gives that expression |
| `(repeat 5 i (circle (name $'dot-{i}') …))` | stands for the expressions it produces, spliced in place when compiling; the count must be known then |
| `(fn p (* 2 p.r))` | a function written in place: binds its parameters in its body (section 5) |
| `(. X Y)` | a part of `X`; `Y` is not evaluated when it is an attribute name (section 7) |
| `(name s)` | turns a string into a name (section 4) |
| `(as T literal)` | gives a literal the type `T` where nothing else gives it one: `(as color 'gold')`, `(as point [0 0])` |

`when`, inside a canvas or a listener, is an item recognized by its head, not a special form: its first part is a condition and the rest are names.

## 7. Reading parts

A part of an object is read with a dot or with brackets.

    p.r                       ; an attribute
    p.pos.x                   ; a chain: p's pos, then its x
    xs[0]                     ; a list item by position
    xs[-1]                    ; counting from the end
    xs[(+ k 1)]               ; any expression in brackets
    g[0]  g['m1']             ; a group member by position, or by its name given as a string
    g.r                       ; on a group: each member's r

A chain of parts always starts with a name. A dot is always followed by an attribute name, or, on a motif instance, the name of one of its members (`d1.face`). Brackets hold a position, a member's name given as a string (used as a key), or any expression that gives one. Group members are read with brackets or by their own name, never with a dot.

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

## 8. How a form's body is read

Every declaration, components included, follows one rule:

    (head name? positional… item…)

- **The name** comes first, when the form declares something with a name. Listeners (`on-drag`, `on-click`) have none.
- **Positional arguments** come next. Each form has a fixed number of them, recognized by where they are, and some forms have none.
- **Items** come last, any number, in any order. Each is recognized by its head (an argument such as `(r 1)`, a constraint such as `(>= 0)`, a member declaration, or a part like `(when …)`), or is a bare name referring to an object.

| Form | Name | Positional | Items |
|----|----|----|----|
| `(real theta 40 (>= 0))` | `theta` | `40` | `(>= 0)` |
| `(circle p (r 1) (fill 'red'))` | `p` | none | `(r 1)`, `(fill 'red')` |
| `(text t 'hi' (pos [0 1]))` | `t` | `'hi'` | `(pos [0 1])` |
| `(group marks (circle m0) (circle m1))` | `marks` | none | two member declarations |
| `(func double (real x) (* 2 x))` | `double` | `(real x)`, `(* 2 x)` | none |
| `(motif dial ((real t 0.5)) (circle face …) …)` | `dial` | its parameters, `((real t 0.5))` | member declarations |
| `(animation grow (theta tr) (wait 0.5))` | `grow` | none | steps; `(theta tr)` moves `theta` along `tr` |
| `(canvas v a b (when show c))` | `v` | none | `a`, `b`, `(when show c)` |
| `(on-drag p (target theta))` | none | `p` | `(target theta)`, required |

Function calls and special forms are not declarations, and do not follow this rule: a call takes its arguments in order, and each special form has its own shape. Inside an animation, a step's head may be any variable or attribute a writer may change, including a path such as `p.r`; the reserved words `wait`, `in-order` and `at-once` are steps of their own.

## 9. Putting a file together

A file is a sequence of declarations, read in order: a name must be declared before it is used. The order is only how the file is written; the objects it declares hold all their relations at once. A typical file runs:

- **Types**: `type`, `motif` and `variant`, at the top level.
- **Globals**: functions, transitions, animations, and variables that are not part of the scene, at the top level.
- **The scene**: exactly one `(scene …)`, holding the shapes and the variables they share.
- **Components**: views (`canvas`, `readout`), controls (`slider`, `button`, `play`, `toggle`) and listeners (`on-drag`, `on-click`), at the top level.

The data model shows how these relate: what reads what, and what writes what.

## 10. Types in brief

A variable's or shape's head is its type: `real`, `int`, `bool`, `string`, `color`, `point`, `list`, a shape such as `circle`, or a type the author declared (section 4 lists the heads that are not types). A function's or motif's parameters always write theirs: `((real t 0.5) (color tint 'red'))`. A type can be written in place: `list[color]` is a list of colors, `real|none` (or `(maybe real)`) a real or `none`, `(real (>= 0))` a real no less than 0.

A literal takes the type expected where it is written: `'red'` is a string, but written as a fill it is a color. The type document covers all of this in full.
