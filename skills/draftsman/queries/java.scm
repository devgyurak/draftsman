; Draftsman extraction query for Java.
; Capture naming protocol: see references/query-protocol.md

; ---------------------------------------------------------------- file scope
(package_declaration [(identifier) (scoped_identifier)] @package)

(import_declaration "static"? @import.static [(identifier) (scoped_identifier)] @import .)
(import_declaration "static"? @import.static [(identifier) (scoped_identifier)] @import.wildcard
  (asterisk))

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

; ---------------------------------------------------------------- bodies
; where names are read: bodies of members, field initializers, enum constants
(method_declaration body: (block) @body.region)
(constructor_declaration body: (constructor_body) @body.region)
(variable_declarator value: (_) @body.region)
(enum_constant arguments: (argument_list) @body.region)
(enum_constant body: (class_body) @body.region)
(class_body (block) @body.init)
(enum_body_declarations (block) @body.init)
(static_initializer) @body.init
(compact_constructor_declaration name: (identifier) @body.init.name body: (block) @body.init)

; names written in a body: every type, as a whole and as its parts (the extractor keeps the
; whole); `var` is no name
((type_identifier) @body.ref.type (#not-eq? @body.ref.type "var"))
(scoped_type_identifier) @body.ref.type
(record_pattern [(identifier) (scoped_identifier)] @body.ref.type)
; `o.new Inner()`: a member of o's type, which the scope does not tell
(object_creation_expression (_) . "." . "new"
  type: [(type_identifier) @body.unread (generic_type (type_identifier) @body.unread)])
; `X.super::m`: X is the name, in type position; `super` is none
((type_identifier) @body.unread (#eq? @body.unread "super"))
(method_reference . (scoped_type_identifier (type_identifier) @_s .) @body.unread
  (#eq? @_s "super"))
; `X.this`, `X.super.m()`: only a type can stand before them; `X.this.m()` is no receiver X,
; and the extractor drops the receiver of `X.super.m()` (the type pattern below records it)
(method_invocation object: [(identifier) (field_access field: (identifier))] @body.ref.receiver)
; `Foo.X`, `case Kind.A`, `Foo.X.m()`; `Foo::m`, `Foo::new` (`Foo[]::new` is a type)
(field_access object: [(identifier) (field_access field: (identifier))] @body.ref.receiver
  field: (identifier))
(method_reference . [(identifier) (field_access field: (identifier))] @body.ref.receiver)
(field_access object: (_) @body.ref.type field: (this))
(method_invocation object: (_) @body.ref.type . (super))

; what may hide one: variables, local classes and type parameters declared in the member
(variable_declarator name: (identifier) @body.var)
(formal_parameter name: (identifier) @body.var)
(catch_formal_parameter name: (identifier) @body.var)
(enhanced_for_statement name: (identifier) @body.var)
(resource name: (identifier) @body.var)
(lambda_expression parameters: (identifier) @body.var)
(inferred_parameters (identifier) @body.var)
(instanceof_expression name: (identifier) @body.var)
(type_pattern (identifier) @body.var)
(record_pattern_component (identifier) @body.var)
(type_parameter (type_identifier) @body.type)
(class_declaration name: (identifier) @body.type)
(interface_declaration name: (identifier) @body.type)
(enum_declaration name: (identifier) @body.type)
(record_declaration name: (identifier) @body.type)
(annotation_type_declaration name: (identifier) @body.type)

; the members an anonymous or local class inherits are in scope inside it
(object_creation_expression . "new" type: (_) @body.class.super (class_body) @body.class)
(class_declaration superclass: (superclass (_) @body.class.super) body: (class_body) @body.class)
(class_declaration (super_interfaces (type_list (_) @body.class.super)) body: (class_body) @body.class)
(interface_declaration (extends_interfaces (type_list (_) @body.class.super)) body: (interface_body) @body.class)
(enum_declaration (super_interfaces (type_list (_) @body.class.super)) body: (enum_body) @body.class)
(record_declaration (super_interfaces (type_list (_) @body.class.super)) body: (class_body) @body.class)
