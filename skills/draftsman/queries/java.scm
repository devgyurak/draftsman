; Draftsman extraction query for Java.
; Capture naming protocol: see references/query-protocol.md

; ---------------------------------------------------------------- file scope
(package_declaration [(identifier) (scoped_identifier)] @package)

(import_declaration [(identifier) (scoped_identifier)] @import .)
(import_declaration [(identifier) (scoped_identifier)] @import.wildcard (asterisk))

; ---------------------------------------------------------------- types
(class_declaration (modifiers)? @modifiers name: (identifier) @name) @type.class
(interface_declaration (modifiers)? @modifiers name: (identifier) @name) @type.interface
(enum_declaration (modifiers)? @modifiers name: (identifier) @name) @type.enum
(record_declaration (modifiers)? @modifiers name: (identifier) @name) @type.record
(annotation_type_declaration (modifiers)? @modifiers name: (identifier) @name) @type.annotation

(type_parameters (type_parameter (type_identifier) @tparam))

; ---------------------------------------------------------------- supertypes
(class_declaration superclass: (superclass (_) @super.extends))
(class_declaration (super_interfaces (type_list (_) @super.implements)))
(enum_declaration (super_interfaces (type_list (_) @super.implements)))
(record_declaration (super_interfaces (type_list (_) @super.implements)))
(interface_declaration (extends_interfaces (type_list (_) @super.extends)))

; ---------------------------------------------------------------- annotations
; on a type, a member or a parameter: the annotation type and the types its arguments name
(marker_annotation name: (_) @annotation.ref.name) @annotation.ref
(annotation name: (_) @annotation.ref.name arguments: (_) @annotation.ref.args) @annotation.ref

; ---------------------------------------------------------------- members
(field_declaration
  (modifiers)? @modifiers
  type: (_) @type
  declarator: (variable_declarator name: (identifier) @name)) @member.field

; interface constants
(constant_declaration
  (modifiers)? @modifiers
  type: (_) @type
  declarator: (variable_declarator name: (identifier) @name)) @member.field

; record components are fields
(record_declaration
  parameters: (formal_parameters
    (formal_parameter type: (_) @type name: (identifier) @name) @member.field))

(method_declaration
  (modifiers)? @modifiers
  type: (_) @type
  name: (identifier) @name
  body: (_)? @body) @member.method

(annotation_type_element_declaration
  (modifiers)? @modifiers
  type: (_) @type
  name: (identifier) @name) @member.method

(constructor_declaration
  (modifiers)? @modifiers
  name: (identifier) @name) @member.constructor

(enum_constant name: (identifier) @name) @member.enum_constant

; ---------------------------------------------------------------- parameters
; `throws E`: the method depends on E
(throws [(type_identifier) (scoped_type_identifier) (generic_type)] @throws)
(method_declaration
  parameters: (formal_parameters
    (formal_parameter type: (_) @param.type name: (identifier) @param.name) @param))
(constructor_declaration
  parameters: (formal_parameters
    (formal_parameter type: (_) @param.type name: (identifier) @param.name) @param))
(formal_parameters
  (spread_parameter
    [(type_identifier) (generic_type) (scoped_type_identifier) (array_type)
     (integral_type) (floating_point_type) (boolean_type)] @param.type
    "..." @param.varargs
    (variable_declarator name: (identifier) @param.name)) @param)
