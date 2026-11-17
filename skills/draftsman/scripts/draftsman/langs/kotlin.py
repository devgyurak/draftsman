from __future__ import annotations

from .base import LanguageSpec

# Kotlin's default imports (kotlinlang.org/docs/packages.html#default-imports): kotlin.*,
# kotlin.annotation.*, kotlin.collections.*, kotlin.comparisons.*, kotlin.io.*,
# kotlin.ranges.*, kotlin.sequences.*, kotlin.text.*, kotlin.math.*; on the JVM also
# java.lang.* and kotlin.jvm.*, on JS kotlin.js.*. The platforms are used together: code
# that compiles names them only where they are visible.

def _in(package: str, names: str) -> dict[str, str]:
    return {name: package for name in names.split()}


# the core types, always these: an explicit star import that shadows `String` or
# `Exception` would be perverse, and doubting them would bury every real gap
_CORE = {
    **_in("kotlin", "Any Unit Nothing Int Long Short Byte Double Float Boolean Char String "
                    "CharSequence Number Comparable Throwable Exception RuntimeException Error "
                    "IllegalStateException IllegalArgumentException UnsupportedOperationException "
                    "NoSuchElementException IndexOutOfBoundsException Pair Triple Result Array "
                    "IntArray LongArray ByteArray CharArray DoubleArray FloatArray BooleanArray "
                    "ShortArray UInt ULong UByte UShort Enum Annotation Function Function0 "
                    "Function1 Function2 AutoCloseable Deprecated Suppress"),
    **_in("kotlin.collections", "Iterable Iterator"),
    **_in("kotlin.ranges", "ClosedRange IntRange LongRange"),
    **_in("kotlin.text", "Regex StringBuilder Appendable"),
    **_in("kotlin.jvm", "JvmInline JvmStatic JvmField JvmOverloads Volatile Transient "
                        "Synchronized"),
}

# the rest of the default-imported types: taken when no star import of an outside package
# could also provide the name, otherwise left unresolved with this as the hint
_DEFAULTS = {
    **_in("java.lang", "Class ClassLoader Runnable Thread ThreadLocal InheritableThreadLocal "
                       "Process ProcessBuilder Runtime System Math StrictMath StackTraceElement "
                       "InterruptedException ReflectiveOperationException ClassNotFoundException "
                       "CloneNotSupportedException SecurityException Void Integer Character "
                       "Override FunctionalInterface SafeVarargs OutOfMemoryError "
                       "StackOverflowError ThreadDeath Package Module ThreadGroup"),
    **_in("kotlin.jvm", "JvmName JvmMultifileClass JvmSuppressWildcards JvmWildcard JvmRecord "
                        "JvmSynthetic Strictfp PurelyImplements JvmSerializableLambda"),
    **_in("kotlin.js", "JsAny JsNumber JsString JsBoolean JsArray JsBigInt JsReference JsName "
                       "JsExport JsModule JsNonModule JsQualifier JsFileName JsFun JsStatic "
                       "Promise Json ExperimentalJsExport"),
    **_in("kotlin.annotation", "Retention Target MustBeDocumented Repeatable AnnotationTarget "
                               "AnnotationRetention"),
    **_in("kotlin.io", "FileTreeWalk FileWalkDirection"),
    **_in("kotlin.text", "MatchResult MatchGroup MatchGroupCollection RegexOption Charsets "
                         "CharCategory Typography"),
    **_in("kotlin.ranges", "CharRange UIntRange ULongRange IntProgression LongProgression "
                           "CharProgression ClosedFloatingPointRange OpenEndRange"),
    **_in("kotlin.sequences", "Sequence"),
    **_in("kotlin.collections", "List MutableList Set MutableSet Map MutableMap Collection "
                                "MutableCollection MutableIterable MutableIterator ListIterator "
                                "MutableListIterator ArrayList HashMap HashSet LinkedHashMap "
                                "LinkedHashSet AbstractList AbstractMutableList "
                                "AbstractCollection AbstractMutableCollection AbstractSet "
                                "AbstractMutableSet AbstractMap AbstractMutableMap ArrayDeque "
                                "Grouping IndexedValue RandomAccess"),
    **_in("kotlin", "ArithmeticException ClassCastException NullPointerException "
                    "NumberFormatException ConcurrentModificationException AssertionError Lazy "
                    "KotlinVersion Comparator Cloneable Throws PublishedApi DslMarker OptIn "
                    "RequiresOptIn ReplaceWith DeprecationLevel UnsafeVariance BuilderInference "
                    "SinceKotlin ExtensionFunctionType ParameterName ExperimentalStdlibApi "
                    "ExperimentalUnsignedTypes DeprecatedSinceKotlin"),
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
    # `dynamic` is Kotlin/JS's dynamic type: a soft keyword, never a class
    builtins = frozenset(_CORE) | {"dynamic"}
    visibility_keywords = {
        "public": "public", "protected": "protected", "private": "private",
        "internal": "internal",
    }

    def builtin_id(self, name):
        return f"{_CORE[name]}.{name}" if name in _CORE else name

    def default_import(self, name):
        return f"{_DEFAULTS[name]}.{name}" if name in _DEFAULTS else None

    def is_varargs(self, param_node):
        # `vararg` sits in the parameter_modifiers node just before the parameter
        prev = param_node.prev_named_sibling
        return prev is not None and prev.type == "parameter_modifiers" and \
            any(m.type == "parameter_modifier" and m.child_count and m.children[0].type == "vararg"
                for m in prev.children)

    def type_text(self, type_node, text, src):
        # `suspend Ctx.() -> Unit`, `context(Log) () -> Unit`: the modifiers are a sibling
        # of the function type
        prev = type_node.prev_named_sibling
        if prev is not None and prev.type == "type_modifiers":
            mods = " ".join(src[prev.start_byte:prev.end_byte].decode("utf-8", "replace").split())
            text = f"{mods} {text}"
        # `vararg val items: Item` is a property holding many Items
        owner = type_node.parent
        if owner is not None and owner.type == "class_parameter" and any(
                c.type == "modifiers" and b"vararg" in c.text for c in owner.children):
            text += "..."
        return text

    def member_name(self, kind, name):
        return "constructor" if kind == "constructor" else name

    def type_name(self, node, name):
        if node.type == "companion_object":   # `companion object Factory`, else Companion
            named = [c for c in node.named_children if c.type == "type_identifier"]
            return named[0].text.decode() if named else "Companion"
        return name

    def accepts(self, filename):
        # Gradle build and settings scripts configure the build; they are not the app
        return not filename.endswith(".gradle.kts")

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
