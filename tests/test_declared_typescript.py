"""TypeScript declared relations from types the type parser used to read no name from
(issue #9: cases 29-32), and what is no name of a type there. Each test is a form of
bench/tsc_oracle/review/ts1, whose answers tsc gives; the relation each form draws is
pinned here, as the key does not tell a dependency from an association."""

from conftest import extract_source

MODEL = (
    "export interface Options { a?: number }\n"
    "export interface Logger { log(): void }\n"
    "export class Item {}\n"
    "export class Key {}\n"
    "export class T {}\nexport class U {}\nexport class K {}\n"
    "export class Store { Logger = 1; Item = ''; }\n"
)
IMPORT = 'import { Options, Logger, Item, Key, T, U, K, Store } from "./model";\n'


def _ir(tmp_path, body: str, extra: str = ""):
    return extract_source(tmp_path, {"model.ts": MODEL, "a.ts": IMPORT + extra
                                     + "export class A {\n" + body + "\n}\n"})


def _rels(ir, src: str = "a.A") -> set[tuple[str, str, str]]:
    return {(r.kind, r.to.rsplit(".", 1)[-1], r.via) for r in ir.relations
            if r.from_ == src and r.evidence is None}


def test_a_union_written_with_a_leading_bar_is_a_union(tmp_path):
    ir = _ir(tmp_path, '  logger: | "simple" | Logger = "simple";\n  both?: | Options | Item;')
    assert _rels(ir) == {("association", "Logger", "logger"), ("association", "Options", "both"),
                         ("association", "Item", "both")}


def test_an_intersection_is_read_as_a_union(tmp_path):
    ir = _ir(tmp_path, "  opts?: Options & Logger;\n  half?: Options & { x?: Item };")
    assert _rels(ir) == {("association", "Options", "opts"), ("association", "Logger", "opts"),
                         ("association", "Options", "half"), ("dependency", "Item", "half")}


def test_an_object_type_literal_names_its_members_types(tmp_path):
    ir = _ir(tmp_path, "  map?: { item: Logger }[];\n"
             "  props?: { Logger: string; Item: number; T: boolean };\n"
             "  index?: { [Key: string]: Item };\n"
             "  method?: { run(x: Options): Logger; new (y: Key): Item };")
    assert _rels(ir) == {("dependency", "Logger", "map"), ("dependency", "Item", "index"),
                         ("dependency", "Options", "method"), ("dependency", "Logger", "method"),
                         ("dependency", "Key", "method"), ("dependency", "Item", "method")}


def test_a_function_type_with_optional_parameters(tmp_path):
    # parameter names (`Logger`) and labels name no type
    ir = _ir(tmp_path, "  fn?: (Logger: string, item?: Item) => void;\n"
             "  tup?: [Logger: string, n?: number];\n"
             "  ctor?: new () => Key;\n"
             "  later(opts?: { cb: (err?: Logger) => void }): void {}")
    assert _rels(ir) == {("dependency", "Item", "fn"), ("dependency", "Key", "ctor"),
                         ("dependency", "Logger", "later")}


def test_an_indexed_access_depends_on_the_type_not_on_its_key(tmp_path):
    ir = _ir(tmp_path, '  idx?: Store["Logger"];\n  deep?: Required<Options>["a"];')
    assert _rels(ir) == {("dependency", "Store", "idx"), ("dependency", "Options", "deep")}


def test_a_conditional_type_depends_on_its_parts(tmp_path):
    ir = _ir(tmp_path, "  cond?: Options extends Logger ? Item : Key;\n"
             "  inferred?: Store extends { Item: infer U } ? U : never;")
    assert _rels(ir) == {("dependency", "Options", "cond"), ("dependency", "Logger", "cond"),
                         ("dependency", "Item", "cond"), ("dependency", "Key", "cond"),
                         ("dependency", "Store", "inferred")}


def test_literals_and_names_the_type_declares_are_no_type_names(tmp_path):
    ir = _ir(tmp_path, '  lit?: "Logger" | "Item";\n  tpl?: `Logger-${number}`;\n'
             "  gfn?: <T>(x: T) => T;\n  keyed?: { [K in keyof Options]: Item | K };\n"
             "  me?: this;")
    assert _rels(ir) == {("dependency", "Options", "keyed"), ("dependency", "Item", "keyed")}


def test_an_alias_of_such_a_type_is_expanded(tmp_path):
    ir = _ir(tmp_path, "  both?: Both;\n  obj?: Obj;\n  gen?: Gen<Options>;\n  c?: Cond<Item[]>;",
             extra="export type Both = | Options | Logger;\n"
                   "export type Obj = { item: Item };\n"
                   "export type Gen<T> = (x: T) => Key;\n"
                   "export type Cond<X> = X extends Array<infer U> ? U : Key;\n")
    # an alias's own type parameters (`T`, `X`) and `infer U` are not the classes T and U
    assert _rels(ir) == {("association", "Options", "both"), ("association", "Logger", "both"),
                         ("dependency", "Item", "obj"), ("dependency", "Key", "gen"),
                         ("dependency", "Options", "gen"), ("dependency", "Key", "c"),
                         ("dependency", "Item", "c")}


def test_typeof_names_a_value_not_a_type_alias_of_its_name(tmp_path):
    ir = _ir(tmp_path, "  tv?: typeof value;\n  cls?: typeof Item;",
             extra="export const value = { n: 1 };\nexport type value = Key;\n")
    assert _rels(ir) == {("association", "Item", "cls")}


def test_a_type_predicate_depends_on_its_type(tmp_path):
    ir = _ir(tmp_path, "  isLogger(x: unknown): x is Logger { return true; }\n"
             "  check(x: unknown): asserts x is Options {}\n"
             "  check2(x: unknown): asserts x {}")
    assert _rels(ir) == {("dependency", "Logger", "isLogger"), ("dependency", "Options", "check")}


def test_a_destructured_parameter_depends_on_its_type(tmp_path):
    ir = _ir(tmp_path, "  start({ a }: Options, [b]: [Item]): void {}")
    assert _rels(ir) == {("dependency", "Options", "start"), ("dependency", "Item", "start")}


def test_a_supertype_alias_of_several_types_extends_each(tmp_path):
    ir = extract_source(tmp_path, {"model.ts": MODEL, "a.ts": IMPORT + (
        "export type Joined = Options & Logger;\n"
        "export type Obj = { item: Item };\n"
        'export type Picked = Omit<Options, "a"> & { extra: Item };\n'
        "export interface I1 extends Joined {}\n"
        "export interface I2 extends Obj {}\n"
        "export interface I3 extends Picked {}\n"
        "export class C1 implements Joined { a?: number; log(): void {} }\n")})
    assert _rels(ir, "a.I1") == {("extends", "Options", None), ("extends", "Logger", None)}
    assert _rels(ir, "a.C1") == {("implements", "Options", None), ("implements", "Logger", None)}
    # an alias that is no type of the sources: what it names is a dependency
    assert _rels(ir, "a.I2") == {("dependency", "Item", None)}
    assert _rels(ir, "a.I3") == {("dependency", "Options", None), ("dependency", "Item", None)}
    assert not ir.unresolved
