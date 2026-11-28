(world-model)=
# World model

This page defines the {term}`world model` of a source, the {term}`compiled model` that the compiler
writes for it, and the {term}`live model` that the runtime builds from the compiled model. What
{term}`values <value>`, {term}`variables <variable>`, attributes and {term}`objects <object>` are is
defined in {doc}`data-model`, and the scene and its shapes in {doc}`scene`.

## The world model of a source

This rule exists to fix what the {term}`compiler` builds from one source, and so what the {term}`runtime` holds while a page is open.

```{rule} what-a-world-model-holds
The world model of a source is every variable, type and object that the
{term}`declarations <declaration>` of the source create ({numref}`declarations-and-bindings`), and every declaration of an imported file that the
source uses ({numref}`mtpc-imported-declarations`).
```

So the world model holds every copy that a `foreach` makes and every shape that `(M …)` declares for
a motif `M`, as the expand step writes them out ({numref}`compile-steps`). The runtime holds it as the
{term}`live model`.
