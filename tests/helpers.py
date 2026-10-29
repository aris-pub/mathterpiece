from mathterpiece.compiler import _head
from mathterpiece.nodes import Form, Name
from mathterpiece.parse import parse
from mathterpiece.scene import Root

VISUAL_FORMS = {"circle", "text", "group"}


# Most tests are about one object, so they write visual objects at the top level for brevity.
# This moves them into one anonymous scene, placed where the first of them was. A source that
# already has a scene is left alone.
def with_scene(src: str) -> tuple[Form, ...]:
    forms = parse(src)
    if any(_head(f) == "scene" for f in forms):
        return forms
    motifs = {
        f.items[1].value
        for f in forms
        if _head(f) == "motif" and len(f.items) > 1 and hasattr(f.items[1], "value")
    }

    def visual(node) -> bool:
        head = _head(node)
        if head == "repeat" and isinstance(node, Form):
            return any(visual(item) for item in node.items[3:])
        return head in VISUAL_FORMS or head in motifs

    inside = [f for f in forms if visual(f)]
    outside = [f for f in forms if not visual(f)]
    first = next((i for i, f in enumerate(forms) if visual(f)), 0)
    # The scene must come after every motif it uses, wherever the test defined them.
    at = max([first, *(i + 1 for i, f in enumerate(outside) if _head(f) == "motif")])
    scene = Form((Name(("scene",)), Name(("_",)), *inside))
    return (*outside[:at], scene, *outside[at:])


# Objects at the top of the file, as the tests wrote them: the scene's members and the
# objects outside the scene, without the built-ins.
def user_objects(scn, builtins=frozenset({"pi", "π", "tau", "τ", "euler", "infty", "∞"})):
    out = []
    for obj in scn.objects:
        if isinstance(obj, Root):
            out.extend(obj.members)
        elif obj.name not in builtins:
            out.append(obj)
    return out
