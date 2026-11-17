from __future__ import annotations

import json
import os
import posixpath
import re

from pathlib import Path

from .base import SKIP_DIRS, LanguageSpec

_BUILTINS = {
    "string", "number", "boolean", "bigint", "symbol", "any", "unknown", "never", "void",
    "object", "undefined", "null", "this", "true", "false", "String", "Number", "Boolean", "Object",
    "Function", "Symbol", "BigInt", "Date", "Error", "TypeError", "RangeError", "RegExp",
    "JSON", "Math", "Intl", "ArrayBuffer", "Uint8Array", "DataView", "Iterable", "Iterator",
    "AsyncIterable", "AsyncIterator", "IterableIterator", "PromiseLike", "ReturnType",
    "Parameters", "InstanceType", "Pick", "Omit", "Exclude", "Extract", "Uppercase",
    "Lowercase", "HTMLElement", "Element", "Event", "Node", "Window", "Document", "URL",
    "Response", "Request", "Headers", "AbortSignal", "AbortController", "Buffer", "NodeJS",
    "Map", "Set", "WeakMap", "WeakSet", "WeakRef", "Array", "Promise", "IteratorResult",
    "Generator", "AsyncGenerator", "ReadableStream", "WritableStream", "EventEmitter",
    "MethodDecorator", "ClassDecorator", "PropertyDecorator", "ParameterDecorator",
    "TemplateStringsArray", "PropertyKey", "ArrayLike", "Awaited", "Record",
    # the rest of the standard library (lib.es*.d.ts): utility types, typed arrays,
    # errors, iteration, disposables, collections and reflection
    "Partial", "Required", "Readonly", "NonNullable", "ConstructorParameters",
    "ThisParameterType", "OmitThisParameter", "ThisType", "Capitalize", "Uncapitalize",
    "NoInfer", "ReadonlyArray", "ReadonlyMap", "ReadonlySet", "ConcatArray",
    "Int8Array", "Uint8ClampedArray", "Int16Array", "Uint16Array", "Int32Array",
    "Uint32Array", "Float16Array", "Float32Array", "Float64Array", "BigInt64Array",
    "BigUint64Array", "SharedArrayBuffer", "ArrayBufferLike", "ArrayBufferView",
    "EvalError", "ReferenceError", "SyntaxError", "URIError", "AggregateError",
    "ErrorConstructor", "Disposable", "AsyncDisposable", "DisposableStack",
    "AsyncDisposableStack", "SuppressedError", "AsyncIterableIterator", "IteratorObject",
    "AsyncIteratorObject", "IteratorYieldResult", "IteratorReturnResult",
    "GeneratorFunction", "AsyncGeneratorFunction", "FinalizationRegistry", "Atomics",
    "Reflect", "ProxyHandler", "PropertyDescriptor", "PropertyDescriptorMap",
    "TypedPropertyDescriptor", "ClassAccessorDecoratorContext", "ClassFieldDecoratorContext",
    "ClassMethodDecoratorContext", "ClassDecoratorContext", "ClassGetterDecoratorContext",
    "ClassSetterDecoratorContext", "DecoratorContext", "PromiseConstructorLike",
    "PromiseSettledResult", "PromiseFulfilledResult", "PromiseRejectedResult",
    "ArrayConstructor", "ObjectConstructor", "FunctionConstructor", "CallableFunction",
    "NewableFunction", "IArguments", "RegExpMatchArray", "RegExpExecArray",
    "WeakKey", "WeakRefConstructor", "BufferEncoding", "Blob", "File",
    "FormData", "TextEncoder", "TextDecoder", "URLSearchParams", "MessagePort",
}

# `export type * from "./x"` (TS 5.0) is not in the tree-sitter grammar; with `type`
# blanked it is the `export *` re-export it means for a diagram (same length, so
# line numbers stay exact)
_EXPORT_TYPE_STAR = re.compile(rb"\bexport(\s+)type(\s+)\*")

_EXT = re.compile(r"\.(d\.)?([cm]?[jt]sx?)$")
_SOURCE = re.compile(r"\.[cm]?tsx?$")


def _module(path: str) -> str:
    path = _EXT.sub("", path)
    if path.endswith("/index"):
        path = path[: -len("/index")]
    return path


class TypeScriptSpec(LanguageSpec):
    name = "typescript"
    grammar = "typescript"
    query = "typescript"
    extensions = (".ts", ".mts", ".cts")
    separator = "."
    opaque_nodes = frozenset({
        "statement_block", "arrow_function", "function_expression", "function_declaration",
        "generator_function", "generator_function_declaration", "class",
        "object_type",  # inline `{ a: T }` types: their properties are not members
    })
    modifier_node_types = frozenset({"accessibility_modifier", "override_modifier"})
    modifier_keywords = frozenset({"static", "readonly", "abstract", "async", "declare",
                                   "get", "set"})
    builtins = frozenset(_BUILTINS)
    visibility_keywords = {"public": "public", "protected": "protected", "private": "private"}
    import_suffix_match = True
    inherited_member_types = False

    def preprocess(self, src):
        return _EXPORT_TYPE_STAR.sub(lambda m: b"export" + m.group(1) + b"    " + m.group(2) + b"*",
                                     src)

    def file_namespace(self, rel):
        return _module(rel)

    def workspace_packages(self, root):
        # every package.json below the root, by its exact "name"
        found: dict[str, list[tuple[str, str]]] = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            if "package.json" not in filenames:
                continue
            try:
                meta = json.loads((Path(dirpath) / "package.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            name = meta.get("name") if isinstance(meta, dict) else None
            if not isinstance(name, str) or not name:
                continue
            rel = Path(dirpath).relative_to(root).as_posix()
            rel = "" if rel == "." else rel
            # the entry the package declares, when it is a source file (src/index.ts);
            # a built one (dist/index.d.ts) is not extracted, so the directory's index
            entry = rel + "/index" if rel else "index"
            for key in ("types", "typings", "source", "module", "main"):
                value = meta.get(key)
                if isinstance(value, str) and _SOURCE.search(value) and not value.endswith(".d.ts") \
                        and (Path(dirpath) / value).is_file():
                    entry = posixpath.normpath(posixpath.join(rel, value))
                    break
            found.setdefault(name, []).append((rel, entry))
        return found

    def workspace_modules(self, text, packages):
        # `@acme/core` is the package's entry, `@acme/core/sub` the module below it;
        # `exports` subpath maps in package.json are not read
        for name, places in packages.items():
            if text == name:
                return [_module(entry) for _, entry in places]
            if text.startswith(name + "/"):
                return [_module(posixpath.join(d, text[len(name) + 1:])) for d, _ in places]
        return []

    def module_id(self, text, rel):
        if text.startswith("."):
            return _module(posixpath.normpath(posixpath.join(posixpath.dirname(rel), text)))
        # path aliases such as "@/order/x" or "~/x" are matched by suffix later
        return _module(re.sub(r"^[@~#]/", "", text))

    def is_opaque(self, node):
        if node.type == "statement_block" and node.parent is not None \
                and node.parent.type in ("internal_module", "module"):
            return False
        return node.type in self.opaque_nodes

    def visibility(self, owner_kind, member_kind, modifiers, name, node):
        if name.startswith("#"):
            return "private"
        return super().visibility(owner_kind, member_kind, modifiers, name, node)

    def is_abstract(self, owner_kind, member_kind, modifiers, has_body, marker=None):
        return "abstract" in modifiers or (owner_kind == "interface" and member_kind == "method")

    def finalize_type(self, raw):
        for rm in raw.members:
            m = rm.member
            if m.kind == "method" and m.name == "constructor":
                m.kind = "constructor"


class TsxSpec(TypeScriptSpec):
    name = "tsx"
    grammar = "tsx"
    extensions = (".tsx",)
