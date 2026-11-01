import pytest

from mathterpiece.colors import parse_color


class TestParse:
    @pytest.mark.parametrize(
        "text, rgba",
        [
            ("#1f2a44", "#1f2a44ff"),
            ("#1F2A44", "#1f2a44ff"),
            ("#1f2a4480", "#1f2a4480"),
            ("#f80", "#ff8800ff"),
            ("#f808", "#ff880088"),
            ("gold", "#ffd700ff"),
            ("Gold", "#ffd700ff"),
            ("transparent", "#00000000"),
        ],
    )
    def test_reads(self, text, rgba):
        assert parse_color(text) == rgba

    @pytest.mark.parametrize("text", ["", "#12", "#gggggg", "golden", "rgb(1, 2, 3)", "none"])
    def test_rejects(self, text):
        assert parse_color(text) is None
