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

(enum_body (property_identifier) @name @member.enum_constant)
(enum_body (enum_assignment name: (_) @name) @member.enum_constant)

; ---------------------------------------------------------------- parameters
(method_definition
  parameters: (formal_parameters
    [(required_parameter pattern: [(identifier) (rest_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)
     (optional_parameter pattern: (identifier) @param.name
                         type: (type_annotation (_) @param.type)?)] @param))
(method_signature
  parameters: (formal_parameters
    [(required_parameter pattern: [(identifier) (rest_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)
     (optional_parameter pattern: (identifier) @param.name
                         type: (type_annotation (_) @param.type)?)] @param))
(abstract_method_signature
  parameters: (formal_parameters
    [(required_parameter pattern: [(identifier) (rest_pattern)] @param.name
                         type: (type_annotation (_) @param.type)?)
     (optional_parameter pattern: (identifier) @param.name
                         type: (type_annotation (_) @param.type)?)] @param))

; ---------------------------------------------------------------- aliases
(type_alias_declaration name: (type_identifier) @alias value: (_) @alias.type)
; `import Inner = Outer.Inner;` (an import alias of a namespace member)
(import_alias (identifier) @alias . (nested_identifier) @alias.type)
