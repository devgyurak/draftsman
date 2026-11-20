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
