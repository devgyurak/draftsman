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
