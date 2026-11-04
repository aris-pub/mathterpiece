# The data model

Who is involved, how a source file becomes something a reader can use, and what the world model holds.

## Four actors and the static model

Two actors sit on each side of one file. On the left, the **author** writes a source file and the **mtp command** builds it. On the right, the **live model** is what that file becomes, and the **reader** uses it. In the middle is the **.mtpc**, the static model: the only thing that passes from one side to the other.

```mermaid
flowchart LR
  author([author]) -->|writes .mtp| parser
  subgraph cmd [mtp command: building]
    parser -->|forms| compiler -->|model| writer
  end
  writer --> mtpc[(".mtpc: static model")]
  writer --> page["a minimal page"]
  mtpc --> runtime
  page --> runtime
  subgraph live [live model, on a page]
    runtime["runtime: holds the model in memory"] --> components["components: views, controls"]
  end
  components <-->|acts, sees| reader([reader])
```

### The author

Writes a mathematical figure as a `.mtp` source file: the shapes, the values they depend on, how they can move, and how a reader can act on them. The author thinks about mathematics and how to show it, not about programming, so the language says what things are and leaves keeping them current to the software. The author then places pieces of the result on a web page (a drawing here, a slider there, a number inside a sentence) and styles them with the page's own CSS.

### The mtp command

Runs on the author's machine. **Building** a figure is four steps, and each has its own name; "compile" and "build" are not interchangeable:

1. **Parsing.** The **parser** reads the text into forms and knows only the syntax.
2. **Compiling.** The **compiler** resolves every name, checks every type, works out everything that can be known in advance, and makes the model, in memory.
3. **Writing the .mtpc.** The **writer** saves the model as the .mtpc.
4. **Writing the page.** It also writes a minimal web page that loads the runtime and the .mtpc and shows every view, control and readout, so the author sees the figure at once instead of a long file of JSON.

Compiling should be fast, but the reader comes first: anything that can be decided here is, even when it makes compiling slower.

The command's subcommands each take one source file, and each runs the steps up to a point:

| Command | Steps | What it does |
|---|---|---|
| `mtp parse file` | 1 | prints the forms the parser reads, one per line, indented by depth |
| `mtp check file` | 1, 2 | reports the first error, if any, and writes nothing |
| `mtp compile file` | 1 to 3 | writes the .mtpc |
| `mtp build file` | 1 to 4 | writes the .mtpc and the page |
| `mtp serve file` | 1 to 4, again on each save | builds, serves the page on the author's machine, and builds again and reloads the page whenever the source file is saved |
| `mtp fmt file` | 1 | rewrites the file in the house layout, keeping its comments |

**What `mtp check` reports.** The first error in the file, with its line and column, and nothing after it: the parser and the compiler stop there. Errors are of two kinds. A **syntax error** comes from parsing: an unclosed parenthesis or string, a name that is not valid, a stray character. A **compile error** comes from compiling: a name that is not declared or is declared twice; a form that is not where it may be or is missing a part; a value of the wrong type; a constraint, or a range a value must stay in, that cannot be proved, such as a radius that might be negative; a value known when compiling that is undefined there, such as `(/ 1 0)`; and anything the reference calls a compile error. Whatever the compiler cannot decide is not an error: a value that may be none while drawing is typed `T|none`, and the author handles it.

### The live model

What the .mtpc becomes on a page. The **runtime**, a library the page loads, rebuilds the model in memory, keeps it current as the reader acts, and serves the **components** the author placed on the page.

### The reader

Opens the page and uses what the author placed there: drags points, moves sliders, presses play, reads values in the prose. The reader never sees the language, and expects every action to show its effect at once. That is the first requirement of everything here: nothing is decided while the reader waits.

**The .mtpc** (mtp compiled) is a JSON file: the model's static representation. Objects have ids, expressions are Lisp-shaped arrays with the operation first, every reference to an object is resolved to an id, and every type the runtime needs is written down. The runtime never reads the source. Its format is specified in `mtpc.md`.

## The language

An `.mtp` file is written in the mtp language. It is Lisp-like: everything is a form in parentheses, with the head first, as in `(circle p (r 0.2))`. It is declarative: the author says what exists and what each thing is equal to, never what to do step by step, and it is reactive: anything given by an expression is bound to it, and follows it for as long as the page is open. When the reader moves a slider, everything that reads what the slider writes changes at once, with nothing written to make that happen.

It is strongly and statically typed: every object's type is known when compiling, and nothing converts silently except a number broadening (an int where a real is expected) and a literal taking the type expected where it is written. Names are bare. Nothing has a side effect except a declaration making its object exist.

Everything in a source file is an **expression**. Some expressions are **forms**: a head and its parts in parentheses. Some forms are **declarations**: their only effect is that a new object exists in the world model, and they return that object, as `(circle p (r 0.2))` returns the circle it declares. Components (views, controls and listeners) are declarations too. **Function calls** have no effect at all and matter only for what they return, as `(+ k 1)` does. A few **special forms** are exceptions, such as `if`, which evaluates only the branch taken, and `let`, which binds names (see the reference, "Special forms"). Type expressions, such as `list[color]` or `(real (>= 0))`, are not evaluated at all: they describe a type.

The whole purpose of an `.mtp` file is to define one **world model** (the **model** for short), as a sequence of declarations.

## The world model

The world model is everything one source file defines. The compiler builds it, the .mtpc stores it, and the runtime holds it live. **Everything in the model is an object, and every object has a type.**

Objects are of two sorts. A **value** is an immutable object: it never changes, and an expression that gives one gives just that value. The number 3 is a value. A **mutable object** can change over time: an attribute of it is written by the reader's actions, or follows an expression that reads something that changed.

A **variable**, such as `(real k 1)`, is not a value: it is a name for a piece of state that holds one object of its type at a time. The objects it holds may be values (3, then 4) or mutable objects (a shape). It evaluates to what it currently holds, and has no attributes of its own.

Every box below has a title and examples of the forms that declare what it holds. Arrows are relations between them. Apart from function calls, forms fall into five groups: special forms, declarations that create types, declarations of things in the scene, declarations of things on the page, and **globals**: declarations of things in neither, which both use. A variable belongs to the scene when declared in it, and to the globals otherwise. Either way, views may read it, and controls and listeners may read it and write it, as long as it is free, has no `const` constraint, and is not a token. A motif's body may declare only bound variables; free per-instance state is a motif parameter.

```mermaid
flowchart LR
  subgraph wm [world model]
    types["types: (motif …) (type …) (variant …)"]
    special["special forms: (foreach …) (let …) …"]
    subgraph scene
      sc["the scene: (scene …)"]
      shapes["shapes: (circle …) (group …) (dial …)"]
    end
    vars["variables: (real …) (color …) (bool …)"]
    subgraph globals
      funcs["functions: (func …)"]
      trans["transitions: (transition …)"]
      anims["animations: (animation …)"]
    end
    subgraph page
      views["views: (canvas …) (readout …)"]
      listeners["listeners: (on-drag …) (on-click …) (on-release …) (on-dragend …) (on-view …)"]
      controls["controls: (slider …) (button …) (play …) (toggle …)"]
    end
  end
  shapes -->|instance of| types
  shapes <-->|read each other| vars
  vars & shapes -->|call| funcs
  anims -->|made of| trans
  anims -->|moves an attribute or variable| shapes
  controls -->|runs| anims
  listeners -->|attached to| shapes
  listeners -->|on-view: attached to| views
  views -->|shows| sc
  views -->|read| vars
  listeners & controls <-->|read, write| vars
```

Variables are declared inside the scene (then they belong to it), at the top level (then they are globals), or in a motif's body (then each instance holds them; only bound ones). They are not declared inside groups. The diagram draws them once.

A group (a row and a column included) and a motif instance are both **containers**: collections of shapes, which behave the same way. Neither draws anything itself, so an attribute such as `fill` or `stroke` is never a container's own: reading one gives every member's, and writing one writes every member's. What an instance has besides is a frame of its own, moved by its `x`, `y`, `translate` and `transform`, and its parameters. The reference, "Containers", gives the full rules, `(defaults …)` included.

- **The scene** is the mathematical content: the shapes, and the variables declared with them. It is a subset of the model and knows nothing of how it is shown or changed. The model includes the scene; the scene never includes the rest of the model.
- **Components** are what the author places or attaches on the page. They come in two sorts, by the direction information flows: **writers** (controls and listeners) carry the reader's actions into the model; **views** carry the model to the reader. ("Reader" on its own always means the person.) Basic components come from the standard library, and authors will be able to make their own from them.
- **Writers are active or not.** A writer that is **active** accepts triggers: a press of a button, a move of a slider's knob, a click on a toggle, a drag, a click on a shape, a release over one, the end of a drag, a canvas coming into view. Once **triggered**, it writes what it targets, directly or through its animation. An inactive writer cannot be triggered; what it already set off goes on. The author says when a writer is active with `(active bool)`; a writer without one is always active.
- **A writer animates only toward a state it knows.** A triggered writer with an animation builds a path from the state at that moment (or from a transition's own `from`) to the state the animation ends at, then writes along it over the animation's duration. It can do so only if that end state is known when it is triggered. A writer whose end state is never known then, such as a drag, which goes wherever the reader takes the pointer, takes no animation. A writer whose end state is known only sometimes follows its animation whenever the end is known, and otherwise writes the end state at once. (A slider differs: its knob sets how far along its animation things are, not a path played over time; see the reference.)
- **Other ways of showing the model** are possible later: scripts on the page reading the model (see "On the page" and "Open"), descriptions for screen readers, sound, and export to an image or data.

## What changes, and what follows

Every variable, and every attribute of a mutable object, is either **free** or **bound**.

- **Free**: it holds whatever was last written to it, starting with the object its declaration gives (a literal, a constant, or a default). A constant is the bare name of a `const` variable or of a built-in constant such as `pi`, or a read of a `const` attribute such as `c.r`: `(angle golden-angle)` is free, starting at golden-angle's value, as if that value were written. While the reader uses the page, only writers (controls and listeners) and the animations they run may write it. Free ones include a variable given a value, a shape attribute given a value, a motif parameter of an instance, and an attribute a variant leaves unset. A write to a group's attribute (`g.r`) writes each member's.
- **Bound**: it is given by any other expression, and always equals that expression. Nothing may write it.
- **A token**, a color or font variable, effectively acts as a bound variable: it is bound to something not declared in the world model, the page's value for its CSS custom property, with its declared value as the fallback (see "On the page"). So it is never known when compiling, and nothing in the figure may write it.

&nbsp;

    (real k 1)                     ; free: a slider may write it
    (circle c (r (* 2 k)))         ; c.r is bound: it is always twice k
    (slider s (move k (from 0) (to 3)))

So every change starts at something free, and spreads to everything bound to it: when the slider writes `k`, `c.r` follows at once, and so does anything that reads `c.r`. The runtime recomputes only what reads what changed. A free variable with the `const` constraint can never be written, so it is known when compiling and costs nothing while drawing.

## How reactivity works

A world model is not a program that runs from top to bottom. It is a set of statements that are true at every moment: `(circle c (r (* 2 k)))` does not set `c.r` once, it says that `c.r` is always twice `k`.

```mermaid
flowchart LR
  reader([reader]) -->|acts| writers["writers: controls, listeners"]
  writers -->|run| animations["animations: frame by frame"]
  subgraph wm [world model]
    free["free: (real k 1)"] -->|follow at once| bound["bound: (circle c (r (* 2 k)))"]
  end
  animations -->|write| free
  bound -->|read| views["views"]
  views -->|sees| reader
```

- **Change only enters through writers.** When the reader acts, a control or a listener runs an animation, and the animation writes free variables and attributes over time, frame by frame. A drag writes its target directly, and so does a toggle.
- **An animation is made of moves.** Each move writes its target, a variable or an attribute, along a transition: where the value starts, where it ends, the way between, how long it takes and how it speeds up. The reference, "Transitions and animations", says how moves are written and put together.
- **Bound variables and attributes follow at once.** The compiler knows what every expression reads, so after a write the runtime recomputes only what depends on it, and the views redraw. Nothing has to be told to update.
- **Writes respect types.** A write that breaks a constraint is brought into it (clamped, rounded or held). This is the one case where a real becomes an int without being asked: a write into an int is rounded. A `const` variable is never written at all.

### Why there is no assignment

In a programming language, `k = 3` is an instruction: at this point in the program, change `k`. Its effect depends on when it runs and what ran before. mtp has no instructions. If an expression could assign, `c.r = 2k` could be true before it and false after it, and the drawing would depend on the order the runtime happened to evaluate things in. Instead, the only writes are the reader's actions, carried by writers, and they reach only free values. Every bound relation the author wrote holds in every frame the reader sees.

## On the page

The author connects a world model to a web page with HTML elements.

    <mtp-model id="dial" src="dial.mtpc"></mtp-model>

    <p>Drag the slider <mtp-slider model="dial" name="s"></mtp-slider>
       and watch the radius, now <mtp-readout model="dial" name="r"></mtp-readout>.</p>

    <mtp-canvas model="dial" name="v"></mtp-canvas>

- **`<mtp-model>`** loads one .mtpc, once, and gives the live model an id.
- **Each component is an element** placed anywhere on the page, naming its model and the view or control it presents: `<mtp-canvas>`, `<mtp-readout>`, `<mtp-slider>`, `<mtp-button>`, `<mtp-play>`, `<mtp-toggle>`. Listeners have no element: they act through the canvas that draws their shape, or, for `on-view`, the canvas they name.
- **One live model feeds any number of components,** which share its state: the slider in one paragraph, the readout inside a sentence and the canvas below all change together.
- **A page may load several world models.** Each has its own state; components of one never affect another.
- **The page styles components with its own CSS.** Tokens, the color and font variables, appear as CSS custom properties that the page may override: a color variable `ink` as `--mtp-ink`, and a font variable `note` through its parts, `--mtp-note-family`, `--mtp-note-style` and `--mtp-note-weight`. The figure is drawn with the page's value, or with the token's declared value where the page gives none. Colors computed from tokens are passed to the browser as CSS color mixes, so they follow the page's values too. An expression that reads a token's channels (`ink.r`) or compares it sees its declared value.
- **The page may read a live model.** Whether it may also write to one is listed under "Open", below.

The elements also give the page these names, for its scripts and its CSS:

| Name | What it is |
|---|---|
| `mtp-ready` | an event an `<mtp-model>` sends, and which bubbles, when its .mtpc has loaded or failed to load |
| `mtp-change` | an event an `<mtp-model>` sends, and which bubbles, whenever a value in its live model changes |
| `mtp-error` | the class of the `<pre>` that takes the place of a component that cannot be shown, holding the error: the model did not load, or it has no view or control of that name |
| `mtp-lit` | the class of a play's step button while its item runs |

## Two properties of every expression

- **Binding time** (or just time): whether what an expression gives is known when compiling, and then folded into the .mtpc as a plain value, or only while the reader uses the page. A bound variable or attribute takes the time of its expression. `rand` counts as known only while the reader uses the page, though its number is drawn once, when the page loads.
- **Access**: who may read an expression. It takes the access of what it reads: an expression that reads only the scene (or nothing, like a literal or a function of its arguments) has scene access and may be read by anything; one that reads a component has page access and may be read only by components and by globals (variables, functions, transitions and animations declared outside the scene). The scene may never read anything with page access. Globals take the access of what they read; being written by a slider does not give a variable page access, reading one does.

## Open

- Whether a page may write to a model, not only read it.
- What the type system does not have yet, such as vectors: see the type system document, "Not yet".
