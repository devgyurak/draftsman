import pytest

from draftsman.typeref import Array, Named, Nullable, Pointer, TypeUnion, all_names, parse_type


@pytest.mark.parametrize("text, expected", [
    ("Order", Named("Order")),
    ("List<Order>", Named("List", (Named("Order"),))),
    ("a.b.Order", Named("a.b.Order")),
    ("Order[]", Array(Named("Order"))),
    ("Order...", Array(Named("Order"))),
    ("Order?", Nullable(Named("Order"))),
    ("Order | None", TypeUnion((Named("Order"), Named("None")))),
    ("list[Order]", Named("list", (Named("Order"),))),
    ("Optional<? extends Shape>", Named("Optional", (Named("Shape"),))),
    ("Optional<? super Shape>", Named("Optional", (None,))),
    ("@NonNull Order", Named("Order")),
    ("const std::vector<Node>&", Pointer(Named("std::vector", (Named("Node"),)), "&")),
    ("Node const*", Pointer(Named("Node"), "*")),
    ("unsigned long long", Named("unsigned long long")),
    ("X509Certificate @Nullable []", Array(Named("X509Certificate"))),
    ("String @A [] @B(x = 1) []", Array(Array(Named("String")))),
])
def test_parse(text, expected):
    assert parse_type(text) == expected


@pytest.mark.parametrize("text", ["(a: A) => B", "'a' | 'b'", "", None, "Map<String"])
def test_unparseable_yields_none(text):
    assert parse_type(text) is None


def test_all_names_walks_arguments():
    assert all_names(parse_type("Map<String, List<Order>>")) == ["Map", "String", "List", "Order"]
    assert all_names(parse_type("Order | null")) == ["Order"]
