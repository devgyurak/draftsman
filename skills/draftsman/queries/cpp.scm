; Draftsman extraction query for C++.
; Capture naming protocol: see references/query-protocol.md
; Declarators (`Node* next`, `void f()`) are decoded by CppSpec.declarator.

; ---------------------------------------------------------------- file scope
(namespace_definition name: (_) @namespace.name) @namespace

(using_declaration "namespace" [(identifier) (qualified_identifier)] @import.wildcard)
; `using a::B;` imports B at file or namespace level; inside a class it is a member
; declaration (`using Base::Base;` inherits constructors, `using Base::f;` a method)
(translation_unit (using_declaration . (qualified_identifier) @import))
(declaration_list (using_declaration . (qualified_identifier) @import))

; ---------------------------------------------------------------- types
; forward declarations (no body) are not types of their own
(class_specifier name: (type_identifier) @name body: (field_declaration_list)) @type.class
(struct_specifier name: (type_identifier) @name body: (field_declaration_list)) @type.struct
(enum_specifier name: (type_identifier) @name body: (enumerator_list)) @type.enum
; out-of-class definitions of nested types: struct Table::Rep { ... }
(class_specifier name: (qualified_identifier) @name body: (field_declaration_list)) @type.class
(struct_specifier name: (qualified_identifier) @name body: (field_declaration_list)) @type.struct

(template_declaration
  parameters: (template_parameter_list
    [(type_parameter_declaration (type_identifier) @tparam)
     (optional_type_parameter_declaration name: (type_identifier) @tparam)
     (variadic_type_parameter_declaration (type_identifier) @tparam)])
  [(class_specifier) (struct_specifier) (function_definition) (field_declaration)
   (declaration)] @tparam.target)

; ---------------------------------------------------------------- supertypes
(base_class_clause [(type_identifier) (qualified_identifier) (template_type)] @super.inherits)

; ---------------------------------------------------------------- members
; fields and method declarations; `= 0` marks a pure virtual method
(field_declaration
  type: (_) @type
  declarator: (_) @declarator
  default_value: (_)? @abstract) @member.field

; inline method definitions (constructors have no type)
(function_definition
  type: (_)? @type
  declarator: (_) @declarator
  body: (_) @body) @member.method

; constructor declarations inside a class body
(field_declaration_list
  (declaration declarator: (function_declarator) @declarator) @member.method)
(field_declaration_list
  (template_declaration
    (declaration type: (_)? @type declarator: (function_declarator) @declarator) @member.method))

(enumerator name: (identifier) @name) @member.enum_constant

; ---------------------------------------------------------------- parameters
(function_declarator
  parameters: (parameter_list
    [(parameter_declaration type: (_) @param.type declarator: (_)? @param.declarator)
     (optional_parameter_declaration type: (_) @param.type declarator: (_)? @param.declarator)]
    @param))

; ---------------------------------------------------------------- aliases (not drawn)
(type_definition declarator: (type_identifier) @alias)
(alias_declaration name: (type_identifier) @alias)
(type_definition
  declarator: (function_declarator
    declarator: (parenthesized_declarator (pointer_declarator declarator: (type_identifier) @alias))))
