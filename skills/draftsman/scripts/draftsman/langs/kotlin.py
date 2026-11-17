from __future__ import annotations

from .base import LanguageSpec

_BUILTINS = {
    "Any", "Unit", "Nothing", "Int", "Long", "Short", "Byte", "Double", "Float", "Boolean",
    "Char", "String", "CharSequence", "Number", "Comparable", "Throwable", "Exception",
    "RuntimeException", "Error", "IllegalStateException", "IllegalArgumentException",
    "UnsupportedOperationException", "NoSuchElementException", "IndexOutOfBoundsException",
    "Pair", "Triple", "Result", "Regex", "Array", "IntArray", "LongArray", "ByteArray",
    "CharArray", "DoubleArray", "FloatArray", "BooleanArray", "ShortArray", "UInt", "ULong",
    "UByte", "UShort", "Enum", "Annotation", "Function", "Function0", "Function1",
    "Function2", "AutoCloseable", "Iterable", "Iterator", "ClosedRange", "IntRange",
    "LongRange", "StringBuilder", "Appendable", "Duration", "JvmInline", "JvmStatic",
    "JvmField", "JvmOverloads", "Deprecated", "Suppress", "Volatile", "Transient",
    "Synchronized", "Serializable",
}


class KotlinSpec(LanguageSpec):
    name = "kotlin"
    grammar = "kotlin"
    extensions = (".kt", ".kts")
    separator = "."
    opaque_nodes = frozenset({
        "function_body", "lambda_literal", "anonymous_function", "object_literal",
        "enum_entry", "getter", "setter", "anonymous_initializer", "statements",
        "control_structure_body",
    })
    static_scope_nodes = frozenset({"companion_object"})
    annotation_nodes = frozenset({"annotation"})
    annotation_name_field = "-"   # no name field: use the annotation's text
    builtins = frozenset(_BUILTINS)
    visibility_keywords = {
        "public": "public", "protected": "protected", "private": "private",
        "internal": "internal",
    }

    def default_visibility(self, owner_kind, member_kind):
        return "public"

    def is_static(self, owner_kind, member_kind, modifiers):
        return member_kind == "enum_constant" or "const" in modifiers

    def is_abstract(self, owner_kind, member_kind, modifiers, has_body, marker=None):
        if "abstract" in modifiers:
            return True
        return owner_kind == "interface" and member_kind in ("method", "property") \
            and not has_body and member_kind == "method"

    def external_super_kind(self, owner_kind, captured, name):
        if captured != "inherits":
            return captured
        # without a constructor call, a class's supertype is an interface
        return "extends" if owner_kind == "interface" else "implements"
