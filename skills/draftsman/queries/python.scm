; Draftsman extraction query for Python.
; Capture naming protocol: see references/query-protocol.md

; ---------------------------------------------------------------- file scope
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @import.from
  name: (dotted_name) @import.name)
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @import.from
  name: (aliased_import name: (dotted_name) @import.name alias: (identifier) @import.alias))
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @import.wildcard
  (wildcard_import))
(import_statement name: (dotted_name) @import.module)
(import_statement name: (aliased_import name: (dotted_name) @import.module alias: (identifier) @import.alias))

; `__all__ = ["A", "B"]` (also `+=`): the names `from m import *` brings in; `__all__` in
; any other form (`__all__.extend(...)`, `a_all + b_all`) cannot be read
(module [(assignment left: (identifier) @_all (#eq? @_all "__all__") right: (_) @exports)
         (expression_statement
           (assignment left: (identifier) @_all (#eq? @_all "__all__") right: (_) @exports))])
(module [(augmented_assignment left: (identifier) @_all (#eq? @_all "__all__")
                               right: (_) @exports)
         (expression_statement
           (augmented_assignment left: (identifier) @_all (#eq? @_all "__all__")
                                 right: (_) @exports))])
(module [(call function: (attribute object: (identifier) @_all (#eq? @_all "__all__"))) @exports
         (expression_statement
           (call function: (attribute object: (identifier) @_all (#eq? @_all "__all__")))
             @exports)])

; ---------------------------------------------------------------- types
(class_definition name: (identifier) @name) @type.class

(class_definition
  superclasses: (argument_list [(identifier) (attribute) (subscript)] @super.inherits))

(decorated_definition
  (decorator [(identifier) (attribute) (call function: (_) @annotation)] @annotation)
  definition: (_) @annotation.target)
; the decorator and the names its arguments pass; a class decorator belongs to the class
(decorated_definition
  (decorator [(identifier) (attribute)] @annotation.ref.name) @annotation.ref
  definition: (_) @annotation.ref.target)
(decorated_definition
  (decorator (call function: (_) @annotation.ref.name arguments: (_) @annotation.ref.args))
    @annotation.ref
  definition: (_) @annotation.ref.target)

; ---------------------------------------------------------------- members
; class-level assignments: dataclass fields, class variables, enum members
(class_definition
  body: (block
    (expression_statement
      (assignment left: (identifier) @name type: (type)? @type right: (_)? @value)
      @member.field)))
(class_definition
  body: (block
    (assignment left: (identifier) @name type: (type)? @type right: (_)? @value)
    @member.field))

; instance attributes: self.x = ... (only inside __init__, see PythonSpec)
(assignment
  left: (attribute object: (identifier) @_self (#eq? @_self "self") attribute: (identifier) @name)
  type: (type)? @type
  right: (_)? @value) @member.field

(function_definition
  name: (identifier) @name
  return_type: (type)? @type
  body: (_) @body) @member.method

; ---------------------------------------------------------------- parameters
(function_definition
  parameters: (parameters
    [(identifier) @param.name
     (typed_parameter (identifier) @param.name type: (type) @param.type)
     (default_parameter name: (identifier) @param.name)
     (typed_default_parameter name: (identifier) @param.name type: (type) @param.type)
     ; `*args: Item`, `**kw: Status` (the name keeps its stars)
     (typed_parameter [(list_splat_pattern) (dictionary_splat_pattern)] @param.name
                      type: (type) @param.type)
     (list_splat_pattern) @param.name
     (dictionary_splat_pattern) @param.name] @param))

; ---------------------------------------------------------------- type variables
; PEP 695: class New[K: Item, *Ts, **P], def f[T]
(class_definition
  type_parameters: (type_parameter
    (type [(identifier) @tparam
           (constrained_type . (type (identifier) @tparam))
           (splat_type (identifier) @tparam)])))
(function_definition
  type_parameters: (type_parameter
    (type [(identifier) @tparam
           (constrained_type . (type (identifier) @tparam))
           (splat_type (identifier) @tparam)])))
; module-level T = TypeVar("T") behaves like a type parameter of the whole file
(module (expression_statement
  (assignment left: (identifier) @typevar
              right: (call function: (_) @_tv (#match? @_tv "TypeVar$")))))
(module (assignment left: (identifier) @typevar
                    right: (call function: (_) @_tv (#match? @_tv "TypeVar$"))))

; ---------------------------------------------------------------- aliases
; `type X = A | B` names its target; module assignments (`X = Union[...]`) may be values
(type_alias_statement left: (type (identifier) @alias) right: (type) @alias.type)
(module (expression_statement (assignment left: (identifier) @alias)))
(module (assignment left: (identifier) @alias))

; ---------------------------------------------------------------- bodies
; where names are read: methods' bodies and the values of assignments directly in a
; class body (its fields' initializers); a method's decorators, parameters and return
; type are not
(function_definition body: (block) @body.region)
(class_definition
  body: (block (expression_statement (assignment left: (identifier) right: (_) @body.region))))
(class_definition body: (block (assignment left: (identifier) right: (_) @body.region)))

; names written in a body. Each is a value, which a variable may be, also in an
; annotation (`x: Foo`): `Foo()`, `Foo.create()`, `isinstance(x, Foo)`, `except Foo`. A
; dotted value is captured as a whole and by its parts (the extractor keeps the whole).
; A plain name that starts lower-case is left out: a class named so is missed, never
; misread
((identifier) @body.ref.receiver (#match? @body.ref.receiver "^[^a-z]"))
(attribute object: [(identifier) (attribute)]) @body.ref.receiver
; no names of the scope: a keyword argument's name, the names in an import (it binds them,
; below) and in `global`/`nonlocal`
(keyword_argument name: (identifier) @body.unread)
; `case Kind.Inner:`, `case p.Foo():`: a part after the first is no name of the scope
(dotted_name (identifier) . (identifier) @body.unread)
; nor is an attribute's name: of a dotted name it is a part (recorded with the whole), of a
; value it is no name at all (`super().Foo`, `xs[0].Foo`, `Foo().Inner`)
(attribute attribute: (identifier) @body.unread)
[(import_statement) (import_from_statement) (future_import_statement)
 (global_statement) (nonlocal_statement)] @body.blind

; a branch of a test of the platform or of the Python version (`if sys.platform ==
; "win32":`) is decided by mypy for the platform it runs on, by pyright and ty for every
; platform: no name in it is read, and a class it declares is no one class
(if_statement condition: (_) @_test (#match? @_test "sys\\.(platform|version_info)")
  consequence: (block) @body.guarded)
(if_statement condition: (_) @_test (#match? @_test "sys\\.(platform|version_info)")
  alternative: [(elif_clause consequence: (block) @body.guarded)
                (else_clause body: (block) @body.guarded)])
(elif_clause condition: (_) @_test (#match? @_test "sys\\.(platform|version_info)")
  consequence: (block) @body.guarded)
(if_statement
  alternative: (elif_clause condition: (_) @_test (#match? @_test "sys\\.(platform|version_info)"))
  alternative: (else_clause body: (block) @body.guarded))

; what may hide one: parameters (of the method and of the functions and lambdas in it),
; the names its statements bind, and local functions and classes
(parameters (identifier) @body.var)
(lambda_parameters (identifier) @body.var)
(typed_parameter . (identifier) @body.var)
(default_parameter name: (identifier) @body.var)
(typed_default_parameter name: (identifier) @body.var)
(list_splat_pattern (identifier) @body.var)
(dictionary_splat_pattern (identifier) @body.var)
(assignment left: (identifier) @body.var)
(augmented_assignment left: (identifier) @body.var)
(pattern_list (identifier) @body.var)
(tuple_pattern (identifier) @body.var)
(list_pattern (identifier) @body.var)
(for_statement left: (identifier) @body.var)
(for_in_clause left: (identifier) @body.var)
(as_pattern_target [(identifier) @body.var
                    (parenthesized_expression (identifier) @body.var)
                    (tuple [(identifier) @body.var (list_splat (identifier) @body.var)])
                    (list [(identifier) @body.var (list_splat (identifier) @body.var)])])
(named_expression name: (identifier) @body.var)
; `del Foo` binds Foo as much as an assignment does (in a function it is a local)
(delete_statement [(identifier) @body.var
                   (expression_list [(identifier) @body.var
                                     (tuple (identifier) @body.var) (list (identifier) @body.var)])
                   (tuple (identifier) @body.var) (list (identifier) @body.var)])
(nonlocal_statement (identifier) @body.var)
(case_pattern . (dotted_name . (identifier) @body.var .) .)
; `case Bar(real=Foo)`, `case Bar() as Foo`, `case [*Foo]`, `case {**Foo}` bind Foo; in
; `case Bar(Foo=0)` it is an attribute's name
(keyword_pattern (dotted_name . (identifier) @body.var .))
(keyword_pattern . (identifier) @body.unread)
(as_pattern (case_pattern) (identifier) @body.var)
(splat_pattern (identifier) @body.var)
(function_definition name: (identifier) @body.var)
(class_definition name: (identifier) @body.type)
(type_alias_statement left: (type (identifier) @body.var))
; `type Pair[T] = tuple[T, T]`: Pair, and T in the statement
(type_alias_statement left: (type (generic_type . (identifier) @body.var)))
(type_alias_statement left: (type (generic_type (type_parameter
  (type [(identifier) @body.var (constrained_type . (type (identifier) @body.var))
         (splat_type (identifier) @body.var)])))))
(function_definition type_parameters: (type_parameter
  (type [(identifier) @body.type (constrained_type . (type (identifier) @body.type))
         (splat_type (identifier) @body.type)])))
(class_definition type_parameters: (type_parameter
  (type [(identifier) @body.type (constrained_type . (type (identifier) @body.type))
         (splat_type (identifier) @body.type)])))
; an import in a function binds its names there (at the top of the file it is an import)
(import_from_statement name: (dotted_name . (identifier) @body.import))
(import_from_statement name: (aliased_import alias: (identifier) @body.import))
(import_statement name: (dotted_name . (identifier) @body.import))
(import_statement name: (aliased_import alias: (identifier) @body.import))
; `global Foo` makes Foo a variable of the module, wherever the function stands
(global_statement (identifier) @body.global)
