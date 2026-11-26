"""Conformance tests of the rule declarations-and-bindings (docs/spec/scope.md)."""

from ._shared import AS_NAME, DOT, DRAG, accepted, compile_error, mtpc, obj, rule


@rule("declarations-and-bindings")
class TestDeclarationsAndBindings:
    def test_a_declaration_with_no_name_creates_an_object(self):
        assert len(obj(mtpc("(scene s (circle_ (r 1)))"), "s")["members"]) == 1

    def test_a_listener_with_no_name_is_created(self):
        d = mtpc(
            "(real k 0) (scene s (circle p (r 1)))"
            " (canvas cv s (on-click p (move k (to 1) (duration 1))))"
        )
        assert [o["kind"] for o in d["objects"]].count("on-click") == 1

    def test_a_binding_creates_nothing(self):
        bound = mtpc("(real v (let ((k 2)) k))")
        plain = mtpc("(real v 2)")
        assert "k" not in bound["names"]
        assert len(bound["objects"]) == len(plain["objects"])

    @AS_NAME
    def test_as_names_the_shape_being_declared_in_a_motif(self):
        accepted("(motif dot () (as me) (circle c (r 1)) (text_ (or? me.name 'a'))) " + DOT)

    @AS_NAME
    def test_as_names_the_position_of_the_pointer(self):
        accepted(DRAG + "(canvas cv s (on-drag p (as ptr) (move a (to ptr.x))))")

    @AS_NAME
    def test_the_language_binds_no_self(self):
        compile_error("(motif dot () (circle c (r 1)) (text_ (or? self.name 'a'))) " + DOT)

    @AS_NAME
    def test_the_language_binds_no_pointer(self):
        compile_error(DRAG + "(canvas cv s (on-drag p (move a (to pointer.x))))")
