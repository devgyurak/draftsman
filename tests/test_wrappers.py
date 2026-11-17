import pytest

from draftsman.typeref import parse_type
from draftsman.wrappers import Leaf, Wrappers

W = Wrappers.load()


def leaves(text, project=(), cpp=False):
    # compared without the type arguments a leaf carries; see test_generic_leaf_keeps_its_args
    return [Leaf(lf.name, lf.multiplicity, lf.ownership)
            for lf in W.leaves(parse_type(text), lambda n: n in project, track_ownership=cpp)]


@pytest.mark.parametrize("text, expected", [
    ("Order", [Leaf("Order", "1", None)]),
    ("List<Order>", [Leaf("Order", "*", None)]),
    ("java.util.List<Order>", [Leaf("Order", "*", None)]),
    ("Map<String, Order>", [Leaf("Order", "*", None)]),
    ("Optional<Order>", [Leaf("Order", "0..1", None)]),
    ("Order?", [Leaf("Order", "0..1", None)]),
    ("Order | undefined", [Leaf("Order", "0..1", None)]),
    ("Optional<List<Order>>", [Leaf("Order", "*", None)]),
    ("CompletableFuture<Order>", [Leaf("Order", "1", None)]),
    ("Order[]", [Leaf("Order", "*", None)]),
    ("list[Order] | None", [Leaf("Order", "*", None)]),
    ("Repo<Order>", [Leaf("Repo", "1", None)]),
    ("List", []),
])
def test_leaves(text, expected):
    assert leaves(text) == expected


def test_generic_leaf_keeps_its_args():
    # Repo is no container: the field points at Repo, and depends on what Repo<...> names
    (leaf,) = W.leaves(parse_type("Repo<Order, Map<String, Line>>"), lambda n: False)
    assert leaf.name == "Repo" and [a.name for a in leaf.args] == ["Order", "Map"]
    (inner,) = W.leaves(parse_type("List<Order>"), lambda n: False)
    assert inner.name == "Order" and inner.args == ()


def test_project_type_shadows_wrapper():
    assert leaves("List<Order>", project={"List"}) == [Leaf("List", "1", None)]


def test_cpp_ownership():
    assert leaves("std::vector<std::unique_ptr<Node>>", cpp=True) == [Leaf("Node", "*", "owned")]
    assert leaves("Node*", cpp=True) == [Leaf("Node", "1", "shared")]
    assert leaves("std::shared_ptr<Node>", cpp=True) == [Leaf("Node", "1", "shared")]
    assert leaves("Node", cpp=True) == [Leaf("Node", "1", "owned")]


def test_user_wrappers_are_appended(tmp_path):
    cfg = tmp_path / "w.yaml"
    cfg.write_text("wrappers:\n  - names: [Bag]\n    arg: 0\n    multiplicity: '*'\n")
    w = Wrappers.load(cfg)
    assert w.leaves(parse_type("Bag<Order>"), lambda n: False) == [Leaf("Order", "*", None)]


@pytest.mark.parametrize("text, expected", [
    # names that mean something of their own, when the project has no class of the name
    ("Literal['a', 'b']", []),
    ("Annotated[Item, Field(gt=0)]", [Leaf("Item", "1", None)]),
    ("Optional[Annotated[Item, 'x']]", [Leaf("Item", "0..1", None)]),
    ("tuple[P, Q]", [Leaf("P", "1", None), Leaf("Q", "1", None)]),
    ("tuple[P, ...]", [Leaf("P", "*", None)]),
    ("Tuple<P, Q>", [Leaf("P", "1", None), Leaf("Q", "1", None)]),
    ("ValueTuple<P, Q>", [Leaf("P", "1", None), Leaf("Q", "1", None)]),
    ("std::pair<int, P*>", [Leaf("int", "1", None), Leaf("P", "1", None)]),
    # a bare Literal is a type of that name (an AST class)
    ("Literal", [Leaf("Literal", "1", None)]),
    ("Literal[]", [Leaf("Literal", "*", None)]),
    # angle brackets: a generic class of that name (Java, TypeScript), not Python's
    ("Literal<Item>", [Leaf("Literal", "1", None)]),
])
def test_special_forms(text, expected):
    assert leaves(text) == expected


@pytest.mark.parametrize("text, name", [
    ("Literal[Item]", "Literal"), ("Annotated[Item, 'x']", "Annotated"),
    ("Tuple<P, Q>", "Tuple"), ("tuple[P, Q]", "tuple"), ("ValueTuple<P, Q>", "ValueTuple"),
    ("std::pair<P, Q>", "std::pair"),
])
def test_project_class_shadows_special_form(text, name):
    """A project class called Tuple (common in Java, which has none) is that class."""
    assert leaves(text, project={name}) == [Leaf(name, "1", None)]
