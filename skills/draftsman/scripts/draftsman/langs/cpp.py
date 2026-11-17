from __future__ import annotations

import re

from .base import LanguageSpec

# `class LEVELDB_EXPORT Status {` -> export/visibility macro between keyword and name
_EXPORT_MACRO = re.compile(
    rb"\b(class|struct|union)(\s+)([A-Z][A-Z0-9_]{2,}(?:\([^()\n]*\))?)(\s+)(?=[A-Za-z_])")
# `int x GUARDED_BY(mu_);`, `void f() EXCLUSIVE_LOCKS_REQUIRED(mu_);`, `Lock(M* m) ACQUIRE(m) :`
_ATTRIBUTE_MACRO = re.compile(
    rb"(?<=[\w)\]])(\s+)([A-Z][A-Z0-9_]{2,}\([^;{}()\n]*\))"
    rb"(?=\s*(?:[;{=,:]|const\b|override\b|final\b))")
# `LEVELDB_EXPORT Iterator* NewIterator();`, `class FOO_API Bar` anywhere
_EXPORT_WORD = re.compile(
    rb"\b[A-Z][A-Z0-9_]*(?:EXPORT|_API|_DLL|_PUBLIC|_VISIBLE|_EXTERN)[A-Z0-9_]*\b(?!\s*\()")
# conditional compilation in the middle of an expression (e.g. an initializer list)
_DIRECTIVE = re.compile(rb"^[ \t]*#[ \t]*(if|ifdef|ifndef|elif|else|endif)\b.*$")


def _blank(m: re.Match, group: int) -> bytes:
    text = m.group(0)
    start, end = m.start(group) - m.start(0), m.end(group) - m.start(0)
    return text[:start] + b" " * (end - start) + text[end:]

_BUILTINS = {
    "void", "bool", "char", "wchar_t", "char8_t", "char16_t", "char32_t", "short", "int",
    "long", "float", "double", "signed", "unsigned", "auto", "size_t", "ptrdiff_t",
    "nullptr_t", "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t",
    "uint32_t", "uint64_t", "intptr_t", "uintptr_t", "string", "string_view", "wstring",
}

_DECL_CHILD = {"pointer_declarator": "*", "reference_declarator": "&", "array_declarator": "[]"}
_NAMES = {"field_identifier", "identifier", "type_identifier"}


def _blank_inline_directives(src: bytes) -> bytes:
    lines = src.split(b"\n")
    prev = b""
    for i, line in enumerate(lines):
        if _DIRECTIVE.match(line):
            if prev.rstrip().endswith((b",", b":", b"(", b")")):
                lines[i] = b" " * len(line)
            continue
        if line.strip():
            prev = line
    return b"\n".join(lines)


class CppSpec(LanguageSpec):
    name = "cpp"
    grammar = "cpp"
    extensions = (".h", ".hh", ".hpp", ".hxx", ".h++", ".cpp", ".cc", ".cxx", ".c++",
                  ".ipp", ".inl")
    separator = "::"
    opaque_nodes = frozenset({"compound_statement", "lambda_expression",
                              "field_initializer_list"})
    modifier_node_types = frozenset({"storage_class_specifier", "virtual",
                                     "explicit_function_specifier"})
    modifier_keywords = frozenset({"virtual", "static", "explicit", "inline", "friend"})
    builtins = frozenset(_BUILTINS)
    parent_namespace_lookup = True

    def is_builtin(self, name):
        return all(w in self.builtins for w in name.split())

    def preprocess(self, src):
        # Macros the parser cannot know about. Replaced by spaces, so byte offsets
        # and line numbers stay exactly as in the file.
        src = b"\n".join(
            line if line.lstrip().startswith(b"#")
            else _EXPORT_WORD.sub(lambda m: b" " * len(m.group(0)), line)
            for line in src.split(b"\n"))
        src = _EXPORT_MACRO.sub(lambda m: _blank(m, 3), src)
        src = _ATTRIBUTE_MACRO.sub(lambda m: _blank(m, 2), src)
        return _blank_inline_directives(src)

    def declarator(self, node, src):
        suffix, is_function = "", False
        cur = node
        while cur is not None:
            t = cur.type
            if t in _NAMES:
                return cur.text.decode(), suffix, is_function
            if t == "qualified_identifier":  # out-of-class definition: A::f
                name = cur.child_by_field_name("name")
                return (name.text.decode() if name is not None else None), suffix, is_function
            if t in ("destructor_name", "operator_name", "operator_cast"):
                return None, suffix, is_function
            if t == "function_declarator":
                is_function = True
            elif t in _DECL_CHILD:
                sigil = _DECL_CHILD[t]
                if t == "reference_declarator" and b"&&" in cur.text[:3]:
                    sigil = "&&"
                suffix += sigil
            elif t not in ("init_declarator", "parenthesized_declarator",
                           "attributed_declarator"):
                return None, suffix, is_function
            nxt = cur.child_by_field_name("declarator")
            if nxt is None:
                nxt = next((c for c in cur.named_children
                            if c.type in _NAMES or c.type.endswith("declarator")
                            or c.type == "qualified_identifier"), None)
            cur = nxt
        return None, suffix, is_function

    def visibility(self, owner_kind, member_kind, modifiers, name, node):
        if member_kind == "enum_constant":
            return "public"
        cur = node
        while cur is not None and cur.parent is not None \
                and cur.parent.type != "field_declaration_list":
            cur = cur.parent
        sib = cur.prev_named_sibling if cur is not None else None
        while sib is not None:
            if sib.type == "access_specifier":
                return sib.text.decode().strip()
            sib = sib.prev_named_sibling
        return "public" if owner_kind == "struct" else "private"

    def is_static(self, owner_kind, member_kind, modifiers):
        return member_kind == "enum_constant" or "static" in modifiers

    def is_abstract(self, owner_kind, member_kind, modifiers, has_body, marker=None):
        return member_kind == "method" and marker == "0"

    def finalize_type(self, raw):
        if raw.kind not in ("class", "struct"):
            return
        methods = [rm.member for rm in raw.members if rm.member.kind == "method"]
        if not any(m.abstract for m in methods):
            return
        fields = [rm.member for rm in raw.members
                  if rm.member.kind == "field" and not rm.member.static]
        # only pure virtual methods and no state: an interface in all but name
        raw.kind = "interface" if not fields and all(m.abstract for m in methods) \
            else "abstract_class"
