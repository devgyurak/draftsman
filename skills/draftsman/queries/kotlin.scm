; Draftsman extraction query for Kotlin.
; Capture naming protocol: see references/query-protocol.md
; Most Kotlin nodes have no field names, so patterns are positional.

; ---------------------------------------------------------------- file scope
(package_header (identifier) @package)

(import_header (identifier) @import .)
(import_header (identifier) @import (import_alias (type_identifier) @import.alias))
(import_header (identifier) @import.wildcard (wildcard_import))

; ---------------------------------------------------------------- types
(class_declaration (modifiers)? @modifiers (type_identifier) @name) @type.class
(class_declaration (modifiers)? @modifiers "interface" (type_identifier) @name) @type.interface
(class_declaration (modifiers)? @modifiers "enum" (type_identifier) @name) @type.enum
(class_declaration (modifiers (class_modifier "annotation")) @modifiers (type_identifier) @name)
  @type.annotation
(object_declaration (modifiers)? @modifiers (type_identifier) @name) @type.object
; a companion with supertypes is the object that implements them (`companion object :
; Parcelable.Creator<A>`), so it is a type, `A.Companion`; one without stays a static scope
(companion_object (modifiers)? @modifiers "companion" @name (delegation_specifier)) @type.object

(type_parameters (type_parameter (type_identifier) @tparam))

; ---------------------------------------------------------------- supertypes
; `Base()` is a superclass; a bare type is an interface for classes
(delegation_specifier (constructor_invocation (user_type) @super.extends))
(delegation_specifier (user_type) @super.inherits)
(delegation_specifier (explicit_delegation (user_type) @super.inherits))

; ---------------------------------------------------------------- members
(property_declaration
  (modifiers)? @modifiers
  (variable_declaration (simple_identifier) @name [(user_type) (nullable_type) (function_type)] @type))
  @member.property
(property_declaration
  (modifiers)? @modifiers
  (variable_declaration (simple_identifier) @name .)) @member.property

; primary constructor parameters declared with val/var are properties
(primary_constructor
  (class_parameter
    (modifiers)? @modifiers
    (binding_pattern_kind)
    (simple_identifier) @name
    [(user_type) (nullable_type) (function_type)] @type) @member.property)

(function_declaration
  (modifiers)? @modifiers
  (receiver_type)? @receiver
  (simple_identifier) @name
  (function_value_parameters)
  .
  [(user_type) (nullable_type) (function_type)] @type) @member.method
(function_declaration
  (modifiers)? @modifiers
  (receiver_type)? @receiver
  (simple_identifier) @name
  (function_body)? @body) @member.method

(secondary_constructor (modifiers)? @modifiers "constructor" @name) @member.constructor
; the primary constructor, when one of its parameters is plain (no val/var): those are
; only here. One whose parameters are all properties adds nothing the properties do not
(class_declaration (type_identifier) @name
  (primary_constructor (modifiers)? @modifiers
    [(class_parameter . (simple_identifier))
     (class_parameter . (modifiers) . (simple_identifier))]) @member.constructor)

(enum_entry (simple_identifier) @name) @member.enum_constant

; ---------------------------------------------------------------- parameters
(function_declaration
  (function_value_parameters
    (parameter (simple_identifier) @param.name
               [(user_type) (nullable_type) (function_type)] @param.type) @param))
(primary_constructor
  (class_parameter (simple_identifier) @param.name
                   [(user_type) (nullable_type) (function_type)] @param.type) @param)
(secondary_constructor
  (function_value_parameters
    (parameter (simple_identifier) @param.name
               [(user_type) (nullable_type) (function_type)] @param.type) @param))

; ---------------------------------------------------------------- aliases
(type_alias (type_identifier) @alias "=" . (_) @alias.type)
