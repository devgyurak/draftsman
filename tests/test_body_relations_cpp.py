"""Relations read from names written in C++ bodies (`evidence` "body", issue #5)."""

import sys
from pathlib import Path

from conftest import extract_source
from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.resolve import _Builder
from draftsman.wrappers import Wrappers

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
from answer_key import expected  # noqa: E402   the hand-written answers' markers

# tests/fixtures/cpp/body, which `bench/clang_oracle/oracle.py selftest` checks against Clang
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cpp" / "body"
SUFFIXES = (".h", ".cc")


def _fixture() -> list:
    return [Extractor(spec_for_path(p.name)).extract(p, p.relative_to(FIXTURE).as_posix(), FIXTURE)
            for p in sorted(FIXTURE.rglob("*")) if p.suffix in SUFFIXES]


def test_body_names_stand_where_the_hand_written_answers_say():
    # every part of a name the extractor records is in the position its marker gives ("r"
    # for a call or a base's initializer, which a value may be as well); a recorded name no
    # marker lists is no name of a type
    want = expected(FIXTURE, SUFFIXES)
    problems = []
    for raw in _fixture():
        refs = [r for t in raw.types for r in t.body_refs] + [r for *_, r in raw.scope.detached_refs]
        for r in refs:
            parts = r.text.lstrip(":").split("::")
            for i, (part, (line, col)) in enumerate(zip(parts, r.places)):
                answer, position = want.get((raw.path, line, col), (None, None))
                where = f"{raw.path}:{line}:{col + 1} {part} of {r.text}"
                # a call's qualifier stands where only a type or a namespace may
                expect = "type" if r.position == "type" or r.position == "call" \
                    and i < len(parts) - 1 else "receiver"
                if answer == "-":
                    problems.append(f"{where}: no name in a body, recorded as {r.position}")
                elif answer is not None and position != expect:
                    problems.append(f"{where}: {r.position}, the marker says {position}")
    assert problems == []


def _built():
    builder = _Builder("body", _fixture(), Wrappers.load())
    builder.build()
    return builder


def test_body_relations_go_where_the_hand_written_answers_say():
    want = expected(FIXTURE, SUFFIXES)
    builder = _built()
    wrong, drawn = [], set()
    # an alias stands for every type it names; a marker gives the first
    also = {"lib::AutoPtr": {"lib::Channel"}, "shop::Lock": {"shop::FastMutex"}}
    for file, line, col, _, to in builder.body_uses:
        drawn.add((file, line, col))
        answer, _ = want[(file, line, col)]
        if answer != to and to not in also.get(answer, ()):
            wrong.append((file, line, answer, to))
    assert wrong == []
    # every project type named in a body of a type is drawn but code outside every type (a
    # free function: `useA()`, `macros()`), a specialisation's (`Box<Money>`), the type's
    # own name (`Order` in Order's own bodies), the part of a longer name (`Order` in
    # `Order::Line`), the system's type of a name
    # a branch no build takes declares (`timeval`), and what follows an `#if` that opens a
    # block in each branch (Clock::price)
    missed = sorted({(rel, line, answer) for (rel, line, col), (answer, _) in want.items()
                     if answer in builder.types and (rel, line, col) not in drawn})
    assert missed == [
        ("shop/anon_a.cc", 11, "shop::State"),
        ("shop/anon_b.cc", 11, "shop::State"), ("shop/hiding.cc", 10, "shop::Order"),
        ("shop/hiding.cc", 24, "shop::Base"), ("shop/hiding.cc", 25, "shop::Base"),
        ("shop/hiding.cc", 35, "shop::Money"), ("shop/hiding.cc", 37, "shop::Money"),
        ("shop/hiding.cc", 43, "lib::Channel"), ("shop/hiding.cc", 45, "lib::AutoPtr"),
        ("shop/hiding.cc", 45, "lib::Channel"), ("shop/hiding.cc", 56, "shop::Money"),
        ("shop/lookup.cc", 125, "timeval"), ("shop/lookup.cc", 148, "shop::Money"),
        ("shop/order.cc", 30, "shop::Order"), ("shop/order.cc", 31, "shop::Order"),
        ("shop/order.cc", 43, "shop::Order")]


def _body(ir) -> list[tuple]:
    return sorted((r.from_, r.to, r.source_location.line)
                  for r in ir.relations if r.evidence == "body")


def test_a_member_defined_out_of_its_class_is_the_classs(tmp_path):
    # its body, its constructor's initializers, a static member's initializer; a
    # specialisation's member (`template <>`) and a free function draw nothing
    ir = extract_source(tmp_path, {
        "a.h": "namespace s { struct Money {}; struct Base { Base(int) {} };\n"
               "template <class T> struct Box { void put(); };\n"
               "struct Order : Base { Order(); void f(); static int k; }; }\n",
        "a.cc": '#include "a.h"\nnamespace s {\n'
                "Order::Order() : Base(1) { Money m; }\n"
                "void Order::f() { Money m; }\n"
                "int Order::k = sizeof(Money);\n"
                "template <class T> void Box<T>::put() { Money m; }\n"
                "template <> void Box<int>::put() { Money m; }\n"
                "void free() { Money m; }\n}\n"})
    assert _body(ir) == [("s::Box", "s::Money", 6), ("s::Order", "s::Base", 3),
                         ("s::Order", "s::Money", 3), ("s::Order", "s::Money", 4),
                         ("s::Order", "s::Money", 5)]


def test_a_definitions_own_template_parameters_are_no_types(tmp_path):
    ir = extract_source(tmp_path, {
        "a.h": "struct U {}; struct V {};\nstruct Box { template <class U> void put(U u); "
               "void get(); };\n",
        "a.cc": '#include "a.h"\ntemplate <class U> void Box::put(U u) { U copy = u; V v; }\n'})
    assert _body(ir) == [("Box", "V", 2)]


def test_an_anonymous_namespaces_type_is_its_files_only(tmp_path):
    ir = extract_source(tmp_path, {
        "a.cc": "namespace s { namespace { struct State {}; }\nstruct A { void f() { State x; } }; }\n",
        "b.cc": "struct State {};\nnamespace s { struct B { void f() { State x; } }; }\n"})
    assert _body(ir) == [("s::A", "s::State", 2), ("s::B", "State", 2)]


def test_a_type_of_a_file_not_included_is_passed_over(tmp_path):
    # the lookup goes on past another program's Utility to the one `using namespace gen`
    # brings in; a declaration the file sees (`struct Fwd;`) stops it: the name is that type
    ir = extract_source(tmp_path, {
        "g.h": "struct Fwd {};\n",
        "app/fwd.h": "namespace app { struct Fwd {}; }\n",
        "app/use.cc": '#include "../g.h"\nnamespace app { struct Fwd;\nstruct K { void f(Fwd* p) { Fwd* q = p; } }; }\n'})
    assert _body(ir) == [("app::K", "app::Fwd", 3)]
    ir = extract_source(tmp_path / "2", {
        "a/util.h": "struct Utility { static int run(); };\n",
        "b/gen.h": "namespace gen { struct Utility { static int run(); }; }\n",
        "b/main.cc": '#include "gen.h"\nusing namespace gen;\nstruct M { int f() { return Utility::run(); } };\n',
        "a/tool.cc": '#include "util.h"\nstruct T { int f() { return Utility::run(); } };\n'})
    assert _body(ir) == [("M", "gen::Utility", 3), ("T", "Utility", 2)]


def test_a_type_of_an_if_branch_is_its_branchs_only(tmp_path):
    ir = extract_source(tmp_path, {
        "a.cc": "#ifdef OLD\nstruct Clock {};\nstruct In { void f() { Clock c; } };\n#endif\n"
                "struct Out { void f() { Clock c; } };\n"})
    assert _body(ir) == [("In", "Clock", 3)]


def test_a_variable_or_a_method_hides_a_type_also_where_a_type_stands(tmp_path):
    ir = extract_source(tmp_path, {
        "a.h": "struct Money {}; struct Tag {}; struct Guard { Guard(int) {} };\n"
               "struct A { int Tag = 0; void f() { Guard g(Tag); } int Money() { return 0; }\n"
               "  void g() { Money(); } };\n"
               "struct B { void f() { Tag t; Money m; } };\n"})
    assert _body(ir) == [("A", "Guard", 2), ("B", "Money", 4), ("B", "Tag", 4)]


def test_a_qualifier_is_a_type_or_a_namespace(tmp_path):
    # `Kind::A`: the enum; `ns::Money(1)`; `Keywords::now()` with a namespace Keywords
    # nearer than the type: nothing
    ir = extract_source(tmp_path, {
        "a.h": "struct Keywords { static int now(); };\nnamespace s {\n"
               "namespace Keywords { int now(); }\nenum class Kind { A };\nstruct Money { Money(int) {} };\n"
               "struct U { int f() { Kind k = Kind::A; Money m = s::Money(1); return Keywords::now(); } }; }\n"})
    assert _body(ir) == [("s::U", "s::Kind", 6), ("s::U", "s::Money", 6)]


def test_an_alias_stands_for_the_types_it_names(tmp_path):
    # as a declared relation's: `typedef AutoPtr<Channel> Ptr;`; not an alias template's
    # own parameters (`Hash`)
    ir = extract_source(tmp_path, {
        "a.h": "#include <map>\ntemplate <class C> struct AutoPtr {};\nstruct Channel { typedef AutoPtr<Channel> Ptr; };\n"
               "struct Hash {};\ntemplate <class K, class Hash = int> using Table = std::map<K, Hash>;\n"
               "struct U { void f() { Channel::Ptr p; Table<int> t; } };\n"})
    assert _body(ir) == [("U", "AutoPtr", 6), ("U", "Channel", 6)]


def test_cpp_and_another_language_name_none_of_each_others_types(tmp_path):
    # a C++ struct of the global namespace is no C# class of the name
    ir = extract_source(tmp_path, {
        "native/helper.h": "struct Helper {};\nstruct User { void f() { Helper h; } };\n",
        "app/Far.cs": "namespace Shop { class Far { Helper field; void F() { var h = new Helper(); } } }\n"})
    assert _body(ir) == [("User", "Helper", 2)]
    assert not [r for r in ir.relations if r.from_ == "Shop.Far"]


def test_an_unscoped_enums_constant_hides_a_type_where_a_value_may_stand(tmp_path):
    # of the class (`enum St { Shut }`) and of a namespace around (`enum Kind { Paid }`);
    # not one of an `enum class`
    ir = extract_source(tmp_path, {
        "a.h": "struct Paid {}; struct Shut {}; struct Open {};\n"
               "namespace s { enum Kind { Paid }; enum class E { Open };\n"
               "struct Lock { Lock(int) {} Lock(::Paid) {} };\n"
               "struct O { enum St { Shut };\n"
               "  void f() { Lock l(Paid); int n = sizeof(Shut) + sizeof(Open); } }; }\n"})
    assert _body(ir) == [("s::O", "Open", 5), ("s::O", "s::Lock", 5)]


def test_a_dependent_base_is_not_looked_into(tmp_path):
    # `TBase<T>`'s nested types and fields are found once T is known; `TBase<int>`'s now
    ir = extract_source(tmp_path, {
        "a.h": "struct Inner {}; struct Helper {};\n"
               "template <class T> struct TBase { struct Inner {}; int Helper; };\n"
               "template <class T> struct Vec : TBase<T> { void f() { Inner i; Helper h; } };\n"
               "struct Fixed : TBase<int> { void f() { Inner i; } };\n"})
    assert _body(ir) == [("Fixed", "TBase::Inner", 4), ("Vec", "Helper", 3), ("Vec", "Inner", 3)]


def test_a_type_of_an_if_branch_is_seen_in_branches_of_its_condition(tmp_path):
    ir = extract_source(tmp_path, {
        "a.h": "#if defined(V6)\nstruct Impl6 {};\n#endif\n",
        "b.cc": '#include "a.h"\nstruct U {\n  void f() {\n#if defined(V6)\n    Impl6 x;\n'
                "#endif\n  }\n  void g() { Impl6 y; }\n};\n"})
    assert _body(ir) == [("U", "Impl6", 5)]


def test_a_namespace_alias_of_the_files_scope_is_read(tmp_path):
    ir = extract_source(tmp_path, {
        "a.cc": "namespace a { namespace inner { struct D {}; } }\nnamespace fs = a::inner;\n"
                "struct U { void f() { fs::D d; } };\n"})
    assert _body(ir) == [("U", "a::inner::D", 3)]


def test_a_function_without_a_return_type_hides_no_call(tmp_path):
    # `Money(int c);` an error left at a namespace's scope (a constructor of a specialisation
    # the grammar lost, POCO's Delegate.h) is no function a call `Money(1)` may be
    ir = extract_source(tmp_path, {
        "a.h": "namespace s { struct Money { Money(int) {} };\nMoney(int c);\n"
               "int Ticket(int n);\nstruct Ticket { Ticket(int) {} };\n"
               "struct U { void f() { Money(1); Ticket(2); } }; }\n"})
    assert _body(ir) == [("s::U", "s::Money", 5)]


def test_a_bases_own_bases_are_looked_into(tmp_path):
    # only the bases of the class and the classes around it may be dependent: `ViaPtr<int>`
    # is known, and so is its `TBase<T*>` (`TBase<int*>`): its nested types and its field
    ir = extract_source(tmp_path, {
        "a.h": "struct Inner {}; struct Deep {}; struct Helper {};\n"
               "template <class T> struct TBase { struct Inner {}; struct Deep {}; int Helper; };\n"
               "template <class T> struct ViaPtr : TBase<T*> { void f() { Inner i; } };\n"
               "struct Leaf : ViaPtr<int> { void f() { Inner i; Deep d; int n = sizeof(Helper); } };\n"
               "template <class T> struct Chain : ViaPtr<int> { void f() { Inner i; } };\n"})
    assert _body(ir) == [("Chain", "TBase::Inner", 5), ("Leaf", "TBase::Deep", 4),
                         ("Leaf", "TBase::Inner", 4), ("ViaPtr", "Inner", 3)]


def test_a_namespace_alias_gives_way_to_a_nearer_namespace_or_class(tmp_path):
    ir = extract_source(tmp_path, {
        "a.cc": "namespace a { namespace inner { struct D {}; struct E {}; } }\n"
                "namespace fs = a::inner;\nnamespace gs = a::inner;\n"
                "namespace shop { namespace fs { struct D {}; }\n"
                "struct X { struct gs { struct D {}; };\n"
                "  void f() { fs::D d; } void g() { gs::D d; } };\n"
                "struct Y { void f() { gs::E e; } }; }\n"})
    assert _body(ir) == [("shop::X", "shop::X::gs::D", 6), ("shop::X", "shop::fs::D", 6),
                         ("shop::Y", "a::inner::E", 7)]


def test_a_type_a_file_may_see_without_including_it_stops_the_lookup(tmp_path):
    # a file including the body's file sees the type (`foo_inl.h` at the end of `foo.h`),
    # or the file includes a path a macro makes: no draw, and no other type of the name
    ir = extract_source(tmp_path, {
        "g.h": "struct Helper {}; struct Util {};\n",
        "app/foo.h": '#pragma once\nnamespace app { struct Helper {}; struct Foo { int run(); }; }\n'
                     '#include "app/foo_inl.h"\n',
        "app/foo_inl.h": '#include "g.h"\nnamespace app { inline int Foo::run() { Helper h; return 0; } }\n',
        "app/util.h": "namespace app { struct Util {}; }\n",
        "app/macro.cc": '#include "g.h"\n#define U "app/util.h"\n#include U\n'
                        "namespace app { struct M { void f() { Util u; } }; }\n"})
    assert _body(ir) == []


def test_a_template_or_enum_declared_only_is_that_type(tmp_path):
    ir = extract_source(tmp_path, {
        "g.h": "struct Mode {}; template <class T> struct Box {};\n",
        "app/defs.h": "namespace app { template <class T> struct Box {}; enum class Mode : int { On }; }\n",
        "app/fwd.h": "namespace app { template <class T> struct Box; enum class Mode : int; }\n",
        "app/use.cc": '#include "g.h"\n#include "app/fwd.h"\n'
                      "namespace app { struct F { void f(Box<int>* b, Mode m) { Box<int>* c = b; Mode n = m; } }; }\n"})
    assert _body(ir) == [("app::F", "app::Box", 3), ("app::F", "app::Mode", 3)]


def test_an_if_condition_is_read_with_the_lines_it_continues(tmp_path):
    ir = extract_source(tmp_path, {
        "a.h": "struct Gate {};\nnamespace s {\n#if defined(A) && \\\n    defined(B)\nstruct Gate {};\n#endif\n}\n",
        "b.cc": '#include "a.h"\nnamespace s { struct C {\n#if defined(A) && \\\n    defined(C)\n'
                "  void f() { Gate g; }\n#endif\n#if defined(A) && \\\n    defined(B)\n"
                "  void g() { Gate g; }\n#endif\n}; }\n"})
    assert _body(ir) == [("s::C", "s::Gate", 9)]


def test_a_function_of_an_if_branch_hides_a_call(tmp_path):
    # a namespace's; not a method of a class's `#if` branch
    ir = extract_source(tmp_path, {
        "g.h": "struct Rate { Rate(int) {} }; struct Fee { Fee(int) {} };\n",
        "s/fns.h": '#include "g.h"\nnamespace s {\n#ifdef EARLY\nint Rate(int);\n#endif\n'
                   "struct K {\n#ifdef X\n  int Fee(int n) { return n; }\n#endif\n}; }\n",
        "s/c.cc": '#include "s/fns.h"\nnamespace s { struct C { void f() { Rate(1); Fee(2); } }; }\n'})
    assert _body(ir) == [("s::C", "Fee", 2)]


def test_an_enumerator_hides_a_type_only_where_a_value_may_stand_and_as_near(tmp_path):
    # the namespace's struct Cash is nearer than the global `enum Coin { Cash }`
    ir = extract_source(tmp_path, {
        "a.h": "enum Coin { Cash };\nstruct Gold {};\n"
               "namespace s { struct Cash {}; enum Metal { Gold };\n"
               "struct M { void f() { Cash c; int n = sizeof(Cash); }\n"
               "  void g() { int n = sizeof(Gold); }\n  void h() { Gold g; } }; }\n"})
    assert _body(ir) == [("s::M", "Gold", 6), ("s::M", "s::Cash", 4)]
