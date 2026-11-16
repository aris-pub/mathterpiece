# mathterpiece

The web runtime of [Mathterpiece](https://mtp-lang.org), a language for math you can touch. It draws
a compiled figure (a `.mtpc` file, written by the `mtp` compiler) as SVG inside web components, so a
figure works in any page or framework.

```html
<script type="module" src="https://cdn.jsdelivr.net/npm/mathterpiece@0.1.0/dist/mathterpiece.js"></script>
<mtp-model id="cs" src="schwarz.mtpc"></mtp-model>
<mtp-canvas model="cs" name="c"></mtp-canvas>
```

The compiler is on PyPI: `uv tool install mathterpiece`. See the
[quickstart](https://docs.mtp-lang.org/quickstart.html) and the
[specification](https://spec.mtp-lang.org).

MIT license.
