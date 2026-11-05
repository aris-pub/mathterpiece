"""Colormaps (mtp-nua; docs/reference.md, "Colormaps"). The author, 2026-11-05: a colormap is two
functions composed, from the figure's values to the unit interval, then from it to colors, and
(colormap name [colors…] (positions …)) is sugar for one function, of type colormap, an alias of
func[real color]. Positions are in the figure's values: two, the start and the end, with the
colors evenly spaced, or one per color; with none, 0 and 1. Colors mix in a straight line between
neighbors; (discrete true) makes each one a solid step, and takes positions only as a start and an
end. A value past an end gets that end's color, or with (wrap-at x) wraps around."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

BW = "(colormap gray ['#000000' '#ffffff'])"


def at(src, call):
    m = model(f"{src} (color v {call})")
    e = m.get("v").value
    assert not e.bound, "literal colors and a known value are worked out when compiling"
    return e.value


class TestMixed:
    def test_evenly_spaced_from_0_to_1(self):
        assert at(BW, "(gray 0)") == "#000000ff"
        assert at(BW, "(gray 1)") == "#ffffffff"
        assert at(BW, "(gray 0.5)") == at(BW, "(mix '#000000' '#ffffff' 0.5)")

    def test_past_an_end_gets_that_ends_color(self):
        assert at(BW, "(gray -3)") == "#000000ff"
        assert at(BW, "(gray 7)") == "#ffffffff"

    def test_a_start_and_an_end(self):
        src = "(colormap heat ['#0000ff' '#ffffff' '#ff0000'] (positions [-5 20]))"
        assert at(src, "(heat -5)") == "#0000ffff"
        assert at(src, "(heat 7.5)") == "#ffffffff"
        assert at(src, "(heat 20)") == "#ff0000ff"

    def test_one_position_per_color(self):
        src = "(colormap heat ['#0000ff' '#ffffff' '#ff0000'] (positions [-5 0 20]))"
        assert at(src, "(heat 0)") == "#ffffffff"
        assert at(src, "(heat 10)") == at(src, "(mix '#ffffff' '#ff0000' 0.5)")

    def test_two_colors_at_one_position_make_a_hard_edge(self):
        src = (
            "(colormap land ['#000080' '#add8e6' '#228b22' '#ffffff'] (positions [-4000 0 0 4000]))"
        )
        assert at(src, "(land 0)") == "#add8e6ff"
        assert at(src, "(land 0.001)") != "#add8e6ff"
        assert at(src, "(land 4000)") == "#ffffffff"


class TestDiscrete:
    SRC = (
        "(colormap risk ['#000001' '#000002' '#000003' '#000004'] (discrete true)"
        " (positions [0 400]))"
    )

    def test_equal_solid_steps(self):
        got = [at(self.SRC, f"(risk {x})") for x in (0, 50, 99.9, 100, 250, 399, 400, 1000, -5)]
        assert got == [
            "#000001ff", "#000001ff", "#000001ff", "#000002ff", "#000003ff",
            "#000004ff", "#000004ff", "#000004ff", "#000001ff",
        ]  # fmt: skip

    def test_from_0_to_1_with_no_positions(self):
        src = "(colormap two ['#000001' '#000002'] (discrete true))"
        assert [at(src, f"(two {x})") for x in (0.2, 0.7)] == ["#000001ff", "#000002ff"]

    def test_only_a_start_and_an_end(self):
        error(
            "(colormap r ['#000001' '#000002' '#000003'] (discrete true) (positions [0 1 2]))",
            "a discrete colormap takes positions only as a start and an end",
        )


class TestWrapAt:
    # The author, 2026-11-05: (wrap-at x) is read as positions are, the value where the map is
    # back at its first color; positions keep their meaning, and after the last one the map mixes
    # from the last color back into the first.
    SRC = "(colormap phase ['#ff0000' '#00ff00' '#0000ff'] (positions [0 120 240]) (wrap-at 360))"

    def test_it_wraps_around(self):
        assert at(self.SRC, "(phase 370)") == at(self.SRC, "(phase 10)")
        assert at(self.SRC, "(phase -90)") == at(self.SRC, "(phase 270)")

    def test_the_last_color_mixes_back_into_the_first(self):
        assert at(self.SRC, "(phase 300)") == at(self.SRC, "(mix '#0000ff' '#ff0000' 0.5)")
        assert at(self.SRC, "(phase 360)") == "#ff0000ff"

    def test_with_a_start_and_an_end(self):
        src = "(colormap p ['#ff0000' '#00ff00' '#0000ff'] (positions [0 240]) (wrap-at 360))"
        assert at(src, "(p 120)") == "#00ff00ff"
        assert at(src, "(p 300)") == at(self.SRC, "(phase 300)")

    def test_discrete(self):
        src = "(colormap c ['#000001' '#000002'] (discrete true) (positions [0 2]) (wrap-at 2))"
        assert [at(src, f"(c {x})") for x in (0.5, 1.5, 2.5, 3.5)] == [
            "#000001ff", "#000002ff", "#000001ff", "#000002ff",
        ]  # fmt: skip

    def test_after_the_last_position(self):
        error(
            "(colormap p ['#ff0000' '#0000ff'] (positions [0 10]) (wrap-at 10))",
            "wrap-at comes after the last position",
        )


class TestDeclaring:
    def test_tokens_stay_tokens(self):
        m = model(
            "(color navy '#1f2a44') (color paper '#ffffff') (real t 0.5)"
            " (colormap ice [navy paper]) (scene s (circle c (fill (ice t))))"
        )
        assert m.get("c").attrs["fill"].bound

    def test_at_least_two_colors(self):
        error("(colormap one ['#000000'])", "a colormap needs at least two colors")

    def test_positions_two_or_one_per_color(self):
        error(
            "(colormap m ['#000000' '#111111' '#222222' '#333333'] (positions [0 1 2]))",
            "positions are a start and an end, or one per color",
        )

    def test_positions_do_not_decrease(self):
        error("(colormap m ['#000000' '#ffffff'] (positions [1 0]))", "positions may not decrease")

    def test_positions_are_known_when_compiling(self):
        error(
            "(real top 1) (colormap m ['#000000' '#ffffff'] (positions [0 top]))",
            "known when compiling",
        )

    def test_an_unknown_keyword(self):
        error("(colormap m ['#000000' '#ffffff'] (stepped true))", "a colormap takes")
        error("(colormap m ['#000000' '#ffffff'] (cyclic true))", "a colormap takes")


class TestType:
    def test_a_colormap_is_a_func_real_color(self):
        model(f"{BW} (func paint ((colormap m)) (m 0.5)) (color v (paint gray))")

    def test_any_func_real_color_is_a_colormap(self):
        model(
            "(func g ((real x)) (mix '#000000' '#ffffff' 0.5))"
            " (func paint ((colormap m)) (m 0.5)) (color v (paint g))"
        )


@pytest.mark.parametrize(
    "src",
    [
        "(color navy '#1f2a44') (real t 0.5) (colormap ice [navy '#ffffff' '#b2182b']"
        " (positions [-5 0 20])) (scene s (circle c (fill (ice t))))",
        "(real t 0.5) (colormap r ['#000001' '#000002'] (discrete true) (wrap-at 1))"
        " (scene s (circle c (fill (r t))))",
    ],
)
def test_the_compiled_file_passes_the_schema(src):
    assert errors(doc(src)) == []
