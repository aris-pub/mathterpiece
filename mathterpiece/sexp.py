from collections.abc import Iterator


def next_sexp(src: str) -> tuple[str, str]:
    sexp_generator = toplevel_sexps(src)
    first = next(sexp_generator)
    rest = " ".join(sexp for sexp in sexp_generator)
    return first, rest


def toplevel_sexps(src: str) -> Iterator[str]:
    last: int = 0
    ptr: int = 0
    nestedness: int = 0
    while ptr < len(src):
        sexp = ""
        while ptr < len(src) and src[ptr] in " \n\t":
            ptr += 1
        if ptr == len(src):
            break

        # atom
        if src[ptr] != "(":
            while ptr < len(src) and src[ptr] != " ":
                ptr += 1

        # list
        elif src[ptr] == "(":
            nestedness += 1
            ptr += 1
            while nestedness != 0:
                if src[ptr] == "(":
                    nestedness += 1
                elif src[ptr] == ")":
                    nestedness -= 1
                ptr += 1

        sexp: str = src[last : ptr].strip()
        if sexp:
            yield sexp
        last = ptr
