"""The standard library (mathterpiece/stdlib/): files of declarations a figure imports by name,
(import math dot), which the compiler finds after the figure's own folder (mtp-1lq). The author,
2026-11-04: the standard library holds declarations that may serve the author, such as eases,
colors, fonts and motifs, and a few functions; everything else stays built in, and nothing is
imported without an import."""

import math as py

import pytest
from helpers import doc
from mtpc_check import errors

from mathterpiece.compiler import STDLIB, _declared, compile_source
from mathterpiece.parse import parse
from mathterpiece.types import PALETTE

NAMES = {
    "colors": [
        "okabe-ito-named",
        "tab10-named",
        "okabe-ito",
        "tab10",
        "viridis",
        "magma",
        "cividis",
        "blue-white-red",
    ],  # fmt: skip
    "fonts": ["serif", "sans", "mono", "math"],
    "math": ["dot", "clamp", "smoothstep", "mean", "norm", "normalize", "cross", "midpoint"],
    "ease": [
        "linear",
        *(
            f"{kind}-{way}"
            for kind in ("cubic", "spring", "bounce", "elastic", "back")
            for way in ("in", "out", "in-out")
        ),
    ],
    "types": ["unit"],
}


def figure(tmp_path, src):
    path = tmp_path / "fig.mtp"
    path.write_text(src)
    return compile_source(src, path=path)


def value(tmp_path, imports, expr, t="real|none"):
    m = figure(tmp_path, f"{imports} ({t} v {expr})")
    e = m.get("v").value
    assert not e.bound, "a call with known arguments is worked out when compiling"
    return e.value


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_file_compiles_on_its_own(name):
    path = STDLIB / f"{name}.mtp"
    compile_source(path.read_text(), path=path)


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_file_declares_what_is_tested_here(name):
    forms = parse((STDLIB / f"{name}.mtp").read_text())
    assert sorted(n for f in forms if (n := _declared(f))) == sorted(NAMES[name])


class TestMath:
    def test_dot(self, tmp_path):
        assert value(tmp_path, "(import math dot)", "(dot [1 2 3] [4 5 6])") == 32
        assert value(tmp_path, "(import math dot)", "(dot [1 2] [1 2 3])") is None

    def test_clamp(self, tmp_path):
        for x, want in ((-1, 0), (0.5, 0.5), (3, 1)):
            assert value(tmp_path, "(import math clamp)", f"(clamp {x} 0 1)") == want

    def test_smoothstep(self, tmp_path):
        got = [
            value(tmp_path, "(import math smoothstep)", f"(smoothstep 0 2 {x})") for x in (-1, 1, 3)
        ]
        assert got == [0, 0.5, 1]

    def test_mean(self, tmp_path):
        assert value(tmp_path, "(import math mean)", "(mean [1 2 6])") == 3

    def test_norm_and_normalize(self, tmp_path):
        assert value(tmp_path, "(import math norm)", "(norm [3 4])") == 5
        got = value(tmp_path, "(import math normalize)", "(normalize [3 4])", "point|none")
        assert got == pytest.approx((0.6, 0.8))

    def test_cross(self, tmp_path):
        # The 2D cross product: positive when b is counterclockwise from a.
        assert value(tmp_path, "(import math cross)", "(cross [1 0] [0 1])") == 1

    def test_midpoint(self, tmp_path):
        assert value(
            tmp_path, "(import math midpoint)", "(midpoint [0 0] [2 4])", "point|none"
        ) == (
            1,
            2,
        )

    def test_imported_whole(self, tmp_path):
        assert value(tmp_path, "(import math)", "(math.clamp 5 0 1)") == 1


EASES = NAMES["ease"]


class TestEases:
    @pytest.mark.parametrize("name", EASES)
    def test_from_0_to_1(self, tmp_path, name):
        ends = [value(tmp_path, f"(import ease {name})", f"({name} {t})") for t in (0, 1)]
        assert [round(e, 9) for e in ends] == [0, 1]

    @pytest.mark.parametrize("kind", ("cubic", "spring", "bounce", "elastic", "back"))
    def test_in_is_out_turned_around(self, tmp_path, kind):
        imports = f"(import ease {kind}-in {kind}-out)"
        a = value(tmp_path, imports, f"({kind}-in 0.3)")
        b = value(tmp_path, imports, f"({kind}-out 0.7)")
        assert py.isclose(a, 1 - b)

    @pytest.mark.parametrize("kind", ("cubic", "spring", "bounce", "elastic", "back"))
    def test_in_out_is_half_way_at_the_middle(self, tmp_path, kind):
        got = value(tmp_path, f"(import ease {kind}-in-out)", f"({kind}-in-out 0.5)")
        assert py.isclose(got, 0.5)

    def test_the_cubic_eases_are_the_ones_built_in_before(self, tmp_path):
        # The same curves as 'ease-in', 'ease-out' and 'ease-in-out' were (web/src/transitions.ts).
        t = 0.3
        for name, want in (
            ("cubic-in", t**3),
            ("cubic-out", 1 - (1 - t) ** 3),
            ("cubic-in-out", 4 * t**3),
            ("linear", t),
        ):
            assert py.isclose(value(tmp_path, f"(import ease {name})", f"({name} {t})"), want)

    def test_back_and_spring_go_past_their_end(self, tmp_path):
        assert value(tmp_path, "(import ease back-out)", "(back-out 0.6)") > 1
        assert value(tmp_path, "(import ease spring-out)", "(spring-out 0.3)") > 1

    def test_the_file_imported_whole(self, tmp_path):
        # The file and a move's (ease …) share a name, and do not clash.
        src = (
            "(import ease) (real k 0) (scene s (circle c (x k)))"
            " (button b (animation (move k (to 1) (duration 1) (ease ease.back-out))))"
            " (import types) (types.unit u 0.5)"
        )
        path = tmp_path / "fig.mtp"
        path.write_text(src)
        assert errors(doc(src, path)) == []

    def test_a_move_takes_one(self, tmp_path):
        src = (
            "(import ease bounce-out) (real k 0) (scene s (circle c (x k)))"
            " (button b (animation (move k (to 1) (duration 1) (ease bounce-out))))"
        )
        path = tmp_path / "fig.mtp"
        path.write_text(src)
        assert errors(doc(src, path)) == []


OKABE_ITO = {
    "orange": "#e69f00ff",
    "sky-blue": "#56b4e9ff",
    "bluish-green": "#009e73ff",
    "yellow": "#f0e442ff",
    "blue": "#0072b2ff",
    "vermillion": "#d55e00ff",
    "reddish-purple": "#cc79a7ff",
    "black": "#000000ff",
}
TAB10 = {
    "blue": "#1f77b4ff",
    "orange": "#ff7f0eff",
    "green": "#2ca02cff",
    "red": "#d62728ff",
    "purple": "#9467bdff",
    "brown": "#8c564bff",
    "pink": "#e377c2ff",
    "gray": "#7f7f7fff",
    "olive": "#bcbd22ff",
    "cyan": "#17becfff",
}


class TestColors:
    @pytest.mark.parametrize(
        "palette, colors", [("okabe-ito-named", OKABE_ITO), ("tab10-named", TAB10)]
    )
    def test_each_palette_holds_its_colors_by_name(self, tmp_path, palette, colors):
        m = figure(tmp_path, f"(import colors) (scene s (circle c (fill colors.{palette}.blue)))")
        ns = m.objects[m.names[f"colors.{palette}"]]
        assert ns.type == PALETTE
        got = {short: m.objects[i].value.value for short, i in ns.data["members"].items()}
        assert got == colors

    def test_imported_by_name(self, tmp_path):
        m = figure(
            tmp_path,
            "(import colors okabe-ito-named) (scene s (circle c (fill okabe-ito-named.orange)))",
        )
        e = m.get("c").attrs["fill"].expr
        # A token, named by the file and the palette: --mtp-colors-okabe-ito-named-orange.
        assert m.objects[e.args[0]].name == "colors.okabe-ito-named.orange"

    @pytest.mark.parametrize("name, colors", [("okabe-ito", OKABE_ITO), ("tab10", TAB10)])
    def test_each_as_a_map_by_number_wrapping_around(self, tmp_path, name, colors):
        # Color k for each whole k, back to the first after the last; each is the palette's own
        # token, so a page restyling it restyles the map too.
        n = len(colors)
        for k, want in [(0, 0), (3, 3), (n - 1, n - 1), (n, 0), (n + 2, 2)]:
            src = f"(import colors {name}) (scene s (circle c (fill ({name} {k}))))"
            e = figure(tmp_path, src).get("c").attrs["fill"].expr
            assert e.op == "read"
            m = figure(tmp_path, src)
            assert m.objects[e.args[0]].name == f"colors.{name}-named.{list(colors)[want]}"


class TestFonts:
    @pytest.mark.parametrize(
        "name, last",
        [("serif", "serif"), ("sans", "sans-serif"), ("mono", "monospace"), ("math", "serif")],
    )
    def test_each_is_a_family_ending_in_a_generic_one(self, tmp_path, name, last):
        # A list of fonts to try in order, as CSS writes it, ending in CSS's own generic family
        # so that something always draws.
        m = figure(tmp_path, f"(import fonts {name}) (scene s (text t 'x' (font {name})))")
        value = m.objects[m.names[f"fonts.{name}"]].value.value
        assert value["family"].split(",")[-1].strip() == last
        assert (value["style"], value["weight"], value["size"]) == ("normal", 400, 16)


class TestColormaps:
    @pytest.mark.parametrize(
        "name, first, middle, last",
        [
            ("viridis", "#440154ff", "#21918cff", "#fde725ff"),
            ("magma", "#000004ff", "#b73779ff", "#fcfdbfff"),
            ("cividis", "#00224eff", "#7d7c78ff", "#fee838ff"),
            ("blue-white-red", "#053061ff", "#f7f7f7ff", "#67001fff"),
        ],
    )
    def test_its_ends_and_middle(self, tmp_path, name, first, middle, last):
        got = [
            value(tmp_path, f"(import colors {name})", f"({name} {t})", "color")
            for t in (0, 0.5, 1)
        ]
        assert got == [first, middle, last]

    def test_imported_whole(self, tmp_path):
        assert value(tmp_path, "(import colors)", "(colors.viridis 1)", "color") == "#fde725ff"
