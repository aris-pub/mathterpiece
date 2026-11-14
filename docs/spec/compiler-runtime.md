# Compiler and runtime

:::{note}
Not drafted yet. This part defines the two programs that implement mtp and the boundary between them:
- the mtp command and its steps (parsing, compiling, writing the .mtpc, writing the inventory page), and what each subcommand runs;
- what the compiler must do: resolve every name, check every type and rule, fold what is known when compiling, and either reject the world model with an error or write the .mtpc;
- what the runtime must do: load a .mtpc, build the live model, keep it current as the reader acts, and serve the components that a page places;
- the .mtpc as the only thing that passes from the compiler to the runtime, and what each side may assume about it;
- what an implementation of either side must do to conform to this spec.
:::
