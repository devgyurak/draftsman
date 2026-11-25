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


def test_a_declaration_outside_every_if_branch_lets_the_type_be_drawn(tmp_path):
    # `class PollSetImpl;` outside every branch: the name is that type in every build, whichever
    # branch defines it; a body is not so (the body rule stands)
    ir = extract_source(tmp_path, {
        "p.h": ("#pragma once\nnamespace net {\nclass PollSetImpl;\n"
                "class PollSet { PollSetImpl* _pImpl; };\n}\n"),
        "p.cc": ("#include \"p.h\"\nnamespace net {\n#if defined(EPOLL)\n"
                 "class PollSetImpl { int ep; };\n#elif defined(POLL)\n"
                 "class PollSetImpl { int sel; };\n#endif\n}\n"),   # (no #else: not every build)
        "v.h": ("#pragma once\nnamespace d {\n#ifndef DOC\nstruct Hash {};\n#endif\n"
                "struct Visitor { Hash h; };\n}\n")})
    assert _rels(ir, "net::PollSet") == {("net::PollSetImpl", "_pImpl")}
    assert not _rels(ir, "d::Visitor")
    assert "#if branch" in _unresolved(ir, "d::Visitor")["Hash"]


def _body(ir, src: str) -> set[str]:
    return {r.to for r in ir.relations if r.from_ == src and r.evidence == "body"}


def test_names_are_looked_up_in_the_base_the_relation_is_drawn_to(tmp_path):
    # one answer for a base clause (Resolver.supertypes): the base drawn is the one a
    # member's type, a parameter's and a body's names are looked up in
    ir = extract_source(tmp_path, {
        "g.h": "#pragma once\nstruct Inner {};\nstruct Base { struct Inner {}; };\n",
        "lib.h": ("#pragma once\n#include \"g.h\"\n"
                  "namespace lib { struct Base { struct Inner {}; struct Deep {}; }; }\n"),
        "t1.h": ("#include \"lib.h\"\nnamespace la = lib;\nnamespace t1 {\n"
                 "struct C : la::Base { Inner i_; Deep d_; int f() { Inner x; return 0; } };\n}\n"),
        "t2.h": ("#include \"g.h\"\nnamespace t2 {\nstruct Base {};\n"
                 "struct G : ::Base { Inner i_; int f() { Inner x; return 0; } };\n}\n"),
        "t3.h": ("#include \"lib.h\"\nnamespace t3 {\nusing lib::Base;\nnamespace in {\n"
                 "struct Base {};\nstruct W : Base { Inner i_; int f() { Inner x; return 0; } };\n}\n}\n"),
        "t4/types.h": "#include \"lib.h\"\nnamespace t4 { using lib::Base; }\n",
        "t4/user.cc": ("#include \"t4/types.h\"\nnamespace t4 {\n"
                       "struct User : Base { Inner i_; int f() { Inner x; return 0; } };\n}\n"),
        "a/base.h": "#pragma once\nstruct Root { struct Inner {}; };\n",
        "b/gen.h": "#pragma once\nnamespace gen { struct Root {}; }\n",
        "b/main.cc": ("#include \"g.h\"\n#include \"b/gen.h\"\nusing namespace gen;\n"
                      "struct M : Root { Inner i_; int f() { Inner x; return 0; } };\n")})
    assert _rels(ir, "t1::C") == {("lib::Base", None), ("lib::Base::Inner", "i_"),
                                  ("lib::Base::Deep", "d_")}
    assert "lib::Base::Inner" in _body(ir, "t1::C")
    assert _rels(ir, "t2::G") == {("Base", None), ("Base::Inner", "i_")}
    assert "Base::Inner" in _body(ir, "t2::G")
    assert _rels(ir, "t3::in::W") == {("t3::in::Base", None), ("Inner", "i_")}
    assert "Inner" in _body(ir, "t3::in::W")
    assert _rels(ir, "t4::User") == {("lib::Base", None), ("lib::Base::Inner", "i_")}
    assert "lib::Base::Inner" in _body(ir, "t4::User")
    assert _rels(ir, "M") == {("gen::Root", None), ("Inner", "i_")}
    assert "Inner" in _body(ir, "M")


def test_names_past_a_base_whose_members_are_not_known_are_not_drawn(tmp_path):
    # PlatBase is a type of an `#if` branch the class is outside of: unresolved, and what it
    # has is not known; a name found in the class or another base is still drawn, one found
    # further out may be its member
    ir = extract_source(tmp_path, {"p.h": (
        "#pragma once\nstruct Handle { static int n; };\nstruct Other { struct Tag {}; };\n"
        "namespace plat {\n"
        "#ifdef _WIN32\nstruct PlatBase { struct Handle { void* h; }; };\n#endif\n"
        "struct File : PlatBase, Other {\n  struct Own {};\n"
        "  Handle h_;\n  Tag t_;\n  Own o_;\n"
        "  int f() { Handle x; Tag y; return 0; }\n  int g() { return Handle::n; }\n};\n}\n")})
    rels = _rels(ir, "plat::File")
    assert ("Handle", "h_") not in rels
    assert {("Other", None), ("Other::Tag", "t_"), ("plat::File::Own", "o_")} <= rels
    assert "base PlatBase" in _unresolved(ir, "plat::File")["Handle"]
    assert _body(ir, "plat::File") == {"Other::Tag"}


def test_a_base_of_a_file_not_included_hides_names_too(tmp_path):
    ir = extract_source(tmp_path, {
        "a/base.h": "#pragma once\nstruct Root { struct Inner {}; };\n",
        "b/g.h": "#pragma once\nstruct Inner {};\n",
        "b/main.cc": ("#include \"g.h\"\nstruct M : Root { Inner i_; "
                      "int f() { Inner x; return 0; } };\n")})
    assert not _rels(ir, "M")
    assert "base Root" in _unresolved(ir, "M")["Inner"]
    assert not _body(ir, "M")


def test_a_type_every_branch_of_an_if_chain_declares_is_drawn(tmp_path):
    ir = extract_source(tmp_path, {"p.h": (
        "#pragma once\nstruct Handle {};\nnamespace plat {\n"
        "#ifdef _WIN32\nstruct PlatBase { struct Handle { void* h; }; };\n"
        "#elif defined(__APPLE__)\nstruct PlatBase { struct Handle { long m; }; };\n"
        "#else\nstruct PlatBase { struct Handle { int fd; }; };\n#endif\n"
        "#ifdef A\nstruct Half {};\n#elif defined(B)\nstruct Half {};\n#endif\n"
        "struct File : PlatBase { Handle h_; int f() { Handle x; return 0; } };\n"
        "struct Uses { PlatBase b_; Half h_; };\n}\n")})
    assert _rels(ir, "plat::File") == {("plat::PlatBase", None),
                                       ("plat::PlatBase::Handle", "h_")}
    assert not _body(ir, "plat::File")   # a body's `#if` rule stands
    assert _rels(ir, "plat::Uses") == {("plat::PlatBase", "b_")}   # no #else: Half is not
    assert "#if branch" in _unresolved(ir, "plat::Uses")["Half"]


def test_a_base_written_as_an_alias_of_one_class_is_looked_into(tmp_path):
    ir = extract_source(tmp_path, {"c.h": (
        "#pragma once\nstruct Inner {};\nnamespace lib { struct Base { struct Inner {}; }; }\n"
        "typedef lib::Base LB;\nusing LU = lib::Base;\n"
        "struct D : LB { Inner i_; int f() { Inner x; return 0; } };\n"
        "struct E : LU { Inner i_; };\n")})
    assert _rels(ir, "D") == {("lib::Base", None), ("lib::Base::Inner", "i_")}
    assert _body(ir, "D") == {"lib::Base::Inner"}
    assert _rels(ir, "E") == {("lib::Base", None), ("lib::Base::Inner", "i_")}
