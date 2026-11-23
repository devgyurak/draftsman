"""Relations read from names written in Python bodies (`evidence` "body", issue #5)."""

import sys
from pathlib import Path

from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.resolve import _Builder
from draftsman.wrappers import Wrappers

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
from answer_key import expected  # noqa: E402   the hand-written answers' markers

# tests/fixtures/python/body, which `bench/py_oracle/oracle.py selftest` checks against
# mypy, pyright and ty
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "python" / "body"
SUFFIXES = (".py",)


def _fixture() -> list:
    return [Extractor(spec_for_path(p.name)).extract(p, p.relative_to(FIXTURE).as_posix(), FIXTURE)
            for p in sorted(FIXTURE.rglob("*")) if p.suffix in SUFFIXES]


def _want() -> dict:
    return expected(FIXTURE, SUFFIXES, "#>")


def test_body_names_stand_where_the_hand_written_answers_say():
    # every part of a name the extractor records is where a marker says a name is, unless
    # no marker lists it: a name outside the sources (`ValueError`, `Optional`) or lower
    # case may go unlisted, as in the key's selftest (one drawn without a marker fails the
    # next test); every marked name is recorded, but one in a branch of a platform test
    want = _want()
    problems, recorded = [], set()
    for raw in _fixture():
        for r in (r for t in raw.types for r in t.body_refs):
            marks = [want.get((raw.path, line, col), (None, None)) for line, col in r.places]
            for part, (line, col), (answer, position) in zip(r.text.split("."), r.places, marks):
                recorded.add((raw.path, line, col))
                where = f"{raw.path}:{line}:{col + 1} {part} of {r.text}"
                if answer is None:
                    continue
                if answer == "-":
                    if all(a in (None, "-") for a, _ in marks):
                        problems.append(f"{where}: not a name, recorded as {r.position}")
                elif position != r.position:
                    problems.append(f"{where}: {r.position}, the marker says {position}")
    assert problems == []
    missed = sorted((rel, line, answer) for (rel, line, col), (answer, _) in want.items()
                    if answer != "-" and (rel, line, col) not in recorded)
    assert missed == [("p/platform.py", 18, "disputed")]


def test_body_relations_go_where_the_hand_written_answers_say():
    want = _want()
    builder = _Builder("body", _fixture(), Wrappers.load())
    builder.build()
    wrong, drawn = [], set()
    for file, line, col, _, to in builder.body_uses:
        drawn.add((file, line, col))
        answer, _ = want[(file, line, col)]
        if answer != to:
            wrong.append((file, line, answer, to))
    assert wrong == []
    # every project class is drawn, but the part of a longer name (`Foo` in
    # `foomod.Foo.Inner`, `Outer` in `Outer.Inner`), a class's own name (`Kind.A` in Kind),
    # one the member binds a variable of elsewhere (the member is the scope: a comprehension's
    # `Foo`, a lambda's parameter, a local import), and one in the class body that its own
    # names hide (`made = Inner()` and the lambda beside it)
    missed = [(file, line, answer) for (file, line, col), (answer, position) in want.items()
              if answer in builder.types and (file, line, col) not in drawn]
    assert sorted(missed) == [
        ("p/forms.py", 28, "p.foo.Foo"), ("p/hide.py", 34, "p.foo.Foo"),
        ("p/hide.py", 42, "p.bar.Bar"), ("p/hide.py", 56, "p.foo.Foo"),
        ("p/scopes.py", 11, "p.scopes.Outer.Inner"), ("p/scopes.py", 12, "p.bar.Inner"),
        ("p/scopes.py", 18, "p.scopes.Outer"), ("p/scopes.py", 34, "p.scopes.Kind")]
