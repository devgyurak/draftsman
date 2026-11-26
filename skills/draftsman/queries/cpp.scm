; Draftsman extraction query for C++.
; Capture naming protocol: see references/query-protocol.md
; Declarators (`Node* next`, `void f()`) are decoded by CppSpec.declarator.

; ---------------------------------------------------------------- file scope
(namespace_definition name: (_) @namespace.name) @namespace

(using_declaration "namespace" [(identifier) (qualified_identifier)] @import.wildcard)
; `using a::B;` imports B; inside a class it is a member declaration (`using Base::Base;`
; inherits constructors), which CppSpec.is_import skips
(using_declaration . (qualified_identifier) @import)

; ---------------------------------------------------------------- types
; forward declarations (no body) are not types of their own
(class_specifier name: (type_identifier) @name body: (field_declaration_list)) @type.class
(struct_specifier name: (type_identifier) @name body: (field_declaration_list)) @type.struct
(enum_specifier name: (type_identifier) @name body: (enumerator_list)) @type.enum
; a named union is a type; the members of an anonymous one belong to the enclosing class
(union_specifier name: (type_identifier) @name body: (field_declaration_list)) @type.union
; C: `typedef struct { ... } Point;` is an anonymous struct named by its typedef
(type_definition type: (struct_specifier !name body: (field_declaration_list)) @type.struct
  . declarator: (type_identifier) @name)
(type_definition type: (enum_specifier !name body: (enumerator_list)) @type.enum
  . declarator: (type_identifier) @name)
; out-of-class definitions of nested types: struct Table::Rep { ... }
(class_specifier name: (qualified_identifier) @name body: (field_declaration_list)) @type.class
(struct_specifier name: (qualified_identifier) @name body: (field_declaration_list)) @type.struct
(union_specifier name: (qualified_identifier) @name body: (field_declaration_list)) @type.union

(template_declaration
  parameters: (template_parameter_list
    [(type_parameter_declaration (type_identifier) @tparam)
     (optional_type_parameter_declaration name: (type_identifier) @tparam)
     (variadic_type_parameter_declaration (type_identifier) @tparam)
     ; values (`std::size_t N`, `int N = 8`, `int... Is`, `auto V`) and templates
     ; (`template <class> class C`): in the template they hide types of the same name
     (parameter_declaration declarator: (identifier) @tparam)
     (optional_parameter_declaration declarator: (identifier) @tparam)
     (variadic_parameter_declaration declarator: (variadic_declarator (identifier) @tparam))
     (template_template_parameter_declaration
       [(type_parameter_declaration (type_identifier) @tparam)
        (optional_type_parameter_declaration name: (type_identifier) @tparam)
        (variadic_type_parameter_declaration (type_identifier) @tparam)])])
  [(class_specifier) (struct_specifier) (union_specifier) (function_definition)
   (field_declaration) (declaration)] @tparam.target)

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
; conversion operators (`operator const Item&() const;`): their type is in the declarator
(field_declaration_list (declaration declarator: (operator_cast) @declarator) @member.method)
; member function templates, also returning a reference or a pointer
(field_declaration_list
  (template_declaration
    (declaration type: (_)? @type
                 declarator: [(function_declarator) (reference_declarator) (pointer_declarator)]
                 @declarator) @member.method))

(enumerator name: (identifier) @name) @member.enum_constant

; ---------------------------------------------------------------- parameters
(function_declarator
  parameters: (parameter_list
    [(parameter_declaration type: (_) @param.type declarator: (_)? @param.declarator)
     (optional_parameter_declaration type: (_) @param.type declarator: (_)? @param.declarator)]
    @param))

; ---------------------------------------------------------------- aliases
(type_definition type: (_) @alias.type declarator: (type_identifier) @alias)
(type_definition type: (_) @alias.type
  declarator: [(pointer_declarator declarator: (type_identifier) @alias)
               (reference_declarator (type_identifier) @alias)])
(alias_declaration name: (type_identifier) @alias type: (_) @alias.type)
(type_definition
  declarator: (function_declarator
    declarator: (parenthesized_declarator (pointer_declarator declarator: (type_identifier) @alias))))

; ---------------------------------------------------------------- bodies (issue #5)
; where a name in a body is read: a function's body, a constructor's initializers, a
; default argument, a default member initializer, an enumerator's value, a variable's
; initializer (a static member's, defined out of its class)
(function_definition body: (compound_statement) @body.region)
(function_definition (field_initializer_list) @body.region)
(field_declaration default_value: (_) @body.region)
(optional_parameter_declaration default_value: (_) @body.region)
(enumerator value: (_) @body.region)
(init_declarator value: (_) @body.region)
; a friend function defined in a class: the class's, as written there; and a class's
; operator or destructor defined in it, which is no member the declarations list
(friend_declaration (function_definition body: (_) @body.init.region) @body.init)
(field_declaration_list
  (function_definition declarator: [(function_declarator declarator: [(operator_name) (destructor_name)])
                                    (reference_declarator (function_declarator declarator: (operator_name)))
                                    (pointer_declarator declarator: (function_declarator declarator: (operator_name)))]
                       body: (_) @body.init.region) @body.init)
(field_declaration_list (function_definition declarator: (operator_cast) body: (_) @body.init.region) @body.init)
(field_declaration_list
  (template_declaration
    (function_definition declarator: [(function_declarator declarator: (operator_name))
                                      (reference_declarator (function_declarator declarator: (operator_name)))
                                      (pointer_declarator declarator: (function_declarator declarator: (operator_name)))]
                         body: (_) @body.init.region)) @body.init)
; a member template's parameters, where its body is read apart (an operator's)
(template_declaration parameters: (template_parameter_list
  [(type_parameter_declaration (type_identifier) @body.type)
   (optional_type_parameter_declaration name: (type_identifier) @body.type)]))
; a member defined outside its class (`void Foo::bar() {}`, `int Foo::x = 1;`): its body
; is the class's (CppSpec.detached_owner)
(function_definition) @body.detached
(declaration declarator: (init_declarator declarator: (qualified_identifier))) @body.detached

; where only a type can stand: a declaration's type, `new`, a cast, a template argument,
; `sizeof`'s type, an elaborated `struct Foo`; and a qualified name, whose parts are types or
; namespaces (`Order::Status::Paid`, `A::B::c()`: CppSpec.values_hide_types). A parameter of
; a block-scope function declaration (`Lock l(Tag);`) may be a variable (CppSpec.ref_position)
(type_identifier) @body.ref.type
(template_type) @body.ref.type
(qualified_identifier) @body.ref.type
; where a value may stand as well: what is called (`Money(1)`, `ns::Money(1)`,
; `AutoPtr<Ch>(p)`, which a function may be), a base's initializer (`: Base(1)`, or a
; member's), `sizeof(Money)`
(call_expression function: [(identifier) (qualified_identifier) (template_function)] @body.ref.call)
(field_initializer . [(field_identifier) (qualified_identifier) (template_method)] @body.ref.call)
(sizeof_expression value: (parenthesized_expression [(identifier) (qualified_identifier)] @body.ref.receiver))
((call_expression function: (identifier) @_typeid
   arguments: (argument_list . [(identifier) (qualified_identifier)] @body.ref.receiver .))
 (#eq? @_typeid "typeid"))

; variables a member declares: parameters, locals (also `Lock l(x);`), `for`, `catch`,
; lambda captures, structured bindings; and the enumerators of an enum it declares
; (`enum { Paid };`: names of the block, not of an `enum class`)
(compound_statement (enum_specifier body: (enumerator_list (enumerator name: (identifier) @body.var.enum))))
(compound_statement (declaration type: (enum_specifier body: (enumerator_list (enumerator name: (identifier) @body.var.enum)))))
(parameter_declaration declarator: [(identifier) @body.var
                                    (pointer_declarator declarator: (identifier) @body.var)
                                    (reference_declarator (identifier) @body.var)
                                    (array_declarator declarator: (identifier) @body.var)])
(optional_parameter_declaration declarator: [(identifier) @body.var
                                             (pointer_declarator declarator: (identifier) @body.var)
                                             (reference_declarator (identifier) @body.var)])
(declaration declarator: [(identifier) @body.var
                          (pointer_declarator declarator: (identifier) @body.var)
                          (reference_declarator (identifier) @body.var)
                          (array_declarator declarator: (identifier) @body.var)
                          (function_declarator declarator: (identifier) @body.var)
                          (init_declarator declarator: [(identifier) @body.var
                                                        (pointer_declarator declarator: (identifier) @body.var)
                                                        (reference_declarator (identifier) @body.var)
                                                        (array_declarator declarator: (identifier) @body.var)])])
(for_range_loop declarator: [(identifier) @body.var
                             (pointer_declarator declarator: (identifier) @body.var)
                             (reference_declarator (identifier) @body.var)
                             (structured_binding_declarator (identifier) @body.var)])
(structured_binding_declarator (identifier) @body.var)
(lambda_capture_specifier (identifier) @body.var)
(condition_clause value: (declaration declarator: (identifier) @body.var))
; types a member declares: local classes, aliases, a local template's parameters
(compound_statement [(class_specifier name: (type_identifier) @body.type)
                     (struct_specifier name: (type_identifier) @body.type)
                     (union_specifier name: (type_identifier) @body.type)
                     (enum_specifier name: (type_identifier) @body.type)])
(compound_statement (declaration type: [(class_specifier name: (type_identifier) @body.type body: (_))
                                        (struct_specifier name: (type_identifier) @body.type body: (_))
                                        (enum_specifier name: (type_identifier) @body.type body: (_))]))
(compound_statement (type_definition declarator: (type_identifier) @body.type))
(compound_statement (alias_declaration name: (type_identifier) @body.type))
; functions of a namespace, which every file may call: a call of the name may be one (with
; a return type: a constructor an error leaves at a namespace's scope is none), also in an
; `#if` branch
; (a function of a class's `#if` branch is a method: CppSpec.top_function; one pattern per
; parent: an alternation of parents around one of children matches nothing)
(translation_unit [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                   (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                   (declaration type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
                   (function_definition type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
                   (template_declaration [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                                          (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))])])
(declaration_list [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                   (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                   (declaration type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
                   (function_definition type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
                   (template_declaration [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                                          (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))])])
(preproc_if [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
             (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
             (declaration type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
             (function_definition type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
             (template_declaration [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                                    (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))])])
(preproc_ifdef [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                (declaration type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
                (function_definition type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
                (template_declaration [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                                       (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))])])
(preproc_else [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
               (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
               (declaration type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
               (function_definition type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
               (template_declaration [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                                      (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))])])
(preproc_elif [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
               (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
               (declaration type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
               (function_definition type: (_) declarator: (_ declarator: (function_declarator declarator: (identifier) @body.function)))
               (template_declaration [(declaration type: (_) declarator: (function_declarator declarator: (identifier) @body.function))
                                      (function_definition type: (_) declarator: (function_declarator declarator: (identifier) @body.function))])])
; a namespace alias of the file's scope (`namespace fs = a::inner;`): `fs::D` in a body of
; the file is a::inner::D
(translation_unit (namespace_alias_definition name: (namespace_identifier) @body.nsalias))
; the files a file includes: a body sees only the types they declare (CppSpec); and the
; types a file declares without defining them (`struct Fwd;`), where a lookup stops
(preproc_include path: [(string_literal) (system_lib_string)] @body.include)
; an include of a path a macro makes (`#include APP_UTIL`): what it includes is not known
(preproc_include path: [(identifier) (call_expression)] @body.include_unknown)
; (one pattern per parent: an alternation of parents with a negated field matches nothing)
(translation_unit (struct_specifier name: (type_identifier) @body.forward !body))
(translation_unit (class_specifier name: (type_identifier) @body.forward !body))
(translation_unit (union_specifier name: (type_identifier) @body.forward !body))
(declaration_list (struct_specifier name: (type_identifier) @body.forward !body))
(declaration_list (class_specifier name: (type_identifier) @body.forward !body))
(declaration_list (union_specifier name: (type_identifier) @body.forward !body))
(preproc_if (struct_specifier name: (type_identifier) @body.forward !body))
(preproc_if (class_specifier name: (type_identifier) @body.forward !body))
(preproc_if (union_specifier name: (type_identifier) @body.forward !body))
(preproc_ifdef (struct_specifier name: (type_identifier) @body.forward !body))
(preproc_ifdef (class_specifier name: (type_identifier) @body.forward !body))
(preproc_ifdef (union_specifier name: (type_identifier) @body.forward !body))
(preproc_else (struct_specifier name: (type_identifier) @body.forward !body))
(preproc_else (class_specifier name: (type_identifier) @body.forward !body))
(preproc_else (union_specifier name: (type_identifier) @body.forward !body))
(preproc_elif (struct_specifier name: (type_identifier) @body.forward !body))
(preproc_elif (class_specifier name: (type_identifier) @body.forward !body))
(preproc_elif (union_specifier name: (type_identifier) @body.forward !body))
; (also a template's, `template <class T> struct Box;`, and an enum's, `enum class Mode : int;`)
(translation_unit (enum_specifier name: (type_identifier) @body.forward !body))
(declaration_list (enum_specifier name: (type_identifier) @body.forward !body))
(preproc_if (enum_specifier name: (type_identifier) @body.forward !body))
(preproc_ifdef (enum_specifier name: (type_identifier) @body.forward !body))
(preproc_else (enum_specifier name: (type_identifier) @body.forward !body))
(preproc_elif (enum_specifier name: (type_identifier) @body.forward !body))
(translation_unit (template_declaration (struct_specifier name: (type_identifier) @body.forward !body)))
(translation_unit (template_declaration (class_specifier name: (type_identifier) @body.forward !body)))
(declaration_list (template_declaration (struct_specifier name: (type_identifier) @body.forward !body)))
(declaration_list (template_declaration (class_specifier name: (type_identifier) @body.forward !body)))
(preproc_if (template_declaration (struct_specifier name: (type_identifier) @body.forward !body)))
(preproc_if (template_declaration (class_specifier name: (type_identifier) @body.forward !body)))
(preproc_ifdef (template_declaration (struct_specifier name: (type_identifier) @body.forward !body)))
(preproc_ifdef (template_declaration (class_specifier name: (type_identifier) @body.forward !body)))
(preproc_else (template_declaration (struct_specifier name: (type_identifier) @body.forward !body)))
(preproc_else (template_declaration (class_specifier name: (type_identifier) @body.forward !body)))
(preproc_elif (template_declaration (struct_specifier name: (type_identifier) @body.forward !body)))
(preproc_elif (template_declaration (class_specifier name: (type_identifier) @body.forward !body)))
