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


# Qt: `Q_OBJECT`, `Q_PROPERTY(int x READ x)`, `Q_DISABLE_COPY(W)` on a line of their own,
# and the `signals:` / `public slots:` sections moc reads. Only Qt's own macros, and only
# when nothing but `;` or a comment follows: `Q_FIRST = 1,` is an enum constant
_QT_MACROS = (rb"OBJECT|GADGET|GADGET_EXPORT|NAMESPACE|NAMESPACE_EXPORT|PROPERTY|PRIVATE_PROPERTY|"
              rb"ENUM|ENUMS|ENUM_NS|FLAG|FLAGS|FLAG_NS|INTERFACES|CLASSINFO|PLUGIN_METADATA|"
              rb"MOC_INCLUDE|PRIVATE_SLOT|DISABLE_COPY|DISABLE_MOVE|DISABLE_COPY_MOVE|"
              rb"DECLARE_PRIVATE|DECLARE_PRIVATE_D|DECLARE_PUBLIC|DECLARE_METATYPE|DECLARE_FLAGS|"
              rb"DECLARE_OPERATORS_FOR_FLAGS|DECLARE_INTERFACE|DECLARE_TYPEINFO|"
              rb"DECLARE_SHARED|DECLARE_LOGGING_CATEGORY|LOGGING_CATEGORY")
# also QT_BEGIN_NAMESPACE / QT_END_NAMESPACE around forward declarations, and the QML
# registration macros (QML_ELEMENT, QML_NAMED_ELEMENT(Name), ...)
# qqmlintegration.h
_QML_MACROS = (rb"ELEMENT|NAMED_ELEMENT|ANONYMOUS|INTERFACE|IMPLEMENTS_INTERFACES|UNCREATABLE|"
               rb"SINGLETON|FOREIGN|FOREIGN_NAMESPACE|EXTENDED|EXTENDED_NAMESPACE|ATTACHED|"
               rb"ADDED_IN_VERSION|ADDED_IN_MINOR_VERSION|REMOVED_IN_VERSION|"
               rb"REMOVED_IN_MINOR_VERSION|SEQUENTIAL_CONTAINER|VALUE_TYPE|CONSTRUCTIBLE_VALUE|"
               rb"STRUCTURED_VALUE|UNAVAILABLE|EXTRA_VERSION")
_QT_STATEMENT = re.compile(
    rb"^([ \t]*)(?:Q_(?:" + _QT_MACROS + rb")|QT_(?:BEGIN|END)_(?:NAMESPACE|HEADER)"
    rb"|QT_FORWARD_DECLARE_(?:CLASS|STRUCT)|QML_(?:" + _QML_MACROS + rb"))\b"
    rb"([ \t]*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?[ \t]*;?"
    rb"(?=[ \t]*(?:/\*[^\n]*?\*/[ \t]*)*(?://.*)?$)",   # then only comments
    re.MULTILINE)
# around a declaration: `Q_REVISION(1) Q_INVOKABLE void f();`, `void g() Q_DECL_OVERRIDE;`
_QT_INLINE = re.compile(rb"\b(?:Q_INVOKABLE|Q_SIGNAL|Q_SLOT|Q_SCRIPTABLE|Q_REVISION|Q_DECL_[A-Z0-9_]+)\b"
                        rb"(?:[ \t]*\([^()\n]*\))?")
_QT_SECTION = re.compile(rb"^([ \t]*)(?:(public|protected|private)([ \t]+)(?:slots|Q_SLOTS)"
                         rb"|signals|Q_SIGNALS)([ \t]*):", re.MULTILINE)


def _spaces(text: bytes) -> bytes:
    """Blank ``text`` but keep its newlines, so line numbers stay."""
    return re.sub(rb"[^\n]", b" ", text)


def _qt_section(m: re.Match) -> bytes:
    # `public slots:` -> `public      :`; `signals:` -> `public :` (signals are public)
    access = m.group(2) or b"public"
    return (m.group(1) + access).ljust(len(m.group(0)) - 1) + b":"


def alias_node_declarators(node):
    """The declarators of a `typedef`, in order."""
    return [c for i, c in enumerate(node.children) if node.field_name_for_child(i) == "declarator"]


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
        if b"Q_" in src or b"QT_" in src or b"QML_" in src or b"signals" in src or b"slots" in src:
            src = _QT_STATEMENT.sub(lambda m: m.group(1) + _spaces(m.group(0)[len(m.group(1)):]), src)
            src = _QT_INLINE.sub(lambda m: b" " * len(m.group(0)), src)
            src = _QT_SECTION.sub(_qt_section, src)
        return _blank_inline_directives(src)

    def alias_target(self, alias_node, type_node, text):
        if type_node.child_by_field_name("body") is not None:
            # `typedef struct Legacy {...} Legacy_t, *LegacyPtr;` names struct Legacy;
            # `typedef struct {...} Point;` is the struct itself, called Point
            name = type_node.child_by_field_name("name")
            if name is None and type_node.type not in ("struct_specifier", "enum_specifier"):
                return ""   # `typedef union {…} U_t;`: an alias of nothing drawn
            if name is None:
                first = next((d for d in alias_node_declarators(type_node.parent)
                              if d.type == "type_identifier"), None)
                if first is None or first.id == alias_node.id:
                    return None
                name = first
            text = name.text.decode()
        parent = alias_node.parent
        if parent is not None and parent.type == "pointer_declarator":
            text += "*"   # `typedef Circle* CirclePtr;`
        elif parent is not None and parent.type == "reference_declarator":
            text += "&"
        return text

    def is_import(self, node):
        # `using Base::Base;` in a class body is a member declaration; at file or namespace
        # level, also inside `#ifndef GUARD_H`, it imports
        cur = node.parent
        while cur is not None:
            if cur.type == "field_declaration_list":
                return False
            cur = cur.parent
        return True

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
                inner = cur.child_by_field_name("declarator")
                if inner is not None and inner.type == "parenthesized_declarator":
                    # `void (*cb)(int)`: a pointer to a function, so a field of type void(int)*
                    params = cur.child_by_field_name("parameters")
                    suffix += " ".join(params.text.decode().split()) if params else "()"
                else:
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
