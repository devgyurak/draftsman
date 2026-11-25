; Draftsman extraction query for TypeScript (also used for TSX).
; Capture naming protocol: see references/query-protocol.md

; ---------------------------------------------------------------- file scope
(internal_module name: (_) @namespace.name) @namespace

(import_statement
  (import_clause (named_imports
    (import_specifier name: (identifier) @import.name alias: (identifier)? @import.alias)))
  source: (string (string_fragment) @import.from))
(import_statement
  (import_clause (identifier) @import.name)
  source: (string (string_fragment) @import.from))
(import_statement
  (import_clause (namespace_import (identifier) @import.alias))
  source: (string (string_fragment) @import.module))
; re-exports make `index.ts` barrels resolvable
(export_statement
  (export_clause (export_specifier name: (identifier) @import.name alias: (identifier)? @import.alias))
  source: (string (string_fragment) @import.from))
(export_statement "*" source: (string (string_fragment) @import.wildcard))

; ---------------------------------------------------------------- types
(class_declaration name: (type_identifier) @name) @type.class
(abstract_class_declaration name: (type_identifier) @name) @type.abstract_class
(interface_declaration name: (type_identifier) @name) @type.interface
(enum_declaration name: (identifier) @name) @type.enum

(type_parameters (type_parameter name: (type_identifier) @tparam))

(export_statement
  decorator: (decorator [(identifier) @annotation (call_expression function: (_) @annotation)])
  declaration: (_) @annotation.target)
(class_declaration
  decorator: (decorator [(identifier) @annotation (call_expression function: (_) @annotation)]))
  @annotation.target
; the decorator and the names its arguments pass, on a class, a member or a parameter;
; `export @Dec() class` puts the decorator outside the class
(decorator [(identifier) (member_expression)] @annotation.ref.name) @annotation.ref
(decorator (call_expression function: (_) @annotation.ref.name arguments: (_) @annotation.ref.args))
  @annotation.ref
(export_statement
  decorator: (decorator [(identifier) (member_expression)] @annotation.ref.name) @annotation.ref
  declaration: (_) @annotation.ref.target)
(export_statement
  decorator: (decorator (call_expression function: (_) @annotation.ref.name
                                         arguments: (_) @annotation.ref.args)) @annotation.ref
  declaration: (_) @annotation.ref.target)

; ---------------------------------------------------------------- supertypes
(class_heritage (extends_clause value: (_) @super.extends))
(class_heritage (implements_clause (_) @super.implements))
(interface_declaration (extends_type_clause type: (_) @super.extends))

; ---------------------------------------------------------------- members
(public_field_definition
  name: (_) @name
  type: (type_annotation (_) @type)?) @member.field
(property_signature
  name: (_) @name
  type: (type_annotation (_) @type)?) @member.field

; constructor parameter properties: constructor(private repo: Repo)
(method_definition
  name: (property_identifier) @_ctor (#eq? @_ctor "constructor")
  parameters: (formal_parameters
    (required_parameter (accessibility_modifier) pattern: (identifier) @name
                        type: (type_annotation (_) @type)?) @member.field))
(method_definition
  name: (property_identifier) @_ctor (#eq? @_ctor "constructor")
  parameters: (formal_parameters
    (required_parameter "readonly" pattern: (identifier) @name
                        type: (type_annotation (_) @type)?) @member.field))
(method_definition
  name: (property_identifier) @_ctor (#eq? @_ctor "constructor")
  parameters: (formal_parameters
    (optional_parameter [(accessibility_modifier) "readonly"] pattern: (identifier) @name
                        type: (type_annotation (_) @type)?) @member.field))

(method_definition
  name: (_) @name
  return_type: (type_annotation (_) @type)?
  body: (_)? @body) @member.method
(method_signature
  name: (_) @name
  return_type: (type_annotation (_) @type)?) @member.method
(abstract_method_signature
  name: (_) @name
  return_type: (type_annotation (_) @type)?) @member.method
; a type predicate as the return type: `x is Logger`, `asserts x is Logger`
(method_definition
  name: (_) @name
  return_type: [(type_predicate_annotation (_) @type) (asserts_annotation (_) @type)] body: (_)? @body) @member.method
(method_signature
  name: (_) @name
  return_type: [(type_predicate_annotation (_) @type) (asserts_annotation (_) @type)]) @member.method
(abstract_method_signature
  name: (_) @name
  return_type: [(type_predicate_annotation (_) @type) (asserts_annotation (_) @type)]) @member.method

(enum_body (property_identifier) @name @member.enum_constant)
(enum_body (enum_assignment name: (_) @name) @member.enum_constant)

; ---------------------------------------------------------------- parameters
(method_definition
  parameters: (formal_parameters
    [(required_parameter pattern: [(identifier) (rest_pattern) (object_pattern) (array_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)
     (optional_parameter pattern: [(identifier) (object_pattern) (array_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)] @param))
(method_signature
  parameters: (formal_parameters
    [(required_parameter pattern: [(identifier) (rest_pattern) (object_pattern) (array_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)
     (optional_parameter pattern: [(identifier) (object_pattern) (array_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)] @param))
(abstract_method_signature
  parameters: (formal_parameters
    [(required_parameter pattern: [(identifier) (rest_pattern) (object_pattern) (array_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)
     (optional_parameter pattern: [(identifier) (object_pattern) (array_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)] @param))

; ---------------------------------------------------------------- aliases
(type_alias_declaration name: (type_identifier) @alias value: (_) @alias.type)
; `import Inner = Outer.Inner;` (an import alias of a namespace member)
(import_alias (identifier) @alias . (nested_identifier) @alias.type)

; ---------------------------------------------------------------- bodies
; where names are read: bodies of methods and accessors, field initializers, static
; blocks, enum members' values
(method_definition body: (statement_block) @body.region)
(public_field_definition value: (_) @body.region)
(enum_assignment value: (_) @body.region)
(class_static_block) @body.init

; names written in a body. A type name stands where only a type can (`: Foo`, `as Foo`,
; `<Foo>`, `implements Foo`); any other name is a value, which a variable may be: `new
; Foo()`, `Foo.m()`, `x instanceof Foo`, `typeof Foo`, `<Foo />`, `Foo` as an argument.
; A dotted value is captured as a whole and by its parts (the extractor keeps the whole).
; A plain value that starts lower-case is left out: it is a variable or a function in all
; but a class named so, which is then missed, never misread, and the extraction is faster
(type_identifier) @body.ref.type
(nested_type_identifier) @body.ref.type
((identifier) @body.ref.receiver (#match? @body.ref.receiver "^[^a-z]"))
(member_expression object: [(identifier) (member_expression)]) @body.ref.receiver
(shorthand_property_identifier) @body.ref.receiver
; a decorator's arguments are no body (queries/tsx.scm adds JSX's closing tags)
(decorator) @body.blind
; a label in a type is no name: `[Foo: string]`, `{ [Key: string]: number }`
(tuple_type [(required_parameter name: (identifier) @body.unread)
             (optional_parameter name: (identifier) @body.unread)])
(index_signature name: (identifier) @body.unread)

; what may hide one: variables, functions, local types and type parameters declared in
; the member
(variable_declarator name: (identifier) @body.var)
(required_parameter pattern: (identifier) @body.var)
(optional_parameter pattern: (identifier) @body.var)
(arrow_function parameter: (identifier) @body.var)
(catch_clause parameter: (identifier) @body.var)
(for_in_statement left: (identifier) @body.var)
(function_declaration name: (identifier) @body.var)
(generator_function_declaration name: (identifier) @body.var)
(function_expression name: (identifier) @body.var)
(pair_pattern value: (identifier) @body.var)
(array_pattern (identifier) @body.var)
(rest_pattern (identifier) @body.var)
(assignment_pattern left: (identifier) @body.var)
(shorthand_property_identifier_pattern) @body.var
(type_parameter name: (type_identifier) @body.type)
(class_declaration name: (type_identifier) @body.type)
(abstract_class_declaration name: (type_identifier) @body.type)
(class name: (type_identifier) @body.type)
(interface_declaration name: (type_identifier) @body.type)
(type_alias_declaration name: (type_identifier) @body.type)
(enum_declaration name: (identifier) @body.type)
(mapped_type_clause name: (type_identifier) @body.type)
(infer_type (type_identifier) @body.type)
