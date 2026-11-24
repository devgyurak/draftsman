from __future__ import annotations

import re

from .base import LanguageSpec

# `class LEVELDB_EXPORT Status {` -> export/visibility macro between keyword and name
_EXPORT_MACRO = re.compile(
    rb"\b(class|struct|union)(\s+)([A-Z][A-Z0-9_]{2,}(?:\([^()\n]*\))?)(\s+)(?=[A-Za-z_])")
# `int x GUARDED_BY(mu_);`, `void f() EXCLUSIVE_LOCKS_REQUIRED(mu_);`, `Lock(M* m) ACQUIRE(m) :`,
# `E_OLD POCO_DEPRECATED("since 4.2; use f() instead") = 4,`: a string argument may hold
# anything
_ATTRIBUTE_MACRO = re.compile(
    rb"(?<=[\w)\]])(\s+)([A-Z][A-Z0-9_]{2,}\((?:[^;{}()\"\n]|\"(?:[^\"\\\n]|\\.)*\")*\))"
    rb"(?=\s*(?:[;{=,:]|const\b|override\b|final\b))")
# `LEVELDB_EXPORT Iterator* NewIterator();`, `class FOO_API Bar` anywhere; also in mixed
# case, as POCO writes them: `Foundation_API`, `NetSSL_Win_API`, `DNSSD_Bonjour_API`
_EXPORT_WORD = re.compile(
    rb"\b(?:[A-Z][A-Z0-9_]*(?:EXPORT|_API|_DLL|_PUBLIC|_VISIBLE|_EXTERN)[A-Z0-9_]*"
    rb"|[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*_(?:API|EXPORT|DLL|PUBLIC|VISIBLE|EXTERN))"
    rb"\b(?!\s*\()(?=\s+[A-Za-z_~])")   # a declaration goes on: not `== ACC_PUBLIC)`
# by position, whatever its name: `class MACRO Name :`, `class MACRO(x) Name {`,
# `struct MACRO Name final` - two identifiers after the keyword and a class head after
# them. Not when the first is all lower case (`struct sockaddr_in addr{};`, `alignas(8)`,
# `__declspec(dllexport)`, which the grammar knows), nor `class Name final`
_CLASS_MACRO = re.compile(
    rb"\b(class|struct|union)(\s+)((?![a-z0-9_]+\b)[A-Za-z_]\w*(?:\([^()\n]*\))?)(\s+)"
    rb"(?!final\b)([A-Za-z_]\w*)(?=\s*(?::(?!:)|\{|final\b))")
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


def _class_macro(m: re.Match) -> bytes:
    # `struct Point origin{0, 0};` declares a variable: a lower-case name and a brace
    if m.group(1) != b"class" and m.group(5)[:1].islower() \
            and m.string[m.end():m.end() + 64].lstrip().startswith(b"{"):
        return m.group(0)
    return _blank(m, 3)


def _blank(m: re.Match, group: int) -> bytes:
    text = m.group(0)
    start, end = m.start(group) - m.start(0), m.end(group) - m.start(0)
    return text[:start] + b" " * (end - start) + text[end:]


_QUALIFIERS = {b"const", b"static", b"constexpr", b"constinit", b"inline", b"extern",
               b"mutable", b"volatile", b"thread_local", b"typename", b"struct", b"class",
               b"enum", b"union", b"unsigned", b"signed", b"long", b"short"}
# before a name and `(`, a declaration or an expression goes on, no attribute
_KEYWORDS = {b"explicit", b"virtual", b"friend", b"inline", b"static", b"constexpr",
             b"consteval", b"return", b"new", b"delete", b"throw", b"else", b"case",
             b"typedef", b"using", b"co_return", b"co_yield", b"co_await", b"operator"}
_ESCAPE = re.compile(rb"\\.")
# keywords a member cannot be named
_RESERVED = {"sizeof", "alignof", "decltype", "noexcept", "static_assert", "typeid",
             "offsetof", "struct", "class", "union", "enum", "return", "new", "delete"}


def _attribute_macro(m: re.Match) -> bytes:
    """Blank an attribute macro after a declarator (`int x_ GUARDED_BY(mu_);`), but not
    an upper-case variable initialised with parentheses after its type (`const std::string
    SENTINEL("=?");`, `static const Poco::Timespan WAIT(1, 0);`), nor inside a string
    literal (`std::string code("static const std::string NS(\\"");`)."""
    src, start = m.string, m.start()
    line = src[src.rfind(b"\n", 0, start) + 1:start]
    if _ESCAPE.sub(b"", line).count(b'"') % 2:
        return m.group(0)
    word = start
    while word > 0 and (src[word - 1:word].isalnum() or src[word - 1:word] == b"_"):
        word -= 1
    if src[word:start] in _KEYWORDS:   # `explicit URI(const std::string& uri);`
        return m.group(0)
    if src[start - 1:start] not in b")]" and src[m.end():m.end() + 64].lstrip()[:1] in (b";", b","):
        # `Type NAME(...);` declares NAME when the word before it starts a declaration
        before = src[:word].rstrip()
        prev = re.search(rb"(\w+)$", before)
        # `VersionSet* const versions_ GUARDED_BY(mutex_);`: a const pointer, then its name
        const_pointer = prev is not None and prev.group(1) in (b"const", b"volatile") \
            and before[:prev.start()].rstrip().endswith((b"*", b"&"))
        at_line_start = not src[src.rfind(b"\n", 0, word) + 1:word].strip()
        if not before or at_line_start \
                or before.endswith((b"::", b"(", b";", b"{", b"}", b"<", b":", b"/")) \
                or (prev is not None and prev.group(1) in _QUALIFIERS and not const_pointer):
            return m.group(0)
    return _blank(m, 2)

_BUILTINS = {
    "void", "bool", "char", "wchar_t", "char8_t", "char16_t", "char32_t", "short", "int",
    "long", "float", "double", "signed", "unsigned", "auto", "size_t", "ptrdiff_t",
    "nullptr_t", "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t",
    "uint32_t", "uint64_t", "intptr_t", "uintptr_t", "string", "string_view", "wstring",
}

_DECL_CHILD = {"pointer_declarator": "*", "reference_declarator": "&", "array_declarator": "[]"}
_NAMES = {"field_identifier", "identifier", "type_identifier"}


# a statement macro on a line of its own, without `;`: `POCO_DECLARE_EXCEPTION(API, E, B)`,
# `POCO_CHECK_MINMAX_MACROS`. Upper case with an underscore, then only comments
_STATEMENT_MACRO = re.compile(
    rb"^[ \t]*[A-Z][A-Z0-9]*_[A-Z0-9_]+(?:[ \t]*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?"
    rb"[ \t]*(?:/\*.*?\*/[ \t]*)*(?://.*)?$")
_COMMENT = re.compile(rb"/\*.*?\*/|//[^\n]*")


def _blank_statement_macros(src: bytes) -> bytes:
    """Blank statement macros where a declaration may start: after `;`, `{` or `}` (or at
    the start of the file), and not before a `{` (`TEST(A, B)` then a body) nor, without
    arguments, before `name(` (`MY_TYPE` then `compute(P p);`: a return type). Not after
    `,` or `:` (`MAX_SIZE(10)` in an initializer list), and not as the only line of an
    enum (`enum E {` / `ONLY_ONE` / `};`)."""
    lines = src.split(b"\n")
    code = []   # (line index, text without comments) of the lines that hold code
    continued = False
    for i, line in enumerate(lines):
        directive = continued or line.lstrip().startswith(b"#")
        continued = directive and line.rstrip().endswith(b"\\")
        text = _COMMENT.sub(b"", line).strip()
        if text and not directive:
            code.append((i, text))
    for k, (i, text) in enumerate(code):
        if not _STATEMENT_MACRO.match(lines[i]) or text.endswith(b";"):
            continue
        prev = code[k - 1][1] if k else b";"
        if not prev.endswith((b";", b"{", b"}")):
            continue
        nxt = code[k + 1][1] if k + 1 < len(code) else b""
        if nxt.startswith(b"{"):
            continue
        # `MY_TYPE` alone, then `compute(P p);`: a return type on a line of its own
        if b"(" not in text and re.match(rb"~?[A-Za-z_]\w*\s*\(", nxt):
            continue
        if prev.endswith(b"{") and any(re.search(rb"\benum\b", t) for _, t in code[max(0, k - 2):k]):
            continue
        lines[i] = _spaces(lines[i])
        code[k] = (i, b";")   # a statement ended here, for the next line to judge by
    return b"\n".join(lines)


# an attribute macro where a declaration starts: `POCO_DEPRECATED("...") void old();`,
# `[[nodiscard]] POCO_DEPRECATED("...")` (the declaration on the next line), and without
# arguments only `POCO_NODISCARD_CTOR Request(int)`: a word like `HANDLE` or `DWORD` there
# is a return type
_LEADING_MACRO = re.compile(
    rb"^([ \t]*(?:\[\[[^\]\n]*\]\][ \t]*)*)"
    rb"([A-Z][A-Z0-9]*_[A-Z0-9_]+)([ \t]*\((?:[^()\n]|\([^()\n]*\))*\))?")
_ATTRIBUTE_WORDS = re.compile(rb"_(?:NODISCARD|DEPRECATED|INLINE|CONSTEXPR|NOEXCEPT|EXPLICIT)(?:_|$)")
_ACCESS = re.compile(rb"^(?:public|protected|private)\s*:$")
_TEMPLATE_HEAD = re.compile(rb"^template\s*<.*>$")
_TYPE_NAME = re.compile(rb"\b(?:class|struct)\s+(\w+)\s*(?:final\s*)?[:{]")


def _blank_leading_macros(src: bytes) -> bytes:
    """Blank attribute macros at the start of a declaration (see _LEADING_MACRO): after
    `;`, `{`, `}`, an access specifier, a `template <...>` head or a `[[...]]` attribute."""
    if b"_" not in src:
        return src
    lines = src.split(b"\n")
    classes = set(_TYPE_NAME.findall(src))
    prev = b";"
    continued = False
    for i, line in enumerate(lines):
        directive = continued or line.lstrip().startswith(b"#")
        continued = directive and line.rstrip().endswith(b"\\")
        text = _COMMENT.sub(b"", line).strip()
        if not text or directive:
            continue
        m = _LEADING_MACRO.match(line)
        at_start = m is not None and (prev.endswith((b";", b"{", b"}"))
                                      or bool(_ACCESS.match(prev) or _TEMPLATE_HEAD.match(prev))
                                      or b"[[" in m.group(1))
        if at_start:
            name, args = m.group(2), m.group(3)
            rest = _COMMENT.sub(b"", line[m.end():]).strip()
            if args:
                # alone on its line, the declaration follows; unless a body does
                # (`TEST_CASE(A, B)` then `{`: a function the macro defines)
                nxt = next((t for t in (_COMMENT.sub(b"", x).strip() for x in lines[i + 1:])
                            if t and not t.startswith(b"#")), b"")
                ok = re.match(rb"[A-Za-z_~]|\[\[", rest) is not None if rest \
                    else not nxt.startswith(b"{")
            else:
                after = re.match(rb"~?(\w+)\s*\(", rest)
                ok = bool(_ATTRIBUTE_WORDS.search(name)) and re.match(rb"[A-Za-z_~]", rest) \
                    or (after is not None and after.group(1) in classes)
            if ok:
                start = m.start(2)
                lines[i] = line[:start] + _spaces(line[start:m.end()]) + line[m.end():]
                text = _COMMENT.sub(b"", lines[i]).strip() or b";"
        prev = text
    return b"\n".join(lines)


def _blank_inline_directives(src: bytes) -> bytes:
    """Blank an `#if` group whose `#if` sits inside an expression (the code line before it
    ends with `,` `:` `(` `)` `=`): the group's `#elif`/`#else`/`#endif` go with it. After
    `=` the branches are alternative values, so only the first stays (`MAX = #if V6
    sizeof(in6_addr) #else sizeof(in_addr) #endif`); elsewhere every branch stays (members
    or initializers of each platform). The lines of other directives (`#define MIN(a, b)
    (...)`, `#pragma pack(push, 1)`) are no code line to judge by."""
    inside = (b",", b":", b"(", b")", b"=")
    lines = src.split(b"\n")
    prev = b""
    groups: list[list[bool]] = []   # per open `#if`: [blanked, first branch only, past it]
    continued = False               # inside a directive continued with `\`
    for i, line in enumerate(lines):
        skipping = any(g[2] for g in groups)
        directive = continued or line.lstrip().startswith(b"#")
        continued = directive and line.rstrip().endswith(b"\\")
        m = _DIRECTIVE.match(line)
        if m:
            word = m.group(1)
            if word.startswith(b"if"):
                end = prev.rstrip()
                groups.append([skipping or end.endswith(inside), end.endswith(b"="), False])
                blank = groups[-1][0]
            else:
                blank = groups[-1][0] if groups else prev.rstrip().endswith(inside)
                if word == b"endif" and groups:
                    groups.pop()
                elif groups and groups[-1][1]:
                    groups[-1][2] = True
            if blank:
                lines[i] = b" " * len(line)
            continue
        if skipping:
            lines[i] = b" " * len(line)
            continue
        if line.strip() and not directive:
            prev = line
    return b"\n".join(lines)


def _template_params(tmpl) -> list[str]:
    """The names of a template declaration's parameters."""
    params = tmpl.child_by_field_name("parameters")
    out = []
    for p in (params.named_children if params is not None else ()):
        for c in p.named_children:
            if c.type in ("type_identifier", "identifier"):
                out.append(c.text.decode())
                break
            if c.type == "variadic_declarator" and c.named_children:
                out.append(c.named_children[0].text.decode())
                break
    return out


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
    # bodies (issue #5)
    type_argument_nodes = frozenset({"template_argument_list"})
    receiver_part_nodes = frozenset({"identifier", "field_identifier", "type_identifier",
                                     "namespace_identifier", "qualified_identifier",
                                     "template_function", "template_method", "template_type"})
    ref_priority = ("call", "receiver", "type")
    values_hide_types = True
    file_local_bodies = True
    include_visibility = True

    def branch_ranges(self, src):
        # every branch of an `#if` group but an include guard (`#ifndef X` / `#define X`
        # around the file) and `#ifdef __cplusplus`, innermost first
        lines = src.split(b"\n")
        offsets, at = [], 0
        for line in lines:
            offsets.append(at)
            at += len(line) + 1
        out, stack = [], []   # stack: [kind, start line index, guard]
        for i, line in enumerate(lines):
            m = _DIRECTIVE.match(line)
            if not m:
                continue
            word = m.group(1)
            if word.startswith(b"if"):
                guard = b"__cplusplus" in line or (
                    word == b"ifndef" and i + 1 < len(lines)
                    and re.match(rb"\s*#\s*define\s+" + re.escape(line.split()[-1]) + rb"\b",
                                 lines[i + 1]) is not None)
                stack.append([i, guard])
            elif stack:
                start, guard = stack[-1]
                if not guard:
                    out.append((offsets[start], offsets[i], start + 1, i + 1))
                if word == b"endif":
                    stack.pop()
                else:
                    stack[-1][0] = i
        out.sort(key=lambda r: r[1] - r[0])   # innermost first
        return out

    def unreadable(self, node):
        # a function defined inside a block is a parse the grammar could not close (an `#if`
        # inside a function that swallowed the functions after it): nothing in it is read
        cur = node.parent
        while cur is not None:
            if cur.type == "function_definition":
                up = cur.parent
                while up is not None and up.type.startswith("preproc_"):
                    up = up.parent
                if up is not None and up.type == "compound_statement":
                    return True   # (a local class's member functions are in its body)
            cur = cur.parent
        return False

    def alias_params(self, node):
        decl = node.parent
        tmpl = decl.parent if decl is not None and decl.type == "alias_declaration" else None
        if tmpl is None or tmpl.type != "template_declaration":
            return []
        return _template_params(tmpl)

    def init_via(self, node, src):
        # a friend function, an operator or a destructor defined in its class: its name
        # (`operator==`, `~Foo`, `operator bool`)
        while node.type == "template_declaration":
            node = next((c for c in node.named_children if c.type == "function_definition"), node)
            if node.type == "template_declaration":
                break
        decl = node.child_by_field_name("declarator")
        if decl is not None and decl.type == "operator_cast":
            return " ".join(decl.text.decode().split("(")[0].split())
        while decl is not None and decl.type != "function_declarator":   # `Foo& operator=(...)`
            decl = decl.child_by_field_name("declarator") or next(
                (c for c in decl.named_children if c.type.endswith("declarator")), None)
        inner = decl.child_by_field_name("declarator") if decl is not None else None
        return " ".join(inner.text.decode().split()) if inner is not None else None

    def ref_text(self, node, text):
        if node.type == "qualified_identifier" and node.child_by_field_name("scope") is None:
            return "::" + text   # `::Helper`
        return text

    def ref_position(self, node, position):
        # `Lock l(Tag);` in a block: a declaration of l, a variable initialised with Tag or a
        # function taking a Tag; a variable Tag hides the type there
        if position != "type":
            return position
        cur = node
        while cur.parent is not None and cur.parent.type in ("qualified_identifier", "template_type"):
            cur = cur.parent
        param = cur.parent
        if param is None or param.type != "parameter_declaration" \
                or param.child_by_field_name("type") != cur:
            return position
        fn = param.parent.parent if param.parent is not None else None
        decl = fn.parent if fn is not None and fn.type == "function_declarator" else None
        if decl is not None and decl.type == "declaration" and decl.parent is not None \
                and decl.parent.type == "compound_statement":
            return "receiver"
        return position

    def detached_owner(self, node, src):
        # `void Foo::bar() {}`, `Foo::Foo() : ... {}`, `int Foo::x = 1;` at a namespace's scope:
        # not in a class (a member defined there is the class's already), nor in a body
        cur = node.parent
        tparams: list[str] = []
        while cur is not None and cur.type in ("template_declaration", "preproc_if",
                                               "preproc_ifdef", "preproc_else", "preproc_elif",
                                               "preproc_elifdef"):
            if cur.type == "template_declaration":
                params = cur.child_by_field_name("parameters")
                if params is None or not params.named_children:
                    return None   # `template <>`: a specialisation's member, not read
                tparams += _template_params(cur)
            cur = cur.parent
        if cur is not None and cur.type not in ("translation_unit", "declaration_list",
                                                "linkage_specification"):
            return None
        if self.unreadable(node.child_by_field_name("declarator") or node):
            return None
        decl = node.child_by_field_name("declarator")
        while decl is not None and decl.type in ("pointer_declarator", "reference_declarator",
                                                 "function_declarator", "init_declarator",
                                                 "parenthesized_declarator"):
            nxt = decl.child_by_field_name("declarator")
            if nxt is None:
                nxt = next((c for c in decl.named_children
                            if c.type.endswith("declarator") or c.type == "qualified_identifier"), None)
            decl = nxt
        if decl is None or decl.type != "qualified_identifier":
            return None
        parts = []
        cur = decl
        while cur is not None and cur.type == "qualified_identifier":
            scope = cur.child_by_field_name("scope")
            if scope is None:
                return None   # `::f()`: the global namespace's
            parts.append(scope)
            cur = cur.child_by_field_name("name")
        if cur is None:
            return None
        # a template's member: the template (`Vec<T>::push`), not a specialisation of it
        written = "::".join((p.child_by_field_name("name") or p).text.decode()
                            if p.type == "template_type" else p.text.decode() for p in parts)
        name = cur.text.decode()
        if cur.type == "destructor_name":
            name = "~" + name.lstrip("~").strip()
        return written, name, tparams

    def file_local_node(self, node):
        cur = node.parent
        while cur is not None:
            if cur.type == "namespace_definition" and cur.child_by_field_name("name") is None:
                return True
            cur = cur.parent
        return False

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
        for _ in range(2):   # `class API DEPRECATED Name`: one macro per pass
            src = _CLASS_MACRO.sub(_class_macro, src)
        src = _ATTRIBUTE_MACRO.sub(_attribute_macro, src)
        if b"Q_" in src or b"QT_" in src or b"QML_" in src or b"signals" in src or b"slots" in src:
            src = _QT_STATEMENT.sub(lambda m: m.group(1) + _spaces(m.group(0)[len(m.group(1)):]), src)
            src = _QT_INLINE.sub(lambda m: b" " * len(m.group(0)), src)
            src = _QT_SECTION.sub(_qt_section, src)
        src = _blank_statement_macros(src)
        src = _blank_leading_macros(src)
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

    base_names_in_scope = True

    def macro_declared_names(self, src):
        out = []
        for i, line in enumerate(src.split(b"\n"), 1):
            m = _STATEMENT_MACRO.match(line)
            if m and b"(" in line:
                macro = line.split(b"(", 1)[0].strip().decode("utf-8", "replace")
                args = line.split(b"(", 1)[1]
                # names, not other macros: `XMLException`, `DataException`; not `XML_API`
                out += [(n.decode(), i, macro) for n in re.findall(rb"\b([A-Z]\w*[a-z]\w*)", args)]
        return out

    def owns_namespace(self, namespace):
        # a project may only specialise templates in std, not declare types there
        return namespace != "std" and not namespace.startswith("std::")

    def is_import(self, node):
        # `using Base::Base;` in a class body is a member declaration; at file or namespace
        # level, also inside `#ifndef GUARD_H`, it imports
        cur = node.parent
        while cur is not None:
            if cur.type == "field_declaration_list":
                return False
            cur = cur.parent
        return True

    def member_name(self, kind, name):
        # `MAX = #if ... sizeof(struct in6_addr) #else ... #endif` in an enum does not
        # parse, and `sizeof` comes out as an enumerator: no member is called that
        return None if name in _RESERVED else name

    def is_opaque(self, node):
        # `template <class S> class Ev<void, S> { ... }`: a specialisation is no type, and
        # neither are the types and members in it. `struct { P inner; } var;`: the members
        # are var's (`var.inner`), not the enclosing class's, as they are of an anonymous
        # union without a variable
        if node.type in ("class_specifier", "struct_specifier", "union_specifier"):
            name = node.child_by_field_name("name")
            if name is None:
                parent = node.parent
                return parent is not None and parent.type in ("field_declaration", "declaration") \
                    and parent.child_by_field_name("declarator") is not None
            return name.type == "template_type"
        return node.type in self.opaque_nodes

    def type_text(self, type_node, text, src):
        # `struct Tag { P p; } tagged;`, `enum Mode { A, B } mode;`: a type defined in place
        # is named by its name, not its body; an anonymous one has no name to point at
        if type_node.type in ("class_specifier", "struct_specifier", "union_specifier",
                              "enum_specifier") and type_node.child_by_field_name("body") is not None:
            name = type_node.child_by_field_name("name")
            return name.text.decode() if name is not None else None
        return text

    def declarator(self, node, src):
        # `poco_static_assert (offsetof(Hdr, code) == 0x01);` in a class body: a macro call
        # the grammar takes for a declarator in parentheses, with an error inside
        if node.type == "parenthesized_declarator" and any(c.type == "ERROR" for c in node.children):
            return None, "", False
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
        return "public" if owner_kind in ("struct", "union") else "private"

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
