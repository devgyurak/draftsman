"""Java: a superclass's private member class is not inherited (issue #7, case 49), in
declarations and bodies alike. A form of bench/javac_oracle/review/jv1."""

from conftest import extract_source


def test_a_private_nested_type_of_a_superclass_is_not_inherited(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Base.java": ("package p;\npublic class Base {\n  private static class Hidden {}\n"
                        "  protected static class Deep {}\n}\n"),
        "p/Hidden.java": "package p; public class Hidden {}\n",
        "p/Deep.java": "package p; public class Deep {}\n",
        "p/Mid.java": "package p; public class Mid extends Base {}\n",
        "p/Sub.java": ("package p;\npublic class Sub extends Mid {\n  Hidden b;\n  Deep c;\n"
                       "  Object m() { Hidden h = new Hidden(); return h; }\n}\n"),
        "p/Own.java": ("package p;\npublic class Own {\n  private static class Hidden {}\n"
                       "  Hidden a;\n}\n")})
    rels = {(r.from_, r.to, r.via, r.evidence) for r in ir.relations}
    assert ("p.Sub", "p.Hidden", "b", None) in rels
    assert ("p.Sub", "p.Hidden", "m", "body") in rels
    assert not any(to == "p.Base.Hidden" for f, to, _, _ in rels if f == "p.Sub")
    assert ("p.Sub", "p.Base.Deep", "c", None) in rels   # a protected one is inherited
    assert ("p.Own", "p.Own.Hidden", "a", None) in rels  # its own class sees it
