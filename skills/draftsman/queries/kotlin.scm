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

; ---------------------------------------------------------------- annotations
; on a type, a member or a parameter: the annotation type and the types its arguments name
(annotation (user_type) @annotation.ref.name) @annotation.ref
(annotation (constructor_invocation (user_type) @annotation.ref.name
                                    (value_arguments) @annotation.ref.args)) @annotation.ref

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

; ---------------------------------------------------------------- bodies (issue #5)
; where a name in a body is read: a function's body, a property's initializer, delegate
; and accessors, a default argument, a secondary constructor's delegation and block, an
; enum entry's arguments and body
(function_declaration (function_body) @body.region)
(property_declaration "=" . (_) @body.region)
(property_declaration (property_delegate) @body.region)
(getter (function_body) @body.region)
(setter (function_body) @body.region)
(function_value_parameters "=" . (_) @body.region)
(class_parameter "=" . (_) @body.region)
(secondary_constructor (constructor_delegation_call) @body.region)
(secondary_constructor (statements) @body.region)
(enum_entry (value_arguments) @body.region)
(enum_entry (class_body) @body.region)
; bodies of no listed member: `init {}`, a superclass's constructor arguments
; (`: Base(Foo.x)`) and a delegate's expression (`: Action by Action(...)`)
(anonymous_initializer) @body.init
(delegation_specifier (constructor_invocation (value_arguments) @body.init))
(explicit_delegation "by" . (_) @body.init)

; where only a type can stand: a type (a local's, a parameter's, `is`, `as`, a type
; argument, `catch`, a local class's or an object's supertype, `super<Foo>`)
(user_type) @body.ref.type

; where a value may stand as well: the head of a member access (`Foo.x`, `Foo.Line.x`,
; `Outer.Inner::class`), a class literal or callable reference's receiver (`Foo::class`,
; `Foo::bar`, which a variable may be too)
(navigation_expression . [(simple_identifier) (navigation_expression)] @body.ref.receiver)
(callable_reference . (type_identifier) @body.ref.receiver)
; what is called (`Foo(1)`, `Outer.Inner()`, `Foo.create()`), or referred to as a function
; (`::Foo`): a function of the name may be called instead (KotlinSpec)
(call_expression . [(simple_identifier) (navigation_expression)] @body.ref.call)
(callable_reference . (simple_identifier) @body.ref.call)

; variables a member declares: parameters, locals, lambda parameters, destructured names,
; `for`, `catch` and `when` subjects; local functions (their calls are theirs)
(parameter (simple_identifier) @body.var)
(variable_declaration (simple_identifier) @body.var)
(catch_block (simple_identifier) @body.var)
(statements (function_declaration (simple_identifier) @body.var))
; a primary constructor's parameters: in scope in the class's initializers (a `val` one
; is a property in every body)
(class_parameter (simple_identifier) @body.field . ":")
; types a member declares: local classes, type parameters
(statements (class_declaration (type_identifier) @body.type))
(type_parameter (type_identifier) @body.type)
; the supertypes of an anonymous object and of a local class: their members are in
; scope in its body
(object_literal
  (delegation_specifier [(constructor_invocation (user_type) @body.class.super) (user_type) @body.class.super])
  (class_body) @body.class)
(class_declaration
  (delegation_specifier [(constructor_invocation (user_type) @body.class.super) (user_type) @body.class.super])
  (class_body) @body.class)
; functions and properties at a file's top, which every file may name: a call of the
; name may be such a function, any name of it such a property
(source_file (function_declaration (simple_identifier) @body.function))
(source_file (property_declaration (variable_declaration (simple_identifier) @body.value)))
; an extension's receiver (`fun Ctx.ext()`, `val Ctx.prop`): its members are names in the
; extension's body
(function_declaration (receiver_type) @body.receiver)
(property_declaration (receiver_type) @body.receiver)
; an anonymous function's (`fun Ctx.(): Int = ...`), which the grammar spreads over the
; function's children (`shop.Ctx` is two type identifiers): its first, and a simple
; name is a type in the body
(anonymous_function "fun" . (type_identifier) @body.receiver)
(anonymous_function "fun" . (type_identifier) @body.ref.type . "." . (function_value_parameters))
; a name standing alone where a value does (`listOf(Registry)`, `val x = Loading`,
; `return Kind`, `"$Registry"`, `Cause.Missing`): an object, a class's companion, or a value
; of any kind
(value_argument [(simple_identifier) (navigation_expression)] @body.ref.value .)
(statements [(simple_identifier) (navigation_expression)] @body.ref.value)
(jump_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(property_declaration "=" . [(simple_identifier) (navigation_expression)] @body.ref.value)
(function_body "=" . [(simple_identifier) (navigation_expression)] @body.ref.value)
(class_parameter "=" . [(simple_identifier) (navigation_expression)] @body.ref.value)
(function_value_parameters "=" . [(simple_identifier) (navigation_expression)] @body.ref.value)
(assignment "=" . [(simple_identifier) (navigation_expression)] @body.ref.value)
(comparison_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(equality_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(conjunction_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(disjunction_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(additive_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(multiplicative_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(elvis_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(range_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(parenthesized_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(when_subject [(simple_identifier) (navigation_expression)] @body.ref.value)
(when_condition [(simple_identifier) (navigation_expression)] @body.ref.value)
(control_structure_body [(simple_identifier) (navigation_expression)] @body.ref.value)
(interpolated_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(collection_literal [(simple_identifier) (navigation_expression)] @body.ref.value)
(prefix_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
(if_expression [(simple_identifier) (navigation_expression)] @body.ref.value)
; an infix call's operands, not its function (`Order to Kind`)
(infix_expression . [(simple_identifier) (navigation_expression)] @body.ref.value)
(infix_expression [(simple_identifier) (navigation_expression)] @body.ref.value .)
(as_expression . [(simple_identifier) (navigation_expression)] @body.ref.value)
(postfix_expression . [(simple_identifier) (navigation_expression)] @body.ref.value)
(indexing_expression . [(simple_identifier) (navigation_expression)] @body.ref.value)
; a class's delegate (`: Encoder by Identity`)
(explicit_delegation "by" . [(simple_identifier) (navigation_expression)] @body.ref.value)
(interpolated_identifier) @body.ref.value
