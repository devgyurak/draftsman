"""Relations read from names written in TypeScript bodies (`evidence` "body", issue #5)."""

import sys
from pathlib import Path

from conftest import extract_source
from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.resolve import _Builder
from draftsman.wrappers import Wrappers

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
from answer_key import expected  # noqa: E402   the hand-written answers' markers

# tests/fixtures/typescript/body, which `bench/tsc_oracle/oracle.py selftest` checks
# against the TypeScript compiler
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "typescript" / "body"
SUFFIXES = (".ts", ".tsx")


def _fixture() -> list:
    return [Extractor(spec_for_path(p.name)).extract(p, p.relative_to(FIXTURE).as_posix(), FIXTURE)
            for p in sorted(FIXTURE.rglob("*")) if p.suffix in SUFFIXES]


def test_body_names_stand_where_the_hand_written_answers_say():
    # every part of a name the extractor records is in the position its marker gives; one
    # no marker lists is lower case (a variable, a method), and one marked "-" (a member
    # after a type, `Kind.A`, or a namespace before one, `Shop.Item`) is part of a name
    # whose other part is a name; every marked name is recorded
    want = expected(FIXTURE, SUFFIXES)
    problems, recorded = [], set()
    for raw in _fixture():
        for r in (r for t in raw.types for r in t.body_refs):
            marks = [want.get((raw.path, line, col), (None, None)) for line, col in r.places]
            for part, (line, col), (answer, position) in zip(r.text.split("."), r.places, marks):
                recorded.add((raw.path, line, col))
                where = f"{raw.path}:{line}:{col + 1} {part} of {r.text}"
                if answer is None:
                    if part[:1].isupper():
                        problems.append(f"{where}: no marker")
                elif answer == "-":
                    if all(a in (None, "-") for a, _ in marks):
                        problems.append(f"{where}: a declaration, recorded as {r.position}")
                elif position != r.position:
                    problems.append(f"{where}: {r.position}, the marker says {position}")
    assert problems == []
    missed = sorted((rel, line, answer) for (rel, line, col), (answer, _) in want.items()
                    if answer != "-" and (rel, line, col) not in recorded)
    assert missed == []


def test_body_relations_go_where_the_hand_written_answers_say():
    want = expected(FIXTURE, SUFFIXES)
    builder = _Builder("body", _fixture(), Wrappers.load())
    builder.build()
    wrong, drawn = [], set()
    for file, line, col, _, to in builder.body_uses:
        drawn.add((file, line, col))
        answer, _ = want[(file, line, col)]
        if answer != to:
            wrong.append((file, line, answer))
    assert wrong == []
    # every project type is drawn, but the part of a longer name (`Foo` in `Foo.Inner`), a
    # type's own name, one the member declares a variable of further down (the
    # destructured `Foo` in `locals`: the member is the scope), and one an alias names
    # (`import Shape = Shop.Item`: an alias draws nothing in a body)
    missed = [(file, line, answer) for (file, line, col), (answer, position) in want.items()
              if answer in builder.types and (file, line, col) not in drawn]
    assert sorted(missed) == [("p/a.ts", 34, "p/foo.Foo"), ("p/a.ts", 35, "p/foo.Foo"),
                              ("p/a.ts", 72, "p/foo.Foo"), ("p/foo.ts", 6, "p/foo.Foo"),
                              ("p/shadow.ts", 15, "p/shop.Shop.Item")]


def _body(ir) -> list[tuple]:
    return sorted((r.from_, r.to, r.via, r.source_location.line)
                  for r in ir.relations if r.evidence == "body")


def test_a_variable_hides_a_class_where_a_value_stands_not_where_a_type_does(tmp_path):
    ir = extract_source(tmp_path, {
        "foo.ts": "export class Foo { }",
        "a.ts": """import { Foo } from "./foo";
export class A {
  m(Foo: number) {
    const x = new Foo();
    const y: Foo | null = null;
  }
  n() { return new Foo(); }
}
"""})
    assert _body(ir) == [("a.A", "foo.Foo", "m", 5), ("a.A", "foo.Foo", "n", 7)]
    assert ir.unresolved == []


def test_an_interface_is_no_value(tmp_path):
    # `Token` as a value is the constant beside the interface
    ir = extract_source(tmp_path, {
        "t.ts": "export const Token = 1;\nexport interface Token { t: number }\n",
        "a.ts": """import { Token } from "./t";
export class A {
  m() {
    const v = Token;
    const w: Token = { t: v };
  }
}
"""})
    assert _body(ir) == [("a.A", "t.Token", "m", 5)]


def test_a_field_hides_no_name_in_a_body(tmp_path):
    # a field is `this.Kind`; the bare name is the enum
    ir = extract_source(tmp_path, {
        "k.ts": "export enum Kind { A }",
        "a.ts": 'import { Kind } from "./k";\nexport class A {\n  Kind = 0;\n  m() { return Kind.A; }\n}\n'})
    assert _body(ir) == [("a.A", "k.Kind", "m", 4)]


def test_a_class_does_not_see_its_merged_namespace_by_simple_names(tmp_path):
    ir = extract_source(tmp_path, {
        "inner.ts": "export class Inner { }",
        "foo.ts": """import { Inner } from "./inner";
export class Foo {
  m() { return new Inner(); }
  n() { return new Foo.Inner(); }
}
export namespace Foo { export class Inner { } }
"""})
    assert _body(ir) == [("foo.Foo", "foo.Foo.Inner", "n", 4), ("foo.Foo", "inner.Inner", "m", 3)]


def test_a_dotted_value_goes_through_an_import_not_through_a_variable(tmp_path):
    # `util.Foo` names the module util's Foo only when the file imports it as util; here
    # util is a constant (and the module `util` a file the extractor sees)
    ir = extract_source(tmp_path, {
        "lib/index.ts": "export class Foo { static of() { return 1; } }",
        "util.ts": "export class Foo { }",
        "a.ts": """import * as lib from "./lib";
const util = { Foo: 1 };
export class A {
  m() {
    lib.Foo.of();
    return util.Foo;
  }
}
"""})
    assert _body(ir) == [("a.A", "lib.Foo", "m", 5)]


def test_a_receiver_is_a_dotted_name_not_an_expression(tmp_path):
    # `new Logger(Util.NAME).warn()`: Logger and Util, each once, and no name of the call
    ir = extract_source(tmp_path, {
        "l.ts": "export class Logger { warn() {} }\nexport class Util { static NAME = 'u'; }\n",
        "a.ts": 'import { Logger, Util } from "./l";\nexport class A {\n'
                '  m() { new Logger(Util.NAME).warn(); }\n  level = Util.NAME;\n}\n'})
    assert _body(ir) == [("a.A", "l.Logger", "m", 3), ("a.A", "l.Util", "level", 4),
                         ("a.A", "l.Util", "m", 3)]


def test_a_jsx_element_names_its_class_once(tmp_path):
    ir = extract_source(tmp_path, {
        "w.ts": "export class Widget { }",
        "a.tsx": 'import { Widget } from "./w";\n'
                 'export class A { render() { return <Widget></Widget>; } }\n'})
    assert _body(ir) == [("a.A", "w.Widget", "render", 2)]


def test_a_parameter_property_hides_a_class_in_the_constructor_only(tmp_path):
    # elsewhere the property is `this.Foo`
    ir = extract_source(tmp_path, {
        "foo.ts": "export class Foo { static make() { return 1; } }",
        "a.ts": """import { Foo } from "./foo";
export class A {
  constructor(private Foo: any, public readonly Bar?: any) { Foo.make(); }
  m() { return Foo.make(); }
}
"""})
    assert _body(ir) == [("a.A", "foo.Foo", "m", 4)]


def test_an_enum_member_hides_a_class_in_the_enum(tmp_path):
    ir = extract_source(tmp_path, {
        "foo.ts": "export class Foo { static N = 1; }",
        "a.ts": 'import { Foo } from "./foo";\n'
                'export enum E { Foo = 1, B = Foo }\nexport enum F { C = Foo.N }\n'})
    assert _body(ir) == [("a.F", "foo.Foo", "C", 3)]


def test_a_namespace_variable_hides_a_class_in_the_namespace(tmp_path):
    # in the namespaces inside it too, and only where a value stands
    ir = extract_source(tmp_path, {
        "foo.ts": "export class Foo { static make() { return 1; } }",
        "a.ts": """import { Foo } from "./foo";
export namespace NS {
  const Foo = { make: () => 2 };
  export class A { m(): number { const f: Foo | null = null; return Foo.make(); } }
  export namespace Inner { export class B { m() { return Foo.make(); } } }
}
export class C { m() { return Foo.make(); } }
"""})
    assert _body(ir) == [("a.C", "foo.Foo", "m", 7), ("a.NS.A", "foo.Foo", "m", 4)]


def test_a_label_in_a_type_is_no_name(tmp_path):
    ir = extract_source(tmp_path, {
        "foo.ts": "export class Foo { }\nexport class Bar { }\n",
        "a.ts": """import { Foo, Bar } from "./foo";
export class A {
  m() {
    const a: [Foo: string, Bar?: number] | null = null;
    const b: { [Foo: string]: Bar } | null = null;
  }
}
"""})
    assert _body(ir) == [("a.A", "foo.Bar", "m", 5)]


def test_an_enum_member_written_as_a_string_hides_a_class_in_the_enum(tmp_path):
    ir = extract_source(tmp_path, {
        "foo.ts": "export class Foo { }",
        "a.ts": 'import { Foo } from "./foo";\nexport enum E { "Foo" = 1, B = Foo }\n'})
    assert _body(ir) == []


def test_a_namespace_type_comes_before_an_import_of_its_name(tmp_path):
    # in declarations and in bodies; an alias in the namespace too, drawn through to its
    # target where a member's type names it
    ir = extract_source(tmp_path, {
        "foo.ts": "export class Foo { }",
        "other.ts": "export namespace Lib { export class Foo { } }",
        "a.ts": """import { Foo } from "./foo";
export namespace N2 {
  class Foo { }
  export class A { f: Foo | null = null; m() { return new Foo(); } }
}
export class B { f: Foo | null = null; }
""",
        "b.ts": """import { Foo } from "./foo";
import { Lib } from "./other";
export namespace N3 {
  import Foo = Lib.Foo;
  export class C { f: Foo | null = null; }
}
"""})
    assert sorted((r.from_, r.to, r.evidence or "") for r in ir.relations) == [
        ("a.B", "foo.Foo", ""), ("a.N2.A", "a.N2.Foo", ""), ("a.N2.A", "a.N2.Foo", "body"),
        ("b.N3.C", "other.Lib.Foo", "")]
