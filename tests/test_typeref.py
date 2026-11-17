import pytest

from draftsman.typeref import (Array, FunctionType, Named, Nullable, Pointer, TypeTuple, TypeUnion,
                               all_names, function_types, parse_type)


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


@pytest.mark.parametrize("text, expected", [
    # Kotlin, with receiver and suspend; named parameters; nullable function type
    ("HttpClientConfig<*>.() -> Unit",
     FunctionType((), Named("Unit"), Named("HttpClientConfig", (None,)))),
    ("suspend Route.(Call) -> Unit", FunctionType((Named("Call"),), Named("Unit"), Named("Route"))),
    ("((A, b: B) -> C)?", Nullable(FunctionType((Named("A"), Named("B")), Named("C")))),
    # TypeScript, with optional and rest parameters
    ("(a: A, b?: B) => C", FunctionType((Named("A"), Named("B")), Named("C"))),
    ("(...rest: A[]) => void", FunctionType((Array(Named("A")),), Named("void"))),
    # Python callables, C++ std::function
    ("Callable[[A, B], C]", FunctionType((Named("A"), Named("B")), Named("C"))),
    ("Callable[..., A]", FunctionType((), Named("A"))),
    ("context(A, B) () -> R", FunctionType((), Named("R"), None, (Named("A"), Named("B")))),
    ("std::function<int(Foo)>", Named("std::function", (FunctionType((Named("Foo"),), Named("int")),))),
    # parentheses that only group stay what they group
    ("(A | B)[]", Array(TypeUnion((Named("A"), Named("B"))))),
    # tuples: TypeScript and C# by syntax; generic names (tuple[A, B], std::tuple) stay names,
    # the wrappers read them as tuples unless the project defines the class
    ("[Point, Circle]", TypeTuple((Named("Point"), Named("Circle")))),
    ("[a: Point, b?: Circle]", TypeTuple((Named("Point"), Named("Circle")))),
    ("(Person a, Point b)", TypeTuple((Named("Person"), Named("Point")))),
    ("tuple[P, Q]", Named("tuple", (Named("P"), Named("Q")))),
    ("tuple[P, ...]", Named("tuple", (Named("P"), None))),
    ("std::tuple<P, B*>", Named("std::tuple", (Named("P"), Pointer(Named("B"), "*")))),
    # Python: Annotated's metadata is cut as text (any expression); what Literal and
    # Annotated mean is the wrappers' business
    ("Literal['a', 'b']", Named("Literal", (None, None))),
    ("Annotated[Item, 'x']", Named("Annotated", (Named("Item"),))),
    ("Annotated[Item, Field(gt=0, json_schema_extra={'a': [1]})]", Named("Annotated", (Named("Item"),))),
    # elsewhere, without a subscript, they are ordinary names
    ("Literal", Named("Literal")),
    ("Literal[]", Array(Named("Literal"))),
    ("Annotated[]", Array(Named("Annotated"))),
    ("list[typing.Annotated[Item, Depends(get_db), 'x,]']]",
     Named("list", (Named("typing.Annotated", (Named("Item"),)),))),
    # C#: global:: is the root namespace
    ("global::Acme.Core.Point", Named("Acme.Core.Point")),
    # C/C++ multi-word builtins still join, a following name does not
    ("unsigned long long", Named("unsigned long long")),
])
def test_function_types(text, expected):
    assert parse_type(text) == expected


def test_function_types_inside_containers():
    ref = parse_type("MutableMap<AttributeKey<*>, (HttpClient) -> Unit>")
    assert all_names(ref) == ["MutableMap", "AttributeKey", "HttpClient", "Unit"]
    assert function_types(ref) == [FunctionType((Named("HttpClient"),), Named("Unit"))]


@pytest.mark.parametrize("text", ["'a' | 'b'", "", None, "Map<String", "(A)(B)"])
def test_unparseable_yields_none(text):
    assert parse_type(text) is None


def test_all_names_walks_arguments():
    assert all_names(parse_type("Map<String, List<Order>>")) == ["Map", "String", "List", "Order"]
    assert all_names(parse_type("Order | null")) == ["Order"]
