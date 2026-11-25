"""C++ declared relations: a declaration's names looked up as names in bodies are
(LanguageSpec.declared_like_bodies, issue #7). Each test is one of the forms of
bench/clang_oracle/review/cpp9, whose answers Clang gives."""

from conftest import extract_source


def _rels(ir, src: str) -> set[tuple[str, str]]:
    return {(r.to, r.via) for r in ir.relations if r.from_ == src and r.evidence is None}


def _unresolved(ir, src: str) -> dict[str, str]:
    return {u.raw_type: u.hint for u in ir.unresolved if u.from_ == src}


def test_an_alias_templates_own_parameter_is_no_type(tmp_path):
    ir = extract_source(tmp_path, {"a.h": (
        "#include <map>\nstruct Hash {};\n"
        "template <class K, class Hash = int> using Table = std::map<K, Hash>;\n"
        "struct Store { Table<int> t; void put(Table<int> x); };\n")})
    assert not any(to == "Hash" for to, _ in _rels(ir, "Store"))


def test_a_qualified_heads_class_alias_comes_first(tmp_path):
    ir = extract_source(tmp_path, {"a.h": (
        "template <class M> struct Lock {};\n"
        "struct FastMutex { using ScopedLock = Lock<FastMutex>; };\n"
        "struct Mutex { using ScopedLock = Lock<Mutex>; };\n"
        "struct Poller { using Mutex = FastMutex; Mutex::ScopedLock l; };\n")})
    assert {to for to, _ in _rels(ir, "Poller")} == {"Lock", "FastMutex"}


def test_another_programs_type_is_passed_over(tmp_path):
    ir = extract_source(tmp_path, {
        "a/util.h": "struct Utility {};\n",
        "a/main.cc": "#include \"util.h\"\nstruct ToolA { Utility u; };\n",
        "b/gen.h": "namespace gen { struct Utility {}; }\n",
        "b/main.cc": ("#include \"gen.h\"\nusing namespace gen;\n"
                      "struct ToolB { Utility u; };\nstruct ToolC : Utility {};\n")})
    assert _rels(ir, "ToolB") == {("gen::Utility", "u")}
    assert _rels(ir, "ToolC") == {("gen::Utility", None)}   # a base so too
    assert _rels(ir, "ToolA") == {("Utility", "u")}


def test_a_type_of_a_file_not_included_is_unresolved(tmp_path):
    ir = extract_source(tmp_path, {
        "a/money.h": "struct Money {};\n",
        "b/user.h": "struct User { Money m; };\n"})
    assert not _rels(ir, "User")
    assert "does not include" in _unresolved(ir, "User")["Money"]


def test_a_type_of_an_if_branch_is_unresolved_outside_it(tmp_path):
    ir = extract_source(tmp_path, {"c.cc": (
        "#include <sys/time.h>\n#ifdef OLD\nstruct timeval { long s; };\n#endif\n"
        "struct Clock { timeval tv; };\n"
        "#ifdef OLD\nstruct Old { timeval tv; };\n#endif\n")})
    assert not _rels(ir, "Clock")
    assert "#if branch" in _unresolved(ir, "Clock")["timeval"]
    assert _rels(ir, "Old") == {("timeval", "tv")}   # the branch of its condition sees it


def test_a_dependent_base_is_not_looked_into(tmp_path):
    ir = extract_source(tmp_path, {"v.h": (
        "struct Inner {};\ntemplate <class T> struct TBase { struct Inner {}; };\n"
        "template <class T> struct Vec : TBase<T> { Inner i; };\n"
        "struct Fixed : TBase<int> { Inner j; };\n")})
    assert ("Inner", "i") in _rels(ir, "Vec")
    assert ("TBase::Inner", "j") in _rels(ir, "Fixed")


def test_a_rooted_name_is_the_global_namespaces(tmp_path):
    ir = extract_source(tmp_path, {"d.h": (
        "struct D {};\nnamespace shop { struct D {}; struct Y { ::D g; D h; }; }\n")})
    assert _rels(ir, "shop::Y") == {("D", "g"), ("shop::D", "h")}


def test_a_namespace_alias_of_the_file(tmp_path):
    ir = extract_source(tmp_path, {"z.h": (
        "namespace a { namespace inner { struct E {}; } }\nnamespace gs = a::inner;\n"
        "namespace near { namespace gs { struct E {}; } struct N { gs::E e; }; }\n"
        "struct Far { gs::E e; };\n")})
    assert _rels(ir, "Far") == {("a::inner::E", "e")}
    assert _rels(ir, "near::N") == {("near::gs::E", "e")}


def test_a_headers_using_declaration_where_it_is_included(tmp_path):
    ir = extract_source(tmp_path, {
        "g.h": "struct Money {};\n",
        "app/types.h": ("#include \"g.h\"\nnamespace lib { struct Money {}; }\n"
                        "namespace app { using lib::Money; }\n"),
        "app/user.cc": ("#include \"app/types.h\"\n"
                        "namespace app { struct User { Money m; }; }\n")})
    assert _rels(ir, "app::User") == {("lib::Money", "m")}


def test_a_nearer_namespaces_type_comes_before_a_using_declaration(tmp_path):
    ir = extract_source(tmp_path, {"w.h": (
        "namespace lib { struct Coin {}; }\nnamespace app { using lib::Coin; }\n"
        "namespace app { namespace in { struct Coin {}; struct W { Coin c; }; } }\n")})
    assert _rels(ir, "app::in::W") == {("app::in::Coin", "c")}


def test_an_alias_of_an_outside_templates_member_names_none_of_its_arguments(tmp_path):
    ir = extract_source(tmp_path, {"h.h": (
        "#include <vector>\n#include <utility>\nstruct Item {};\nstruct Var {};\n"
        "struct Holder { typedef std::vector<Item>::const_iterator It; bool first(It& i); };\n"
        "template <class K> struct Pair { using Data = typename std::pair<K, Var>; Data d; };\n")})
    assert not _rels(ir, "Holder")
    assert _rels(ir, "Pair") == {("Var", "d")}   # `typename std::pair<...>` is the pair


def test_a_classs_own_nested_type_defined_where_it_is_included(tmp_path):
    # the header does not see where Rep is defined, but a file including it does: drawn
    ir = extract_source(tmp_path, {
        "t.h": "class Table {\n public:\n  struct Rep;\n  Rep* rep_;\n};\n",
        "t.cc": "#include \"t.h\"\nstruct Table::Rep { int n; };\n",
        "u.h": "struct Reader { Table* t; };\n",
        "x.cc": "#include \"t.h\"\n#include \"u.h\"\n"})
    assert ("Table::Rep", "rep_") in _rels(ir, "Table")
    assert ("Table", "t") in _rels(ir, "Reader")   # u.h's includer brings Table in
