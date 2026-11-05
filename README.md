# mathterpiece

mathterpiece (mtp) is a small language for mathematics a reader can drag, slide and play. A
world model is written in a `.mtp` file, in a Lisp-like syntax. A compiler checks it and writes
the compiled model, a `.mtpc` file, which a JavaScript runtime draws on a web page.

```lisp
(real k 1 (>= 0.2) (<= 3))
(scene s
  (circle c (r k) (fill 'teal')))
(canvas v (x -4) (y -4) (width 8) (height 8) s)
(slider radius (move k (from 0.2) (to 3)) (label 'radius'))
(readout area $'area = {(* pi k k):.2f}')
```

The circle's radius is the variable `k`, the slider moves `k`, and the readout shows the area.
The compiler checks the types and the ranges, so a world model that could draw something undefined,
such as a negative radius, does not compile.

## Install

You need Python 3.13 or later with [uv](https://docs.astral.sh/uv/), and, for the web runtime,
Node with [pnpm](https://pnpm.io/). [just](https://just.systems/) runs the common tasks.

```sh
uv sync
cd web && pnpm install
```

## Build a world model

```sh
uv run mtp build dial.mtp              # writes build_dial/: the .mtpc and a page that shows it
uv run mtp serve dial.mtp              # serves that page, building again on each save
uv run mtp compile dial.mtp            # writes dial.mtpc next to it
uv run mtp compile dial.mtp -o out.mtpc
uv run mtp check dial.mtp              # reports the first error, writes nothing
uv run mtp parse dial.mtp              # prints the forms the parser reads
uv run mtp fmt dial.mtp                # indents the file as the Emacs mode does
```

A compile error names the line and column and says what is wrong. Building is four steps:
parsing, compiling, writing the .mtpc and writing a page that shows it (see the data model).
`mtp build` and `mtp serve` build the runtime with Node and pnpm.

## Put a live figure on a page

Build the runtime with `just build-web`, which writes `web/dist/mathterpiece.js`. A page loads
it and places the world model's components anywhere in its text:

```html
<script type="module" src="mathterpiece.js"></script>

<mtp-model id="dial" src="dial.mtpc"></mtp-model>
<p>Drag the slider <mtp-slider model="dial" name="radius"></mtp-slider>
   and watch the <mtp-readout model="dial" name="area"></mtp-readout>.</p>
<mtp-canvas model="dial" name="v"></mtp-canvas>
```

`<mtp-model>` can also read the compiled model from a JSON block anywhere in the page, as in
`<mtp-model id="dial" src="#dial-data">` with `<script type="application/json" id="dial-data">`,
so the page needs no second file. The same lines work in a Markdown file. The data model
("On the page") describes the page's elements, how the author writes them in Markdown, and how a
page restyles a world model's components with CSS.

## Develop

```sh
just web-dev     # build the examples and serve a page that shows any of them
just test        # the compiler's tests
just web-test    # the runtime's tests
just check       # lint, type checks and both test suites
```

## Layout

- `mathterpiece/`: the compiler (`parse.py`, `compiler.py`, `mtpc.py`) and the `mtp` command.
- `web/src/`: the runtime, which plays a `.mtpc` and defines the page's elements.
- `docs/`: the language and the file format.
- `examples/`: one world model per feature to read and try, and the interactive ones from the
  Bourgain notes (`bourgain-*.mtp`). `house.mtp` is not a world model to show: it holds the colors and fonts
  the examples share, and they import it.
- `tests/`: the compiler's tests; `tests/shared/` holds cases both the compiler and the runtime
  check.
- `web/test/`: the runtime's tests.
- `editors/mtp-mode.el`: an Emacs mode for `.mtp` files.

## Docs

- [Syntax](docs/syntax.md): how a file is written.
- [Reference](docs/reference.md): every form, function and constant.
- [Type system](docs/type-system.md): types, ranges and none.
- [Data model](docs/data-model.md): variables, attributes, who may write them, and the page.
- [The .mtpc format](docs/mtpc.md), with its [JSON schema](docs/mtpc.schema.json).

## License

MIT. See [LICENSE](LICENSE).
