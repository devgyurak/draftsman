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
