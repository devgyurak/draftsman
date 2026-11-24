"""The C++ answer key's joining of translation units (bench/clang_oracle/oracle.py): what
its selftest, one directory's units, cannot show."""

import importlib.util
import json
from pathlib import Path

ORACLE = Path(__file__).resolve().parents[1] / "bench" / "clang_oracle" / "oracle.py"
spec = importlib.util.spec_from_file_location("clang_oracle", ORACLE)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def use(name, line, col, kind="type", target="shop::Money", tf="shop/model.h", pos="type",
        frm="shop::Order", **extra):
    return {"n": name, "f": "shop/model.h", "l": line, "c": col, "k": kind, "t": target,
            "tf": tf, "pos": pos, "max": 1, "from": frm, "spec": 0, "m": "", **extra}


# what shop/model.h defines (a type only declared there would be none of the sources')
DECLS = [{"decl": t, "f": "shop/model.h", "l": 1, "kind": "struct", "anon": 0}
         for t in ("shop::Money", "lib::AutoPtr", "lib::Channel")]


def joined(tmp_path, *units, files=("shop/model.h", "shop/a.cc", "shop/b.cc"), headers=()):
    """The key of shop/model.h, entered by each unit given as (its records, lines it skips)."""
    root = tmp_path / "src"
    (root / "shop").mkdir(parents=True)
    for f in files:
        (root / f).write_text("x\n" * 20)
    raw = tmp_path / "raw"
    raw.mkdir()
    for i, (recs, skips) in enumerate(units):
        main = f"/src/shop/{'ab'[i % 2]}.cc" if i < 2 else f"/work/hdr/{i}.cpp"
        lines = [{"inc": "shop/model.h"}] + [{"skip": "shop/model.h", "l1": a, "l2": b} for a, b in skips]
        lines += DECLS
        lines += recs + [{"tu": main, "ms": 1, "rc": 0}]
        (raw / f"{i}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in lines))
    return oracle.join(raw, list(files), root, set(headers))


def test_units_that_agree_give_the_answer(tmp_path):
    recs = joined(tmp_path, ([use("Money", 3, 4)], []), ([use("Money", 3, 4)], []))
    [r] = [r for r in recs if "use" in r]
    assert (r["kind"], r["target"], r["project"], r["units"], r["from"]) == \
        ("type", "shop::Money", True, 2, "shop::Order")


def test_units_that_differ_or_say_nothing_split(tmp_path):
    recs = joined(tmp_path, ([use("Money", 3, 4)], []), ([use("Money", 3, 4, kind="var", target="m", tf="")], []))
    [r] = [r for r in recs if "use" in r]
    assert r["kind"] == "split" and r["target"] is None
    recs = joined(tmp_path / "2", ([use("Money", 3, 4)], []), ([], []))
    [r] = [r for r in recs if "use" in r]
    assert r["kind"] == "split" and r["answers"]["none"] == 1


def test_a_unit_that_skips_the_line_has_no_say(tmp_path):
    # the second unit's `#if` leaves line 3 out: the first one's answer stands
    recs = joined(tmp_path, ([use("Money", 3, 4)], []), ([], [(2, 4)]))
    [r] = [r for r in recs if "use" in r]
    assert (r["kind"], r["units"]) == ("type", 1)


def test_lines_and_files_no_unit_compiles(tmp_path):
    recs = joined(tmp_path, ([], [(5, 7)]), ([], [(6, 9)]),
                  files=("shop/model.h", "shop/a.cc", "shop/b.cc", "shop/c.h"))
    unc = {r["uncompiled"]: r["lines"] for r in recs if "uncompiled" in r}
    assert unc == {"shop/model.h": [6, 7], "shop/c.h": "all"}


def test_an_alias_stands_for_the_project_types_it_names(tmp_path):
    alias = {"aliasdecl": "lib::Channel::Ptr", "f": "shop/model.h", "l": 1,
             "names": [["type", "lib::AutoPtr", "shop/model.h", "2"], ["type", "lib::Channel", "shop/model.h", "3"],
                       ["type", "std::string", "", ""]]}
    feed = {"aliasdecl": "shop::Feed", "f": "shop/model.h", "l": 5,
            "names": [["alias", "lib::Channel::Ptr", "shop/model.h", "1"]]}
    other = {"aliasdecl": "shop::Feed", "f": "shop/model.h", "l": 9, "names": []}
    recs = joined(tmp_path, ([alias, other, feed, use("Feed", 3, 4, kind="alias", target="shop::Feed",
                                                      tf="shop/model.h:5")], []))
    [r] = [r for r in recs if "use" in r]
    assert (r["kind"], r["target"], r["targets"], r["alias"], r["project"]) == \
        ("type", "lib::AutoPtr", ["lib::AutoPtr", "lib::Channel"], "shop::Feed", True)


def test_an_alias_of_no_project_type_is_none(tmp_path):
    alias = {"aliasdecl": "shop::Number", "f": "shop/model.h", "l": 2, "names": []}
    recs = joined(tmp_path, ([alias, use("Number", 3, 4, kind="alias", target="shop::Number",
                                         tf="shop/model.h:2")], []))
    [r] = [r for r in recs if "use" in r]
    assert (r["kind"], r["project"]) == ("type", False)


def test_a_header_only_a_unit_of_its_own_enters_is_marked(tmp_path):
    recs = joined(tmp_path, ([], []), ([], []), ([use("Money", 3, 4)], []), headers={"/work/hdr/2.cpp"})
    [r] = [r for r in recs if "use" in r]
    assert r["kind"] == "split"   # the two others enter it as well and say nothing
    recs = joined(tmp_path / "2", ([use("Money", 3, 4)], []), files=("shop/model.h",),
                  headers={"/src/shop/a.cc"})
    [r] = [r for r in recs if "use" in r]
    assert r.get("header") is True


def test_a_type_only_declared_in_the_sources_is_none_of_theirs(tmp_path):
    recs = joined(tmp_path, ([use("bignum_st", 3, 4, target="bignum_st")], []))
    [r] = [r for r in recs if "use" in r]
    assert (r["kind"], r["project"]) == ("type", False)


def test_types_several_files_define_under_one_id():
    recs = [{"declared": "shop::State", "file": "shop/a.cc"},
            {"declared": "shop::State", "file": "shop/b.cc"},
            {"declared": "shop::Money", "file": "shop/model.h"}]
    assert oracle.merged(recs) == {"shop::State": {"shop/a.cc", "shop/b.cc"}}
    why = oracle.apart(oracle.merged(recs))
    assert why({"kind": "type", "target": "shop::State"}) == "one id, several types"
    assert why({"kind": "dependent", "target": None}) == "a dependent name"
    assert why({"kind": "type", "target": "shop::Money"}) is None
