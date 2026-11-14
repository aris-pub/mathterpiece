# Glossary

:::{note}
Not drafted yet. Each term the spec defines will be listed here, with a link to where it is defined.
:::

```{glossary}
core form
  A form that the prover checks and the runtime runs: every form that is not sugar. See
  {numref}`core-form`.

head
  The first item of a form, such as `if` in `(if c a b)`. See {ref}`core-kinds`.

library
  The built-in functions and the files of the standard library. A call of a library function is
  a core form. See {numref}`library-form`.

prover
  The part of the compiler that checks types, proves ranges and constraints, and checks every
  invariant of the world model. It sees only core forms. See {numref}`prover-sees-core`.

rewrite
  A rule that replaces a sugar form by core forms, as a pair of mtp fragments. See
  {ref}`core-rewrites`.

sugar
  A form that can be rewritten into core forms without computing any value. Also called a
  derived form. See {numref}`sugar-form`.
```
