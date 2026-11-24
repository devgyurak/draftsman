from __future__ import annotations

import re

from .base import LanguageSpec

_DOTTED_NAME = re.compile(r"^\w+(?:\s*\.\s*\w+)*$")

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
    # the top type of Kotlin/Wasm's JS interop, written where Any would be: `: JsAny`
    **_in("kotlin.js", "JsAny"),
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
    **_in("kotlin.js", "JsNumber JsString JsBoolean JsArray JsBigInt JsReference JsName "
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

# Library types reached through a star import of their package (`import kotlinx.coroutines.*`),
# from the packages' API references: kotlinlang.org/api/core/kotlin-stdlib (2.4) for
# kotlin.coroutines and kotlin.reflect, kotlinlang.org/api/kotlinx.coroutines (1.11.0) for
# the rest. Classifiers only: no functions (`SupervisorJob()`), no typealiases
# (`CompletionHandler`), and none whose `actual` is a typealias on some platform in the
# kotlinx.coroutines 1.11.0 sources: `CancellationException` (also in
# kotlin.coroutines.cancellation), `Runnable` (java.lang.Runnable on the JVM),
# `CloseableCoroutineDispatcher` (ExecutorCoroutineDispatcher on the JVM).
_LIBRARY: dict[str, tuple[str, ...]] = {}
# Library types that are common supertypes: (their own nested classifiers, their supertypes),
# from the types' API pages and the kotlinx.coroutines 1.11.0 sources. In a class that
# extends one, its nested classifiers and those of its supertypes are in scope without
# qualification and come before any import, so the table does not apply to those names
# there. Under a supertype not listed, any nested type is possible: no table at all.
_SUPERTYPES: dict[str, tuple[frozenset, tuple[str, ...]]] = {
    "kotlin.coroutines.CoroutineContext": (frozenset({"Element", "Key"}), ()),
    "kotlin.coroutines.CoroutineContext.Element": (frozenset(), ("kotlin.coroutines.CoroutineContext",)),
    "kotlin.coroutines.AbstractCoroutineContextElement":
        (frozenset(), ("kotlin.coroutines.CoroutineContext.Element",)),
    "kotlin.coroutines.Continuation": (frozenset(), ()),
    "kotlin.coroutines.ContinuationInterceptor":
        (frozenset({"Key"}), ("kotlin.coroutines.CoroutineContext.Element",)),
    "kotlinx.coroutines.CoroutineScope": (frozenset(), ()),
    "kotlinx.coroutines.DisposableHandle": (frozenset(), ()),
    "kotlinx.coroutines.Job": (frozenset({"Key"}), ("kotlin.coroutines.CoroutineContext.Element",)),
    "kotlinx.coroutines.CompletableJob": (frozenset(), ("kotlinx.coroutines.Job",)),
    "kotlinx.coroutines.Deferred": (frozenset(), ("kotlinx.coroutines.Job",)),
    "kotlinx.coroutines.CoroutineDispatcher": (frozenset(), (
        "kotlin.coroutines.AbstractCoroutineContextElement", "kotlin.coroutines.ContinuationInterceptor")),
    "kotlinx.coroutines.CoroutineExceptionHandler":
        (frozenset({"Key"}), ("kotlin.coroutines.CoroutineContext.Element",)),
    "kotlinx.coroutines.flow.Flow": (frozenset(), ()),
    "kotlinx.coroutines.flow.FlowCollector": (frozenset(), ()),
    "kotlinx.coroutines.channels.Channel": (frozenset({"Factory"}), (
        "kotlinx.coroutines.channels.SendChannel", "kotlinx.coroutines.channels.ReceiveChannel")),
    "kotlinx.coroutines.channels.SendChannel": (frozenset(), ()),
    "kotlinx.coroutines.channels.ReceiveChannel": (frozenset(), ()),
    "kotlinx.coroutines.channels.ChannelIterator": (frozenset(), ()),
    # kotlin.* (API pages; on the JVM these are java.lang classes, none with a nested class
    # in the Java SE 21 API)
    "kotlin.AutoCloseable": (frozenset(), ()),
    "kotlin.Throwable": (frozenset(), ()),
    "kotlin.Exception": (frozenset(), ("kotlin.Throwable",)),
    "kotlin.RuntimeException": (frozenset(), ("kotlin.Exception",)),
    "kotlin.IllegalStateException": (frozenset(), ("kotlin.RuntimeException",)),
    "kotlin.IllegalArgumentException": (frozenset(), ("kotlin.RuntimeException",)),
    # kotlinx.serialization 1.11.0 sources; sealed ones (Json, JsonElement,
    # SerializersModule) cannot be extended outside the library
    "kotlinx.serialization.SerializationStrategy": (frozenset(), ()),
    "kotlinx.serialization.DeserializationStrategy": (frozenset(), ()),
    "kotlinx.serialization.KSerializer": (frozenset(), (
        "kotlinx.serialization.SerializationStrategy",
        "kotlinx.serialization.DeserializationStrategy")),
    "kotlinx.serialization.SerialFormat": (frozenset(), ()),
    "kotlinx.serialization.StringFormat": (frozenset(), ("kotlinx.serialization.SerialFormat",)),
    "kotlinx.serialization.BinaryFormat": (frozenset(), ("kotlinx.serialization.SerialFormat",)),
    "kotlinx.serialization.descriptors.SerialDescriptor": (frozenset(), ()),
    "kotlinx.serialization.encoding.Decoder": (frozenset(), ()),
    "kotlinx.serialization.encoding.Encoder": (frozenset(), ()),
    "kotlinx.serialization.encoding.CompositeDecoder": (frozenset({"Companion"}), ()),
    "kotlinx.serialization.encoding.CompositeEncoder": (frozenset(), ()),
    "kotlinx.serialization.encoding.AbstractDecoder": (frozenset(), (
        "kotlinx.serialization.encoding.Decoder", "kotlinx.serialization.encoding.CompositeDecoder")),
    "kotlinx.serialization.encoding.AbstractEncoder": (frozenset(), (
        "kotlinx.serialization.encoding.Encoder", "kotlinx.serialization.encoding.CompositeEncoder")),
    "kotlinx.serialization.modules.SerializersModuleCollector": (frozenset(), ()),
    "kotlinx.serialization.json.JsonDecoder": (frozenset(), (
        "kotlinx.serialization.encoding.Decoder", "kotlinx.serialization.encoding.CompositeDecoder")),
    "kotlinx.serialization.json.JsonEncoder": (frozenset(), (
        "kotlinx.serialization.encoding.Encoder", "kotlinx.serialization.encoding.CompositeEncoder")),
    "kotlinx.serialization.json.JsonContentPolymorphicSerializer":
        (frozenset(), ("kotlinx.serialization.KSerializer",)),
    "kotlinx.serialization.json.JsonTransformingSerializer":
        (frozenset(), ("kotlinx.serialization.KSerializer",)),
}


def _nested_in_scope(type_id: str) -> frozenset:
    own, supers = _SUPERTYPES[type_id]
    return own.union(*(_nested_in_scope(s) for s in supers))


_NESTED: dict[str, frozenset] = {t: _nested_in_scope(t) for t in _SUPERTYPES}

for _package, _names in {
    "kotlin.coroutines": "AbstractCoroutineContextElement AbstractCoroutineContextKey "
                         "Continuation ContinuationInterceptor CoroutineContext "
                         "EmptyCoroutineContext ExperimentalStdlibCoroutineSupportApi "
                         "RestrictsSuspension SuspendFunction",
    "kotlin.reflect": "AssociatedObjectKey ExperimentalAssociatedObjects KAnnotatedElement "
                      "KCallable KClass KClassifier KDeclarationContainer KFunction "
                      "KMutableProperty KMutableProperty0 KMutableProperty1 KMutableProperty2 "
                      "KParameter KProperty KProperty0 KProperty1 KProperty2 KType "
                      "KTypeParameter KTypeProjection KVariance KVisibility",
    "kotlinx.coroutines": "CancellableContinuation CompletableDeferred CompletableJob "
                          "CopyableThreadContextElement CopyableThrowable CoroutineDispatcher "
                          "CoroutineExceptionHandler "
                          "CoroutineName CoroutineScope CoroutineStart Deferred "
                          "DelicateCoroutinesApi Dispatchers DisposableHandle "
                          "ExecutorCoroutineDispatcher ExperimentalCoroutinesApi "
                          "ExperimentalForInheritanceCoroutinesApi FlowPreview GlobalScope "
                          "InternalCoroutinesApi InternalForInheritanceCoroutinesApi Job "
                          "MainCoroutineDispatcher NonCancellable ObsoleteCoroutinesApi "
                          "ThreadContextElement TimeoutCancellationException",
    "kotlinx.coroutines.channels": "ActorScope BufferOverflow Channel ChannelIterator "
                                   "ChannelResult ClosedReceiveChannelException "
                                   "ClosedSendChannelException ProducerScope ReceiveChannel "
                                   "SendChannel TickerMode",
    "kotlinx.coroutines.flow": "AbstractFlow Flow FlowCollector MutableSharedFlow "
                               "MutableStateFlow SharedFlow SharingCommand SharingStarted "
                               "StateFlow",
    # kotlinx.serialization: names both in the API reference (1.13.0) and the 1.11.0
    # sources Ktor builds with (ChunkedDecoder, only in the sources, is left out)
    "kotlinx.serialization": "BinaryFormat Contextual ContextualSerializer "
                             "DeserializationStrategy EncodeDefault ExperimentalSerializationApi "
                             "InheritableSerialInfo InternalSerializationApi KSerializer "
                             "KeepGeneratedSerializer MetaSerializable MissingFieldException "
                             "Polymorphic PolymorphicSerializer Required SealedClassSerializer "
                             "SealedSerializationApi SerialFormat SerialInfo SerialName "
                             "Serializable SerializationException SerializationStrategy "
                             "Serializer StringFormat Transient UseContextualSerialization "
                             "UseSerializers",
    "kotlinx.serialization.descriptors": "ClassSerialDescriptorBuilder PolymorphicKind "
                                         "PrimitiveKind SerialDescriptor SerialKind StructureKind",
    "kotlinx.serialization.encoding": "AbstractDecoder AbstractEncoder CompositeDecoder "
                                      "CompositeEncoder Decoder Encoder",
    "kotlinx.serialization.modules": "PolymorphicModuleBuilder SerializersModule "
                                     "SerializersModuleBuilder SerializersModuleCollector",
    "kotlinx.serialization.json": "ClassDiscriminatorMode DecodeSequenceMode Json JsonArray "
                                  "JsonArrayBuilder JsonBuilder JsonClassDiscriminator "
                                  "JsonConfiguration JsonContentPolymorphicSerializer JsonDecoder "
                                  "JsonDecodingException JsonElement JsonEncoder "
                                  "JsonEncodingException JsonException JsonIgnoreUnknownKeys "
                                  "JsonNames JsonNamingStrategy JsonNull JsonObject "
                                  "JsonObjectBuilder JsonPrimitive JsonTransformingSerializer",
}.items():
    for _name in _names.split():
        _LIBRARY[_name] = _LIBRARY.get(_name, ()) + (_package,)


# source sets every other one of a module sees: Kotlin Multiplatform's common one
# (`common/src` in Ktor's layout, `src/commonMain/kotlin`), a single-platform module's
# `src/main`
_COMMON_SOURCE_SETS = frozenset({"common", "commonMain", "main"})


_APPLE_SOURCE_SETS = ("ios", "macos", "tvos", "watchos", "darwin", "apple")


def _source_set(file: str, module) -> str:
    """The source set of a file of the module (a path below the extraction root): Ktor's
    `<module>/<set>/src/...`, Gradle's `<module>/src/<set>/kotlin/...`, else `main`."""
    rel = file[len(module) + 1:] if module else file
    parts = rel.split("/")
    if parts[0] == "src":
        return parts[1] if len(parts) > 3 and parts[2] in ("kotlin", "java") else "main"
    if len(parts) > 2 and parts[1] == "src":
        return parts[0]
    return "main"


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
    # a name in a body: `Foo.x`, `p.Foo.x`, `Foo::class`; `Box<Cash>`'s arguments are names
    # of their own
    receiver_part_nodes = frozenset({"simple_identifier", "navigation_expression",
                                     "navigation_suffix", "type_identifier"})
    type_argument_nodes = frozenset({"type_arguments"})
    alias_declarations = True
    outside_supers_hide = True
    file_local_copies = True
    class_nested_only = True
    alias_import_hides = True
    static_scope_nodes = frozenset({"companion_object"})
    static_scope_names = frozenset({"Companion"})
    annotation_nodes = frozenset({"annotation"})
    annotation_value_args = frozenset({"navigation_expression"})   # `Kind.A`
    annotation_name_field = "-"   # no name field: use the annotation's text

    def annotation_arg(self, node, text):
        if node.type in ("callable_reference", "navigation_expression") and \
                "::" in (written := text(node)):
            # `X::class`, `Outer.Inner::class` (a navigation to `::class`); `X::create`
            # names X or a value
            head, tail = (p.strip() for p in written.rsplit("::", 1))
            if _DOTTED_NAME.match(head):
                return head, tail == "class"
            return None   # `listOf(A::class)` inside a call: look inside it
        return super().annotation_arg(node, text)
    # `dynamic` is Kotlin/JS's dynamic type: a soft keyword, never a class
    builtins = frozenset(_CORE) | {"dynamic"}
    visibility_keywords = {
        "public": "public", "protected": "protected", "private": "private",
        "internal": "internal",
    }

    def builtin_id(self, name):
        return f"{_CORE[name]}.{name}" if name in _CORE else name

    def library_type(self, name, imported, arity=None, external_supers=None):
        # only through a star import of the package, and only when exactly one of the
        # star-imported packages has the name: two would be an ambiguity error in Kotlin
        # a core type or default import of the name (`Transient`, kotlin.js `Json`) is not
        # overruled: which of the two a star import gets is not decided here either
        if name in _CORE or name in _DEFAULTS:
            return None
        packages = [p for p in _LIBRARY.get(name, ()) if p in imported]
        if len(packages) != 1:
            return None
        # a nested type of a supertype comes before any import; one of an external
        # supertype is known only for the types listed in _NESTED
        for sup in external_supers() if external_supers else ():
            if sup not in _NESTED or name in _NESTED[sup]:
                return None
        return f"{packages[0]}.{name}"

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

    def project_imports(self, path, root):
        # the Gradle module a file is in: the nearest directory with a build script
        root = root.resolve()
        cur = path.resolve().parent
        while cur != root and root in cur.parents:
            if (cur / "build.gradle.kts").is_file() or (cur / "build.gradle").is_file():
                return cur.relative_to(root).as_posix(), []
            cur = cur.parent
        return None, []

    def sees_declaration(self, scope, target, namespace, declared):
        # a platform's source set (jvm, posix, a flavor) sees its own and the common ones;
        # which others it depends on (jvm on jvmAndPosix) the build says, not the sources
        mine = _source_set(scope.file, scope.project)
        if not any((s := _source_set(f, p)) in _COMMON_SOURCE_SETS or s == mine
                   for f, p in declared):
            return False
        # a type of the file's package in other modules only is seen if the file's module
        # depends on one of them, which the build says: not where a star import or a default
        # import may bring in the name instead (the file's package comes before them)
        name = target.rsplit(".", 1)[-1]
        if namespace == scope.namespace and scope.project not in {p for _, p in declared} \
                and not any(i.local_name == name for i in scope.imports if not i.wildcard):
            return not any(i.wildcard for i in scope.imports) and self.default_import(name) is None
        return True

    def unbuilt_ranges(self, src, path, root):
        # an Apple target's source set (ios, macos, tvos, watchos, darwin, apple; Ktor's
        # `darwin/src`, Gradle's `src/iosMain`): only a macOS host builds it, which no
        # answer key here can
        module, _ = self.project_imports(path, root)
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        name = _source_set(rel, module).lower()
        return [(0, len(src))] if name.startswith(_APPLE_SOURCE_SETS) else []

    def outside_member(self, super_id, name, nested_only):
        # nested types: known of the library supertypes _NESTED lists; members (properties
        # and functions) of none
        if nested_only and super_id in _NESTED:
            return name in _NESTED[super_id]
        return True

    def outside_functions(self, scope):
        # Kotlin/Native's platform libraries (`platform.posix`, `platform.windows`) are C
        # APIs: functions of any name, `WinHttpConnect` beside a class of the name
        return any(imp.wildcard and imp.path.startswith("platform.") for imp in scope.imports)

    def file_local(self, modifiers):
        # a private top-level class is seen in its file only (a private nested one in its
        # outer class, which is in one file too)
        return "private" in modifiers

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
