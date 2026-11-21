from __future__ import annotations

import re

from .base import LanguageSpec

# `X509Certificate @Nullable ... certs`: type annotations right before varargs are valid
# Java 8 but the tree-sitter grammar rejects them. Annotation arguments may nest one level
# of parentheses (`@Size(max = (3))`), and several annotations may stack.
_VARARGS_ANNOTATIONS = re.compile(
    rb"(?:@\s*[A-Za-z_$][\w$.]*(?:\s*\((?:[^()]|\([^()]*\))*\))?\s*)+(?=\.\.\.)")


def _blank(m: re.Match) -> bytes:
    return re.sub(rb"[^\n]", b" ", m.group(0))  # same length, newlines kept

_PRIMITIVES = {"boolean", "byte", "char", "short", "int", "long", "float", "double", "void", "var"}

_JAVA_LANG = {
    "Object", "String", "CharSequence", "StringBuilder", "StringBuffer", "Number",
    "Boolean", "Byte", "Character", "Short", "Integer", "Long", "Float", "Double", "Void",
    "Class", "Enum", "Record", "Iterable", "Comparable", "Runnable", "AutoCloseable",
    "Cloneable", "Thread", "ThreadLocal", "Math", "System", "Throwable", "Exception",
    "RuntimeException", "Error", "IllegalArgumentException", "IllegalStateException",
    "UnsupportedOperationException", "NullPointerException", "IndexOutOfBoundsException",
    "ArithmeticException", "ClassCastException", "InterruptedException",
    "CloneNotSupportedException", "SecurityException", "Override", "Deprecated",
    "FunctionalInterface", "SuppressWarnings", "SafeVarargs", "Appendable", "Readable",
    "ClassLoader", "Process", "ProcessBuilder", "Runtime", "StackTraceElement",
    "InheritableThreadLocal", "ThreadGroup", "Module", "Package", "StrictMath",
    "ReflectiveOperationException", "ClassNotFoundException", "NoSuchFieldException",
    "NoSuchMethodException", "NumberFormatException", "ArrayIndexOutOfBoundsException",
    "StringIndexOutOfBoundsException", "NegativeArraySizeException", "ArrayStoreException",
    "EnumConstantNotPresentException", "IllegalMonitorStateException", "AssertionError",
    "LinkageError", "OutOfMemoryError", "StackOverflowError", "VirtualMachineError",
    "ExceptionInInitializerError", "ScopedValue", "StringTemplate",
}

# Very common JDK types outside java.lang. Treated like builtins so they do
# not flood the unresolved list when imported through wildcards.
_JDK_COMMON = {
    "BigDecimal", "BigInteger", "UUID", "Date", "Calendar", "Locale", "Currency",
    "Random", "Objects", "Arrays", "Collections", "Comparator", "Scanner",
    "Instant", "Duration", "Period", "LocalDate", "LocalTime", "LocalDateTime",
    "ZonedDateTime", "OffsetDateTime", "ZoneId", "ZoneOffset", "Clock", "DateTimeFormatter",
    "Function", "BiFunction", "Consumer", "BiConsumer", "Predicate", "BiPredicate",
    "UnaryOperator", "BinaryOperator", "Callable", "Executor", "ExecutorService",
    "TimeUnit", "Pattern", "Matcher", "File", "Path", "Paths", "InputStream",
    "OutputStream", "Reader", "Writer", "IOException", "Serializable", "Closeable",
    "URI", "URL", "Charset", "StandardCharsets", "Logger",
}


class JavaSpec(LanguageSpec):
    name = "java"
    grammar = "java"
    extensions = (".java",)
    separator = "."
    opaque_nodes = frozenset({
        "block", "constructor_body", "lambda_expression", "object_creation_expression",
        "enum_constant", "static_initializer", "switch_expression",
    })
    annotation_nodes = frozenset({"marker_annotation", "annotation"})
    type_argument_nodes = frozenset({"type_arguments"})
    annotation_value_args = frozenset({"field_access"})   # `Include.NON_NULL`
    builtins = frozenset(_PRIMITIVES | _JAVA_LANG | _JDK_COMMON)
    visibility_keywords = {
        "public": "public", "protected": "protected", "private": "private",
    }

    def preprocess(self, src):
        return _VARARGS_ANNOTATIONS.sub(_blank, src)

    def annotation_arg(self, node, text):
        if node.type == "class_literal":   # `X.class`, `X[].class`
            return text(node.named_children[0]), True
        return super().annotation_arg(node, text)

    def builtin_id(self, name: str) -> str:
        return "java.lang." + name if name in _JAVA_LANG else name

    def default_visibility(self, owner_kind: str, member_kind: str) -> str:
        if owner_kind in ("interface", "annotation") or member_kind == "enum_constant":
            return "public"
        if owner_kind == "record" and member_kind == "field":
            return "private"  # record components are private final fields
        return "package"

    def is_static(self, owner_kind, member_kind, modifiers):
        if member_kind == "enum_constant":
            return True
        if owner_kind in ("interface", "annotation") and member_kind == "field":
            return True
        return "static" in modifiers

    def is_abstract(self, owner_kind, member_kind, modifiers, has_body, marker=None):
        if "abstract" in modifiers:
            return True
        return (
            owner_kind in ("interface", "annotation")
            and member_kind == "method"
            and not has_body
            and "static" not in modifiers
        )
