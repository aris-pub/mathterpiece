"""Conformance tests of the rule mixed-color-channels (docs/spec/evaluation.md)."""

from ._shared import MIX, rule, value


@rule("mixed-color-channels")
class TestMixedColorChannels:
    @MIX
    def test_a_channel_that_lies_halfway_rounds_up(self):
        assert value("(color v (mix #'#000000' #'#050505' 0.5))", "v") == "#030303ff"

    def test_a_channel_that_does_not_lie_halfway(self):
        assert value("(color v (mix #'#000000' #'#060606' 0.5))", "v") == "#030303ff"
