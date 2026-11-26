; Draftsman extraction query for C#.
; Capture naming protocol: see references/query-protocol.md

; ---------------------------------------------------------------- file scope
(file_scoped_namespace_declaration name: (_) @package)
(namespace_declaration name: (_) @namespace.name) @namespace

; `using X;` makes every type of namespace X visible; `using static X;` the static members
; and nested types of type X
[(using_directive . [(identifier) (qualified_name)] @import.wildcard .)
 (using_directive "static" @import.static . [(identifier) (qualified_name)] @import.wildcard .)]

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
(base_list [(identifier) (generic_name) (qualified_name) (alias_qualified_name)] @super.inherits)
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

; ---------------------------------------------------------------- bodies (issue #5)
; where a name in a body is read: a member's block or `=>`, a constructor initializer, a
; field's, property's or enum member's initializer
(method_declaration body: (_) @body.region)
(constructor_declaration body: (_) @body.region)
(constructor_declaration (constructor_initializer) @body.region)
(accessor_declaration body: (_) @body.region)
(property_declaration value: (_) @body.region)
(variable_declarator name: (_) . (_) @body.region)
(enum_member_declaration value: (_) @body.region)
; bodies of no listed member, whose parameters are its names: their `via` is
; CSharpSpec.init_via's
(operator_declaration body: (_) @body.init.region) @body.init
(conversion_operator_declaration body: (_) @body.init.region) @body.init
(destructor_declaration body: (_) @body.init.region) @body.init
(indexer_declaration value: (_) @body.init.region) @body.init
(indexer_declaration accessors: (accessor_list) @body.init.region) @body.init
(event_declaration accessors: (accessor_list) @body.init.region) @body.init
; a primary constructor's base arguments: `class B(int x) : A(x)`, `record R(int x) : Q(x)`
(base_list (argument_list) @body.init)
(base_list (primary_constructor_base_type (argument_list) @body.init))

; where only a type can stand: every `type:` (a local's, `new`, a cast, `typeof`,
; `default`, a pattern's, `catch`, `foreach`, a lambda's or local function's parameter,
; `T?`, `T[]`), `as` and `is` with a type, type arguments, and `is Foo` alone, which
; Roslyn reads as a type before it reads a constant
(_ type: [(identifier) (generic_name) (qualified_name) (alias_qualified_name)] @body.ref.type)
(as_expression right: [(identifier) (generic_name) (qualified_name) (alias_qualified_name)] @body.ref.type)
(is_expression right: [(identifier) (generic_name) (qualified_name) (alias_qualified_name)] @body.ref.type)
(type_argument_list [(identifier) (generic_name) (qualified_name) (alias_qualified_name)] @body.ref.type)
(is_pattern_expression pattern: (constant_pattern . [(identifier) (generic_name)] .) @body.ref.type)
; `a * b` read as a pointer type in a declaration: no type
(pointer_type type: (_) @body.unread)
; `(Order) - 1`: C# reads a parenthesized name before `-`, `+`, `&`, `*`, `++`, `--` or `^`
; as an expression, not a cast (only a keyword type casts there: `(int)-1`)
(cast_expression
  type: [(identifier) (generic_name) (qualified_name) (alias_qualified_name)] @body.unread
  value: (prefix_unary_expression . ["-" "+" "&" "*" "++" "--" "^"]))
; `(Money)[0]`, `(a.Money)[0]`: nor before `[` (an element access, which tree-sitter reads
; as a cast of a collection expression); `(Money[])[...]` and `(List<Money>)[...]` can only
; be types and stay casts
(cast_expression
  type: [(identifier) (qualified_name) (alias_qualified_name)] @body.unread
  value: (collection_expression))
; a declaration expression's type: read where C# reads a declaration there (an `out`
; argument, a deconstruction's tuple; LanguageSpec.declaration_read), not where tree-sitter
; reads `F(Order < b, Customer > d)`, `[Order < b, Customer > d]` or `this[...]` as one
(declaration_expression type: (_) @body.declared_type)
; a property pattern's member path: `{ Customer.Name: "x" }` names members, not a type
(subpattern . (member_access_expression) @body.blind)

; where an expression stands, which a variable may be: the head of a member access
; (`Foo.Create()`, `Foo.Line.Make()`, `Repo<int>.Make()`), `nameof(Foo)`, a constant
; pattern (`case Status.Open:`, a switch arm's `Foo =>`, `is not Foo`, `is A.B`)
(member_access_expression
  expression: [(identifier) (generic_name) (member_access_expression) (alias_qualified_name)] @body.ref.receiver)
(invocation_expression
  function: (identifier) @_nameof (#eq? @_nameof "nameof")
  arguments: (argument_list
    (argument [(identifier) (generic_name) (member_access_expression)] @body.ref.receiver)))
(constant_pattern [(identifier) (generic_name) (member_access_expression)] @body.ref.receiver)

; variables a member declares: parameters, locals, `foreach`, `catch`, pattern and `out`
; variables, deconstruction, lambda parameters, LINQ's range variables
(parameter name: (identifier) @body.var)
(implicit_parameter) @body.var
(variable_declarator name: (identifier) @body.var)
(foreach_statement left: (identifier) @body.var)
(catch_declaration name: (identifier) @body.var)
(declaration_pattern name: (identifier) @body.var)
(declaration_expression name: (identifier) @body.var)
(recursive_pattern name: (identifier) @body.var)
(tuple_pattern name: (identifier) @body.var)
(parenthesized_variable_designation (identifier) @body.var)
(from_clause name: (identifier) @body.var)
(let_clause . (identifier) @body.var)
(join_clause (identifier) @body.var . "in")
(join_into_clause (identifier) @body.var)
(query_expression "into" . (identifier) @body.var)
(type_parameter name: (identifier) @body.type)
; a primary constructor's parameters are in scope in every body of the class (a record's
; are its properties)
(class_declaration (parameter_list (parameter name: (identifier) @body.field)))
(struct_declaration (parameter_list (parameter name: (identifier) @body.field)))
; a C# 14 extension block's receiver is a parameter of every member in it, its type
; parameters are types there (both in scope across the static class around it)
(extension_declaration (receiver_parameter name: (identifier) @body.field))
(extension_declaration (type_parameter_list (type_parameter name: (identifier) @body.hidden_tparam)))
; a delegate is a type ir.json does not record: it hides a type of its name
(delegate_declaration name: (identifier) @body.hidden_type)
; methods that extend a type: a call of one of these names may be an instance call
(method_declaration
  name: (identifier) @body.extension
  parameters: (parameter_list . (parameter (modifier) @_this (#eq? @_this "this"))))
(extension_declaration
  (extension_body [(method_declaration name: (identifier) @body.extension)
                   (property_declaration name: (identifier) @body.extension)]))
; an event field, which is no member of ir.json
(event_field_declaration (variable_declaration (variable_declarator name: (identifier) @body.field)))
; members a source generator declares in the type (CommunityToolkit.Mvvm's
; [ObservableProperty] and [RelayCommand], System.Text.Json's [JsonSerializable]):
; CSharpSpec.generated_fields names them
((attribute name: (_) @_generator) @body.generated
  (#match? @_generator "(^|[.])(ObservableProperty|RelayCommand|JsonSerializable)(Attribute)?$"))
