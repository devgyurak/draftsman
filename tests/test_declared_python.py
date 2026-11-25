"""Python declared relations looked up as the checkers do (issue #7: cases 6, 7, 50): a
class body's own bindings, and a name bound twice. Each test is a form of
bench/py_oracle/review/py1, whose answers mypy, pyright and ty give."""

from conftest import extract_source


def _rels(ir, src: str) -> set[tuple[str, str]]:
    return {(r.to, r.via) for r in ir.relations if r.from_ == src and r.evidence is None}


def _unresolved(ir, src: str) -> dict[str, str]:
    return {u.raw_type: u.hint for u in ir.unresolved if u.from_ == src}


def test_a_class_bodys_binding_is_a_members_decorator(tmp_path):
    # #6: `Other = print` in the class body: `@Other` on a method is that, not the class
    ir = extract_source(tmp_path, {"q/__init__.py": "", "q/d.py": (
        "class Other: ...\n\n\nclass A:\n    Other = print\n\n    @Other\n    def m(self): ...\n\n\n"
        "class B:\n    @Other\n    def m(self): ...\n")})
    assert not _rels(ir, "q.d.A")
    assert _rels(ir, "q.d.B") == {("q.d.Other", "@Other")}


def test_a_class_bodys_binding_in_an_annotation_is_disputed(tmp_path):
    # #50: mypy and ty take the class body's `Item = int`, pyright the module's Item
    ir = extract_source(tmp_path, {
        "q/__init__.py": "", "q/a.py": "class Item: ...\nclass Money: ...\n",
        "q/s.py": ("from q.a import Item, Money\n\n\nclass Shadow:\n    Item = int\n"
                   "    a: Item\n    b: Money\n\n    def f(self, x: Item) -> None: ...\n\n\n"
                   "class Plain:\n    a: Item\n")})
    assert _rels(ir, "q.s.Shadow") == {("q.a.Money", "b")}
    assert "the class body binds Item" in _unresolved(ir, "q.s.Shadow")["Item"]
    assert _rels(ir, "q.s.Plain") == {("q.a.Item", "a")}


def test_a_nested_class_beside_the_modules_name_in_an_annotation_is_disputed(tmp_path):
    # #50: mypy and ty take the nested class, pyright the module's import of the name;
    # without one at the module's top the nested class is the answer
    ir = extract_source(tmp_path, {
        "q/__init__.py": "", "q/b.py": "class In2: ...\n",
        "q/u.py": ("from q.b import In2\n\n\nclass Use:\n    class In2: ...\n\n    g: In2\n\n\n"
                   "class Own:\n    class Inner: ...\n\n    h: Inner\n")})
    assert not any(to.endswith("In2") for to, _ in _rels(ir, "q.u.Use"))
    assert ("q.u.Own.Inner", "h") in _rels(ir, "q.u.Own")

