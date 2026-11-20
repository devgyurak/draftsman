; Draftsman extraction query for C#.
; Capture naming protocol: see references/query-protocol.md

; ---------------------------------------------------------------- file scope
(file_scoped_namespace_declaration name: (_) @package)
(namespace_declaration name: (_) @namespace.name) @namespace

; `using X;` makes every type of namespace X visible
(using_directive . [(identifier) (qualified_name)] @import.wildcard .)

; ---------------------------------------------------------------- types
(class_declaration (modifier)* @modifiers name: (identifier) @name) @type.class
(interface_declaration (modifier)* @modifiers name: (identifier) @name) @type.interface
(struct_declaration (modifier)* @modifiers name: (identifier) @name) @type.struct
(enum_declaration (modifier)* @modifiers name: (identifier) @name) @type.enum
(record_declaration (modifier)* @modifiers name: (identifier) @name) @type.record

(type_parameter_list (type_parameter name: (identifier) @tparam))

(_ (attribute_list (attribute name: (_) @annotation))) @annotation.target
; the attribute type and the types its arguments name, on a type, a member or a parameter
(attribute name: (_) @annotation.ref.name (attribute_argument_list)? @annotation.ref.args)
  @annotation.ref

; ---------------------------------------------------------------- supertypes
(base_list [(identifier) (generic_name) (qualified_name)] @super.inherits)
(base_list (primary_constructor_base_type type: (_) @super.extends))

; ---------------------------------------------------------------- members
(field_declaration
  (modifier)* @modifiers
  (variable_declaration
    type: (_) @type
    (variable_declarator name: (identifier) @name))) @member.field

(property_declaration
  (modifier)* @modifiers
  type: (_) @type
  name: (identifier) @name) @member.property

; positional record parameters are public properties
(record_declaration
  (parameter_list (parameter type: (_) @type name: (identifier) @name) @member.property))

(method_declaration
  (modifier)* @modifiers
  returns: (_) @type
  name: (identifier) @name
  body: (_)? @body) @member.method

(constructor_declaration
  (modifier)* @modifiers
  name: (identifier) @name) @member.constructor
; primary constructors (C# 12): `class Order(IRepo<Order> repo, Person owner)`. Records
; turn their parameters into properties instead (above)
(class_declaration name: (identifier) @name (parameter_list) @member.constructor)
(struct_declaration name: (identifier) @name (parameter_list) @member.constructor)

(enum_member_declaration name: (identifier) @name) @member.enum_constant

; ---------------------------------------------------------------- parameters
(method_declaration
  parameters: (parameter_list
    (parameter type: (_) @param.type name: (identifier) @param.name) @param))
(constructor_declaration
  parameters: (parameter_list
    (parameter type: (_) @param.type name: (identifier) @param.name) @param))
(class_declaration
  (parameter_list (parameter type: (_) @param.type name: (identifier) @param.name) @param))
(struct_declaration
  (parameter_list (parameter type: (_) @param.type name: (identifier) @param.name) @param))
; `params Q[] qs` is no parameter node: the keyword, type and name are list items
(method_declaration
  parameters: (parameter_list "params" . (_) @param.type . (identifier) @param.name @param))
(constructor_declaration
  parameters: (parameter_list "params" . (_) @param.type . (identifier) @param.name @param))

; ---------------------------------------------------------------- aliases
; drawn through: a field typed with an alias relates to what the alias names
(using_directive name: (identifier) @alias "=" . (_) @alias.type)
