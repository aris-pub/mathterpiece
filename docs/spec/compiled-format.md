```{include} ../mtpc.md
```

## Imported declarations

This rule exists so that a .mtpc holds no more than its page can use.

```{rule} mtpc-imported-declarations
Of the declarations that a source imports ({numref}`import-puts-in`), a .mtpc holds only those that
the source uses, directly or through other declarations.
```

:::{admonition} Code differs
:class: note
The format describes what the compiler writes today, which differs from the spec in these ways:

- It has the type and the value `transform`, and the attributes `translate` and `transform`, where
  the spec has the frame attributes `shift`, `rotate`, `scale-x` and so on. Bead mtp-1vyc.
- It has `transition` objects and `animation` objects with steps, where the spec has movements,
  scores with lags, and animations as templates. Beads mtp-kir3, mtp-cg47 and mtp-idcs.
- It has the types `namespace` and `palette`, and writes a font as a value, where the spec has
  records, and a font is a record. Beads mtp-h732 and mtp-1vyc.
- It writes a shape declared with a motif with members, where the spec makes such a shape one shape
  whose body's shapes are its attributes. Bead mtp-ar1u.
- The `map` of an `on-drag` reads the name `pointer`, where the spec binds a name with `(as N)`. Bead
  mtp-t8in.
- It can write only some of the types of the spec. Bead mtp-uhak.
:::
