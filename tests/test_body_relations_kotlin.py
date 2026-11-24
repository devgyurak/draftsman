"""Relations read from names written in Kotlin bodies (`evidence` "body", issue #5)."""

import sys
from pathlib import Path

from conftest import extract_source
from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.resolve import _Builder
from draftsman.wrappers import Wrappers

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
from answer_key import expected  # noqa: E402   the hand-written answers' markers

# tests/fixtures/kotlin/body, which `bench/kotlin_oracle/oracle.py selftest` checks against
# the Kotlin compiler
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "kotlin" / "body"
SUFFIXES = (".kt",)


def _fixture() -> list:
    return [Extractor(spec_for_path(p.name)).extract(p, p.relative_to(FIXTURE).as_posix(), FIXTURE)
            for p in sorted(FIXTURE.rglob("*")) if p.suffix in SUFFIXES]


def test_body_names_stand_where_the_hand_written_answers_say():
    # every part of a name the extractor records is in the position its marker gives ("r"
    # for a call, which a value may be as well); one no marker lists is no name a marker
    # gives (a member after a `.` or a variable), and every marked name a body relation
    # could come from is recorded
    want = expected(FIXTURE, SUFFIXES)
    problems, recorded = [], set()
    for raw in _fixture():
        for r in (r for t in raw.types for r in t.body_refs):
            marks = [want.get((raw.path, line, col), (None, None)) for line, col in r.places]
            for i, (part, (line, col), (answer, position)) in enumerate(
                    zip(r.text.split("."), r.places, marks)):
                recorded.add((raw.path, line, col))
                where = f"{raw.path}:{line}:{col + 1} {part} of {r.text}"
                expect = "type" if r.position == "type" else "receiver"
                if answer is None:
                    if part[:1].isupper() and i == 0:   # not a member (`Status.New`)
                        problems.append(f"{where}: no marker")
                elif answer == "-":
                    if all(a in (None, "-") for a, _ in marks):
                        problems.append(f"{where}: a declaration, recorded as {r.position}")
                elif position != expect:
                    problems.append(f"{where}: {r.position}, the marker says {position}")
    assert problems == []
    # a type named in code outside every type, a value alone (`listOf(Registry)`), an
    # annotation in a body, and a name after another (`Ticket.Factory`)
    missed = sorted((rel, line, answer) for (rel, line, col), (answer, _) in want.items()
                    if answer.startswith(("shop.", "lib.")) and (rel, line, col) not in recorded)
    assert missed == [
        ("shop/Model.kt", 19, "shop.Money"), ("shop/Model.kt", 42, "shop.Order"),
        ("shop/Model.kt", 43, "shop.Customer"), ("shop/Places.kt", 37, "shop.Customer"),
        ("shop/Places.kt", 38, "shop.Order"), ("shop/Uses.kt", 14, "shop.Mark"),
        ("shop/Uses.kt", 29, "shop.Order"), ("shop/Uses.kt", 29, "shop.Registry"),
        ("shop/Uses.kt", 51, "shop.Ticket.Factory")]


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
    # every project type recorded is drawn but where a function of the name may be called
    # instead (`Money(1)`: a function `Money` is declared at a file's top), a top-level type
    # of the name of an interface's or a superclass's companion's nested type, which the
    # extractor finds first and so gives up (`InComp` in Sub), a type's own
    # name (`Order(1)` in Order's companion) and the part of a longer name (`Order` in
    # `Order.Line`)
    recorded = {(raw.path, line, col) for raw in _fixture() for t in raw.types
                for r in t.body_refs for line, col in r.places}
    missed = sorted((rel, line, answer) for (rel, line, col), (answer, _) in want.items()
                    if answer in builder.types and (rel, line, col) in recorded - drawn)
    assert missed == [
        ("shop/Hiding.kt", 34, "shop.Money"), ("shop/Model.kt", 7, "shop.Order"),
        ("shop/Model.kt", 8, "shop.Order"), ("shop/Model.kt", 17, "shop.Money"),
        ("shop/Nesting.kt", 14, "shop.InComp"), ("shop/Nesting.kt", 15, "shop.InComp"),
        ("shop/Nesting.kt", 18, "shop.N"), ("shop/Nesting.kt", 19, "shop.N"),
        ("shop/Places.kt", 8, "shop.Money"), ("shop/Places.kt", 15, "shop.Money"),
        ("shop/Places.kt", 21, "shop.Money"), ("shop/Places.kt", 31, "shop.Money"),
        ("shop/Places.kt", 32, "shop.Money"), ("shop/Uses.kt", 13, "shop.Order"),
        ("shop/Uses.kt", 21, "shop.Order"), ("shop/Uses.kt", 24, "shop.Order"),
        ("shop/Uses.kt", 38, "shop.Money"), ("shop/Uses.kt", 40, "shop.Money")]


def _body(ir) -> list[tuple]:
    return sorted((r.from_, r.to, r.source_location.line)
                  for r in ir.relations if r.evidence == "body")


def test_a_call_may_be_a_function_of_the_name(tmp_path):
    # a function at another file's top, a method of the class or of a project supertype,
    # a companion's function after the outer class: the call may be any of them
    ir = extract_source(tmp_path, {
        "p/Types.kt": "package p\nclass Money\nclass Widget\nclass Outer { class Inner\n"
                      "  companion object { fun Inner(x: Int) = Inner() } }\nopen class Base {\n"
                      "  fun Widget(x: Int) = 0 }\nclass Plain\n",
        "p/Fns.kt": "package p\nfun Money(a: Int, b: Int) = Money()\n",
        "p/Use.kt": "package p\nclass Use : Base() {\n"
                    "  fun a() = Money(1, 2)\n"
                    "  fun b() = Widget(1)\n"
                    "  fun c() = Outer.Inner(1)\n"
                    "  fun d() = Plain()\n"
                    "  fun e() = Money::class\n}\n"})
    assert _body(ir) == [("p.Use", "p.Money", 7), ("p.Use", "p.Outer", 5), ("p.Use", "p.Plain", 6)]


def test_a_property_at_a_files_top_hides_a_type(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Types.kt": "package p\nclass Logger { companion object { fun trace() = 0 } }\nclass Other\n",
        "q/Vals.kt": "package q\nval Logger = 1\n",
        "p/Use.kt": "package p\nclass Use { fun a() = Logger.trace()\n  fun b() = Other.hashCode() }\n"})
    assert _body(ir) == [("p.Use", "p.Other", 3)]


def test_a_typealias_draws_the_class_it_names_directly(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Types.kt": "package p\nclass Money\nopen class Box<T>\n",
        "q/Aliases.kt": "package q\nimport p.*\ntypealias Cash = Money\n"
                        "typealias Cashes = List<Money>\ntypealias Boxed = Box<Money>\n",
        "r/Use.kt": "package r\nimport q.*\nclass Use {\n"
                    "  fun a(): Any = Cash()\n"
                    "  fun b(): Any { val x: Cashes = listOf(); val y: Boxed? = null; return x }\n}\n"})
    assert _body(ir) == [("r.Use", "p.Money", 4)]


def test_a_private_top_level_class_is_seen_in_its_file_only(tmp_path):
    ir = extract_source(tmp_path, {
        "p/A.kt": "package p\nprivate class Helper\nclass A { fun a() = Helper() }\n",
        "p/B.kt": "package p\nimport lib.*\nclass B { fun b() = Helper() }\n"})
    assert _body(ir) == [("p.A", "p.Helper", 3)]


def test_a_call_after_a_star_import_of_a_native_platform_library_draws_nothing(tmp_path):
    # `WinHttpConnect(...)` is the C function of platform.winhttp when the class's
    # constructor does not take the arguments: the compiler goes on past it
    ir = extract_source(tmp_path, {
        "p/Connect.kt": "package p\ninternal class WinHttpConnect(val h: Int)\n",
        "p/Use.kt": "package p\nimport platform.winhttp.*\n"
                    "class Use { fun a() = WinHttpConnect(1, 2)\n"
                    "  fun b(): WinHttpConnect? = null\n  fun c() { val x: WinHttpConnect? = null } }\n"})
    assert _body(ir) == [("p.Use", "p.WinHttpConnect", 5)]


def _module(tmp_path: Path, name: str) -> None:
    (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / name / "build.gradle.kts").write_text("")


def test_a_platform_source_set_sees_its_own_types_and_the_common_ones(tmp_path):
    # Ktor's layout (`<module>/<set>/src`) and Gradle's (`<module>/src/<set>/kotlin`)
    _module(tmp_path, "net")
    _module(tmp_path, "app")
    ir = extract_source(tmp_path, {
        "net/jvm/src/p/Queue.kt": "package p\ninternal class Queue\n",
        "net/common/src/p/Common.kt": "package p\nclass Common\n",
        "net/jvm/src/p/OnJvm.kt": "package p\nclass OnJvm { fun a() = Queue() }\n",
        "net/nix/src/p/OnNix.kt": "package p\nclass OnNix { fun a() = Queue()\n  fun b() = Common() }\n",
        "app/src/jvmMain/kotlin/p/Jvm.kt": "package p\nclass Jvm2\n",
        "app/src/jsMain/kotlin/p/Js.kt": "package p\nclass OnJs { fun a() = Jvm2() }\n"})
    assert _body(ir) == [("p.OnJvm", "p.Queue", 2), ("p.OnNix", "p.Common", 3)]


def test_a_type_of_the_files_package_in_another_module_only_may_be_unseen(tmp_path):
    # the file's package comes before its star imports, but only with the modules its
    # module depends on, which the build says
    _module(tmp_path, "plugin")
    _module(tmp_path, "schema")
    ir = extract_source(tmp_path, {
        "plugin/src/p/Prim.kt": "package p\nenum class JsonPrimitive { A }\nclass Mine\n",
        "schema/src/p/Use.kt": "package p\nimport kotlinx.serialization.json.*\n"
                               "class Use { fun a(x: Any) = x is JsonPrimitive }\n",
        "schema/src/p/Other.kt": "package p\nclass Other { fun a() = Mine() }\n"})
    assert _body(ir) == [("p.Other", "p.Mine", 2)]


def test_an_apple_source_set_draws_nothing(tmp_path):
    # only a macOS host compiles it, which no answer key here can
    _module(tmp_path, "net")
    ir = extract_source(tmp_path, {
        "net/common/src/p/Common.kt": "package p\nclass Common\n",
        "net/darwin/src/p/D.kt": "package p\nclass D { fun a() = Common() }\n",
        "net/src/iosMain/kotlin/p/I.kt": "package p\nclass I { fun a() = Common() }\n",
        "net/linux/src/p/L.kt": "package p\nclass L { fun a() = Common() }\n"})
    assert _body(ir) == [("p.L", "p.Common", 2)]


def test_a_private_class_of_each_platforms_file_is_its_one_id_there(tmp_path):
    _module(tmp_path, "io")
    ir = extract_source(tmp_path, {
        "io/js/src/p/A.js.kt": "package p\nprivate class Impl\nclass A { fun a() = Impl() }\n",
        "io/wasmJs/src/p/A.wasm.kt": "package p\nprivate class Impl\nclass B { fun a() = Impl() }\n",
        "io/js/src/p/C.kt": "package p\nclass C { fun a() = Impl() }\n"})
    assert _body(ir) == [("p.A", "p.Impl", 3), ("p.B", "p.Impl", 3)]


def test_a_supertype_outside_the_sources_may_have_a_member_of_the_name(tmp_path):
    # under a superclass outside the sources a type name may be its nested type
    # (androidx.work's `Result` under CoroutineWorker), and under any outside supertype a
    # value may be its property or function; CoroutineScope's nested types are known
    ir = extract_source(tmp_path, {
        "p/A.kt": "package p\nimport androidx.work.CoroutineWorker\n"
                  "import kotlinx.coroutines.CoroutineScope\n"
                  "class Result { companion object { fun success() = 1 } }\nclass Plain\n"
                  "class W : CoroutineWorker() {\n"
                  "  fun a() = Result.success()\n  fun b() = Plain()\n"
                  "  fun d() { val x: Result? = null } }\n"
                  "class S : CoroutineScope {\n"
                  "  fun a() = Result.success()\n  fun b() = Plain()\n"
                  "  fun d() { val x: Result? = null } }\n"
                  "class Q { fun a() = object : CoroutineWorker() { fun b() = Plain() } }\n"
                  "class N : Plain2() { fun d() { val x: Result? = null; Plain() } }\n"
                  "open class Plain2\n"})
    assert _body(ir) == [("p.N", "p.Plain", 15), ("p.N", "p.Result", 15), ("p.S", "p.Result", 13)]


def test_a_kotlin_files_top_level_names_are_no_names_of_java_code_beside_it(tmp_path):
    # `val Money = 1` at a Kotlin file's top hides nothing in Java (kt8)
    ir = extract_source(tmp_path, {
        "j/shop/Money.java": "package shop;\npublic class Money { public static int ZERO = 0; }\n",
        "j/shop/Use.java": "package shop;\npublic class Use { int f() { return Money.ZERO; } }\n",
        "shop/D.kt": "package shop\nval Money = 1\nfun Use() = 0\n"})
    assert _body(ir) == [("shop.Use", "shop.Money", 2)]


def test_importing_a_type_under_another_name_hides_its_own(tmp_path):
    # `Token` is other.Token after `import shop.Token as Tok`, even in package shop (kt7)
    ir = extract_source(tmp_path, {
        "shop/Token.kt": "package shop\nclass Token\n",
        "other/Token.kt": "package other\nclass Token\n",
        "shop/AH.kt": "package shop\nimport other.*\nimport shop.Token as Tok\n"
                      "class AH {\n  fun a() = Token()\n  fun b() { val t: Token? = null }\n"
                      "  fun d() = Tok()\n}\n"})
    assert _body(ir) == [("shop.AH", "shop.Token", 7)]


def test_an_extensions_receiver_hides_a_name_by_a_member_of_it(tmp_path):
    # in `fun Ctx.ext()` the members of Ctx are names; its nested types are not (kt1, kt7)
    ir = extract_source(tmp_path, {
        "shop/A.kt": "package shop\nclass Money(x: Int)\nclass Order\nclass Part\n"
                     "class Ctx { fun Money(x: Int) = x; val Order = 1; class Part }\n"
                     "class R {\n  fun Ctx.ext() = Money(2)\n"
                     "  val Ctx.prop: Any get() = Order.toString()\n"
                     "  fun Ctx.part(): Any = Part()\n  fun h() = Money(4)\n}\n"})
    assert _body(ir) == [("shop.R", "shop.Money", 10), ("shop.R", "shop.Part", 9)]
