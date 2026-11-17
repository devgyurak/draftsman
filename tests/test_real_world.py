"""Regressions found by running Draftsman on real projects (see README: smoke tests)."""

from conftest import extract_source


def rels(ir):
    return {(r.from_, r.kind, r.to) for r in ir.relations}


def test_cpp_export_and_attribute_macros(tmp_path):
    ir = extract_source(tmp_path, {
        "status.h": "namespace db {\nclass DB_EXPORT Status { int code_; };\n}\n",
        "env.h": '#include "status.h"\nnamespace db {\n'
                 "class Mutex {};\n"
                 "class DB_EXPORT Env {\n public:\n  virtual Status Open() = 0;\n"
                 "  DB_EXPORT static Env* Default();\n"
                 " private:\n  Mutex mu_;\n  int x_ GUARDED_BY(mu_);\n"
                 "  Lock(Mutex* m) EXCLUSIVE_LOCK_FUNCTION(m) : m_(m) {}\n};\n}\n",
    })
    assert {t.id for t in ir.types} >= {"db::Status", "db::Env"}
    assert not ir.diagnostics
    assert ("db::Env", "dependency", "db::Status") in rels(ir)
    assert not ir.unresolved
    env = next(t for t in ir.types if t.id == "db::Env")
    assert env.location.line == 4  # blanking keeps line numbers


def test_cpp_directive_inside_initializer_list(tmp_path):
    ir = extract_source(tmp_path, {"a.cc": (
        "namespace n {\nclass Limiter {\n public:\n  Limiter(int m)\n      :\n"
        "#if !defined(NDEBUG)\n        max_(m),\n#endif\n        allowed_(m) {}\n"
        " private:\n  int max_;\n  int allowed_;\n};\nclass Env { Limiter limiter_; };\n}\n")})
    assert {t.id for t in ir.types} == {"n::Limiter", "n::Env"}   # Env is not nested
    assert ("n::Env", "association", "n::Limiter") in rels(ir)


def test_cpp_out_of_class_nested_definition(tmp_path):
    ir = extract_source(tmp_path, {
        "table.h": "namespace db {\nclass Table {\n  struct Rep;\n  Rep* rep_;\n};\n}\n",
        "table.cc": '#include "table.h"\nnamespace db {\nstruct Table::Rep { int size; };\n}\n',
    })
    rep = next(t for t in ir.types if t.name == "Rep")
    assert rep.id == "db::Table::Rep" and rep.outer == "db::Table"
    assert ("db::Table", "association", "db::Table::Rep") in rels(ir)


def test_aliases_are_not_unresolved(tmp_path):
    ir = extract_source(tmp_path, {
        "a.ts": "type Handler = (x: number) => void;\nexport class A { h: Handler; }\n",
        "b.py": "from typing import Callable\nHook = Callable[[int], None]\n"
                "class B:\n    def __init__(self, hook: Hook) -> None:\n        self.hook = hook\n",
        "c.kt": "package c\ntypealias Ids = List<Long>\nclass C(val ids: Ids)\n",
        "d.cs": "using Ids = System.Collections.Generic.List<long>;\n"
                "namespace D { class E { Ids ids; } }\n",
        "e.h": "typedef unsigned long long Seq;\nusing Fn = int(*)(int);\n"
               "typedef int (*BlockFunction)(void*);\n"
               "class F { Seq s; Fn f; BlockFunction b; unsigned int n; };\n",
    })
    assert ir.unresolved == []


def test_typescript_inline_object_types_are_not_members(tmp_path):
    ir = extract_source(tmp_path, {"f.ts": (
        "export interface Factory {\n  make<TReq>(key: string, { req }: { req: TReq }): void;\n}\n")})
    (t,) = ir.types
    assert [m.name for m in t.members] == ["make"]
    assert ir.unresolved == []


def test_typescript_enum_member_as_type(tmp_path):
    ir = extract_source(tmp_path, {
        "v.ts": "export enum Kind { URI, HEADER }\n"
                "export interface UriOptions { type: Kind.URI; }\n"})
    assert ("v.UriOptions", "association", "v.Kind") in rels(ir)
    assert ir.unresolved == []


def test_typescript_global_builtins_as_supertypes(tmp_path):
    ir = extract_source(tmp_path, {"m.ts": "export class Modules extends Map<string, number> {}\n"})
    assert ir.unresolved == []
    assert [e.id for e in ir.externals] == ["Map"]


# ------------------------------------------------------------------ POCO (2ef5cec8a9)

def _members(ir, tid):
    from draftsman.graph import member_text
    return [member_text(m) for m in next(t for t in ir.types if t.id == tid).members]


def test_cpp_directives_after_other_directives(tmp_path):
    """`#define MIN(a, b) (...)`, `#pragma pack(push, 1)` end with `)`, but they are no code
    line: the `#endif` after them is not inside an expression. A group is blanked or kept
    as a whole (String.h: `#pragma clang loop unroll(enable)` then `#elif`)."""
    ir = extract_source(tmp_path, {
        "min.h": "#ifndef MIN\n#define MIN(a, b) ((a) < (b) ? (a) : (b))\n#endif\nclass P {};\n",
        "api.h": ("#if defined(_WIN32)\n#define API __declspec(dllexport)\n#else\n"
                  "#define API __attribute__((visibility(\"default\")))\n#endif\nclass Q {};\n"),
        "pack.h": "#ifdef __GNUC__\n#pragma pack(push, 1)\n#endif\nclass R { P* p; };\n",
        "loop.h": ("#if defined(__clang__)\n#pragma clang loop unroll(enable)\n"
                   "#elif defined(_MSC_VER)\n#pragma loop(ivdep)\n#endif\nclass S { Q* q; };\n"),
        "cont.h": "#if X\n#define F(a, \\\n   b) (a + b)\n#endif\nclass T { R* r; };\n",
    })
    assert not ir.diagnostics
    assert {(r.from_, r.to) for r in ir.relations} == {("R", "P"), ("S", "Q"), ("T", "R")}


def test_cpp_export_macros_by_position(tmp_path):
    ir = extract_source(tmp_path, {"a.h": (
        "namespace Poco {\n"
        "class Foundation_API Channel {};\n"
        "class Foundation_API Logger: public Channel { Channel* _pChannel; };\n"
        "class NetSSL_Win_API Context final : public Channel {};\n"
        "class DNSSD_Bonjour_API HTTPCookie {};\n"
        "class MyLib_Decl(x) Other {};\n"
        "class API DEPRECATED Twice : public Channel {};\n"
        "class Plain final { Channel* c; };\n"
        "Net_API std::ostream& operator << (std::ostream& o, const Channel& c);\n"
        "[[nodiscard]] AIMCP_API bool sameId(const Channel& a);\n"
        "std::string CppParser_API replace(const std::string& input);\n"
        "struct Point { int x, y; };\n"
        "struct Point origin{0, 0};\n"          # variables, not class heads
        "struct sockaddr_in addr{};\n"
        "enum Access { ACC_PUBLIC, ACC_PRIVATE };\n"
        "class Sym { bool isPublic() const { return _access == ACC_PUBLIC; }\n"
        "  int f(int x) { switch (x) { case ACC_PUBLIC: return ACC_PUBLIC; } return x; }\n"
        "  Access _access; };\n"
        "}\n")})
    assert not ir.diagnostics
    assert {t.id for t in ir.types} == {
        "Poco::Channel", "Poco::Logger", "Poco::Context", "Poco::HTTPCookie", "Poco::Other",
        "Poco::Twice", "Poco::Plain", "Poco::Point", "Poco::Access", "Poco::Sym"}
    assert {("Poco::Logger", "extends", "Poco::Channel"), ("Poco::Context", "extends", "Poco::Channel"),
            ("Poco::Twice", "extends", "Poco::Channel")} <= rels(ir)
    assert _members(ir, "Poco::Access") == ["ACC_PUBLIC", "ACC_PRIVATE"]


def test_cpp_names_missing_from_project_namespaces(tmp_path):
    """A qualified name into a namespace the project declares types in, that is not there,
    is unresolved only when something says the project may declare it where the parser
    could not see: a macro it is passed to, or a class head inside a syntax error.
    Otherwise it is a library's (a project may extend a library's namespace), and std
    never is the project's."""
    ir = extract_source(tmp_path, {
        "data.h": ("namespace Poco { namespace Data {\nclass Base {};\n"
                   "POCO_DECLARE_EXCEPTION(Data_API, DataException, Base)\n"
                   "POCO_DECLARE_EXCEPTION(XML_API, XMLException, Base)\n"
                   "class X : public Poco::Data::XMLException {};\n"
                   "class MySQLException : public Poco::Data::DataException {};\n"
                   "class A { Poco::Data::Broken* b; };\n} }\n"),
        # a lower-case macro the preprocessing does not know: the class does not parse
        "broken.h": "namespace Poco { namespace Data {\nclass dll_export Broken : public Base { int a; };\n} }\n",
        "util.h": ("namespace Poco { namespace Util { class MyExtension {}; } }\n"
                   "class Server : public Poco::Util::ServerApplication { Poco::Util::Timer t; };\n"),
        "std.h": ("namespace std { template<> struct hash<Poco::Data::Base> { int x; };\n"
                  "class MyStdThing {};\nclass std_api Mine : x { int a; }; }\n"
                  "class D : public std::exception {};\nclass E : public std::Mine {};\n"),
    })
    assert {("Server", "extends", "Poco::Util::ServerApplication"),
            ("D", "extends", "std::exception"), ("E", "extends", "std::Mine")} <= rels(ir)
    hints = {u.raw_type: u.hint for u in ir.unresolved}
    assert hints.get("Poco::Data::DataException") == (
        "the project's namespace Poco::Data declares no type DataException the parser saw; "
        "POCO_DECLARE_EXCEPTION(...) at data.h:3 may declare it")
    assert "Poco::Data::XMLException" in hints and "XML_API" not in {u.raw_type for u in ir.unresolved}
    assert hints.get("Poco::Data::Broken") == (
        "the project's namespace Poco::Data declares no type Broken the parser saw; "
        "its declaration in broken.h:2-2 did not parse")
    assert not any(e.id.startswith("Poco::Data::") for e in ir.externals)


def test_cpp_base_class_names_are_in_scope(tmp_path):
    """`CodeGenerator::Properties` in a subclass of CodeGenerator (also through another
    base): the base's name is in the derived class's scope."""
    ir = extract_source(tmp_path, {"a.h": (
        "namespace Poco { namespace CodeGeneration {\n"
        "class CodeGenerator { public: struct Properties {}; }; } }\n"
        "class Mid : public Poco::CodeGeneration::CodeGenerator {};\n"
        "class AbstractGenerator : public Mid { CodeGenerator::Properties p; };\n"
        "class Ext : public lib::Base { Base* b; };\n"
        # a class's own name comes first: Listener in TCP::Listener is TCP::Listener
        "namespace tcp { class Listener : public lib::Listener {\n"
        "  public: using Ptr = Listener*;\n"
        "  class EventSubscription { Listener* owner; }; }; }\n"
        "namespace tcp { class ServerConnection { Listener::Ptr p; }; }\n")})
    assert not ir.unresolved
    assert ("AbstractGenerator", "association",
            "Poco::CodeGeneration::CodeGenerator::Properties") in rels(ir)
    assert {("tcp::Listener::EventSubscription", "association", "tcp::Listener"),
            ("tcp::ServerConnection", "association", "tcp::Listener")} <= rels(ir)


def test_cpp_statement_macros(tmp_path):
    ir = extract_source(tmp_path, {"a.h": (
        '#include "Poco/Foundation.h"\nPOCO_CHECK_MINMAX_MACROS\nPOCO_OTHER_STATEMENT\n'
        "namespace Poco {\nclass Exception {};\n"
        "POCO_DECLARE_EXCEPTION(Foundation_API, LogicException, Exception)\n"
        "POCO_DECLARE_EXCEPTION(Foundation_API, AssertionViolationException, LogicException) // x\n"
        "class Timestamp { Exception* e; };\n"
        "class Holder {\npublic:\n  Holder(): a(1),\n    MAX_SIZE(10)\n  {}\n  int a;\n"
        "  POCO_DECLARE_SOMETHING(Holder)\n  Timestamp t;\n};\n"
        "enum Single {\n  ONLY_ONE\n};\n"
        "enum Pair { FIRST_ONE = 1,\n  LAST_ONE\n};\n"
        "TEST_CASE(A, B)\n{\n}\n"
        "class W {\n  MY_TYPE\n  compute(Timestamp t);\n};\n"
        "}\n")})
    assert not ir.diagnostics
    assert {t.id for t in ir.types} == {"Poco::Exception", "Poco::Timestamp", "Poco::Holder",
                                         "Poco::Single", "Poco::Pair", "Poco::W"}
    # an upper-case word alone on its line, then `name(`: a return type, not a macro
    assert _members(ir, "Poco::W") == ["- compute(t: Timestamp): MY_TYPE"]
    assert _members(ir, "Poco::Single") == ["ONLY_ONE"]
    assert _members(ir, "Poco::Pair") == ["FIRST_ONE", "LAST_ONE"]
    assert _members(ir, "Poco::Holder") == ["+ Holder()", "+ a: int", "+ t: Timestamp"]
    # the macro's exception classes are not drawn: their users point at nothing invented
    assert ("Poco::Timestamp", "association", "Poco::Exception") in rels(ir)


def test_cpp_attribute_macros_before_declarations(tmp_path):
    ir = extract_source(tmp_path, {"a.h": (
        "namespace Poco {\nclass Notification {};\nclass Item {};\n"
        "class Foundation_API AbstractObserver\n{\npublic:\n"
        '\t[[nodiscard]] POCO_DEPRECATED("use `bool accepts(Notification::Ptr&)` instead")\n'
        "\tvirtual bool accepts(Notification* pNf) const;\n"
        '\tPOCO_DEPRECATED("old") void old(Notification* n);\n'
        "\ttemplate <class C>\n"
        '\tPOCO_DEPRECATED("use addNObserver() instead")\n'
        "\tvoid addObserver(C& object);\n};\n"
        "class Request {\npublic:\n\tPOCO_NODISCARD_CTOR Request(int x);\n"
        "\tMY_CTOR_MACRO Request(double y);\n\tPOCO_NODISCARD_INLINE Item make();\n"
        "\tHANDLE Open();\n\tDWORD f();\n\tBOOL ok();\n\tFILE* fp;\n\tSECURITY_STATUS s;\n};\n}\n")})
    assert not ir.diagnostics
    assert _members(ir, "Poco::AbstractObserver") == [
        "+ accepts(pNf: Notification*): bool", "+ old(n: Notification*): void",
        "+ addObserver(object: C&): void"]
    # a bare upper-case word before a declaration is a type
    assert _members(ir, "Poco::Request") == [
        "+ Request(x: int)", "+ Request(y: double)", "+ make(): Item", "+ Open(): HANDLE", "+ f(): DWORD", "+ ok(): BOOL",
        "+ fp: FILE*", "+ s: SECURITY_STATUS"]
    assert {u.raw_type for u in ir.unresolved} == {"HANDLE", "DWORD", "BOOL", "FILE", "SECURITY_STATUS"}


def test_cpp_attribute_macros_with_string_arguments(tmp_path):
    """A string argument may hold `;` and parentheses (MongoDB/Database.h lost the class)."""
    ir = extract_source(tmp_path, {"a.h": (
        "namespace Poco {\nclass Database {\npublic:\n  enum IndexOptions {\n    INDEX_UNIQUE = 1,\n"
        '    INDEX_BACKGROUND POCO_DEPRECATED("Deprecated since 4.2; builds are online") = 1 << 2,\n'
        "    INDEX_HIDDEN = 8\n  };\n"
        '  void old() POCO_DEPRECATED("use bar() instead");\n'
        '  void esc() POCO_DEPRECATED("say \\"hi\\"; (really)");\n  void bar();\n};\n}\n')})
    assert not ir.diagnostics
    assert _members(ir, "Poco::Database::IndexOptions") == [
        "INDEX_UNIQUE", "INDEX_BACKGROUND", "INDEX_HIDDEN"]
    assert _members(ir, "Poco::Database") == ["+ old(): void", "+ esc(): void", "+ bar(): void"]


def test_cpp_template_parameters_of_every_kind(tmp_path):
    """Values (`std::size_t N`, with a default, variadic, `auto`) and templates
    (`template <class> class C`) are template parameters too: in the template they hide a
    project type of the same name (`struct N`)."""
    ir = extract_source(tmp_path, {"a.h": (
        "namespace n {\nstruct N {};\nstruct P {};\n"
        "template <class T, std::size_t M> struct Array { T data[M]; };\n"
        "template <class T, std::size_t N> class Buf { Array<P, N> a; };\n"
        "template <std::size_t S = 64> class Sock { Array<P, S> b; };\n"
        "template <auto V> class Val { Array<P, V> d; };\n"
        "template <int... Is> class Seq { Array<P, Is...> e; };\n"
        "template <template <class> class C> class Wrap { C<P> c; };\n"
        "template <template <class> class D = Array> class Wrap2 { D<P> c; };\n"
        "class Free { template <std::size_t K> void f(Array<P, K> a); };\n}\n")})
    assert not ir.unresolved
    assert ("n::Buf", "dependency", "n::N") not in rels(ir)
    assert {t.id: t.generics for t in ir.types if t.generics}["n::Buf"] == ["T", "N"]


def test_cpp_unqualified_names_a_macro_may_declare(tmp_path):
    """`XMLException` written in the namespace where a macro is passed it gets the macro as
    a hint, also from nested namespaces; not from other namespaces. The reason stays."""
    ir = extract_source(tmp_path, {"xml.h": (
        "namespace Poco {\nclass Exception {};\nnamespace XML {\n"
        "POCO_DECLARE_EXCEPTION(XML_API, XMLException, Poco::Exception)\n"
        "class DOMException: public XMLException {};\n"
        "namespace DOM { class Node { XMLException* e; }; }\n}\n"
        "namespace Data { class Session { XMLException* e; }; }\n}\n"
        "namespace other { class Thing: public XMLException {}; }\n")})
    hints = {u.from_: (u.hint, u.reason) for u in ir.unresolved}
    macro = "POCO_DECLARE_EXCEPTION(...) at xml.h:4 may declare it"
    assert hints["Poco::XML::DOMException"] == (macro, "unexplained")
    assert hints["Poco::XML::DOM::Node"] == (macro, "unexplained")
    assert hints["Poco::Data::Session"] == (None, "unexplained")
    assert hints["other::Thing"] == (None, "unexplained")


def test_cpp_names_several_macros_mention(tmp_path):
    """Every macro argument is recorded, bases too: several places are mentions, and the
    file named after the name comes first (XMLException.h declares it; SAXException.h
    passes it as a base and comes first in file order)."""
    ir = extract_source(tmp_path, {
        "SAX/SAXException.h": "namespace Poco { namespace XML {\n"
                              "POCO_DECLARE_EXCEPTION(XML_API, SAXException, XMLException)\n} }\n",
        "XML/XMLException.h": "namespace Poco { namespace XML {\nclass Base {};\n"
                              "POCO_DECLARE_EXCEPTION(XML_API, XMLException, Base)\n} }\n",
        "XML/DOMException.h": "namespace Poco { namespace XML {\n"
                              "class DOMException: public XMLException {};\n} }\n",
    })
    (u,) = [u for u in ir.unresolved if u.raw_type == "XMLException"]
    assert u.hint == (
        "mentioned by POCO_DECLARE_EXCEPTION(...) at XML/XMLException.h:3, "
        "POCO_DECLARE_EXCEPTION(...) at SAX/SAXException.h:2; one of them may declare it")
    assert u.reason == "unexplained"


def test_cpp_member_aliases_are_inherited(tmp_path):
    ir = extract_source(tmp_path, {"a.h": (
        "class Item {};\n"
        "class TextEncoding { public: using CharacterMap = int[256]; using Names = int;\n"
        "  typedef Item* ItemPtr; struct Inner {};\n"
        "  virtual const CharacterMap& characterMap() const = 0; };\n"
        "class ASCIIEncoding: public TextEncoding { public:\n"
        "  const CharacterMap& characterMap() const; Names names() const; Inner in;\n"
        "  ItemPtr ip; };\n")})
    assert not ir.unresolved
    assert {("ASCIIEncoding", "association", "TextEncoding::Inner"),
            ("ASCIIEncoding", "association", "Item")} <= rels(ir)


def test_cpp_preprocessing_keeps_directive_groups_whole():
    """What the parser is given: a directive line is no code line to judge the next
    `#if` by, a group is blanked or kept as a whole, and a macro before `{` is a head."""
    from draftsman.langs.cpp import CppSpec
    pre = CppSpec().preprocess
    src = b"#define MIN(a, b) ((a) < (b) ? (a) : (b))\n#if X\nint x;\n#endif\n"
    assert pre(src) == src
    src = b"void f(int a,\n#if X\n   int b\n#endif\n);\n"
    out = pre(src).split(b"\n")
    assert out[1].strip() == out[3].strip() == b""          # #if and its #endif both go
    src = b"namespace n {\nTEST_CASE(A, B)\n{\n}\n}\n"
    assert pre(src) == src
